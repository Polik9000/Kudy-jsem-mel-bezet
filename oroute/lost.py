"""Help for "I am at the control, I cannot see it and I do not know exactly where I am": from a rough position of
the runner (a tap on the map, or the track of the watch after the race) and how unsure it is (a circle), what
to catch that cannot be missed, how to get from it to the control, and what is crossed on the way. Rules and
geometry on the map without course, as oroute/relocate.py (whose catching features it builds on); no
control descriptions needed (a description typed by hand is only shown).

usage: python3 -m oroute.lost MAPONLY.kmz OUT_DIR [--analysis DIR] [--course COURSE.kmz|course.json]
           [--dem aws|cuzk|auto] [--terrain-cache FILE] [--barriers FILE] [--model FILE] [--stamp JSON]
           [--debug DIR] [--radius M]

OUT_DIR   where lost.json and lost.npz go: the scene of every control (see build).
--analysis the output folder of the race (default OUT_DIR). With its analysis.json (analyze.py) the controls are
          taken from it, else from --course (a course.json, or the KMZ with the course, read as analyze.py reads it
          without a track). Its best/ gives the elevation, the model, the forbidden crossings and the attack points.
--debug   also draw every control with the advice for a runner RADIUS (default 50) m unsure, 70 m from the
          control towards the control before it, and for the places the track shows the runner lost there.

Two parts. build() reads the map once (heavy, a job of a few tens of seconds): around every control, on cells
of about CELL_M, what can be caught (lines: paths, streams, fences, the edges of settlements, of large open
land and of ponds; buildings and the walls of a sprint map; the point features of relocate.candidates) and what
cannot be gone through (water, out of bounds, buildings, fenced ground, the forbidden lines and areas, the
fences of the map: a fence is not climbed on our advice). advise() is quick (numpy on one cut-out, no map
picture): from the circle, parallel rays in every direction; a line almost every ray of a direction meets
before anything impassable is one that cannot be missed (SURE), wherever in the circle the runner is. Of
those the most certain wins, not the nearest; then how to get from it to the control: along it to where the
control is beside it or to a junction on it, or a bearing. Bearings are to the north of the map (its magnetic
north lines), as everywhere in relocate.
"""
import argparse
import json
import math
import os

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from . import relocate as R
from .kmzmap import GeoMap
from .routing import Grid
from .speedmodel import SpeedModel

VERSION = 2            # of the scene (lost.json); the web app offers to prepare an older one again
                       # (2: whether the map is a sprint map, the angle of its north lines; no enclosure crossed)
CIRCLE_M = 50.0        # how unsure the runner is by default, in metres: in the forest ...
CIRCLE_SPRINT_M = 25.0  # ... and on a sprint map, where some street is always within 50 m (question 40)
SCENE_M = 320.0        # the scene of a control reaches this far from it (a runner up to RAY_M + a circle away)
CELL_M = 2.0           # cells of about this size (whole map pixels)
RAY_M = 250.0          # rays reach this far from the circle
RAYS = 9               # parallel rays across the circle in every direction ...
DIR_STEP = 10.0        # ... in directions this many degrees apart
SURE = 0.8             # a line met by this share of the rays of a direction cannot be missed
VIS_M = 8.0            # a point feature is seen when one passes this close to it (in forest, by day)
LINK_NEAR_M = 40.0     # a line that passes this close to the control leads to it: "the control is 30 m to the right"
LINK_POINT_M = 150.0   # a junction (end, stream crossing) on the line this close to the control is where to leave it
ALONG_MAX_M = 300.0    # ... when it is no farther than this along the line
LINK_NEAR_FAR_M = 100.0  # a line this close to the control leads to it too, when no point on it is a shorter way
POINT_DETOUR = 1.25    # ... than this many times the way along it to where it is nearest and the bearing from there
POINT_SAME_M, POINT_DETOUR_MAX = 15.0, 1.5   # (or its bearing is no more than this longer, the way up to this)
ON_LINE_M = 6.0        # a point feature this close to a line lies on it
DETOUR = 1.5           # a feature whose way to the control round something impassable is longer than this many
                       # times the straight line is no help
DETOUR_OK = 1.5       # the whole way of the advice may be this many times the straight way to the control (or the
                       # radius of the circle) before it counts less
BACK_DEG = 70.0        # a feature within this of the way the runner came is "go back to"
FAR_FULL_M, FAR_HALF_M = 150.0, 250.0   # features farther than FAR_FULL_M count less, at FAR_HALF_M half
LINES = ("path", "stream", "fence", "settlement", "open_edge", "pond", "building", "wall")
REL = dict(path=1.0, stream=0.9, fence=0.85, settlement=0.9, building=0.9, wall=0.9, pond=0.85, open_edge=0.7)
AREAS = ("building", "pond", "wall", "settlement")     # one comes to these, one does not follow them
LINE_POINTS = ("junction", "path_end", "stream_path")  # points on a line that say where on it one is
POINT_KINDS = ("junction", "path_end", "stream_path", "clearing", "hilltop") + R.SYMBOLS
# looking back at a race: where the track shows trouble near a control
NEAR_LOST_M = 100.0    # only this close to the control ...
AT_CONTROL_M = 20.0    # ... and not this close (the punch itself)
SLOW = 0.5             # slower than this share of the runner's reference speed ...
SLOW_S = 10.0          # ... for this long
TURN_DEG = 135.0       # the direction turned this much ...
TURN_S = 10.0          # ... from the TURN_S before to the TURN_S after
LOOP_S, LOOP_M, LOOP_SHARE = 45.0, 30.0, 0.4   # a loop: in LOOP_S at least LOOP_M run, but ending less than
                                               # LOOP_SHARE of it away from where it began
MERGE_M, MERGE_S = 30.0, 20.0   # two places this close (in metres and seconds) are one
MAX_MOMENTS = 4
BEFORE_M = 100.0       # what the track crossed in the last metres before the place
SEEN_M = 30.0          # what lay this close to the place
PASS_MIN_M = 10.0      # what is passed nearer than this to where one sets off is not worth saying
INSIDE_LONG, INSIDE_MIN_M = 2.0, 60.0   # a line through the circle counts when this many times its radius across
RETRO_R = 30.0         # how unsure the place on the track is (GPS and the moment of doubt)


# ---------------------------------------------------------------------------------------------- geometry
def bearing(du, dv):
    """Bearing in degrees (0 = up in the picture, clockwise) of a step in cells (or pixels); public() turns the
    bearings it gives to the north lines of the map (relocate.north_bearings)."""
    return R.bearing(du, dv)


def apart(a, b):
    """The angle between two bearings, 0..180."""
    return R._apart(a, b)


def far_factor(d):
    if d <= FAR_FULL_M:
        return 1.0
    return max(0.5, 1.0 - 0.5 * (d - FAR_FULL_M) / (FAR_HALF_M - FAR_FULL_M))


def _cells(mask, s, shape):
    """A mask of map pixels on cells of s x s pixels: a cell has it when any of its pixels has."""
    Hc, Wc = shape
    m = np.asarray(mask, bool)[:Hc * s, :Wc * s]
    return m.reshape(Hc, s, Wc, s).any((1, 3))


def _ring(mask, n):
    """The cells up to n outside a mask (where one comes to it from outside)."""
    return ndi.binary_dilation(mask, iterations=n) & ~mask if mask.any() else mask.copy()


def _line_cells(a, b):
    """The cells under the straight line from a to b = (col, row), half a cell apart: (cols, rows)."""
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) * 2) + 1)
    return (np.round(np.linspace(a[0], b[0], n)).astype(int), np.round(np.linspace(a[1], b[1], n)).astype(int))


# ---------------------------------------------------------------------------------------------- the scene
def build(P, c, model, prev=None, attack=None):
    """The scene of the control at map pixel c = (u, v): (meta, arrays) or (None, None) at the very edge of the map.
    P: relocate.prepare(); prev: the control before (or the start) in map pixels; attack: the attack point of
    relocate (dict kind, lat, lon) or None.
    meta: shape, s (map pixels per cell), cell (metres), origin and A (the affine map (lat, lon) -> (col, row),
    see to_cell), ctrl, prev (cells), attack, points (the point features: kind, at = (col, row), r = seen from
    this far in metres, base, on = the lines it lies on). arrays: imp and one boolean picture per kind of LINES."""
    C = R.cut(P, c, SCENE_M)
    if C is None:
        return None, None
    gm, mpp = P["gm"], P["mpp"]
    (u0, v0, u1, v1), box, win, height, L = C["box"], C["sl"], C["win"], C["height"], C["L"]
    cls = P["cls"][box]
    ctrl = win(c)
    cands = R.candidates(cls, P["blue"][box], height, mpp, ctrl, P["dem"].source, P["rgb"][box], C["here"], L)
    R.describe(cands, cls, height, mpp, ctrl, model, C["local"], P["step"])
    s = max(1, int(round(CELL_M / mpp)))
    grid = Grid(cls, height, mpp, model, step=s, barriers=C["local"])
    shape = grid.shape
    sz = lambda m: _cells(m, s, shape)
    imp = ~np.isfinite(grid.base)
    if C["local"].get("hard_mask") is not None:
        imp |= sz(C["local"]["hard_mask"])          # a fence of the map is not climbed on our advice
    walls = sz(P["obs"]["walls"][box])
    houses = sz(L["houses"])
    fenced = sz(L["fence"])
    settlement = sz(L["settlement"])
    ponds = sz(L["water"])          # any water, also a pond too narrow to be one for relocate (Petřvald S-1)
    arrays = dict(
        imp=imp,
        path=sz(L["path"]), stream=sz(L["stream"]),
        # what lies on the edge of something impassable is met a cell or two before it
        fence=sz(L["fence_line"]) | _ring(fenced, 2),
        settlement=_ring(settlement, 2),
        open_edge=_ring(sz(L["open_big"]), 1),
        pond=_ring(ponds, 2),
        building=_ring(houses, 1) | houses,
        wall=_ring(walls, 1) | walls)
    cell = lambda p: (p[0] / s - 0.5, p[1] / s - 0.5)            # pixels of the cut-out -> cells
    near = {k: ndi.distance_transform_edt(~arrays[k]) * s * mpp if arrays[k].any() else None
            for k in ("path", "stream", "fence")}
    points = []
    for f in cands:
        if f["kind"] not in POINT_KINDS or not f.get("ok"):
            continue
        at = cell(f["px"])
        ri, ci = int(np.clip(round(at[1]), 0, shape[0] - 1)), int(np.clip(round(at[0]), 0, shape[1] - 1))
        crowd = sum(g["kind"] == f["kind"] and g is not f and
                    math.hypot(g["px"][0] - f["px"][0], g["px"][1] - f["px"][1]) * mpp <= R.CROWD_M for g in cands)
        r = VIS_M + (math.sqrt(f["size"] / math.pi) if f["kind"] == "clearing" else 0.0)
        points.append(dict(kind=f["kind"], at=[round(at[0], 2), round(at[1], 2)], r=round(r, 1),
                           base=round(R.BASE[f["kind"]] * (0.6 if crowd >= R.CROWD else 1.0), 3),
                           on=[k for k, d in near.items() if d is not None and d[ri, ci] <= ON_LINE_M]))
    meta = dict(shape=list(shape), s=s, cell=s * mpp, **affine(gm, (u0, v0, u1, v1), s),
                ctrl=list(cell(ctrl)), prev=list(cell(win(prev))) if prev is not None else None, points=points,
                north=round(float(P.get("north", 0.0)), 3))
    if attack:
        meta["attack"] = dict(kind=attack["kind"], at=list(to_cell(meta, attack["lat"], attack["lon"])))
    return meta, arrays


def affine(gm, box, s):
    """dict(origin, A): the map (lat, lon) -> (col, row) of the cells of s x s pixels of the cut-out box = (u0, v0,
    u1, v1) of the map (see to_cell). It is affine: GeoMap is a flat earth turned by the rotation of the map."""
    u0, v0, u1, v1 = box
    U = np.array([0.0, u1 - u0, 0.0, u1 - u0])
    V = np.array([0.0, 0.0, v1 - v0, v1 - v0])
    la, lo = (np.asarray(a, float) for a in gm.px_to_latlon(U + u0, V + v0))
    origin = [float(la.mean()), float(lo.mean())]
    X = np.c_[(la - origin[0]) * 1e4, (lo - origin[1]) * 1e4, np.ones(4)]
    A = np.linalg.lstsq(X, np.c_[U / s - 0.5, V / s - 0.5], rcond=None)[0]
    return dict(origin=origin, A=A.tolist())


def to_cell(meta, lat, lon):
    o, A = meta["origin"], np.asarray(meta["A"])
    q = np.array([(lat - o[0]) * 1e4, (lon - o[1]) * 1e4, 1.0]) @ A
    return float(q[0]), float(q[1])


def to_latlon(meta, col, row):
    o, A = meta["origin"], np.asarray(meta["A"])
    d = np.linalg.solve(A[:2].T, np.array([col, row]) - A[2])
    return round(float(o[0] + d[0] / 1e4), 6), round(float(o[1] + d[1] / 1e4), 6)


def save(path_json, path_npz, scenes, stamp=None, sprint=False):
    """Write the scenes {k: (meta, arrays)}: the meta as JSON, the pictures bit-packed in one .npz. sprint: the map
    is a sprint map (mapdata.obstacles), which makes the default circle smaller (circle_m)."""
    out, arrs = [], {}
    for k, (meta, arrays) in sorted(scenes.items()):
        out.append(dict(meta, k=k))
        for name, a in arrays.items():
            arrs[f"{k}_{name}"] = np.packbits(a.ravel())
    np.savez_compressed(path_npz + ".tmp.npz", **arrs)
    os.replace(path_npz + ".tmp.npz", path_npz)
    with open(path_json + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dict(version=VERSION, north="lines", sprint=bool(sprint), stamp=stamp, controls=out), f)
    os.replace(path_json + ".tmp", path_json)


class Scene:
    """The scenes of one race as written by save(): load(), then control(k) for one control (unpacked once)."""

    def __init__(self, meta, npz):
        self.meta = meta
        self._npz = npz
        self._by_k = {c["k"]: c for c in meta["controls"]}
        self._open = {}

    @classmethod
    def load(cls, path_json, path_npz):
        with open(path_json, encoding="utf-8") as f:
            meta = json.load(f)
        with np.load(path_npz) as z:
            npz = {k: z[k] for k in z.files}
        return cls(meta, npz)

    @property
    def controls(self):
        return sorted(self._by_k)

    @property
    def circle_m(self):
        """The default radius of the circle of uncertainty for this map, in metres."""
        return CIRCLE_SPRINT_M if self.meta.get("sprint") else CIRCLE_M

    def control(self, k):
        """dict(meta of the control, the pictures by name, k) or None when the control has no scene."""
        if k not in self._by_k:
            return None
        if k not in self._open:
            m = self._by_k[k]
            Hc, Wc = m["shape"]
            S = dict(m)
            for name in ("imp",) + LINES:
                S[name] = np.unpackbits(self._npz[f"{k}_{name}"])[:Hc * Wc].reshape(Hc, Wc).astype(bool)
            self._open[k] = S
        return self._open[k]


# ---------------------------------------------------------------------------------------------- the advice
def _ways(S):
    """Metres from every cell to the control keeping out of everything impassable, and the next cell on that way
    (8 neighbours), computed once per control."""
    if "_ways" in S:
        return S["_ways"]
    imp = S["imp"]
    Hc, Wc = imp.shape
    idx = np.arange(Hc * Wc).reshape(Hc, Wc)
    rows, cols, data = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        ys, xs = slice(max(0, -dy), Hc - max(0, dy)), slice(max(0, -dx), Wc - max(0, dx))
        yd, xd = slice(max(0, dy), Hc - max(0, -dy)), slice(max(0, dx), Wc - max(0, -dx))
        ok = ~imp[ys, xs] & ~imp[yd, xd]
        a, b = idx[ys, xs][ok], idx[yd, xd][ok]
        w = np.full(len(a), S["cell"] * math.hypot(dx, dy))
        rows += [a, b]
        cols += [b, a]
        data += [w, w]
    G = csr_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(Hc * Wc, Hc * Wc))
    home = _free(S, S["ctrl"])
    far, nxt = dijkstra(G, indices=int(round(home[1])) * Wc + int(round(home[0])), return_predecessors=True)
    S["_ways"] = (far.reshape(Hc, Wc), nxt)
    return S["_ways"]


def _free(S, p):
    """The passable cell nearest to p = (col, row) (p itself when it is passable), as (col, row)."""
    imp = S["imp"]
    Hc, Wc = imp.shape
    ci, ri = int(np.clip(round(p[0]), 0, Wc - 1)), int(np.clip(round(p[1]), 0, Hc - 1))
    if not imp[ri, ci]:
        return float(p[0]), float(p[1])
    if "_free" not in S:
        S["_free"] = ndi.distance_transform_edt(imp, return_distances=False, return_indices=True)
    rr, cc = S["_free"][:, ri, ci]
    return float(cc), float(rr)


def _blocked(S, a, b):
    cs, rs = _line_cells(a, b)
    Hc, Wc = S["imp"].shape
    ok = (cs >= 0) & (cs < Wc) & (rs >= 0) & (rs < Hc)
    return bool(S["imp"][rs[ok], cs[ok]][1:-1].any())


def _to_control(S, p):
    """How to get from p = (col, row) to the control: dict(dist, az (the bearing to set off on), via = the way
    round in cells or None) or None when the way round is too long (or there is none)."""
    c = S["ctrl"]
    straight = math.hypot(c[0] - p[0], c[1] - p[1]) * S["cell"]
    if not _blocked(S, p, c):
        return dict(dist=straight, az=bearing(c[0] - p[0], c[1] - p[1]), via=None)
    far, nxt = _ways(S)
    q = _free(S, p)
    ri, ci = int(round(q[1])), int(round(q[0]))
    if not np.isfinite(far[ri, ci]) or far[ri, ci] > DETOUR * max(straight, 1.0) + 2 * S["cell"]:
        return None
    Wc = S["imp"].shape[1]
    way, i = [], ri * Wc + ci
    while i >= 0 and len(way) < 5000:
        way.append((float(i % Wc), float(i // Wc)))
        i = int(nxt[i])
    way = R._simplify([tuple(p)] + way + [tuple(c)], 1.0)
    first = way[1] if len(way) > 1 else c
    return dict(dist=float(far[ri, ci]), az=bearing(first[0] - p[0], first[1] - p[1]), via=way)


def _along(comp, a, b):
    """The way along the cells of comp (a line) from cell a to cell b = (col, row): (length in cells, the cells)."""
    rr, cc = np.nonzero(comp)
    n = len(rr)
    if n == 0:
        return np.inf, []
    pos = -np.ones(comp.shape, int)
    pos[rr, cc] = np.arange(n)
    rows, cols, data = [], [], []
    Hc, Wc = comp.shape
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        r2, c2 = rr + dy, cc + dx
        ok = (r2 >= 0) & (r2 < Hc) & (c2 >= 0) & (c2 < Wc)
        ok[ok] &= pos[r2[ok], c2[ok]] >= 0
        i, j = np.arange(n)[ok], pos[r2[ok], c2[ok]]
        w = np.full(len(i), math.hypot(dx, dy))
        rows += [i, j]
        cols += [j, i]
        data += [w, w]
    G = csr_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    near = lambda p: int(np.argmin((cc - p[0]) ** 2 + (rr - p[1]) ** 2))
    ia, ib = near(a), near(b)
    d, pred = dijkstra(G, indices=ia, return_predecessors=True)
    if not np.isfinite(d[ib]):
        return np.inf, []
    way, i = [], ib
    while i >= 0:
        way.append((float(cc[i]), float(rr[i])))
        i = int(pred[i])
    return float(d[ib]), way[::-1]


def _component(mask, p, r=2):
    """The connected part of mask (8 neighbours) at or within r cells of p = (col, row), or None."""
    Hc, Wc = mask.shape
    ci, ri = int(round(p[0])), int(round(p[1]))
    r0, r1, c0, c1 = max(ri - r, 0), min(ri + r + 1, Hc), max(ci - r, 0), min(ci + r + 1, Wc)
    win = mask[r0:r1, c0:c1]
    if not win.any():
        return None
    lab, _ = ndi.label(mask, structure=np.ones((3, 3)))
    vs, us = np.nonzero(win)
    k = np.argmin((us + c0 - ci) ** 2 + (vs + r0 - ri) ** 2)
    return lab == lab[vs[k] + r0, us[k] + c0]


def _link(S, kind, tgt, at_line=False):
    """How to get from where a line is caught (tgt, cells) to the control: dict(type = near | point | direct, ...),
    or None when the control cannot reasonably be reached from there.
    near: the line passes within LINK_NEAR_M of the control: go along it (along m, az) to where it is nearest, the
          control is then dist m to the side (right / left of the way along) at bearing az_off.
    point: a junction (end, stream crossing) on the line within LINK_POINT_M of the control: along it to that point,
          then the bearing.
    direct: the bearing and distance from where it is caught.
    at_line: the runner stands at the line already (_inside), so where it is caught is known: the bearing from there
    to a control within LINK_NEAR_FAR_M is what the other ways have to beat (Bělá 11: on the path 45 m south of the
    control, not along it to a junction and 95 m back).
    A line that passes farther than LINK_NEAR_M but within LINK_NEAR_FAR_M of the control is also "near" when
    every point on it would mean a way POINT_DETOUR times as long (Bělá 4: along the path away from the control
    to a junction and 120 m back, where the control was 55 m from the path: a short straight way to a sure line
    and along it is the advice, not a detour)."""
    cell = S["cell"]
    c = S["ctrl"]
    out = None
    comp = _component(S[kind], tgt) if kind not in AREAS else None
    if comp is not None:
        rr, cc = np.nonzero(comp)
        j = int(np.argmin((cc - c[0]) ** 2 + (rr - c[1]) ** 2))
        q = (float(cc[j]), float(rr[j]))
        dq = math.hypot(q[0] - c[0], q[1] - c[1]) * cell
        near_opt = None
        if dq <= LINK_NEAR_FAR_M:
            g, way = _along(comp, tgt, q)
            if g * cell <= ALONG_MAX_M:
                rest = _to_control(S, q)
                if rest is not None:
                    back = way[max(0, len(way) - 1 - int(10.0 / cell))] if len(way) > 1 else tgt
                    v = (q[0] - back[0], q[1] - back[1])
                    w = (c[0] - q[0], c[1] - q[1])
                    side = "right" if v[0] * w[1] - v[1] * w[0] > 0 else "left"
                    moves = g * cell >= 10
                    near_opt = dict(type="near", along=g * cell, az=bearing(q[0] - tgt[0], q[1] - tgt[1]) if moves
                                    else None, at=q, way=way, dist=dq, az_off=rest["az"], side=side if moves else None,
                                    via=rest["via"])
                    if dq <= LINK_NEAR_M:
                        out = near_opt
                    elif not moves:
                        # caught where it is nearest already: the bearing from there (direct) is what a point
                        # on the line has to beat
                        near_opt = dict(type="direct", along=0.0, dist=dq, az_off=rest["az"], via=rest["via"])
        if out is None:
            best = None
            for p in S["points"]:
                if p["kind"] not in LINE_POINTS or kind not in p["on"]:
                    continue
                at = tuple(p["at"])
                dc = math.hypot(at[0] - c[0], at[1] - c[1]) * cell
                if dc > LINK_POINT_M or not comp[int(round(at[1])), int(round(at[0]))] and \
                        _component(comp, at, int(ON_LINE_M / cell) + 1) is None:
                    continue
                g, way = _along(comp, tgt, at)
                if g * cell > ALONG_MAX_M:
                    continue
                rest = _to_control(S, at)
                if rest is not None and (best is None or g * cell + rest["dist"] < best[0]):
                    best = (g * cell + rest["dist"], p, g, way, rest)
            # a point on the line says where on it one is: it wins unless its bearing is longer and the whole way
            # much longer than along the line to where it is nearest and the bearing from there
            if at_line:
                here_d = math.hypot(tgt[0] - c[0], tgt[1] - c[1]) * cell
                rest0 = _to_control(S, tgt) if here_d <= LINK_NEAR_FAR_M else None
                if rest0 is not None and (near_opt is None or rest0["dist"] < near_opt["along"] + near_opt["dist"]):
                    near_opt = dict(type="direct", along=0.0, dist=rest0["dist"], az_off=rest0["az"], via=rest0["via"])
            nt = near_opt["along"] + near_opt["dist"] if near_opt else None
            if best and (near_opt is None or best[0] <= POINT_DETOUR * nt
                         or (best[4]["dist"] <= near_opt["dist"] + POINT_SAME_M and best[0] <= POINT_DETOUR_MAX * nt)):
                _, p, g, way, rest = best
                out = dict(type="point", point=p["kind"], at=tuple(p["at"]), along=g * cell,
                           az=bearing(p["at"][0] - tgt[0], p["at"][1] - tgt[1]), way=way,
                           dist=rest["dist"], az_off=rest["az"], via=rest["via"])
            elif near_opt is not None:
                out = near_opt
    if out is None:
        rest = _to_control(S, tgt)
        if rest is None:
            return None
        out = dict(type="direct", dist=rest["dist"], az_off=rest["az"], via=rest["via"])
    return out


def _rays(S, pos, r_cells):
    """Parallel rays from across the circle around pos in every direction: the cells they pass (cols, rows of
    shape directions x rays x samples), where each first meets something impassable (sample index), whether it
    starts on passable ground inside the scene, the sample step in metres, the directions and the unit vectors."""
    imp = S["imp"]
    Hc, Wc = imp.shape
    dirs = np.arange(0.0, 360.0, DIR_STEP)
    th = np.radians(dirs)
    d = np.stack([np.sin(th), -np.cos(th)], 1)
    n = np.stack([np.cos(th), np.sin(th)], 1)
    offs = np.linspace(-r_cells, r_cells, RAYS)
    t = np.arange(0.0, RAY_M / S["cell"] + 1e-9, 0.5)
    start = np.asarray(pos, float)[None, None, :] + offs[None, :, None] * n[:, None, :]
    q = start[:, :, None, :] + t[None, None, :, None] * d[:, None, None, :]
    ci, ri = np.round(q[..., 0]).astype(int), np.round(q[..., 1]).astype(int)
    inside = (ci >= 0) & (ci < Wc) & (ri >= 0) & (ri < Hc)
    ci, ri = np.clip(ci, 0, Wc - 1), np.clip(ri, 0, Hc - 1)
    stop = imp[ri, ci] | ~inside
    first = np.where(stop.any(-1), stop.argmax(-1), len(t))
    valid = ~stop[..., 0]
    return dict(ci=ci, ri=ri, inside=inside, first=first, valid=valid, start=start, step=0.5 * S["cell"],
                r_m=r_cells * S["cell"],
                dirs=dirs, d=d, n=n, t=t, offs=offs)


def _hits(S, Y):
    """For every kind of LINES and every point feature: (kind, None | point index, hit (dir x ray), sample index)."""
    out = []
    for kind in LINES:
        m = S[kind]
        if not m.any():
            continue
        on = m[Y["ri"], Y["ci"]] & Y["inside"]
        entry = on.copy()
        entry[..., 1:] &= ~on[..., :-1]
        entry[..., 0] = False                       # the line the runner stands on is not one to catch
        has = entry.any(-1)
        idx = np.where(has, entry.argmax(-1), len(Y["t"]))
        # what lies inside the circle is no catch for a ray: a runner in front of it would never meet it (_inside)
        beyond = idx * Y["step"] >= Y["r_m"]
        out.append((kind, None, has & (idx <= Y["first"]) & Y["valid"] & beyond, idx))
    cell = S["cell"]
    for i, p in enumerate(S["points"]):
        rel = np.asarray(p["at"], float)[None, None, :] - Y["start"]
        along = (rel * Y["d"][:, None, :]).sum(-1)
        across = (rel * Y["n"][:, None, :]).sum(-1)
        idx = np.round(along / 0.5).astype(int)
        near = (np.abs(across) * cell <= p["r"]) & (idx <= Y["first"]) & Y["valid"]
        hit = (along * cell >= Y["r_m"]) & (along * cell <= RAY_M) & near
        out.append((p["kind"], i, hit, idx))
    return out


def _seen(S, Y, di, oi, upto, skip_kind=None, skip_point=None):
    """What a runner on ray oi of direction di passes before sample upto: [(kind, metres)], first of each kind."""
    got = {}
    for kind in LINES:
        if kind == skip_kind or not S[kind].any():
            continue
        on = S[kind][Y["ri"][di, oi], Y["ci"][di, oi]] & Y["inside"][di, oi]
        entry = np.nonzero(on[1:] & ~on[:-1])[0] + 1
        entry = entry[(entry < min(upto, Y["first"][di, oi])) & (entry * Y["step"] >= PASS_MIN_M)]
        if len(entry):
            got[kind] = float(entry[0] * Y["step"])
    for i, p in enumerate(S["points"]):
        if i == skip_point or p["kind"] not in LINE_POINTS + ("clearing",):
            continue
        rel = np.asarray(p["at"], float) - Y["start"][di, oi]
        along, across = float(rel @ Y["d"][di]), float(rel @ Y["n"][di])
        if PASS_MIN_M <= along * S["cell"] and along / 0.5 < upto and abs(across) * S["cell"] <= p["r"]:
            got.setdefault(p["kind"], along * S["cell"])
    return sorted(got.items(), key=lambda kv: kv[1])


def advise(S, pos=None, r_m=50.0, came_from=None):
    """The advice for a runner at pos = (col, row) (None: anywhere up to r_m from the control), unsure by r_m.
    came_from: the bearing back along the way the runner came (to the control before, or back along the track).
    Returns dict(pos, snapped, r, helpers (best first: kind, at, share, sure, dist, az from the runner, cdist, caz
    from the control, seen, link, score), pick (index into helpers or None), relocate_first, back, attack, far)."""
    cell = S["cell"]
    c = tuple(S["ctrl"])
    here = c if pos is None else (float(pos[0]), float(pos[1]))
    Hc, Wc = S["imp"].shape
    out = dict(pos=here, snapped=False, r=float(r_m), helpers=[], pick=None, relocate_first=False, back=False,
               attack=S.get("attack"), far=False, no_runner=pos is None, ctrl=c)
    if not (0 <= here[0] < Wc and 0 <= here[1] < Hc) or \
            math.hypot(here[0] - c[0], here[1] - c[1]) * cell > SCENE_M - 20.0:
        out["far"] = True
        return out
    q = _free(S, here)
    if q != here:
        out.update(pos=q, snapped=True)
        here = q
    Y = _rays(S, here, max(r_m, 5.0) / cell)
    d0 = math.hypot(here[0] - c[0], here[1] - c[1]) * cell
    mid = RAYS // 2
    cands = []
    for kind, pi, hit, idx in _hits(S, Y):
        nv = Y["valid"].sum(1)
        share = np.where(nv > 0, hit.sum(1) / np.maximum(nv, 1), 0.0)
        for di in np.nonzero(share >= 0.3)[0]:
            rays = np.nonzero(hit[di])[0]
            oi = mid if hit[di, mid] else int(rays[np.argmin(np.abs(rays - mid))])
            dist = float(np.median(idx[di, rays])) * Y["step"]
            if pi is None:
                at = (float(Y["ci"][di, oi, idx[di, oi]]), float(Y["ri"][di, oi, idx[di, oi]]))
                base = REL[kind]
            else:
                at = tuple(S["points"][pi]["at"])
                base = S["points"][pi]["base"]
            cands.append(dict(kind=kind, point=pi, dir=float(Y["dirs"][di]), di=int(di), oi=oi, at=at,
                              upto=int(idx[di, oi]), share=float(share[di]), dist=dist,
                              pre=base * float(share[di]) * far_factor(dist)))
    cands += _inside(S, here, r_m)
    # one line is caught in many directions: of a kind and one connected piece of it (or one point) the best few
    groups = {}
    labels = {k: ndi.label(S[k], structure=np.ones((3, 3)))[0] for k in LINES if S[k].any()}
    for f in cands:
        key = (f["kind"], f["point"]) if f["point"] is not None else \
            (f["kind"], int(labels[f["kind"]][int(f["at"][1]), int(f["at"][0])]))
        groups.setdefault(key, []).append(f)
    scored = []
    for key, fs in groups.items():
        for f in sorted(fs, key=lambda f: (-round(f["pre"], 6), f["dist"]))[:3]:
            link = _link(S, f["kind"], f["at"], bool(f.get("inside"))) if f["point"] is None \
                else _to_point_link(S, f["at"])
            if link is None:
                continue
            # a long bearing from the feature is easily lost again: the nearer the control, the better
            far = 1.0 - 0.35 * min(1.0, max(0.0, link["dist"] - 60.0) / 120.0)
            bonus = 1.2 if link["type"] == "near" else (1.1 if link["type"] == "point" else 1.0) * far
            # the whole way (to the feature, along it, to the control) against the straight way: a feature that
            # leads far away and back is the last resort, not the first
            whole = f["dist"] + link.get("along", 0.0) + link["dist"]
            ratio = whole / max(d0, r_m, 1.0)
            detour = 1.0 if ratio <= DETOUR_OK else max(0.6, 1.0 - 0.2 * (ratio - DETOUR_OK))
            f.update(link=link, score=f["pre"] * bonus * detour, group=key)
            scored.append(f)
            break
    scored.sort(key=lambda f: (-round(f["score"], 6), f["dist"]))
    picked = []
    for f in scored:
        if len(picked) >= R.MAX_FEATURES:
            break
        if any(apart(f["dir"], g["dir"]) < R.APART_DEG and f["kind"] == g["kind"] for g in picked):
            continue
        picked.append(f)
    for f in picked:
        at = f["at"]
        f.update(sure=f["share"] >= SURE, az=bearing(at[0] - here[0], at[1] - here[1]),
                 dist=math.hypot(at[0] - here[0], at[1] - here[1]) * cell,
                 cdist=math.hypot(at[0] - c[0], at[1] - c[1]) * cell, caz=bearing(at[0] - c[0], at[1] - c[1]),
                 seen=[] if f.get("inside") else _seen(S, Y, f["di"], f["oi"], f["upto"],
                                                       f["kind"] if f["point"] is None else None, f["point"]))
    out["helpers"] = picked
    sure = [f for f in picked if f["sure"]]
    if sure:
        out["pick"] = picked.index(sure[0])
        nearest = min(f["dist"] for f in sure)
        if pos is not None and nearest > r_m and math.hypot(here[0] - c[0], here[1] - c[1]) * cell > r_m:
            out["relocate_first"] = True
        if pos is not None and came_from is not None:
            out["back"] = apart(sure[0]["az"], came_from) <= BACK_DEG
    elif picked:
        out["pick"] = 0
        out["relocate_first"] = pos is not None
    if out.get("attack"):
        a = out["attack"]["at"]
        out["attack"] = dict(out["attack"], dist=math.hypot(a[0] - here[0], a[1] - here[1]) * cell,
                             az=bearing(a[0] - here[0], a[1] - here[1]), to=_to_control(S, tuple(a)))
    return out


def _inside(S, here, r_m):
    """The long lines that run through the circle itself: a runner anywhere in it is at most r_m from them and sees
    them (the rays do not count a line the circle lies across: from half of the circle it is behind). One candidate
    per kind, at the place of the line nearest to here, when its piece is at least INSIDE_LONG times r_m (and
    INSIDE_MIN_M) across and the straight way there is free."""
    out = []
    cell = S["cell"]
    r = int(r_m / cell) + 1
    ci, ri = int(round(here[0])), int(round(here[1]))
    for kind in LINES:
        if kind in AREAS:
            continue
        m = S[kind]
        r0, c0 = max(ri - r, 0), max(ci - r, 0)
        vs, us = np.nonzero(m[r0:ri + r + 1, c0:ci + r + 1])
        if not len(vs):
            continue
        d = np.hypot(us + c0 - here[0], vs + r0 - here[1])
        j = int(np.argmin(d))
        if d[j] * cell > r_m:
            continue
        at = (float(us[j] + c0), float(vs[j] + r0))
        if _blocked(S, here, at):
            continue
        comp = _component(m, at, 1)
        rr, cc = np.nonzero(comp)
        across = math.hypot(rr.max() - rr.min(), cc.max() - cc.min()) * cell
        if across < max(INSIDE_LONG * r_m, INSIDE_MIN_M):
            continue
        dist = float(d[j]) * cell
        out.append(dict(kind=kind, point=None, dir=bearing(at[0] - here[0], at[1] - here[1]) if dist >= cell else 0.0,
                        di=None, oi=None, at=at, upto=0, share=1.0, dist=dist, inside=True,
                        pre=REL[kind] * far_factor(dist)))
    return out


def _to_point_link(S, at):
    rest = _to_control(S, at)
    return None if rest is None else dict(type="direct", dist=rest["dist"], az_off=rest["az"], via=rest["via"])


def route(a):
    """The line to draw for the advice, in cells: the runner, the feature, along it, the control."""
    if a["pick"] is None:
        return []
    f = a["helpers"][a["pick"]]
    line = [tuple(a["pos"]), tuple(f["at"])]
    link = f["link"]
    if link.get("way"):
        line += [tuple(p) for p in R._simplify(link["way"], 1.0)]
    line += [tuple(p) for p in link["via"]] if link.get("via") else [tuple(a["ctrl"])]
    return line


def public(S, a, desc=None):
    """The advice with cells turned into (lat, lon) and numbers rounded, for the page (webapp/texts.lost_advice)."""
    ll = lambda p: list(to_latlon(S, p[0], p[1]))
    hs = []
    for f in a["helpers"]:
        link = {k: v for k, v in f["link"].items() if k not in ("way", "at", "via")}
        link["round"] = f["link"].get("via") is not None
        for k in ("along", "dist", "az", "az_off"):
            if link.get(k) is not None:
                link[k] = round(float(link[k]), 1)
        if f["link"].get("at") is not None:
            link["at"] = ll(f["link"]["at"])
        hs.append(dict(kind=f["kind"], point=f["point"] is not None, inside=bool(f.get("inside")), at=ll(f["at"]),
                       share=round(f["share"], 2),
                       sure=f["sure"], dist=round(f["dist"], 1), az=round(f["az"], 1), cdist=round(f["cdist"], 1),
                       caz=round(f["caz"], 1), seen=[[k, round(m, 1)] for k, m in f["seen"]], link=link))
    out = dict(k=S.get("k"), pos=ll(a["pos"]), control=ll(S["ctrl"]), snapped=a["snapped"], r=a["r"], helpers=hs,
               pick=a["pick"], relocate_first=a["relocate_first"], back=a["back"], far=a["far"],
               no_runner=a["no_runner"], route=[ll(p) for p in route(a)], desc=desc or None)
    if a.get("attack") and a["attack"].get("dist") is not None:
        t = a["attack"]
        out["attack"] = dict(kind=t["kind"], at=ll(t["at"]), dist=round(t["dist"], 1), az=round(t["az"], 1),
                             to=dict(dist=round(t["to"]["dist"], 1), az=round(t["to"]["az"], 1)) if t.get("to") else None)
    # bearings to the north of the map (its north lines), not to the top of the picture
    return R.north_bearings(out, S.get("north", 0.0))


def advice(scene, k, lat=None, lon=None, r_m=50.0, desc=None):
    """advise() for control k of a Scene from (lat, lon) (None: the control and around it), as public()."""
    S = scene.control(k)
    if S is None:
        return None
    pos = to_cell(S, lat, lon) if lat is not None and lon is not None else None
    came = None
    if pos is not None and S.get("prev"):
        p = S["prev"]
        came = bearing(p[0] - pos[0], p[1] - pos[1])
    return public(S, advise(S, pos, r_m, came), desc)


# ---------------------------------------------------------------------------------------------- after the race
def moments(S, cols, rows, t, a, b, vref, anchors=()):
    """Where the track of the leg to this control (indices a..b of the track in cells cols, rows and seconds t)
    shows trouble near the control: [dict(i, why)], at most MAX_MOMENTS, in the order run.
    anchors: [(i, why)] what the analysis found already (the kind of mistake, a stop, where contact was lost);
    to them come the places where the runner was slower than SLOW of vref for SLOW_S, or turned by TURN_DEG.
    Only places between AT_CONTROL_M and NEAR_LOST_M from the control; two within MERGE_M and MERGE_S are one."""
    cell = S["cell"]
    c = S["ctrl"]
    x, y, tt = (np.asarray(v, float)[a:b + 1] for v in (cols, rows, t))
    if len(x) < 3:
        return []
    d = np.hypot(x - c[0], y - c[1]) * cell
    found = [(int(i), why) for i, why in anchors if a <= i <= b]
    step = np.r_[np.hypot(np.diff(x), np.diff(y)) * cell, 0.0]
    dt = np.r_[np.diff(tt), 0.0]
    slow = (step < SLOW * max(vref, 0.5) * np.maximum(dt, 1e-6)) & (d <= NEAR_LOST_M)
    lab, n = ndi.label(slow)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        i0, i1 = sl[0].start, sl[0].stop - 1
        if tt[i1] + dt[i1] - tt[i0] >= SLOW_S:
            found.append((a + i0, "slow"))
    run = np.r_[0.0, np.cumsum(step[:-1])]
    for i in range(len(x)):
        if d[i] > NEAR_LOST_M:
            continue
        e = int(np.searchsorted(tt, tt[i] + LOOP_S))
        ran = run[e] - run[i] if e < len(x) else 0.0
        if ran >= LOOP_M and math.hypot(x[e] - x[i], y[e] - y[i]) * cell < LOOP_SHARE * ran:
            found.append((a + i, "loop"))
            break
    for i in range(len(x)):
        if d[i] > NEAR_LOST_M:
            continue
        before = np.nonzero((tt >= tt[i] - TURN_S) & (tt < tt[i]))[0]
        after = np.nonzero((tt > tt[i]) & (tt <= tt[i] + TURN_S))[0]
        if len(before) < 2 or len(after) < 2:
            continue
        h0 = bearing(x[i] - x[before[0]], y[i] - y[before[0]])
        h1 = bearing(x[after[-1]] - x[i], y[after[-1]] - y[i])
        moved = min(math.hypot(x[i] - x[before[0]], y[i] - y[before[0]]),
                    math.hypot(x[after[-1]] - x[i], y[after[-1]] - y[i])) * cell
        if moved >= 8.0 and apart(h0, h1) >= TURN_DEG:
            found.append((a + i, "turn"))
    keep = []
    order = {"mistake": 0, "lost": 1, "stop": 2, "loop": 3, "turn": 4, "slow": 5}
    for i, why in sorted(found, key=lambda f: (f[0], order.get(f[1].split(":")[0], 9))):
        j = i - a
        if not AT_CONTROL_M <= d[j] <= NEAR_LOST_M:
            continue
        if keep:
            p = keep[-1]["i"] - a
            if math.hypot(x[j] - x[p], y[j] - y[p]) * cell <= MERGE_M or tt[j] - tt[p] <= MERGE_S:
                # one place: it keeps where it began, and is named by what the analysis found there if it did
                if order.get(why.split(":")[0], 9) < order.get(keep[-1]["why"].split(":")[0], 9):
                    keep[-1]["why"] = why
                continue
        keep.append(dict(i=i, why=why, dist=float(d[j])))
    return keep[:MAX_MOMENTS]


def look_back(S, cols, rows, t, a, b, vref, anchors=()):
    """moments() with what the runner should have seen there and the advice from there: [dict(i, why, dist, crossed
    = [(kind, metres before)], near = [(kind, metres, bearing)], advice (advise() from the place, unsure by
    RETRO_R, going back along the track))]."""
    cell = S["cell"]
    x, y = np.asarray(cols, float), np.asarray(rows, float)
    out = []
    for m in moments(S, cols, rows, t, a, b, vref, anchors):
        i = m["i"]
        # what the track crossed in the last BEFORE_M
        j, walked = i, 0.0
        while j > a and walked < BEFORE_M:
            walked += math.hypot(x[j] - x[j - 1], y[j] - y[j - 1]) * cell
            j -= 1
        crossed = {}
        for kind in LINES:
            if not S[kind].any():
                continue
            seen = False
            back = 0.0
            for q in range(i, j, -1):
                cs, rs = _line_cells((x[q - 1], y[q - 1]), (x[q], y[q]))
                ok = (cs >= 0) & (cs < S[kind].shape[1]) & (rs >= 0) & (rs < S[kind].shape[0])
                if S[kind][rs[ok], cs[ok]].any() and q != i:
                    seen = True
                    break
                back += math.hypot(x[q] - x[q - 1], y[q] - y[q - 1]) * cell
            if seen:
                crossed[kind] = back
        # what lay close by
        near = []
        r = int(SEEN_M / cell) + 1
        ci, ri = int(round(x[i])), int(round(y[i]))
        for kind in LINES:
            w = S[kind][max(ri - r, 0):ri + r + 1, max(ci - r, 0):ci + r + 1]
            vs, us = np.nonzero(w)
            if not len(vs):
                continue
            du, dv = us + max(ci - r, 0) - x[i], vs + max(ri - r, 0) - y[i]
            k = int(np.argmin(du * du + dv * dv))
            dd = math.hypot(du[k], dv[k]) * cell
            if dd <= SEEN_M:
                near.append((kind, dd, bearing(du[k], dv[k])))
        for p in S["points"]:
            dd = math.hypot(p["at"][0] - x[i], p["at"][1] - y[i]) * cell
            if dd <= SEEN_M + p["r"]:
                near.append((p["kind"], dd, bearing(p["at"][0] - x[i], p["at"][1] - y[i])))
        near.sort(key=lambda f: f[1])
        k0 = max(a, i - max(2, int(50.0 / max(cell, 0.1))))
        came = bearing(x[k0] - x[i], y[k0] - y[i]) if (x[k0], y[k0]) != (x[i], y[i]) else None
        out.append(dict(m, crossed=sorted(crossed.items(), key=lambda kv: kv[1]), near=near[:4],
                        advice=advise(S, (x[i], y[i]), RETRO_R, came)))
    return out


def public_moment(S, m):
    """A place of look_back() for the page."""
    return dict(i=m["i"], why=m["why"], dist=round(m["dist"], 1), crossed=[[k, round(v, 1)] for k, v in m["crossed"]],
                near=[[k, round(d, 1), round((az - S.get("north", 0.0)) % 360.0, 1)] for k, d, az in m["near"]],
                advice=public(S, m["advice"]))


# ---------------------------------------------------------------------------------------------- the script
def _controls(out, course):
    """The course as [(lat, lon)] (start, controls, finish), the names of the controls by index and the analysis
    (or None): from analysis.json when there is one, else from --course."""
    A = None
    p = os.path.join(out, "analysis.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            A = json.load(f)
        return [(c["lat"], c["lon"]) for c in A["course"]], A
    if not course:
        raise SystemExit("no analysis.json in OUT_DIR: pass --course")
    if course.endswith(".json"):
        with open(course, encoding="utf-8") as f:
            c = json.load(f)
        pts = [c["start"]] + c["controls"] + [c["finish"]]
        return [(p["lat"], p["lon"]) for p in pts], None
    from .course import detect_course, order_by_lines
    gm = GeoMap.from_kmz(course)
    det = detect_course(gm)
    if det["start"] is None or det["finish"] is None or not det["controls"]:
        raise SystemExit("the course could not be read from the map (start, finish or controls missing)")
    ordered, _ = order_by_lines(det["mask"], det["start"], det["controls"], det["finish"])
    pts = [det["start"]] + [p[:2] for p in ordered] + [det["finish"]]
    return [tuple(float(v) for v in gm.px_to_latlon(p[0], p[1])) for p in pts], None


def _anchors(A, leg, to_idx):
    """What the analysis found on a leg, as [(track index, why)]."""
    out = []
    m = leg.get("mistake")
    if m and m.get("at"):
        out.append((to_idx(m["at"][0], m["at"][1], leg["a"], leg["b"]), f"mistake:{m['type']}"))
    for s in leg.get("stops") or []:
        out.append((int(s["a"]) if isinstance(s, dict) else int(s[0]), "stop"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kmz")
    ap.add_argument("out")
    ap.add_argument("--course")
    ap.add_argument("--dem", default="aws", choices=("aws", "cuzk", "auto"))
    ap.add_argument("--terrain-cache", metavar="FILE")
    ap.add_argument("--barriers", metavar="FILE")
    ap.add_argument("--model", metavar="FILE")
    ap.add_argument("--debug", metavar="DIR")
    ap.add_argument("--radius", type=float, help="default: CIRCLE_M, on a sprint map CIRCLE_SPRINT_M")
    ap.add_argument("--analysis", metavar="DIR", help="folder of the analysis (analysis.json, best/); default OUT_DIR")
    ap.add_argument("--stamp", help="JSON kept in lost.json as it is (the web app compares it)")
    args = ap.parse_args()
    src = args.analysis or args.out
    best_dir = os.path.join(src, "best")
    os.makedirs(args.out, exist_ok=True)
    cache_dir = best_dir if os.path.isdir(best_dir) else args.out
    course, A = _controls(src, args.course)
    def load(name, default):
        path = os.path.join(best_dir, name)
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    best = load("best.json", {})
    rel = {c["leg"]: c for c in load("relocate.json", {}).get("controls", [])}
    mfile = args.model or os.path.join(best_dir, "speed_model.json")
    model = SpeedModel.load(mfile) if os.path.exists(mfile) else SpeedModel()
    barriers = args.barriers or (os.path.join(best_dir, "barriers.json")
                                 if os.path.exists(os.path.join(best_dir, "barriers.json")) else None)
    P = R.prepare(args.kmz, course, cache_dir, args.dem, best.get("dem"), args.terrain_cache, barriers)
    ctrl = P["ctrl"]
    scenes = {}
    for k in range(1, len(ctrl) - 1):
        meta, arrays = build(P, ctrl[k], model, prev=ctrl[k - 1], attack=(rel.get(k) or {}).get("attack"))
        if meta is None:
            continue
        scenes[k] = (meta, arrays)
    st = os.stat(args.kmz)
    stamp = json.loads(args.stamp) if args.stamp else [st.st_size, st.st_mtime_ns]
    paths = os.path.join(args.out, "lost.json"), os.path.join(args.out, "lost.npz")
    save(*paths, scenes, stamp=stamp, sprint=P["obs"]["sprint"])
    scene = Scene.load(*paths)
    radius = args.radius or scene.circle_m
    report = []
    for k in scene.controls:
        S = scene.control(k)
        p = S.get("prev")
        c = S["ctrl"]
        pos = None
        if p:
            d = math.hypot(p[0] - c[0], p[1] - c[1])
            if d > 0:
                f = min(1.0, (70.0 / S["cell"]) / d)
                pos = (c[0] + f * (p[0] - c[0]), c[1] + f * (p[1] - c[1]))
        a = advise(S, pos, radius, bearing(p[0] - pos[0], p[1] - pos[1]) if pos and p else None)
        item = dict(k=k, live=public(S, a), back=[])
        if A is not None:
            leg = next((g for g in A["legs"] if g["leg"] == k), None)
            if leg and not leg.get("no_data"):
                tr = A["track"]
                cols, rows = zip(*(to_cell(S, la, lo) for la, lo in zip(tr["lat"], tr["lon"])))

                def to_idx(la, lo, i0, i1):
                    q = to_cell(S, la, lo)
                    seg = np.hypot(np.asarray(cols[i0:i1 + 1]) - q[0], np.asarray(rows[i0:i1 + 1]) - q[1])
                    return i0 + int(np.argmin(seg))
                anchors = _anchors(A, leg, to_idx)
                lost = (rel.get(k) or {}).get("lost")
                if lost:
                    anchors.append((int(lost["i"]), "lost"))
                for m in look_back(S, cols, rows, tr["t"], leg["a"], leg["b"], A.get("vref") or 3.0, anchors):
                    item["back"].append(public_moment(S, m))
                    if args.debug:
                        _draw(args.debug, P, S, m["advice"], f"{k}_zpet_{m['i']}", (cols, rows, leg["a"], leg["b"]))
        report.append(item)
        _say(k, item)
        if args.debug:
            _draw(args.debug, P, S, a, f"{k}", None)
    if args.debug:
        with open(os.path.join(args.debug, "rady.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)


def _sentences(a):
    try:
        from webapp import texts
        return texts.lost_advice(a)
    except Exception:            # the script runs without the web app too
        h = a["helpers"][a["pick"]] if a.get("pick") is not None else None
        return [f"{h['kind']} {h['dist']:.0f} m az {h['az']:.0f}"] if h else ["-"]


def _say(k, item):
    print(f"{k}: " + " ".join(_sentences(item["live"])))
    for m in item["back"]:
        print(f"   back {m['why']} {m['dist']:.0f} m: " + " ".join(_sentences(m["advice"])))


def _draw(folder, P, S, a, name, track):
    """The cut-out of the map around the control with the circle, the features (numbered, the picked one larger),
    the line of the advice and its sentences below."""
    from PIL import Image, ImageDraw, ImageFont

    from .render import _font
    gm = P["gm"]
    c_ll = to_latlon(S, *S["ctrl"])
    cu, cv = (float(v) for v in gm.latlon_to_px(*c_ll))
    half = int(200.0 / P["mpp"])
    u0, v0 = int(max(cu - half, 0)), int(max(cv - half, 0))
    u1, v1 = int(min(cu + half, gm.W)), int(min(cv + half, gm.H))
    Z = 2 if P["mpp"] > 0.8 else 1
    im = Image.fromarray(P["rgb"][v0:v1, u0:u1]).resize(((u1 - u0) * Z, (v1 - v0) * Z), Image.NEAREST).convert("RGB")
    sent = _sentences(public(S, a))
    font = _font(15)
    if "DejaVu" not in str(getattr(font, "path", "")):     # no font with Czech letters: without diacritics
        import unicodedata
        font = ImageFont.load_default(15)
        sent = ["".join(ch for ch in unicodedata.normalize("NFKD", t) if not unicodedata.combining(ch)) for t in sent]
    W = im.width
    lines = []
    for t in sent:
        words, cur = t.split(), ""
        for w in words:
            if font.getlength(cur + " " + w) > W - 16 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
    out = Image.new("RGB", (W, im.height + 10 + 20 * len(lines)), (255, 255, 255))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out, "RGBA")

    def P2(p):
        la, lo = to_latlon(S, p[0], p[1])
        u, v = gm.latlon_to_px(la, lo)
        return ((float(u) - u0) * Z, (float(v) - v0) * Z)
    px_m = Z / P["mpp"]
    if track:
        cols, rows, ta, tb = track
        d.line([P2((cols[i], rows[i])) for i in range(ta, tb + 1)], fill=(220, 30, 40, 170), width=3)
    x, y = P2(S["ctrl"])
    r = 37.5 * px_m
    d.ellipse([x - r, y - r, x + r, y + r], outline=(170, 40, 220, 255), width=3)
    x, y = P2(a["pos"])
    r = a["r"] * px_m
    d.ellipse([x - r, y - r, x + r, y + r], outline=(230, 120, 0, 255), fill=(230, 120, 0, 40), width=3)
    d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(230, 120, 0, 255))
    rt = route(a)
    if len(rt) > 1:
        d.line([P2(p) for p in rt], fill=(20, 70, 220, 230), width=4)
    for n, f in enumerate(a["helpers"], 1):
        x, y = P2(f["at"])
        big = n - 1 == a["pick"]
        q = 13 if big else 9
        d.ellipse([x - q, y - q, x + q, y + q], outline=(20, 70, 220, 255) if f["sure"] else (120, 120, 120, 255),
                  width=4 if big else 2, fill=(255, 255, 255, 150))
        d.text((x - 4, y - 8), str(n), fill=(20, 70, 220, 255), font=_font(13))
    d.text((6, 4), f"kontrola {name}", fill=(0, 0, 0, 255), font=_font(18))
    for i, t in enumerate(lines):
        d.text((8, im.height + 6 + 20 * i), t, fill=(0, 0, 0, 255), font=font)
    os.makedirs(folder, exist_ok=True)
    out.save(os.path.join(folder, f"rada_{name}.png"))


if __name__ == "__main__":
    main()
