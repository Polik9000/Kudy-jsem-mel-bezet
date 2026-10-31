"""The page "Ztratil jsem se u kontroly", a look back after the race (the rules forbid a phone and any other aid
during it, so nothing here is meant for the forest): the places near the controls where the track shows trouble,
with what could not be missed there and how to get from it to the control (oroute/lost.py, rules only); and,
for a race without a track or a place the track missed, the same from where the runner taps they roughly were.
Before the race (its day or later, no track yet) the page only says so.

The scenes are prepared once per entry by a short job (lost_scene) when the page finds them missing or stale;
the advice itself is quick and is worked out in the web process."""
import json
import os
from collections import OrderedDict

import numpy as np
from flask import abort, g, jsonify, redirect, render_template, request, url_for

from oroute import lost

from .. import cfg, get_db, texts
from ..auth import login_required
from ..db import loads
from ..services import jobs, runner
from . import bp
from .legs import DESC_MAX, save_control_desc
from .races import get_entry, map_layers, too_early

_SCENES = OrderedDict()     # path of lost.npz -> (its stamp, Scene): a few of the last ones stay unpacked
_KEEP = 6
RADII = (25, 50, 100, 150)


def _scene(entry_id):
    d = runner.lost_dir(cfg(), entry_id)
    pj, pn = os.path.join(d, "lost.json"), os.path.join(d, "lost.npz")
    try:
        st = os.stat(pn)
    except OSError:
        return None
    key = (st.st_size, st.st_mtime_ns)
    hit = _SCENES.get(pn)
    if hit and hit[0] == key:
        _SCENES.move_to_end(pn)
        return hit[1]
    try:
        sc = lost.Scene.load(pj, pn)
    except (OSError, ValueError, KeyError):
        return None
    _SCENES[pn] = (key, sc)
    while len(_SCENES) > _KEEP:
        _SCENES.popitem(last=False)
    return sc


def _job(db, entry_id):
    return db.execute("SELECT * FROM jobs WHERE entry_id = ? AND kind = 'lost_scene' ORDER BY id DESC LIMIT 1",
                      (entry_id,)).fetchone()


def _state(db, e, again=False):
    """(ready | preparing | failed | no_maps | too_early, the scene or None, the last job). Asks for the scene when
    it is missing or stale and nothing is preparing it; not again after it failed or was stopped with what the
    entry has now (again=True: the runner asked for it)."""
    if too_early(e):
        return "too_early", None, None
    if not e["maponly_file"] or not e["course_file"]:
        return "no_maps", None, None
    info = runner.entry_info(db, e["id"])
    if runner.lost_fresh(db, cfg(), info):
        return "ready", _scene(e["id"]), _job(db, e["id"])
    job = _job(db, e["id"])
    if job is not None and job["status"] in ("queued", "running"):
        return "preparing", None, job
    stamp = runner.lost_stamp(db, cfg(), info)
    tried = job is not None and job["status"] in ("failed", "stopped")
    if not again and tried and (loads(job["payload"]) or {}).get("stamp") == stamp:
        return "failed", None, job
    jobs.enqueue(db, "lost_scene", user_id=g.user["id"], entry_id=e["id"], payload=dict(stamp=stamp))
    return "preparing", None, _job(db, e["id"])


def _descs(db, entry_id):
    return {r["leg_n"]: r["control_desc"] for r in db.execute(
        "SELECT leg_n, control_desc FROM leg_notes WHERE entry_id = ? AND control_desc IS NOT NULL", (entry_id,))}


@bp.route("/races/<int:entry_id>/ztraceny")
@login_required
def lost_page(entry_id):
    e = get_entry(entry_id)
    db = get_db()
    state, sc, job = _state(db, e)
    controls = []
    if sc is not None:
        descs = _descs(db, entry_id)
        for k in sc.controls:
            S = sc.control(k)
            controls.append(dict(k=k, at=list(lost.to_latlon(S, *S["ctrl"])), desc=descs.get(k) or ""))
    r0 = int(sc.circle_m) if sc is not None else int(lost.CIRCLE_M)
    return render_template("ob/ztraceny.html", e=e, state=state, job=job, controls=controls, radii=RADII, r0=r0,
                           maps=map_layers(e) if state == "ready" else {}, back=bool(e["analysis_id"]),
                           desc_max=DESC_MAX, aktivni="races", error=(job["error"] or "").split("\n\n")[0]
                           if state == "failed" and job is not None else None)


@bp.route("/races/<int:entry_id>/ztraceny/stav.json")
@login_required
def lost_state(entry_id):
    e = get_entry(entry_id)
    state, _, job = _state(get_db(), e)
    return jsonify(state=state, progress=job["message"] if job is not None and state == "preparing" else None)


@bp.route("/races/<int:entry_id>/ztraceny/pripravit", methods=["POST"])
@login_required
def lost_prepare(entry_id):
    """Prepare the scenes again after they failed or were stopped."""
    e = get_entry(entry_id)
    _state(get_db(), e, again=True)
    return redirect(url_for("ob.lost_page", entry_id=entry_id))


def _number(d, key, lo, hi):
    v = float(d[key])
    if not (lo <= v <= hi) or v != v:
        raise ValueError
    return v


@bp.route("/races/<int:entry_id>/ztraceny/rada", methods=["POST"])
@login_required
def lost_advice(entry_id):
    """{k, lat, lon, r} -> the advice for control k from (lat, lon) unsure by r metres; without lat and lon for
    anywhere up to r from the control."""
    e = get_entry(entry_id)
    d = request.get_json(silent=True) or {}
    try:
        k = int(d["k"])
        r = _number(d, "r", 10, 200) if d.get("r") is not None else None
        lat = _number(d, "lat", -90, 90) if d.get("lat") is not None else None
        lon = _number(d, "lon", -180, 180) if d.get("lon") is not None else None
        if (lat is None) != (lon is None):
            raise ValueError
    except (ValueError, TypeError, KeyError):
        abort(400)
    sc = _scene(entry_id)
    if sc is None or not runner.lost_fresh(get_db(), cfg(), runner.entry_info(get_db(), e["id"])):
        abort(409)
    if k not in sc.controls:
        abort(400)
    a = lost.advice(sc, k, lat, lon, r or sc.circle_m, _descs(get_db(), entry_id).get(k))
    return jsonify(dict(a, sentences=texts.lost_advice(a), note=texts.lost_note(a), names=_names(a)))


def _names(a):
    """The Czech name of every helper, for the list under the advice."""
    out = []
    for h in a["helpers"]:
        name = texts.LOST_NAMES.get(h["kind"], (h["kind"],))[0]
        out.append(dict(name=name, sure=h["sure"],
                        text=f"{name}: od tebe {texts.about(h['dist'])} m na azimut {texts.bearing(h['az'])}, "
                             f"od kontroly {texts.about(h['cdist'])} m na azimut {texts.bearing(h['caz'])}"
                             + (" (nešlo minout)" if h["sure"]
                                else f" (trefil bys ji z {round(100 * h['share'])} % kruhu)")))
    return out


@bp.route("/races/<int:entry_id>/ztraceny/zpetne")
@login_required
def lost_back(entry_id):
    """?k= -> the places near control k where the track shows trouble, each with what was there to see and the
    way back (oroute/lost.look_back). Needs the analysis (the track and what it found)."""
    get_entry(entry_id)
    db = get_db()
    try:
        k = int(request.args["k"])
    except (KeyError, ValueError):
        abort(400)
    sc = _scene(entry_id)
    analysis = db.execute("SELECT * FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
    if sc is None or analysis is None:
        abort(404)
    S = sc.control(k)
    row = db.execute("SELECT data FROM legs WHERE analysis_id = ? AND n = ?", (analysis["id"], k)).fetchone()
    if S is None or row is None:
        abort(404)
    leg = json.loads(row["data"])
    if leg.get("no_data"):
        return jsonify(moments=[], track=[])
    tr = loads(analysis["track"])
    a, b = int(leg["a"]), int(leg["b"])
    cols, rows = (np.full(len(tr["t"]), np.nan) for _ in range(2))
    for i in range(a, b + 1):
        cols[i], rows[i] = lost.to_cell(S, tr["lat"][i], tr["lon"][i])
    anchors = []
    m = leg.get("mistake")
    if m and m.get("at"):
        q = lost.to_cell(S, m["at"][0], m["at"][1])
        anchors.append((a + int(np.argmin(np.hypot(cols[a:b + 1] - q[0], rows[a:b + 1] - q[1]))), f"mistake:{m['type']}"))
    for s in leg.get("stops") or []:
        anchors.append((int(s["a"]), "stop"))
    found = (leg.get("relocate") or {}).get("lost")
    if found and found.get("i") is not None:
        anchors.append((int(found["i"]), "lost"))
    summary = loads(analysis["summary"]) or {}
    out = []
    for mo in lost.look_back(S, cols, rows, tr["t"], a, b, summary.get("vref") or 3.0, anchors):
        p = lost.public_moment(S, mo)
        p.update(texts.lost_moment(p), at=[tr["lat"][mo["i"]], tr["lon"][mo["i"]]], t=tr["t"][mo["i"]] - tr["t"][a])
        out.append(p)
    return jsonify(moments=out, track=[[tr["lat"][i], tr["lon"][i]] for i in range(a, b + 1)])


@bp.route("/races/<int:entry_id>/ztraceny/popis", methods=["POST"])
@login_required
def lost_desc(entry_id):
    """{k, text}: the description of control k, typed by hand (empty: none). Only shown in the advice."""
    get_entry(entry_id)
    d = request.get_json(silent=True) or {}
    try:
        k = int(d["k"])
        if not 1 <= k <= 200:
            raise ValueError
    except (ValueError, TypeError, KeyError):
        abort(400)
    db = get_db()
    save_control_desc(db, entry_id, k, d.get("text"))
    db.commit()
    return jsonify(k=k, desc=_descs(db, entry_id).get(k) or "")
