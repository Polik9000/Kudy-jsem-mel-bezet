"""Doplnit kontroly: the course of a class put right by hand, when the circles read from the map are not the controls
of the course (a circle cut open for a detail of the map and not found, a control number read as a circle, a map
whose purple was read wrong).

The page shows the map with the course and the points S, 1 ... N, C, where N is the number of controls in ORIS (the
runner's split times, else the class), never the number of circles found. It starts from the course read by the last
analysis: each circle goes to the control punched nearest to it (the runner's track at the official punch times,
oroute/georef.ground_course), the controls with no circle are left for the runner to click, and the circles no
control took are shown as likely extra. Saving writes the course of the class next to its KMZ
(storage.course_json, the format of oroute/course.save_course), where analyze.py takes it instead of reading the
map (runner._analyse_in, --course) until a new map with the course is uploaded (storage.save_map drops it), and the
analysis of everybody in the class is run again.

The clicking is the page of the photos (templates/ob/photo.html, static/photo.js)."""
import json
import os

import numpy as np
from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for

from oroute import georef
from oroute.course import save_course
from oroute.official import linear_sum_assignment

from .. import cfg, get_db, texts
from ..auth import login_required
from ..db import loads
from ..i18n import _
from ..services import jobs, mapfix, matching, storage
from . import bp
from .photo import TRACK_POINTS, _ground, _names, _points, _where
from .races import get_entry

FAR_M = 40.0          # a control clicked this far from where the watch was at its punch is likely another one
NEAR_M = 120.0        # a circle read from the map is the control punched within this of it
MAX_CONTROLS = 80     # a course without ORIS: at most this many controls


def _entry(entry_id):
    e = get_entry(entry_id)
    if not e["course_file"] or not os.path.exists(cfg().path(e["course_file"])):
        abort(404)
    return e


def _ground_or_none(e):
    """(ground_course, lat0, lon0, track) of the entry, or None without the run or the official split times."""
    try:
        return _ground(e)
    except jobs.Refused:
        return None


def _record(entry_id):
    """The points clicked so far (kept between the checks and the saving)."""
    return cfg().path("manual", f"kontroly_entry_{entry_id}.json")


def _saved(e):
    """(course dict, given by hand) the page starts from: the course of the class given by hand or by the placing of
    a photo, else the one the last analysis read from the map; (None, False) without either."""
    own = cfg().path(storage.course_json(e["course_file"]))
    a = get_db().execute("SELECT out_dir FROM analyses WHERE entry_id = ?", (e["id"],)).fetchone()
    for path in (own, a and cfg().path(a["out_dir"], "course.json")):
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f), path == own
            except (OSError, ValueError):
                continue
    return None, False


def _count(e, ground, course):
    """(number of controls, True when it comes from ORIS)."""
    if ground is not None:
        return len(ground[0]["controls"]), True
    row = get_db().execute("SELECT control_codes FROM classes WHERE id = ?", (e["class_id"],)).fetchone()
    codes = loads(row["control_codes"] if row else None)
    if codes:
        return len(codes), True       # not classes.controls: it often says more (runner.oris_controls)
    try:
        n = int(request.args.get("n", ""))
    except ValueError:
        n = len(course["controls"]) if course else 0
    return max(1, min(n, MAX_CONTROLS)), False


def _names_of(ground, n):
    """S, 1 ... N, C: every one may be clicked here, also a control without a punch (the course needs all of them)."""
    if ground is not None:
        return [(m, True) for m, _ok in _names(ground[0])]
    return [("S", True)] + [(str(k + 1), True) for k in range(n)] + [("C", True)]


def _start(e, n, gm, k, ground, course, own):
    """([name, u, v]) of the preview for the points the page starts with, and [[u, v]] of the circles left over."""
    if course is None:
        return [], []
    prev = lambda px: [round(float(px[0]) * k, 1), round((float(px[1]) - gm.header_px) * k, 1)]
    pts = [[name, *prev(course[key]["px"])] for name, key in (("S", "start"), ("C", "finish")) if course.get(key)]
    circles = [c["px"] for c in course["controls"]]
    if own or ground is None:
        # a course given before is in the order of the course
        return pts + [[str(i + 1), *prev(px)] for i, px in enumerate(circles[:n])], [prev(px) for px in circles[n:]]
    g0, lat0, lon0, _t = ground
    to_xy = georef.local_frame(lat0, lon0)
    where = []
    for px in circles:
        la, lo = gm.px_to_latlon(px[0], px[1])
        x, y = to_xy(la, lo)
        where.append((float(x), float(y)))
    punched = [(i, c) for i, c in enumerate(g0["controls"]) if c is not None]
    used = set()
    if punched and where:
        d = np.array([[np.hypot(c[0] - w[0], c[1] - w[1]) for w in where] for _i, c in punched])
        for r, col in zip(*linear_sum_assignment(d)):
            if d[r, col] <= NEAR_M:
                pts.append([str(punched[r][0] + 1), *prev(circles[col])])
                used.add(int(col))
    return pts, [prev(px) for j, px in enumerate(circles) if j not in used]


@bp.route("/races/<int:entry_id>/kontroly")
@login_required
def course_fix_page(entry_id):
    e = _entry(entry_id)
    ground = _ground_or_none(e)
    course, own = _saved(e)
    n, oris = _count(e, ground, course)
    _path, size, k, gm = mapfix.preview(cfg(), e["course_file"])
    pts, extra = _start(e, n, gm, k, ground, course, own)
    names = {m for m, _ok in _names_of(ground, n)}
    try:
        # the points clicked before, unless the map with the course is newer than they are
        if os.path.getmtime(_record(entry_id)) >= os.path.getmtime(cfg().path(e["course_file"])):
            with open(_record(entry_id), encoding="utf-8") as f:
                kept = [p for p in json.load(f) if p[0] in names]
            if kept:
                pts = kept
    except (OSError, ValueError):
        pass
    found = len(course["controls"]) if course and not own else None
    return render_template("ob/photo.html", e=e, size=size, names=_names_of(ground, n), points=pts, kmz=False,
                           aktivni="races", min_points=n + 2, kontroly=True, extra=extra, n=n, oris=oris,
                           found=found, own=own and _can_drop(e),
                           has_ground=ground is not None,
                           image_url=url_for("ob.course_fix_image", entry_id=entry_id),
                           check_url=url_for("ob.course_fix_points", entry_id=entry_id, n=None if oris else n),
                           save_url=url_for("ob.course_fix_save", entry_id=entry_id, n=None if oris else n))


def _can_drop(e):
    """The course given here can go back to the one read from the map: not for a photo of the map, whose course comes
    from its placing (its purple is not read)."""
    return storage.course_by_hand(cfg(), e["course_file"]) and storage.course_source(cfg(), e) not in ("photo", "manual")


@bp.route("/races/<int:entry_id>/kontroly.jpg")
@login_required
def course_fix_image(entry_id):
    from flask import send_file
    e = _entry(entry_id)
    resp = send_file(mapfix.preview(cfg(), e["course_file"])[0], mimetype="image/jpeg", max_age=0)
    resp.headers["Cache-Control"] = "private, no-cache"
    return resp


def _evaluate(e, pts):
    """What the page shows: ok (every point placed once), per control how far it is from where the watch was at its
    punch, the problems, and the track over the map (preview pixels)."""
    ground = _ground_or_none(e)
    course, _own = _saved(e)
    n, _oris = _count(e, ground, course)
    names = [m for m, _ok in _names_of(ground, n)]
    got = [p[0] for p in pts]
    if any(m not in names for m in got):
        abort(400)
    _path, _size, k, gm = mapfix.preview(cfg(), e["course_file"])
    out = dict(deviation={}, problems=[])
    if len(set(got)) < len(got):
        out["problems"].append(texts.photo_problem("same"))
    if ground is not None:
        g0, lat0, lon0, track = ground
        to_xy = georef.local_frame(lat0, lon0)
        for name, u, v in pts:
            at = _where(g0, name)
            if at is None or got.count(name) != 1:
                continue
            la, lo = gm.px_to_latlon(u / k, v / k + gm.header_px)
            x, y = to_xy(la, lo)
            out["deviation"][name] = round(float(np.hypot(float(x) - at[0], float(y) - at[1])))
        for name, dev in out["deviation"].items():
            if dev > FAR_M:
                out["problems"].append(_("Bod %(n)s je %(v)s m od místa, kde byly hodinky při ražení: asi je na jiné "
                                         "kontrole.", n=name, v=dev))
        if len(track):
            kx, ky = to_xy(lat0, lon0 + 1.0)[0], to_xy(lat0 + 1.0, lon0)[1]
            step = max(1, len(track) // TRACK_POINTS)
            uu, vv = gm.latlon_to_px(lat0 + track[::step, 1] / ky, lon0 + track[::step, 0] / kx)
            out["track"] = [[round(float(a * k), 1), round(float((b - gm.header_px) * k), 1)] for a, b in zip(uu, vv)]
    missing = [m for m in names if m not in got]
    out["ok"] = not missing and len(set(got)) == len(got)
    if out["ok"]:
        out["summary"] = _("Všechny kontroly jsou označené. Uložením se trať kategorie nahradí touhle.")
    elif missing and len(missing) <= 5:
        out["problems"].append(_("Chybí: %(names)s.", names=", ".join(missing)))
    out["rms"], out["accuracy"] = 0, 0
    return out


@bp.route("/races/<int:entry_id>/kontroly/body", methods=["POST"])
@login_required
def course_fix_points(entry_id):
    e = _entry(entry_id)
    pts = _points(entry_id)
    out = _evaluate(e, pts)
    os.makedirs(os.path.dirname(_record(entry_id)), exist_ok=True)
    with open(_record(entry_id), "w", encoding="utf-8") as f:
        json.dump(pts, f)
    return jsonify(out)


@bp.route("/races/<int:entry_id>/kontroly/ulozit", methods=["POST"])
@login_required
def course_fix_save(entry_id):
    e = _entry(entry_id)
    try:
        with open(_record(entry_id), encoding="utf-8") as f:
            pts = [tuple(p) for p in json.load(f)]
    except (OSError, ValueError):
        abort(400)
    out = _evaluate(e, pts)
    page = url_for("ob.course_fix_page", entry_id=entry_id, n=request.args.get("n"))
    if not out["ok"]:
        flash(" ".join(out["problems"]) or _("Označ všechny kontroly, start i cíl."), "error")
        return redirect(page)
    _path, _size, k, gm = mapfix.preview(cfg(), e["course_file"])
    full = {name: (u / k, v / k + gm.header_px) for name, u, v in pts}
    n = len(full) - 2
    path = cfg().path(storage.course_json(e["course_file"]))
    course = save_course(path, gm, {"start": full["S"], "controls": [full[str(i + 1)] for i in range(n)],
                                    "finish": full["C"]})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(course, by_hand=True, by=g.user["id"]), f, indent=2)
    os.remove(_record(entry_id))
    db = get_db()
    for r in db.execute("SELECT id FROM entries WHERE class_id = ?", (e["class_id"],)).fetchall():
        matching.queue_analysis(db, r["id"])
    flash(_("Trať kategorie je uložená (%(n)s kontrol). Analýza se spustí znovu.", n=n), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id))


@bp.route("/races/<int:entry_id>/kontroly/smazat", methods=["POST"])
@login_required
def course_fix_drop(entry_id):
    """Back to the course read from the map: the course given on this page goes (not the one of a placed photo)."""
    e = _entry(entry_id)
    if _can_drop(e):
        os.remove(cfg().path(storage.course_json(e["course_file"])))
        if os.path.exists(_record(entry_id)):
            os.remove(_record(entry_id))
        db = get_db()
        for r in db.execute("SELECT id FROM entries WHERE class_id = ?", (e["class_id"],)).fetchall():
            matching.queue_analysis(db, r["id"])
        flash(_("Ruční trať je smazaná, trať se zase čte z mapy. Analýza se spustí znovu."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id))
