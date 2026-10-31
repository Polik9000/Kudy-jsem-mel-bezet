"""Help for "I lost contact with the map near the control": what is around every control that can be found
again in the terrain (catching features), how to get from each to the control, where to attack the control
from on the way in, what stops a runner who ran past it, and whether the track shows the runner was lost
there. Rules and geometry on the map without course, no control descriptions.

usage: python3 -m oroute.relocate MAPONLY.kmz OUT_DIR RESULT.json
           [--dem aws|cuzk|auto] [--terrain-cache FILE] [--barriers FILE] [--debug DIR]

OUT_DIR      output folder of the race: analysis.json (analyze.py) and best/ (bestroute.py)
RESULT.json  {"version": VERSION, "controls": [{"leg": 3, "features": [...], "attack": {...} | null,
             "beyond": {"az", "back_az", "parts": [{"side": "left" | "ahead" | "right", "kind", "dist", "line", ...}]}
             | null, "lost": {...} | null}]}
--debug DIR  also draw every control with what was found around it (to check the features against the map)

Around a control (up to RADIUS_M, the attack point up to ATTACK_HI) the map gives, named as in ISOM 2017-2:

  from the terrain classes of oroute/terrain.py and the black and blue lines of the picture
    junction     where paths meet (502-508), every arm going on for BRANCH_M
    path_end     where a path stops
    path         a road, track or path, as a line
    enclosure    the ground a fence (516, 518) closes in: a fenced plantation
    stream       a watercourse (304-306), as a line; stream_path: where a path crosses one
    pond         water wide enough to be a pond (301, 302)
    building     a building (521)
    clearing     a small open patch alone in the forest (401, 403); open_edge: the edge of a large one
    settlement   the edge of an area that must not be entered (520), as a line
  from the elevation
    hilltop      a top with everything around it clearly lower
  from the point symbols of the picture (oroute/symbols.py)
    knoll 109, depression 111, pit 112, landform 115, boulder 204/205, water_pit 303, well 311, tree 417,
    stand 525, object 530/531

Features the control cannot reasonably be reached from (out of bounds, water, forbidden lines in between) are
dropped, the rest are ranked and two to four are kept, spread around the control. Bearings are to the north
of the map (its magnetic north lines), which is what the compass shows.

The way in is that of the best route (bestroute.py): the attack point lies before the control on it. The
backstop ("beyond") is what a runner who ran on past the control runs into, to the left, straight on and to
the right of the way they came: a line across (path, stream) or something large (fenced ground, a pond, the
edge of open land or of a settlement, a house). A point one can run past 20 m to the side is no backstop.

Left out on purpose after looking at the four races of data/ (docs/validace.md): the edges of thickets (on
maps with much green the nearest edge is no place one could name), pieces of a mosaic of half-open land
taken for clearings, and anything from control descriptions.
"""
import argparse
import json
import math
import os

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import mapdata, symbols
from . import terrain as T
from .jsonout import rounded
from .kmzmap import GeoMap
from .mistakes import MIN_LOSS_S, junctions
from .routing import Grid
from .speedmodel import SpeedModel

VERSION = 8            # goes up when the rules change: results of an older version are offered to be redone
                       # (7: the walls of a sprint map bar the way and are no house; 8: north lines at any angle
                       # are no streams, bearings to them, pens of coarse pictures)
RADIUS_M = 150.0       # catching features are looked for this far from the control ...
NEAR_M = 30.0          # ... and no nearer than this (that is the control itself);
LINE_NEAR_M = 10.0     # a line may pass nearer: "the stream runs 20 m south of the control" is worth knowing
ATTACK_HI = 200.0      # the attack point may be this far (as oroute.mistakes.attack_point had it)
ATTACK_DEG = 70.0      # "on the way in": within this angle of the direction the best route comes from ...
ON_ROUTE_M = 30.0      # ... or this close to the best route itself, which is better
ATTACK_MIN_LEG_M = 80.0     # a leg shorter (straight) than this has no attack point: one sets off from the control before
ATTACK_FROM_PREV_M = 25.0   # the attack point lies at least this far from the control before (or the start) ...
ATTACK_LEG_SHARE = 0.7      # ... and no farther before its own control than this share of the straight length of the leg
APPROACH_M = 100.0     # the direction of the way in: from where the best route is this far before the control
RUN_IN_M = 40.0        # the direction a runner runs on past the control in: that of this last stretch of the route
CUT_M = 260.0          # the map is read this far around a control
BEYOND_M = (15.0, 200.0)   # a backstop is looked for this far beyond the control ...
BEYOND_FAN = 60.0      # ... on rays up to this much to either side of the direction of travel, ...
BEYOND_STEP = 10.0     # ... this many degrees apart;
BEYOND_AHEAD = 20.0    # the rays within this of the direction are "straight on", the others "left" and "right"
BEYOND_FAR_M = 150.0   # a part farther than this counts only when two thirds of its rays meet the same thing
OWN_M = 15.0           # open land this close to the control is where the control stands: its edge up to
OWN_FAR_M = 45.0       # ... this far away is the control's own feature, no backstop (the far edge of a field is one)
TRACK_IN_M = 30.0      # the runner's own way in is taken when the track ends this close to the control
OWN_LINE_M = 10.0      # a path or stream this close to the control is the control's own line ...
OWN_LINE_GOES_M = 60.0 # ... up to this far from it, no backstop until a ray has left it ...
OWN_LEAVE_M = 5.0      # ... for this far
ALONG_DEG = 30.0       # straight on, a path or stream closer than this to the direction of the ray runs along
ALONG_M = 12.0         # the way (the path one came by), not across it; its direction is read this far around
ALONG_NEAR_M = 15.0    # ... and it is the path one came by only when, drawn on, it passes this close to the control
MIN_FEATURES, MAX_FEATURES = 2, 4
MIN_SCORE = 0.38       # weaker candidates are not shown
APART_DEG = 45.0       # features closer in bearing than this tell the same thing
DETOUR = 2.5           # reachable = at most this many times the straight run through forest, plus DETOUR_S
DETOUR_S = 30.0
WALL_M = 4.0           # the straight line from a feature to the control is barred when this much of it lies in
                       # what one cannot go through (fenced ground, forbidden lines and areas, water, out of bounds);
VIA_MIN = 1.05         # a way round less than this many times the straight distance is the straight line (it only
                       # clips a corner of the obstacle): the bearing stays
DIRECT_DETOUR = 1.3    # the feature is then shown only when the way round is at most this many times the straight
                       # distance, and with that way round instead of the straight bearing
FIRST_M = 30.0         # the bearing to set off on along the way round: that of its first stretch this long
VIA_TOL_M = 3.0        # the way round is drawn as a line no farther than this from the cells it was found on
EDGE_NEAR_M = 20.0     # the edge of such a feature counts in full from this distance on
EDGE_KINDS = ("enclosure", "pond")    # large features one comes to at their edge: they are placed where the
                                      # straight line from the control meets them, not at their middle
SAME_M = 25.0          # two finds of one kind closer than this are one feature
MIN_LINE_M = 60.0      # a path or a stream shorter than this is a map symbol, not a line to catch
POND_WIDE_M = 12.0     # water at least this wide is a pond; narrower water is a stream
BRANCH_M = 21.0        # every arm of a junction must reach this far from it
END_GAP_M = 12.0       # a path that goes on within this distance did not end: the line is only interrupted
ENCLOSURE_M2 = (100.0, 60000.0)   # the ground a fence closes in is an enclosure when it is this large, ...
LARGE_M2, LARGE_TICK_M = 10000.0, 60.0  # (a pen larger than LARGE_M2 needs a tick every LARGE_TICK_M of its edge)
FENCE_SHARE = 0.6                 # ... at least this much of what is around it is a black line ...
FENCE_TICKS = 2                   # ... and that line has at least this many ticks pointing inwards
TICK_M = (2.5, 10.0)              # how long a tick is (longer black strokes inside are paths, not ticks); on a
TICK_MIN_M, TICK_MIN_PX = 1.5, 2  # coarse picture the short end is less: what is left of a tick in the hole after
TICK_FINE_PX = 4                  # the line is drawn over its foot, at least TICK_MIN_PX pixels (night 25. 10.);
                                  # coarse = TICK_M[0] is fewer than TICK_FINE_PX pixels (a screenshot at 1 m/px)
INK_NEAR_PX = 1                   # the black of the map up to this far from a line makes it a line of the map
THIN_M = 6.0                      # ground fenced in holds a circle this wide (a road between two fences does not)
PAVED_SHARE = 0.25                # ... and is no street: not more than this share of it paved (ISOM 501, 502)
CORNER_M2, CORNER_SHARE = 400.0, 0.45   # a ground this small, closed in by this much black, ...
CORNER_GAP_M = 5.0                # ... this close across a fence from a pen found, is a corner of that pen
FENCE_GAP_M = 5.0                 # a gap this wide in the line around the ground does not open it, ...
FENCE_BRIDGE_M = 12.0             # ... nor one up to this wide between the ends of two fences (a gate, a path
                                  # through the fence: 3 to 5 m, with the line broken for a contour or a ride;
                                  # 12 m = 9 px at 1.33 m/px; wider is a way in)
ROUTE_FENCE_M = 3.5               # routes keep out of fenced ground and this far around it (the fence itself)
FENCE_ROW = 3                     # a fence that closes nothing in: at least this many ticks in a row on one side
FENCE_TICK_GAP_M = 45.0           # ... of one continuous line, no farther apart than this, ...
FENCE_BEND_DEG = 35.0             # ... the line turning less than this from one tick to the next
FENCE_HALF_M = 2.5                # the black within this distance of the line through the feet of the ticks is the fence
TICK_TIP_M = 2.2                  # the tip of a tick: one arc of black on a circle of this radius, ...
TICK_ARC = 0.3                    # ... no wider than this share of the circle (the edge of a thick line: half of it)
TICK_BEYOND_M = 3.0               # this far beyond the length of the tick the circle cuts the line it stands on twice
TICK_TWIN_M = 3.5                 # two ticks this close on opposite sides of a line are one bar across it
TICK_LEAN_DEG = 55.0              # a tick may lean this much from the perpendicular of its line
TICK_PAIR_M = 4.0                 # two ticks on the same side this close are a pair: an impassable fence
HIGH_PAIRS, HIGH_SHARE = 2, 0.6   # ... when at least this many pairs make this share of its ticks
PAIR_APART = 2.0                  # ... and the gaps before and after a pair are this many times as long
CLEARING_M2 = (200.0, 4000.0)     # open land of this size, alone in the forest, is a clearing: a point
OPEN_EDGE_M2 = 10000.0            # open land at least this large has an edge worth naming
SETTLEMENT_M2 = 1500.0            # ... and so has an area that must not be entered of this size
INK_SHARE = 0.01                  # a line or a house with less of the black of the map in it than this is grey
                                  # print around the map (its legend, the code of Livelox): measured, the black
                                  # lines of the four maps have 0.05 and more, the grey print none
STOP_SAME_M = 5.0                 # two backstops this close behind each other are one thing (a field and the
                                  # path along its edge): the one earlier in BACKSTOPS is named
BUILDING_M2 = 30.0
POND_M2 = (40.0, 3000.0)
HILLTOP_RING_M = 45.0  # a hilltop: every point this far around it is lower by HILLTOP_DROP_M (by elevation source)
HILLTOP_DROP_M = {"cuzk": 3.0, "aws": 6.0}
CROWD_M, CROWD = 60.0, 3   # this many of one kind this close together: none of them tells where one is
ZONE_M = 200.0         # wandering is looked for from where the track first comes this close to the control
WANDER_M = 60.0        # the track ran at least this much more than the straight way in ...
WANDER_S = 30.0        # ... and took at least this much longer than running it straight
LOST_NEAR_M = 120.0    # a feature farther than this from the wandering track was no help

SYMBOLS = ("knoll", "depression", "pit", "landform", "boulder", "water_pit", "well", "tree", "stand", "object")
POINTS = ("junction", "path_end", "stream_path", "building", "enclosure", "pond", "clearing", "hilltop") + SYMBOLS
BASE = dict(junction=1.0, stream_path=1.0, enclosure=0.95, building=0.9, pond=0.9, path_end=0.8, clearing=0.75,
            hilltop=0.7, tree=0.7, stand=0.7, well=0.7, object=0.65, knoll=0.6, boulder=0.6, landform=0.6,
            depression=0.55, pit=0.55, water_pit=0.55,
            path=0.65, stream=0.65, settlement=0.6, open_edge=0.5, fence=0.65)
# what stops a runner who ran on past the control; where two lie on each other the first one is named
BACKSTOPS = ("enclosure", "fence", "pond", "building", "settlement", "path", "stream", "clearing", "open_edge")


def _disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


# Growing, closing and opening a mask by a disc of r pixels. They give what scipy's binary_dilation, _closing
# and _opening give with _disk(r) (outside the picture counts as empty), but through the distance to the
# nearest pixel, which takes the same time for a disc of any size: on a sharp map the discs are up to 29
# pixels wide. (For the small discs of enclosures(), on the whole map, scipy's own are faster.)
def _grow(mask, r):
    return ndi.distance_transform_edt(~mask) <= r if mask.any() else mask.copy()


def _shrink(mask, r):
    p = int(r) + 1
    return ~_grow(~np.pad(mask, p), r)[p:-p, p:-p]


def _close(mask, r):
    p = int(r) + 1
    return ~_grow(~_grow(np.pad(mask, p), r), r)[p:-p, p:-p]


def _open(mask, r):
    return _grow(_shrink(mask, r), r)


def _arcs(mask, pts, r):
    """Number of separate arcs of `mask` on the circle of radius r px around each point (u, v)."""
    if not len(pts):
        return np.zeros(0, int)
    H, W = mask.shape
    ang = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    p = np.asarray(pts, float)
    uu = np.clip(np.round(p[:, :1] + r * np.cos(ang)[None]).astype(int), 0, W - 1)
    vv = np.clip(np.round(p[:, 1:] + r * np.sin(ang)[None]).astype(int), 0, H - 1)
    on = mask[vv, uu]
    return (on & ~np.roll(on, 1, axis=1)).sum(1)


def _long(mask, min_px):
    """The connected parts of a mask that are at least min_px across."""
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if not n:
        return np.zeros(mask.shape, bool)
    ext = np.array([max(s[0].stop - s[0].start, s[1].stop - s[1].start) for s in ndi.find_objects(lab)])
    return np.r_[False, ext >= min_px][lab]


def _nearest(mask, c):
    """The pixel of a mask nearest to c = (u, v), or None."""
    vs, us = np.nonzero(mask)
    if not len(us):
        return None
    k = np.argmin((us - c[0]) ** 2 + (vs - c[1]) ** 2)
    return float(us[k]), float(vs[k])


def _to_line(p, line):
    """Distance in pixels from point p to a polyline [(u, v), ...]."""
    q, p = np.asarray(line, float), np.asarray(p, float)
    if len(q) < 2:
        return float(np.hypot(*(p - q[0]))) if len(q) else np.inf
    a, d = q[:-1], np.diff(q, axis=0)
    t = np.clip(((p - a) * d).sum(1) / np.maximum((d ** 2).sum(1), 1e-9), 0, 1)
    return float(np.hypot(*(a + t[:, None] * d - p).T).min())


def stream_mask(rgb, header_px=0):
    """Blue lines of the map picture (streams, ditches) without the magnetic north lines (terrain.north_lines:
    straight, parallel and evenly spaced, at whatever angle the picture has them). Where a stream crosses a north
    line the blue in the band of the line is the stream's: it stays, so the stream is not cut in two. Areas of
    water and marsh are taken out later, where the terrain classes are at hand."""
    blue = (rgb[..., 2] > 200) & (rgb[..., 0] < 120)
    north = T.north_lines(rgb, header_px)
    band = north["mask"]
    if not band.any():
        return blue
    rest = blue & ~band
    # a piece of blue off the lines that reaches the band from the side: what of the band lies within the
    # width of the line from it is where it crosses
    w = max(2, int(round(north["width_px"])) + 2)
    pieces = _long(rest, 4 * w)
    return rest | (blue & band & _grow(pieces, w))


def no_symbols(cls, mpp):
    """Where point symbols are not looked for (oroute.symbols.find, skip): areas that must not be entered and
    a few metres around them (the small black squares there are houses), and buildings."""
    return ndi.binary_dilation(cls == T.OOB, iterations=max(1, int(round(5.0 / mpp)))) | (cls == T.BUILDING)


def enclosures(rgb, cls, mpp, grow_m=5.0, why=None, fence_lines=None, grounds=None, sprint=False):
    """(mask of fenced ground with the fence around it, [(u, v, area m2)] of the enclosures in it).
    grow_m: how far around the ground the mask reaches: 5 m takes the fence and what is drawn along it (for
    reading features), ROUTE_FENCE_M only the fence (for routing: a path along it stays open). Several
    distances give a tuple of masks.

    A fence (ISOM 516, 518) is a black line like a path, with short ticks to one side; around a closed area
    the ticks point inwards. So an enclosure is ground closed in by a solid black line with at least
    FENCE_TICKS short black strokes standing into it from that line. A contour is drawn over the black, so
    where one crosses the line its brown counts as the line (only there: a contour through the middle of the
    ground does not split it). A loop
    of paths, the outline of a roof or of a paved area have no ticks; an area that must not be entered (olive)
    is no enclosure whatever is drawn around it, and neither is a long thin strip (a road between two fences),
    a sliver along such an area, or a patch in colours no map area has (the emblem in the corner of the sheet).
    A fence that closes nothing in is not read: it stays a path like every other black line.
    rgb: the picture, cls: its terrain classes (the same cut-out, or the whole map).
    fence_lines: the fences of the map as fences() gives them ([[(u, v), ...]] along the feet of their ticks):
    where two of them end FENCE_GAP_M to FENCE_BRIDGE_M apart, the gap between the ends (a gate, a path through
    the fence, the line broken for a symbol) is closed too. Only fences: a loop of paths has no ticks.
    sprint: the map is a sprint map (mapdata.obstacles): its paved areas are a lighter brown (terrain.paved).
    grounds: a list to fill with (slices, mask) of the ground of every enclosure found, in the order of pens
    (mapdata.obstacles opens the one a control stands in, and only that one).
    why: a dict to fill for tools/oplocenky.py: holes (the labels of every ground closed in by black) and list
    ([dict(i, u, v, area, reason)]: why each was not taken, "ok" when it was). Nothing else changes."""
    H, W = cls.shape
    im = rgb.astype(np.int32)
    dark = (im.sum(-1) < 330) & (im.max(-1) - im.min(-1) < 45)
    black = symbols.colours(rgb)["black"]        # the black of the map, not the grey of its legend and codes
    dark &= ~ndi.binary_opening(dark, _disk(max(2, int(3.0 / mpp))))        # not the solid black of buildings
    over = symbols.colours(rgb)["brown"] & ndi.binary_dilation(dark, _disk(max(2, int(round(3.0 / mpp)))))
    if fence_lines:
        dark = dark | _bridges(fence_lines, mpp, dark.shape)
    # a fence drawn up to a contour or a green edge may stop a few metres short of it: such gaps are closed
    closed = ndi.binary_closing(np.pad(dark | over, 12), _disk(max(1, int(round(FENCE_GAP_M / 2 / mpp)))))[12:-12, 12:-12]
    holes, _ = ndi.label(ndi.binary_fill_holes(closed) & ~closed)
    notch = max(2, int(1.8 / mpp) + 1)       # a tick is thinner than twice this
    pad = notch + max(2, int(6.0 / mpp))
    halo = max(4, int(15.0 / mpp))          # what lies this far around a ground tells a map from a picture
    # A coarse picture (a tick shorter than TICK_FINE_PX pixels: a map of Livelox at 1 to 1.33 m per pixel,
    # a screenshot) draws a pen with blurred lines, short ticks swallowed by the line and stripes mixed with
    # the fill: the rules marked "coarse" below read it as drawn (night 25. 10., Bělá). On a sharper map they
    # would take the yards of a town for pens, so there the reading stays as it was.
    coarse = TICK_M[0] / mpp < TICK_FINE_PX
    # the colours of the areas of a map, and the saturated green of a thicket or of planted rows (a pen is
    # often full of it); not the blue of water: a pond with a black bank is no pen
    palette = np.array(list(T.AREA) + [T.LINE["dgreen"]], np.int32)
    map_colours = np.array(list(T.AREA) + [c for k, c in T.LINE.items() if k not in ("black", "dgreen")]
                           + [T.LINE["dgreen"]], np.int32)
    grows = (grow_m,) if np.isscalar(grow_m) else tuple(grow_m)
    fenced, pens = [np.zeros((H, W), bool) for _ in grows], []
    if why is not None:
        why["holes"], why["list"] = holes, []
    taken = np.zeros((H, W), bool)          # the ground of the enclosures found (for their corners, below)
    corners = []                            # small grounds that may be a corner of one of them

    def no(i, sl, area, reason):
        if why is not None:
            v, u = ndi.center_of_mass(holes[sl] == i)
            why["list"].append(dict(i=i, u=float(u + sl[1].start), v=float(v + sl[0].start), area=area, reason=reason))
    for i, sl in enumerate(ndi.find_objects(holes), 1):
        hp, wp = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = float((holes[sl] == i).sum()) * mpp * mpp
        on_edge = sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == H or sl[1].stop == W
        # long and thin is a road between two fences or a sliver along an area, not ground fenced in: thin as
        # measured inside it (the widest circle it holds), so a long pen that bends or narrows to a point stays
        if coarse:
            thin = min(hp, wp) * mpp < 6.0 or (2.0 * ndi.distance_transform_edt(np.pad(holes[sl] == i, 1)).max()
                                              * mpp < THIN_M)
        else:
            thin = min(hp, wp) * mpp < 6.0 or min(hp, wp) < 0.25 * max(hp, wp) or area < 0.3 * hp * wp * mpp * mpp
        if not ENCLOSURE_M2[0] <= area <= ENCLOSURE_M2[1] or on_edge or thin:
            if area >= 50.0:
                no(i, sl, area, "plocha" if not ENCLOSURE_M2[0] <= area <= ENCLOSURE_M2[1] else "okraj" if on_edge
                   else "tvar")
            continue
        big = (slice(max(sl[0].start - pad, 0), sl[0].stop + pad), slice(max(sl[1].start - pad, 0), sl[1].stop + pad))
        part = holes[big] == i
        around = ndi.binary_dilation(part, iterations=2) & ~part
        beside = ndi.binary_dilation(part, iterations=max(3, int(4.0 / mpp))) & ~part
        # the black of the map is looked for up to a pixel from the line: on a blurred picture (a screenshot of
        # Livelox) only the middle of a line is that dark, its edges are grey
        ink = ndi.binary_dilation(black[big], iterations=INK_NEAR_PX) if coarse else black[big]
        if (cls[big][part] == T.OOB).mean() > 0.5 or (cls[big][beside] == T.OOB).mean() > 0.5 \
                or dark[big][around].mean() < FENCE_SHARE or ink[around & dark[big]].mean() < 0.3:
            no(i, sl, area, "oob" if (cls[big][part] == T.OOB).mean() > 0.5 or (cls[big][beside] == T.OOB).mean() > 0.5
               else f"podil_cerne {dark[big][around].mean():.2f}")
            if coarse and area <= CORNER_M2 and dark[big][around].mean() >= CORNER_SHARE \
                    and (cls[big][part] != T.OOB).all():
                corners.append((i, big, part, area))
            continue
        inside = im[big][part & ~dark[big]][::7]
        # ... and so is what lies around it (the map: its areas and its lines), not a picture in the margin
        wide = (slice(max(sl[0].start - halo, 0), sl[0].stop + halo), slice(max(sl[1].start - halo, 0), sl[1].stop + halo))
        hole = holes[wide] == i
        ann = _grow(hole, halo) & ~_grow(hole, max(2, int(6.0 / mpp)))
        out = im[wide][ann & ~dark[wide]][::5]
        if len(inside) and (_palette_dist(inside, palette, mix=(-1,) if coarse else ()) < 45).mean() < 0.6 \
                or len(out) and (_palette_dist(out, map_colours, mix=(0, -1)) < 45).mean() < 0.6 \
                or (cls[big][part] == T.WATER).mean() > 0.5:
            no(i, sl, area, "paleta")
            continue
        # a street between the fenced gardens of a village is paved (light brown): one runs along it
        if T.paved(rgb[big], sprint)[part].mean() > PAVED_SHARE:
            no(i, sl, area, "silnice")
            continue
        # the ticks are black, so they are notches in the hole: closing the hole fills them in. A tick hangs
        # on the line around the hole; a dash of a path that crosses the ground does not.
        # The ground as drawn: closing the gaps (above) also fills the room between the ticks and the line on a
        # coarse picture, so the ground shrinks by the length of the ticks and loses them, and its narrow corners
        # (the point of a triangle). Without it, where the line is whole: what the line itself closes in and
        # that overlaps the ground found above.
        if coarse:
            part = _drawn(part, (dark | over)[big])
        # a tick is as thick as the line it hangs on: on a blurred picture that is more pixels than its 0.2 mm
        ring = dark[big] & ndi.binary_dilation(part, iterations=notch + 3)
        width = 2.0 * float(np.percentile(ndi.distance_transform_edt(ring)[ring], 90)) if ring.any() else 0.0
        nt = max(notch, int(np.ceil(width / 2.0)) + 1) if coarse else notch
        filled = ndi.binary_closing(part, _disk(nt))
        ticks, n = ndi.label(filled & ~part & dark[big])
        line = ndi.binary_dilation(dark[big] & ~filled, iterations=1)
        good = 0
        lo = TICK_M[0] if TICK_M[0] / mpp >= TICK_FINE_PX else max(TICK_MIN_M, TICK_MIN_PX * mpp)
        for j, t in enumerate(ndi.find_objects(ticks), 1):
            reach = max(t[0].stop - t[0].start, t[1].stop - t[1].start) * mpp
            good += lo <= reach <= TICK_M[1] and bool((line[t] & (ticks[t] == j)).any())
        need = FENCE_TICKS
        if area > LARGE_M2:
            # a large ground is fenced all round: ticks along the whole of its edge, not two of a path's dashes
            need = max(need, int(around.sum() / 2 * mpp / LARGE_TICK_M))
        if good < need:
            no(i, sl, area, f"zoubky {good}")
            if coarse and area <= CORNER_M2:
                corners.append((i, big, part, area))
            continue
        no(i, sl, area, "ok")
        taken[big] |= part
        if grounds is not None:
            grounds.append((big, part))
        v, u = ndi.center_of_mass(part)
        pens.append((float(u + big[1].start), float(v + big[0].start), area))
        # ... with the fence itself: the line round the ground (on a coarse picture it may be wider than g). Not on
        # a sprint map: its black lines along a yard are the edges of houses and streets
        fence = ring & _grow(part, width + 2) if not sprint else np.zeros(part.shape, bool)
        for mask, g in zip(fenced, grows):
            mask[big] |= _grow(part, max(2, int(g / mpp))) | ndi.binary_dilation(fence, iterations=1)
    # The narrow point of a pen (a triangle) is cut off its ground by the closing of the gaps: a small ground
    # just across the fence from a pen found, with no ticks of its own to show, is that corner of it.
    for i, big, part, area in corners:
        if not (ndi.binary_dilation(part, iterations=max(2, int(round(CORNER_GAP_M / mpp)))) & taken[big]).any():
            continue
        if why is not None:
            for d in why["list"]:
                if d["i"] == i:
                    d["reason"] = "ok (roh)"
        ring = dark[big] & _grow(part, max(2, int(round(CORNER_GAP_M / mpp))))
        for mask, g in zip(fenced, grows):
            mask[big] |= _grow(part, max(2, int(g / mpp))) | ndi.binary_dilation(ring, iterations=1)
    return (fenced[0] if np.isscalar(grow_m) else tuple(fenced)), pens


def _bridges(lines, mpp, shape):
    """The straight lines across the gaps between the ends of fences (fences()) FENCE_GAP_M to FENCE_BRIDGE_M
    apart, as a mask: closed, a gate or a path through a fence does not open the ground it fences in."""
    from PIL import Image, ImageDraw
    ends = [(tuple(l[0]), k) for k, l in enumerate(lines) if len(l) >= 2] + \
           [(tuple(l[-1]), k) for k, l in enumerate(lines) if len(l) >= 2]
    canvas = Image.new("1", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(canvas)
    width = max(2, int(round(1.0 / mpp)))
    for a in range(len(ends)):
        for b in range(a + 1, len(ends)):
            (p, i), (q, j) = ends[a], ends[b]
            d = math.hypot(p[0] - q[0], p[1] - q[1]) * mpp
            if FENCE_GAP_M < d <= FENCE_BRIDGE_M and (i != j or len(lines[i]) > 3):
                draw.line([p, q], fill=1, width=width)
    return np.array(canvas, bool)


def _palette_dist(px, palette, mix=(-1,)):
    """How far each colour of px (n, 3) is from the colours of the palette and from their mixtures with the
    ones at the indices `mix` (default the last one, the green of stripes and planted rows: a blurred picture
    mixes the stripes of a pen with the fill between them; the white of the paper: the soft edge of a line).
    Not any two: yellow and blue mixed would let the emblem in the corner of a sheet through."""
    p = np.asarray(px, float)
    pal = np.asarray(palette, float)
    best = np.sqrt(((p[:, None] - pal[None]) ** 2).sum(-1)).min(1)
    for b in sorted({m % len(pal) for m in mix}):
        for a in range(len(pal)):
            if a == b:
                continue
            d = pal[b] - pal[a]
            t = np.clip(((p - pal[a]) @ d) / max(d @ d, 1e-9), 0, 1)
            best = np.minimum(best, np.sqrt(((p - pal[a] - t[:, None] * d) ** 2).sum(-1)))
    return best


def _drawn(part, lines):
    """The ground closed in by the drawn lines (no gaps closed) that overlaps `part` (a ground found with its gaps
    closed), joined to it; `part` alone where the lines leave it open. All in one cut-out. A line is joined
    across a pixel or two first (its antialiased edge or a contour drawn over it breaks it)."""
    for r in (1, 2):
        joined = ndi.binary_closing(np.pad(lines, r + 1), _disk(r))[r + 1:-r - 1, r + 1:-r - 1]
        inside = ndi.binary_fill_holes(joined) & ~joined
        lab, n = ndi.label(inside)
        ids = np.unique(lab[part & inside]) if n else np.zeros(0, int)
        ids = ids[ids > 0]
        if not len(ids):
            continue
        fine = np.isin(lab, ids)
        # only what the lines close in near the ground found: a hole of the lines that reaches far beyond it
        # is another ground the closing cut off (two pens side by side), not this one
        if fine.sum() > 2.0 * part.sum() + 50 or fine.sum() < 0.5 * part.sum():
            continue
        return part | fine
    return part


def _ring(mask, pts, r, n=64):
    """What of a mask lies on the circle of radius r px around each point (u, v): booleans (len(pts), n),
    and the angles of the n samples."""
    H, W = mask.shape
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    p = np.asarray(pts, float).reshape(-1, 2)
    uu = np.round(p[:, :1] + r * np.cos(ang)[None]).astype(int)
    vv = np.round(p[:, 1:] + r * np.sin(ang)[None]).astype(int)
    ok = (uu >= 0) & (uu < W) & (vv >= 0) & (vv < H)
    return mask[np.clip(vv, 0, H - 1), np.clip(uu, 0, W - 1)] & ok, ang


def _arc_angles(on, ang):
    """The middle angle of every arc of one row of _ring()."""
    n = len(on)
    if on.all() or not on.any():
        return []
    start = int(np.nonzero(on & ~np.roll(on, 1))[0][0])
    on, ang = np.roll(on, -start), np.roll(ang, -start)
    out, k = [], 0
    while k < n:
        if on[k]:
            j = k
            while j + 1 < n and on[j + 1]:
                j += 1
            out.append(float(np.angle(np.exp(1j * ang[k:j + 1]).mean())))
            k = j + 1
        else:
            k += 1
    return out


def _ticks(thin, mpp):
    """The ticks of the black lines of a mask: short strokes that stand out of a line that runs on to both
    sides of them. [dict(tip=(u, v), foot=(u, v), along=(du, dv) unit vector of the line at the foot, len_m)].

    The tip of a tick is where a thin black stroke ends (one narrow arc of black on a small circle around
    it). On larger circles it stays one arc for the length of the tick, and then the circle cuts the line
    the tick stands on in two places, both on the far side of the tick. The end of a path sees no second
    arc; the end of a dash sees the next dash, but straight ahead, opposite to the dash itself."""
    r1 = max(2, int(round(TICK_TIP_M / mpp)))
    vs, us = np.nonzero(thin)
    tip = np.zeros(thin.shape, bool)
    for a in range(0, len(us), 200000):
        on, _ = _ring(thin, np.c_[us[a:a + 200000], vs[a:a + 200000]], r1)
        one = ((on & ~np.roll(on, 1, axis=1)).sum(1) == 1) & (on.mean(1) <= TICK_ARC)
        tip[vs[a:a + 200000][one], us[a:a + 200000][one]] = True
    lab, n = ndi.label(tip, structure=np.ones((3, 3)))
    if not n:
        return []
    tips = np.array([(u, v) for v, u in ndi.center_of_mass(tip, lab, range(1, n + 1))]).round()
    radii = np.arange(r1 + 1, int((TICK_M[1] + 1.0) / mpp) + 2)
    arcs = np.stack([(lambda on: (on & ~np.roll(on, 1, axis=1)).sum(1))(_ring(thin, tips, r)[0]) for r in radii])
    first = np.where((arcs >= 2).any(0), (arcs >= 2).argmax(0), -1)
    out = []
    for k in np.nonzero(first >= 0)[0]:
        length = radii[first[k]] * mpp
        if not TICK_M[0] <= length <= TICK_M[1] or (arcs[:first[k], k] != 1).any():
            continue
        back = _arc_angles(*(lambda r: (r[0][0], r[1]))(_ring(thin, tips[k], r1)))
        R = radii[first[k]] + TICK_BEYOND_M / mpp
        on, ang = _ring(thin, tips[k], R)
        two = _arc_angles(on[0], ang)
        if len(back) != 1 or len(two) != 2:
            continue
        # seen from the tip the line lies ahead, to both sides of the way the tick points (a tick may lean)
        apart = abs((two[0] - two[1] + np.pi) % (2 * np.pi) - np.pi)
        ahead = float(np.angle(np.exp(1j * two[0]) + np.exp(1j * two[1])))
        lean = abs((ahead - back[0] + np.pi) % (2 * np.pi) - np.pi)
        if not np.radians(40) <= apart <= np.radians(150) or lean > np.radians(TICK_LEAN_DEG):
            continue        # the next dash straight ahead (the arcs lie opposite each other), the arms of a V
        p1, p2 = (tips[k] + R * np.array([np.cos(a), np.sin(a)]) for a in two)
        along = (p2 - p1) / max(np.hypot(*(p2 - p1)), 1e-9)
        foot = p1 + along * float((tips[k] - p1) @ along)
        # a bar across the line (a sleeper of a railway, a bar of a power line) goes on beyond the line
        u, v = (2 * foot - tips[k]).round().astype(int)
        q = max(1, int(round(1.2 / mpp)))
        if thin[max(v - q, 0):v + q + 1, max(u - q, 0):u + q + 1].any():
            continue
        out.append(dict(tip=tuple(tips[k]), foot=tuple(foot), along=tuple(along), len_m=float(length)))
    return out


def fences(rgb, cls, mpp, high=None):
    """(mask of the fences of the map: their lines with the ticks; [[(u, v), ...]] the feet of the ticks of
    every fence, in a row).

    A fence (ISOM 516, 518; the same goes for a wall or a cliff drawn with tags) is a continuous black line
    with short ticks to one side. Read as: at least FENCE_ROW ticks (_ticks) on the same side of one
    continuous line, each no farther than FENCE_TICK_GAP_M from the next. A dashed path has no ticks, the
    branches of a path are longer than a tick, the sleepers of a railway and the bars of a power line stand
    out to both sides, contours and their slope lines are brown, and the print around the map is grey.
    Whether the fence closes anything in does not matter here (enclosures() reads the ground inside).
    high: a list to fill with the indices (in the list returned) of the impassable fences (ISOM 518, in ISOM
    2000 524 "high fence"): ticks in pairs, two on the same side TICK_PAIR_M apart, at least HIGH_PAIRS pairs
    making HIGH_SHARE of the ticks of the fence."""
    H, W = cls.shape
    im = rgb.astype(np.int32)
    dark = (im.sum(-1) < 330) & (im.max(-1) - im.min(-1) < 45)
    thin = dark & ~ndi.binary_opening(dark, _disk(max(2, int(3.0 / mpp))))        # not the solid black of buildings
    ink = symbols.colours(rgb)["black"]
    ticks = [t for t in _ticks(thin, mpp)
             if cls[int(t["tip"][1]), int(t["tip"][0])] != T.OOB or cls[int(np.clip(t["foot"][1], 0, H - 1)),
                                                                          int(np.clip(t["foot"][0], 0, W - 1))] != T.OOB]
    mask = np.zeros((H, W), bool)
    if len(ticks) < FENCE_ROW:
        return mask, []
    near = _grow(thin, max(1.0, 1.5 / mpp))
    feet = np.array([t["foot"] for t in ticks])
    tip = np.array([t["tip"] for t in ticks])
    along = np.array([t["along"] for t in ticks])
    side = np.sign(along[:, 0] * (tip - feet)[:, 1] - along[:, 1] * (tip - feet)[:, 0])
    d = np.hypot(*(feet[:, None] - feet[None]).transpose(2, 0, 1)) * mpp
    # a bar across the line (sleeper, power line) has a tick on either side of the same foot: neither counts
    turn = np.sign(along @ along.T)
    twin = ((d <= TICK_TWIN_M) & (side[:, None] * side[None] * turn < 0)).any(1)
    link = np.zeros(d.shape, bool)
    for i, j in zip(*np.nonzero(np.triu((d > 0) & (d <= FENCE_TICK_GAP_M), 1))):
        if twin[i] or twin[j] or abs(along[i] @ along[j]) < np.cos(np.radians(FENCE_BEND_DEG)) \
                or side[i] * side[j] * turn[i, j] <= 0:
            continue
        # ... and the line runs on between the two feet, along the direction of both
        step = (feet[j] - feet[i]) / max(d[i, j] / mpp, 1e-9)
        if abs(step @ along[i]) < np.cos(np.radians(FENCE_BEND_DEG)):
            continue
        q = feet[i] + np.arange(0, d[i, j] / mpp + 1)[:, None] * step[None]
        qu, qv = np.clip(q[:, 0].round().astype(int), 0, W - 1), np.clip(q[:, 1].round().astype(int), 0, H - 1)
        link[i, j] = link[j, i] = near[qv, qu].mean() >= 0.95
    # of several ticks ahead only the nearest on either side along the line is the next one
    from scipy.sparse.csgraph import connected_components
    n, row = connected_components(link, directed=False)
    from PIL import Image, ImageDraw
    canvas = Image.new("1", (W, H), 0)
    draw = ImageDraw.Draw(canvas)
    width = max(3, int(round(2 * FENCE_HALF_M / mpp)))
    found = []
    for r in range(n):
        idx = np.nonzero(row == r)[0]
        if len(idx) < FENCE_ROW:
            continue
        order = idx[np.argsort((feet[idx] - feet[idx[0]]) @ along[idx[0]])]
        if ink[np.clip(feet[order, 1].round().astype(int), 0, H - 1),
               np.clip(feet[order, 0].round().astype(int), 0, W - 1)].mean() < 0.5 and _inked(near, ink)[
                int(np.clip(feet[order[0], 1], 0, H - 1)), int(np.clip(feet[order[0], 0], 0, W - 1))] == 0:
            continue        # grey print around the map
        line = [tuple(feet[k]) for k in order]
        # the fence goes on beyond its last ticks for as long as the line runs straight on, up to half a gap
        for end, sign in ((0, -1.0), (-1, 1.0)):
            k = order[end]
            way = along[k] * sign * (1.0 if (feet[order[-1]] - feet[order[0]]) @ along[k] >= 0 else -1.0)
            reach = 0
            for s in range(1, int(FENCE_TICK_GAP_M / 2 / mpp)):
                u, v = (feet[k] + way * s).round().astype(int)
                if not (0 <= u < W and 0 <= v < H) or not near[v, u]:
                    break
                reach = s
            line.insert(0, tuple(feet[k] + way * reach)) if end == 0 else line.append(tuple(feet[k] + way * reach))
        draw.line(line, fill=1, width=width)
        for k in order:
            draw.line([tuple(tip[k]), tuple(feet[k])], fill=1, width=width)
        if high is not None:
            # ticks two by two: a short gap with gaps at least PAIR_APART times as long before and after it (on a
            # sprint map the ticks of any fence are a few metres apart, but evenly)
            gaps = [float(d[a_, b_]) for a_, b_ in zip(order[:-1], order[1:])]
            pairs = 0
            for k, gk in enumerate(gaps):
                a_, b_ = order[k], order[k + 1]
                if gk > TICK_PAIR_M or side[a_] * side[b_] * turn[a_, b_] <= 0:
                    continue
                if all(gaps[q] >= PAIR_APART * gk for q in (k - 1, k + 1) if 0 <= q < len(gaps)):
                    pairs += 1
            # (the fence of an area that must not be entered, ticks into the olive, is closed off by that area)
            into_oob = np.mean([cls[int(np.clip(tip[k][1], 0, H - 1)), int(np.clip(tip[k][0], 0, W - 1))] == T.OOB
                                for k in order])
            if pairs >= HIGH_PAIRS and 2 * pairs >= HIGH_SHARE * len(order) and into_oob < 0.5:
                high.append(len(found))
        found.append(line)
    mask = np.array(canvas, bool) & _grow(thin, 1.0)
    return mask, found


def out_of_bounds(rgb, cls, mpp):
    """The areas of the map that must not be entered (ISOM 520, olive): not the margin of the sheet, which
    the terrain classes also give as out of bounds, and not specks of olive in the edge of a brown line."""
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    olive = (cls == T.OOB) & (r > 120) & (r < 200) & (g > 140) & (g < 200) & (b < 90)
    return _open(olive, max(1, int(3 * T.REF_M_PER_PX / mpp + 0.5)))


def layers(cls, blue, mpp, rgb=None, fenced=None, pens=None, fence_line=None, walls=None):
    """The masks of a cut-out of the map that the features are read from, made once per control:
    path, fence (fenced ground, see enclosures), fence_line (the fences that close nothing in, see fences),
    stream, water, ponds, houses, open_big, settlement (booleans), open
    (labels of the patches of open land, with open_size in m2 and open_cut = it goes on beyond the cut-out),
    pens. fenced, pens: what enclosures() gave for this cut-out, when the caller has read the whole map;
    fence_line: what fences() gave for it (a fence is no path, and where it meets one there is no junction).
    walls: the impassable walls of a sprint map (mapdata.obstacles): buildings in cls, but no house to name."""
    s = T.REF_M_PER_PX / mpp
    px = lambda n: max(1, int(n * s + 0.5))
    H, W = cls.shape
    edge = np.zeros((H, W), bool)
    edge[[0, -1], :] = edge[:, [0, -1]] = True
    # the dashes of a track are drawn with gaps: joined, so that the track is one line and has no ends in it
    black = cls == T.PATH
    lines = _long(black | _close(black, px(3)), MIN_LINE_M / mpp)
    ink = symbols.colours(rgb)["black"] if rgb is not None else None
    if ink is not None:
        lines &= _inked(lines, ink)
    if fenced is None:
        fenced, pens = enclosures(rgb, cls, mpp) if rgb is not None else (np.zeros((H, W), bool), [])
    fence = fenced
    if fence_line is None:
        fence_line = np.zeros((H, W), bool)
    off = fence | fence_line
    path = _long(lines & ~off, MIN_LINE_M / mpp) if off.any() else lines
    water = cls == T.WATER
    ponds = _grow(_open(water, max(1, int(POND_WIDE_M / mpp / 2))), px(3)) & water
    stream = _long(blue & ~_grow(ponds, px(2)), MIN_LINE_M / mpp)
    # open land; a path through it does not cut it in two and is not its edge: the black of a path belongs
    # to the land it runs through or along
    land = (cls == T.OPEN) | (cls == T.ROUGH_OPEN)
    if rgb is not None:
        # a paved road or yard (ISOM 501, 502: light brown) is run like open land but is none: its black edge
        # is a line of its own
        land &= ~T.paved(rgb)
    if land.any() and black.any():
        land |= black & _grow(land, px(6))      # 8 m: also the middle of a wide junction
    lab, n = ndi.label(land)
    size = np.bincount(lab.ravel(), minlength=n + 1) * mpp * mpp
    cut = np.zeros(n + 1, bool)
    cut[np.unique(lab[edge])] = True
    big = (size >= OPEN_EDGE_M2) | (cut & (size >= OPEN_EDGE_M2 / 2))
    big[0] = False
    settlement = np.zeros((H, W), bool)
    if rgb is not None:
        slab, m = ndi.label(out_of_bounds(rgb, cls, mpp))
        ssize = np.bincount(slab.ravel(), minlength=m + 1) * mpp * mpp
        ssize[0] = 0
        settlement = (ssize >= SETTLEMENT_M2)[slab]
    houses = cls == T.BUILDING
    if walls is not None and walls.any():
        houses &= ~ndi.binary_dilation(walls, iterations=2)
    if ink is not None:
        houses = _inked(houses, ink)
    return dict(edge=edge, path=path, fence=fence, fence_line=fence_line, pens=pens, stream=stream, water=water,
                ponds=ponds, ink=ink,
                houses=houses,
                open=lab, open_size=size, open_cut=cut, open_big=big[lab], settlement=settlement)


def _inked(mask, ink):
    """The patches of a mask that have the black of the map in them (ink: symbols.colours(...)["black"])."""
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if not n:
        return mask
    size = np.bincount(lab.ravel(), minlength=n + 1)
    share = np.bincount(lab.ravel(), weights=ink.ravel(), minlength=n + 1) / np.maximum(size, 1)
    share[0] = 0.0
    return (share >= INK_SHARE)[lab]


def _path_ends(path, cls, fence, mpp, px):
    """Where a long path stops: [(u, v)]. Not where it only leaves the cut-out, runs into a fence or an area
    that must not be entered, or is interrupted and goes on a few metres further."""
    H, W = path.shape
    vs, us = np.nonzero(path)
    if not len(us):
        return []
    pts = np.c_[us, vs]
    r1, r2 = px(7), BRANCH_M / mpp
    one = (_arcs(path, pts, r1) == 1) & (_arcs(path, pts, r2) == 1)
    ends = np.zeros((H, W), bool)
    ends[vs[one], us[one]] = True
    lab, n = ndi.label(ends, structure=np.ones((3, 3)))
    gap = int(r1 + END_GAP_M / mpp)
    off = _grow(fence, px(6)) | _grow(cls == T.OOB, px(5))
    out = []
    for v, u in ndi.center_of_mass(ends, lab, range(1, n + 1)) if n else []:
        ui, vi = int(round(u)), int(round(v))
        if min(ui, vi, W - 1 - ui, H - 1 - vi) <= r2 + 2 or off[vi, ui]:
            continue
        a, b = max(vi - gap, 0), max(ui - gap, 0)
        yy, xx = np.mgrid[a:min(vi + gap + 1, H), b:min(ui + gap + 1, W)]
        # any black line counts here, also a piece too short to be a path of its own (one dash of a track)
        around = (path | (cls == T.PATH))[a:vi + gap + 1, b:ui + gap + 1] & ((xx - ui) ** 2 + (yy - vi) ** 2 <= gap * gap)
        if ndi.label(around, structure=np.ones((3, 3)))[1] == 1:      # no other piece of path right ahead
            out.append((float(u), float(v)))
    return out


def candidates(cls, blue, height, mpp, ctrl, source="aws", rgb=None, found=(), L=None):
    """Everything around a control that could be a catching feature: [dict(kind, px=(u, v), size)].
    cls, blue, height, rgb: a cut-out of the map (terrain classes, stream_mask, heights, the picture) with the
    control at ctrl = (u, v) in its pixels; found: the point symbols in it (oroute.symbols.find, px in the
    cut-out); L: its layers() when the caller has them. Nothing is ranked or left out by distance here."""
    s = T.REF_M_PER_PX / mpp
    px = lambda n: max(1, int(n * s + 0.5))
    H, W = cls.shape
    L = L or layers(cls, blue, mpp, rgb)
    edge, path = L["edge"], L["path"]
    out = []

    # paths: junctions whose arms all go on, ends, and the path itself as a line
    js = junctions(path, ring=px(7))
    for (u, v), far in zip(js, _arcs(path, js, BRANCH_M / mpp)):
        if far >= 3:
            out.append(dict(kind="junction", px=(u, v), size=int(far)))
    for p in _path_ends(path, cls, L["fence"], mpp, px):
        out.append(dict(kind="path_end", px=p, size=0))
    p = _nearest(path, ctrl)
    if p:
        out.append(dict(kind="path", px=p, size=0))

    # the ground a fence closes in
    for u, v, area in L["pens"]:
        out.append(dict(kind="enclosure", px=(u, v), size=area))

    # water: the long blue lines of the picture are streams (the dashes of a marsh are short and stay out);
    # where a path crosses a stream is a point
    stream = L["stream"]
    p = _nearest(stream, ctrl)
    if p:
        out.append(dict(kind="stream", px=p, size=0))
    lab, n = ndi.label(_grow(stream, px(2)) & _grow(path, px(1)))
    for v, u in ndi.center_of_mass(lab > 0, lab, range(1, n + 1)) if n else []:
        out.append(dict(kind="stream_path", px=(float(u), float(v)), size=0))

    # buildings and ponds: solid blobs that lie whole inside the cut-out
    for mask, kind, lo, hi in ((L["houses"], "building", BUILDING_M2, np.inf), (L["ponds"], "pond", *POND_M2)):
        lab, n = ndi.label(mask)
        for k, sl in enumerate(ndi.find_objects(lab), 1):
            part = lab[sl] == k
            area = float(part.sum()) * mpp * mpp
            if lo <= area <= hi and not edge[sl][part].any():
                v, u = ndi.center_of_mass(part)
                out.append(dict(kind=kind, px=(u + sl[1].start, v + sl[0].start), size=area))

    # open land: a small compact patch alone in the forest is a clearing (a point), a large one has an edge
    # to hit. What lies between (the pieces of a mosaic of half-open land) is no place one could name.
    lab, at = L["open"], (int(np.clip(round(ctrl[1]), 0, H - 1)), int(np.clip(round(ctrl[0]), 0, W - 1)))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        area = L["open_size"][k]
        if area < CLEARING_M2[0]:
            continue
        part = lab[sl] == k
        compact = part.mean() >= 0.4 and min(part.shape) >= 0.35 * max(part.shape)
        if area <= CLEARING_M2[1] and compact and not L["open_cut"][k]:
            v, u = ndi.center_of_mass(part)
            out.append(dict(kind="clearing", px=(u + sl[1].start, v + sl[0].start), size=area))
        elif area >= OPEN_EDGE_M2 or (L["open_cut"][k] and area >= OPEN_EDGE_M2 / 2):
            whole = lab == k
            # the control stands in it: its edge is where it ends, seen from inside
            p = _nearest(~whole & ~edge if whole[at] else whole, ctrl)
            if p:
                out.append(dict(kind="open_edge", px=p, size=area))
    p = _nearest(L["settlement"], ctrl)
    if p:
        out.append(dict(kind="settlement", px=p, size=0))

    # hilltops from the elevation: a local top with everything around it clearly lower
    r = HILLTOP_RING_M / mpp
    drop = HILLTOP_DROP_M.get(source, HILLTOP_DROP_M["aws"])
    step = px(3)
    low = height[::step, ::step]
    top = (low == ndi.maximum_filter(low, footprint=_disk(max(1, int(r / step)))))
    ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    for vv, uu in zip(*np.nonzero(top)):
        u, v = uu * step, vv * step
        ru, rv = np.round(u + r * np.cos(ang)).astype(int), np.round(v + r * np.sin(ang)).astype(int)
        if ru.min() < 0 or rv.min() < 0 or ru.max() >= W or rv.max() >= H:
            continue
        ring = height[rv, ru]
        if (ring <= height[v, u] - drop).all():
            out.append(dict(kind="hilltop", px=(float(u), float(v)), size=float(height[v, u] - ring.max())))
    # several finds of one kind next to each other (the arms of a wide junction, a stream crossed twice by a
    # winding path) are one feature: the first one stays
    kept = []
    for f in out:
        if not any(g["kind"] == f["kind"] and f["kind"] in POINTS and
                   math.hypot(f["px"][0] - g["px"][0], f["px"][1] - g["px"][1]) * mpp < SAME_M for g in kept):
            kept.append(f)
    # the point symbols of the map, each as it stands (two knolls 15 m apart are two knolls)
    return kept + [dict(kind=f["kind"], px=(float(f["px"][0]), float(f["px"][1])), size=max(f["size"]))
                   for f in found if f["kind"] in SYMBOLS]


def bearing(du, dv):
    """Bearing in degrees (0 = up in the picture, clockwise) of a step in map pixels. What a compass shows is
    this less the angle of the north lines (north_bearings, at the output)."""
    return math.degrees(math.atan2(du, -dv)) % 360.0


BEARING_KEYS = ("az", "back_az", "first_az", "caz", "az_off")


def north_bearings(obj, north_deg):
    """The bearings of a result (every key of BEARING_KEYS, in dicts and lists at any depth) turned from up in the
    picture to the north of the map: its north lines lean by north_deg (terrain.north_lines) on a map that is
    turned in its picture. In place; returns obj."""
    if not north_deg:
        return obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BEARING_KEYS and isinstance(v, (int, float)) and v is not None:
                obj[k] = round((v - north_deg) % 360.0, 1)
            else:
                north_bearings(v, north_deg)
    elif isinstance(obj, list):
        for v in obj:
            north_bearings(v, north_deg)
    return obj


def _apart(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _place(f, height, mpp, ctrl):
    """Where a feature lies seen from the control: adds dist (m), az (its bearing from the control), back_az
    (the bearing to run from it to the control) and dh (the control is this much higher)."""
    H, W = height.shape
    at = lambda p: height[int(np.clip(round(p[1]), 0, H - 1)), int(np.clip(round(p[0]), 0, W - 1))]
    du, dv = f["px"][0] - ctrl[0], f["px"][1] - ctrl[1]
    f.update(dist=math.hypot(du, dv) * mpp, az=bearing(du, dv), dh=float(at(ctrl) - at(f["px"])))
    f["back_az"] = (f["az"] + 180.0) % 360.0
    return f


def _simplify(pts, tol):
    """A polyline with the points left out that lie within tol of the line through their neighbours
    (Douglas-Peucker)."""
    pts = [tuple(p) for p in pts]
    keep = [0, len(pts) - 1]
    todo = [(0, len(pts) - 1)]
    while todo:
        a, b = todo.pop()
        if b - a < 2:
            continue
        q = np.asarray(pts[a + 1:b], float)
        p0, d = np.asarray(pts[a], float), np.asarray(pts[b], float) - np.asarray(pts[a], float)
        t = np.clip(((q - p0) @ d) / max(float(d @ d), 1e-9), 0, 1)
        off = np.hypot(*(q - p0 - t[:, None] * d).T)
        k = int(np.argmax(off))
        if off[k] > tol:
            keep.append(a + 1 + k)
            todo += [(a, a + 1 + k), (a + 1 + k, b)]
    return [pts[i] for i in sorted(keep)]


def describe(cands, cls, height, mpp, ctrl, model, barriers=None, step=2):
    """Distance, bearings, height difference (_place) and reachability of every candidate: ok = the control
    can reasonably be reached from it.

    A feature with something one cannot go through on the straight line to the control (fenced ground, a
    forbidden line or area, water, an area out of bounds; WALL_M of the line in it) is no help with a
    straight bearing: it is left out (ok = False, barred = True) when the shortest way round is more than
    DIRECT_DETOUR times the straight distance, and else gets that way round: via (the line in pixels, from
    the feature to the control), walk (its length in metres) and first_az (the bearing to set off on).
    Fenced ground and a pond are come to at their edge: such a feature is moved from its middle to where the
    straight line from the control meets it (edge = True), with the distance and the bearing of that place."""
    grid = Grid(cls, height, mpp, model, step=step, barriers=barriers)
    Hc, Wc = grid.shape
    r, c = grid.nearest_passable(*grid.to_cell(*ctrl))
    home = r * Wc + c
    cost = dijkstra(grid.G.T.tocsr(), indices=home)        # seconds from every cell to the control
    # what one cannot go through (a house is walked round without a thought and is not in it), piece by piece
    wall, _ = ndi.label(~np.isfinite(grid.base) & (grid.cls != T.BUILDING), structure=np.ones((3, 3)))
    cell = lambda p: (int(np.clip(round((p[1] - grid.v0) / grid.step - 0.5), 0, Hc - 1)),
                      int(np.clip(round((p[0] - grid.u0) / grid.step - 0.5), 0, Wc - 1)))

    def line(a, b):
        """The pieces of wall under the straight line from a to b (map pixels), sample by sample, the
        samples themselves and the metres from one to the next."""
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (0.5 * grid.step)) + 1)
        q = np.c_[np.linspace(a[0], b[0], n), np.linspace(a[1], b[1], n)]
        rows = np.clip(np.round((q[:, 1] - grid.v0) / grid.step - 0.5).astype(int), 0, Hc - 1)
        cols = np.clip(np.round((q[:, 0] - grid.u0) / grid.step - 0.5).astype(int), 0, Wc - 1)
        return wall[rows, cols], q, math.hypot(b[0] - a[0], b[1] - a[1]) * mpp / (n - 1)
    # the shortest way to the control that keeps out of everything impassable, from every cell: in metres,
    # not in seconds (the fastest way may take a path far round; what counts here is how far round one has to go)
    e = grid.G.tocoo()
    hop = grid.cell * np.hypot(e.row // Wc - e.col // Wc, e.row % Wc - e.col % Wc)
    far, nxt = dijkstra(csr_matrix((hop, (e.col, e.row)), shape=e.shape), indices=home, return_predecessors=True)
    for f in cands:
        mine = wall[cell(f["px"])]          # the piece of wall the feature itself is (a pond, fenced ground), or 0
        if f["kind"] in EDGE_KINDS and mine:
            under, q, _ = line(ctrl, f["px"])
            first = np.nonzero(under == mine)[0]
            if len(first):
                f.update(px=(float(q[first[0], 0]), float(q[first[0], 1])), edge=True)
        _place(f, height, mpp, ctrl)
        fr, fc = grid.nearest_passable(*grid.to_cell(*f["px"]))
        moved = math.hypot(fr - grid.to_cell(*f["px"])[0], fc - grid.to_cell(*f["px"])[1]) * grid.cell
        straight = f["dist"] / (model.v_flat * model.factors[T.FOREST])
        # a building, a pond, a settlement or fenced ground is come to from its edge; anything else that lies
        # in the impassable is no help
        inside_ok = (f["kind"] in ("building", "pond", "settlement") and moved <= 40.0) or \
            (f["kind"] == "enclosure" and moved <= 70.0)
        f["ok"] = bool(np.isfinite(cost[fr * Wc + fc]) and cost[fr * Wc + fc] <= DETOUR * straight + DETOUR_S
                       and (moved <= 2 * grid.cell or inside_ok))
        if not f["ok"]:
            continue
        under, _, each = line(f["px"], ctrl)
        if ((under > 0) & (under != mine)).sum() * each < WALL_M:
            continue
        way, i = [], fr * Wc + fc
        while i != home and i >= 0 and len(way) <= Hc * Wc:
            way.append(grid.to_px(i // Wc, i % Wc))
            i = int(nxt[i])
        if i != home:
            f.update(ok=False, barred=True)
            continue
        way = _simplify([tuple(f["px"])] + way + [tuple(ctrl)], VIA_TOL_M / mpp)
        steps = np.hypot(*np.diff(np.asarray(way, float), axis=0).T) * mpp
        walk = float(steps.sum())
        if walk > DIRECT_DETOUR * f["dist"]:
            f.update(ok=False, barred=True)
            continue
        if walk < VIA_MIN * f["dist"]:
            continue
        # the bearing to set off on: to where the way round is FIRST_M on
        along = np.r_[0, np.cumsum(steps)]
        at = min(FIRST_M, walk)
        to = (float(np.interp(at, along, [p[0] for p in way])), float(np.interp(at, along, [p[1] for p in way])))
        f.update(via=way, walk=walk, first_az=bearing(to[0] - f["px"][0], to[1] - f["px"][1]))
    return cands


def way_in(route, ctrl, mpp, back_m=APPROACH_M):
    """(bearing from the control back along the best route, the last stretch of that route in pixels).
    route: the best route of the leg as [(u, v), ...] ending at the control. The bearing is to where the route
    is back_m before the control (APPROACH_M: a last bend round a thicket does not turn it); None when the
    route is too short to have a direction."""
    q = [tuple(p) for p in route] + [tuple(ctrl)]
    left, back, tail = 0.0, None, [q[-1]]
    for a, b in zip(q[-2::-1], q[:0:-1]):
        step = math.hypot(a[0] - b[0], a[1] - b[1]) * mpp
        if back is None and left + step >= back_m:
            t = (back_m - left) / max(step, 1e-9)
            back = (b[0] + t * (a[0] - b[0]), b[1] + t * (a[1] - b[1]))
        left += step
        tail.append(a)
        if left >= ATTACK_HI + 50.0:
            break
    back = back or q[0]
    if math.hypot(back[0] - ctrl[0], back[1] - ctrl[1]) * mpp < 5.0:
        return None, tail
    return bearing(back[0] - ctrl[0], back[1] - ctrl[1]), tail


def choose(cands, approach_az, mpp, route=None, prev=None, leg_m=None):
    """(features, attack point): MIN..MAX_FEATURES catching features spread around the control, best first,
    and the point to attack the control from (on the way in), or None. cands: describe()d candidates;
    approach_az: bearing from the control back to where the leg comes from; route: the last stretch of the
    best route in pixels (way_in), when there is one; prev, leg_m: the control before (or the start) in the
    same pixels and the straight length of the leg. With them the attack point has to lie inside the leg: a
    point 135 m before a control 120 m from the last one is at the last control, not before this one."""
    apart_m = lambda f, g: math.hypot(f["px"][0] - g["px"][0], f["px"][1] - g["px"][1]) * mpp

    def score(f):
        d = f["dist"]
        # (the edge of fenced ground or of a pond is not "too near" at 20 m as a point is: it is large)
        close = 1.0 if f.get("edge") and d >= EDGE_NEAR_M else 0.6 + 0.4 * min(1.0, max(0.0, d - NEAR_M) / 15.0)
        near = close if d < 45 else 1.0 if d <= 110 else max(0.6, 1.0 - 0.4 * (d - 110) / 40.0)
        lone = 0.6 if f["crowd"] >= CROWD else 1.0     # one house of a village, one knoll of a field of knolls
        return BASE[f["kind"]] * near * lone * (1.25 if _apart(f["az"], approach_az) <= ATTACK_DEG else 1.0)
    # (what is come to at its edge may lie as near as a line may: "fenced ground 25 m east of the control")
    ok = [f for f in cands if f["ok"] and (NEAR_M if f["kind"] in POINTS and not f.get("edge") else LINE_NEAR_M)
          <= f["dist"] <= ATTACK_HI]
    # where the nearest point of a path is its end, the end says it all
    ends = [f for f in ok if f["kind"] == "path_end"]
    ok = [f for f in ok if not (f["kind"] == "path" and any(apart_m(f, e) < SAME_M for e in ends))]
    for f in ok:
        f["crowd"] = sum(g["kind"] == f["kind"] and g is not f and apart_m(f, g) <= CROWD_M for g in cands) \
            if f["kind"] == "building" or f["kind"] in SYMBOLS else 0
        f["score"] = score(f)
    pool = [f for f in ok if f["dist"] <= RADIUS_M]
    picked = []
    while len(picked) < MAX_FEATURES:
        def worth(f):
            w = f["score"]
            for g in picked:
                if _apart(f["az"], g["az"]) < APART_DEG and (f["kind"] in POINTS) == (g["kind"] in POINTS):
                    # two points (or two lines) in the same direction: of one kind the second says nothing new,
                    # of another kind only when it lies clearly nearer or farther. A line and a point in one
                    # direction both stay (the road, and the junction on it).
                    w *= 0.0 if g["kind"] == f["kind"] else 0.45 if abs(f["dist"] - g["dist"]) < 40.0 else 0.8
            if sum(g["kind"] == f["kind"] for g in picked) >= 2:
                w *= 0.6
            return w
        rest = [f for f in pool if all(f is not g for g in picked)]
        best = max(rest, key=worth, default=None)
        if best is None or worth(best) < MIN_SCORE:
            break
        picked.append(best)
    if len(picked) < MIN_FEATURES:
        picked = picked if picked and picked[0]["score"] >= 2 * MIN_SCORE else []
    # the attack point: a point before the control, best of all one the best route passes
    on_route = lambda f: route is not None and _to_line(f["px"], route) * mpp <= ON_ROUTE_M \
        and _apart(f["az"], approach_az) <= 110.0
    in_leg = lambda f: prev is None or leg_m is None or (
        f["dist"] <= ATTACK_LEG_SHARE * leg_m
        and math.hypot(f["px"][0] - prev[0], f["px"][1] - prev[1]) * mpp >= ATTACK_FROM_PREV_M)
    before = [f for f in ok if f["kind"] in POINTS and f["score"] >= MIN_SCORE and in_leg(f)
              and (on_route(f) or _apart(f["az"], approach_az) <= ATTACK_DEG)]
    if leg_m is not None and leg_m < ATTACK_MIN_LEG_M:
        before = []
    attack = max(before, key=lambda f: (on_route(f), f["score"], -f["dist"]), default=None)
    return picked, attack


def _runs_along(mask, at, az, mpp, ctrl=None):
    """Whether the line of a mask through pixel at = (u, v) runs along bearing az (within ALONG_DEG of it):
    the main direction of the mask pixels up to ALONG_M around. A junction or a bend has none. With ctrl (the
    control), only a line that, drawn on straight, passes within ALONG_NEAR_M of the control: the path one came
    by going on. A path that runs nearly the same way 30 m to the side lies across the way of whoever overran."""
    r = max(3, int(ALONG_M / mpp))
    u, v = int(at[0]), int(at[1])
    v0, u0 = max(v - r, 0), max(u - r, 0)
    vs, us = np.nonzero(mask[v0:v + r + 1, u0:u + r + 1])
    x = np.c_[us + u0 - u, vs + v0 - v].astype(float)
    x = x[(x ** 2).sum(1) <= r * r]
    if len(x) < 3:
        return False
    x -= x.mean(0)
    w, vec = np.linalg.eigh(x.T @ x)
    if w[0] > 0.25 * w[1]:
        return False
    if abs((bearing(vec[0, 1], vec[1, 1]) - az + 90.0) % 180.0 - 90.0) >= ALONG_DEG:
        return False
    if ctrl is None:
        return True
    d = np.array([vec[0, 1], vec[1, 1]])
    off = np.array([ctrl[0] - at[0], ctrl[1] - at[1]], float)
    return abs(off[0] * d[1] - off[1] * d[0]) * mpp <= ALONG_NEAR_M


def beyond(L, cands, ctrl, travel_az, mpp):
    """What a runner who ran on past the control runs into: on rays from the control, BEYOND_STEP apart up to
    BEYOND_FAN to either side of the direction of travel, the first of BACKSTOPS within BEYOND_M (of two
    within STOP_SAME_M of each other the one earlier in BACKSTOPS). Straight on,
    a path or stream that runs along the ray is passed over: that is the path one came by going on, not a
    line across the way. The rays to the left, straight on and to the right are three parts; a part counts
    when at least half of its rays meet the same kind of thing.
    Returns dict(parts=[dict(side, kind, px=(u, v) of the middle one of those rays, line=[(u, v), ...] where
    they met it)]) or None. L: layers() of the cut-out, cands: its candidates (for the clearings)."""
    H, W = L["path"].shape
    rim = lambda area: ndi.binary_dilation(area, iterations=1) & ~ndi.binary_erosion(area, iterations=1)
    lab = L["open"]
    glades = {int(lab[int(np.clip(round(f["px"][1]), 0, H - 1)), int(np.clip(round(f["px"][0]), 0, W - 1))])
              for f in cands if f["kind"] == "clearing"} - {0}
    # the clearing or the field the control stands in or at the edge of is the control's own feature
    r = int(OWN_M / mpp)
    cu, cv = int(round(ctrl[0])), int(round(ctrl[1]))
    own = set(np.unique(lab[max(cv - r, 0):cv + r + 1, max(cu - r, 0):cu + r + 1]).tolist()) - {0}
    yy, xx = np.mgrid[0:H, 0:W]
    mine = rim(np.isin(lab, list(own))) & ((xx - ctrl[0]) ** 2 + (yy - ctrl[1]) ** 2 <= (OWN_FAR_M / mpp) ** 2)
    masks = dict(path=L["path"], stream=L["stream"], pond=rim(L["water"]), enclosure=rim(L["fence"]),
                 fence=L.get("fence_line", np.zeros((H, W), bool)),
                 open_edge=rim(L["open_big"]) & ~mine, clearing=rim(np.isin(lab, list(glades))) & ~mine,
                 settlement=rim(L["settlement"]), building=L["houses"])
    # A path or stream the control stands at (within OWN_LINE_M) is the control's own line, not what stops a runner
    # who ran past it (Bělá 1: the control by two paths, the backstop was "15 m to the left and right", the path
    # across the way 50 m on was the one to name). Its piece up to OWN_LINE_GOES_M from the control counts on a ray
    # only after the ray has left it for OWN_LEAVE_M (a street of a sprint map that the ray runs beside).
    yy, xx = np.mgrid[0:H, 0:W]
    dist2 = (xx - ctrl[0]) ** 2 + (yy - ctrl[1]) ** 2
    near_disc = dist2 <= (OWN_LINE_GOES_M / mpp) ** 2
    own_line = np.zeros((H, W), bool)
    for k in ("path", "stream"):
        lab_k, nk = ndi.label(masks[k] & near_disc, structure=np.ones((3, 3)))
        if nk:
            mine_k = np.unique(lab_k[(dist2 <= (OWN_LINE_M / mpp) ** 2) & (lab_k > 0)])
            own_line |= np.isin(lab_k, mine_k[mine_k > 0])
    by_own = ndi.binary_dilation(own_line, iterations=2) if own_line.any() else own_line
    kind_at = np.zeros((H, W), np.uint8)
    for n in range(len(BACKSTOPS), 0, -1):
        kind_at[ndi.binary_dilation(masks[BACKSTOPS[n - 1]], iterations=1)] = n
    t = np.arange(BEYOND_M[0] / mpp, BEYOND_M[1] / mpp, 1.0)
    offsets = np.arange(-BEYOND_FAN, BEYOND_FAN + 1e-6, BEYOND_STEP)
    hits = []           # (offset of the ray, distance in pixels, kind, (u, v))
    for off in offsets:
        a = math.radians(travel_az + off)
        u = np.round(ctrl[0] + t * math.sin(a)).astype(int)
        v = np.round(ctrl[1] - t * math.cos(a)).astype(int)
        inside = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        u, v, far = u[inside], v[inside], t[inside]
        k = kind_at[v, u]
        # where the ray has left the control's own line (OWN_LEAVE_M away from it in a row)
        leave = max(1, int(round(OWN_LEAVE_M / mpp)))
        away = ~by_own[v, u]
        left_at = len(away)
        if len(away):
            run = np.convolve(away.astype(int), np.ones(leave, int), "full")[leave - 1:leave - 1 + len(away)]
            if (run >= leave).any():
                left_at = int(np.argmax(run >= leave))
        same = max(1, int(STOP_SAME_M / mpp))
        for i in np.nonzero(k)[0]:
            near = k[i:i + same]
            n = int(near[near > 0].min())
            kind, j = BACKSTOPS[n - 1], i + int(np.argmax(near == n))
            if abs(off) <= BEYOND_AHEAD and kind in ("path", "stream") \
                    and _runs_along(masks[kind], (u[j], v[j]), travel_az + off, mpp, ctrl):
                continue
            if kind in ("path", "stream") and i < left_at and by_own[v[j], u[j]]:
                continue
            hits.append((float(off), float(far[i]), kind, (float(u[i]), float(v[i]))))
            break
    parts = []
    for side, lo, hi in (("left", -BEYOND_FAN, -BEYOND_AHEAD - 1e-6), ("ahead", -BEYOND_AHEAD, BEYOND_AHEAD),
                         ("right", BEYOND_AHEAD + 1e-6, BEYOND_FAN)):
        got = [h for h in hits if lo <= h[0] <= hi]
        if not got:
            continue
        kind = max({h[2] for h in got}, key=lambda q: (sum(h[2] == q for h in got), -min(h[1] for h in got if h[2] == q)))
        same = sorted((h for h in got if h[2] == kind), key=lambda h: h[1])
        rays = ((offsets >= lo) & (offsets <= hi)).sum()
        far = same[(len(same) - 1) // 2][1] * mpp > BEYOND_FAR_M
        if (3 * len(same) < 2 * rays) if far else (2 * len(same) < rays):
            continue
        parts.append(dict(side=side, kind=kind, px=same[(len(same) - 1) // 2][3],
                          line=[h[3] for h in sorted(same, key=lambda h: h[0])]))
    return dict(parts=parts) if parts else None


def wandering(t, x, y, a, b, ctrl_xy, vref, est_loss=None):
    """Whether the track of a leg (indices a..b of t, x, y in seconds and metres) shows the runner lost near
    the control, and from where: dict(i = track index where the direct way in ended, dist = how far from
    the control that was, extra_m and extra_s = how much more was run and how much longer it took than
    going straight in from there) or None.

    Once inside ZONE_M of the control, the way still to run minus the straight distance to the control stays
    the same while the runner heads for the control and falls whenever they do not: where it starts to fall,
    contact was lost."""
    if est_loss is not None and est_loss < MIN_LOSS_S:
        return None
    xs, ys, ts = np.asarray(x[a:b + 1], float), np.asarray(y[a:b + 1], float), np.asarray(t[a:b + 1], float)
    if len(xs) < 4:
        return None
    d = np.hypot(xs - ctrl_xy[0], ys - ctrl_xy[1])
    left = np.r_[np.cumsum(np.hypot(np.diff(xs), np.diff(ys))[::-1])[::-1], 0.0]   # metres still to run
    excess = left - d
    inside = np.nonzero(d <= ZONE_M)[0]
    if not len(inside):
        return None
    i0 = int(inside[0])
    if excess[i0] < WANDER_M:
        return None
    tol = max(15.0, 0.08 * excess[i0])       # a track wiggles: this much is lost on the straightest way in
    i = i0 + int(np.nonzero(excess[i0:] >= excess[i0] - tol)[0][-1])
    extra_s = float(ts[-1] - ts[i] - d[i] / max(vref, 0.5))
    if extra_s < WANDER_S:
        return None
    return dict(i=a + i, dist=float(d[i]), extra_m=float(excess[i]), extra_s=extra_s)


def nearest_help(cands, track_px, mpp):
    """The point feature the wandering track came closest to: (candidate, metres, index into track_px) or None."""
    best = None
    tp = np.asarray(track_px, float)
    for f in cands:
        if f["ok"] and f["kind"] in POINTS and f.get("score", 0) >= MIN_SCORE:
            dd = np.hypot(tp[:, 0] - f["px"][0], tp[:, 1] - f["px"][1]) * mpp
            k = int(np.argmin(dd))
            if dd[k] <= LOST_NEAR_M and (best is None or dd[k] < best[1]):
                best = (f, float(dd[k]), k)
    return best


def prepare(kmz, ctrl_ll, best_dir, dem="aws", used=None, terrain_cache=None, barriers_file=None):
    """Everything read from the map once for all its controls: the picture, the terrain classes, the blue lines,
    the point symbols, what cannot be gone through (mapdata.obstacles, opened at the controls) and the
    elevation. ctrl_ll: the controls as [(lat, lon)]; best_dir: where the elevation is cached; used: the
    elevation source an earlier run ended up with (best.json "dem"). Returns a dict for cut()."""
    gm = GeoMap.from_kmz(kmz)
    mpp = gm.m_per_px_x
    rgb = np.asarray(gm.image)
    cls = mapdata.terrain(gm, kmz, terrain_cache)
    blue = stream_mask(rgb, gm.header_px)
    north = T.north_lines(rgb, gm.header_px)["angle_deg"]
    marks = symbols.find(rgb, mpp, gm.header_px, skip=no_symbols(cls, mpp))
    ctrl = [tuple(float(a) for a in gm.latlon_to_px(la, lo)) for la, lo in ctrl_ll]
    obs = mapdata.obstacles(gm, cls, open_at=ctrl)
    return dict(gm=gm, mpp=mpp, rgb=rgb, cls=obs["cls"], blue=blue, marks=marks, ctrl=ctrl, obs=obs, north=north,
                fence_line=_grow(obs["hard"], max(1.0, 1.5 / mpp)),
                dem=mapdata.elevation(gm, best_dir, dem, used=used),
                barriers=mapdata.barriers(barriers_file, gm) if barriers_file else None,
                step=max(2, int(round(2 * T.REF_M_PER_PX / mpp))))


def cut(P, c, cut_m=CUT_M):
    """The map cut_m around the point c = (u, v) (a control) as relocate works on it, or None at the very edge:
    dict(box=(u0, v0, u1, v1), sl (the numpy slices), win (map pixels -> pixels of the cut-out), height, local
    (what the routes keep out of, for describe), here (the point symbols in it), L (its layers))."""
    gm, mpp, obs, barriers = P["gm"], P["mpp"], P["obs"], P["barriers"]
    half = int(cut_m / mpp)
    u0, v0 = max(int(c[0]) - half, 0), max(int(c[1]) - half, 0)
    u1, v1 = min(int(c[0]) + half + 1, gm.W), min(int(c[1]) + half + 1, gm.H)
    if u1 - u0 < 8 or v1 - v0 < 8:
        return None
    v, u = np.mgrid[v0:v1, u0:u1].astype(float)
    height = P["dem"].height(*gm.px_to_latlon(u, v))
    win = lambda p: (p[0] - u0, p[1] - v0)
    box = (slice(v0, v1), slice(u0, u1))
    # what the routes keep out of (bestroute.py): the forbidden lines and areas, and fenced ground
    local = dict(forbidden=[], hard=[], crossings=[], areas=[], mask=obs["blocked"][box], hard_mask=obs["hard"][box])
    if obs["walls"].any() or obs["climb"].any():       # (sprint maps only)
        local.update(wall_mask=obs["walls"][box], climb_mask=obs["climb"][box])
    if barriers:
        local.update(forbidden=[[win(p) for p in l] for l in barriers["forbidden"]],
                     hard=[[win(p) for p in l] for l in barriers["hard"]],
                     crossings=[win(p) for p in barriers["crossings"]],
                     areas=[[win(p) for p in a] for a in barriers["areas"]])
    here = [dict(f, px=win(f["px"])) for f in P["marks"] if u0 <= f["px"][0] < u1 and v0 <= f["px"][1] < v1]
    L = layers(P["cls"][box], P["blue"][box], mpp, P["rgb"][box], obs["fenced"][box],
               [(pu - u0, pv - v0, area) for pu, pv, area in obs["pens"] if u0 <= pu < u1 and v0 <= pv < v1],
               P["fence_line"][box], obs["walls"][box])
    return dict(box=(u0, v0, u1, v1), sl=box, win=win, height=height, local=local, here=here, L=L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kmz")
    ap.add_argument("out")
    ap.add_argument("result")
    ap.add_argument("--dem", default="aws", choices=("aws", "cuzk", "auto"))
    ap.add_argument("--terrain-cache", metavar="FILE")
    ap.add_argument("--barriers", metavar="FILE")
    ap.add_argument("--debug", metavar="DIR")
    args = ap.parse_args()
    best_dir = os.path.join(args.out, "best")
    with open(os.path.join(best_dir, "best.json"), encoding="utf-8") as f:
        best = json.load(f)
    with open(os.path.join(args.out, "analysis.json"), encoding="utf-8") as f:
        A = json.load(f)
    P = prepare(args.kmz, [(c["lat"], c["lon"]) for c in A["course"]], best_dir, args.dem, best.get("dem"),
                args.terrain_cache, args.barriers)
    gm, mpp, rgb, cls, blue, ctrl, dem, step = (P[k] for k in ("gm", "mpp", "rgb", "cls", "blue", "ctrl", "dem", "step"))
    model = SpeedModel.load(os.path.join(best_dir, "speed_model.json"))
    routes = {l["leg"]: [tuple(float(a) for a in gm.latlon_to_px(p[0], p[1])) for p in l.get("route") or []]
              for l in best["legs"]}
    track = A["track"]
    tu, tv = (np.asarray(a, float) for a in gm.latlon_to_px(np.array(track["lat"]), np.array(track["lon"])))
    tx, ty = (np.asarray(a, float) for a in gm.to_xy(np.array(track["lat"]), np.array(track["lon"])))
    tt = np.asarray(track["t"], float)
    ll = lambda p: [rounded([float(v)], 6)[0] for v in gm.px_to_latlon(*p)]
    out = []
    for leg in A["legs"]:
        k = leg["leg"]
        if k >= len(ctrl) - 1:
            continue  # the last leg ends at the finish, which is no control to look for
        c = ctrl[k]
        C = cut(P, c)
        if C is None:
            continue
        (u0, v0, u1, v1), box, win, height, L = C["box"], C["sl"], C["win"], C["height"], C["L"]
        cands = candidates(cls[box], blue[box], height, mpp, win(c), dem.source, rgb[box], C["here"], L)
        describe(cands, cls[box], height, mpp, win(c), model, C["local"], step)
        # the way in: along the best route; a leg without one comes straight from the control before
        prev = ctrl[k - 1]
        az, tail = way_in(routes.get(k) or [prev], c, mpp)
        if az is None:
            az = bearing(prev[0] - c[0], prev[1] - c[1])
        tail = [win(p) for p in tail]
        feats, attack = choose(cands, az, mpp, tail if routes.get(k) else None, prev=win(prev),
                               leg_m=math.hypot(prev[0] - c[0], prev[1] - c[1]) * mpp)
        # A runner who misses the control runs on the way they came: the last stretch of their own track when
        # it shows them coming in (it reaches the control and they were not wandering about there), else the
        # last stretch of the best route.
        lost = wandering(tt, tx, ty, leg["a"], leg["b"], gm.to_xy(A["course"][k]["lat"], A["course"][k]["lon"]),
                         A.get("vref") or 0.0, leg.get("est_loss"))
        on, by = None, "route"
        own = [(tu[j], tv[j]) for j in range(leg["a"], leg["b"] + 1)]
        if not leg.get("no_data") and not lost and len(own) > 3 \
                and math.hypot(own[-1][0] - c[0], own[-1][1] - c[1]) * mpp <= TRACK_IN_M:
            on = way_in(own, c, mpp, RUN_IN_M)[0]
            by = "track" if on is not None else "route"
        if on is None:
            on = way_in(routes.get(k) or [prev], c, mpp, RUN_IN_M)[0]
        on = ((az if on is None else on) + 180.0) % 360.0
        stop = beyond(L, cands, win(c), on, mpp)
        for part in stop["parts"] if stop else []:
            _place(part, height, mpp, win(c))

        def public(f):
            la, lo = ll((f["px"][0] + u0, f["px"][1] + v0))
            out = dict(kind=f["kind"], lat=la, lon=lo, dist=round(f["dist"], 1), az=round(f["az"], 1),
                       back_az=round(f["back_az"], 1), dh=round(f["dh"], 1),
                       point=f["kind"] in POINTS and not f.get("edge"))     # of an edge the nearest place is given
            if f.get("via"):
                out.update(via=[ll((x + u0, y + v0)) for x, y in f["via"]], walk=round(f["walk"], 1),
                           first_az=round(f["first_az"], 1))
            return out
        if lost:
            i = lost["i"]
            seg = [(tu[j] - u0, tv[j] - v0) for j in range(i, leg["b"] + 1)]
            near = nearest_help(cands, seg, mpp)
            lost = dict(i=i, lat=track["lat"][i], lon=track["lon"][i], dist=round(lost["dist"], 1),
                        extra_m=round(lost["extra_m"], 1), extra_s=round(lost["extra_s"], 1),
                        near=dict(public(near[0]), track_m=round(near[1], 1), i=i + near[2]) if near else None)
        # the backstop: its parts, and the bearing back to the control for whoever ran into one of them
        past = dict(az=round(on, 1), back_az=round((on + 180.0) % 360.0, 1), within=BEYOND_M[1], by=by,
                    parts=[dict(public(q), side=q["side"], line=[ll((x + u0, y + v0)) for x, y in q["line"]])
                           for q in stop["parts"]]) if stop else None
        out.append(dict(leg=k, name=leg["name"], features=[public(f) for f in feats],
                        attack=public(attack) if attack else None, beyond=past, lost=lost))
        print(f"{leg['name']}: " + (", ".join(f"{f['kind']} {f['dist']:.0f} m at {f['az']:.0f}" for f in feats) or "-")
              + (f"; attack {attack['kind']} {attack['dist']:.0f} m" if attack else "")
              + ("; beyond " + ", ".join(f"{q['side']} {q['kind']} {q['dist']:.0f} m" for q in stop["parts"])
                 if stop else "")
              + (f"; lost {lost['dist']:.0f} m out, {lost['extra_s']:.0f} s" if lost else ""))
        if args.debug:
            _draw(args.debug, gm, leg["name"], (u0, v0, u1, v1), c, tail, cands, feats, attack, stop, lost,
                  [(tu[j], tv[j]) for j in range(leg["a"], leg["b"] + 1)], leg["a"], L)
    # bearings to the north of the map: that of its north lines, which lean on a map turned in its picture
    north_bearings(out, P["north"])
    with open(args.result, "w", encoding="utf-8") as f:
        json.dump(dict(version=VERSION, north=dict(by="lines", deg=round(P["north"], 2)), controls=out), f)


def _draw(folder, gm, name, box, c, tail, cands, feats, attack, stop, lost, track_px, a, L):
    """The cut-out of the map around one control with every candidate (small), the chosen features (numbered),
    the attack point (green square), the parts of the backstop (orange: where the rays met it, and the square
    at the one that is named), the last stretch of the best route (blue),
    what was read as fenced ground (magenta tint), the track (red) and where contact was lost (red ring)."""
    from PIL import Image, ImageDraw

    from .render import _font
    u0, v0, u1, v1 = box
    S = 3 if gm.m_per_px_x > 1 else 2
    c0 = (c[0] - u0, c[1] - v0)
    cut = np.asarray(gm.image.crop(box)).copy()
    cut[L["fence"]] = cut[L["fence"]] // 2 + np.array([127, 0, 127], np.uint8)
    im = Image.fromarray(cut).resize(((u1 - u0) * S, (v1 - v0) * S), Image.NEAREST)
    d = ImageDraw.Draw(im, "RGBA")
    P = lambda p: ((p[0] - u0) * S, (p[1] - v0) * S)
    W = lambda p: (p[0] * S, p[1] * S)
    r = 37.5 / gm.m_per_px_x * S
    x, y = P(c)
    d.ellipse([x - r, y - r, x + r, y + r], outline=(170, 40, 220, 255), width=3)
    for R in (RADIUS_M, ATTACK_HI):
        q = R / gm.m_per_px_x * S
        d.ellipse([x - q, y - q, x + q, y + q], outline=(170, 40, 220, 90), width=1)
    if len(tail) > 1:
        d.line([W(p) for p in tail], fill=(20, 70, 220, 200), width=3)
    if len(track_px) > 1:
        d.line([P(p) for p in track_px], fill=(220, 30, 40, 200), width=3)
    for f in cands:
        x, y = W(f["px"])
        col = (0, 0, 0, 255) if f["ok"] else (150, 150, 150, 255)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 255, 255, 230), outline=col, width=2)
        d.text((x + 5, y - 5), f["kind"][:4], fill=col, font=_font(12))
        if f.get("barred"):         # left out: something impassable on the straight line, and far round it
            d.line([x - 7, y - 7, x + 7, y + 7], fill=(220, 30, 40, 255), width=3)
            d.line([x - 7, y + 7, x + 7, y - 7], fill=(220, 30, 40, 255), width=3)
    for n, f in enumerate(feats, 1):
        x, y = W(f["px"])
        # the way from the feature to the control: straight, or round what bars the straight line
        d.line([W(p) for p in f.get("via") or [f["px"], c0]], fill=(20, 70, 220, 170), width=2)
        d.ellipse([x - 11, y - 11, x + 11, y + 11], outline=(20, 70, 220, 255), width=4)
        d.text((x + 13, y + 4), f"{n} {f['kind']} {f['dist']:.0f}m {f['az']:.0f}", fill=(20, 70, 220, 255), font=_font(16))
    for f, col in [(attack, (0, 140, 60, 255))] + [(q, (240, 130, 0, 255)) for q in (stop or {}).get("parts", [])]:
        if f:
            x, y = W(f["px"])
            d.rectangle([x - 15, y - 15, x + 15, y + 15], outline=col, width=4)
            d.text((x - 15, y - 34), f"{f.get('side', '')} {f['kind']}".strip(), fill=col, font=_font(16))
            for hx, hy in (W(h) for h in f.get("line", [])):
                d.line([W(c0), (hx, hy)], fill=col[:3] + (110,), width=1)
                d.ellipse([hx - 5, hy - 5, hx + 5, hy + 5], fill=col)
    if lost:
        x, y = P(track_px[lost["i"] - a])
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(220, 30, 40, 255), width=4)
    d.text((6, 4), name, fill=(0, 0, 0, 255), font=_font(22))
    os.makedirs(folder, exist_ok=True)
    im.save(os.path.join(folder, f"ctrl_{name.replace('-', '_')}.png"))


if __name__ == "__main__":
    main()
