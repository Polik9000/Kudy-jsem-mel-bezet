"""Two screenshots of Livelox (with the course, and the same view with the course switched off) instead of the two
KMZ, for races whose organiser does not let the KMZ be downloaded (oroute/pair.py does the work).

The screenshot with the course becomes the map with the course of the class (as a photo would, unless a KMZ is
there); the one without becomes the map without course of the whole race, from which the best routes are found
(unless a KMZ without course is there, which is sharper and placed exactly). Both screenshots are kept for the class
and the runner: the one without the course may come later, and the map can be cut out by hand
(views/photo.py)."""
import json
import os
import shutil
import tempfile

from .. import texts
from ..db import loads
from ..i18n import _
from . import jobs, matching, runner, storage

PHOTO_SOURCES = ("image", "photo", "manual")


def row(con, conf, class_id, user_id):
    """The screenshots kept for a class and a runner, or None (also when the file is gone)."""
    r = con.execute("SELECT * FROM screens WHERE class_id = ? AND user_id = ?", (class_id, user_id)).fetchone()
    if r is None or not os.path.exists(conf.path(r["course_file"])):
        return None
    return r


def _keep(conf, src, class_id, user_id, which):
    """The screenshot at the absolute path src to its place (moved from incoming/, left where it is when it is kept
    already). Returns the relative path."""
    ext = os.path.splitext(src)[1].lower() or ".png"
    rel = os.path.join("screens", f"class_{class_id}_user_{user_id}_{which}{ext}")
    dst = conf.path(rel)
    if os.path.abspath(src) == os.path.abspath(dst):
        return rel
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    for other in (".png", ".jpg", ".jpeg"):            # an older one in another format
        old = conf.path(os.path.join("screens", f"class_{class_id}_user_{user_id}_{which}{other}"))
        if old != dst and os.path.exists(old):
            os.remove(old)
    if os.path.abspath(src).startswith(os.path.abspath(conf.path("incoming"))):
        os.replace(src, dst)
    else:
        shutil.copyfile(src, dst)
    return rel


def drop_event(con, conf, event_id):
    """A KMZ without course came for the race: the screenshots kept for its classes are of no more use. Not
    committed."""
    for r in con.execute("SELECT s.* FROM screens s JOIN classes c ON c.id = s.class_id WHERE c.event_id = ?",
                         (event_id,)).fetchall():
        for f in (r["course_file"], r["maponly_file"], preview_path(r["course_file"])):
            if f and os.path.exists(conf.path(f)):
                os.remove(conf.path(f))
        con.execute("DELETE FROM screens WHERE class_id = ? AND user_id = ?", (r["class_id"], r["user_id"]))


def _store(con, conf, cid, uid, course_p, maponly_p, kept, size, crop, state):
    """The screenshots (absolute paths, maponly_p may be None) kept for the class and the runner, with what their
    placing said. Not committed."""
    c_rel = _keep(conf, course_p, cid, uid, "trat")
    m_rel = _keep(conf, maponly_p, cid, uid, "bez") if maponly_p else None
    if kept and kept["maponly_file"] and m_rel is None and os.path.exists(conf.path(kept["maponly_file"])):
        os.remove(conf.path(kept["maponly_file"]))
    if os.path.exists(conf.path(preview_path(c_rel))):
        os.remove(conf.path(preview_path(c_rel)))
    con.execute("INSERT INTO screens (class_id, user_id, course_file, maponly_file, width, height, crop, info)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (class_id, user_id) DO UPDATE SET"
                " course_file = excluded.course_file, maponly_file = excluded.maponly_file, width = excluded.width,"
                " height = excluded.height, crop = excluded.crop, info = excluded.info, uploaded_at = datetime('now')",
                (cid, uid, c_rel, m_rel, size[0], size[1], json.dumps(crop) if crop else None, json.dumps(state)))


def preview_path(rel):
    """Where the smaller copy of a kept screenshot for the page cutting it out by hand lies."""
    return os.path.splitext(rel)[0] + "_nahled.jpg"


def _open(path):
    """A screenshot at full size, upright, RGB."""
    from PIL import Image, ImageOps
    im = Image.open(path)
    im.load()
    return ImageOps.exif_transpose(im).convert("RGB")


def place(ctx, job, p):
    """The job georef_map with payload.screens = {course: incoming file or None, maponly: incoming file or None}
    (none of them: the kept ones again, with payload.crop = [x0, y0, x1, y1] cut out by hand). Returns the text for
    the job list; raises jobs.Refused with a Czech sentence."""
    from PIL import Image

    from oroute import georef, pair

    from .handlers import photo_track
    con, conf = ctx.con, ctx.conf
    sc = p["screens"]
    new = {k: conf.path(sc[k]) for k in ("course", "maponly") if sc.get(k)}
    try:
        info = runner.entry_info(con, job["entry_id"])
        track, start_s, cumulative = photo_track(conf, info)
        cid, uid, eid = info["cid"], job["user_id"], info["event_id"]
        kept = con.execute("SELECT * FROM screens WHERE class_id = ? AND user_id = ?", (cid, uid)).fetchone()
        course_p = new.get("course") or (conf.path(kept["course_file"]) if kept else None)
        if "maponly" in new:
            maponly_p = new["maponly"]
        elif "course" in new:
            maponly_p = None                   # a new screenshot with the course alone: the old one without is
        else:                                  # of another view
            maponly_p = conf.path(kept["maponly_file"]) if kept and kept["maponly_file"] else None
        if course_p is None or not os.path.exists(course_p) or (maponly_p and not os.path.exists(maponly_p)):
            raise jobs.Refused(_("Snímek s tratí už tu není; nahraj znovu oba snímky."))
        crop = p.get("crop")
        if crop is None and kept and "course" not in new:
            crop = loads(kept["crop"])         # the same view as before: the map cut out by hand still holds
        try:
            course = _open(course_p)
            maponly = _open(maponly_p) if maponly_p else None
        except (OSError, ValueError, Image.DecompressionBombError) as e:
            raise jobs.Refused(_("Snímek se nepodařilo otevřít jako obrázek (png nebo jpg).")) from e
        lat0, lon0 = georef.track_frame(track)
        ground = georef.ground_course(track, georef.local_frame(lat0, lon0), start_s, cumulative)
        try:
            r = pair.place_pair(course, maponly, ground["controls"], lat0, lon0, crop=crop)
        except pair.PairError as e:
            text = texts.screen_failed(e.code, e.data)
            if e.code == "no_fit":
                # maybe the page of Livelox was taken for the map: kept, so that it can be cut out by hand
                _store(con, conf, cid, uid, course_p, maponly_p, kept, course.size, crop,
                       dict(box=[0, 0, course.size[0], course.size[1]], reliable=False, notes=[], res=None))
                con.commit()
                text += " " + texts.screen_crop()
            raise jobs.Refused(text) from e
        if r["swapped"]:
            course_p, maponly_p = maponly_p, course_p
        f = r["work_fit"]
        said = []
        name = f"{info['event_name']} ({info['class_name']})"
        cls = con.execute("SELECT * FROM classes WHERE id = ?", (cid,)).fetchone()
        before = storage.course_source(conf, cls)
        class_changed = event_changed = False
        if before == "kmz":
            said.append(_("Snímek s tratí usazen podle %(n)s z %(controls)s kontrol (odchylka %(rms).0f m); "
                            "mapa s tratí z KMZ zůstává, je přesnější.", n=f['n'], controls=f['controls'], rms=f['rms']))
        else:
            gm, img = r["course"]
            fd, tmp = tempfile.mkstemp(suffix=".kmz", dir=conf.path("incoming"))
            os.close(fd)
            georef.write_kmz(tmp, img, gm, name=name, png=True)
            rel = storage.save_map(conf, tmp, eid, cid)
            con.execute("UPDATE classes SET course_file = ?, course_by = ?, course_at = datetime('now'),"
                        " course_source = 'screen', course_rms = ?, course_n = ?, course_edge_m = ? WHERE id = ?",
                        (rel, uid, round(f["rms"], 1), f["n"], round(r["edge_m"], 1), cid))
            class_changed = True
            replaced = {"image": _(" Nahradil mapu z obrázku."), "photo": " Nahradil mapu z fotky.",
                        "manual": " Nahradil mapu z fotky.", "screen": _(" Nahradil předchozí snímek.")}.get(before, "")
            said.append(_("Snímek s tratí usazen podle %(n)s z %(controls)s kontrol, odchylka %(rms).0f m.",
                n=f['n'], controls=f['controls'], rms=f['rms'])
                        + replaced)
        if maponly is not None:
            ev = con.execute("SELECT maponly_file, maponly_source FROM events WHERE id = ?", (eid,)).fetchone()
            if ev["maponly_file"] and (ev["maponly_source"] or "kmz") == "kmz":
                said.append(_("Pro závod už je mapa bez tratě z KMZ, která je přesnější; snímek bez tratě se "
                                "nepoužil."))
            elif r["maponly"] is not None:
                gm, img = r["maponly"]
                fd, tmp = tempfile.mkstemp(suffix=".kmz", dir=conf.path("incoming"))
                os.close(fd)
                georef.write_kmz(tmp, img, gm, name=name + _(" bez tratě"), png=True)
                rel = storage.save_map(conf, tmp, eid)
                con.execute("UPDATE events SET maponly_file = ?, maponly_by = ?, maponly_at = datetime('now'),"
                            " maponly_source = 'snimek', maponly_res_m = ?, maponly_acc_m = ? WHERE id = ?",
                            (rel, uid, round(r["out_res"], 2), round(r["accuracy"]), eid))
                event_changed = True
                res = f"{r['out_res']:.1f}".replace(".", ",")
                said.append(_("Mapa bez tratě uložena pro celý závod (%(res)s m na pixel, přesnost asi "
                                "±%(accuracy).0f m).", res=res, accuracy=r['accuracy'])
                            + (_(" Nahradila předchozí snímek.") if ev["maponly_source"] == "snimek" else ""))
        if "shifted" in r["notes"] and r["shift"]:
            said.append(_("Mapa se mezi snímky posunula o %(max)s px, vyrovnal jsem to.",
                max=max(1, round(abs(complex(*r['shift']))))))
        for code in r["notes"]:
            t = texts.screen_note(code, r["res"])
            if t:
                said.append(t)
        # keep both screenshots for later (the one without the course alone, a cut by hand)
        x0, y0, x1, y1 = r["box"]
        _store(con, conf, cid, uid, course_p, maponly_p, kept, course.size, crop,
               dict(box=[x0, y0, x1, y1], reliable=r["reliable"], notes=r["notes"], res=round(r["res"], 3)))
        con.commit()
        if event_changed:
            who = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id WHERE c.event_id = ?",
                              (eid,)).fetchall()
        elif class_changed:
            who = con.execute("SELECT id FROM entries WHERE class_id = ?", (cid,)).fetchall()
        else:
            who = []
        queued = [matching.queue_analysis(con, w["id"]) for w in who]
        if any(q is not None for q in queued):
            said.append(_("Analýza je ve frontě."))
        return " ".join(said)
    finally:
        for path in new.values():
            if os.path.exists(path):
                os.remove(path)
