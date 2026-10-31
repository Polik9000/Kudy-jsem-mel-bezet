"""A map that is really placed a few metres off (a Livelox KMZ or a pair of Livelox screenshots): the runner clicks the
controls on the map with the course (views/photo.py, the page of the photos), and the whole map is moved, turned and
scaled so that they lie where the track was at the official punch times (oroute/georef.ground_course). Only the
LatLonBox of the KMZ changes (georef.shift_kmz); the originals are kept to go back to (a new upload of a map drops
its original: storage.save_map).

What moves together: a Livelox KMZ is the map of the whole event, so the KMZ with the course of every class of the
event and the KMZ without course; a screenshot pair only its own two maps (the map with the course of the class and
the map without course made from the same pair)."""
import json
import math
import os
import shutil

import numpy as np

from oroute import georef
from oroute.kmzmap import GeoMap

from . import matching

MIN_POINTS = 3           # a similarity has 4 numbers: 3 points leave one to check
FAR_M = 40.0             # a point this far from where the others put it is on the wrong circle
PREVIEW_PX = 3000        # the map is shown on the page this large at most
ORIGINAL = "_puvodni.kmz"


def preview(conf, course_rel):
    """(path of a JPEG of the map with the course without its title bar, at most PREVIEW_PX, its size, scale, header)
    kept next to the KMZ until the KMZ changes."""
    src = conf.path(course_rel)
    st = os.stat(src)
    path = conf.path("manual", f"{os.path.basename(course_rel)}.{st.st_size}.{st.st_mtime_ns}.jpg")
    gm = GeoMap.from_kmz(src)
    W, H = gm.W, gm.H - gm.header_px
    k = min(1.0, PREVIEW_PX / max(W, H))
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im = gm.image.convert("RGB").crop((0, gm.header_px, gm.W, gm.H))
        if k < 1:
            im = im.resize((max(1, round(W * k)), max(1, round(H * k))))
        im.save(path + ".tmp.jpg", "JPEG", quality=88)
        os.replace(path + ".tmp.jpg", path)
    return path, (max(1, round(W * k)), max(1, round(H * k))), k, gm


def evaluate(gm, k, points, where, lat0, lon0, track_xy):
    """points: [(name, u, v)] clicked on the preview; where(name) -> (x, y) metres on the ground or None.
    Returns dict(ok, corr, rms, shift_m, turn_deg, scale_pct, deviation {name: m}, far [names], track [[u, v]] in
    preview pixels as the corrected map would show it)."""
    to_xy = georef.local_frame(lat0, lon0)
    use = [(n, u, v) for n, u, v in points if where(n) is not None]
    out = dict(ok=False, n=len(use), deviation={}, far=[], corr=None)
    if len(use) < MIN_POINTS:
        return out
    full = [(u / k, v / k + gm.header_px) for _, u, v in use]
    la, lo = gm.px_to_latlon([p[0] for p in full], [p[1] for p in full])
    now = np.c_[to_xy(la, lo)]
    ground = np.array([where(n) for n, _, _ in use], float)
    sv = np.linalg.svd(ground - ground.mean(0), compute_uv=False)
    if sv[1] < 0.05 * sv[0]:                    # on a line: the turn cannot be told
        out["problem"] = "line"
        return out
    corr = georef.similarity(now, ground)
    res = np.hypot(*(georef.apply_similarity(corr, now) - ground).T)
    for i, (n, _, _) in enumerate(use):
        rest = [j for j in range(len(use)) if j != i]
        if len(rest) >= 2:
            c = georef.similarity(now[rest], ground[rest])
            out["deviation"][n] = round(float(np.hypot(*(georef.apply_similarity(c, now[[i]])[0] - ground[i]))))
    out["far"] = [n for n, d in out["deviation"].items() if d > FAR_M]
    if out["far"] and len(use) >= MIN_POINTS + 1:
        # one point on the wrong circle throws the others off too: the culprit is the one without which the rest fit
        # best (as georef.fit_points does for a photo)
        def rest_rms(i):
            rest = [j for j in range(len(use)) if j != i]
            c = georef.similarity(now[rest], ground[rest])
            return float(np.sqrt((np.hypot(*(georef.apply_similarity(c, now[rest]) - ground[rest]).T) ** 2).mean()))
        culprit = min(range(len(use)), key=rest_rms)
        if rest_rms(culprit) < FAR_M / 2:
            out["far"] = [use[culprit][0]]
    centre = now.mean(0)
    moved = georef.apply_similarity(corr, [centre])[0] - centre
    out.update(corr=[float(x) for x in corr], rms=round(float(np.sqrt((res ** 2).mean())), 1),
               shift_m=round(float(np.hypot(*moved)), 1), turn_deg=round(math.degrees(corr[1]), 2),
               scale_pct=round((corr[0] - 1) * 100, 2), ok=not out["far"])
    # the track as the corrected map would carry it: ground -> where it lies on the map now -> preview pixels
    back = georef.similarity(ground, now)
    if len(track_xy):
        q = georef.apply_similarity(back, track_xy)
        kx = georef.R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
        ky = georef.R_EARTH * math.pi / 180
        u, v = gm.latlon_to_px(lat0 + q[:, 1] / ky, lon0 + q[:, 0] / kx)
        out["track"] = [[round(float(a * k), 1), round(float((b - gm.header_px) * k), 1)] for a, b in zip(u, v)]
    return out


def _record(conf, event_id):
    return conf.path("manual", f"event_{event_id}.json")


def shifted(conf, event_id):
    """What was moved by hand at the event (dict(files, by, at, shift_m, turn_deg)) or None."""
    try:
        with open(_record(conf, event_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def maps_to_move(con, e):
    """The KMZ files (relative) that move with the map with the course of the entry's class."""
    ev = con.execute("SELECT * FROM events WHERE id = ?", (e["event_id"],)).fetchone()
    if (e["course_source"] or "kmz") == "screen":
        files = [e["course_file"]]
        if ev["maponly_file"] and ev["maponly_source"] == "snimek":
            files.append(ev["maponly_file"])
        return files
    files = [r["course_file"] for r in con.execute(
        "SELECT course_file FROM classes WHERE event_id = ? AND course_file IS NOT NULL"
        " AND COALESCE(course_source, 'kmz') = 'kmz'", (e["event_id"],))]
    if ev["maponly_file"] and (ev["maponly_source"] or "kmz") == "kmz":
        files.append(ev["maponly_file"])
    return files


def apply(con, conf, e, corr, lat0, lon0, user_id, summary):
    """Move the maps (maps_to_move) by corr, keep the originals (the first ones: going back returns to what was
    uploaded), note it at the event and queue the analysis of everyone there. Returns the number of maps moved."""
    files = maps_to_move(con, e)
    for rel in files:
        orig = conf.path(rel)[:-4] + ORIGINAL
        if not os.path.exists(orig):
            shutil.copyfile(conf.path(rel), orig)
        georef.shift_kmz(conf.path(rel), conf.path(rel), corr, lat0, lon0)
    rec = shifted(conf, e["event_id"]) or dict(files=[])
    rec.update(files=sorted(set(rec["files"]) | set(files)), by=user_id, **summary)
    os.makedirs(os.path.dirname(_record(conf, e["event_id"])), exist_ok=True)
    with open(_record(conf, e["event_id"]) + ".tmp", "w", encoding="utf-8") as f:
        json.dump(rec, f)
    os.replace(_record(conf, e["event_id"]) + ".tmp", _record(conf, e["event_id"]))
    _requeue(con, e["event_id"])
    return len(files)


def revert(con, conf, event_id):
    """Back to the maps as they were uploaded. Returns how many came back."""
    rec = shifted(conf, event_id)
    if rec is None:
        return 0
    n = 0
    for rel in rec["files"]:
        orig = conf.path(rel)[:-4] + ORIGINAL
        if os.path.exists(orig) and os.path.exists(conf.path(rel)):
            shutil.copyfile(orig, conf.path(rel) + ".tmp")
            os.replace(conf.path(rel) + ".tmp", conf.path(rel))
            os.remove(orig)
            n += 1
    os.remove(_record(conf, event_id))
    _requeue(con, event_id)
    return n


def _requeue(con, event_id):
    for r in con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id WHERE c.event_id = ?",
                         (event_id,)).fetchall():
        matching.queue_analysis(con, r["id"])
