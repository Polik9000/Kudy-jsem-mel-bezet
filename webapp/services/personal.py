"""The runner's own speed model: refitted from all their analysed races with oroute.personal.fit
(newer races weigh more). The runner's notes decide which legs count (oroute.annotations)."""
import json
import os
import time

import numpy as np

from oroute import annotations
from oroute import personal as fitter

from ..db import dumps, loads

DEFAULT_SLOPE = os.path.join(os.path.dirname(fitter.__file__), "slope_prior.json")


def leg_reads(con, entry_id, analysis_id, event_id, legs=None):
    """({leg n: annotations.read_leg}, {leg n: note}) of one analysed entry.
    legs: the legs of an analysis that is not in the database yet (as analysis.json has them)."""
    notes = {r["leg_n"]: dict(r) for r in con.execute("SELECT * FROM leg_notes WHERE entry_id = ?", (entry_id,))}
    refresh = [(r["lat"], r["lon"]) for r in con.execute("SELECT lat, lon FROM refreshments WHERE event_id = ?",
                                                         (event_id,))]
    if legs is None:
        legs = [loads(r["data"]) for r in con.execute("SELECT data FROM legs WHERE analysis_id = ? ORDER BY n",
                                                      (analysis_id,))]
    return {l["leg"]: annotations.read_leg(l, notes.get(l["leg"]), refresh) for l in legs}, notes


def user_races(con, conf, user_id, fresh=None):
    """Every analysed race of the user (with best routes) as input for oroute.personal.fit.
    fresh: (entry id, output folder) of a race that is being analysed right now. It counts as well, read from
    the files in the folder (analysis.json, best/leg_samples.npz), whatever the database holds for the entry."""
    races = []
    rows = con.execute(
        "SELECT e.id AS entry_id, a.id, a.out_dir, a.has_routes, c.event_id FROM entries e"
        " JOIN classes c ON c.id = e.class_id LEFT JOIN analyses a ON a.entry_id = e.id"
        " WHERE e.user_id = ? ORDER BY e.id", (user_id,)).fetchall()
    for a in rows:
        new = fresh is not None and a["entry_id"] == fresh[0]
        if not new and not a["has_routes"]:
            continue
        out_dir = fresh[1] if new else a["out_dir"]
        path = conf.path(out_dir, "best", "leg_samples.npz")
        if not os.path.exists(path):
            continue
        d = np.load(path)
        samples = {k: d[k] for k in d.files}
        legs = None
        if new:
            with open(conf.path(out_dir, "analysis.json"), encoding="utf-8") as f:
                legs = json.load(f)["legs"]
        reads, notes = leg_reads(con, a["entry_id"], a["id"], a["event_id"], legs)
        race = annotations.model_race(samples, reads, notes)
        if race is not None and len(race["dist"]):
            races.append(race)
    return races


CLUB_MIN_RUNNERS = 3     # the club average of a terrain needs at least this many other runners ...
CLUB_MIN_SECONDS = 300   # ... each with this much of their own data in it


def club_prior(con, user_id):
    """Terrain factors of the club: for every terrain the geometric mean of the other runners' own factors
    (their latest models), where at least CLUB_MIN_RUNNERS of them have real data in it. Used as the starting
    point of a runner's factors instead of the ISOM values when OB_CLUB_PRIOR=1. Returns {class id: factor}."""
    from oroute import terrain as T
    rows = con.execute(
        "SELECT m.model FROM speed_models m JOIN users u ON u.id = m.user_id WHERE m.user_id != ? AND m.id ="
        " (SELECT MAX(id) FROM speed_models WHERE user_id = m.user_id)"
        " AND COALESCE(u.oris_regno, '') != COALESCE((SELECT oris_regno FROM users WHERE id = ?), '-')",
        (user_id, user_id)).fetchall()
    logs = {}
    for r in rows:
        m = loads(r["model"])
        for name, o in (m.get("notes", {}).get("terrain") or {}).items():
            if o.get("seconds", 0) >= CLUB_MIN_SECONDS and name in m["factors"] and m["factors"][name] > 0:
                logs.setdefault(name, []).append(np.log(m["factors"][name]))
    return {T.NAMES.index(name): float(np.exp(np.mean(v))) for name, v in logs.items() if len(v) >= CLUB_MIN_RUNNERS}


KEEP_TOL = 0.005   # "Přepočítat všechno": a model this close to the last one (relative) keeps the last one


def _same(a, b, tol=0.0):
    """The same speeds: flat speed and every terrain factor within tol (relative; 0 = equal), the same slope."""
    def close(x, y):
        return abs(x - y) <= max(1e-9, tol * abs(y))
    return a is not None and close(a["v_flat"], b["v_flat"]) and a["up_k"] == b["up_k"] \
        and all(close(a["factors"].get(k, -1), v) for k, v in b["factors"].items())


def refit(con, conf, user_id, today=None, fresh=None, tol=0.0):
    """Fit the user's model from their races (fresh: see user_races). Returns (model id or None, True if it
    differs from the last one). tol: keep the last model when the new one is this close to it (_same); the
    weights of the races depend on the day, so the same races give a slightly different model tomorrow."""
    races = user_races(con, conf, user_id, fresh)
    last = con.execute("SELECT * FROM speed_models WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    if not races:
        return (last["id"] if last else None), False
    user = con.execute("SELECT slope_file FROM users WHERE id = ?", (user_id,)).fetchone()
    slope = conf.path(user["slope_file"]) if user["slope_file"] else DEFAULT_SLOPE
    prior = club_prior(con, user_id) if conf.club_prior else None
    model = fitter.fit(races, slope=slope, today=today, prior=prior)
    model.notes["slope_own"] = bool(user["slope_file"])
    if prior:
        model.notes["club_prior"] = sorted(prior)
    if len(races) >= 2:
        # how well the other races predict each one (leave one race out), shown on the model page
        model.notes["check"] = {row["title"]: row["pooled"]
                                for row in fitter.check([dict(r) for r in races], 365.0, slope=slope, today=today)}
    new = json.loads(json.dumps(model.to_dict()))
    if _same(loads(last["model"]) if last else None, new, tol):
        return last["id"], False
    rel = os.path.join("models", f"user_{user_id}", f"model_{time.strftime('%Y%m%d_%H%M%S')}_{os.urandom(2).hex()}.json")
    os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
    model.save(conf.path(rel))
    mid = con.execute("INSERT INTO speed_models (user_id, model, file) VALUES (?, ?, ?)",
                      (user_id, dumps(new), rel)).lastrowid
    con.commit()
    return mid, True
