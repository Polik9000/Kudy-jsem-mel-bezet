"""Crossings that are not allowed, from OpenStreetMap: railways, motorways, fences and walls as lines,
level crossings, bridges and underpasses as the places where crossing is fine.

One Overpass query per map (fetch), the answer is turned into plain lines and points (parse) and the caller
keeps it (the web app stores it per event). Data © OpenStreetMap contributors, ODbL: say so wherever the
lines are shown.

  lines      [{"kind": "forbidden" | "hard", "what": "railway" | "motorway" | "fence", "line": [[lat, lon], ...]}]
             railway and motorway are "forbidden" (the web app can turn them into "hard" per event),
             fences and walls are "hard": ISOM tells apart what must not be crossed from what is merely
             impassable for most runners.
  crossings  [[lat, lon], ...]: level crossings, and where a road or path on a bridge or in a tunnel
             meets a barrier line. A railway or motorway that is itself on a bridge or in a tunnel is
             left out altogether (one can pass under or over it).
"""
import json
import time
import urllib.parse
import urllib.request

OVERPASS = "https://overpass-api.de/api/interpreter"
# a second public Overpass, asked only when the first fails (502 / 504 when it is busy), by the same rules
FALLBACK = "https://overpass.private.coffee/api/interpreter"
AGENT = "OB-tracker (club route analysis; one query per race map)"
RAIL = ("rail", "light_rail", "narrow_gauge")
ROAD = ("motorway", "trunk", "motorway_link", "trunk_link")
FENCE = ("fence", "wall", "city_wall")


def query(south, west, north, east):
    box = f"({south:.6f},{west:.6f},{north:.6f},{east:.6f})"
    return ("[out:json][timeout:40];("
            f'way["railway"~"^({"|".join(RAIL)})$"]{box};'
            f'way["highway"~"^({"|".join(ROAD)})$"]{box};'
            f'way["barrier"~"^({"|".join(FENCE)})$"]{box};'
            f'node["railway"~"^(level_crossing|crossing)$"]{box};'
            f'way["highway"]["bridge"]{box};way["highway"]["tunnel"]{box};'
            ");out body geom;")


def fetch(south, west, north, east, url=None, timeout=60, retries=2, pause=8.0):
    """The Overpass answer (dict) for a box: from OVERPASS, and when it does not answer from FALLBACK (or only from
    `url`). Raises OSError when none answers."""
    data = urllib.parse.urlencode({"data": query(south, west, north, east)}).encode()
    last = None
    for server in ([url] if url else [OVERPASS, FALLBACK]):
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(server, data=data, headers={"User-Agent": AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except (OSError, ValueError) as e:  # busy server (429/502/504), timeout, HTML instead of JSON
                last = e
                if attempt < retries:
                    time.sleep(pause)
    raise OSError(f"Overpass: {last}")


def _yes(tags, key):
    return tags.get(key) not in (None, "", "no")


def _cross(p1, p2, p3, p4):
    """Intersection point of segments p1-p2 and p3-p4 ([lat, lon]) or None."""
    (y1, x1), (y2, x2), (y3, x3), (y4, x4) = p1, p2, p3, p4
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if d == 0:
        return None
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return [y1 + t * (y2 - y1), x1 + t * (x2 - x1)]
    return None


def parse(data, fences=True):
    """Overpass JSON -> dict(lines, crossings) as described at the top."""
    lines, crossings, passages = [], [], []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        if el.get("type") == "node":
            if tags.get("railway") in ("level_crossing", "crossing"):
                crossings.append([round(el["lat"], 6), round(el["lon"], 6)])
            continue
        geom = [[round(p["lat"], 6), round(p["lon"], 6)] for p in el.get("geometry") or []]
        if len(geom) < 2:
            continue
        over_or_under = _yes(tags, "bridge") or _yes(tags, "tunnel")
        if tags.get("railway") in RAIL:
            if not over_or_under:
                lines.append(dict(kind="forbidden", what="railway", line=geom))
        elif tags.get("highway") in ROAD:
            if not over_or_under:
                lines.append(dict(kind="forbidden", what="motorway", line=geom))
        elif tags.get("barrier") in FENCE:
            if fences:
                lines.append(dict(kind="hard", what="fence", line=geom))
        elif "highway" in tags and over_or_under:
            passages.append(geom)
    # a road or path on a bridge or in a tunnel that meets a railway or motorway: a place to cross
    for way in passages:
        for b in lines:
            if b["what"] == "fence":
                continue
            for p1, p2 in zip(way, way[1:]):
                for p3, p4 in zip(b["line"], b["line"][1:]):
                    x = _cross(p1, p2, p3, p4)
                    if x:
                        crossings.append([round(x[0], 6), round(x[1], 6)])
    uniq = []
    for c in crossings:
        if c not in uniq:
            uniq.append(c)
    return dict(lines=lines, crossings=uniq)


def for_box(south, west, north, east, **kw):
    """fetch + parse, with the day it was read."""
    out = parse(fetch(south, west, north, east, **kw))
    out["fetched"] = time.strftime("%Y-%m-%d")
    out["source"] = "© OpenStreetMap contributors, ODbL"
    return out
