"""One race in one file (.obzavod), to hand it to another runner without a server (TODO 49, R39).

The file is a zip:
    obzavod.json      what the race is: event, class, official times of the class, refreshment points, lines not
                      to cross; with "mine", also the runner's own result and settings
    maponly.kmz       the map without the course (when the race has one)
    course.kmz        the map with the course of the class
    course.json       the course read from a placed photo (next to course.kmz, when there is one)
    run.fit           the runner's own track (only when they ticked it)

Loading it into another app adds what that app does not have yet; nothing there is replaced. The analysis of
whoever loads it is computed again on their computer (from their own .fit), nothing computed travels."""
import datetime as dt
import io
import json
import os
import re
import unicodedata
import zipfile

from .. import oris
from ..db import dumps, loads
from . import matching, regnos, storage
from . import splits as class_splits

FORMAT = "obzavod"
VERSION = 1
SUFFIX = ".obzavod"
MAX_MEMBER = 200 * 1024 * 1024      # a KMZ from Livelox has a few to tens of MB
NAMES = {"obzavod.json", "maponly.kmz", "course.kmz", "course.json", "run.fit"}

EVENT_FIELDS = ("oris_id", "name", "date", "place", "discipline", "livelox_id", "lat", "lon", "links", "locations",
                "osm_mode", "hatch_mode", "maponly_source", "maponly_res_m", "maponly_acc_m")
CLASS_FIELDS = ("oris_id", "name", "distance_km", "climb_m", "controls", "control_codes", "course_source",
                "course_rms", "course_n", "course_edge_m")
RESULT_FIELDS = ("official_time_s", "start_local", "result_place", "splits")
NOTE_FIELDS = ("leg_n", "planned", "deliberate_stop", "lost_contact", "green", "fatigue", "text", "corrected",
               "control_desc")
JSON_FIELDS = {"links", "locations", "control_codes", "splits", "planned", "corrected"}


class BadFile(ValueError):
    """The file cannot be loaded; the message is Czech and goes to the page."""


def file_name(e):
    """'2025-05-17-mo-kratka-trat-pohora-h16c.obzavod' from the event name, date and class."""
    text = unicodedata.normalize("NFKD", f"{e['date']} {e['event_name']} {e['class_name']}")
    slug = re.sub(r"[^a-z0-9]+", "-", text.encode("ascii", "ignore").decode().lower()).strip("-")[:80]
    return (slug or "zavod") + SUFFIX


def _row(row, fields):
    out = {}
    for k in fields:
        v = row[k]
        out[k] = loads(v) if k in JSON_FIELDS and isinstance(v, str) else v
    return out


def export(con, conf, entry_id, track=False, mine=False):
    """The .obzavod of one entry as bytes. track: the runner's .fit and their official result go too;
    mine: their own settings of the race and notes of the legs (plans drawn, ticks, texts)."""
    e = con.execute("SELECT e.*, c.event_id FROM entries e JOIN classes c ON c.id = e.class_id WHERE e.id = ?",
                    (entry_id,)).fetchone()
    ev = con.execute("SELECT * FROM events WHERE id = ?", (e["event_id"],)).fetchone()
    cls = con.execute("SELECT * FROM classes WHERE id = ?", (e["class_id"],)).fetchone()
    files = {}
    if ev["maponly_file"] and os.path.exists(conf.path(ev["maponly_file"])):
        files["maponly.kmz"] = conf.path(ev["maponly_file"])
    if cls["course_file"] and os.path.exists(conf.path(cls["course_file"])):
        files["course.kmz"] = conf.path(cls["course_file"])
        if os.path.exists(conf.path(storage.course_json(cls["course_file"]))):
            files["course.json"] = conf.path(storage.course_json(cls["course_file"]))
    doc = dict(
        format=FORMAT, version=VERSION,
        event=_row(ev, EVENT_FIELDS), **{"class": _row(cls, CLASS_FIELDS)},
        class_splits=class_splits.load(con, cls["id"]),
        refreshments=[dict(lat=r["lat"], lon=r["lon"], source=r["source"]) for r in con.execute(
            "SELECT * FROM refreshments WHERE event_id = ? ORDER BY id", (ev["id"],))],
        barriers=[dict(kind=r["kind"], line=loads(r["line"])) for r in con.execute(
            "SELECT * FROM barriers WHERE event_id = ? ORDER BY id", (ev["id"],))])
    if not files.get("maponly.kmz"):
        doc["event"].update(maponly_source=None, maponly_res_m=None, maponly_acc_m=None)
    if not files.get("course.kmz"):
        doc["class"].update(course_source=None, course_rms=None, course_n=None, course_edge_m=None)
    own = {}
    if track:
        own["result"] = _row(e, RESULT_FIELDS)
        act = con.execute("SELECT file FROM activities WHERE id = ?", (e["activity_id"],)).fetchone() \
            if e["activity_id"] else None
        if act and os.path.exists(conf.path(act["file"])):
            files["run.fit"] = conf.path(act["file"])
    if mine:
        own["settings"] = dict(own_osm_mode=e["own_osm_mode"], own_hatch_mode=e["own_hatch_mode"])
        own["leg_notes"] = [_row(r, NOTE_FIELDS) for r in con.execute(
            "SELECT * FROM leg_notes WHERE entry_id = ? ORDER BY leg_n", (entry_id,))]
    if own:
        doc["mine"] = own
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("obzavod.json", json.dumps(doc, ensure_ascii=False, indent=1))
        for name, path in files.items():
            # maps are compressed pictures already
            z.write(path, name, zipfile.ZIP_STORED if name.endswith(".kmz") else zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def _read(data):
    """(doc, {name: bytes}) out of the bytes of a .obzavod, or BadFile."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        infos = z.infolist()
    except (zipfile.BadZipFile, OSError, ValueError) as err:
        raise BadFile("Soubor není závod uložený z aplikace (.obzavod).") from err
    names = {i.filename for i in infos}
    if "obzavod.json" not in names:
        raise BadFile("Soubor není závod uložený z aplikace (.obzavod): chybí v něm popis závodu.")
    if any(i.filename not in NAMES or i.file_size > MAX_MEMBER for i in infos):
        raise BadFile("V souboru je něco, co do uloženého závodu nepatří. Nenačetl jsem ho.")
    try:
        doc = json.loads(z.read("obzavod.json").decode("utf-8"))
        files = {n: z.read(n) for n in names if n != "obzavod.json"}
    except (ValueError, UnicodeDecodeError, zipfile.BadZipFile, OSError) as err:
        raise BadFile("Soubor je poškozený, závod z něj načíst nejde.") from err
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise BadFile("Soubor není závod uložený z aplikace (.obzavod).")
    if not isinstance(doc.get("version"), int) or doc["version"] > VERSION:
        raise BadFile("Závod je uložený novější verzí aplikace. Nainstaluj si novou verzi a načti ho znovu.")
    ev, cls = doc.get("event"), doc.get("class")
    if not isinstance(ev, dict) or not isinstance(cls, dict) or not ev.get("name") or not cls.get("name"):
        raise BadFile("Soubor je poškozený: chybí v něm název závodu nebo kategorie.")
    try:
        dt.date.fromisoformat(str(ev.get("date")))
    except ValueError as err:
        raise BadFile("Soubor je poškozený: datum závodu nejde přečíst.") from err
    return doc, files


def _value(k, v):
    return dumps(v) if k in JSON_FIELDS and v is not None else v


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _event(con, ev, user_id):
    """(events.id, True when it is new): the race the app already has (same ORIS id, or same name and date for a
    race outside ORIS), else a new one."""
    oris_id = ev.get("oris_id") if isinstance(ev.get("oris_id"), int) else None
    if oris_id:
        row = con.execute("SELECT id FROM events WHERE oris_id = ?", (oris_id,)).fetchone()
    else:
        row = con.execute("SELECT id FROM events WHERE oris_id IS NULL AND name = ? AND date = ?",
                          (ev["name"], ev["date"])).fetchone()
    if row:
        have = con.execute("SELECT * FROM events WHERE id = ?", (row["id"],)).fetchone()
        for k in ("place", "discipline", "livelox_id", "lat", "lon", "links", "locations"):
            if have[k] is None and ev.get(k) is not None:
                con.execute(f"UPDATE events SET {k} = ? WHERE id = ?", (_value(k, ev[k]), row["id"]))
        return row["id"], False
    modes = dict(osm_mode=ev.get("osm_mode") if ev.get("osm_mode") in ("forbid", "penalty", "off") else "forbid",
                 hatch_mode=ev.get("hatch_mode") if ev.get("hatch_mode") in ("forbid", "off") else "forbid")
    cur = con.execute(
        "INSERT INTO events (oris_id, name, date, place, discipline, livelox_id, lat, lon, links, locations,"
        " osm_mode, hatch_mode, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (oris_id, str(ev["name"])[:200], str(ev["date"]), ev.get("place"), ev.get("discipline"),
         ev.get("livelox_id"), _num(ev.get("lat")), _num(ev.get("lon")), _value("links", ev.get("links")),
         _value("locations", ev.get("locations")), modes["osm_mode"], modes["hatch_mode"], user_id))
    return cur.lastrowid, True


def _class(con, event_id, cls):
    oris_id = cls.get("oris_id") if isinstance(cls.get("oris_id"), int) else None
    row = None
    if oris_id:
        row = con.execute("SELECT id FROM classes WHERE oris_id = ? AND event_id = ?", (oris_id, event_id)).fetchone()
    row = row or con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ?",
                             (event_id, str(cls["name"])[:40])).fetchone()
    if row is None:
        if oris_id and con.execute("SELECT 1 FROM classes WHERE oris_id = ?", (oris_id,)).fetchone():
            oris_id = None
        row = dict(id=con.execute("INSERT INTO classes (event_id, oris_id, name) VALUES (?,?,?)",
                                  (event_id, oris_id, str(cls["name"])[:40])).lastrowid)
    have = con.execute("SELECT * FROM classes WHERE id = ?", (row["id"],)).fetchone()
    for k in ("distance_km", "climb_m", "controls", "control_codes"):
        if have[k] is None and cls.get(k) is not None:
            con.execute(f"UPDATE classes SET {k} = ? WHERE id = ?", (_value(k, cls[k]), row["id"]))
    return row["id"]


def _maps(con, conf, files, doc, event_id, class_id, user_id):
    """Store the maps the app does not have yet. Returns which went in ('maponly', 'course')."""
    ev, cls = doc["event"], doc["class"]
    added = []
    have_ev = con.execute("SELECT maponly_file FROM events WHERE id = ?", (event_id,)).fetchone()
    have_cls = con.execute("SELECT course_file FROM classes WHERE id = ?", (class_id,)).fetchone()
    for kind, name, have in (("maponly", "maponly.kmz", have_ev["maponly_file"]),
                             ("course", "course.kmz", have_cls["course_file"])):
        if name not in files or have:
            continue
        rel, tmp = storage.incoming(conf, ".kmz")
        with open(tmp, "wb") as f:
            f.write(files[name])
        try:
            storage.check_kmz(tmp)
        except ValueError as err:
            os.remove(tmp)
            raise BadFile(("Mapa bez tratě" if kind == "maponly" else "Mapa s tratí")
                          + " v souboru nejde přečíst. " + str(err)) from err
        if kind == "maponly":
            path = storage.save_map(conf, tmp, event_id)
            src = ev.get("maponly_source") if ev.get("maponly_source") in ("kmz", "snimek") else "kmz"
            con.execute("UPDATE events SET maponly_file = ?, maponly_by = ?, maponly_at = datetime('now'),"
                        " maponly_source = ?, maponly_res_m = ?, maponly_acc_m = ? WHERE id = ?",
                        (path, user_id, src, _num(ev.get("maponly_res_m")), _num(ev.get("maponly_acc_m")), event_id))
        else:
            path = storage.save_map(conf, tmp, event_id, class_id)
            src = cls.get("course_source") if cls.get("course_source") in (
                "kmz", "image", "photo", "manual", "screen") else "kmz"
            if "course.json" in files:
                with open(conf.path(storage.course_json(path)), "wb") as f:
                    f.write(files["course.json"])
            con.execute("UPDATE classes SET course_file = ?, course_by = ?, course_at = datetime('now'),"
                        " course_source = ?, course_rms = ?, course_n = ?, course_edge_m = ? WHERE id = ?",
                        (path, user_id, src, _num(cls.get("course_rms")),
                         int(cls["course_n"]) if isinstance(cls.get("course_n"), int) else None,
                         _num(cls.get("course_edge_m")), class_id))
        added.append(kind)
    return added


def _extras(con, doc, event_id, class_id, user_id):
    """Official times of the class, refreshment points and lines not to cross that the app does not have yet."""
    data = doc.get("class_splits")
    if isinstance(data, dict) and isinstance(data.get("runners"), list) and class_splits.load(con, class_id) is None:
        con.execute("INSERT INTO class_splits (class_id, data) VALUES (?, ?)", (class_id, dumps(data)))
    have = {(round(r["lat"], 6), round(r["lon"], 6))
            for r in con.execute("SELECT lat, lon FROM refreshments WHERE event_id = ?", (event_id,))}
    for r in doc.get("refreshments") or []:
        lat, lon = _num(r.get("lat")), _num(r.get("lon"))
        if lat is None or lon is None or (round(lat, 6), round(lon, 6)) in have:
            continue
        con.execute("INSERT INTO refreshments (event_id, lat, lon, source, created_by) VALUES (?,?,?,?,?)",
                    (event_id, lat, lon, r.get("source") if r.get("source") in ("manual", "detected") else "manual",
                     user_id))
    lines = {r["line"] for r in con.execute("SELECT line FROM barriers WHERE event_id = ?", (event_id,))}
    for b in doc.get("barriers") or []:
        line = b.get("line")
        if not isinstance(line, list) or len(line) < 2 or dumps(line) in lines:
            continue
        con.execute("INSERT INTO barriers (event_id, kind, line, created_by) VALUES (?,?,?,?)",
                    (event_id, b.get("kind") if b.get("kind") in ("forbidden", "hard") else "forbidden",
                     dumps(line), user_id))


def _my_times(con, class_id, regnos):
    """The runner's own official result from the stored times of the class (no ORIS call), or None."""
    data = class_splits.load(con, class_id)
    mine = oris.numbers(regnos)
    me = next((r for r in (data or {}).get("runners", []) if (r.get("regno") or "").upper() in mine), None)
    if me is None:
        return None
    return dict(official_time_s=me["time_s"], start_local=me["start_local"], result_place=me["place"],
                splits=dumps(me["cum"][:-1] + [me["time_s"]]) if me["time_s"] is not None else None)


def load(con, conf, user, data):
    """Add the race of a .obzavod (bytes) to the runner's races. Returns (entry id, Czech message)."""
    doc, files = _read(data)
    uid = user["id"]
    try:
        event_id, _ = _event(con, doc["event"], uid)
        class_id = _class(con, event_id, doc["class"])
        added = _maps(con, conf, files, doc, event_id, class_id, uid)
        _extras(con, doc, event_id, class_id, uid)
        have = con.execute("SELECT e.id, c.name FROM entries e JOIN classes c ON c.id = e.class_id"
                           " WHERE e.user_id = ? AND c.event_id = ? ORDER BY e.id LIMIT 1", (uid, event_id)).fetchone()
        mine = doc.get("mine") if isinstance(doc.get("mine"), dict) else {}
        if have:
            entry_id, new_entry = have["id"], False
        else:
            entry_id = con.execute("INSERT INTO entries (user_id, class_id, class_chosen) VALUES (?, ?, 1)",
                                   (uid, class_id)).lastrowid
            new_entry = True
            res = _my_times(con, class_id, regnos.of(con, uid))
            if res is None and isinstance(mine.get("result"), dict):
                r = mine["result"]
                res = dict(official_time_s=r.get("official_time_s") if isinstance(r.get("official_time_s"), int)
                           else None, start_local=r.get("start_local"), result_place=r.get("result_place"),
                           splits=_value("splits", r.get("splits")) if isinstance(r.get("splits"), list) else None)
            if res:
                con.execute("UPDATE entries SET official_time_s = ?, start_local = ?, result_place = ?, splits = ?"
                            " WHERE id = ?", (res["official_time_s"], res["start_local"], res["result_place"],
                                              res["splits"], entry_id))
        if isinstance(mine.get("settings"), dict):
            s = mine["settings"]
            con.execute("UPDATE entries SET own_osm_mode = ?, own_hatch_mode = ? WHERE id = ?",
                        (s.get("own_osm_mode") if s.get("own_osm_mode") in ("forbid", "penalty", "off") else None,
                         s.get("own_hatch_mode") if s.get("own_hatch_mode") in ("forbid", "off") else None, entry_id))
        for n in mine.get("leg_notes") or []:
            if not isinstance(n, dict) or not isinstance(n.get("leg_n"), int):
                continue
            con.execute("INSERT OR IGNORE INTO leg_notes (entry_id, leg_n, planned, deliberate_stop, lost_contact,"
                        " green, fatigue, text, corrected, control_desc) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (entry_id, n["leg_n"], _value("planned", n.get("planned")), 1 if n.get("deliberate_stop") else 0,
                         1 if n.get("lost_contact") else 0, n.get("green") if n.get("green") in ("through", "around")
                         else None, n.get("fatigue") if n.get("fatigue") in (1, 2, 3, 4, 5) else None,
                         n.get("text"), _value("corrected", n.get("corrected")), n.get("control_desc")))
        con.commit()
    except Exception:
        con.rollback()
        raise
    run = None
    if "run.fit" in files:
        run = storage.save_activity(con, conf, uid, files["run.fit"], "run.fit", "fit")[0]
        if run is not None and not con.execute("SELECT activity_id FROM entries WHERE id = ?",
                                                (entry_id,)).fetchone()["activity_id"]:
            con.execute("UPDATE entries SET activity_id = ?, match_confidence = 'manual', match_note = NULL"
                        " WHERE id = ?", (run, entry_id))
            con.commit()
    if new_entry and run is None:
        matching.match_user(con, uid, queue=False)
    # the maps that came in serve every runner of the race in this app, so their analysis is due again
    again = {entry_id}
    if "maponly" in added:
        again.update(r["id"] for r in con.execute(
            "SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id WHERE c.event_id = ?", (event_id,)))
    if "course" in added:
        again.update(r["id"] for r in con.execute("SELECT id FROM entries WHERE class_id = ?", (class_id,)))
    queued = [i for i in sorted(again) if matching.queue_analysis(con, i) is not None]
    parts = ["Závod je načtený." if new_entry else f"Závod už máš (kategorie {have['name']}), doplnil jsem, co chybělo."]
    if added:
        parts.append("Mapy: " + " a ".join({"maponly": "bez tratě", "course": "s tratí"}[k] for k in added) + ".")
    if run is not None:
        parts.append("Běh ze souboru je spárovaný se závodem.")
    if entry_id in queued:
        parts.append("Analýza se spustila.")
    elif not con.execute("SELECT activity_id FROM entries WHERE id = ?", (entry_id,)).fetchone()["activity_id"]:
        parts.append("Nahraj k němu svůj běh z hodinek (.fit).")
    return entry_id, " ".join(parts)

