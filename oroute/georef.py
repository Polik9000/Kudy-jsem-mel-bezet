"""Put a picture of a map with the course on the ground without a KMZ (a scan, a photo, any export).

What is known without the picture being georeferenced:
  - where the runner was when each control was punched: the GPS track at the official punch times
    (control_positions), good to 5-15 m;
  - where the control circles are in the picture (find_circles): purple rings, all of one size.
Which circle is which control is not known. fit() finds it together with the transform:

  RANSAC   take two controls and two circles, assume they belong together: that fixes a similarity
           transform (scale, rotation, shift). Count the controls that then have a circle within INLIER_M.
           Only pairs whose distance ratio fits the scale read from the circle size are tried
           (a control circle is 75 m across in the terrain, ISOM 2017).
  least squares   on the inliers of the best guess: a similarity transform (Umeyama), then scale in x and y
           separately (a stretched scan), which is what a KML LatLonBox with a rotation can hold.
           The full affine fit is computed too, only to report how much shear the picture has.

write_kmz() stores the picture with that georeference as a KMZ, so everything else (analyze.py,
bestroute.py, the web map) reads it like a Livelox export; it has no title bar (ob-header-px: 0).
"""
import io
import math
import os
import re
import zipfile

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi

from .course import hough_circles, purple_mask
from .kmzmap import R_EARTH, GeoMap

CIRCLE_M = 75.0        # diameter of a control circle in the terrain (ISOM 2017-2: 5 mm at 1:15 000)
CIRCLE_SIZES_M = (CIRCLE_M, 50.0, 30.0)  # ... and at 1:10 000, on a sprint map (each covers SCALE_TOL around it)
INLIER_M = 30.0        # a control "has" a circle when the transformed circle centre is this close
SCALE_TOL = 0.25       # how far the scale of a guess may be from the one read from the circle size
MIN_INLIERS = 4
MIN_SHARE = 0.5        # at least this share of the controls must be matched
MAX_RMS_M = 25.0       # worse than this is not a fit
MAX_SIDE_PX = 4000     # larger pictures are scaled down before anything else
PHOTO_SAT = 0.2        # loose_purple of a photo: a thin ring blurred into the paper is pale
PHOTO_RETRY = 0.9      # with fewer controls matched than this share, the circles are read again as in a photo


class GeorefError(Exception):
    pass


def control_positions(track, to_xy, start_s, cumulative):
    """Where the track was at the official punch times: [(x, y)] in metres for the controls (not the start
    and finish; None where a punch is missing). track: dict t, lat, lon; to_xy(lat, lon) -> metres;
    start_s: official start in seconds of the track clock; cumulative: seconds from the start to each
    control and, last, the finish."""
    x, y = to_xy(track["lat"], track["lon"])
    t = track["t"]
    out = []
    for c in cumulative[:-1]:
        if c is None or not (t[0] <= start_s + c <= t[-1]):
            out.append(None)
        else:
            out.append((float(np.interp(start_s + c, t, x)), float(np.interp(start_s + c, t, y))))
    return out


def ground_course(track, to_xy, start_s, cumulative):
    """Where the runner was at the official start, at each control punch and at the finish: dict(start, controls,
    finish) of (x, y) in metres or None."""
    x, y = to_xy(track["lat"], track["lon"])
    t = track["t"]
    at = lambda s: (float(np.interp(s, t, x)), float(np.interp(s, t, y))) if t[0] <= s <= t[-1] else None
    # a watch started only after the start: where the recording begins (the start triangle is looked for there)
    start = at(start_s) or (at(t[0]) if start_s < t[0] else None)
    return dict(start=start, controls=control_positions(track, to_xy, start_s, cumulative),
                finish=at(start_s + cumulative[-1]) if cumulative and cumulative[-1] is not None else None)


def loose_purple(rgb, sat_min=0.35):
    """Purple/magenta overprint in a scan or a photo: by hue and saturation, not by the exact Livelox colour.
    sat_min: lower for a photo with its light evened out, where a thin ring blurred into the white paper around it
    is paler (the hue - red and blue both above green - still keeps the map colours out)."""
    a = np.asarray(rgb).astype(float) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    # purple to magenta: red and blue both clearly above green
    return (sat > sat_min) & (mx > 0.35) & (r - g > 0.12) & (b - g > 0.12) & (np.abs(r - b) < 0.45)


SMALL_SIDE_PX = 1100   # the circle size is first looked for on a copy of the mask this large
SMALL_RADII = range(5, 34)


SCREEN_SMALL_PX = 2200  # ... on a copy this large for a screenshot (oroute/pair.py): a big sprint map zoomed out has
                         # circles under 5 px on a copy 1100 px large


def ring_radius(mask):
    """The radius (px) of the control circles when the scale of the picture is not known: on a small copy
    of the purple mask the circle transform is tried for every radius. Control circles give a clear peak at
    their radius; the loops of the control numbers (0, 6, 8, 9) give another one at a few pixels, so the
    largest radius whose ten best circles score nearly as well as the best radius wins.
    None when no radius gives at least three circles."""
    got = ring_radii(mask)
    return got[0] if got else None


def ring_radii(mask, side=SMALL_SIDE_PX):
    """ring_radius first, then the other peaks of the score over the radius (at least 40 % of the best, a
    quarter apart), larger first: on a blurred small photo the thin rings score lower than the thick loops of
    the control numbers, and the ring radius is only a smaller peak."""
    H, W = mask.shape
    k = max(1, math.ceil(max(H, W) / side))
    small = mask[:H // k * k, :W // k * k].reshape(H // k, k, W // k, k).any((1, 3))
    scores = {}
    for r in SMALL_RADII:
        found = hough_circles(small, [r], min_votes=0.3, min_sep=r)
        if len(found) >= 3:
            scores[r] = sum(c[3] for c in found[:10])
    if not scores:
        return []
    top = max(scores.values())
    out = [max(r for r, v in scores.items() if v >= 0.85 * top)]
    peaks = [r for r, v in scores.items() if v >= 0.4 * top and v >= scores.get(r - 1, 0) and v >= scores.get(r + 1, 0)]
    for r in sorted(peaks, reverse=True):
        if all(abs(r - o) > 0.25 * o for o in out):
            out.append(r)
    return [float(r * k) for r in out]


PAPER_SIDE_PX = 400   # the colour of the paper is estimated on a copy this large
PAPER_WINDOW = 1 / 12  # ... as the brightest colour within this share of its shorter side (a control circle is
                       # about 1/30 of a map across, so the window always reaches paper around it)


def paper_colour(rgb):
    """The colour of the bare paper at every pixel (float32, H x W x 3): what white paper looks like there under
    the light of the photo. Brightest nearby colour on a small copy, smoothed, blown up again."""
    W, H = rgb.size
    k = max(1, math.ceil(max(W, H) / PAPER_SIDE_PX))
    small = np.asarray(rgb.resize((max(1, W // k), max(1, H // k)), Image.BOX), np.float32)
    win = max(5, int(min(small.shape[:2]) * PAPER_WINDOW))
    est = np.stack([ndi.maximum_filter(ndi.uniform_filter(small[..., c], 3), size=win) for c in range(3)], -1)
    est = ndi.gaussian_filter(est, (win / 2, win / 2, 0))
    return np.stack([np.asarray(Image.fromarray(est[..., c]).resize((W, H), Image.BILINEAR)) for c in range(3)], -1)


def flatten_light(rgb):
    """A photo with its light evened out: every channel divided by the colour of the paper there. That is the
    white balance (a tinted light makes the paper tinted) and the shadow (a dark paper) in one step."""
    a = np.asarray(rgb, np.float32)
    out = a / np.maximum(paper_colour(rgb), 8.0) * 245.0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def find_circles(image, photo=False):
    """Control circles of a picture: ([(u, v, r)], radius in px). Works without knowing the scale.
    photo: the purple of a photo (light evened out first, then by hue) instead of the exact Livelox purple."""
    return next(circle_sets(image, photo))


CIRCLE_TRIES = 3       # radii of the control circles tried, when the first does not match the track


def circle_sets(image, photo=False, side=SMALL_SIDE_PX):
    """find_circles for each radius ring_radii gives (at most CIRCLE_TRIES), one after another: the caller stops
    when one matches the track. A photo is read with the purple of a scan first and then with the paler one
    (PHOTO_SAT): the paler purple finds thin blurred rings, but on a map with much pale purple it can hide the
    ring radius. Raises GeorefError when there is not even one set."""
    rgb = image.convert("RGB")
    if photo:
        flat = flatten_light(rgb)
        masks = (loose_purple(flat), lambda: loose_purple(flat, PHOTO_SAT))
    else:
        mask = purple_mask(rgb)
        masks = (mask if mask.sum() >= 500 else loose_purple(rgb),)
    seen = False
    for mask in masks:
        mask = mask() if callable(mask) else mask
        for r in ring_radii(mask, side)[:CIRCLE_TRIES]:
            seen = True
            yield circles_at(mask, r), r
    if not seen:
        raise GeorefError("no control circles found in the picture (purple rings of one size)")


def circles_at(mask, r):
    """The circles of the mask with a radius near r: [(u, v, r)]."""
    radii = sorted({int(round(r * f)) for f in (0.86, 0.9, 0.94, 0.97, 1.0, 1.03, 1.06, 1.1, 1.14) if r * f >= 5})
    found = hough_circles(mask, radii, min_sep=max(8, int(r * 0.8)))
    # one circle per place: the best scoring radius
    out = []
    for c in found:
        if all(math.hypot(c[0] - o[0], c[1] - o[1]) > r * 0.8 for o in out):
            out.append(c)
    return [(c[0], c[1], c[2]) for c in out]


def similarity(src, dst):
    """Least-squares similarity transform dst ~ s * R * src + t (Umeyama, no reflection in the picture's own
    handedness: the caller flips y first). Returns (s, angle in radians, tx, ty)."""
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    num = (a[:, 0] * b[:, 0] + a[:, 1] * b[:, 1]).sum()
    cross = (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum()
    var = (a ** 2).sum()
    if var <= 0:
        raise GeorefError("the points do not span anything")
    ang = math.atan2(cross, num)
    s = math.hypot(num, cross) / var
    c, sn = math.cos(ang), math.sin(ang)
    tx = md[0] - s * (c * ms[0] - sn * ms[1])
    ty = md[1] - s * (sn * ms[0] + c * ms[1])
    return s, ang, tx, ty


def apply_similarity(p, pts, sy=None):
    """Transform points with (s, angle, tx, ty); sy: scale along the second axis when it differs."""
    s, ang, tx, ty = p
    pts = np.asarray(pts, float)
    x, y = pts[:, 0] * s, pts[:, 1] * (s if sy is None else sy)
    c, sn = math.cos(ang), math.sin(ang)
    return np.c_[c * x - sn * y + tx, sn * x + c * y + ty]


def fit(circles, controls, radius_px, size, quad=None, focal=None, flat=False):
    """Which circle is which control, and the transform from picture pixels to metres.

    circles: [(u, v, r)] from find_circles; controls: [(x, y) or None] in metres (east, north);
    radius_px: circle radius in the picture; size: (width, height) of the picture; quad: the four corners of
    the sheet in a photo (paper_quad), or None; flat: never a homography (a screenshot is a straight picture of
    the map, and a perspective found in it would only follow the GPS error of the controls).
    Returns dict(scale = metres per pixel (x), scale_y, angle, tx, ty  - for a picture with y pointing up,
    centred on its middle: see to_metres -, pairs = [(control index, circle index)], rms, n, affine_rms,
    shear, kind = similarity | paper | homography, H = the 3 x 3 transform for the last two).
    Raises GeorefError when no convincing fit exists.
    """
    W, H = size
    # picture coordinates with y up and the origin in the middle (so the transform has no reflection)
    cp = np.array([[c[0] - W / 2, H / 2 - c[1]] for c in circles], float)
    idx = [k for k, c in enumerate(controls) if c is not None]
    gp = np.array([controls[k] for k in idx], float)
    if len(cp) < MIN_INLIERS or len(gp) < MIN_INLIERS:
        raise GeorefError(f"too few points: {len(cp)} circles in the picture, {len(gp)} controls with a punch time")
    n, p, pairs = ransac(cp, gp, radius_px)
    need = max(MIN_INLIERS, math.ceil(MIN_SHARE * len(gp)))
    no_fit = GeorefError(f"the circles in the picture do not fit the track: {n} of {len(gp)} controls matched"
                         f" ({len(cp)} circles)")
    keep, flat_ok = None, False
    if p is not None and n >= MIN_INLIERS:
        keep = refine(cp, gp, p, pairs)
        src, dst = cp[[c for _, c in keep]], gp[[k for k, _ in keep]]
        sx, sy, ang, tx, ty, rms = axis_scaled(src, dst)
        flat_ok = n >= need and rms <= MAX_RMS_M
    elif quad is None:
        raise no_fit

    def flat_on(p):
        return axis_scaled(cp[[c for _, c in p["pairs"]]], gp[[k for k, _ in p["pairs"]]])[-1]
    persp, kind = None, "similarity"
    # a photo with the edges of the sheet in it: the perspective from them, unless it fits the controls clearly
    # worse than the flat fit (then the edges found are not those of the map)
    if quad is not None:
        qc = np.array([[u - W / 2, H / 2 - v] for u, v in quad], float)
        persp = by_paper(cp, gp, size, qc, radius_px, focal)
        if persp is not None and (persp["n"] < need or persp["rms"] > MAX_RMS_M
                                  or persp["rms"] > max(1.15 * flat_on(persp), flat_on(persp) + 3)):
            persp = None
        kind = "paper"
    # a photo taken at a slant: a homography, when it is clearly better than the flat fit on the same controls
    slanted = None        # a homography the controls clearly want but do not hold: how unsure the corners are
    if persp is None and keep is not None and len(gp) >= H_MIN and not flat:
        persp, kind = perspective(cp, gp, keep, size), "homography"
        if persp is not None and persp["rms"] <= (1 - H_GAIN) * flat_on(persp):
            slanted = persp
        if persp is not None and (persp["n"] < need or persp["rms"] > MAX_RMS_M
                                  or (flat_ok and persp["rms"] > (1 - H_GAIN) * flat_on(persp))
                                  # ... and only when the controls hold it: not one that only extrapolates
                                  or persp["spread"] > max(H_SPREAD_M, 2 * flat_spread(cp, gp, persp["pairs"], size))):
            persp = None
    if persp is not None:
        keep, rms, M = persp["pairs"], persp["rms"], persp["H"]
        src, dst = cp[[c for _, c in keep]], gp[[k for k, _ in keep]]
        J = jacobian(M, 0.0, 0.0)
        sx = sy = math.sqrt(abs(np.linalg.det(J)))
        ang, (tx, ty) = math.atan2(J[1, 0] - J[0, 1], J[0, 0] + J[1, 1]), apply_h(M, [[0.0, 0.0]])[0]
    elif keep is None or n < need:
        raise no_fit
    elif rms > MAX_RMS_M:
        raise GeorefError(f"the fit is too loose: {rms:.0f} m RMS on {len(keep)} controls")
    # the general affine fit, only to say how skewed the picture is
    A = np.c_[src, np.ones(len(src))]
    coef, *_ = np.linalg.lstsq(A, dst, rcond=None)
    aff = A @ coef - dst
    Ma = coef[:2].T
    shear = float(abs(Ma[:, 0] @ Ma[:, 1]) / (np.linalg.norm(Ma[:, 0]) * np.linalg.norm(Ma[:, 1]) + 1e-12))
    f = dict(scale=sx, scale_y=sy, angle=ang, tx=float(tx), ty=float(ty), pairs=[(idx[k], c) for k, c in keep],
             n=len(keep), rms=rms, affine_rms=float(np.sqrt((aff ** 2).sum(1).mean())), shear=shear,
             kind="similarity")
    if persp is not None:
        f.update(kind=kind, H=persp["H"].tolist(), unsure_m=persp["spread"])
        if persp.get("bend"):
            f.update(kind="paper-bent", bend=persp["bend"], Q=persp["Q"], S=persp["S"])
    else:
        # the flat fit: how much its corners move without one control, and how far they are from where the
        # homography the controls asked for puts them (a slanted photo whose sheet is not wholly in it)
        f["unsure_m"] = flat_spread(cp, gp, keep, size)
        if slanted is not None:
            W2, H2 = W / 2, H / 2
            corners = np.array([(-W2, -H2), (W2, -H2), (W2, H2), (-W2, H2)])
            gap = np.hypot(*(apply_h(slanted["H"], corners) - apply_h(similarity_matrix(f), corners)).T).max()
            f["unsure_m"] = max(f["unsure_m"], float(gap))
    return f


def ransac(cp, gp, radius_px):
    """Take two controls and two circles, assume they belong together: that fixes a similarity transform. Only
    pairs whose distance fits the scale read from the circle size are tried. Returns (controls matched,
    the best transform or None, its pairs [(control, circle)]).

    A control circle is CIRCLE_M across on a forest map at 1:15 000; at 1:10 000 it is 50 m, on a sprint map
    (6 mm at 1:4 000 or 1:5 000) 24 to 30 m. Those are tried only when the first size leaves controls without a
    circle, and the size that matches the most controls wins."""
    best = (0, None, None)
    for size_m in CIRCLE_SIZES_M:
        got = _ransac(cp, gp, (size_m / 2) / radius_px)
        if got[0] > best[0]:
            best = got
        if best[0] >= PHOTO_RETRY * len(gp):
            break
    return best


def _ransac(cp, gp, s0):
    dc = np.hypot(cp[:, None, 0] - cp[None, :, 0], cp[:, None, 1] - cp[None, :, 1])
    dg = np.hypot(gp[:, None, 0] - gp[None, :, 0], gp[:, None, 1] - gp[None, :, 1])
    best = (0, None, None)
    for i in range(len(gp)):
        for j in range(i + 1, len(gp)):
            if dg[i, j] < 150:                      # too short a baseline to fix the rotation
                continue
            want = dg[i, j] / s0
            a_, b_ = np.nonzero((np.abs(dc - want) <= SCALE_TOL * want) & (dc > 0))
            for a, b in zip(a_, b_):
                p = similarity(cp[[a, b]], gp[[i, j]])
                q = apply_similarity(p, cp)
                d = np.hypot(q[:, None, 0] - gp[None, :, 0], q[:, None, 1] - gp[None, :, 1])  # circles x controls
                near = d.argmin(0)
                ok = d[near, np.arange(len(gp))] <= INLIER_M
                # one circle serves one control
                n = len({int(c) for c, o in zip(near, ok) if o})
                if n > best[0]:
                    best = (n, p, [(k, int(c)) for k, (c, o) in enumerate(zip(near, ok)) if o])
    return best


def refine(cp, gp, p, pairs):
    """Least squares on the matched pairs, re-matching with the better transform: [(control, circle)]."""
    for _ in range(3):
        used, keep = set(), []
        for k, c in sorted(pairs, key=lambda kc: np.hypot(*(apply_similarity(p, cp[[kc[1]]])[0] - gp[kc[0]]))):
            if c not in used:
                used.add(c)
                keep.append((k, c))
        p = similarity(cp[[c for _, c in keep]], gp[[k for k, _ in keep]])
        q = apply_similarity(p, cp)
        d = np.hypot(q[:, None, 0] - gp[None, :, 0], q[:, None, 1] - gp[None, :, 1])
        near = d.argmin(0)
        pairs = [(k, int(c)) for k, c in enumerate(near) if d[c, k] <= INLIER_M]
    return keep


def axis_scaled(src, dst):
    """The flat fit: similarity, then the scale along the picture's two axes separately (what a LatLonBox can
    hold): the ground points are rotated back into the picture's frame and each axis is fitted on its own.
    Returns (sx, sy, angle, tx, ty, rms)."""
    s, ang, tx, ty = similarity(src, dst)
    c, sn = math.cos(-ang), math.sin(-ang)
    back = np.c_[c * (dst[:, 0] - tx) - sn * (dst[:, 1] - ty), sn * (dst[:, 0] - tx) + c * (dst[:, 1] - ty)]
    sx = float((src[:, 0] * back[:, 0]).sum() / max((src[:, 0] ** 2).sum(), 1e-9))
    sy = float((src[:, 1] * back[:, 1]).sum() / max((src[:, 1] ** 2).sum(), 1e-9))
    if len(src) < 6 or not (0.9 < sx / s < 1.1 and 0.9 < sy / s < 1.1):
        sx = sy = s                                   # too few points, or nonsense: keep the plain similarity
    res = apply_similarity((sx, ang, tx, ty), src, sy) - dst
    return sx, sy, ang, tx, ty, float(np.sqrt((res ** 2).sum(1).mean()))


# --- a photo taken at a slant: homography ----------------------------------------------------------------------

H_MIN = 5              # a homography (8 numbers) only from this many controls
H_GAIN = 0.25          # ... and only when its RMS is this much below the flat fit on the same controls
H_SPREAD_M = 50.0      # ... and its corners move at most this (or twice what the flat fit's do) without a control
MIN_FORESHORTEN = 0.7  # the picture squashed by at most this in one direction (a phone tilted ~45 deg)


def _normalise(p):
    m = p.mean(0)
    d = float(np.sqrt(((p - m) ** 2).sum(1)).mean())
    s = math.sqrt(2) / d if d > 0 else 1.0
    return np.array([[s, 0, -s * m[0]], [0, s, -s * m[1]], [0, 0, 1]])


def homography(src, dst):
    """Least-squares homography dst ~ H(src) (normalised DLT, Hartley): 3 x 3 with H[2, 2] = 1."""
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    if len(src) < 4:
        raise GeorefError("too few points for a homography")
    Ts, Td = _normalise(src), _normalise(dst)
    a, b = apply_h(Ts, src), apply_h(Td, dst)
    rows = []
    for (x, y), (u, v) in zip(a, b):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    h = np.linalg.svd(np.asarray(rows))[2][-1].reshape(3, 3)
    M = np.linalg.inv(Td) @ h @ Ts
    if abs(M[2, 2]) < 1e-12:
        raise GeorefError("degenerate homography")
    return M / M[2, 2]


def affine(src, dst):
    """Least-squares affine transform as a 3 x 3 matrix."""
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    A = np.c_[src, np.ones(len(src))]
    coef = np.linalg.lstsq(A, dst, rcond=None)[0]
    return np.r_[coef.T, [[0.0, 0.0, 1.0]]]


def apply_h(M, pts):
    pts = np.asarray(pts, float)
    q = np.c_[pts, np.ones(len(pts))] @ np.asarray(M, float).T
    return q[:, :2] / q[:, 2:3]


def jacobian(M, x, y):
    """d(output) / d(input) of a 3 x 3 transform at one point."""
    M = np.asarray(M, float)
    w = M[2, 0] * x + M[2, 1] * y + M[2, 2]
    out = M[:2, :2] @ [x, y] + M[:2, 2]
    return (M[:2, :2] * w - np.outer(out, M[2, :2])) / w ** 2


def h_sane(M, size):
    """A homography a photo of a flat map can have: the same side of the camera everywhere in the picture
    (no division by ~0), not mirrored, squashed by at most MIN_FORESHORTEN. Picture coordinates centred, y up."""
    W, H = size
    pts = [(0.0, 0.0), (-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)]
    M = np.asarray(M, float)
    w = [M[2, 0] * x + M[2, 1] * y + M[2, 2] for x, y in pts]
    if min(w) <= 0.33 * w[0] or max(w) >= 3 * w[0] or w[0] <= 0:
        return False
    if any(np.linalg.det(jacobian(M, x, y)) <= 0 for x, y in pts):
        return False
    sv = np.linalg.svd(jacobian(M, 0.0, 0.0), compute_uv=False)
    return sv[1] / sv[0] >= MIN_FORESHORTEN


def match(q, gp, radius=INLIER_M):
    """Each control the nearest circle within radius, one circle per control: [(control, circle)]."""
    d = np.hypot(q[:, None, 0] - gp[None, :, 0], q[:, None, 1] - gp[None, :, 1])      # circles x controls
    cand = sorted((d[c, k], k, c) for k in range(len(gp)) for c in np.nonzero(d[:, k] <= radius)[0])
    used_c, used_k, out = set(), set(), []
    for _, k, c in cand:
        if k not in used_k and c not in used_c:
            used_k.add(k)
            used_c.add(int(c))
            out.append((k, int(c)))
    return sorted(out)


def grow(cp, gp, pairs, size, model, least):
    """Fit `model` (pairs -> 3 x 3) on the pairs, match every circle again with it, fit again, until the matches
    stay: first within twice INLIER_M (a flat fit of a slanted photo is that far off at the far end of the
    course), then within INLIER_M. Returns dict(H, pairs, n, rms) or None when it goes nowhere sane."""
    pairs = sorted(pairs)
    for radius in (2 * INLIER_M, INLIER_M):
        for _ in range(10):
            M = model(pairs)
            if M is None:
                return None
            new = match(apply_h(M, cp), gp, radius)
            if new == pairs or len(new) < MIN_INLIERS:
                break
            pairs = new
    if len(pairs) < least:
        return None
    M = model(pairs)
    if M is None:
        return None
    res = apply_h(M, cp[[c for _, c in pairs]]) - gp[[k for k, _ in pairs]]
    return dict(H=M, pairs=pairs, n=len(pairs), rms=float(np.sqrt((res ** 2).sum(1).mean())),
                spread=spread(model, pairs, M, size))


def spread(model, pairs, M, size):
    """How much the corners of the picture move when the model is fitted without one of the controls, each in
    turn (the largest move, metres): small for a fit the controls hold firmly, large for one that only
    extrapolates (a homography from controls in the middle of a cut photo). inf when it cannot be fitted."""
    W, H = size
    corners = np.array([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)])
    at = apply_h(M, corners)
    worst = 0.0
    for i in range(len(pairs)):
        Mi = model(pairs[:i] + pairs[i + 1:])
        if Mi is None:
            return float("inf")
        worst = max(worst, float(np.hypot(*(apply_h(Mi, corners) - at).T).max()))
    return worst


def flat_spread(cp, gp, pairs, size):
    """spread() of the flat fit (axis_scaled) on the pairs."""
    def model(p):
        return on_sheet(cp[[c for _, c in p]], gp[[k for k, _ in p]]) if len(p) >= 2 else None
    return spread(model, pairs, model(pairs), size)


def perspective(cp, gp, keep, size):
    """A homography grown from the controls the flat fit matched (with fewer than H_MIN pairs an affine
    transform leads the way)."""
    def model(pairs):
        src, dst = cp[[c for _, c in pairs]], gp[[k for k, _ in pairs]]
        try:
            M = homography(src, dst) if len(pairs) >= H_MIN else affine(src, dst)
        except (GeorefError, np.linalg.LinAlgError):
            return None
        return M if h_sane(M, size) else None
    return grow(cp, gp, keep, size, model, H_MIN)


def on_sheet(src, dst):
    """The transform from the straightened sheet to the ground: the flat fit (axis_scaled: similarity, the two
    axes of the sheet scaled apart only when the controls clearly say so; no shear - a printed map is not
    skewed) as a 3 x 3 matrix."""
    sx, sy, ang, tx, ty, _ = axis_scaled(np.asarray(src, float), np.asarray(dst, float))
    c, s = math.cos(ang), math.sin(ang)
    return np.array([[sx * c, -sy * s, tx], [sx * s, sy * c, ty], [0.0, 0.0, 1.0]])


def sheet_aspect(quad, focal=None):
    """Width / height of the rectangle a quadrilateral in the photo is a picture of (corners centred on the middle
    of the photo, y up, counter-clockwise from the one at the rectangle's (0, 0)), by the focal length the
    quadrilateral itself gives (Zhang and He, whiteboard scanning, 2007; square pixels, the middle of the photo on
    the optical axis). Returns (aspect, focal length in pixels), or None when the photo is taken nearly straight
    from above: then the focal length cannot be told, and the mean lengths of opposite sides are as good.
    focal: the focal length in pixels when it is known; the one the quadrilateral gives is unsteady when the
    phone is tilted only a little (a pixel at a corner moves it by thousands)."""
    q = np.c_[np.asarray(quad, float), np.ones(4)]
    m1, m2, m4, m3 = q                     # rectangle corners (0, 0), (w, 0), (w, h), (0, h)
    try:
        k2 = np.dot(np.cross(m1, m4), m3) / np.dot(np.cross(m2, m4), m3)
        k3 = np.dot(np.cross(m1, m4), m2) / np.dot(np.cross(m3, m4), m2)
    except FloatingPointError:
        return None
    n2, n3 = k2 * m2 - m1, k3 * m3 - m1
    if not focal and abs(n2[2] * n3[2]) < 1e-9:      # two sides parallel: the focal length cannot be told
        return None
    f2 = focal ** 2 if focal else -(n2[0] * n3[0] + n2[1] * n3[1]) / (n2[2] * n3[2])
    if not np.isfinite(f2) or f2 <= 0:
        return None
    w2 = (n2[0] ** 2 + n2[1] ** 2) / f2 + n2[2] ** 2
    h2 = (n3[0] ** 2 + n3[1] ** 2) / f2 + n3[2] ** 2
    if w2 <= 0 or h2 <= 0:
        return None
    return math.sqrt(w2 / h2), math.sqrt(f2)


PHONE_FOCAL = 0.65     # focal length of a phone's main camera, as a share of the photo's diagonal (24-28 mm
                       # in 35 mm terms: 0.55 to 0.65); a photo's EXIF says it exactly when it is there


def sheet_frame(quad, diagonal=None, focal=None):
    """(Q, a, b): the homography from the sheet in the photo (corners centred, y up, counter-clockwise) to a
    rectangle 2a x 2b centred on 0: as wide as the mean of the two sides along it, as high as the sheet's real
    proportions say (sheet_aspect with the focal length: given in pixels, else PHONE_FOCAL x diagonal), else
    as the mean of the other two sides."""
    q = np.asarray(quad, float)
    side = [np.hypot(*(q[(i + 1) % 4] - q[i])) for i in range(4)]
    a, b = (side[0] + side[2]) / 4, (side[1] + side[3]) / 4
    got = sheet_aspect(q, focal or (PHONE_FOCAL * diagonal if diagonal else None))
    if got is not None and 0.5 < got[0] * b / a < 2:
        b = a / got[0]
    return homography(q, [(-a, -b), (a, -b), (a, b), (-a, b)]), a, b


def circles_on_sheet(image, quad, focal=None):
    """circle_sets on the photo straightened by the edges of the sheet (on a slanted photo the circles are
    ellipses). Yields ([(u, v, r)] in picture pixels of the photo, radius in px as on the photo's middle)."""
    W, H = image.size
    qc = [(u - W / 2, H / 2 - v) for u, v in quad]
    Q, a, b = sheet_frame(qc, math.hypot(W, H), focal)
    Wr, Hr = int(round(2 * a)), int(round(2 * b))
    # straight picture px -> straight centred y up -> photo centred y up -> photo px
    R = np.array([[1, 0, -a], [0, -1, b], [0, 0, 1]])
    P = np.array([[1, 0, W / 2], [0, -1, H / 2], [0, 0, 1]])
    C = P @ np.linalg.inv(Q) @ R
    C = C / C[2, 2]
    flat = image.transform((Wr, Hr), Image.PERSPECTIVE, tuple(C.flatten()[:8]), Image.BILINEAR,
                           fillcolor=(255, 255, 255))
    k = math.sqrt(abs(np.linalg.det(jacobian(Q, 0.0, 0.0))))      # straight px per photo px in the middle
    for circles, r in circle_sets(flat, photo=True):
        back = apply_h(C, [c[:2] for c in circles]) if circles else []
        yield [(float(u), float(v), c[2] / k) for (u, v), c in zip(back, circles)], r / k


def by_paper(cp, gp, size, quad, radius_px, focal=None):
    """The perspective from the edges of the paper: the quadrilateral of the sheet in the photo (centred, y up)
    is made a rectangle with the mean lengths of its opposite sides, the circles are matched there as in a
    flat picture (ransac, refine), and the flat fit from the rectangle (on_sheet) fits the controls. The edges span
    the whole photo, so the corners of the map do not depend on a few controls in its middle."""
    try:
        Q, a, b = sheet_frame(quad, math.hypot(*size), focal)
    except (GeorefError, np.linalg.LinAlgError):
        return None
    cr = apply_h(Q, cp)
    n, p, pairs = ransac(cr, gp, radius_px * math.sqrt(abs(np.linalg.det(jacobian(Q, 0.0, 0.0)))))
    if p is None or n < MIN_INLIERS:
        return None
    keep = refine(cr, gp, p, pairs)

    def model(pairs):
        if len(pairs) < 3:
            return None
        M = on_sheet(cr[[c for _, c in pairs]], gp[[k for k, _ in pairs]]) @ Q
        M = M / M[2, 2]
        return M if h_sane(M, size) else None
    got = grow(cp, gp, keep, size, model, MIN_INLIERS)
    if got is not None and got["n"] >= BEND_MIN:
        bent = bend_fit(cr[[c for _, c in got["pairs"]]], gp[[k for k, _ in got["pairs"]]], a, b)
        if bent is not None and bent["rms"] <= (1 - BEND_GAIN) * got["rms"]:
            got.update(bent, Q=Q.tolist())
    return got


BEND_MIN = 15          # a bent sheet is straightened only with this many controls
BEND_GAIN = 0.15       # ... and only when that makes the RMS this much smaller
BEND_MAX = 0.1         # ... by at most this share of the half length of the sheet at its ends


def bent(pts, axis, k, a, b):
    """Points of the straightened sheet (rectangle 2a x 2b) moved as a sheet bent along one of its axes moves
    them: axis 0 shifts y by k x^2 / a (the sheet curls over its x axis), axis 1 shifts x by k y^2 / b."""
    p = np.array(pts, float)
    if axis == 0:
        p[:, 1] += k * p[:, 0] ** 2 / a
    else:
        p[:, 0] += k * p[:, 1] ** 2 / b
    return p


def unbent(pts, axis, k, a, b):
    """The inverse of bent()."""
    return bent(pts, axis, -k, a, b)


def _golden_minimum(f, bounds, method=None, tol=1e-6):
    """Minimum of f on bounds (golden section): an object with x and fun, like scipy's minimize_scalar."""
    lo, hi = bounds
    g = (5 ** 0.5 - 1) / 2
    x1, x2 = hi - g * (hi - lo), lo + g * (hi - lo)
    f1, f2 = f(x1), f(x2)
    while hi - lo > tol:
        if f1 < f2:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - g * (hi - lo)
            f1 = f(x1)
        else:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + g * (hi - lo)
            f2 = f(x2)
    x = (lo + hi) / 2
    return type("Res", (), dict(x=x, fun=f(x)))


def bend_fit(src, dst, a, b):
    """The bend of the sheet (bent()) that fits the controls best, with the flat fit on top: dict(rms,
    bend = [axis, k, a, b], S = the flat fit as 3 x 3) or None."""
    try:
        from scipy.optimize import minimize_scalar
    except ImportError:  # scipy.optimize blocked (Windows Application Control): golden section does the same job
        minimize_scalar = _golden_minimum

    def rms(axis, k):
        p = bent(src, axis, k, a, b)
        return float(np.sqrt(((apply_h(on_sheet(p, dst), p) - dst) ** 2).sum(1).mean()))
    best = None
    for axis in (0, 1):
        r = minimize_scalar(lambda k: rms(axis, k), bounds=(-BEND_MAX, BEND_MAX), method="bounded")
        if best is None or r.fun < best[0]:
            best = (float(r.fun), axis, float(r.x))
    if best is None or abs(best[2]) >= 0.98 * BEND_MAX:
        return None                       # at the limit: not a bend the sheet can have
    rms_, axis, k = best
    return dict(rms=rms_, bend=[axis, k, a, b], S=on_sheet(bent(src, axis, k, a, b), dst).tolist())


def to_metres(f, size, pts):
    """Picture pixels [(u, v)] -> metres (east, north) with the fit of fit()."""
    W, H = size
    p = np.array([[u - W / 2, H / 2 - v] for u, v in pts], float)
    if f.get("bend"):
        return apply_h(f["S"], bent(apply_h(f["Q"], p), *f["bend"]))
    if f.get("H") is not None:
        return apply_h(f["H"], p)
    return apply_similarity((f["scale"], f["angle"], f["tx"], f["ty"]), p, f["scale_y"])


def from_metres(f, size, xy):
    """Metres -> picture pixels [(u, v)]: the inverse of to_metres for a fit with H (and maybe a bend)."""
    W, H = size
    if f.get("bend"):
        c = apply_h(np.linalg.inv(f["Q"]), unbent(apply_h(np.linalg.inv(f["S"]), xy), *f["bend"]))
    else:
        c = apply_h(np.linalg.inv(np.asarray(f["H"], float)), xy)
    return np.c_[c[:, 0] + W / 2, H / 2 - c[:, 1]]


RECTIFIED_MAX_PX = 5000   # the longer side of a straightened photo


def paper_mask(image):
    """Where the paper is in the photo (bool array, the size of the picture), or None when it cannot be told
    from the table: the colour of the paper (paper_colour) is light and grey on paper and the colour of the table
    elsewhere. The largest such part, with its holes (the map drawing) filled."""
    W, H = image.size
    k = max(1, math.ceil(max(W, H) / PAPER_SIDE_PX))
    small = image.resize((max(1, W // k), max(1, H // k)), Image.BOX)
    est = paper_colour(small) / 255.0
    mx, mn = est.max(-1), est.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    m = (sat < 0.25) & (mx > 0.5 * np.percentile(mx, 98))
    lab, n = ndi.label(m)
    if n == 0:
        return None
    sizes = ndi.sum(m, lab, range(1, n + 1))
    best = int(np.argmax(sizes)) + 1
    m = ndi.binary_fill_holes(lab == best)
    if m.sum() < 0.2 * m.size:
        return None
    m = ndi.binary_dilation(m, iterations=2)
    return np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((W, H), Image.NEAREST)) > 0


QUAD_SIDE_PX = 800     # the sheet is looked for on a copy this large
SHEET_MIN = 0.12       # ... and it has to take up at least this share of the photo


def _sheet(image, all_parts=False):
    """(small copy as float RGB, bool mask of the sheet on it, how much smaller) or None: everything whose
    chromaticity differs from the table, which is what the frame of the photo shows. A shadow keeps the
    chromaticity; a white table has the chromaticity of the paper, and then nothing is found.
    all_parts=True: how many separate parts larger than a tenth of the photo there are instead (two sheets)."""
    W, H = image.size
    k = max(1, math.ceil(max(W, H) / QUAD_SIDE_PX))
    a = np.asarray(image.resize((max(1, W // k), max(1, H // k)), Image.BOX), np.float32)
    h, w = a.shape[:2]
    chroma = a / np.maximum(a.sum(-1, keepdims=True), 1.0)
    b = max(2, int(0.02 * min(h, w)))
    frame = np.r_[chroma[:b].reshape(-1, 3), chroma[-b:].reshape(-1, 3), chroma[:, :b].reshape(-1, 3),
                  chroma[:, -b:].reshape(-1, 3)]
    table = np.median(frame, 0)
    spread = np.median(np.abs(frame - table).sum(-1))
    if np.abs(table - 1 / 3).sum() < 0.04:            # the frame is grey: a grey table, or paper to the edge
        return None
    d = np.abs(chroma - table).sum(-1)
    m = d > max(0.04, 4 * spread)
    m = ndi.binary_opening(m, iterations=2)
    lab, n = ndi.label(m)
    if n == 0:
        return None
    sizes = ndi.sum(m, lab, range(1, n + 1))
    if all_parts:
        return int((sizes > 0.1 * m.size).sum())
    big = int(np.argmax(sizes)) + 1
    return a, ndi.binary_fill_holes(lab == big), k


BLURRY = 12.0          # photo_quality: below this sharpness a photo is too blurred to find circles in
DARK = 0.18            # ... and below this mean brightness too dark


def photo_quality(image):
    """What may be wrong with a photo, to say it when it cannot be placed: dict(sharpness = variance of the
    Laplacian of the brightness on a copy 1000 px large, brightness 0..1, sheets = how many separate sheets lie on
    the table, blurry, dark)."""
    W, H = image.size
    k = max(1, math.ceil(max(W, H) / 1000))
    g = np.asarray(image.convert("L").resize((max(1, W // k), max(1, H // k)), Image.BOX), np.float32)
    sharp = float(ndi.laplace(g).var())
    bright = float(g.mean() / 255)
    sheets = 0
    got = _sheet(image, all_parts=True)
    if got is not None:
        sheets = got
    # an empty picture (one colour) is neither: it simply has no map in it
    plain = float(g.std()) < 0.04 * max(float(g.mean()), 1.0)
    return dict(sharpness=sharp, brightness=bright, sheets=sheets, blurry=sharp < BLURRY and not plain,
                dark=bright < DARK and not plain)


def paper_quad(image):
    """The four corners of the sheet in a photo, in picture pixels, counter-clockwise as seen with y up (the
    order a homography to a square needs), or None when there is no clear quadrilateral sheet lying wholly in
    the picture (no table around it, a cut-off corner, two sheets, a white table)."""
    from scipy.spatial import ConvexHull
    got = _sheet(image)
    if got is None:
        return None
    a, m, k = got
    h, w = m.shape
    if m.sum() < SHEET_MIN * m.size:
        return None
    ys, xs = np.nonzero(m ^ ndi.binary_erosion(m))
    pts = np.c_[xs + 0.5, ys + 0.5]
    hull = pts[ConvexHull(pts).vertices]
    # the sheet is convex: where the map drawing at its edge has the table's colour, the mask has a notch, which
    # must not pull a side in; the sides are fitted on the outline of the convex hull
    from PIL import ImageDraw
    outline = Image.new("L", (w, h), 0)
    ImageDraw.Draw(outline).polygon([tuple(p) for p in hull], fill=255)
    full = np.asarray(outline) > 0
    ys, xs = np.nonzero(full ^ ndi.binary_erosion(full))
    pts = np.c_[xs + 0.5, ys + 0.5]
    # the four hull points that keep the most area: drop the least important vertex until four are left
    poly = list(map(tuple, hull))
    while len(poly) > 4:
        areas = []
        for i in range(len(poly)):
            (ax, ay), (bx, by) = np.subtract(poly[i - 1], poly[i]), np.subtract(poly[(i + 1) % len(poly)], poly[i])
            areas.append(abs(ax * by - ay * bx))
        poly.pop(int(np.argmin(areas)))
    poly = np.array(poly)
    area = 0.5 * abs(np.dot(poly[:, 0], np.roll(poly[:, 1], 1)) - np.dot(poly[:, 1], np.roll(poly[:, 0], 1)))
    if area < SHEET_MIN * w * h or m.sum() < 0.9 * area:
        return None
    # each side again as the straight line through the edge pixels along its middle part (the hull corners may
    # be off where a corner lies in a shadow): a wide band first, then a narrow one around the line found
    lines = []
    for i in range(4):
        p, q = poly[i], poly[(i + 1) % 4]
        L = np.hypot(*(q - p))
        c, dirn = p, (q - p) / L
        for band in (max(6.0, 0.06 * L), max(3.0, 0.015 * L), 2.0):
            nrm = np.array([-dirn[1], dirn[0]])
            t = (pts - p) @ ((q - p) / L)
            near = (np.abs((pts - c) @ nrm) < band) & (t > 0.1 * L) & (t < 0.9 * L)
            if near.sum() < 10:
                return None
            c = pts[near].mean(0)
            dirn = np.linalg.svd(pts[near] - c)[2][0]
        on_frame = (pts[near, 0] < 1.5) | (pts[near, 0] > w - 1.5) | (pts[near, 1] < 1.5) | (pts[near, 1] > h - 1.5)
        if on_frame.mean() > 0.5:
            return None                               # this side is the edge of the photo: the sheet is cut
        lines.append((c, dirn))
    corners = []
    for i in range(4):
        (c1, d1), (c2, d2) = lines[i - 1], lines[i]
        A = np.c_[d1, -d2]
        if abs(np.linalg.det(A)) < 1e-6:
            return None
        s = np.linalg.solve(A, c2 - c1)
        corners.append(c1 + s[0] * d1)
    corners = np.array(corners)
    over = 0.01 * max(w, h)
    if (corners[:, 0] < -over).any() or (corners[:, 0] > w + over).any() or (corners[:, 1] < -over).any() \
            or (corners[:, 1] > h + over).any():
        return None                                   # a corner off the photo: the sheet is cut
    corners = corners * k
    cx, cy = corners.mean(0)
    order = np.argsort(np.arctan2(-(corners[:, 1] - cy), corners[:, 0] - cx))     # angle with y up
    return [tuple(map(float, c)) for c in corners[order]]


def rectify(image, f, lat0, lon0, mask=None):
    """A photo placed by a homography, straightened: north up, the scale of the fit in its middle, only the paper
    (mask) and white around it. Returns the GeoMap of the new picture (no rotation, no title bar)."""
    W, H = image.size
    M = np.asarray(f["H"], float)
    res = math.sqrt(abs(np.linalg.det(jacobian(M, 0.0, 0.0))))      # metres per pixel in the middle
    if mask is None:
        mask = np.ones((H, W), bool)
    ys, xs = np.nonzero(mask[::8, ::8])
    pts = np.c_[xs * 8 + 4 - W / 2, H / 2 - (ys * 8 + 4)]
    if len(pts) == 0:
        pts = np.array([[-W / 2, -H / 2], [W / 2, -H / 2], [W / 2, H / 2], [-W / 2, H / 2]])
    g = apply_h(M, pts)
    x0, x1, y0, y1 = g[:, 0].min(), g[:, 0].max(), g[:, 1].min(), g[:, 1].max()
    res = max(res, max(x1 - x0, y1 - y0) / RECTIFIED_MAX_PX)
    Wo, Ho = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    # output pixel -> metres -> centred picture coordinates (y up) -> picture pixels
    G = np.array([[res, 0, x0], [0, -res, y1], [0, 0, 1]])
    P = np.array([[1, 0, W / 2], [0, -1, H / 2], [0, 0, 1]])
    C = P @ np.linalg.inv(M) @ G
    C = C / C[2, 2]
    method, data = Image.PERSPECTIVE, tuple(C.flatten()[:8])
    if f.get("bend"):
        # a bent sheet is no homography: a mesh of small cells, each mapped by its corners
        step, cells = 48, []
        for y in range(0, Ho, step):
            for x in range(0, Wo, step):
                box = (x, y, min(x + step, Wo), min(y + step, Ho))
                corners = [(box[0], box[1]), (box[0], box[3]), (box[2], box[3]), (box[2], box[1])]
                xy = apply_h(G, corners)
                cells.append((box, tuple(from_metres(f, (W, H), xy).flatten())))
        method, data = Image.MESH, cells
    out = image.transform((Wo, Ho), method, data, Image.BILINEAR, fillcolor=(255, 255, 255))
    keep = Image.fromarray(mask.astype(np.uint8) * 255).transform((Wo, Ho), method, data, Image.NEAREST)
    out = Image.composite(out, Image.new("RGB", (Wo, Ho), (255, 255, 255)), keep)
    ky = R_EARTH * math.pi / 180
    kx = R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    gm = GeoMap(out, lat0 + y1 / ky, lat0 + (y1 - Ho * res) / ky, lon0 + (x0 + Wo * res) / kx, lon0 + x0 / kx,
                rotation=0.0, header_px=0)
    return gm


# --- placing by hand: points clicked on the photo -------------------------------------------------------------

MANUAL_MIN = 4          # points needed
MANUAL_FAR_M = 40.0     # a point this far from where the others put it is probably on the wrong circle
MANUAL_LINE = 0.1       # the points lie nearly on a line when the spread across is below this share of along


def fit_points(px, ground, size, quad=None, focal=None):
    """The transform from points clicked on a picture to where they are on the ground, shared by the page for
    placing a photo by hand (webapp/views/photo.py) and the job that saves it.

    px: [(u, v)] in picture pixels; ground: [(x, y)] metres; size: the picture's size; quad: paper_quad() or
    None. With 4 or 5 points an affine transform (6 numbers; a homography of 8 would fit any 4 points exactly and
    follow the 5 to 15 m of GPS error), from 6 points a homography when it is a quarter better; with the edges of
    the sheet the perspective comes from them and the points fix the flat fit (on_sheet) on top, as fit() does.
    Every point's deviation is measured leaving it out (with all points in, 4 points would always fit).

    Returns dict(H, kind, rms, n, deviation = [metres per point], problems = [(code, point index or None)]).
    Codes: few, line, mirror, far (this point is on the wrong circle), loose (the points do not agree, which one
    is off cannot be told). H is None when there are too few points or they lie on a line."""
    W, H = size
    src = np.array([[u - W / 2, H / 2 - v] for u, v in px], float).reshape(-1, 2)
    dst = np.asarray(ground, float).reshape(-1, 2)
    n = len(src)
    out = dict(H=None, kind=None, rms=None, n=n, deviation=[None] * n, problems=[])
    if n < MANUAL_MIN:
        out["problems"].append(("few", None))
        return out
    for pts in (src, dst):
        sv = np.linalg.svd(pts - pts.mean(0), compute_uv=False)
        if sv[1] < MANUAL_LINE * sv[0]:
            out["problems"].append(("line", None))
            return out
    Q = None
    if quad is not None:
        try:
            Q = sheet_frame([(u - W / 2, H / 2 - v) for u, v in quad], math.hypot(W, H), focal)[0]
        except (GeorefError, np.linalg.LinAlgError):
            Q = None

    def model(idx, kind):
        s, d = src[idx], dst[idx]
        if kind == "paper":
            M = on_sheet(apply_h(Q, s), d) @ Q
            return M / M[2, 2]
        return homography(s, d) if kind == "homography" else affine(s, d)

    def rms_of(M, idx):
        return float(np.sqrt(((apply_h(M, src[idx]) - dst[idx]) ** 2).sum(1).mean()))
    every = np.arange(n)
    kinds = {"affine": model(every, "affine")}
    if Q is not None:
        kinds["paper"] = model(every, "paper")
    if n >= 6:
        try:
            kinds["homography"] = model(every, "homography")
        except (GeorefError, np.linalg.LinAlgError):
            pass
    flat = rms_of(kinds["affine"], every)
    kind = "affine"
    if "paper" in kinds and h_sane(kinds["paper"], size) and rms_of(kinds["paper"], every) <= max(1.15 * flat, flat + 3):
        kind = "paper"
    elif "homography" in kinds and h_sane(kinds["homography"], size) \
            and rms_of(kinds["homography"], every) <= (1 - H_GAIN) * flat:
        kind = "homography"
    M = kinds[kind]
    if np.linalg.det(jacobian(M, 0.0, 0.0)) <= 0:
        out["problems"].append(("mirror", None))
    def leave_one_out(idx):
        """{point: its distance from where the other points of idx put it}."""
        dev = {}
        for i in idx:
            rest = np.array([j for j in idx if j != i])
            sv = np.linalg.svd(dst[rest] - dst[rest].mean(0), compute_uv=False)
            if sv[1] < 2 * MANUAL_LINE * sv[0]:
                dev[i] = None            # the others nearly on a line: where they put this point says nothing
                continue
            k = kind if not (kind == "homography" and len(rest) < H_MIN) else "affine"
            try:
                dev[i] = float(np.hypot(*(apply_h(model(rest, k), src[[i]])[0] - dst[i])))
            except (GeorefError, np.linalg.LinAlgError):
                dev[i] = None
        return dev
    dev = leave_one_out(list(every))
    if max(d or 0 for d in dev.values()) > MANUAL_FAR_M:
        # one point on the wrong circle throws every other one off too: the culprit is the point without which
        # the rest fit best (from 5 points on; with 4 the other 3 always fit exactly)
        culprit = None
        if n >= 5:
            rests = {i: rms_of(model(np.delete(every, i), "affine"), np.delete(every, i)) for i in range(n)}
            i = min(rests, key=rests.get)
            if rests[i] < MANUAL_FAR_M / 2:
                culprit = i
        if culprit is None:
            out["problems"].append(("loose", max(dev, key=lambda i: dev[i] or 0)))
        else:
            dev.update(leave_one_out([j for j in range(n) if j != culprit]))
            out["problems"].append(("far", culprit))
    out["deviation"] = [dev[i] for i in range(n)]
    out.update(H=M, kind=kind, rms=rms_of(M, every))
    return out


def place_by_points(image, points, ground, lat0, lon0):
    """Place a picture by points clicked on it: points {control index | "S" | "C": (u, v)}; ground:
    ground_course(). Returns (GeoMap of the straightened picture, fit dict as fit() gives it, with "course").
    Raises GeorefError when the points do not give a sane placing."""
    keys = [k for k in points if (ground["start"] if k == "S" else ground["finish"] if k == "C"
                                  else ground["controls"][k]) is not None]
    where = lambda k: ground["start"] if k == "S" else ground["finish"] if k == "C" else ground["controls"][k]
    quad = paper_quad(image)
    got = fit_points([points[k] for k in keys], [where(k) for k in keys], image.size, quad, photo_focal(image))
    bad = [c for c, _ in got["problems"] if c in ("few", "line", "mirror")]
    if got["H"] is None or bad or not h_sane(got["H"], image.size):
        raise GeorefError("the points do not place the picture: " + (", ".join(bad) or "not sane"))
    J = jacobian(got["H"], 0.0, 0.0)
    f = dict(kind="manual-" + got["kind"], H=got["H"].tolist(), rms=got["rms"], n=got["n"],
             scale=math.sqrt(abs(np.linalg.det(J))), angle=math.atan2(J[1, 0] - J[0, 1], J[0, 0] + J[1, 1]),
             pairs=[], photo=quad is not None or purple_mask(image.convert("RGB")).sum() < 500,
             deviation=got["deviation"], problems=got["problems"])
    f["scale_y"] = f["scale"]
    f["tx"], f["ty"] = (float(v) for v in apply_h(got["H"], [[0.0, 0.0]])[0])
    W, H = image.size
    f["edge_m"] = edge_error(f, image.size, quad or [(0, 0), (W, 0), (W, H), (0, H)], [where(k) for k in keys])
    src = flatten_light(image) if f["photo"] else image
    gm = rectify(src, f, lat0, lon0, paper_mask(image) if f["photo"] else None)
    f["course"] = course_points(gm, lat0, lon0, f, image.size, points, ground)
    return gm, f


START_NEAR_M = 200.0   # the start triangle is taken when it is this close to where the runner was at the start


def course_points(gm, lat0, lon0, f, size, placed, ground):
    """Start, controls and finish in pixels of the placed map gm, for course.save_course: the course read from
    the placing itself instead of from the purple of the picture (a photo has no exact Livelox purple).

    f: the fit (to_metres); size: the picture's size; placed: {control index: (u, v) in the picture} (the matched
    circles, or the points clicked by hand); ground: ground_course(). A control without a circle is where the
    runner punched it; one without either lies halfway between its neighbours. The start is the triangle
    nearest to where the runner was at the start time (within START_NEAR_M), else that place; the finish is
    where the runner was at the finish time."""
    ky = R_EARTH * math.pi / 180
    kx = R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180

    def px(xy):
        u, v = gm.latlon_to_px(lat0 + xy[1] / ky, lon0 + xy[0] / kx)
        return float(u), float(v)
    on_map = lambda key: px(to_metres(f, size, [placed[key]])[0])
    ctrl = []
    for k, g in enumerate(ground["controls"]):
        ctrl.append(on_map(k) if k in placed else px(g) if g is not None else None)
    for k, c in enumerate(ctrl):
        if c is None:
            prev = next((ctrl[j] for j in range(k - 1, -1, -1) if ctrl[j] is not None), None)
            nxt = next((ctrl[j] for j in range(k + 1, len(ctrl)) if ctrl[j] is not None), None)
            both = [p for p in (prev, nxt) if p is not None]
            ctrl[k] = tuple(np.mean(both, 0)) if both else (gm.W / 2, gm.H / 2)
    start = px(ground["start"]) if ground["start"] is not None else ctrl[0]
    finish = on_map("C") if "C" in placed else px(ground["finish"]) if ground["finish"] is not None else ctrl[-1]
    if "S" in placed:
        return dict(start=on_map("S"), controls=ctrl, finish=finish)
    from .course import closed_shapes
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    tri = closed_shapes(loose_purple(gm.image))[1]
    if tri:
        near = min(tri, key=lambda t: math.hypot(t[0] - start[0], t[1] - start[1]))
        if math.hypot(near[0] - start[0], near[1] - start[1]) * mpp <= START_NEAR_M:
            start = (float(near[0]), float(near[1]))
    return dict(start=start, controls=ctrl, finish=finish)


def geomap(image, f, lat0, lon0):
    """The GeoMap (KML LatLonBox + rotation) that places `image` as the fit says. lat0, lon0: the point the
    metres of the fit are measured from (the same to_xy that made the control positions)."""
    W, H = image.size
    ky = R_EARTH * math.pi / 180
    latc = lat0 + f["ty"] / ky
    lonc = lon0 + f["tx"] / (R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180)
    kx = R_EARTH * math.cos(math.radians(latc)) * math.pi / 180
    half_w, half_h = W * f["scale"] / 2, H * f["scale_y"] / 2
    return GeoMap(image, latc + half_h / ky, latc - half_h / ky, lonc + half_w / kx, lonc - half_w / kx,
                  rotation=math.degrees(f["angle"]), header_px=0)


def write_kmz(path, image, gm, name="map", png=False):
    """A KMZ like the Livelox export (one GroundOverlay) from a picture and its GeoMap, marked as having no
    title bar. png=True: the picture is kept without loss (a map without course: its terrain is read by the exact
    colours, which a JPEG would smear)."""
    buf = io.BytesIO()
    if png:
        image.convert("RGB").save(buf, "PNG")
    else:
        image.convert("RGB").save(buf, "JPEG", quality=90)
    href = "files/map.png" if png else "files/map.jpg"
    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n'
           "<!-- ob-header-px: 0 -->\n"
           + (f"<!-- ob-blur-m: {gm.blur_m:.3f} -->\n" if getattr(gm, "blur_m", 0) else "") +
           f"<GroundOverlay><name>{name}</name><Icon><href>{href}</href></Icon>"
           f"<LatLonBox><north>{gm.n:.9f}</north><south>{gm.s:.9f}</south><east>{gm.e:.9f}</east>"
           f"<west>{gm.w:.9f}</west><rotation>{gm.rot:.6f}</rotation></LatLonBox></GroundOverlay>\n</kml>\n")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
        z.writestr(href, buf.getvalue())


def photo_focal(image):
    """The focal length of the camera in pixels of the picture, from the EXIF focal length in 35 mm terms that
    phones write (open_image keeps it), or None."""
    f35 = image.info.get("focal35")
    return float(f35) / 43.27 * math.hypot(*image.size) if f35 else None


def open_image(src):
    """A picture for georeferencing: upright as the EXIF orientation of a phone photo says, RGB, at most
    MAX_SIDE_PX on its longer side, with the EXIF focal length (35 mm terms) in info["focal35"] when it is
    there. A big JPEG is decoded at a reduced size straight away (a 50 Mpx photo would take 150 MB of memory
    otherwise)."""
    im = Image.open(src)
    if im.format == "JPEG" and max(im.size) > 2 * MAX_SIDE_PX:
        im.draft("RGB", (MAX_SIDE_PX, MAX_SIDE_PX))   # scales by 1/2, 1/4 or 1/8 but stays above the size asked
    im.load()
    try:
        focal35 = im.getexif().get_ifd(0x8769).get(0xA405)
    except (AttributeError, KeyError, ValueError, OSError):
        focal35 = None
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    if max(im.size) > MAX_SIDE_PX:
        k = MAX_SIDE_PX / max(im.size)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    if focal35:
        im.info["focal35"] = float(focal35)
    return im


def local_frame(lat0, lon0):
    """to_xy(lat, lon) -> metres (east, north) from lat0, lon0, as the fit measures them."""
    kx = R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    ky = R_EARTH * math.pi / 180
    return lambda la, lo: ((np.asarray(lo) - lon0) * kx, (np.asarray(la) - lat0) * ky)


def shift_kmz(src, dst, corr, lat0, lon0):
    """A copy of the KMZ src at dst with the whole map moved on the ground by the similarity corr = (scale, angle,
    tx, ty) in metres from lat0, lon0 (local_frame): for a map that Livelox (or a screenshot) put a few metres off.
    Only the LatLonBox of the KML changes (centre moved, size scaled, rotation turned); the picture, its title bar
    and everything else stay byte for byte."""
    s, ang, _, _ = corr
    with zipfile.ZipFile(src) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    k = next(n for n, (i, _) in enumerate(items) if i.filename.lower().endswith(".kml"))
    kml = items[k][1].decode("utf-8")

    def get(tag, d=None):
        m = re.search(rf"<{tag}>([^<]+)</{tag}>", kml)
        return float(m.group(1)) if m else d
    n, so, e, w, rot = get("north"), get("south"), get("east"), get("west"), get("rotation", 0.0)
    ky = R_EARTH * math.pi / 180
    kx0 = R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    latc, lonc = (n + so) / 2, (e + w) / 2
    half_w = (e - w) / 2 * R_EARTH * math.cos(math.radians(latc)) * math.pi / 180
    half_h = (n - so) / 2 * ky
    x, y = apply_similarity(corr, [[(lonc - lon0) * kx0, (latc - lat0) * ky]])[0]
    latc2, lonc2 = lat0 + y / ky, lon0 + x / kx0
    kx2 = R_EARTH * math.cos(math.radians(latc2)) * math.pi / 180
    new = dict(north=latc2 + s * half_h / ky, south=latc2 - s * half_h / ky, east=lonc2 + s * half_w / kx2,
               west=lonc2 - s * half_w / kx2, rotation=rot + math.degrees(ang))
    for tag, v in new.items():
        if re.search(rf"<{tag}>", kml):
            kml = re.sub(rf"<{tag}>[^<]+</{tag}>", f"<{tag}>{v:.9f}</{tag}>", kml)
        else:                                       # a box without rotation gets one
            kml = kml.replace("</LatLonBox>", f"<{tag}>{v:.9f}</{tag}></LatLonBox>")
    items[k] = (items[k][0], kml.encode("utf-8"))
    tmp = f"{dst}.tmp.kmz"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            z.writestr(info, data)
    os.replace(tmp, dst)


def track_frame(track):
    """The point the metres are measured from for a track: its mean position."""
    return float(np.nanmean(track["lat"])), float(np.nanmean(track["lon"]))


def place(image, controls, lat0, lon0, screen=False):
    """(GeoMap, fit dict) for a picture and the control positions [(x, y) or None] in metres from lat0, lon0.

    The circles are read as in a Livelox export first. When that does not match nearly every control (a photo:
    shadow, tinted light, the exact purple only in part of it), they are read again as in a photo, and the fit
    with more matched controls (then the smaller RMS) wins.
    screen=True: a screenshot of Livelox (oroute/pair.py): read only as an export, no sheet, no perspective; the
    fit is the flat one or none."""
    n_controls = sum(c is not None for c in controls)
    enough = math.ceil(PHOTO_RETRY * n_controls)
    quad = None if screen else paper_quad(image)      # a sheet lying on a table: certainly a photo
    best, error = None, None
    # nearly every control matched counts the same; then the edges of the sheet; then the smaller RMS
    key = lambda g: (min(g["n"], enough), g["kind"].startswith("paper"), -g["rms"])
    for photo in ((False,) if screen else (False, True)):
        if photo and quad is not None:
            sets = circles_on_sheet(image, quad, photo_focal(image))
        else:
            sets = circle_sets(image, photo=photo, side=SCREEN_SMALL_PX if screen else SMALL_SIDE_PX)
        try:
            for circles, r in sets:
                try:
                    f = fit(circles, controls, r, image.size, quad=quad if photo else None, focal=photo_focal(image),
                            flat=screen)
                except GeorefError as e:
                    error = e if error is None or str(error).startswith("no control circles") else error
                    continue
                f["circles"], f["controls"], f["photo"] = len(circles), n_controls, photo
                f["circle_px"] = [(float(c[0]), float(c[1])) for c in circles]
                if best is None or key(f) > key(best):
                    best = f
                if f["n"] >= enough:
                    break
        except GeorefError as e:          # no circles at all
            error = e if error is None or str(error).startswith("no control circles") else error
        if best is not None and best["n"] >= enough and quad is None:
            break
    if best is None:
        raise error
    W, H = image.size
    best["edge_m"] = max(edge_error(best, image.size, quad or [(0, 0), (W, 0), (W, H), (0, H)],
                                     [controls[k] for k, _ in best["pairs"]]), best.get("unsure_m", 0.0))
    if best["kind"] == "similarity" and not best["photo"]:
        return geomap(image, best, lat0, lon0), best
    # a photo: straightened (north up, the table cut away, the light evened out) so that a KMZ can hold it
    M = best.get("H") or similarity_matrix(best)
    src = flatten_light(image) if best["photo"] else image
    return rectify(src, dict(best, H=M), lat0, lon0, paper_mask(image) if best["photo"] else None), best


def edge_error(f, size, corners, ground):
    """How far off the corners of the map may be (metres): inside the matched controls the fit is as good as
    its RMS; the error grows with the distance from them, roughly in proportion (a scale or rotation slightly
    off). RMS x (distance of the farthest corner from the middle of the controls / distance of the farthest
    matched control), at least the RMS. ground: [(x, y)] of the matched controls."""
    g = np.array(ground, float)
    mid = g.mean(0)
    reach = max(float(np.hypot(*(g - mid).T).max()), 1.0)
    far = float(np.hypot(*(to_metres(f, size, corners) - mid).T).max())
    return float(f["rms"] * max(1.0, far / reach))


def similarity_matrix(f):
    """The flat fit of fit() as a 3 x 3 matrix (centred picture coordinates, y up -> metres)."""
    c, s = math.cos(f["angle"]), math.sin(f["angle"])
    return [[f["scale"] * c, -f["scale_y"] * s, f["tx"]], [f["scale"] * s, f["scale_y"] * c, f["ty"]], [0, 0, 1]]


def crop_frame(f, size, box, out_size):
    """The flat fit of a picture (fit() without H) for a part of it: box (x0, y0, x1, y1) in pixels of the picture
    of size, scaled to out_size (w, h). Rotation stays; the scale grows by how much smaller the part became; the
    middle moves to the middle of the box. geomap() of the new picture places it as the whole one was placed."""
    if f.get("H") is not None:
        raise ValueError("crop_frame needs a flat fit")
    x0, y0, x1, y1 = box
    (tx, ty), = to_metres(f, size, [((x0 + x1) / 2, (y0 + y1) / 2)])
    return dict(f, scale=f["scale"] * (x1 - x0) / out_size[0], scale_y=f["scale_y"] * (y1 - y0) / out_size[1],
                tx=float(tx), ty=float(ty))


def georeference(image, track, start_s, cumulative, course=False):
    """Everything in one call: (GeoMap, fit dict) for a picture, the runner's track and the official times.
    Raises GeorefError with a reason when it cannot be done. course=True: the fit dict gets "course", the
    start, controls and finish in pixels of the GeoMap's picture (course_points)."""
    lat0, lon0 = track_frame(track)
    ground = ground_course(track, local_frame(lat0, lon0), start_s, cumulative)
    gm, f = place(image, ground["controls"], lat0, lon0)
    if course:
        placed = {k: f["circle_px"][c] for k, c in f["pairs"]}
        f["course"] = course_points(gm, lat0, lon0, f, image.size, placed, ground)
    return gm, f
