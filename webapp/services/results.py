"""Put the outputs of analyze.py / bestroute.py (analysis.json, best.json) into the database."""
import json
import math

from ..db import dumps

SLOW = ["light green (slow run)", "green (walk)", "dark green (fight)", "undergrowth (stripes)", "marsh"]
RELOCATE = 8   # oroute.relocate.VERSION the pages expect; an analysis with another one is offered to be redone
ROUTES = 9     # the same for the best routes (bestroute.VERSION)


GPS_FAR_M = 30.0        # the track at the punch farther than this from the control ...
GPS_JUMP_KMH = 30.0     # ... or faster than this over GPS_WINDOW_S anywhere on the leg: "GPS tu asi zlobí"
GPS_WINDOW_S = 5.0      # (point to point, a second apart, plain noise of 3 m alone gives 40 km/h)


def gps_trouble(A, leg):
    """Why the GPS of a leg looks wrong (analysis.json A, one of its legs), or None: the track at the punch is more
    than GPS_FAR_M from the control, or it jumps (faster than GPS_JUMP_KMH over GPS_WINDOW_S, nobody runs that).
    dict(far_m, jump_kmh)."""
    tr, course = A.get("track") or {}, A.get("course") or []
    a, b, k = leg.get("a"), leg.get("b"), leg["leg"]
    if leg.get("no_data") or a is None or b is None or k >= len(course) or not tr.get("t") or b >= len(tr["t"]):
        return None
    lat, lon, t = tr["lat"], tr["lon"], tr["t"]
    kx = 111320.0 * math.cos(math.radians(lat[a]))

    def metres(la1, lo1, la2, lo2):
        return math.hypot((lo2 - lo1) * kx, (la2 - la1) * 110540.0)
    far = metres(lat[b], lon[b], course[k]["lat"], course[k]["lon"])
    jump, j = 0.0, a
    for i in range(a, b):
        j = max(j, i + 1)
        while j < b and t[j] - t[i] < GPS_WINDOW_S:
            j += 1
        # only whole windows (a leg shorter than one: the leg as a whole)
        if t[j] - t[i] >= GPS_WINDOW_S or (i == a and t[j] > t[i]):
            jump = max(jump, metres(lat[i], lon[i], lat[j], lon[j]) / (t[j] - t[i]) * 3.6)
    if far <= GPS_FAR_M and jump <= GPS_JUMP_KMH:
        return None
    return dict(far_m=round(far), jump_kmh=round(jump) if jump > GPS_JUMP_KMH else None)


def route(m):
    """The numbers of one route (bestroute.route_metrics) the pages show."""
    mix = m.get("mix") or {}
    return dict(time=m["time"], dist=m["dist"], climb=m["climb"], path_m=mix.get("path/road", 0.0),
                slow_m=sum(v for k, v in mix.items() if k in SLOW))


def _relocate(conf, rel):
    """What oroute/relocate.py left in the output folder: (its version, {leg: what it found at the control of
    the leg}); (None, {}) when it did not run."""
    try:
        with open(conf.path(rel, "best", "relocate.json"), encoding="utf-8") as f:
            found = json.load(f)
    except (OSError, ValueError):
        return None, {}
    return found.get("version", 1), {c["leg"]: c for c in found["controls"]}


def _with_relocate(data, r):
    """The data of a leg with the catching features around its control (r, or None for the last leg): the
    attack point before the control and the backstop beyond it come only from there."""
    data = {k: v for k, v in data.items() if k not in ("relocate", "attack", "beyond")}
    if r:
        data.update(relocate=dict(features=r["features"], lost=r["lost"]), attack=r["attack"], beyond=r.get("beyond"))
    return data


def store_relocate(con, conf, entry_id):
    """Put a fresh relocate.json of an analysed entry into its stored legs (the rest of the analysis stays).
    Returns the version stored, None when there is nothing to store."""
    a = con.execute("SELECT * FROM analyses WHERE entry_id = ? AND has_routes = 1", (entry_id,)).fetchone()
    if a is None:
        return None
    version, R = _relocate(conf, a["out_dir"])
    if version is None:
        return None
    for leg in con.execute("SELECT id, n, data FROM legs WHERE analysis_id = ?", (a["id"],)).fetchall():
        con.execute("UPDATE legs SET data = ? WHERE id = ?",
                    (dumps(_with_relocate(json.loads(leg["data"]), R.get(leg["n"]))), leg["id"]))
    # the page shows another analysis now: its stamp (views.jobs.analysis_stamp) has to change
    con.execute("UPDATE analyses SET summary = ?, finished_at = datetime('now') WHERE id = ?",
                (dumps(dict(json.loads(a["summary"] or "{}"), relocate=version)), a["id"]))
    con.commit()
    return version


def store(con, conf, entry_id, rel, has_routes, model_id):
    """Replace the entry's analysis with what is in the output folder. Returns the analysis id."""
    with open(conf.path(rel, "analysis.json"), encoding="utf-8") as f:
        A = json.load(f)
    B, top = None, {}
    if has_routes:
        with open(conf.path(rel, "best", "best.json"), encoding="utf-8") as f:
            top = json.load(f)
        B = {l["leg"]: l for l in top["legs"]}
    version, R = _relocate(conf, rel) if has_routes else (None, {})
    con.execute("DELETE FROM analyses WHERE entry_id = ?", (entry_id,))
    summary = dict(vref=A["vref"], rref=A["rref"], offset_m=A["offset_m"], est_loss=A["est_loss"],
                   weak_order=A["weak_order"], official=A["official"], dem=top.get("dem"),
                   barriers=top.get("barriers"), relocate=version, routes=top.get("version", 1) if B else None)
    aid = con.execute(
        "INSERT INTO analyses (entry_id, has_routes, total_time_s, start_utc, model_id, summary, course, track, out_dir)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (entry_id, 1 if B else 0, A["total_time"], A["start"], model_id, dumps(summary), dumps(A["course"]),
         dumps(dict(A["track"], punch=A["punch"])), rel)).lastrowid
    for leg in A["legs"]:
        data = dict(leg, gps_trouble=gps_trouble(A, leg))
        b = B.get(leg["leg"]) if B else None
        if b:
            data.update(best=route(b["best"]), line=route(b["yours"]), straight_line=route(b["straight"]),
                        best_time=b["best"]["time"], line_time=b["yours"]["time"],
                        alts=[dict(route(a), delta=a["delta"], route=a["route"]) for a in b.get("alternatives") or []],
                        balanced=bool(b.get("balanced")), crossed=b.get("crossed") or [],
                        generic=b.get("generic"), corrected=bool(b.get("corrected")))
        data = _with_relocate(data, R.get(leg["leg"]))
        con.execute("INSERT INTO legs (analysis_id, n, name, data, best_route, explain_cs, explain_en)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (aid, leg["leg"], leg["name"], dumps(data), dumps(b["route"]) if b else None,
                     b["text_cs"] if b else None, b["text_en"] if b else None))
    con.commit()
    return aid
