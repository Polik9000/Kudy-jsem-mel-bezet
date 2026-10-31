"""Two screenshots of Livelox from the same view: one with the course, one with the course switched off.

The screenshot with the course is placed like any picture of the map with the course (oroute/georef.py: control
circles against the runner's track at the official punch times), but flat: a screenshot is a straight picture of the
map. The screenshot without the course has the same pixels (same view, same zoom), so the same placing serves it, and
it becomes the map without course from which the terrain is read (oroute/terrain.py) as from a Livelox KMZ.

What has to be checked before that is believed:
  - the two belong together: same size, and outside the purple of the course the same picture, maybe moved by a few
    pixels (the map was nudged between the two); a change of zoom or rotation, or another map, is refused;
  - which one has the course (swapped ones are swapped back) and that the other one really has none;
  - no routes of other runners (coloured lines that are not ISOM colours) over the map;
  - what on the screenshot is the map: the bar, the list of runners, the buttons and the grey page around the map
    are not, and become white, which the reading of the terrain takes for outside the map (as the white margin of a
    KMZ picture).

Everything here works on copies about SMALL_PX large, except the placing (a copy WORK_PX large) and the pictures
kept (cut out of the full screenshots).
"""
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from . import georef
from . import terrain as T
from .course import purple_mask

SMALL_PX = 1600          # the pair is compared, and the map looked for, on copies this large
WORK_PX = georef.MAX_SIDE_PX   # the screenshot with the course is placed on a copy this large
MAX_OUT_PX = 20_000_000  # the pictures kept are at most this large (pixels); a sharper screenshot is scaled down
WARN_M_PER_PX = 2.0      # coarser than this: the terrain is read less well (a Livelox KMZ has about 1.33)
MAX_M_PER_PX = 3.0       # ... and coarser than this the map without course is not kept at all
ACCURACY_MIN_M = 10.0    # the accuracy shown is never better than this
OPAQUE = 0.5             # the one without the course has at least this many pixels of its exact purple: it is on
FAINT_MIN = 0.04         # the course left on the screenshot without it at least this opaque is taken out
COARSEST_KEPT = T.REF_M_PER_PX   # a zoomed map is made less sharp at most down to this (metres per pixel)
BILINEAR_SIGMA = 0.41            # a bilinear resampling blurs like a gaussian of this sigma (pixels of the coarser side)

COURSE_SHARE = 0.001     # purple on at least this share of the map: the screenshot shows a course
ROUTE_SHARE = 1.5        # lines in route colours together at least this long (times the map's longer side): routes
ROUTE_LEN_PX = 25        # ... in pieces at least this long (on the small copy)
ROUTE_CORE = 0.25        # ... and thin: at most this share of a piece is left after taking two pixels off its edge
TILE_PEAK = 0.08         # a tile of the pair matches when its phase correlation peaks at least this high
TILES_NEED = 0.5         # ... and at least this share of the tiles with map in them have to match
SCALE_TOL = 0.004        # displacements that change by more than this per pixel: the zoom or the rotation changed
FIT_TOL_PX = 1.5         # tiles further than this (small px) from a common shift: the pictures do not belong together
DIFF_MAX = 0.08          # after the shift, more than this share of the map differs outside the course: not one view
SHIFT_MAX = 0.1          # a shift of more than this share of the screenshot is not "the same view"
OUTSIDE_COLOUR = 0.01    # the map is found clearly when at most this share of what is around it has map colours

PALETTE = np.array(list(T.AREA) + list(T.LINE.values()), np.float32)   # white and black included
MAP_COLOURS = np.array([c for c in list(T.AREA) + list(T.LINE.values())
                        if max(c) - min(c) >= 30 and c != T.LINE["purple"]], np.float32)


class PairError(Exception):
    """The pair cannot be used. code: size, no_course, course_in_maponly, routes, zoom, far, unrelated, no_fit;
    data: what the sentence for the user needs."""

    def __init__(self, code, **data):
        super().__init__(code + (f" {data}" if data else ""))
        self.code = code
        self.data = data


def small(image, side=SMALL_PX):
    """(uint8 array of a copy at most side large, (kx, ky) = full pixels per small pixel)."""
    W, H = image.size
    k = max(1.0, max(W, H) / side)
    w, h = max(1, int(round(W / k))), max(1, int(round(H / k)))
    a = np.asarray(image.convert("RGB").resize((w, h), Image.BOX))
    return a, (W / w, H / h)


def _disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def mix_distance(a, chunk=60_000):
    """How far every pixel is from the ISOM palette of Livelox and from every mix of two of its colours (the
    smoothed edge between two colours, a line blurred by the zoom): float32 array of the picture's shape."""
    X = a.reshape(-1, 3).astype(np.float32)
    out = np.empty(len(X), np.float32)
    P = PALETTE
    pairs = [(i, j) for i in range(len(P)) for j in range(i + 1, len(P))]
    for s in range(0, len(X), chunk):
        x = X[s:s + chunk]
        best = np.full(len(x), np.inf, np.float32)
        for i, j in pairs:
            d = P[j] - P[i]
            t = np.clip((x - P[i]) @ d / float(d @ d), 0.0, 1.0)
            best = np.minimum(best, np.linalg.norm(x - P[i] - t[:, None] * d, axis=1))
        out[s:s + chunk] = best
    return out.reshape(a.shape[:2])


def unmix(image, flat_std=3.0, chunk=40_000):
    """A zoomed screenshot made sharp again in the palette: the browser draws a zoomed map with bilinear smoothing, so
    the edge of every line is a mix of two map colours, and a mix of brown and white is nearer to the yellow of rough
    open land than to either (oroute/terrain.py takes every pixel for its nearest palette colour). Every pixel that
    is not flat (its 3 x 3 neighbourhood varies) and lies near the mix of two palette colours becomes the one of the
    two it has more of. Flat areas keep their colour (the grey of a sprint map's buildings is no mix). Returns a new
    RGB picture."""
    a = np.array(image.convert("RGB"))
    x = a.astype(np.float32)
    mean = ndi.uniform_filter(x, (3, 3, 1))
    var = (ndi.uniform_filter(x * x, (3, 3, 1)) - mean * mean).sum(-1)
    P = PALETTE
    pal_d = np.min(np.linalg.norm(x[..., None, :] - P, axis=-1), axis=-1) if x.size <= 3 * 4_000_000 else None
    todo = var > flat_std * flat_std * 3
    if pal_d is not None:
        todo &= pal_d > 4
    idx = np.flatnonzero(todo.ravel())
    if not len(idx):
        return Image.fromarray(a)
    pairs = np.array([(i, j) for i in range(len(P)) for j in range(i + 1, len(P))])
    Pi, D = P[pairs[:, 0]], P[pairs[:, 1]] - P[pairs[:, 0]]           # (K, 3)
    DD = (D * D).sum(1)
    flat = a.reshape(-1, 3)
    X = x.reshape(-1, 3)
    for s in range(0, len(idx), chunk):
        ii = idx[s:s + chunk]
        q = X[ii]                                                      # (n, 3)
        rel = q[:, None, :] - Pi[None]                                 # (n, K, 3)
        t = np.clip((rel * D[None]).sum(-1) / DD[None], 0.0, 1.0)      # (n, K)
        dist = np.linalg.norm(rel - t[..., None] * D[None], axis=-1)
        k = dist.argmin(1)
        tk = t[np.arange(len(ii)), k]
        dk = dist[np.arange(len(ii)), k]
        ends = np.where(tk < 0.5, pairs[k, 0], pairs[k, 1])
        near = dk <= 18
        flat[ii[near]] = P[ends[near]].astype(np.uint8)
    return Image.fromarray(a)


def map_colour(a):
    """Pixels in one of the coloured map colours (brown, yellow, green, blue, olive): the page of Livelox around the
    map has none of them in large numbers (grey, white, black text)."""
    x = a.astype(np.float32)
    chroma = x.max(-1) - x.min(-1)
    d = np.min(np.linalg.norm(x[..., None, :] - MAP_COLOURS, axis=-1), axis=-1)
    return (chroma >= 25) & (d <= 40)


def _hull_mask(mask):
    """The convex hull of a mask, as a mask, and the share of its smallest enclosing rectangle it fills."""
    from scipy.spatial import ConvexHull
    ys, xs = np.nonzero(mask ^ ndi.binary_erosion(mask))
    pts = np.c_[xs, ys].astype(float)
    if len(pts) < 3:
        return mask, 0.0
    hull = pts[ConvexHull(pts).vertices]
    img = Image.new("L", (mask.shape[1], mask.shape[0]), 0)
    ImageDraw.Draw(img).polygon([tuple(p) for p in hull], fill=255, outline=255)
    out = np.asarray(img) > 0
    # the smallest rectangle around the hull: one of its sides lies along a side of the hull
    best = np.inf
    for i in range(len(hull)):
        e = hull[(i + 1) % len(hull)] - hull[i]
        L = np.hypot(*e)
        if L == 0:
            continue
        u = e / L
        v = np.array([-u[1], u[0]])
        pu, pv = hull @ u, hull @ v
        best = min(best, (pu.max() - pu.min()) * (pv.max() - pv.min()))
    return out, float(out.sum() / best) if np.isfinite(best) and best > 0 else 0.0


def _bands(g, mask, share=0.8, step=24):
    """Bands of the page of Livelox drawn over the edge of the map (a bar, a slider, half see-through or not): a
    straight edge across the whole width (or height) of the mask's box where the brightness changes the same way in
    most columns (rows). Returns the mask with what lies beyond such an edge (towards the nearer side of the box,
    within 15 % of it) taken off. A map has no edge like that across all of it, other than its own border."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return mask
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = mask.copy()
    gi = g.astype(np.int16)
    for axis in (0, 1):
        lo, hi = (y0, y1) if axis == 0 else (x0, x1)
        lim = int(0.15 * (hi - lo))
        part = gi[:, x0:x1] if axis == 0 else gi[y0:y1, :].T
        d = np.diff(part, axis=0)                          # change from one row (column) to the next
        for side in (0, 1):
            rng = range(lo, lo + lim) if side == 0 else range(hi - 2, hi - 2 - lim, -1)
            for i in rng:
                row = d[i]
                strong = np.abs(row) >= step
                if strong.mean() >= share and abs(np.sign(row[strong]).mean()) >= 0.9:
                    cut = slice(None, i + 1) if side == 0 else slice(i + 1, None)
                    if axis == 0:
                        out[cut, :] = False
                    else:
                        out[:, cut] = False
                    break
    return out


def map_area(a):
    """Where the map is on a screenshot (small copy): dict(mask, box = (x0, y0, x1, y1), reliable, share, fill).
    The coloured map colours, closed, the largest part, its convex hull, edges covered by the page of Livelox
    trimmed, a little room added. White forest at the edge of the map may fall outside: it stays white anyway.
    reliable: the map takes up at least a sixth of the screenshot and is nearly a rectangle."""
    h, w = a.shape[:2]
    m = map_colour(a)
    r = max(3, int(round(0.012 * max(h, w))))
    # closed on a copy half as large (the time of a closing grows with the disc)
    m2 = m[::2, ::2]
    closed = ndi.binary_closing(np.pad(m2, r), structure=_disk(max(2, r // 2)))[r:-r, r:-r]
    lab, n = ndi.label(closed)
    if not n:
        return dict(mask=np.ones((h, w), bool), box=(0, 0, w, h), reliable=False, share=0.0, fill=0.0, outside=1.0)
    sizes = np.bincount(lab.ravel())[1:]
    part = lab == int(np.argmax(sizes)) + 1
    part = np.kron(part, np.ones((2, 2), bool))[:h, :w]
    if part.shape != (h, w):
        part = np.pad(part, ((0, h - part.shape[0]), (0, w - part.shape[1])))
    hull, fill = _hull_mask(part)
    colour = m
    # (the bar, the list of runners and a slider have no map colours, so the hull stops at their edge; a band drawn
    # half see-through over the map is cut off along its straight edge)
    hull = _bands(a.astype(np.float32).mean(-1), hull)
    hull = ndi.binary_dilation(hull, structure=_disk(max(1, r // 3)))
    ys, xs = np.nonzero(hull)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    share = float(hull.mean())
    around = ~ndi.binary_dilation(hull, structure=_disk(r))
    outside = float(colour[around].mean()) if around.any() else 0.0
    return dict(mask=hull, box=box, reliable=bool(share >= 1 / 6 and outside <= OUTSIDE_COLOUR), share=share,
                fill=fill, outside=outside)


def rect_area(size_small, crop, k):
    """map_area for a rectangle given by hand (full pixels x0, y0, x1, y1)."""
    w, h = size_small
    x0, y0, x1, y1 = crop
    box = (max(0, int(x0 / k[0])), max(0, int(y0 / k[1])), min(w, int(math.ceil(x1 / k[0]))),
           min(h, int(math.ceil(y1 / k[1]))))
    mask = np.zeros((h, w), bool)
    mask[box[1]:box[3], box[0]:box[2]] = True
    return dict(mask=mask, box=box, reliable=True, share=float(mask.mean()), fill=1.0, outside=0.0)


def purple(a):
    """The purple of a course on a screenshot: the exact Livelox colour, and by hue (a course drawn half see-through
    over the map)."""
    return purple_mask(a) | georef.loose_purple(a)


def course_share(a, mask):
    return float((purple(a) & mask).sum() / max(1, mask.sum()))


def has_circles(a):
    """Control circles on a small copy (find_circles): at least three of one size."""
    try:
        circles, _ = georef.find_circles(Image.fromarray(a))
    except georef.GeorefError:
        return False
    return len(circles) >= 3


def hue_sat(a):
    """(hue in degrees, saturation 0..1, value 0..1) of every pixel."""
    x = a.astype(np.float32) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx, mn = x.max(-1), x.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    return h, (mx - mn) / np.maximum(mx, 1e-6), mx


def route_colour(a):
    """Colours Livelox draws runners' routes in that no map has: a saturated red (the brown of contours and the
    orange of paved areas are yellower) and a saturated deep blue (the blue of water is cyan). Routes in orange or
    green look like map colours and are not told apart."""
    h, s, v = hue_sat(a)
    red = ((h >= 340) | (h <= 12)) & (s >= 0.55) & (v >= 0.55)
    blue = (h >= 210) & (h <= 255) & (s >= 0.6) & (v >= 0.45)
    return red | blue


def routes_share(a, mask, skip):
    """How much of routes of runners (drawn over the map by Livelox) there is: the length of the long thin lines in
    a route colour (route_colour), in multiples of the longer side of the map. Thin: what is left of a piece after
    taking two pixels off its edge is little (a logo or a coat of arms is a blob; crossing routes are a tangle,
    still thin)."""
    cand = route_colour(a) & mask & ~skip
    if not cand.any():
        return 0.0
    lab, n = ndi.label(cand, structure=np.ones((3, 3)))
    if not n:
        return 0.0
    sl = ndi.find_objects(lab)
    ext = np.array([max(s[0].stop - s[0].start, s[1].stop - s[1].start) for s in sl])
    count = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    core = np.bincount(lab[ndi.binary_erosion(cand, iterations=2)], minlength=n + 1)[1:]
    inner = np.bincount(lab[ndi.binary_erosion(cand)], minlength=n + 1)[1:]
    line = (ext >= ROUTE_LEN_PX) & (core <= ROUTE_CORE * count)
    # how long the lines are: a line w pixels wide and L long has about 2 L pixels on its edge
    length = float(((count - inner)[line] / 2).sum())
    ys, xs = np.nonzero(mask)
    side = max(np.ptp(ys), np.ptp(xs), 1) if len(ys) else 1
    return length / side


def _phase(ta, tb):
    """(dx, dy, peak): tb is ta moved by (dx, dy) pixels (sub-pixel), peak 0..1 how clearly."""
    h, w = ta.shape
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    A = np.fft.rfft2((ta - ta.mean()) * win)
    B = np.fft.rfft2((tb - tb.mean()) * win)
    R = B * np.conj(A)
    R /= np.maximum(np.abs(R), 1e-9)
    r = np.fft.irfft2(R, s=(h, w))
    iy, ix = np.unravel_index(int(np.argmax(r)), r.shape)
    peak = float(r[iy, ix])

    def sub(c, m, along):
        a_, b_, c_ = (r[(iy + d) % h, ix] if along == 0 else r[iy, (ix + d) % w] for d in (-1, 0, 1))
        den = a_ - 2 * b_ + c_
        off = 0.5 * (a_ - c_) / den if abs(den) > 1e-12 else 0.0
        v = c + float(np.clip(off, -0.5, 0.5))
        return v - m if v > m / 2 else v
    return sub(ix, w, 1), sub(iy, h, 0), peak


def tile_shifts(ga, gb, mask, skip, grid=4):
    """Phase correlation of the pair in grid x grid tiles of the map's box: [(x, y of the tile's middle, dx, dy,
    peak)] for the tiles mostly on the map. The course (skip) is greyed out in both."""
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    T_ = int(min(256, (x1 - x0) // grid, (y1 - y0) // grid))
    T_ -= T_ % 2
    out = []
    if T_ < 32:
        return out
    for i in range(grid):
        for j in range(grid):
            cx = x0 + (x1 - x0) * (i + 0.5) / grid
            cy = y0 + (y1 - y0) * (j + 0.5) / grid
            sx, sy = int(cx - T_ / 2), int(cy - T_ / 2)
            box = (slice(sy, sy + T_), slice(sx, sx + T_))
            if mask[box].mean() < 0.7:
                continue
            ta, tb = ga[box].copy(), gb[box].copy()
            s = skip[box]
            if s.mean() > 0.3:
                continue
            fill = float(np.median(ta[~s])) if (~s).any() else 255.0
            ta[s] = fill
            tb[s] = fill
            if ta.std() < 4:                      # an empty piece of the map says nothing
                continue
            dx, dy, peak = _phase(ta, tb)
            out.append((cx, cy, dx, dy, peak))
    return out


def compare(a, b, mask, skip):
    """How the screenshot without the course (b) lies against the one with it (a), small copies: dict(shift = (dx,
    dy) in small px, tiles, diff = share of the map differing after the shift, outside the course). PairError zoom
    or unrelated when they are not two views that differ by a shift only."""
    ga = a.astype(np.float32).mean(-1)
    gb = b.astype(np.float32).mean(-1)
    tiles = tile_shifts(ga, gb, mask, skip)
    good = [t for t in tiles if t[4] >= TILE_PEAK]
    if not tiles or len(good) < max(3, TILES_NEED * len(tiles)):
        raise PairError("unrelated", tiles=len(tiles), matched=len(good))
    P = np.array([(t[0], t[1], 1.0) for t in good])
    D = np.array([(t[2], t[3]) for t in good])
    coef, *_ = np.linalg.lstsq(P, D, rcond=None)          # d = A p + t
    A = coef[:2].T
    spread = max(np.ptp(P[:, 0]), np.ptp(P[:, 1]), 1.0)
    res = np.hypot(*(P @ coef - D).T)
    med = np.median(D, 0)
    if np.abs(A).max() > SCALE_TOL and np.abs(A).max() * spread > 2 * FIT_TOL_PX and res.max() <= 2 * FIT_TOL_PX:
        raise PairError("zoom", change=float(np.abs(A).max()))
    near = np.hypot(*(D - med).T) <= FIT_TOL_PX
    if near.sum() < max(3, TILES_NEED * len(tiles)):
        if np.abs(A).max() > SCALE_TOL:
            raise PairError("zoom", change=float(np.abs(A).max()))
        raise PairError("unrelated", tiles=len(tiles), matched=int(near.sum()))
    dx, dy = (float(v) for v in D[near].mean(0))
    # after the shift: how much of the map outside the course still differs
    ix, iy = int(round(dx)), int(round(dy))
    h, w = ga.shape
    sa = (slice(max(0, -iy), min(h, h - iy)), slice(max(0, -ix), min(w, w - ix)))
    sb = (slice(max(0, iy), min(h, h + iy)), slice(max(0, ix), min(w, w + ix)))
    m = mask[sa] & ~ndi.binary_dilation(skip, iterations=2)[sa]
    # a pixel differs when it lies outside what the other picture has around the same place (the shift is known
    # to a fraction of a pixel only, and a sharp edge moved by half a pixel changes by half its contrast)
    pa, pb = a[sa].astype(np.int16), b[sb].astype(np.int16)
    lo = ndi.minimum_filter(pb, size=(3, 3, 1))
    hi = ndi.maximum_filter(pb, size=(3, 3, 1))
    diff = ((pa < lo - 40) | (pa > hi + 40)).any(-1)
    if ix or iy:
        # what did not move with the map (the bar, the buttons, a slider over it) is the same in both unshifted
        still = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(-1) <= 10
        m &= ~ndi.binary_dilation(still & ~ndi.binary_erosion(still, iterations=2), iterations=1)[sa] & ~still[sa]
    share = float((diff & m).sum() / max(1, m.sum()))
    if share > DIFF_MAX:
        raise PairError("unrelated", diff=share)
    return dict(shift=(dx, dy), tiles=len(tiles), matched=int(near.sum()), diff=share)


def refine_shift(a, b, shift, mask_full_box):
    """The shift between the full screenshots, starting from the coarse one: phase correlation of a piece 1024 px
    large in the middle of the map. Returns (dx, dy) in full px."""
    x0, y0, x1, y1 = mask_full_box
    T_ = int(min(1024, (x1 - x0) // 2, (y1 - y0) // 2))
    T_ -= T_ % 2
    if T_ < 64:
        return shift
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    ix, iy = int(round(shift[0])), int(round(shift[1]))
    ba = (cx - T_ // 2, cy - T_ // 2, cx + T_ // 2, cy + T_ // 2)
    bb = (ba[0] + ix, ba[1] + iy, ba[2] + ix, ba[3] + iy)
    ta = np.asarray(a.crop(ba).convert("L"), np.float32)
    tb = np.asarray(b.crop(bb).convert("L"), np.float32)
    s = purple(np.asarray(a.crop(ba).convert("RGB")))
    s = ndi.binary_dilation(s, iterations=3)
    fill = float(np.median(ta[~s])) if (~s).any() else 255.0
    ta[s] = fill
    tb[s] = fill
    dx, dy, peak = _phase(ta, tb)
    if peak < TILE_PEAK or math.hypot(dx, dy) > 3:
        return shift
    return ix + dx, iy + dy


EDGE_STEP = 40           # an edge: brightness changing by at least this from one pixel to the next
EDGE_NATIVE = (1.05, 0.95)  # the sharpest edges of a map zoomed z times are about 1.05 + 0.95 z pixels wide
ZOOM_SAFE = 0.85         # ... and the map is kept only this much less sharp than that says (rather too sharp)


def edge_width(g, top=0.2):
    """How wide the sharpest edges of a grey picture are (median, pixels, along rows and columns): over each edge the
    whole change of brightness divided by its steepest step. A map drawn by Livelox at its own resolution has edges
    one or two pixels wide (smoothed lines); zoomed in by the browser, the bilinear smoothing makes every edge a ramp
    as long as the zoom. None without edges."""
    out = []
    for a in (g, g.T):
        d = np.diff(a.astype(np.float32), axis=1)
        mag = np.abs(d)
        peak = (mag > EDGE_STEP) & (mag >= np.roll(mag, 1, 1)) & (mag > np.roll(mag, -1, 1))
        ys, xs = np.nonzero(peak[:, 4:-4])
        xs = xs + 4
        if not len(ys):
            continue
        sgn = np.sign(d[ys, xs])
        tot = np.zeros(len(ys), np.float32)
        for o in range(-4, 5):
            v = d[ys, xs + o]
            tot += np.where(np.sign(v) == sgn, np.abs(v), 0)
        keep = tot >= np.quantile(tot, 1 - top)
        out.append((tot / mag[ys, xs])[keep])
    if not out:
        return None
    w = np.concatenate(out)
    return float(np.median(w)) if len(w) >= 200 else None


def zoom_of(image, box, side=1024, n=4):
    """How many times the browser zoomed the map in (1.0 = not at all or unknown), from the width of its sharpest
    edges (edge_width) in the n most detailed windows of the map's box (full pixels)."""
    x0, y0, x1, y1 = box
    s = int(min(side, (x1 - x0), (y1 - y0)))
    if s < 128:
        return 1.0
    cands = []
    for cy in np.linspace(y0 + s / 2, y1 - s / 2, 4):
        for cx in np.linspace(x0 + s / 2, x1 - s / 2, 4):
            b = (int(cx - s / 2), int(cy - s / 2), int(cx - s / 2) + s, int(cy - s / 2) + s)
            sm = np.asarray(image.crop(b).convert("L").resize((64, 64), Image.BOX), np.float32)
            cands.append((float(np.abs(np.diff(sm, axis=1)).mean()), b))
    cands.sort(key=lambda c: -c[0])
    g = np.concatenate([np.asarray(image.crop(b).convert("L")) for _, b in cands[:n]], axis=1)
    w = edge_width(g)
    if w is None:
        return 1.0
    return float(max(1.0, (w - EDGE_NATIVE[0]) / EDGE_NATIVE[1]))


def background_colour(a, mask):
    """The grey of the page around the map (the commonest flat grey outside the map), or None."""
    out = ~ndi.binary_dilation(mask, iterations=3)
    if out.mean() < 0.02:
        return None
    x = a[out].astype(np.int16)
    grey = (np.abs(x[:, 0] - x[:, 1]) < 6) & (np.abs(x[:, 1] - x[:, 2]) < 6) & (x.mean(1) > 100) & (x.mean(1) < 250)
    if grey.mean() < 0.2:
        return None
    q = (x[grey] // 4)
    keys, counts = np.unique(q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2], return_counts=True)
    k = keys[np.argmax(counts)]
    return tuple(int(v) * 4 + 2 for v in (k // 4096, (k // 64) % 64, k % 64))


def paint(image, mask, bg=None):
    """Everything off the map white: outside the mask, and the page colour bg where it reaches into the mask from
    outside (between the hull of the map and its edge). Returns a new RGB picture."""
    a = np.array(image.convert("RGB"))
    a[~mask] = 255
    if bg is not None:
        near = (np.abs(a.astype(np.int16) - np.array(bg, np.int16)) <= 6).all(-1) & mask
        if near.any():
            lab, n = ndi.label(near)
            edge = ndi.binary_dilation(~mask) & near
            touch = np.unique(lab[edge])
            a[np.isin(lab, touch[touch > 0])] = 255
    return Image.fromarray(a)


def unfade(course, maponly):
    """The course left half see-through on the screenshot without it (Livelox draws a course switched off this way
    in some views: about an eighth opaque) taken out again. Both pictures are the parts kept, pixel on pixel.

    Where the course is drawn fully on the screenshot with it, a white map under it shows how opaque the rest is on the
    one without (alpha). On the smoothed edge of a line the course covers a pixel only in part (cov): the screenshot
    with the course has (1 - cov) map + cov P, the one without (1 - a cov) map + a cov P, with P the purple of the
    course; from the two, cov, and then the map under it. Returns (picture, alpha); the picture as it was when alpha
    is below FAINT_MIN."""
    c = np.asarray(course.convert("RGB"))
    full = purple_mask(c)
    area = ndi.binary_dilation(purple(c), iterations=2)
    if full.sum() < 100:
        return maponly, 0.0
    m = np.array(maponly.convert("RGB"))
    P = np.median(c[full], 0).astype(np.float32)
    # white map under the course: the colour lies on the line from white to the purple, as far along it as the
    # course is opaque (a pale green or yellow map under it is off that line)
    if P[1] > 200:
        return maponly, 0.0
    D = 255.0 - P
    q = 255.0 - m[full].astype(np.float32)
    t = q @ D / float(D @ D)
    on = (np.linalg.norm(q - t[:, None] * D, axis=1) <= 12) & (t < 0.6)
    if on.sum() < 100:
        return maponly, 0.0
    alpha = float(np.median(np.clip(t[on], 0, 1)))
    if not FAINT_MIN <= alpha < 0.6:
        return maponly, max(alpha, 0.0)
    idx = np.nonzero(area)
    mv, cv = m[idx].astype(np.float32), c[idx].astype(np.float32)
    d = P - mv
    k = np.clip(((cv - mv) * d).sum(1) / np.maximum((d * d).sum(1), 1.0), 0.0, 1.0)
    cov = np.clip(k / (1 - alpha + k * alpha), 0.0, 1.0)
    e = (alpha * cov)[:, None]
    m[idx] = np.clip((mv - e * P) / (1 - e), 0, 255).astype(np.uint8)
    return Image.fromarray(m), alpha


def _scale_fit(f, k, size, box, full):
    """The flat fit f of a copy (size) of the part box of a picture (full: its size), scaled by 1/k (picture px per
    copy px), for the whole picture: the scale divided by k, the middle moved to the middle of the whole picture."""
    mid = ((full[0] / 2 - box[0]) / k[0], (full[1] / 2 - box[1]) / k[1])
    (tx, ty), = georef.to_metres(f, size, [mid])
    return dict(f, scale=f["scale"] / k[0], scale_y=f["scale_y"] / k[1], tx=float(tx), ty=float(ty))


def place_pair(course, maponly, controls, lat0, lon0, crop=None, max_px=MAX_OUT_PX, out_res=None):
    """Both screenshots (PIL, full size; maponly may be None: the one with the course alone) into placed maps.

    controls: [(x, y) or None] metres from lat0, lon0 (georef.control_positions). crop: (x0, y0, x1, y1) of the map
    on the screenshot given by hand, else it is looked for. out_res: metres per pixel of the pictures kept (default:
    as sharp as the screenshot, up to max_px pixels).

    Returns dict(course = (GeoMap, picture), maponly = (GeoMap, picture) or None, fit = the flat fit of the full
    screenshot with the course, res = its metres per pixel, out_res, shift = (dx, dy) full px or None, box = the part
    kept (full px), reliable = the map was found clearly, swapped, notes = [codes: swapped, shifted, coarse,
    coarse_stop, unsure_area], accuracy = metres for the label, area = map_area dict on the small copy, k).
    Raises PairError with what is wrong."""
    notes = []
    W, H = course.size
    if maponly is not None and maponly.size != course.size:
        raise PairError("size", a=course.size, b=maponly.size)
    a, k = small(course)
    b = small(maponly)[0] if maponly is not None else None
    area = rect_area((a.shape[1], a.shape[0]), crop, k) if crop else map_area(a)
    mask = area["mask"]
    swapped = False
    if b is not None:
        pa, pb = course_share(a, mask), course_share(b, mask)
        if max(pa, pb) < COURSE_SHARE:
            raise PairError("no_course")
        if pb > pa:
            course, maponly, a, b, pa, pb = maponly, course, b, a, pb, pa
            swapped = True
            notes.append("swapped")
        # the course still on the one without it: drawn in the exact purple as on the other one (a course left
        # half see-through is paler, and is taken out by unfade)
        opaque = (purple_mask(b) & mask).sum() >= OPAQUE * (purple_mask(a) & mask).sum()
        if pb >= COURSE_SHARE and opaque and has_circles(b):
            raise PairError("course_in_maponly")
    skip = ndi.binary_dilation(purple(a), iterations=2)
    shift = None
    if b is not None:
        if routes_share(a, mask, skip) >= ROUTE_SHARE and routes_share(b, mask, skip) >= ROUTE_SHARE:
            raise PairError("routes")
        cmp = compare(a, b, mask, skip)
        shift = (cmp["shift"][0] * k[0], cmp["shift"][1] * k[1])
        if math.hypot(*shift) > SHIFT_MAX * max(W, H):
            raise PairError("far", px=math.hypot(*shift))
        x0, y0, x1, y1 = area["box"]
        shift = refine_shift(course, maponly, shift, (int(x0 * k[0]), int(y0 * k[1]), int(x1 * k[0]), int(y1 * k[1])))
        if math.hypot(*shift) >= 0.5:
            notes.append("shifted")
    else:
        if course_share(a, mask) < COURSE_SHARE:
            raise PairError("no_course")
    # place the screenshot with the course, on a copy without what is off the map
    # (the map's box only: the circles are larger on the copy than with the page of Livelox around them)
    x0, y0, x1, y1 = area["box"]
    wb = (max(0, int(x0 * k[0])), max(0, int(y0 * k[1])), min(W, int(math.ceil(x1 * k[0]))),
          min(H, int(math.ceil(y1 * k[1]))))
    part = course.crop(wb)
    kw = max(1.0, max(part.size) / WORK_PX)
    work = part if kw == 1.0 else part.resize((int(round(part.size[0] / kw)), int(round(part.size[1] / kw))),
                                              Image.LANCZOS)
    kw = (part.size[0] / work.size[0], part.size[1] / work.size[1])
    mwork = np.asarray(Image.fromarray(mask).transform(
        work.size, Image.AFFINE, (kw[0] / k[0], 0, wb[0] / k[0], 0, kw[1] / k[1], wb[1] / k[1]), Image.NEAREST))
    try:
        _, f = georef.place(paint(work, mwork), controls, lat0, lon0, screen=True)
    except georef.GeorefError as e:
        raise PairError("no_fit", reason=str(e)) from e
    outside = sum(1 for _, c in f["pairs"]
                  if not mwork[min(work.size[1] - 1, int(f["circle_px"][c][1])),
                               min(work.size[0] - 1, int(f["circle_px"][c][0]))])
    reliable = area["reliable"] and outside == 0
    if not reliable:
        notes.append("unsure_area")
    full = _scale_fit(f, kw, work.size, wb, (W, H))
    res = (full["scale"] + full["scale_y"]) / 2
    if res > MAX_M_PER_PX:
        notes.append("coarse_stop")
    elif res > WARN_M_PER_PX:
        notes.append("coarse")
    # the part kept: the map's box, inside both screenshots
    x0, y0, x1, y1 = area["box"]
    box = [x0 * k[0], y0 * k[1], x1 * k[0], y1 * k[1]]
    ish = (int(round(shift[0])), int(round(shift[1]))) if shift else (0, 0)
    box = [max(box[0], 0, -ish[0]), max(box[1], 0, -ish[1]), min(box[2], W, W - ish[0]), min(box[3], H, H - ish[1])]
    box = tuple(int(round(v)) for v in box)
    bw, bh = box[2] - box[0], box[3] - box[1]
    # as sharp as the map itself: a map the browser zoomed in has nothing finer than its own pixels, only bigger
    # pictures and a finer grid of the route search than a KMZ of the same map would give
    zoom = zoom_of(maponly if maponly is not None else course, box)
    # (but not coarser than a Livelox KMZ usually is: the zoom of a screenshot zoomed out is read too large)
    r_out = out_res or max(min(res * max(1.0, ZOOM_SAFE * zoom), max(res, COARSEST_KEPT)),
                           res * math.sqrt(bw * bh / max_px))
    r_out = max(r_out, res)
    out = (max(1, int(round(bw * res / r_out))), max(1, int(round(bh * res / r_out))))
    mout = np.asarray(Image.fromarray(mask).transform(
        out, Image.AFFINE, (bw / out[0] / k[0], 0, box[0] / k[0], 0, bh / out[1] / k[1], box[1] / k[1]),
        Image.NEAREST))
    bg = background_colour(a, mask)

    def cut(image, d=(0, 0)):
        part = image.crop((box[0] + d[0], box[1] + d[1], box[2] + d[0], box[3] + d[1]))
        if part.size != out:
            part = part.resize(out, Image.BILINEAR)
        return paint(part, mout, bg)
    fc = georef.crop_frame(full, (W, H), box, out)
    # how much more blurred the map kept is than a Livelox export of it (a gaussian sigma in metres): a bilinear
    # zoom of the browser spreads a pixel of the map over sigma ~0.41 of it, the resizing to r_out over ~0.41 of
    # r_out; a screenshot at zoom 1 kept at its own pixels is as sharp as the export
    b_zoom = BILINEAR_SIGMA * res * zoom if zoom > 1.05 else 0.0
    b_cut = BILINEAR_SIGMA * r_out if r_out > 1.05 * res else 0.0
    blur_m = round(math.hypot(b_zoom, b_cut), 3)
    c_img = cut(course)
    result = dict(course=(georef.geomap(c_img, fc, lat0, lon0), c_img), maponly=None, fit=full, work_fit=f,
                  res=res, out_res=r_out, zoom=zoom, shift=shift, box=box, reliable=reliable, swapped=swapped, notes=notes,
                  area=area, k=k, kw=kw, blur_m=blur_m)
    if maponly is not None and "coarse_stop" not in notes:
        m_img = cut(maponly, ish)
        m_img, result["faint"] = unfade(c_img, m_img)
        if result["faint"] >= FAINT_MIN:
            notes.append("faint_course")
        gm = georef.geomap(m_img, fc, lat0, lon0)
        gm.blur_m = result["blur_m"]
        result["maponly"] = (gm, m_img)
    # how far off the corners of the part kept may be (georef.edge_error on that part, not on the whole screenshot
    # with the page of Livelox around the map)
    ground = [controls[kk] for kk, _ in f["pairs"]]
    corners = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
    result["edge_m"] = georef.edge_error(full, (W, H), corners, ground)
    result["accuracy"] = float(max(ACCURACY_MIN_M, f["rms"], result["edge_m"]))
    return result
