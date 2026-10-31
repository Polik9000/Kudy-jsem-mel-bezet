"""Fastest route between two points on a terrain + elevation grid.

The map is resampled to cells of `step` map pixels. Every cell connects to its 16
neighbours (8 + knight moves, so routes are not forced into 45-degree zigzags).
Edge cost = length * mean pace of the two cells * slope multiplier for the
direction of travel, so uphill and downhill cost differently (directed graph).
Shortest paths use scipy's Dijkstra.

Barriers (Grid(..., barriers=...)): lines that must not be crossed make their cells impassable
("forbidden": ISOM 708/709, a railway by the rules of the race), lines that are only very hard to cross
("hard": an impassable cliff or fence is not forbidden, just very slow) add HARD_CROSS_S seconds to a
crossing. Around a crossing point (level crossing, bridge, underpass) both are lifted. Areas that must not be
entered ("areas": the purple hatching on the map with the course, see oroute/hatch.py) are impassable all over;
a crossing point does not open them. The same holds for "mask", a picture of what is impassable (the ground
fences close in, oroute.relocate.enclosures). "hard_mask" is a picture of lines that are hard to cross (the
fences of the map, oroute.relocate.fences): crossing one costs HARD_CROSS_S, and so does every stretch of its
width run along it, which keeps routes off the line itself; it is kept thin so that a path beside a fence
stays a path. "climb_mask" is the same for the passable walls of a sprint map, at CLIMB_CROSS_S. "wall_mask"
is a picture of impassable walls (oroute.terrain.sprint_walls): every cell it touches is impassable, and no
diagonal or knight move may pass between or over its cells, so that a wall one cell thick is not jumped however
coarse the grid is, and a gate in it as narrow as two cells stays open (a gate is often no wider than a lane).

crossed() says which of these a line went through: the track of a runner is priced without them
(route_metrics), so a track across a railway can come out faster than the best route that had to go round.

Alternatives (Grid.alternatives): the next best routes that really differ from the best one, found by
making the corridor of the routes already found expensive and searching again (k dissimilar shortest
paths by the penalty method).
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

from . import terrain as T

IMPASSABLE = (T.WATER, T.OOB, T.BUILDING)
OFFS = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1),
        (1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]

BARRIER_CELLS = 4        # barrier lines are drawn this many cells thick, so no 16-neighbour move jumps over them
HARD_MASK_CELLS = 2      # a hard line given as a picture (hard_mask) is at least this many cells thick on the grid
HARD_CROSS_S = 90.0      # seconds it costs to cross a "hard" line (a fence to climb, a cliff to get round)
CLIMB_CROSS_S = 6.0      # seconds it costs to climb over a passable wall of a sprint map (climb_mask)
CROSSING_M = 14.0        # radius around a crossing point where the barrier is lifted
CORRIDOR_M = 30.0        # two routes are "the same" where they run within this distance of each other
ALT_PENALTY = 1.6        # how much more expensive the corridor of the routes already found gets
ALT_MIN_APART = 0.35     # an alternative must run outside the corridors for at least this share of its length
ALT_MAX_SLOWER = 0.35    # ... and be at most this much slower than the best route (plus ALT_MAX_SLOWER_S)
ALT_MAX_SLOWER_S = 30.0
SIDE_M = 8.0             # a line was crossed when the track gets this far from it on both sides of the crossing
INSIDE_M = 10.0          # an area was entered when this much of the track lies inside it, ...
EDGE_M = 5.0             # ... this far from its edge (GPS is a few metres off)
TRACK_OFF_M = 8.0        # a point of a GPS track on impassable ground is taken to lie on the passable ground up to this
                         # far beside it (nobody ran through the house: the track is a few metres off)
PATH_SIDE_M = 15.0       # a stretch of a runner's track this close to a path and running along it is taken to be on
                         # the path (GPS drifts, a map is placed a few metres off; decided on 11 Oct 2026) ...
PATH_RUN_M = 30.0        # ... when the stretch is at least this long ...
PATH_ALONG = 0.7         # ... and over every WINDOW_M of it the nearest point of the path moves along with the track
PATH_ANGLE_DEG = 30.0    # (at least this share of the way, at most this angle off its direction)
PATH_WINDOW_M = 10.0
POCKET_M2 = 5000.0       # passable ground smaller than this, cut off from the rest, is a pocket: a point in it is
                         # routed to from the nearest ground outside (a yard between houses, an island)


def block_classes(cls, step, model):
    """Downsample the class map: a block with a path keeps the path (paths are thin),
    otherwise the block takes its slowest passable class if that covers >= 1/3 of it,
    else the most common class. Mostly-impassable blocks stay impassable."""
    H, W = cls.shape[0] // step * step, cls.shape[1] // step * step
    c = cls[:H, :W].reshape(H // step, step, W // step, step).transpose(0, 2, 1, 3).reshape(H // step, W // step, -1)
    n = c.shape[-1]
    counts = np.stack([(c == k).sum(-1) for k in range(len(T.NAMES))], -1)
    out = counts.argmax(-1).astype(np.uint8)
    imp = counts[..., [T.WATER, T.OOB, T.BUILDING]].sum(-1)
    out[(counts[..., T.PATH] > 0) & (imp * 2 < n)] = T.PATH
    return out


class Grid:
    def __init__(self, cls, height, mpp, model, step=2, box=None, barriers=None):
        """cls: full-res class map, height: DEM at full res (same shape), mpp: metres per map pixel.
        box = (u0, v0, u1, v1) in map pixels to restrict the search area.
        barriers: dict(forbidden=[polyline], hard=[polyline], crossings=[point], areas=[polygon]) in map
        pixels, or None; it may also hold mask = a boolean picture the size of cls of what is impassable,
        hard_mask = one of lines that are hard to cross, climb_mask = one of low walls to climb over and
        wall_mask = one of thin walls that are impassable."""
        self.step, self.model = step, model
        self.barriers = barriers
        u0, v0, u1, v1 = box or (0, 0, cls.shape[1], cls.shape[0])
        u0, v0 = u0 // step * step, v0 // step * step
        self.u0, self.v0 = u0, v0
        self._cut = (slice(v0, v1), slice(u0, u1))
        sub = cls[v0:v1, u0:u1]
        self.cls = block_classes(sub, step, model)
        hh = height[v0:v1, u0:u1]
        Hc, Wc = self.cls.shape
        self.h = hh[:Hc * step, :Wc * step].reshape(Hc, step, Wc, step).mean((1, 3))
        self.cell = mpp * step
        self.shape = (Hc, Wc)
        self._piece = None       # which connected piece of the grid each cell belongs to (found when first needed)
        self._build()

    def _cell_xy(self, pts):
        """Map pixels -> (column, row) of the grid, as floats."""
        return [((u - self.u0) / self.step - 0.5, (v - self.v0) / self.step - 0.5) for u, v in pts]

    def _line_mask(self, lines, width=BARRIER_CELLS):
        Hc, Wc = self.shape
        im = Image.new("1", (Wc, Hc), 0)
        d = ImageDraw.Draw(im)
        for line in lines:
            if len(line) >= 2:
                d.line(self._cell_xy(line), fill=1, width=width)
        return np.array(im, bool)

    def _area_mask(self, polygons):
        Hc, Wc = self.shape
        im = Image.new("1", (Wc, Hc), 0)
        d = ImageDraw.Draw(im)
        for poly in polygons:
            if len(poly) >= 3:
                d.polygon(self._cell_xy(poly), fill=1, outline=1)
        return np.array(im, bool)

    def _barrier_grids(self):
        """(blocked cells, seconds per metre added) from self.barriers; (None, None) without barriers.
        Sets self._walls: the cells of the walls (wall_mask), whose moves _build checks, or None."""
        b = self.barriers
        self._walls = None
        if not b or not (b.get("forbidden") or b.get("hard") or b.get("areas")
                         or any(b.get(k) is not None for k in ("mask", "hard_mask", "climb_mask", "wall_mask"))):
            return None, None
        Hc, Wc = self.shape
        blocked = self._line_mask(b.get("forbidden") or [])
        hard = self._line_mask(b.get("hard") or []) & ~blocked
        if b.get("crossings"):
            yy, xx = np.mgrid[0:Hc, 0:Wc]
            r = CROSSING_M / self.cell
            for cx, cy in self._cell_xy(b["crossings"]):
                if -r <= cx < Wc + r and -r <= cy < Hc + r:
                    near = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
                    blocked &= ~near
                    hard &= ~near
        if b.get("areas"):
            blocked |= self._area_mask(b["areas"])
        if b.get("mask") is not None:
            # a cell is impassable when any of its pixels is (the mask has to be two cells thick to stop every
            # move of the grid; fenced ground with its fence is)
            m = np.asarray(b["mask"], bool)[self._cut][:Hc * self.step, :Wc * self.step]
            blocked |= m.reshape(Hc, self.step, Wc, self.step).any((1, 3))
        if b.get("wall_mask") is not None:
            m = np.asarray(b["wall_mask"], bool)[self._cut][:Hc * self.step, :Wc * self.step]
            self._walls = m.reshape(Hc, self.step, Wc, self.step).any((1, 3))
            blocked |= self._walls
        hard &= ~blocked
        extra = hard * (HARD_CROSS_S / (BARRIER_CELLS * self.cell))
        for key, sec, free in (("hard_mask", HARD_CROSS_S, True), ("climb_mask", CLIMB_CROSS_S, False)):
            if b.get(key) is None:
                continue
            band = self._band(b[key])
            if free and b.get("crossings"):
                yy, xx = np.mgrid[0:Hc, 0:Wc]
                r = CROSSING_M / self.cell
                for cx, cy in self._cell_xy(b["crossings"]):
                    band &= (xx - cx) ** 2 + (yy - cy) ** 2 > r * r
            extra = np.maximum(extra, (band & ~blocked) * (sec / (HARD_MASK_CELLS * self.cell)))
        return blocked, extra

    def _band(self, mask):
        """The cells a line given as a picture touches, and one more beside them: two cells thick at least, so
        that every move of the grid across it lands on it."""
        Hc, Wc = self.shape
        m = np.asarray(mask, bool)[self._cut][:Hc * self.step, :Wc * self.step]
        return binary_dilation(m.reshape(Hc, self.step, Wc, self.step).any((1, 3)), np.ones((2, 2), bool))

    def _build(self):
        Hc, Wc = self.shape
        base = self.model.pace(self.cls, 0.0) / self.model.slope_mult(0.0)
        self.blocked, extra = self._barrier_grids()
        if self.blocked is not None:
            base = base + extra
            base[self.blocked] = np.inf
        self.base = base
        idx = np.arange(Hc * Wc).reshape(Hc, Wc)
        rows, cols, data = [], [], []
        for dy, dx in OFFS:
            ys = slice(max(0, -dy), Hc - max(0, dy))
            xs = slice(max(0, -dx), Wc - max(0, dx))
            yd = slice(max(0, dy), Hc - max(0, -dy))
            xd = slice(max(0, dx), Wc - max(0, -dx))
            L = self.cell * np.hypot(dx, dy)
            p = 0.5 * (base[ys, xs] + base[yd, xd])
            g = (self.h[yd, xd] - self.h[ys, xs]) / L
            cost = L * p * self.model.slope_mult(g)
            ok = np.isfinite(cost)
            if self._walls is not None and abs(dy) + abs(dx) > 1:
                ok &= ~self._over_wall(dy, dx, ys, xs)
            rows.append(idx[ys, xs][ok])
            cols.append(idx[yd, xd][ok])
            data.append(cost[ok])
        n = Hc * Wc
        self.G = csr_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))

    def _over_wall(self, dy, dx, ys, xs):
        """For the move (dy, dx) from the cells (ys, xs): it passes between two cells of a wall (a diagonal
        move across a wall drawn as a staircase) or over one (a knight move)."""
        w = self._walls
        at = lambda ay, ax: w[ys.start + ay:ys.stop + ay, xs.start + ax:xs.stop + ax]
        sy, sx = int(np.sign(dy)), int(np.sign(dx))
        if abs(dy) == 1 and abs(dx) == 1:
            return at(dy, 0) & at(0, dx)
        if abs(dx) == 2:
            return at(0, sx) | at(dy, sx)
        return at(sy, 0) | at(sy, dx)

    def with_model(self, model):
        """The same grid with another speed model (the old graph is dropped first: no second copy in memory)."""
        self.G = None
        self.model, self._piece = model, None
        self._build()
        return self

    def to_cell(self, u, v):
        return int(round((v - self.v0) / self.step - 0.5)), int(round((u - self.u0) / self.step - 0.5))

    def to_px(self, r, c):
        return self.u0 + (c + 0.5) * self.step, self.v0 + (r + 0.5) * self.step

    def nearest_passable(self, r, c):
        Hc, Wc = self.shape
        r, c = min(max(r, 0), Hc - 1), min(max(c, 0), Wc - 1)
        if np.isfinite(self.base[r, c]):
            return r, c
        rr, cc = np.nonzero(np.isfinite(self.base))
        k = np.argmin((rr - r) ** 2 + (cc - c) ** 2)
        return int(rr[k]), int(cc[k])

    def _ends(self, a_px, b_px):
        """The cells a route from a to b starts and ends in: the passable cells nearest to the two points.
        A point walled in on a small piece of ground (a control in a yard closed in by buildings, on an
        island, in a pocket between two areas out of bounds: less than POCKET_M2) is taken from the nearest
        ground that is no such pocket instead: the route then leads as near to the control as one can get.
        Two large pieces with nothing to cross between them (a railway without a crossing) stay apart: there
        is no route then."""
        Hc, Wc = self.shape
        cells = [self.to_cell(*a_px), self.to_cell(*b_px)]
        ends = [self.nearest_passable(*c) for c in cells]
        if self._piece is None:
            self._piece = connected_components(self.G, directed=False)[1].reshape(Hc, Wc)
        piece = self._piece
        if piece[ends[0]] != piece[ends[1]]:
            ok = np.isfinite(self.base)
            large = (np.bincount(piece.ravel()) * self.cell ** 2 > POCKET_M2)[piece] & ok
            rr, cc = np.nonzero(large)
            for n, (r, c) in enumerate(cells):
                if len(rr) and not large[ends[n]]:
                    k = int(np.argmin((rr - r) ** 2 + (cc - c) ** 2))
                    ends[n] = (int(rr[k]), int(cc[k]))
        return ends[0][0] * Wc + ends[0][1], ends[1][0] * Wc + ends[1][1]

    def _search(self, G, s, t, limit=np.inf):
        """(seconds, cell indices of the path) of the cheapest path in graph G, or (inf, [])."""
        dist, pred = dijkstra(G, indices=s, return_predecessors=True, limit=limit)
        if not np.isfinite(dist[t]):
            return np.inf, []
        path = [t]
        while path[-1] != s:
            path.append(pred[path[-1]])
        return float(dist[t]), path[::-1]

    def route(self, a_px, b_px):
        """Fastest route from a to b (map px). Returns (seconds, [(u, v), ...])."""
        Wc = self.shape[1]
        s, t = self._ends(a_px, b_px)
        cost, path = self._search(self.G, s, t)
        return cost, [self.to_px(i // Wc, i % Wc) for i in path]

    def _corridor(self, path, radius_m):
        """Cells within radius_m of a path (cell indices), as a boolean grid."""
        Hc, Wc = self.shape
        on = np.ones((Hc, Wc), bool)
        on.ravel()[path] = False
        return distance_transform_edt(on) * self.cell <= radius_m

    def alternatives(self, a_px, b_px, k=2, best=None):
        """Up to k more routes from a to b that differ from the best one (and from each other).

        best: (seconds, [(u, v)]) as route() returned it, to save one search. Each candidate is the
        cheapest path after the corridors of the routes found so far were made ALT_PENALTY times more
        expensive; it is kept when at least ALT_MIN_APART of its length runs outside those corridors and
        its real cost is at most ALT_MAX_SLOWER above the best. Returns [(seconds, [(u, v)]), ...] with
        the real (unpenalised) cost, cheapest first.
        """
        Hc, Wc = self.shape
        s, t = self._ends(a_px, b_px)
        if best is None:
            t0, p0 = self._search(self.G, s, t)
        else:
            t0 = best[0]
            p0 = [r * Wc + c for r, c in (self.to_cell(u, v) for u, v in best[1])]
        if not p0 or not np.isfinite(t0):
            return []
        limit = t0 * (1 + ALT_MAX_SLOWER) + ALT_MAX_SLOWER_S
        found = [p0]
        near = self._corridor(p0, CORRIDOR_M)
        # the corridor is not penalised around the two controls: every route has to start and end there
        ends = np.zeros((Hc, Wc), bool)
        ends.ravel()[[s, t]] = True
        free = distance_transform_edt(~ends) * self.cell <= 2 * CORRIDOR_M
        out = []
        for _ in range(2 * k):
            if len(out) >= k:
                break
            pen = (near & ~free).ravel()
            G = self.G.copy()
            G.data = G.data * np.where(pen[G.indices], ALT_PENALTY, 1.0)
            _, p = self._search(G, s, t, limit=limit * ALT_PENALTY)
            if not p:
                break
            real = float(sum(self.G[i, j] for i, j in zip(p, p[1:])))
            apart = float(np.mean(~near.ravel()[p]))
            near |= self._corridor(p, CORRIDOR_M)
            if apart < ALT_MIN_APART or real > limit or any(p == q for q in found):
                continue
            found.append(p)
            out.append((real, [self.to_px(i // Wc, i % Wc) for i in p]))
        return sorted(out, key=lambda r: r[0])


def _dist_to_line(pts, line):
    """Distance in pixels from each point (n, 2) to a polyline (m, 2)."""
    a, d = line[:-1], np.diff(line, axis=0)
    w = pts[:, None, :] - a[None]
    t = np.clip((w * d[None]).sum(-1) / np.maximum((d ** 2).sum(-1), 1e-9)[None], 0, 1)
    return np.hypot(*np.moveaxis(w - t[..., None] * d[None], -1, 0)).min(1)


def crossed(pts_px, barriers, mpp):
    """What a line in map px (the track of a leg) went through although the routes must not:
    [dict(kind="line" | "area" | "enclosure", what, px=(u, v) where)], at most one for every forbidden line
    and one for all the areas of a kind. barriers: as Grid takes them; origin (a list beside forbidden: what
    each line is, see mapdata.barriers) names the lines.

    A forbidden line counts when the track cuts it farther than CROSSING_M from a crossing point and gets
    SIDE_M away from it on both sides (a track along a railway wobbles over it without crossing). An area
    or fenced ground counts when INSIDE_M of the track lie EDGE_M inside it. Hard lines are not forbidden."""
    b = barriers or {}
    P = np.asarray(pts_px, float)
    out = []
    if len(P) < 2:
        return out
    origin = b.get("origin") or []
    free = np.asarray(b.get("crossings") or [], float).reshape(-1, 2)
    for n, line in enumerate(b.get("forbidden") or []):
        Q = np.asarray(line, float)
        if len(Q) < 2:
            continue
        p, r = P[:-1, None], np.diff(P, axis=0)[:, None]
        q, s = Q[None, :-1], np.diff(Q, axis=0)[None]
        den = r[..., 0] * s[..., 1] - r[..., 1] * s[..., 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = ((q - p)[..., 0] * s[..., 1] - (q - p)[..., 1] * s[..., 0]) / den
            u = ((q - p)[..., 0] * r[..., 1] - (q - p)[..., 1] * r[..., 0]) / den
        hit = np.nonzero(((den != 0) & (t >= 0) & (t < 1) & (u >= 0) & (u <= 1)).any(1))[0]
        if not len(hit):
            continue
        far = _dist_to_line(P, Q) * mpp
        cuts = [0, *(hit + 1), len(P)]            # the track between two cuts lies on one side of the line
        for k, i in enumerate(hit):
            j = int(np.nonzero((den[i] != 0) & (t[i] >= 0) & (t[i] < 1) & (u[i] >= 0) & (u[i] <= 1))[0][0])
            at = P[i] + t[i, j] * (P[i + 1] - P[i])
            if len(free) and (np.hypot(*(free - at).T) * mpp <= CROSSING_M).any():
                continue
            if far[cuts[k]:cuts[k + 1]].max() >= SIDE_M and far[cuts[k + 1]:cuts[k + 2]].max() >= SIDE_M:
                what = origin[n].get("what") if n < len(origin) else None
                out.append(dict(kind="line", what=what or "manual", px=(float(at[0]), float(at[1]))))
                break
    # the track every 2 m, and what is impassable in a cut-out around it
    seg = np.hypot(*np.diff(P, axis=0).T) * mpp
    along = np.r_[0, np.cumsum(seg)]
    q = np.arange(0, along[-1] + 1e-9, 2.0)
    uu, vv = np.interp(q, along, P[:, 0]), np.interp(q, along, P[:, 1])
    pad = int(EDGE_M / mpp) + 3
    u0, v0 = int(uu.min()) - pad, int(vv.min()) - pad
    W, H = int(uu.max()) + pad + 1 - u0, int(vv.max()) + pad + 1 - v0
    masks = []
    if b.get("areas"):
        im = Image.new("1", (W, H), 0)
        d = ImageDraw.Draw(im)
        for poly in b["areas"]:
            if len(poly) >= 3:
                d.polygon([(x - u0, y - v0) for x, y in poly], fill=1, outline=1)
        masks.append(("area", np.array(im, bool)))
    if b.get("mask") is not None:
        full = np.asarray(b["mask"], bool)
        cut = np.zeros((H, W), bool)
        a0, a1, b0, b1 = max(v0, 0), min(v0 + H, full.shape[0]), max(u0, 0), min(u0 + W, full.shape[1])
        if a1 > a0 and b1 > b0:
            cut[a0 - v0:a1 - v0, b0 - u0:b1 - u0] = full[a0:a1, b0:b1]
        masks.append(("enclosure", cut))
    for kind, m in masks:
        deep = distance_transform_edt(m) * mpp >= EDGE_M
        inside = deep[np.clip(np.round(vv).astype(int) - v0, 0, H - 1), np.clip(np.round(uu).astype(int) - u0, 0, W - 1)]
        if inside.sum() * 2.0 >= INSIDE_M:
            k = int(np.nonzero(inside)[0][inside.sum() // 2])
            out.append(dict(kind=kind, what=kind, px=(float(uu[k]), float(vv[k]))))
    return out


def slope_field(height, mpp):
    """Gradient of the terrain (gu, gv): metres of height per metre along the picture's u and v axes."""
    gv, gu = np.gradient(np.asarray(height, np.float32), mpp)
    return gu, gv


def cross_slope(field, u, v, du, dv):
    """How steep the hillside is across the direction of travel (|dz/dm|), at map pixels (u, v) for steps
    (du, dv): the part of the terrain gradient at right angles to the step. Running along a contour on a
    steep hillside has no climb but a large cross slope."""
    gu, gv = field
    ui = np.clip(np.round(u).astype(int), 0, gu.shape[1] - 1)
    vi = np.clip(np.round(v).astype(int), 0, gu.shape[0] - 1)
    n = np.maximum(np.hypot(du, dv), 1e-9)
    return np.abs(gu[vi, ui] * dv - gv[vi, ui] * du) / n


def neighbour_shares(cls, u, v, radius_px, n_classes=len(T.NAMES)):
    """Share of every terrain class at nine points around (u, v): the point itself and eight on a circle of
    radius_px. GPS is a few metres off, so the single pixel under a track point is often the neighbouring
    terrain; the shares say what is around. Shape (len(u), n_classes), rows sum to 1."""
    ang = np.arange(8) * np.pi / 4
    uu = np.r_[[np.asarray(u)], [u + radius_px * np.cos(a) for a in ang]]
    vv = np.r_[[np.asarray(v)], [v + radius_px * np.sin(a) for a in ang]]
    c = cls[np.clip(np.round(vv).astype(int), 0, cls.shape[0] - 1), np.clip(np.round(uu).astype(int), 0, cls.shape[1] - 1)]
    return np.stack([(c == k).mean(0) for k in range(n_classes)], 1).astype(np.float32)


def along_path(u, v, cls, mpp, side_m=PATH_SIDE_M):
    """For the points (u, v) of a runner's track (map px, in order): True where the track runs along a path no
    farther than side_m from it, on a stretch at least PATH_RUN_M long. Along means: over PATH_WINDOW_M before
    and after the point, the nearest point of the path moves with the track (PATH_ALONG of the way, within
    PATH_ANGLE_DEG of its direction), so a track that only crosses a path, or runs up to it and away, is not on it."""
    u, v = np.asarray(u, float), np.asarray(v, float)
    out = np.zeros(len(u), bool)
    path = cls == T.PATH
    if len(u) < 3 or not path.any():
        return out
    pad = int(side_m / mpp) + 3
    H, W = cls.shape
    ui = np.clip(np.round(u).astype(int), 0, W - 1)
    vi = np.clip(np.round(v).astype(int), 0, H - 1)
    v0, u0 = max(int(vi.min()) - pad, 0), max(int(ui.min()) - pad, 0)
    cut = path[v0:int(vi.max()) + pad + 1, u0:int(ui.max()) + pad + 1]
    if not cut.any():
        return out
    far, (iy, ix) = distance_transform_edt(~cut, return_indices=True)
    at = (vi - v0, ui - u0)
    close = far[at] * mpp <= side_m
    nu, nv = ix[at].astype(float), iy[at].astype(float)
    s = np.r_[0, np.cumsum(np.hypot(np.diff(u), np.diff(v)))] * mpp
    a = np.clip(np.searchsorted(s, s - PATH_WINDOW_M), 0, len(s) - 1)
    b = np.clip(np.searchsorted(s, s + PATH_WINDOW_M), 0, len(s) - 1)
    tu, tv = u[b] - u[a], v[b] - v[a]
    pu, pv = nu[b] - nu[a], nv[b] - nv[a]
    lt, lp = np.hypot(tu, tv), np.hypot(pu, pv)
    cos = (tu * pu + tv * pv) / np.maximum(lt * lp, 1e-9)
    ok = close & close[a] & close[b] & (lp >= PATH_ALONG * lt) & (cos >= np.cos(np.radians(PATH_ANGLE_DEG))) & (lt > 0)
    # only stretches long enough
    edges = np.diff(np.r_[0, ok.astype(np.int8), 0])
    for i, j in zip(np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]):
        if s[j - 1] - s[i] >= PATH_RUN_M:
            out[i:j] = True
    return out


def route_samples(pts_px, cls, height, mpp, sample_m=2.0, beside_m=0.0, on_path_m=0.0):
    """Resample a polyline in map px every sample_m metres: piece lengths d (m), terrain class and grade
    of each piece, plus the heights at the sample points.
    beside_m: for the track of a runner. A sample on impassable ground (a building, water, out of bounds)
    takes the class of the nearest passable ground when that lies within beside_m: a track along a street
    between gardens wobbles into them by the error of GPS, and was priced at a walk there.
    on_path_m: for the track of a runner too. Where it runs along a path no farther than this from it
    (along_path), it is on the path: GPS and the placing of the map are metres off, the runner was not."""
    pts = np.asarray(pts_px, float)
    seg = np.hypot(*np.diff(pts, axis=0).T) * mpp
    s = np.r_[0, np.cumsum(seg)]
    L = s[-1]
    q = np.arange(0, L + 1e-9, sample_m)
    if q[-1] < L:
        q = np.r_[q, L]
    u = np.interp(q, s, pts[:, 0])
    v = np.interp(q, s, pts[:, 1])
    ui = np.clip(np.round(u).astype(int), 0, cls.shape[1] - 1)
    vi = np.clip(np.round(v).astype(int), 0, cls.shape[0] - 1)
    c = cls[vi, ui]
    off = np.isin(c, IMPASSABLE) if beside_m else np.zeros(len(c), bool)
    if off.any():
        pad = int(beside_m / mpp) + 2
        v0, u0 = max(int(vi[off].min()) - pad, 0), max(int(ui[off].min()) - pad, 0)
        cut = cls[v0:int(vi[off].max()) + pad + 1, u0:int(ui[off].max()) + pad + 1]
        far, (iy, ix) = distance_transform_edt(np.isin(cut, IMPASSABLE), return_indices=True)
        at = (vi[off] - v0, ui[off] - u0)
        c = c.copy()
        c[off] = np.where(far[at] * mpp <= beside_m, cut[iy[at], ix[at]], c[off])
    if on_path_m:
        on = along_path(u, v, cls, mpp, on_path_m)
        if on.any():
            c = c.copy()
            c[on] = T.PATH
    h = height[vi, ui]
    d = np.diff(q)
    return d, c[1:], np.diff(h) / np.maximum(d, 1e-6), h


def route_pace(model, cm, g):
    pace = model.pace(cm, g)
    return np.where(np.isfinite(pace), pace, model.pace(T.WALK, g))  # GPS through 'impassable' -> walk


def route_metrics(pts_px, cls, height, mpp, model, sample_m=2.0, beside_m=0.0, on_path_m=0.0):
    """Distance, climb, model time and terrain mix along a polyline in map px (beside_m, on_path_m: see
    route_samples)."""
    if len(pts_px) < 2:
        return None
    d, cm, g, h = route_samples(pts_px, cls, height, mpp, sample_m, beside_m, on_path_m)
    L = float(d.sum())
    dh = np.diff(h)
    pace = route_pace(model, cm, g)
    mix = {}
    for k in np.unique(cm):
        mix[T.NAMES[int(k)]] = float(d[cm == k].sum())
    return dict(dist=float(L), climb=float(np.clip(dh, 0, None).sum()), descent=float(np.clip(-dh, 0, None).sum()),
                time=float((pace * d).sum()), mix=mix, max_h=float(h.max()), min_h=float(h.min()))
