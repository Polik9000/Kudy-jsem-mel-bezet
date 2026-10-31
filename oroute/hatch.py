"""Out-of-bounds areas read from the purple hatching of a map with the course (ISOM 709).

usage: python3 -m oroute.hatch COURSE.kmz OUT.json     (OUT.json can be given to bestroute.py --barriers)

Cross-hatching is two families of thin purple lines at 45 degrees, so it cuts the map into many small closed
cells with slanted sides. The course itself makes few closed shapes (a control circle, the inside of an "8"),
and those are big, round or come one or two at a time. So:
  1. take every small gap closed in by the purple overprint (black map lines count as walls too: the purple
     disappears under them, a road edge would otherwise open every cell along it),
  2. keep the gaps whose border is mostly purple and mostly slanted: the cells,
  3. the size of a cell is the same all over the map; it is taken from the places where at least MIN_CELLS
     cells lie tightly together,
  4. cells no further apart than about one cell belong to one area; an area needs MIN_CELLS cells.

Hatching of parallel vertical lines (older maps, sprint maps) has no closed cells. It is found as many thin
purple strokes that run straight up the map side by side at even distances (_stripes): at least MIN_STRIPES
of them, each at least STRIPE_MIN_M long. A leg that happens to run north, the sides of a control circle and
the strokes of digits and letters are purple and vertical too, but they come alone or unevenly spaced.

Limits: an out-of-bounds line (ISOM 708) is not read: one purple line cannot be told from a leg of the course
by its look, and there is no map to check it on. Neither is the olive area (520, that one is read from the
map without the course in oroute/terrain.py). Vertical hatching was only tried on drawn maps (tests), the four
maps of data/ have none. A patch of fewer than MIN_CELLS cells is left out, and a strip one cell wide along a
road is found only where its cells are whole, so it may come out in pieces.
"""
import json
import sys

import numpy as np
from scipy import ndimage as ndi

from .course import purple_mask

CELL_MAX_M = 25.0    # a cell is at most this wide (the 0.8 mm line spacing is 12 m on a 1:15 000 map)
CELL_MIN_M2 = 6.0    # ... and at least this big; smaller gaps are noise where the purple runs over a dark symbol
MIN_CELLS = 6        # fewer cells together are digits and letters, not hatching
JOIN_M = 2.0         # cells closer than this (plus 2 px) lie tightly together: only a hatching line between them
PURPLE_SHARE = 0.5   # at least this much of a cell's border is purple (the rest is black map lines)
SLANT_SHARE = 0.6    # at least this much of the purple border runs at 45 degrees (a circle has a third)
SLANT = 0.58         # "at 45 degrees" = within 15 degrees of it: tan(30 deg)
OUTLINE_M = 2.0      # the outline is traced on a grid about this fine and simplified to that precision
STRIPE_MIN_M = 12.0  # a line of vertical hatching runs at least this far straight up the map ...
STRIPE_WIDE_M = 4.0  # ... and is thinner than this
STRIPE_GAP_M = (2.5, 13.0)   # distance between neighbouring lines (0.6 to 0.8 mm on the map)
MIN_STRIPES = 6      # fewer lines side by side are digits, letters or legs, not hatching
STRIPE_EVEN = 0.25   # the lines are evenly spaced: most gaps within this share of the usual one


def _disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def _cells(gm):
    """(labels of the closed gaps, boolean 'is a hatching cell' per label, area in pixels per label)."""
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    rgb = np.asarray(gm.image).astype(np.int32)
    P = purple_mask(gm.image)
    P[:gm.header_px] = False
    r = int(round(1.2 / mpp))  # the purple also breaks where it crosses a brown contour: bridge gaps of about 2 m
    if r >= 1:
        P = ndi.binary_closing(P, structure=_disk(r))
    dark = (rgb.mean(-1) < 110) & ~P
    lab, n = ndi.label(~(P | dark))  # 4-connected, so a diagonal line one pixel thick still closes a cell
    area = np.bincount(lab.ravel(), minlength=n + 1)
    ok = np.zeros(n + 1, bool)
    if not n:
        return lab, ok, area
    # which way the purple edge runs at each wall pixel: the gradient of the mask (no blur: a cell can be 5 px wide)
    soft = P.astype(np.float32)
    gx, gy = np.abs(ndi.sobel(soft, 1)), np.abs(ndi.sobel(soft, 0))
    slant = np.minimum(gx, gy) >= SLANT * np.maximum(gx, gy)
    purple, black, slanted = (np.zeros(n + 1) for _ in range(3))
    for axis in (0, 1):
        for shift in (1, -1):
            nb = np.roll(lab, shift, axis)  # the gap next to each wall pixel on this side
            purple += np.bincount(nb[P & (nb > 0)], minlength=n + 1)
            black += np.bincount(nb[dark & (nb > 0)], minlength=n + 1)
            slanted += np.bincount(nb[P & slant & (nb > 0)], minlength=n + 1)
    sl = ndi.find_objects(lab)
    h = np.array([s[0].stop - s[0].start for s in sl])
    w = np.array([s[1].stop - s[1].start for s in sl])
    a = area[1:]
    ok[1:] = (a >= max(4.0, CELL_MIN_M2 / mpp ** 2)) & (a <= (CELL_MAX_M / mpp) ** 2) \
        & (np.maximum(h, w) <= 3 * np.minimum(h, w)) & (a >= 0.25 * h * w) \
        & (purple[1:] > 0) & (purple[1:] >= PURPLE_SHARE * (purple[1:] + black[1:])) \
        & (slanted[1:] >= SLANT_SHARE * purple[1:])
    return lab, ok, area


def _groups(cells, lab, ids, reach):
    """Cells no further than `reach` pixels apart form a group.
    Returns (group labels, group of each cell in ids, number of cells per group)."""
    grp, n = ndi.label(ndi.distance_transform_edt(~cells) <= reach / 2)
    of = ndi.maximum(grp, lab, ids).astype(int)
    return grp, of, np.bincount(of, minlength=n + 1)


def _loops(mask):
    """Boundary of a boolean mask as closed loops of pixel-corner points [(x, y), ...], the inside on the right."""
    m = np.pad(mask, 1)
    nxt = {}
    for (dy, dx), (ax, ay), (bx, by) in (((-1, 0), (0, 0), (1, 0)), ((0, 1), (1, 0), (1, 1)),
                                         ((1, 0), (1, 1), (0, 1)), ((0, -1), (0, 1), (0, 0))):
        ys, xs = np.nonzero(m & ~np.roll(m, (-dy, -dx), (0, 1)))
        for y, x in zip(ys.tolist(), xs.tolist()):
            nxt.setdefault((x + ax - 1, y + ay - 1), []).append((x + bx - 1, y + by - 1))
    loops = []
    while nxt:
        # start at a corner with one way out, so the walk is back at its start exactly when the loop is closed
        start = p = next(c for c, out in nxt.items() if len(out) == 1)
        d, loop = None, []
        while True:
            out = nxt[p]
            q = out[0]
            if len(out) > 1:  # two pixels touch by a corner here: turn right, which stays with the same pixel
                q = next((c for c in out if (c[0] - p[0], c[1] - p[1]) == (-d[1], d[0])), q)
            out.remove(q)
            if not out:
                del nxt[p]
            loop.append(p)
            d, p = (q[0] - p[0], q[1] - p[1]), q
            if p == start:
                break
        loops.append(loop)
    return loops


def _simplify(pts, tol):
    """Douglas-Peucker on a closed loop."""
    p = np.asarray(pts, float)
    if len(p) < 5:
        return p
    far = int(np.argmax(((p - p[0]) ** 2).sum(1)))
    q = np.vstack([p, p[:1]])
    keep = np.zeros(len(q), bool)
    keep[[0, far, len(p)]] = True
    stack = [(0, far), (far, len(p))]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        ab = q[j] - q[i]
        seg = q[i + 1:j] - q[i]
        L = np.hypot(*ab)
        dist = np.abs(ab[0] * seg[:, 1] - ab[1] * seg[:, 0]) / L if L else np.hypot(seg[:, 0], seg[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return q[keep][:-1]


def _outlines(region, x0, y0, mpp, **about):
    """The outlines of a filled region (a cut-out of the map at x0, y0) as the dicts detect() returns."""
    f = max(1, int(round(OUTLINE_M / mpp)))
    H, W = (region.shape[0] + f - 1) // f * f, (region.shape[1] + f - 1) // f * f
    coarse = np.pad(region, ((0, H - region.shape[0]), (0, W - region.shape[1])))
    coarse = ndi.binary_fill_holes(coarse.reshape(H // f, f, W // f, f).any((1, 3)))
    out = []
    for loop in _loops(coarse):
        px = _simplify(loop, 1.0) * f + (x0, y0)
        if len(px) < 3:
            continue
        x, y = px[:, 0], px[:, 1]
        m2 = abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2 * mpp ** 2
        out.append(dict(px=[(float(u), float(v)) for u, v in px], area_m2=round(m2), **about))
    return out


def _crossed(gm):
    """Areas of cross-hatching: see the top of the file."""
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    lab, ok, area = _cells(gm)
    ids = np.nonzero(ok)[0]
    if len(ids) < MIN_CELLS:
        return []
    cells = ok[lab]
    _, of, count = _groups(cells, lab, ids, 2 * (JOIN_M / mpp + 2))
    tight = count[of] >= MIN_CELLS
    if not tight.any():
        return []
    side = float(np.percentile(area[ids[tight]], 75)) ** 0.5  # whole cells; the ones cut by a map line are smaller
    grp, of, count = _groups(cells, lab, ids, 1.5 * side)
    f = max(1, int(round(OUTLINE_M / mpp)))
    out = []
    for g, s in enumerate(ndi.find_objects(grp), 1):
        if count[g] < MIN_CELLS:
            continue
        pad = int(1.5 * side) + f + 1
        y0, x0 = max(s[0].start - pad, 0), max(s[1].start - pad, 0)
        box = (slice(y0, min(s[0].stop + pad, grp.shape[0])), slice(x0, min(s[1].stop + pad, grp.shape[1])))
        mine = cells[box] & (grp[box] == g)
        # close the gaps between the cells, then keep half a cell around them: the cells at the edge of the
        # hatching are open and were not counted
        region = ndi.distance_transform_edt(ndi.distance_transform_edt(~mine) <= 0.75 * side) >= 0.25 * side
        out += _outlines(region, x0, y0, mpp, cells=int(count[g]), cell_m=round(side * mpp, 1))
    return out


def _stripes(gm):
    """Areas hatched with parallel vertical purple lines: many thin strokes straight up the map, side by side
    at even distances. `cells` is the number of lines, `cell_m` the distance between them."""
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    P = purple_mask(gm.image)
    P[:gm.header_px] = False
    tall = max(3, int(round(STRIPE_MIN_M / mpp)))
    wide = max(4, int(round(STRIPE_WIDE_M / mpp)) + 1)
    # strokes: purple that runs at least `tall` pixels straight up and is nowhere `wide` pixels across
    strokes = ndi.binary_opening(P, structure=np.ones((tall, 1), bool)) \
        & ~ndi.binary_opening(P, structure=np.ones((1, wide), bool))
    lab, n = ndi.label(strokes, structure=np.ones((3, 3)))
    if n < MIN_STRIPES:
        return []
    col = np.asarray(ndi.center_of_mass(strokes, lab, range(1, n + 1)))[:, 1]
    reach = int(round(STRIPE_GAP_M[1] / mpp))
    up = max(1, int(round(STRIPE_WIDE_M / mpp)))     # a road or a contour across the hatching does not split it
    # strokes no further apart sideways than the widest gap of a hatching belong together
    grp, m = ndi.label(ndi.binary_dilation(strokes, structure=np.ones((2 * up + 1, 2 * (reach // 2) + 1), bool)))
    of = ndi.maximum(grp, lab, range(1, n + 1)).astype(int)
    out = []
    for g, s in enumerate(ndi.find_objects(grp), 1):
        xs = np.sort(col[of == g])
        if len(xs) < MIN_STRIPES:
            continue
        xs = xs[np.r_[True, np.diff(xs) > 1.5]]      # a line broken by a map symbol is still one line
        gaps = np.diff(xs)
        if len(xs) < MIN_STRIPES:
            continue
        usual = float(np.median(gaps))
        even = np.abs(gaps - usual) <= max(1.0, STRIPE_EVEN * usual)
        if not STRIPE_GAP_M[0] <= usual * mpp <= STRIPE_GAP_M[1] or even.mean() < 0.7:
            continue
        pad = int(usual) + 2
        y0, x0 = max(s[0].start - pad, 0), max(s[1].start - pad, 0)
        box = (slice(y0, min(s[0].stop + pad, grp.shape[0])), slice(x0, min(s[1].stop + pad, grp.shape[1])))
        mine = strokes[box] & (grp[box] == g)
        # fill between the lines, and half a gap around them
        region = ndi.binary_dilation(mine, structure=np.ones((2 * up + 1, 2 * int(round(0.6 * usual)) + 1), bool))
        out += _outlines(region, x0, y0, mpp, cells=int(len(xs)), cell_m=round(usual * mpp, 1), lines="vertical")
    return out


def detect(gm):
    """Out-of-bounds areas on the map with the course `gm` (oroute.kmzmap.GeoMap).

    Returns [dict(px=[(u, v), ...] outline in map pixels, cells=number of hatching cells (or of lines),
    cell_m=side of a cell (or distance of the lines) in metres, area_m2=...; lines="vertical" for hatching of
    parallel lines)], biggest first.
    """
    return sorted(_crossed(gm) + _stripes(gm), key=lambda r: -r["area_m2"])


def to_latlon(gm, areas):
    """The outlines of detect() as [[lat, lon], ...] rings (what barriers.json and the web app keep)."""
    rings = []
    for r in areas:
        la, lo = gm.px_to_latlon([p[0] for p in r["px"]], [p[1] for p in r["px"]])
        rings.append([[round(float(a), 6), round(float(b), 6)] for a, b in zip(la, lo)])
    return rings


def main():
    from .kmzmap import GeoMap
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    gm = GeoMap.from_kmz(sys.argv[1])
    areas = detect(gm)
    for r in areas:
        what = f"{r['cells']} vertical lines {r['cell_m']} m apart" if r.get("lines") else \
            f"{r['cells']} cells of {r['cell_m']} m"
        print(f"out-of-bounds area: {r['area_m2']} m2, {what}")
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(dict(lines=[], crossings=[], areas=to_latlon(gm, areas)), f)
    print(f"{len(areas)} area(s) -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
