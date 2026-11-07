"""Placing a photo of the map by hand: the runner clicks the controls on the photo (the page shows how far each
point is from where the others put it, and the track over the photo), and saving queues the job georef_map with
the points (services/handlers.py), which straightens the photo and keeps it as the KMZ of the class.

The same page cuts out the map on a pair of Livelox screenshots by hand (services/screens.py), when the bar or the
page of Livelox was not told from the map: a rectangle dragged over the screenshot with the course.

Where the controls are on the ground is known without any background map: the runner's track at the official
punch times (oroute/georef.py ground_course)."""
import json
import os

import numpy as np
from flask import abort, flash, g, jsonify, redirect, render_template, request, send_file, url_for

from oroute import georef

from .. import cfg, get_db, texts
from ..auth import login_required
from ..db import loads
from ..i18n import _, _n
from ..services import jobs, mapfix, screens, storage
from . import bp
from .races import get_entry

TRACK_POINTS = 800     # the track over the photo, at most this many points
_cache = {}            # (fit file, start) -> ground, and photo file + mtime -> (size, quad); per process
CACHE_MAX = 32


def _photo(entry_id):
    row = get_db().execute("SELECT * FROM photos WHERE entry_id = ?", (entry_id,)).fetchone()
    if row is None or not os.path.exists(cfg().path(row["file"])):
        return None
    return row


def _ground(e):
    """(ground_course, lat0, lon0, track in metres sampled) of the entry, or jobs.Refused."""
    from ..services import runner
    from ..services.handlers import photo_track
    info = runner.entry_info(get_db(), e["id"])
    key = ("g", info["fit_file"], info["start_local"], info["splits"], info["gps_trim"])
    if key not in _cache:
        _trim()
        track, start_s, cumulative = photo_track(cfg(), info)
        lat0, lon0 = georef.track_frame(track)
        to_xy = georef.local_frame(lat0, lon0)
        x, y = to_xy(track["lat"], track["lon"])
        t = np.asarray(track["t"])
        on = (t >= start_s) & (t <= start_s + (cumulative[-1] or 0))
        xy = np.c_[x, y][on]
        step = max(1, len(xy) // TRACK_POINTS)
        _cache[key] = (georef.ground_course(track, to_xy, start_s, cumulative), lat0, lon0, xy[::step])
    return _cache[key]


def _sheet(path):
    """(size, paper_quad) of a kept photo."""
    key = ("p", path, os.path.getmtime(path))
    if key not in _cache:
        _trim()
        im = georef.open_image(path)
        _cache[key] = (im.size, georef.paper_quad(im))
    return _cache[key]


def _trim():
    if len(_cache) >= CACHE_MAX:
        _cache.clear()


def _names(ground):
    """The points the runner may click: S, 1, 2, ..., C, and whether the track says where each is."""
    out = [("S", ground["start"] is not None)]
    out += [(str(k + 1), c is not None) for k, c in enumerate(ground["controls"])]
    return out + [("C", ground["finish"] is not None)]


def _key(name):
    return name if name in ("S", "C") else int(name) - 1


def _where(ground, name):
    k = _key(name)
    return ground["start"] if k == "S" else ground["finish"] if k == "C" else ground["controls"][k]


@bp.route("/races/<int:entry_id>/fotka")
@login_required
def photo_page(entry_id):
    e = get_entry(entry_id)
    row = _photo(entry_id)
    shot = screens.row(get_db(), cfg(), e["class_id"], g.user["id"])
    if shot is not None and (request.args.get("snimek") or row is None):
        info = loads(shot["info"], {})
        box = loads(shot["crop"]) or info.get("box") or [0, 0, shot["width"], shot["height"]]
        return render_template("ob/screen_crop.html", e=e, size=(shot["width"], shot["height"]), box=box,
                               by_hand=bool(shot["crop"]), reliable=info.get("reliable", True),
                               maponly=bool(shot["maponly_file"]), aktivni="races")
    if row is None:
        flash(_("K závodu není uložená žádná fotka mapy. Nahraj ji v Podkladech (pole Mapa s tratí)."), "error")
        return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")
    try:
        ground = _ground(e)[0]
    except jobs.Refused as err:
        flash(str(err), "error")
        return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")
    size, _sheets = _sheet(cfg().path(row["file"]))
    return render_template("ob/photo.html", e=e, size=size, names=_names(ground), points=loads(row["points"], []),
                           kmz=storage.course_source(cfg(), e) == "kmz", aktivni="races",
                           min_points=georef.MANUAL_MIN)


@bp.route("/races/<int:entry_id>/fotka.jpg")
@login_required
def photo_image(entry_id):
    get_entry(entry_id)
    row = _photo(entry_id)
    if row is None:
        abort(404)
    resp = send_file(cfg().path(row["file"]), mimetype="image/jpeg", max_age=0)
    resp.headers["Cache-Control"] = "private, no-cache"
    return resp


def _points(entry_id):
    """[(name, u, v)] sent by the page, checked; abort(400) on anything else."""
    d = request.get_json(silent=True) or {}
    try:
        pts = [(str(p["control"]), float(p["u"]), float(p["v"])) for p in d.get("points", [])]
    except (KeyError, TypeError, ValueError):
        abort(400)
    if len(pts) > 200:
        abort(400)
    return pts


@bp.route("/races/<int:entry_id>/fotka/body", methods=["POST"])
@login_required
def photo_points(entry_id):
    """How the points clicked so far place the photo: per point the deviation in metres, the problems in Czech,
    and the track drawn in pixels of the photo. The points are kept, so the page shows them again later."""
    e = get_entry(entry_id)
    row = _photo(entry_id)
    if row is None:
        abort(404)
    pts = _points(entry_id)
    try:
        out = _evaluate(e, row, pts)
    except jobs.Refused as err:
        return jsonify(ok=False, problems=[str(err)])
    db = get_db()
    db.execute("UPDATE photos SET points = ? WHERE entry_id = ?", (json.dumps(pts), entry_id))
    db.commit()
    return jsonify(out)


def _evaluate(e, row, pts):
    """What the page shows for the points: ok (they place the photo), deviation per point, problems in Czech,
    the track in pixels of the photo."""
    ground, lat0, lon0, track = _ground(e)
    known = {n for n, ok in _names(ground) if ok}
    names = [p[0] for p in pts]
    if any(n not in {m for m, _p in _names(ground)} for n in names):
        abort(400)
    problems = []
    if len(set(names)) < len(names):
        problems.append(texts.photo_problem("same"))
    use = [p for p in pts if p[0] in known and names.count(p[0]) == 1]
    size, quad = _sheet(cfg().path(row["file"]))
    got = georef.fit_points([p[1:] for p in use], [_where(ground, p[0]) for p in use], size, quad)
    out = dict(ok=got["H"] is not None, kind=got["kind"], rms=got["rms"], n=got["n"], deviation={})
    for p, dev in zip(use, got["deviation"]):
        out["deviation"][p[0]] = None if dev is None else round(dev)
    for code, i in got["problems"]:
        problems.append(texts.photo_problem(code, use[i][0] if i is not None else None,
                                            got["deviation"][i] if i is not None else None))
    blocking = [c for c, _p in got["problems"] if c in ("few", "line", "mirror")]
    out["ok"] = out["ok"] and not blocking and len(set(names)) == len(names)
    if got["H"] is not None and not blocking:
        # metres -> picture centred with y up -> picture pixels
        inv = np.linalg.inv(got["H"])
        W, H = size
        q = georef.apply_h(inv, track)
        out["track"] = [[round(float(u + W / 2), 1), round(float(H / 2 - v), 1)] for u, v in q]
        out["accuracy"] = int(max(15.0, got["rms"]) + 0.5)
    out["problems"] = problems
    return out


@bp.route("/races/<int:entry_id>/fotka/ulozit", methods=["POST"])
@login_required
def photo_save(entry_id):
    e = get_entry(entry_id)
    row = _photo(entry_id)
    if row is None:
        abort(404)
    if storage.course_source(cfg(), e) == "kmz":
        flash(_("Pro tuhle kategorii už je mapa z KMZ, která je přesnější. Fotka se nepoužila."), "error")
        return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")
    pts = [tuple(p) for p in loads(row["points"], [])]
    try:
        out = _evaluate(e, row, pts)
    except jobs.Refused as err:
        flash(str(err), "error")
        return redirect(url_for("ob.photo_page", entry_id=entry_id))
    if not out["ok"]:
        flash(" ".join(out["problems"]) or texts.photo_problem("few"), "error")
        return redirect(url_for("ob.photo_page", entry_id=entry_id))
    jobs.enqueue(get_db(), "georef_map", user_id=g.user["id"], entry_id=entry_id, payload=dict(points=pts))
    flash(_("Fotka se usazuje podle tvých bodů na pozadí. Až bude hotová, analýza kategorie se spustí znovu."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")


# --- a KMZ or a screenshot pair that is placed a few metres off: moved by hand (services/mapfix.py) ----------------

def _map_points_path(entry_id):
    return cfg().path("manual", f"entry_{entry_id}.json")


def _map_entry(entry_id):
    """The entry, when its class has a map with the course from a KMZ or a screenshot pair; else abort(404)."""
    e = get_entry(entry_id)
    if storage.course_source(cfg(), e) not in ("kmz", "screen") or not os.path.exists(cfg().path(e["course_file"])):
        abort(404)
    return e


def _map_evaluate(e, pts):
    ground, lat0, lon0, track = _ground(e)
    names = {m for m, _p in _names(ground)}
    if any(p[0] not in names for p in pts):
        abort(400)
    _a, _b, k, gm = mapfix.preview(cfg(), e["course_file"])
    got = [p[0] for p in pts]
    out = mapfix.evaluate(gm, k, [p for p in pts if got.count(p[0]) == 1], lambda n: _where(ground, n),
                          lat0, lon0, track)
    problems = []
    if len(set(got)) < len(got):
        problems.append(texts.photo_problem("same"))
    if out["n"] < mapfix.MIN_POINTS:
        problems.append(_("Označ aspoň %(MIN_POINTS)s kontroly, co nejdál od sebe.", MIN_POINTS=mapfix.MIN_POINTS))
    elif out.get("problem") == "line":
        problems.append(texts.photo_problem("line"))
    for n in out["far"]:
        problems.append(_("Bod %(n)s je o %(v)s m jinde, než kam ho dávají ostatní: asi je na jiné kontrole.",
            n=n, v=out['deviation'][n]))
    out["ok"] = out["ok"] and len(set(got)) == len(got)
    if out["corr"]:
        out["summary"] = (_("Mapa by se posunula o %(shift_m).0f m a otočila o %(abs).1f° (měřítko "
                              "%(scale_pct)+.1f %%); body pak sedí na %(rms).0f m.",
                                  shift_m=out['shift_m'], abs=abs(out['turn_deg']),
                                      scale_pct=out['scale_pct'], rms=out['rms']))
        out["accuracy"] = int(max(10.0, out["rms"]) + 0.5)
    out["problems"] = problems
    return out


@bp.route("/races/<int:entry_id>/mapa-rucne")
@login_required
def map_fix_page(entry_id):
    e = _map_entry(entry_id)
    try:
        ground = _ground(e)[0]
    except jobs.Refused as err:
        flash(str(err), "error")
        return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")
    _a, size, _b, _c = mapfix.preview(cfg(), e["course_file"])
    try:
        with open(_map_points_path(entry_id), encoding="utf-8") as f:
            points = json.load(f)
    except (OSError, ValueError):
        points = []
    return render_template("ob/photo.html", e=e, size=size, names=_names(ground), points=points, kmz=False,
                           aktivni="races", min_points=mapfix.MIN_POINTS, mapa=True,
                           screen=storage.course_source(cfg(), e) == "screen",
                           image_url=url_for("ob.map_fix_image", entry_id=entry_id),
                           check_url=url_for("ob.map_fix_points", entry_id=entry_id),
                           save_url=url_for("ob.map_fix_save", entry_id=entry_id))


@bp.route("/races/<int:entry_id>/mapa-rucne.jpg")
@login_required
def map_fix_image(entry_id):
    e = _map_entry(entry_id)
    resp = send_file(mapfix.preview(cfg(), e["course_file"])[0], mimetype="image/jpeg", max_age=0)
    resp.headers["Cache-Control"] = "private, no-cache"
    return resp


@bp.route("/races/<int:entry_id>/mapa-rucne/body", methods=["POST"])
@login_required
def map_fix_points(entry_id):
    e = _map_entry(entry_id)
    pts = _points(entry_id)
    try:
        out = _map_evaluate(e, pts)
    except jobs.Refused as err:
        return jsonify(ok=False, problems=[str(err)])
    os.makedirs(os.path.dirname(_map_points_path(entry_id)), exist_ok=True)
    with open(_map_points_path(entry_id), "w", encoding="utf-8") as f:
        json.dump(pts, f)
    return jsonify(out)


@bp.route("/races/<int:entry_id>/mapa-rucne/ulozit", methods=["POST"])
@login_required
def map_fix_save(entry_id):
    e = _map_entry(entry_id)
    try:
        with open(_map_points_path(entry_id), encoding="utf-8") as f:
            pts = [tuple(p) for p in json.load(f)]
        out = _map_evaluate(e, pts)
        _a, lat0, lon0, _b = _ground(e)
    except (OSError, ValueError):
        abort(400)
    except jobs.Refused as err:
        flash(str(err), "error")
        return redirect(url_for("ob.map_fix_page", entry_id=entry_id))
    if not out["ok"]:
        flash(" ".join(out["problems"]) or _("Označ aspoň %(MIN_POINTS)s kontroly.", MIN_POINTS=mapfix.MIN_POINTS), "error")
        return redirect(url_for("ob.map_fix_page", entry_id=entry_id))
    n = mapfix.apply(get_db(), cfg(), e, out["corr"], lat0, lon0, g.user["id"],
                     dict(shift_m=out["shift_m"], turn_deg=out["turn_deg"], rms=out["rms"]))
    flash(_n(n, "Mapa posunutá o %(shift_m).0f m a otočená o %(turn).1f° (%(n)s mapa). Analýzy závodu se pustí znovu.",
             "Mapa posunutá o %(shift_m).0f m a otočená o %(turn).1f° (%(n)s mapy). Analýzy závodu se pustí znovu.",
             "Mapa posunutá o %(shift_m).0f m a otočená o %(turn).1f° (%(n)s map). Analýzy závodu se pustí znovu.",
             shift_m=out["shift_m"], turn=abs(out["turn_deg"])), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")


@bp.route("/races/<int:entry_id>/mapa-rucne/vratit", methods=["POST"])
@login_required
def map_fix_revert(entry_id):
    e = get_entry(entry_id)
    n = mapfix.revert(get_db(), cfg(), e["event_id"])
    flash(_("Mapy jsou zpět, jak byly nahrané. Analýzy závodu se pustí znovu.") if n else _("Nebylo co vracet."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")


PREVIEW_PX = 2400       # the screenshot is shown on the page for cutting it out this large at most


@bp.route("/races/<int:entry_id>/fotka/snimek.jpg")
@login_required
def screen_image(entry_id):
    """A smaller copy of the screenshot with the course kept for the class (made on the first request)."""
    e = get_entry(entry_id)
    shot = screens.row(get_db(), cfg(), e["class_id"], g.user["id"])
    if shot is None:
        abort(404)
    path = cfg().path(screens.preview_path(shot["course_file"]))
    if not os.path.exists(path):
        from PIL import Image
        im = Image.open(cfg().path(shot["course_file"])).convert("RGB")
        im.thumbnail((PREVIEW_PX, PREVIEW_PX), Image.BOX)
        tmp = path + ".tmp"
        im.save(tmp, "JPEG", quality=85)
        os.replace(tmp, path)
    resp = send_file(path, mimetype="image/jpeg", max_age=0)
    resp.headers["Cache-Control"] = "private, no-cache"
    return resp


@bp.route("/races/<int:entry_id>/fotka/orez", methods=["POST"])
@login_required
def screen_crop(entry_id):
    """The map cut out by hand on the screenshots (x0, y0, x1, y1 in pixels of the screenshot): the job places the
    pair again with that rectangle."""
    e = get_entry(entry_id)
    shot = screens.row(get_db(), cfg(), e["class_id"], g.user["id"])
    if shot is None:
        abort(404)
    try:
        x0, y0, x1, y1 = (float(request.form[k]) for k in ("x0", "y0", "x1", "y1"))
    except (KeyError, ValueError):
        abort(400)
    W, H = shot["width"], shot["height"]
    x0, x1 = sorted((min(max(x0, 0), W), min(max(x1, 0), W)))
    y0, y1 = sorted((min(max(y0, 0), H), min(max(y1, 0), H)))
    if x1 - x0 < 0.1 * W or y1 - y0 < 0.1 * H:
        flash(_("Obdélník je moc malý. Natáhni ho přes celou mapu (bez lišty a tlačítek Livelox)."), "error")
        return redirect(url_for("ob.photo_page", entry_id=entry_id, snimek=1))
    jobs.enqueue(get_db(), "georef_map", user_id=g.user["id"], entry_id=entry_id,
                 payload=dict(screens={}, crop=[round(x0), round(y0), round(x1), round(y1)]))
    flash(_("Snímky se usazují znovu s mapou, jak jsi ji ořízl. Výsledek uvidíš v úlohách."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#podklady")
