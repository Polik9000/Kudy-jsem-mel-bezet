"""The terrain and the elevation of a map without course, read the same way by every script that needs them
(bestroute.py, oroute/planned.py, oroute/relocate.py): what one of them priced a route on, the others see too.
"""
import hashlib
import json
import os
import zipfile

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.ndimage import label as ndi_label

from . import terrain as T
from .dem import TerrariumDEM, load_dem
from .errors import InputError

OUTLINE_M = 2.5      # a black line this close to an out-of-bounds area is the outline of that area
OUTLINE_WIDE_M = 4.0  # ... and so is the black joined to it up to this far on
WALL_OPEN_M = 4.0     # an impassable wall of a sprint map is open this close around a control of the course
MATCH_M = 15.0        # an override belongs to the recognised obstacle whose centre lies this close to its own
PEN_IN_M = 5.0        # fenced ground opens for a control in it or this close to it, as before (decision of q22);
                      # only that ground, not one beside it within the same distance


def terrain(gm, kmz, cache=None):
    """Terrain class of every pixel of the map (terrain.classify). cache: a file that keeps the result for
    the next run; the map is read again when the KMZ or oroute/terrain.py has changed."""
    rgb = np.asarray(gm.image)
    key = None
    if cache:
        st = os.stat(kmz)
        with open(T.__file__, "rb") as f:
            key = (f"{hashlib.sha1(f.read()).hexdigest()}/{st.st_size}/{st.st_mtime_ns}/{gm.header_px}"
                   f"/{getattr(gm, 'blur_m', 0.0)}")
        try:
            with np.load(cache) as z:
                if str(z["key"]) == key and z["cls"].shape == rgb.shape[:2]:
                    return z["cls"]
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            pass
    cls = T.classify(rgb, gm.header_px, gm.m_per_px_x, blur_m=getattr(gm, "blur_m", 0.0))
    if cache:
        os.makedirs(os.path.dirname(os.path.abspath(cache)), exist_ok=True)
        tmp = f"{cache}.{os.getpid()}.npz"
        np.savez_compressed(tmp, cls=cls, key=key)
        os.replace(tmp, cache)
    return cls


def _pick(overrides, kind, u, v, mpp):
    """The action of the person's override (dict(kind, u, v, action), map pixels) for the obstacle of this kind
    with its centre at (u, v): the nearest one within MATCH_M, or None."""
    best, at = None, (MATCH_M / mpp) ** 2
    for o in overrides or []:
        d = (o["u"] - u) ** 2 + (o["v"] - v) ** 2
        if o["kind"] == kind and d <= at:
            best, at = o["action"], d
    return best


def _hull(us, vs, step):
    """The outline of a set of pixels as a polygon [(u, v)] (convex hull; for showing an enclosure on a map)."""
    pts = np.c_[us, vs][::step].astype(float)
    try:
        from scipy.spatial import ConvexHull
        return [tuple(map(float, pts[i])) for i in ConvexHull(pts).vertices]
    except Exception:  # fewer than three points or all on a line
        return [tuple(map(float, p)) for p in pts[:2]]


def _pen_element(pen, sl, part, action):
    vs, us = np.nonzero(part)
    return dict(kind="enclosure", u=float(pen[0]), v=float(pen[1]), tall=False, action=action, area=float(pen[2]),
                line=_hull(us + sl[1].start, vs + sl[0].start, max(1, len(us) // 400)))


def obstacles(gm, cls, box=None, open_at=None, overrides=None):
    """What the picture of the map shows that a route cannot go through or can hardly cross, read in one
    place for everything that finds or prices a route (bestroute.py, oroute/planned.py, oroute/relocate.py,
    tools/kontrola.py), so that all of them see the same:

      cls      the terrain classes to route and price on
      blocked  what is impassable: the ground fences close in, with the fence (relocate.enclosures)
      hard     the fences that close nothing in (relocate.fences), as a mask: hard to cross, and no path
      fenced   fenced ground with what is drawn along its fence (wider than blocked: for reading features)
      pens     [(u, v, area in m2)] of the enclosures
      walls    the impassable walls of a sprint map (terrain.sprint_walls; buildings in cls already)
      climb    its passable walls: slow to climb over (routing.CLIMB_CROSS_S), and no path
      sprint   whether the map is a sprint map (terrain.sprint_greys: it has grey buildings)

    box = (u0, v0, u1, v1) in map pixels: read only that part of the map (seconds instead of a minute on a
    large map); everything is still given for the whole map, with nothing found outside the box.
    open_at = [(u, v)]: the controls of the course. Fenced ground with a control in it can be entered (nobody
    sets a control where one must not go: the fence has a gate, or the ground was read as fenced by mistake,
    as the yards between the houses of a sprint map are): it is taken out of blocked, fenced and pens.
    overrides = [dict(kind, u, v, action)] (map pixels): what a person corrected by hand, as a recognised obstacle
    is told by its kind and its centre (within MATCH_M, so that it survives a new reading of the map). kind "fence":
    action "remove" (no obstacle), "hard" (a fence to climb, if it was an impassable one) or "tall" (impassable);
    kind "enclosure": "remove" or "fence" (not closed in, but its outline is a fence to climb).
    elements = [dict(kind, u, v, line, tall?, action)] is what was recognised, for the person to see on a map.
    The recognising itself lives in oroute/relocate.py."""
    from . import relocate  # here, not at the top: relocate imports this module
    if box is not None:
        u0, v0, u1, v1 = box
        cut = (slice(max(v0, 0), min(v1, gm.H)), slice(max(u0, 0), min(u1, gm.W)))
        du, dv = cut[1].start, cut[0].start
        part = obstacles(_Cut(gm, cut), cls[cut], open_at=[(u - du, v - dv) for u, v in open_at or []],
                         overrides=[dict(o, u=o["u"] - du, v=o["v"] - dv) for o in overrides or []])
        out = dict(cls=cls.copy(), pens=[(u + du, v + dv, a) for u, v, a in part["pens"]],
                   fences=[[(u + du, v + dv) for u, v in line] for line in part["fences"]],
                   elements=[dict(e, u=e["u"] + du, v=e["v"] + dv, line=[(u + du, v + dv) for u, v in e["line"]])
                             for e in part["elements"]])
        out["cls"][cut] = part["cls"]
        out["sprint"] = part["sprint"]
        for k in ("blocked", "hard", "fenced", "outline", "walls", "climb"):
            out[k] = np.zeros(cls.shape, bool)
            out[k][cut] = part[k]
        return out
    rgb = np.asarray(gm.image)
    # the fences first: where two of them end a gate apart, the ground they close in is fenced all the same
    high = []
    hard, lines = relocate.fences(rgb, cls, gm.m_per_px_x, high=high)
    mpp = gm.m_per_px_x
    elements = []
    quiet = np.zeros(cls.shape, bool)
    if lines:
        from PIL import Image, ImageDraw
        width = max(2, int(round(2 * relocate.FENCE_HALF_M / mpp)))
        keep, gone_lines = [], []
        for k, line in enumerate(lines):
            mid = line[len(line) // 2]
            act = _pick(overrides, "fence", mid[0], mid[1], mpp)
            elements.append(dict(kind="fence", u=float(mid[0]), v=float(mid[1]), tall=k in high, action=act,
                                 line=[tuple(map(float, q)) for q in line[::max(1, len(line) // 12)]]))
            if act == "remove":
                gone_lines.append(line)
            else:
                keep.append(k)
        if gone_lines:
            # no obstacle: the black of that fence is only a line on the map, no path either way
            canvas = Image.new("1", (hard.shape[1], hard.shape[0]), 0)
            draw = ImageDraw.Draw(canvas)
            for line in gone_lines:
                draw.line([tuple(q) for q in line], fill=1, width=width)
            # (the ticks too: every piece of the mask that the fence touches goes)
            lab, _ = ndi_label(hard, structure=np.ones((3, 3)))
            hit = np.unique(lab[np.array(canvas, bool) & hard])
            taken = np.isin(lab, hit[hit > 0])
            quiet |= taken            # still a black line, so no path: the terrain beside it, no fence to cross
            hard = hard & ~taken
        was_high = set(high)
        lines = [lines[k] for k in keep]
        high[:] = [i for i, k in enumerate(keep) if k in was_high and elements[k]["action"] != "hard"]
        high.extend(i for i, k in enumerate(keep) if k not in was_high and elements[k]["action"] == "tall")
    grounds = []
    grey = T.sprint_greys(rgb, gm.m_per_px_x)[0]
    sprint = grey is not None     # (its paved areas are a lighter brown)
    (fenced, blocked), pens = relocate.enclosures(rgb, cls, gm.m_per_px_x, grow_m=(5.0, relocate.ROUTE_FENCE_M),
                                                  fence_lines=lines, grounds=grounds, sprint=sprint)
    corner = []        # outlines of enclosures a person turned into a fence to climb
    if (open_at or overrides) and blocked.any():
        H, W = blocked.shape
        inside = max(1, int(round(PEN_IN_M / mpp)))
        gone = np.zeros((H, W), bool)
        keep = []
        for pen, (sl, part) in zip(pens, grounds):
            act = _pick(overrides, "enclosure", pen[0], pen[1], mpp)
            elements.append(_pen_element(pen, sl, part, act))
            # a control stands in this ground or at its fence: the whole of it opens
            near = relocate._grow(part, inside)
            if act in ("remove", "fence") or any(
                    sl[0].start <= int(round(v)) < sl[0].stop and sl[1].start <= int(round(u)) < sl[1].stop
                    and near[int(round(v)) - sl[0].start, int(round(u)) - sl[1].start] for u, v in open_at or []):
                g = np.zeros((H, W), bool)
                g[sl] = relocate._grow(part, max(2, int(round((5.0 + 1.0) / mpp))))
                gone |= g
                if act == "fence":
                    ring = np.zeros((H, W), bool)
                    ring[sl] = part & ~binary_dilation(~part, iterations=max(1, int(round(1.5 / mpp))))
                    corner.append(ring)
                if act is None:
                    elements.pop()     # opened by a control: it is no obstacle to show
            else:
                keep.append(pen)
        # a control on the fence itself (outside it, at a corner): the fence is open just around it, so that the
        # control can be reached, the ground behind stays closed
        r = (relocate.ROUTE_FENCE_M + 1.0) / mpp
        for u, v in open_at or []:
            ui, vi = int(round(u)), int(round(v))
            if 0 <= ui < W and 0 <= vi < H and blocked[vi, ui] and not gone[vi, ui]:
                pad = int(r) + 1
                v0, u0 = max(vi - pad, 0), max(ui - pad, 0)
                yy, xx = np.mgrid[v0:min(vi + pad + 1, H), u0:min(ui + pad + 1, W)]
                hole = (xx - u) ** 2 + (yy - v) ** 2 <= r * r
                blocked[v0:v0 + hole.shape[0], u0:u0 + hole.shape[1]] &= ~hole
        if gone.any():
            blocked, fenced, pens = blocked & ~gone, fenced & ~gone, keep
    else:
        elements.extend(_pen_element(pen, sl, part, None) for pen, (sl, part) in zip(pens, grounds))
    if high:
        # an impassable fence (ISOM 518, in ISOM 2000 524 "high fence": ticks in pairs) is not climbed: blocked as
        # the fence of fenced ground is, a path along it stays open
        from PIL import Image, ImageDraw
        canvas = Image.new("1", (blocked.shape[1], blocked.shape[0]), 0)
        draw = ImageDraw.Draw(canvas)
        width = max(2, int(round(2 * relocate.FENCE_HALF_M / gm.m_per_px_x)))
        for k in high:
            draw.line([tuple(p) for p in lines[k]], fill=1, width=width)
        tall = np.array(canvas, bool) & relocate._grow(hard, 1.0)
        tall = relocate._grow(tall, max(1.0, 1.0 / gm.m_per_px_x))
        blocked = blocked | tall
        hard = hard & ~tall
    for ring in corner:
        hard |= ring & ~blocked
    hard &= ~blocked
    # The black line around an area that must not be entered (ISOM 520: a settlement, a private garden) is
    # its fence or its edge, with or without ticks: no path either. A road along it keeps its paved surface.
    outline = (cls == T.PATH) & relocate._grow(relocate.out_of_bounds(rgb, cls, gm.m_per_px_x),
                                               max(1.0, OUTLINE_M / gm.m_per_px_x))
    # ... the whole width of that line (the fence of a settlement is drawn up to 4 m thick), but not a path
    # that only runs near it
    # ... nor the black edge of a paved road or street (ISOM 501, 502: light brown) that runs through or along
    # the area: that is where one runs
    paved = relocate._grow(T.paved(rgb, sprint), max(1.0, OUTLINE_M / gm.m_per_px_x))
    outline = binary_dilation(outline & ~paved, iterations=max(1, int(round(OUTLINE_WIDE_M / gm.m_per_px_x))),
                              mask=(cls == T.PATH) & ~paved)
    # The walls of a sprint map (terrain.sprint_walls): an impassable one is a building in cls already, and is
    # given to the routing grid as well, so that it stays a wall however coarse the grid is; a passable one is
    # slow to climb over, and no path.
    walls, climb = np.zeros(cls.shape, bool), np.zeros(cls.shape, bool)
    if sprint:
        walls, climb = T.sprint_walls(rgb, grey, gm.m_per_px_x, blur_m=getattr(gm, "blur_m", 0.0))
        walls = binary_dilation(walls)
        if open_at and walls.any():
            # A control set on a wall (at its corner or its end, Mistrovství MSK 11) is punched from either
            # side: the wall is open around it. Else the nearest cell of the control may lie behind the wall.
            r = WALL_OPEN_M / gm.m_per_px_x
            pad = int(r) + 20                    # the ground beside the wall is looked for this far around
            H, W = cls.shape
            cls = cls.copy()
            for u, v in open_at:
                u0, u1 = max(int(u) - pad, 0), min(int(u) + pad + 1, W)
                v0, v1 = max(int(v) - pad, 0), min(int(v) + pad + 1, H)
                if u0 >= u1 or v0 >= v1:
                    continue
                yy, xx = np.mgrid[v0:v1, u0:u1]
                near = (xx - u) ** 2 + (yy - v) ** 2 <= r * r
                box = (slice(v0, v1), slice(u0, u1))
                part = cls[box]
                gate = walls[box] & near & (part == T.BUILDING)
                walls[box] &= ~near
                if gate.any():
                    _, (iy, ix) = distance_transform_edt(part == T.BUILDING, return_indices=True)
                    part[gate] = part[iy[gate], ix[gate]]
        climb &= ~blocked & ~walls
        # (relocate.fences takes the dots of a passable wall for the ticks of a fence: it is a wall to climb)
        hard &= ~binary_dilation(climb, iterations=2)
    off = hard | outline | climb | quiet
    if off.any():
        # such a line is drawn in black like a path, but nobody runs along it at the speed of one: the
        # terrain under it is what lies beside it
        fix = off & (cls == T.PATH)
        _, (iy, ix) = distance_transform_edt((cls == T.PATH) | off, return_indices=True)
        cls = cls.copy()
        cls[fix] = cls[iy[fix], ix[fix]]
    return dict(cls=cls, blocked=blocked, hard=hard, fenced=fenced, pens=pens, fences=lines, outline=outline,
                walls=walls, climb=climb, sprint=sprint, elements=elements)


class _Cut:
    """A part of a map, as far as obstacles() needs one: its picture and its resolution."""

    def __init__(self, gm, cut):
        self.image = np.asarray(gm.image)[cut]
        self.m_per_px_x = gm.m_per_px_x


def barriers(path, gm):
    """barriers.json (lat/lon, see oroute/osm.py, oroute/hatch.py and the web app) -> what routing.Grid takes,
    in map pixels. origin: what each forbidden line is (dict(source, what), for routing.crossed)."""
    with open(path, encoding="utf-8") as f:
        b = json.load(f)
    px = lambda line: [tuple(float(a) for a in gm.latlon_to_px(p[0], p[1])) for p in line]
    forbidden = [l for l in b.get("lines", []) if l.get("kind") != "hard"]
    return dict(forbidden=[px(l["line"]) for l in forbidden],
                origin=[dict(source=l.get("source"), what=l.get("what")) for l in forbidden],
                hard=[px(l["line"]) for l in b.get("lines", []) if l.get("kind") == "hard"],
                crossings=px(b.get("crossings", [])), areas=[px(a) for a in b.get("areas", [])])


def overrides(path, gm):
    """The corrections a person made to the recognised obstacles (barriers.json "overrides": [dict(kind, lat, lon,
    action)]) in map pixels, for obstacles(). Nothing (None) without a file or without any."""
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f).get("overrides") or []
    out = []
    for o in raw:
        u, v = gm.latlon_to_px(o["lat"], o["lon"])
        out.append(dict(kind=o["kind"], u=float(u), v=float(v), action=o["action"]))
    return out or None


def corner_box(gm):
    """(north, south, east, west) around the four corners of the picture: a rotated map reaches beyond its
    LatLonBox."""
    la, lo = gm.px_to_latlon([0, gm.W, 0, gm.W], [0, 0, gm.H, gm.H])
    return float(max(la)), float(min(la)), float(max(lo)), float(min(lo))


def elevation(gm, cache_dir, source="aws", used=None):
    """The elevation model of the map, cached in cache_dir (see dem.load_dem for the sources).
    used: the source an earlier run with the same `source` ended up with ("aws" when ČÚZK did not answer
    then); given it, that run's elevation is taken again instead of asking ČÚZK once more."""
    try:
        if source == "aws":
            return TerrariumDEM(gm.n, gm.s, gm.e, gm.w, cache=os.path.join(cache_dir, "dem_cache.npz"))
        return load_dem(*corner_box(gm), cache_dir, "aws" if used == "aws" else source)
    except OSError as e:     # urllib's URLError and timeouts: nothing stored and no way to download it
        raise InputError("no_network", f"the elevation could not be downloaded ({e})") from e
