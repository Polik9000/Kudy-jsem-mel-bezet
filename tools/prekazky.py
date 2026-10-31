#!/usr/bin/env python3
"""Contact sheets of everything a map was read to have as an obstacle, to check the reading by eye.

usage: python3 tools/prekazky.py MAPONLY.kmz OUT_DIR [--cache FILE]

Writes OUT_DIR/ploty_N.jpg (every fence that closes nothing in: the cut-out of the map, and the same with the
fence as it was read in orange) and OUT_DIR/oplocenky_N.jpg (every enclosure, the fenced ground in magenta),
and prints how many there are. A wrong find on these sheets means the rule has to be tightened.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import mapdata  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402
from oroute.render import _font  # noqa: E402

TILE, COLS, ROWS = 230, 6, 3      # pixels of one cut-out, and how many pairs fit on a sheet (two pictures a pair)


def tile(rgb, mask, box, colour):
    u0, v0, u1, v1 = box
    cut = rgb[v0:v1, u0:u1]
    shown = cut.copy()
    m = mask[v0:v1, u0:u1]
    shown[m] = (shown[m] * 0.25 + np.array(colour) * 0.75).astype(np.uint8)
    fit = lambda a: Image.fromarray(a).resize((TILE, TILE), Image.LANCZOS)
    return fit(cut), fit(shown)


def sheets(rgb, mask, spots, mpp, colour, path, pad_m=18.0):
    """spots: [(u0, v0, u1, v1)] of the finds; each gets a square cut-out around it."""
    H, W = mask.shape
    out = []
    for n in range(0, len(spots), COLS // 2 * ROWS):
        sheet = Image.new("RGB", (COLS * (TILE + 4), ROWS * (TILE + 22)), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for k, (a0, b0, a1, b1) in enumerate(spots[n:n + COLS // 2 * ROWS]):
            half = int(max(a1 - a0, b1 - b0) / 2 + pad_m / mpp)
            cu, cv = int((a0 + a1) / 2), int((b0 + b1) / 2)
            box = (max(cu - half, 0), max(cv - half, 0), min(cu + half, W), min(cv + half, H))
            x, y = (k % (COLS // 2)) * 2 * (TILE + 4), (k // (COLS // 2)) * (TILE + 22)
            for i, im in enumerate(tile(rgb, mask, box, colour)):
                sheet.paste(im, (x + i * (TILE + 2), y + 20))
            d.text((x + 2, y + 2), f"{n + k + 1}: ({cu}, {cv}) {2 * half * mpp:.0f} m", fill=(0, 0, 0), font=_font(13))
        name = f"{path}_{n // (COLS // 2 * ROWS) + 1}.jpg"
        sheet.save(name, quality=88)
        out.append(name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kmz")
    ap.add_argument("out")
    ap.add_argument("--cache", help="terrain cache file (mapdata.terrain)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for old in os.listdir(a.out):
        if old.startswith(("ploty_", "oplocenky_")):
            os.remove(os.path.join(a.out, old))
    gm = GeoMap.from_kmz(a.kmz)
    rgb, mpp = np.asarray(gm.image), gm.m_per_px_x
    obs = mapdata.obstacles(gm, mapdata.terrain(gm, a.kmz, a.cache))
    grow = max(1, int(round(1.2 / mpp)))
    from scipy.ndimage import binary_dilation
    fences = [(min(p[0] for p in line), min(p[1] for p in line), max(p[0] for p in line), max(p[1] for p in line))
              for line in obs["fences"]]
    made = sheets(rgb, binary_dilation(obs["hard"], iterations=grow), fences, mpp, (255, 110, 0),
                  os.path.join(a.out, "ploty"))
    r = lambda area: (area ** 0.5) / mpp / 2
    pens = [(u - r(area), v - r(area), u + r(area), v + r(area)) for u, v, area in obs["pens"]]
    made += sheets(rgb, obs["blocked"], pens, mpp, (230, 0, 200), os.path.join(a.out, "oplocenky"))
    print(f"{os.path.basename(a.kmz)}: {len(fences)} fences ({obs['hard'].sum() * mpp:.0f} m of line, roughly), "
          f"{len(pens)} enclosures; {len(made)} sheets in {a.out}")


if __name__ == "__main__":
    main()
