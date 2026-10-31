"""Read terrain types from an ISOM-coloured map image (map-only Livelox export).

The map is turned into one terrain class per pixel. Area colours (white forest,
greens, yellows, olive) give the base class. Line and point symbols (brown
contours, black paths, blue streams, green stripes) are removed and the area
underneath is filled in from the nearest area pixel; some of them are then put
back as overlays:
  - black linear features -> paths (dashes bridged, short bits dropped)
  - large solid black blobs -> buildings (uncrossable)
  - dense green vertical stripes -> undergrowth (slower)
  - dense blue hatching -> marsh, solid blue patches -> open water (uncrossable)
Brown contours are ignored on purpose: slope comes from the DEM instead.

Limits: cliffs, small rock features and erosion gullies are not detected (fences:
oroute/relocate.py); the stripe/hatch detection is a density threshold, so a stream
lined with marsh symbols may be read partly as marsh.
"""
import math

import numpy as np
from scipy import ndimage as ndi

# class ids
FOREST, SLOW, WALK, FIGHT, ROUGH_OPEN, OPEN, UNDERGROWTH, MARSH, PATH, WATER, OOB, BUILDING = range(12)
NAMES = ["forest (runnable)", "light green (slow run)", "green (walk)", "dark green (fight)",
         "rough open", "open land", "undergrowth (stripes)", "marsh", "path/road", "water",
         "out of bounds", "building"]
COLORS = [(255, 255, 255), (194, 225, 192), (110, 190, 110), (30, 120, 50), (254, 225, 170),
          (253, 185, 70), (150, 220, 90), (100, 200, 240), (0, 0, 0), (0, 90, 200),
          (171, 165, 54), (120, 0, 0)]

# ISOM palette as it appears in Livelox PNG exports
AREA = {  # rgb -> class
    (255, 255, 255): FOREST,
    (194, 225, 192): SLOW,
    (137, 202, 139): WALK,
    (254, 219, 162): ROUGH_OPEN,
    (253, 190, 79): OPEN,
    (171, 165, 54): OOB,
}
LINE = {
    "brown": (194, 96, 46),
    "black": (35, 31, 32),
    "blue": (0, 173, 238),
    "lblue": (191, 234, 251),
    "dgreen": (24, 177, 75),
    "purple": (180, 70, 245),
}


def _disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


NORTH_MAX_DEG = 30.0   # the north lines may lean this much from the side of the picture (a turned map, a photo)
NORTH_COVER = 0.3      # a north line: blue along at least this share of its length across the map ...
NORTH_RUN = 0.15       # ... in one piece (gaps up to NORTH_GAP_RUN px) at least this share of it: a dashed stream has
NORTH_GAP_RUN = 2      # short pieces only
NORTH_WEAK = 0.12      # a line on the grid of the others (same spacing) needs only this much of each
NORTH_ALONE = 0.8      # a single line with no other one to make a grid needs this much cover (of a line
                       # one pixel wide: blue along this share of the map)
NORTH_GRID_PX = 2.0    # on the grid = this close to a whole number of spacings from a line found
NORTH_WIDE_PX = 4.0    # a north line is no wider than this (0.18 mm; a wider peak has something along it)
NORTH_ALONE_SHARE = 0.25   # ... and beside it (4 to 8 px away) at most this share of its blue: a line, not an area
NORTH_MIN_GAP_PX = 50.0    # the lines are at least this far apart (120 m at 1:4000 are 300 px at 0.4 m/px)
_DEBUG = False
_NORTH = {}            # the last pictures read (id and shape -> result): classify and stream_mask ask for the same


def _blue(rgb):
    return (rgb[..., 2] > 200) & (rgb[..., 0] < 120)


def north_lines(rgb, top=0):
    """The magnetic north lines of the map (ISOM 601): straight, unbroken blue lines across the whole map, all
    parallel and evenly spaced. Not necessarily up and down in the picture: a map turned by a few degrees (a
    screenshot of Livelox, a photo) has them leaning, and then no column of pixels holds one.

    Found by projection: the blue pixels are summed along lines leaning by every angle up to NORTH_MAX_DEG; at
    the angle of the north lines a few positions hold most of them (the sharpest peaks). A peak is a north line
    when blue covers NORTH_COVER of its length across the drawn map in pieces of which one is at least NORTH_RUN
    long (a stream is crooked, or dashed: ISOM 304-306); weaker lines count when they lie on the grid of the
    strong ones.
    Returns dict(mask (the band of every line, as wide as the line and half a pixel more on either side), angle_deg
    (the bearing of the north the lines show, in degrees clockwise from up in the picture: subtract it from a
    bearing taken against the picture), spacing_px, offsets (the position of each line across, in pixels),
    width_px)."""
    key = (id(rgb), rgb.shape, top)
    if key in _NORTH and _NORTH[key][0] is rgb:
        return _NORTH[key][1]
    out = _north_lines(rgb, top)
    _NORTH.clear()
    _NORTH[key] = (rgb, out)
    return out


def _north_lines(rgb, top):
    H, W = rgb.shape[:2]
    none = dict(mask=np.zeros((H, W), bool), angle_deg=0.0, spacing_px=None, offsets=[], width_px=0.0)
    blue = _blue(rgb)
    blue[:top] = False
    vs, us = np.nonzero(blue)
    if len(us) < 50:
        return none
    # the drawn map (a screenshot has white around it): the rows and columns with ink in them
    ink = rgb[top:].astype(np.int16).sum(-1) < 720
    rows = np.nonzero(ink.mean(1) > 0.05)[0] + top
    cols = np.nonzero(ink.mean(0) > 0.05)[0]
    if not len(rows) or not len(cols):
        return none
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    uf, vf = us.astype(np.float64), vs.astype(np.float64)

    def hist(t):
        # a line leaning by t (radians) runs along (sin t, cos t); across it the position is u cos t - v sin t
        rho = uf * np.cos(t) - vf * np.sin(t)
        lo = rho.min()
        return np.bincount(np.round(rho - lo).astype(np.int64)), lo

    def score(deg):
        h, _ = hist(np.radians(deg))
        return float((h.astype(np.float64) ** 2).sum())
    coarse = max(np.arange(-NORTH_MAX_DEG, NORTH_MAX_DEG + 1e-9, 0.5), key=score)
    deg = max(np.arange(coarse - 0.6, coarse + 0.6 + 1e-9, 0.02), key=score)
    t = np.radians(deg)
    h, lo = hist(t)
    s = np.r_[0, h, 0].astype(np.float64)
    win = s[:-2] + s[1:-1] + s[2:]                   # the blue of a line two or three pixels wide

    def length(rho):
        """How long the line at position rho is inside the drawn map (r0..r1 x c0..c1), and where it enters."""
        # points u = rho cos t + k sin t, v = -rho sin t + k cos t
        ks = []
        for a, b, lim in ((np.sin(t), rho * np.cos(t), (c0, c1)), (np.cos(t), -rho * np.sin(t), (r0, r1))):
            if abs(a) < 1e-9:
                if not lim[0] <= b <= lim[1]:
                    return 0.0, 0.0
                continue
            ks.append(sorted(((lim[0] - b) / a, (lim[1] - b) / a)))
        k0 = max(k[0] for k in ks)
        k1 = min(k[1] for k in ks)
        return max(0.0, k1 - k0), k0

    def along(rho, k0, n):
        """The blue along the line (a pixel either side), as booleans one pixel apart."""
        k = k0 + np.arange(int(n))
        out = np.zeros(len(k), bool)
        for d in (-1, 0, 1):
            u = np.round((rho + d) * np.cos(t) + k * np.sin(t)).astype(int)
            v = np.round(-(rho + d) * np.sin(t) + k * np.cos(t)).astype(int)
            ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
            out[ok] |= blue[v[ok], u[ok]]
        return out

    def longest(on):
        """The longest piece of blue, with gaps up to NORTH_GAP_RUN pixels bridged."""
        if not on.any():
            return 0
        idx = np.nonzero(on)[0]
        breaks = np.nonzero(np.diff(idx) > NORTH_GAP_RUN + 1)[0]
        starts = np.r_[idx[0], idx[breaks + 1]]
        ends = np.r_[idx[breaks], idx[-1]]
        return int((ends - starts + 1).max())

    found = []          # (position across, cover, run)
    peaks = [i for i in range(len(win)) if win[i] > 0 and win[i] >= win[max(i - 3, 0):i + 4].max()]
    for i in peaks:
        if found and i - found[-1][0] < 4:
            continue
        # a line, not the middle of a blue area: a few pixels beside it there is little blue
        c = max(i - 1, 0) + int(np.argmax(h[max(i - 1, 0):i + 2]))      # the bin of the line itself
        side = np.r_[h[max(c - 8, 0):max(c - 3, 0)], h[c + 4:c + 9]]
        if len(side) and side.mean() > NORTH_ALONE_SHARE * h[c]:
            continue
        rho = i + lo
        n, k0 = length(rho)
        if n < 20:
            continue
        cover = win[i] / n
        if cover < NORTH_WEAK:
            continue
        on = along(rho, k0, n)
        found.append((i, cover, longest(on) / n))
    if _DEBUG:
        print("north candidates", round(deg, 2), [(int(f[0] + lo), round(f[1], 2), round(f[2], 2)) for f in found])
    # Measured on the eleven maps of tools/kola.sh: the north lines are broken for the names and symbols they
    # cross, their longest whole piece is only 5 to 30 % of the map; what tells them is the grid. The lines with
    # NORTH_COVER make it: the spacing is the middle gap between them, the grid is laid from the line most of
    # the others agree with, and every line on it with NORTH_WEAK of blue is a north line. A blue line off the
    # grid (the frame of the sheet, a straight ditch) is none.
    strong = [f for f in found if f[1] >= NORTH_COVER]
    keep, spacing = [], None
    if len(strong) >= 2:
        gaps = np.diff(sorted(f[0] for f in strong)).astype(float)
        mid = float(np.median(gaps))
        near = gaps[np.abs(gaps - mid) <= 0.1 * mid]
        spacing = float(np.median(near)) if len(near) else mid
    if spacing is not None and spacing < NORTH_MIN_GAP_PX:
        spacing, strong = None, [f for f in strong if f[2] >= NORTH_RUN]
    if spacing is not None:
        # (the spacing is known to about a pixel: a line n spacings away may be off by half a pixel more each)
        on = lambda a, b: abs((a - b) / spacing - round((a - b) / spacing)) * spacing \
            <= NORTH_GRID_PX + 0.5 * abs(round((a - b) / spacing))
        base = max((f[0] for f in strong), key=lambda b: sum(on(g[0], b) for g in strong))
        keep = [f for f in found if on(f[0], base)]
        if sum(f in strong for f in keep) < 2:
            keep, spacing = [], None
        else:
            # the spacing from all the lines on the grid (a straight line through their positions)
            n = np.array([round((f[0] - base) / spacing) for f in keep], float)
            if len(set(n)) >= 2:
                spacing = float(np.polyfit(n, [f[0] for f in keep], 1)[0])
    if not keep:
        # one line alone: long and mostly whole
        def cover1(i):
            # the cover of a line as wide as one pixel (the window of three bins holds a line of two twice)
            c = max(i - 1, 0) + int(np.argmax(h[max(i - 1, 0):i + 2]))
            wide = max(1, int((h[max(c - 2, 0):c + 3] > h[c] / 2).sum()))
            return win[i] / wide / max(length(i + lo)[0], 1.0)
        alone = [f for f in strong if cover1(f[0]) >= NORTH_ALONE and f[2] >= NORTH_RUN]
        if not alone:
            return none
        keep = [max(alone, key=lambda f: f[1])]
    # the width of a line: the bins of its peak above half its height (a few pixels: a wider peak is the peak
    # of something else lying along the line)
    widths = []
    for i, _, _ in keep:
        j0, j1 = i, i
        while j0 > i - 4 and j0 > 0 and h[j0 - 1] > h[i] / 2:
            j0 -= 1
        while j1 < i + 4 and j1 + 1 < len(h) and h[j1 + 1] > h[i] / 2:
            j1 += 1
        widths.append(j1 - j0 + 1)
    width = float(min(max(np.median(widths), 1.0), NORTH_WIDE_PX))
    half = width / 2.0 + 0.5           # (a line 2 px wide: a band of 3, as the columns of the old mask were)
    mask = np.zeros((H, W), bool)
    v = np.arange(H)
    reach = half / max(np.cos(t), 1e-6)                  # the half width of a band along a row
    for i, _, _ in keep:
        uc = (i + lo + v * np.sin(t)) / np.cos(t)        # where the line crosses each row
        a = np.clip(np.ceil(uc - reach), 0, W).astype(int)
        b = np.clip(np.floor(uc + reach) + 1, 0, W).astype(int)
        for row in np.nonzero(b > a)[0]:
            mask[row, a[row]:b[row]] = True
    mask[:top] = False
    return dict(mask=mask, angle_deg=float(-deg), spacing_px=spacing, offsets=[float(i + lo) for i, _, _ in keep],
                width_px=width)


def north_line_mask(rgb, top=0):
    """The band of every magnetic north line of the map (north_lines)."""
    return north_lines(rgb, top)["mask"]


def _across(angle_deg, n):
    """A straight structuring element n pixels long across the north lines (perpendicular to them)."""
    t = np.radians(-angle_deg)
    r = (n - 1) / 2.0
    k = np.arange(n) - r
    u = np.round(k * np.cos(t) + r).astype(int)
    v = np.round(-k * np.sin(t) + r).astype(int)
    se = np.zeros((int(v.max()) + 1, int(u.max()) + 1), bool)
    se[v - v.min(), u - u.min()] = True
    return se


REF_M_PER_PX = 1.33  # resolution of the maps the sizes in pixels below were tuned on (Livelox, 1:10 000)
DOT_PX = 3           # a black mark up to this many pixels across (at REF_M_PER_PX: 4 m) is a dot, not a dash of a path
EDGE_CELLS = 8       # the map goes on beyond the edge of its picture where, in a strip this many cells (of 4 px) deep
                     # (a picture may have a white frame of a dozen pixels around the map) ...
EDGE_SHARE = 0.3     # ... along that edge, at least this share is drawn in the colours of a map (not white, grey or black)
NORTH_GAP_PX = 9     # a north line with water this close on both sides of it (in one row) lies in that water
OLIVE_GAP_PX = 4     # black with olive within this many pixels on both sides of it lies inside a settlement
STREET_PX = 2        # ... and is a path only this close to the light brown of a paved street
POND_M2 = 30.0       # a solid blue patch at least this large ...
BANK_SHARE = 0.8     # ... with a ring this black around it is a pond, however narrow it is. Measured on the four
                     # maps of data/: the ten ponds of Petřvald have 0.97 and more, no other blue patch over 0.66


# Sprint maps (ISSprOM 2019): buildings are a grey fill with a black outline, a passage under a roof a lighter
# grey, a paved area a light brown. A forest map (ISOM) has none of the grey: the rules below only apply on a map
# that has solid grey patches (sprint_greys), so nothing changes on the others.
BUILDING_GREY = (105, 150)   # mean of the grey of a building (ISSprOM 521: 121 to 132 on the maps of data-extra/)
CANOPY_GREY = (188, 222)     # mean of the lighter grey of a passage or canopy (ISSprOM 522: 200 to 211)
GREY_SPREAD = 14             # a grey is no colour: its channels lie this close together
SPRINT_SHARE = 0.005         # a map is a sprint map when this share of it is solid building grey (sprints of
                             # data-extra/: 2.5 to 6.5 %; forest maps of data/: 0.001 % at most)


def _grey_mask(rgb, lo, hi):
    mx, mn = rgb.max(-1), rgb.min(-1)
    s = rgb.sum(-1, dtype=np.int32)
    return (mx.astype(np.int16) - mn < GREY_SPREAD) & (s >= 3 * lo) & (s <= 3 * hi)


def sprint_greys(rgb, m_per_px=None):
    """(building, canopy) masks of a sprint map: the solid grey patches of ISSprOM 521 and 522 (the grey edge of
    an antialiased black line is too thin to count). (None, None) on a map without grey buildings."""
    grey = _grey_mask(rgb, *BUILDING_GREY)
    if grey.mean() < SPRINT_SHARE:
        return None, None
    s = REF_M_PER_PX / m_per_px if m_per_px else 1.0
    r = max(1, int(s + 0.5))
    building = ndi.binary_opening(grey, structure=_disk(r))
    if building.mean() < SPRINT_SHARE:
        return None, None
    canopy = ndi.binary_opening(_grey_mask(rgb, *CANOPY_GREY), structure=_disk(r))
    return building, canopy


# Walls of a sprint map. A wall is a solid black line; how wide it is drawn tells what it is. Widths are measured
# from the ink of the line (blurred, then the width of a straight line of that ink: no rounding to pixels) on its
# ridge. On the sprints of data-extra/: the edges of paved areas and canopies 0.5 to 0.7 m, passable walls (drawn
# with dots) and the dashes of paths 0.75 to 1.1 m, impassable walls and fences, the rails of a bridge 1.28 to
# 1.55 m; where two dashed paths cross, the ink of both makes 1.22 m.
WALL_SIGMA_M = 0.5    # the ink is blurred this much (lines 1.5 m apart, the two edges of a lane, stay apart)
WALL_MIN_M = 0.7      # a black line narrower than this is an edge, an outline or a step: no wall
WALL_THICK_M = 1.25   # ... at least this wide on its ridge: an impassable wall (ISSprOM 515, 518 alike)
WALL_LEN_M = 8.0      # ... and at least this long in one piece (a dash of a path or a symbol is shorter)
WALL_DOT_R_M = 0.8    # a passable wall (ISSprOM 513) is drawn with dots: round black blobs a disc this wide fits in,
WALL_DOT_EXT_M = 3.0  # ... no wider than this across; a line between the two widths with at least WALL_DOTS of
WALL_DOTS = 2         # them on it is a passable wall. Without dots it is left as it was (the edge of a lane is
                      # as wide), so a low wall without dots is still read as no obstacle at all


def sprint_walls(rgb, building, m_per_px=None, blur_m=0.0):
    """(impassable, passable) masks of the walls of a sprint map (see WALL_*); building: its grey buildings
    (sprint_greys), whose black outline is no wall. The masks are the black of the lines, not grown.
    blur_m: how much more blurred the picture is than a Livelox export (GeoMap.blur_m): the ink of a line is then
    spread wider and lower, and its width is read with the blur of both (a wall of 1.3 m would read 1.22 m on a map
    cut out of a screenshot zoomed 1.5 times, and be no wall)."""
    H, W = rgb.shape[:2]
    mpp = m_per_px or REF_M_PER_PX
    near = ndi.binary_dilation(building, iterations=2)
    black = np.zeros((H, W), bool)
    ridge = np.zeros((H, W), bool)
    width = np.zeros((H, W), np.float16)
    sig = WALL_SIGMA_M / mpp
    margin = int(4 * sig) + 2
    rows = max(64, 4_000_000 // max(W, 1))        # a band of rows at a time: the floats of a whole map are large
    from scipy.special import erfinv
    for r0 in range(0, H, rows):
        a, b = max(r0 - margin, 0), min(r0 + rows + margin, H)
        sub = rgb[a:b]
        lum = sub.mean(-1, dtype=np.float32)
        grey = (sub.max(-1).astype(np.int16) - sub.min(-1) < 45) & ~near[a:b]
        blk = (lum < 150) & grey
        ink = np.clip((210 - lum) / 180, 0, 1) * grey
        del lum, grey
        w = (2 * np.sqrt(2) * math.hypot(WALL_SIGMA_M, blur_m)) * erfinv(np.clip(ndi.gaussian_filter(ink, sig), 0, 0.995))
        top = r0 - a
        n = min(rows, H - r0)
        rid = blk & (w >= ndi.maximum_filter(w, 3))
        black[r0:r0 + n] = blk[top:top + n]
        ridge[r0:r0 + n] = rid[top:top + n]
        width[r0:r0 + n] = w[top:top + n]
        del ink, w, rid, blk
    # the dots a passable wall is drawn with
    dl, _ = ndi.label(ndi.binary_opening(black, structure=_disk(max(1, int(round(WALL_DOT_R_M / mpp))))))
    dots = np.zeros((H, W), bool)
    for k, sl in enumerate(ndi.find_objects(dl), 1):
        h, w_ = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        part = dl[sl] == k
        if max(h, w_) * mpp <= WALL_DOT_EXT_M and max(h, w_) <= 1.6 * min(h, w_) and part.mean() >= 0.5:
            dots[sl] |= part
    del dl
    dlab, _ = ndi.label(dots)
    near_dot = ndi.binary_dilation(dots, iterations=max(2, int(round(1.2 / mpp))))
    # every dot grown by a metre with its number: the dots on a line, touching it or not
    dlab = ndi.grey_dilation(dlab, footprint=_disk(max(1, int(round(1.0 / mpp)))))
    lab, _ = ndi.label(black & (width >= WALL_MIN_M), structure=np.ones((3, 3)))
    hard, low = np.zeros((H, W), bool), np.zeros((H, W), bool)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) * mpp < WALL_LEN_M:
            continue
        part = lab[sl] == k
        top = part & ridge[sl] & ~near_dot[sl]
        if not top.any():
            continue
        if float(np.median(width[sl][top].astype(np.float32))) >= WALL_THICK_M:
            hard[sl] |= part
        elif len(set(np.unique(dlab[sl][part])) - {0}) >= WALL_DOTS:
            low[sl] |= part
    return hard, low


def paved(rgb, sprint=False):
    """The light brown of a paved road, street or yard (ISOM 501, 502) in the picture.
    sprint: also the lighter brown of a paved area of a sprint map (ISSprOM 501), which on a forest map would be
    too close to rough open land (ISOM 403) to tell apart."""
    r, g, b = (rgb[..., k].astype(np.int16) for k in range(3))
    out = (r > 205) & (r < 240) & (g > 150) & (g < 185) & (b > 100) & (b < 145)
    if sprint:
        out |= (r >= 222) & (r <= 248) & (g >= 158) & (g <= 214) & (b >= 112) & (b <= 185) & (r - b > 50) & (g - b <= 55)
    return out


def _closed(mask, r):
    """A mask closed by a disc of r pixels (what scipy's binary_closing gives with it, the outside of the
    picture counting as empty), through the distance to the nearest pixel and only around the mask: the
    time does not grow with the disc."""
    vs, us = np.nonzero(mask.any(1))[0], np.nonzero(mask.any(0))[0]
    if not len(vs):
        return mask.copy()
    p = int(r) + 2
    box = (slice(max(vs[0] - p, 0), vs[-1] + p + 1), slice(max(us[0] - p, 0), us[-1] + p + 1))
    part = np.pad(mask[box], p)
    grown = ndi.distance_transform_edt(~part) <= r
    out = np.zeros(mask.shape, bool)
    out[box] = (ndi.distance_transform_edt(grown) > r)[p:-p, p:-p]
    return out


def banked_water(blue, black, px, m_per_px):
    """Uncrossable water drawn with a bank line (ISOM 301): solid blue patches closed in by a black line, with
    that line. The rule "blue wide enough is water" misses a pond 8 m wide, and its bank line would be read as
    a path along the shore. A stream, the dashes of a marsh and blue without a bank have no black around them.
    blue, black: masks of the picture; px(n): n pixels of a map with REF_M_PER_PX in pixels of this one."""
    lab, n = ndi.label(ndi.binary_opening(blue, structure=_disk(px(1))))
    out = np.zeros(blue.shape, bool)
    if not n:
        return out
    big = np.bincount(lab.ravel(), minlength=n + 1) * m_per_px * m_per_px >= POND_M2
    reach = px(2) + 1                # the bank line lies within this distance of the blue
    H, W = blue.shape
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if not big[k]:
            continue
        box = (slice(max(sl[0].start - reach - 1, 0), min(sl[0].stop + reach + 1, H)),
               slice(max(sl[1].start - reach - 1, 0), min(sl[1].stop + reach + 1, W)))
        part = lab[box] == k
        # the bank line is the blackest of the rings one pixel wide around the blue (how far out it lies and
        # how thick it is depends on the picture: its first ring is the antialiased edge of the blue)
        grown, share = part, 0.0
        for _ in range(px(2)):
            wider = ndi.binary_dilation(grown)
            share = max(share, float(black[box][wider & ~grown].mean()))
            grown = wider
        if share >= BANK_SHARE:
            out[box] |= grown | (ndi.binary_dilation(grown, iterations=reach - px(2)) & (blue[box] | black[box]))
    return out


def classify(rgb, header_px=0, m_per_px=None, blur_m=0.0):
    """rgb: HxWx3 uint8 map-only image. Returns HxW uint8 class map. blur_m: see sprint_walls."

    m_per_px: resolution of the picture. The sizes of map symbols below are in pixels of a map with
    REF_M_PER_PX; on a sharper picture the same symbols are that many times bigger, so the sizes grow with
    it (a road 9 px wide at 0.59 m per pixel is not a building 7 px across). None = sizes as they are.
    Not scaled: the growing by one pixel that covers the antialiased edge of a line, the same at any resolution.
    """
    s = REF_M_PER_PX / m_per_px if m_per_px else 1.0

    def px(n):
        return max(1, int(n * s + 0.5))
    im = rgb.astype(np.int32)
    H, W = im.shape[:2]
    keys = list(AREA) + list(LINE.values())
    pal = np.array(keys, np.int32)
    # the nearest palette colour of every pixel, a band of rows at a time: all at once the differences take
    # 144 bytes per pixel (over 2 GB on a map of 18 million pixels)
    near = np.empty((H, W), np.intp)
    rows = max(1, 2_000_000 // max(W, 1))
    for r in range(0, H, rows):
        near[r:r + rows] = ((im[r:r + rows, :, None, :] - pal[None, None]) ** 2).sum(-1).argmin(-1)
    nA = len(AREA)
    area_cls = np.array(list(AREA.values()), np.uint8)
    names = list(LINE)
    line = {n: near == nA + i for i, n in enumerate(names)}
    north = north_lines(rgb, header_px)
    nline = north["mask"]
    line["blue"] = (line["blue"] | line["lblue"]) & ~nline
    del line["lblue"]
    # thin black lines are antialiased to grey, so take every dark, unsaturated pixel as black
    mx, mn = im.max(-1), im.min(-1)
    line["black"] = (im.mean(-1) < 150) & (mx - mn < 45)
    # ... but not the grey fill of a building on a sprint map: that is a house whatever its width
    grey_bld, canopy = sprint_greys(rgb, m_per_px)
    sprint = grey_bld is not None
    if sprint:
        line["black"] &= ~ndi.binary_dilation(grey_bld, iterations=1)

    # anything that is a line, an antialiased edge of a line, or a north line gets filled in
    linepix = np.zeros((H, W), bool)
    for m in line.values():
        linepix |= m
    linepix = ndi.binary_dilation(linepix, iterations=1) | nline
    # very dark green vegetation is drawn in the same colour as the stripes; a solid patch = fight
    fight = ndi.binary_opening(line["dgreen"], structure=np.ones((px(5), px(5))))

    base = np.where(near < nA, area_cls[np.minimum(near, nA - 1)], 255).astype(np.uint8)
    base[linepix] = 255
    # fill gaps with the nearest area pixel
    _, (iy, ix) = ndi.distance_transform_edt(base == 255, return_indices=True)
    base = base[iy, ix]
    # majority-ish smoothing: drop speckles of a class narrower than ~3 px
    out = base.copy()
    m = base == OOB  # olive also shows up in antialiased brown edges; only solid patches count
    out[m & ~ndi.binary_opening(m, structure=np.ones((px(5), px(5))))] = FOREST
    for c in (SLOW, WALK, ROUGH_OPEN, OPEN):
        m = base == c
        keep = ndi.binary_opening(m, structure=_disk(px(1)))
        out[m & ~keep] = FOREST
    out[fight] = FIGHT

    # overlays
    stripes = ndi.uniform_filter(line["dgreen"].astype(float), px(15)) > 0.08
    stripes &= ~fight
    out[stripes & (out != WALK)] = UNDERGROWTH
    blue = line["blue"]
    black = line["black"]
    water = ndi.binary_opening(blue, structure=_disk(px(3)))
    pond = banked_water(blue, black, px, m_per_px or REF_M_PER_PX)
    # marsh is hatching: the blue of open water does not count towards it, or every pond and every wide
    # stream gets a rim of marsh as wide as the window
    wet = ndi.binary_dilation(water, iterations=1) | pond
    marsh = (ndi.uniform_filter((blue & ~wet).astype(float), px(15)) > 0.22) & ~water & ~pond
    out[marsh] = MARSH
    wet = ndi.binary_dilation(water, iterations=1) | pond
    # A magnetic north line drawn across a pond is taken out of the blue with every other north line, which
    # left a strip of "forest" a few pixels wide right through the water: a way across the pond. Where a
    # north line has water on both sides of it, it is water.
    if nline.any():
        wet |= nline & ndi.binary_closing(wet, structure=_across(north["angle_deg"], NORTH_GAP_PX))
    out[wet] = WATER
    if sprint:
        # a paved area and a passage under a roof are run like a street
        out[(ndi.binary_opening(paved(rgb, sprint=True), structure=_disk(px(1))) | canopy) & ~wet] = PATH

    bld = ndi.binary_opening(black, structure=np.ones((px(7), px(7))))
    if sprint:
        # the grey of a building with its black outline (and the antialiased edge between them)
        bld |= grey_bld | (black & ndi.binary_dilation(grey_bld, iterations=px(1) + 1))
        # ... and an impassable wall is one too (a passable wall stays a black line here; mapdata.obstacles
        # makes it slow to cross and no path)
        bld |= sprint_walls(rgb, grey_bld, m_per_px, blur_m)[0]
    out[ndi.binary_dilation(bld, iterations=1)] = BUILDING
    path = black & ~bld & ~pond      # the bank line of a pond is no path
    if header_px:
        path[:header_px] = False
    # Inside a settlement (ISOM 520, olive) only the paved streets may be run (501, 502: light brown). The
    # black drawn in the olive is the outline of a house, a fence between two plots or the edge of a plot:
    # out of bounds like the ground it stands on, and no path. The black edge of a street stays one.
    # (The olive of the picture itself, in solid patches: not what was filled in under the lines along it. A
    # line with olive on one side only is the outline of the settlement; mapdata.obstacles deals with that.)
    olive = ndi.binary_opening(near == list(AREA.values()).index(OOB), structure=np.ones((px(5), px(5))))
    plot = np.zeros((H, W), bool)
    if olive.any():
        street = ndi.binary_dilation(paved(rgb, sprint), structure=_disk(px(STREET_PX)))
        plot = black & _closed(olive, px(OLIVE_GAP_PX)) & ~street & ~pond
    # A row of dots is the edge of a stand or of a field (ISOM 416, 415), the dots of cultivated land (412) or
    # of stony ground: no path. A path is drawn in dashes several times as long as a dot is wide.
    lab, n = ndi.label(path, structure=np.ones((3, 3)))
    if n:
        ext = np.array([max(s[0].stop - s[0].start, s[1].stop - s[1].start) for s in ndi.find_objects(lab)])
        path &= np.r_[False, ext > px(DOT_PX)][lab]
    # group dashes: join pieces closer than ~4 px, keep groups at least ~50 m across
    grp = ndi.binary_dilation(path, structure=_disk(px(2)))
    lab, n = ndi.label(grp, structure=np.ones((3, 3)))
    if n:
        sl = ndi.find_objects(lab)
        ext = np.array([max(s[0].stop - s[0].start, s[1].stop - s[1].start) for s in sl])
        good = np.r_[False, ext >= px(40)]
        path = ndi.binary_dilation(path & good[lab], iterations=1) | (good[lab] & ndi.binary_closing(path, structure=_disk(px(2))))
    # (taken out only now: which dashes make a path long enough to be one is judged as it always was, so
    # nothing changes outside the settlements; with the pixels the lines were grown and their corners filled by)
    path &= ~ndi.binary_dilation(plot, structure=np.ones((3, 3)), iterations=2)
    out[path & (out != BUILDING)] = PATH
    out[plot & (out != BUILDING)] = OOB
    # outside the drawn map is white too: everything beyond the map content is out of bounds
    content = (im.min(-1) < 235)
    if header_px:
        content[:header_px] = False
    small = content[::4, ::4]
    closed = ndi.binary_closing(small, structure=_disk(px(8)), iterations=2)
    # Closing takes what lies beyond the picture for empty, so a band 85 m wide along the edge of the picture
    # comes out as out of bounds. That is right for the margin of a sheet (its frame and print must not close
    # the white in), and wrong for a map drawn right up to the edge of its picture (a sprint map, a cut-out):
    # where the strip along an edge is full of map colours, the map is taken to go on beyond that edge and the
    # band is closed again with room around the picture.
    room = 2 * px(8) + 1
    drawn = (mx - mn > 25)[::4, ::4] & small       # (the palest map colour, light green, has 33)
    top, bottom, left, right = (ndi.uniform_filter1d(strip, 2 * room + 1, mode="nearest") >= EDGE_SHARE
                                for strip in (drawn[:EDGE_CELLS].mean(0), drawn[-EDGE_CELLS:].mean(0),
                                              drawn[:, :EDGE_CELLS].mean(1), drawn[:, -EDGE_CELLS:].mean(1)))
    if top.any() or bottom.any() or left.any() or right.any():
        wide = np.pad(small, room)
        band = np.zeros(small.shape, bool)
        wide[:room, room:-room] |= top[None]
        wide[-room:, room:-room] |= bottom[None]
        wide[room:-room, :room] |= left[:, None]
        wide[room:-room, -room:] |= right[:, None]
        wide[:room, :room] |= top[0] and left[0]
        wide[:room, -room:] |= top[-1] and right[0]
        wide[-room:, :room] |= bottom[0] and left[-1]
        wide[-room:, -room:] |= bottom[-1] and right[-1]
        band[:room] |= top[None]
        band[-room:] |= bottom[None]
        band[:, :room] |= left[:, None]
        band[:, -room:] |= right[:, None]
        closed |= band & ndi.binary_closing(wide, structure=_disk(px(8)), iterations=2)[room:-room, room:-room]
    # The same band swallows the map itself where the map ends within 85 m of the edge of the picture behind
    # a white margin. There the closing is done again without that loss (with room around the picture), and
    # kept only between the outermost map colours of every row and of every column: the margin beyond them,
    # with its frame and its print, stays out of bounds.
    band = np.ones(small.shape, bool)
    band[room:-room, room:-room] = False
    if (drawn & band & ~closed).any():
        exact = ndi.binary_closing(np.pad(small, room), structure=_disk(px(8)), iterations=2)[room:-room, room:-room]
        across = np.maximum.accumulate(drawn, axis=1) & np.maximum.accumulate(drawn[:, ::-1], axis=1)[:, ::-1]
        down = np.maximum.accumulate(drawn, axis=0) & np.maximum.accumulate(drawn[::-1], axis=0)[::-1]
        within = ndi.maximum_filter1d(across, 2 * px(8) + 1, axis=0) & ndi.maximum_filter1d(down, 2 * px(8) + 1, axis=1)
        closed |= band & exact & within
    small = ndi.binary_fill_holes(closed)
    inside = np.kron(small, np.ones((4, 4), bool))[:H, :W]
    out[~inside] = OOB
    if header_px:
        out[:header_px] = OOB
    return out


def render_classes(cls):
    pal = np.array(COLORS, np.uint8)
    return pal[cls]
