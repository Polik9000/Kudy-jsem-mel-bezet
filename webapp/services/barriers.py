"""Crossings that are not allowed at an event: lines drawn by hand (table `barriers`) and railways, motorways
and fences from OpenStreetMap (cached per event in the instance folder by the worker, see oroute/osm.py).
Both are shared by everyone who ran the event. Areas that must not be entered are read from the purple
hatching of the map with the course (oroute/hatch.py), so they are kept per class, like that map.
bestroute.py gets all of it as one JSON file (--barriers).

Whether the OpenStreetMap lines and the hatched areas are used is a setting of each runner (entries.own_*),
with the value of the race (events.osm_mode, hatch_mode) for those who did not choose: one runner's choice
never recalculates another runner's routes. A line drawn by hand is shared on purpose; it says who drew it
and only they may delete it."""
import json
import math
import os

from ..db import loads
from . import jobs

MODES = ("forbid", "penalty", "off")
HATCH_MODES = ("forbid", "off")
# what a runner may turn an obstacle read from the map into (table barrier_overrides): remove = not an obstacle
OVERRIDES = dict(fence=("remove", "hard", "tall"), enclosure=("remove", "fence"), osm=("remove", "hard"),
                 hatch=("remove",))
MATCH_M = 15.0      # a correction belongs to the obstacle whose centre lies this close to its key
MAX_OVERRIDES = 300


def _length_m(line):
    k = 111195.0
    return sum(math.hypot((b[0] - a[0]) * k, (b[1] - a[1]) * k * math.cos(math.radians(a[0])))
               for a, b in zip(line, line[1:]))


def manual(con, event_id, user_id=None):
    """The lines drawn by hand at the event. by: who drew it; mine: user_id may delete it (their own line, or
    one whose author's account is gone)."""
    out = []
    for r in con.execute("SELECT b.*, COALESCE(u.name, u.username) AS who FROM barriers b LEFT JOIN users u"
                         " ON u.id = b.created_by WHERE b.event_id = ? ORDER BY b.id", (event_id,)):
        line = loads(r["line"], [])
        out.append(dict(id=r["id"], kind=r["kind"], line=line, length_m=_length_m(line), by=r["who"],
                        mine=r["created_by"] in (None, user_id)))
    return out


def osm_path(conf, event_id):
    return conf.path("osm", f"event_{event_id}.json")


def osm_data(conf, event_id):
    """What was fetched from OpenStreetMap for the event (dict with lines, crossings, fetched) or None."""
    try:
        with open(osm_path(conf, event_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _osm_lines(conf, osm):
    """The OSM lines that are used: railways and motorways always, fences and walls only with OB_OSM_FENCES=1.
    Fences are off by default because nothing here shows they help: OpenStreetMap maps them unevenly (many
    around gardens, few in the forest) and a fence that is not there would send routes on detours."""
    return [l for l in osm.get("lines", []) if conf.osm_fences or l.get("what") != "fence"]


def for_map(con, conf, event_id, mode, user_id=None):
    """(manual lines, OSM lines and crossings or None) as the map page draws them for user_id."""
    osm = osm_data(conf, event_id) if mode != "off" else None
    if osm:
        osm = dict(lines=_osm_lines(conf, osm), crossings=osm.get("crossings", []))
    return [dict(id=b["id"], kind=b["kind"], line=b["line"], by=b["by"], mine=b["mine"])
            for b in manual(con, event_id, user_id)], osm


def hatch_path(conf, class_id):
    return conf.path("hatch", f"class_{class_id}.json")


def _stamp(course):
    """What tells one upload of the map with the course from the next."""
    st = os.stat(course)
    return [st.st_size, int(st.st_mtime)]


def hatch_data(conf, class_id, course=None):
    """What was read from the hatching of the class's map with the course (dict with areas, read) or None.
    With `course` (the path of that map) a reading of an older upload does not count."""
    try:
        with open(hatch_path(conf, class_id), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    return None if course and d.get("source") != _stamp(course) else d


def save_hatch(conf, class_id, course, areas, read):
    os.makedirs(os.path.dirname(hatch_path(conf, class_id)), exist_ok=True)
    with open(hatch_path(conf, class_id), "w", encoding="utf-8") as f:
        json.dump(dict(areas=areas, source=_stamp(course), read=read), f)


def hatch_areas(conf, class_id, mode):
    """The out-of-bounds areas the map page draws and the routes keep out of: [[[lat, lon], ...], ...]."""
    d = hatch_data(conf, class_id) if mode != "off" else None
    return d["areas"] if d else []


def key_of(lat, lon):
    return f"{lat:.5f},{lon:.5f}"


def _latlon(key):
    la, lo = key.split(",")
    return float(la), float(lo)


def center(points):
    """The centre of a line (its middle point) or of a ring of an area (the mean of its points): [lat, lon]."""
    if len(points) > 2 and points[0] == points[-1]:
        points = points[:-1]
        return [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]
    return list(points[len(points) // 2])


def _apart_m(a, b):
    return math.hypot((a[0] - b[0]) * 111195.0, (a[1] - b[1]) * 111195.0 * math.cos(math.radians(a[0])))


def overrides(con, entry_id):
    """The corrections of the runner for the obstacles read from the map: [dict(kind, key, lat, lon, action)]."""
    out = []
    for r in con.execute("SELECT kind, key, action FROM barrier_overrides WHERE entry_id = ? ORDER BY rowid",
                         (entry_id,)):
        la, lo = _latlon(r["key"])
        out.append(dict(kind=r["kind"], key=r["key"], lat=la, lon=lo, action=r["action"]))
    return out


def _action(fixes, kind, c):
    """What the runner made of the obstacle of this kind with its centre c = [lat, lon], or None."""
    best, at = None, MATCH_M
    for o in fixes or []:
        d = _apart_m(c, (o["lat"], o["lon"]))
        if o["kind"] == kind and d <= at:
            best, at = o["action"], d
    return best


def set_override(con, entry_id, kind, key, action):
    """Remember a correction (action None: take it back). Raises ValueError for what is not allowed."""
    if kind not in OVERRIDES or (action is not None and action not in OVERRIDES[kind]):
        raise ValueError("kind or action")
    _latlon(key)
    if action is None:
        con.execute("DELETE FROM barrier_overrides WHERE entry_id = ? AND kind = ? AND key = ?", (entry_id, kind, key))
        return
    if con.execute("SELECT COUNT(*) FROM barrier_overrides WHERE entry_id = ?", (entry_id,)).fetchone()[0] >= MAX_OVERRIDES:
        raise ValueError("too many")
    con.execute("INSERT INTO barrier_overrides (entry_id, kind, key, action) VALUES (?,?,?,?)"
                " ON CONFLICT (entry_id, kind, key) DO UPDATE SET action = excluded.action", (entry_id, kind, key, action))


def recognised(summary_obstacles, osm, areas, fixes):
    """Everything the routes of the runner keep out of or cross slowly that was not drawn by hand, as the map page
    shows it and lets it be corrected: [dict(kind, key, line, what, tall, area, action)]. summary_obstacles: what
    the map was read to have (bestroute.py, best.json); osm: the OSM lines in use; areas: the hatched areas.
    action: what the runner made of it (None: left as it was read)."""
    out = []
    for o in summary_obstacles or []:
        c = [o["lat"], o["lon"]]
        out.append(dict(kind=o["kind"], key=key_of(*c), line=o["line"], what=o["kind"], tall=bool(o.get("tall")),
                        area=o.get("area"), action=_action(fixes, o["kind"], c)))
    for l in osm or []:
        c = center(l["line"])
        out.append(dict(kind="osm", key=key_of(*c), line=l["line"], what=l.get("what"), tall=l.get("kind") == "hard",
                        area=None, action=_action(fixes, "osm", c)))
    for a in areas or []:
        c = center(a)
        out.append(dict(kind="hatch", key=key_of(*c), line=a, what="hatch", tall=False, area=None,
                        action=_action(fixes, "hatch", c)))
    return out


def obstacles_view(con, conf, e, summary):
    """The obstacles the page shows on the layer "Rozpoznané překážky" for entry e (a row of views.races.ENTRY_SQL) and
    the OSM lines and hatched areas it draws as forbidden (the ones the runner took off are not):
    (obstacles, osm or None, areas). summary: the summary of the analysis."""
    fixes = overrides(con, e["id"])
    _, osm = for_map(con, conf, e["event_id"], e["osm_mode"], e["user_id"])
    areas = hatch_areas(conf, e["class_id"], e["hatch_mode"])
    found = recognised((summary or {}).get("obstacles"), osm["lines"] if osm else [], areas, fixes)
    gone = {(o["kind"], o["key"]) for o in found if o["action"] == "remove"}
    if osm:
        osm = dict(osm, lines=[l for l in osm["lines"] if ("osm", key_of(*center(l["line"]))) not in gone])
    return found, osm, [a for a in areas if ("hatch", key_of(*center(a))) not in gone]


def for_routing(con, conf, event_id, mode, areas=None, fixes=None):
    """The dict bestroute.py takes with --barriers, or None when there is nothing to forbid.
    OSM lines are 'forbidden' in mode forbid and 'hard' (very slow) in mode penalty; fences and walls from OSM
    (only with OB_OSM_FENCES=1) are always 'hard' (ISOM: impassable is not the same as forbidden).
    areas: the hatched out-of-bounds areas of the runner's map (hatch_areas).
    fixes: the runner's corrections (overrides): an OSM line or an area they took off is left out, an OSM line they
    made "hard" is slow to cross instead of forbidden; the ones for what is read from the picture of the map go on
    in the file for bestroute.py (mapdata.overrides)."""
    lines = [dict(kind=b["kind"], line=b["line"], source="manual") for b in manual(con, event_id)]
    crossings = []
    osm = osm_data(conf, event_id) if mode != "off" else None
    if osm:
        for l in _osm_lines(conf, osm):
            act = _action(fixes, "osm", center(l["line"]))
            if act == "remove":
                continue
            kind = "hard" if mode == "penalty" or l.get("kind") == "hard" or act == "hard" else "forbidden"
            lines.append(dict(kind=kind, line=l["line"], source="osm", what=l.get("what")))
        crossings = osm.get("crossings", [])
    areas = [a for a in areas or [] if _action(fixes, "hatch", center(a)) != "remove"]
    picture = [dict(kind=o["kind"], lat=o["lat"], lon=o["lon"], action=o["action"]) for o in fixes or []
               if o["kind"] in ("fence", "enclosure")]
    if not (lines or areas or picture):
        return None
    return dict(lines=lines, crossings=crossings, areas=areas, **(dict(overrides=picture) if picture else {}))


def requeue_event(con, event_id, following=()):
    """The barriers changed: draw the best routes again for everyone at the event who has them.
    following: names of settings of the race that changed (osm_mode, hatch_mode); then only for the runners
    who follow the race in one of them, not for those with a setting of their own."""
    assert all(k in ("osm_mode", "hatch_mode") for k in following)
    own = " AND (" + " OR ".join(f"e.own_{k} IS NULL" for k in following) + ")" if following else ""
    n = 0
    for r in con.execute(
            "SELECT e.id, e.user_id FROM entries e JOIN classes c ON c.id = e.class_id JOIN analyses a ON a.entry_id = e.id"
            f" WHERE c.event_id = ? AND a.has_routes = 1{own}", (event_id,)).fetchall():
        n += requeue_entry(con, r["id"], r["user_id"])
    return n


def requeue_entry(con, entry_id, user_id):
    """Draw the best routes of one entry again (its track and splits stay as they are). Returns 1."""
    jobs.enqueue(con, "analyse", user_id=user_id, entry_id=entry_id, payload=dict(refit=False, routes_only=True))
    return 1


def save_osm(conf, event_id, data):
    path = osm_path(conf, event_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(f"{path}.{os.getpid()}.tmp", "w", encoding="utf-8") as f:      # whole or not at all
        json.dump(data, f, ensure_ascii=False)
    os.replace(f"{path}.{os.getpid()}.tmp", path)
