"""Files in the instance folder: .fit activities and KMZ maps. Names are ours, never the uploaded ones."""
import datetime as dt
import hashlib
import json
import os
import secrets

from oroute import garmin
from oroute.kmzmap import GeoMap

from ..i18n import N_, _

# sports worth keeping from a whole Garmin export (an orienteering race is recorded as one of these)
KEEP_SPORTS = {"running", "walking", "hiking", "generic", "None", "fitness_equipment", "training"}


def incoming(conf, suffix):
    """A fresh path for an upload that the worker will pick up."""
    os.makedirs(conf.path("incoming"), exist_ok=True)
    rel = os.path.join("incoming", secrets.token_hex(12) + suffix)
    return rel, conf.path(rel)


def save_activity(con, conf, user_id, data, original_name, source):
    """Store one .fit (bytes) if it is an activity with a start time. Returns (activity id, True if new)
    or (None, False) for anything else (settings, monitoring files, broken files...)."""
    info = garmin.scan_fit(data)
    if info.get("type") != "activity" or info.get("error") or info.get("start") is None:
        return None, False
    if source == "garmin-export" and info.get("sport") not in KEEP_SPORTS:
        return None, False
    sha1 = hashlib.sha1(data).hexdigest()
    row = con.execute("SELECT id FROM activities WHERE user_id = ? AND sha1 = ?", (user_id, sha1)).fetchone()
    if row:
        return row["id"], False
    rel = os.path.join("fit", f"user_{user_id}", sha1 + ".fit")
    os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
    with open(conf.path(rel), "wb") as f:
        f.write(data)
    gps = info.get("first_gps")
    cur = con.execute(
        "INSERT INTO activities (user_id, sha1, file, original_name, source, start_utc, sport, sub_sport, timer_s,"
        " elapsed_s, dist_m, lat, lon, has_gps) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, sha1, rel, os.path.basename(original_name or "")[:200], source,
         garmin.local(info["start"]).astimezone(dt.timezone.utc).isoformat(), info.get("sport"),
         info.get("sub_sport"), info.get("timer"), info.get("elapsed"), info.get("dist"),
         gps[0] if gps else None, gps[1] if gps else None, 1 if gps else 0))
    con.commit()
    return cur.lastrowid, True


def drop_activity(con, conf, activity_id):
    """Delete one activity: its file and its row (not committed)."""
    row = con.execute("SELECT file FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if row is None:
        return
    try:
        os.remove(conf.path(row["file"]))
    except OSError:
        pass
    con.execute("DELETE FROM activities WHERE id = ?", (activity_id,))


def drop_unpaired(con, conf, user_id, source, keep=()):
    """Delete the runner's activities of one source that are not paired with any race (file and row), except
    the ones in `keep` (ids: unpaired runs recorded at a race, see matching.at_races).
    Returns (paired and kept, unpaired and kept, dropped)."""
    rows = con.execute(
        "SELECT a.id, EXISTS (SELECT 1 FROM entries e WHERE e.activity_id = a.id) AS paired"
        " FROM activities a WHERE a.user_id = ? AND a.source = ?", (user_id, source)).fetchall()
    paired = sum(r["paired"] for r in rows)
    spared = dropped = 0
    for r in rows:
        if r["paired"]:
            continue
        if r["id"] in keep:
            spared += 1
            continue
        drop_activity(con, conf, r["id"])
        dropped += 1
    con.commit()
    return paired, spared, dropped


def check_kmz(path):
    """The map of a KMZ, or ValueError with a message for the user (Czech)."""
    try:
        gm = GeoMap.from_kmz(path)
    except Exception as e:
        raise ValueError(_("Soubor není KMZ s mapou (export z Livelox: Share → Export → Google Earth KMZ).")) from e
    if None in (gm.n, gm.s, gm.e, gm.w) or gm.W < 200 or gm.H < 200:
        raise ValueError(_("V KMZ chybí umístění mapy (LatLonBox) nebo je obrázek příliš malý."))
    return gm


IMAGE_EXT = (".jpg", ".jpeg", ".png")
# iPhone photos: Pillow cannot read them without another library; the form takes them only to say what to do
HEIC_EXT = (".heic", ".heif")
HEIC_TEXT = (N_("Fotka je ve formátu HEIC. Ulož ji jako JPEG (v iPhonu Nastavení → Fotoaparát → Formáty → "
                 "Nejkompatibilnější), nebo ji nahraj přes prohlížeč, který ji převede."))


def check_image(path):
    """ValueError with a message for the user (Czech) when the file is not a usable picture of a map."""
    from PIL import Image
    with open(path, "rb") as f:
        head = f.read(16)
    if head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"heim", b"heis", b"hevc"):
        raise ValueError(_(HEIC_TEXT))          # a HEIC photo renamed to .jpg
    try:
        with Image.open(path) as im:
            w, h = im.size
            im.verify()
    except Image.DecompressionBombError as e:
        raise ValueError(_("Obrázek je příliš velký (nejvýš 120 megapixelů).")) from e
    except Exception as e:
        raise ValueError(_("Soubor není obrázek (jpg nebo png).")) from e
    if min(w, h) < 400:
        raise ValueError(_("Obrázek je příliš malý, kontroly by na něm nešly najít (aspoň 400 px na kratší "
                             "straně)."))
    if w * h > 120_000_000:
        raise ValueError(_("Obrázek je příliš velký (nejvýš 120 megapixelů)."))


def course_json(rel):
    """Where the course read from the placing of a photo lies next to its KMZ (analyze.py --course)."""
    return rel + ".course.json"


def course_source(conf, row):
    """Where the map with the course of a class came from: kmz | image | photo | manual, None without one.
    row: has course_file and course_source. A map stored before the column existed is a KMZ, unless it is a
    placed picture (those have no title bar: header_px 0)."""
    if not row["course_file"]:
        return None
    if row["course_source"]:
        return row["course_source"]
    try:
        return "image" if map_meta(conf, row["course_file"])["header_px"] == 0 else "kmz"
    except (OSError, ValueError, KeyError):
        return "kmz"


def save_photo(con, conf, entry_id, image, waiting_for_run=False):
    """Keep the photo of an entry (upright, already made smaller) for placing it by hand; replaces the one before
    and the points clicked on it. waiting_for_run marks a photo uploaded before its FIT/ORIS splits."""
    rel = os.path.join("photos", f"entry_{entry_id}.jpg")
    os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
    tmp = conf.path(rel) + f".{secrets.token_hex(4)}.tmp"
    from PIL import Image
    exif = Image.Exif()
    if image.info.get("focal35"):                # the camera's focal length: the sheet's proportions need it
        exif.get_ifd(0x8769)[0xA405] = int(round(image.info["focal35"]))
    image.convert("RGB").save(tmp, "JPEG", quality=92, exif=exif.tobytes())
    os.replace(tmp, conf.path(rel))
    con.execute("INSERT INTO photos (entry_id, file, waiting_for_run) VALUES (?, ?, ?)"
                " ON CONFLICT (entry_id) DO UPDATE SET file = excluded.file, points = NULL,"
                " waiting_for_run = excluded.waiting_for_run, uploaded_at = datetime('now')",
                (entry_id, rel, int(waiting_for_run)))
    con.commit()
    return rel


def drop_photos(con, conf, class_id):
    """A KMZ replaced the photo of a class: the photos kept for placing by hand go (files and rows), and so
    does the course read from the placing. Not committed."""
    for r in con.execute("SELECT p.entry_id, p.file FROM photos p JOIN entries e ON e.id = p.entry_id"
                         " WHERE e.class_id = ?", (class_id,)).fetchall():
        try:
            os.remove(conf.path(r["file"]))
        except OSError:
            pass
        con.execute("DELETE FROM photos WHERE entry_id = ?", (r["entry_id"],))


def save_map(conf, tmp_path, event_id, class_id=None):
    """Move a checked KMZ to its place: the map without course belongs to the event (shared by everyone
    who ran it), the map with the course to one class. Returns the relative path."""
    name = "maponly.kmz" if class_id is None else f"course_class_{class_id}.kmz"
    rel = os.path.join("maps", f"event_{event_id}", name)
    os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
    os.replace(tmp_path, conf.path(rel))
    # a map moved by hand before (services/mapfix.py): the new upload replaces it, its original goes too
    if os.path.exists(conf.path(rel)[:-4] + "_puvodni.kmz"):
        os.remove(conf.path(rel)[:-4] + "_puvodni.kmz")
    record = conf.path("manual", f"event_{event_id}.json")
    try:
        with open(record, encoding="utf-8") as f:
            moved = json.load(f)
        moved["files"] = [r for r in moved["files"] if r != rel]
        if moved["files"]:
            with open(record, "w", encoding="utf-8") as f:
                json.dump(moved, f)
        else:
            os.remove(record)
    except (OSError, ValueError, KeyError):
        pass
    if class_id is not None and os.path.exists(conf.path(course_json(rel))):
        os.remove(conf.path(course_json(rel)))     # of a photo placed before; the caller writes a new one
    map_meta(conf, rel)
    return rel


def map_meta(conf, rel):
    """What the race page needs to lay a stored KMZ over its map: corners ([top-left, top-right, bottom-left]
    as [lat, lon]), header_px (the bar at the top of the picture to hide) and stamp, which changes with every
    upload. Finding the corners decodes the whole picture, so it is done once per upload and kept in a small
    file next to the KMZ (a map stored before that file existed gets it on the first request)."""
    path = conf.path(rel)
    st = os.stat(path)
    stamp = [st.st_size, st.st_mtime_ns]
    try:
        with open(path + ".json", encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("stamp") == stamp:
            return meta
    except (OSError, ValueError):
        pass
    gm = GeoMap.from_kmz(path)
    pts = [gm.px_to_latlon(u, v) for u, v in ((0, 0), (gm.W, 0), (0, gm.H))]
    meta = dict(stamp=stamp, corners=[[float(la), float(lo)] for la, lo in pts], header_px=gm.header_px)
    tmp = f"{path}.json.{secrets.token_hex(4)}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f)
    os.replace(tmp, path + ".json")
    return meta
