"""A map with the course drawn on it, made usable as a map without course.

The purple course (ISOM 7xx) and the red line of the runner's track that Livelox draws over the map hide the
terrain under them. mask() finds those pixels, fill() puts the terrain of their surroundings in their place, so
that terrain.classify can read the picture. It is an estimate: a ring and a connecting line (one or two lines
wide) fill in well, a whole path hidden under a line does not come back unless it goes on past the mask (the
"bridge" variant joins black lines across a gap along their direction).
"""
import os

import numpy as np
from scipy import ndimage as ndi

from . import course as _course
from . import georef

VERSION = 1
GROW_PX = 2                 # the antialiased edge of a line is not purple any more, but hides the map all the same
VARIANTS = ("nearest", "median", "bridge")


def red_mask(rgb):
    """The red line of a track (Livelox: about (216, 26, 34)). Not the brown or orange of the map."""
    a = np.asarray(rgb).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r > 170) & (g < 90) & (b < 90) & (r - g > 110) & (abs(g - b) < 50)


def mask(rgb, red=True, grow=GROW_PX):
    """Pixels of the picture hidden by the course (purple) and, with red, by the track line."""
    rgb = np.asarray(rgb)
    m = _course.purple_mask(rgb)
    if m.sum() < 500:
        m = m | georef.loose_purple(rgb)
    if red:
        m = m | red_mask(rgb)
    if grow and m.any():
        m = ndi.binary_dilation(m, iterations=grow)
    return m


def share(m):
    """The share of the picture that is hidden."""
    return float(m.mean()) if m.size else 0.0


def _nearest(rgb, m):
    _, (iy, ix) = ndi.distance_transform_edt(m, return_indices=True)
    return rgb[iy, ix]


def _median(rgb, m, rounds=64):
    """Peel the mask from its edge inward: each pixel gets the median of the known pixels around it."""
    out = rgb.copy()
    todo = m.copy()
    for _ in range(rounds):
        if not todo.any():
            break
        known = ~todo
        edge = todo & ndi.binary_dilation(known)
        ys, xs = np.nonzero(edge)
        H, W = todo.shape
        for k in range(3):
            vals = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)
                    ok = known[yy, xx]
                    vals.append(np.where(ok, out[yy, xx, k].astype(float), np.nan))
            out[ys, xs, k] = np.nan_to_num(np.nanmedian(np.stack(vals), axis=0)).astype(np.uint8)
        todo[ys, xs] = False
    if todo.any():
        out[todo] = _nearest(rgb, m)[todo]
    return out


def _bridge(rgb, m):
    """Nearest fill, then black lines that enter the hidden part from two sides are joined across it: a
    path or a fence under the course goes on. Joined are pixels of the mask whose two opposite neighbours at
    some distance (along any of four directions) outside the mask are both dark and unsaturated."""
    out = _nearest(rgb, m)
    a = rgb.astype(int)
    dark = (a.mean(-1) < 150) & (a.max(-1) - a.min(-1) < 45) & ~m
    H, W = m.shape
    dist = ndi.distance_transform_edt(m)
    reach = int(min(12, max(2, dist.max())))
    join = np.zeros_like(m)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for d in range(1, reach + 1):
            sy, sx = dy * d, dx * d
            ys, xs = np.nonzero(m)
            ya, xa = np.clip(ys + sy, 0, H - 1), np.clip(xs + sx, 0, W - 1)
            yb, xb = np.clip(ys - sy, 0, H - 1), np.clip(xs - sx, 0, W - 1)
            both = dark[ya, xa] & dark[yb, xb]
            # the ends must be close to the same line: only the nearest few steps count
            join[ys[both], xs[both]] = True
    # only a thin join (a line, not a patch)
    join &= m & ~ndi.binary_erosion(ndi.binary_dilation(join), iterations=3)
    out[join] = (0, 0, 0)
    return out


def fill(rgb, m, variant="nearest"):
    """The picture with the hidden pixels replaced by an estimate of the terrain under them."""
    rgb = np.asarray(rgb)
    if not m.any():
        return rgb.copy()
    if variant == "nearest":
        return _nearest(rgb, m)
    if variant == "median":
        return _median(rgb, m)
    if variant == "bridge":
        return _bridge(rgb, m)
    raise ValueError(f"unknown variant {variant!r}")


def repair(rgb, variant="nearest", red=True):
    """(picture with the course taken out, mask, share of the picture hidden)."""
    rgb = np.asarray(rgb)
    m = mask(rgb, red=red)
    return fill(rgb, m, variant), m, share(m)


def hidden_along(m, pts_px, step_px=4):
    """The share of a route (a list of (u, v) map pixels) that runs over hidden pixels: how far an estimate
    from the covered map can be trusted along it."""
    if len(pts_px) < 2:
        return 0.0
    H, W = m.shape
    n = hit = 0
    for (u0, v0), (u1, v1) in zip(pts_px[:-1], pts_px[1:]):
        k = max(1, int(max(abs(u1 - u0), abs(v1 - v0)) / step_px))
        for t in np.linspace(0, 1, k + 1):
            u, v = int(round(u0 + (u1 - u0) * t)), int(round(v0 + (v1 - v0) * t))
            if 0 <= u < W and 0 <= v < H:
                n += 1
                hit += bool(m[v, u])
    return hit / n if n else 0.0


def derive_kmz(course_kmz, out_kmz, variant="nearest"):
    """Write a KMZ of the map of course_kmz with the course (and a red track line) taken out, to be read as a
    map without course. Returns the share of the picture that was hidden. The variant that measured best is
    the default (docs/jen-mapa-s-trati.md)."""
    from .kmzmap import GeoMap
    gm = GeoMap.from_kmz(course_kmz)
    fixed, _, hidden = repair(np.asarray(gm.image), variant)
    from PIL import Image
    tmp = f"{out_kmz}.{os.getpid()}.tmp"
    georef.write_kmz(tmp, Image.fromarray(fixed), gm, png=True)
    os.replace(tmp, out_kmz)
    return hidden
