"""How much does it matter that the map has the course (and the runner's red line) on it?

For every race that has both maps (a folder with course.kmz, maponly.kmz, run.fit): the best routes are found on
the map without course (the reference) and on the map with course after oroute/occlusion.py took the course out,
once with a red track line drawn over it and once without. The routes are compared leg by leg.

    python tools/jen_mapa_s_trati.py OUT_DIR FOLDER [FOLDER ...] [--variants nearest,median,bridge]

FOLDER holds course.kmz, maponly.kmz, run.fit (tests/golden/<name>/dem_cache.npz is used for the elevation when
it exists, else the network). Output: OUT_DIR/summary.csv, OUT_DIR/<race>/<variant>/ and crops of the filled map.
"""
import argparse
import csv
import os
import shutil
import statistics
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from oroute import georef, occlusion  # noqa: E402
from oroute.fitload import load_track  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402

RED = (216, 26, 34)       # the colour Livelox draws the track in (measured on a screenshot)
SAME_LEN = 0.03           # best routes of this relative length difference are taken for the same variant
SAME_SHARE_MIN = 0.85     # decided beforehand: the share of legs with the same route ...
MEDIAN_DIFF_MAX = 0.05    # ... and the median relative difference of the time of the best route


def _run(*cmd):
    return subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)


def secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def read_legs(path):
    with open(path, encoding="utf-8") as f:
        return {r["leg"]: r for r in csv.DictReader(f)}


def draw_track(img, gm, fit, red=RED):
    """The track of the run in red over the picture, as Livelox shows it (about 4 m wide)."""
    tr = load_track(fit)
    pts = [tuple(float(a) for a in gm.latlon_to_px(la, lo)) for la, lo in zip(tr['lat'], tr['lon'])]
    out = img.copy()
    ImageDraw.Draw(out).line(pts, fill=red, width=max(3, int(round(4.0 / gm.m_per_px_x))))
    return out


def one(folder, out, variants):
    name = os.path.basename(os.path.normpath(folder))
    course_kmz, maponly, fit = (os.path.join(folder, f) for f in ("course.kmz", "maponly.kmz", "run.fit"))
    race = os.path.join(out, name)
    os.makedirs(race, exist_ok=True)
    r = _run("analyze.py", course_kmz, fit, race)
    if r.returncode:
        print(name, "analyze failed:", r.stderr[-300:])
        return []
    golden = os.path.join(ROOT, "tests", "golden", name, "dem_cache.npz")

    def best(kmz, sub):
        d = os.path.join(race, sub)
        os.makedirs(d, exist_ok=True)
        if os.path.exists(golden):
            shutil.copyfile(golden, os.path.join(d, "dem_cache.npz"))
        r = _run("bestroute.py", kmz, os.path.join(race, "course.json"), fit, d, "--title", name, "--no-images")
        if r.returncode:
            print(name, sub, "bestroute failed:", r.stderr[-300:])
            return None
        return read_legs(os.path.join(d, "best_legs.csv"))

    ref = best(maponly, "ref")
    if ref is None:
        return []
    gm = GeoMap.from_kmz(course_kmz)
    rows = []
    for red in (False, True):
        base = draw_track(gm.image, gm, fit) if red else gm.image
        for v in variants:
            rgb = np.asarray(base)
            fixed, m, hid = occlusion.repair(rgb, v, red=red)
            tag = f"{v}{'-cervena' if red else ''}"
            kmz = os.path.join(race, f"mapa-{tag}.kmz")
            georef.write_kmz(kmz, Image.fromarray(fixed), gm, png=True)
            Image.fromarray(np.where(m[..., None], np.array([255, 0, 255], np.uint8), rgb)[:1500, :1500]).save(
                os.path.join(race, f"maska-{tag}.png"))
            Image.fromarray(fixed[:1500, :1500]).save(os.path.join(race, f"doplneno-{tag}.png"))
            got = best(kmz, tag)
            if got is None:
                continue
            same = diffs = 0
            diffs = []
            for leg, a in ref.items():
                b = got.get(leg)
                if not b or not a["best_m"] or not b["best_m"]:
                    continue
                dl = abs(float(b["best_m"]) - float(a["best_m"])) / max(float(a["best_m"]), 1)
                dt = abs(secs(b["best_model"]) - secs(a["best_model"])) / max(secs(a["best_model"]), 1)
                dy = abs(secs(b["your_line_model"]) - secs(a["your_line_model"])) / max(secs(a["your_line_model"]), 1)
                same += dl <= SAME_LEN
                diffs.append((dt, dy))
                rows.append(dict(race=name, variant=tag, leg=leg, hidden=round(hid, 4), same=int(dl <= SAME_LEN),
                                 d_len=round(dl, 4), d_best_time=round(dt, 4), d_your_time=round(dy, 4)))
            if diffs:
                print(f"{name:14s} {tag:18s} hidden {hid:6.1%}  same route {same}/{len(diffs)}  "
                      f"median dt {statistics.median(d[0] for d in diffs):.1%}  "
                      f"median dyour {statistics.median(d[1] for d in diffs):.1%}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--variants", default=",".join(occlusion.VARIANTS))
    a = ap.parse_args()
    rows = []
    for f in a.folders:
        rows += one(f, a.out, a.variants.split(","))
    if not rows:
        return
    with open(os.path.join(a.out, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print("\nvariant           legs  same   median dt  verdict")
    for tag in sorted({r["variant"] for r in rows}):
        rs = [r for r in rows if r["variant"] == tag]
        sh = sum(r["same"] for r in rs) / len(rs)
        md = statistics.median(r["d_best_time"] for r in rs)
        ok = sh >= SAME_SHARE_MIN and md <= MEDIAN_DIFF_MAX
        print(f"{tag:18s}{len(rs):5d}  {sh:5.1%}  {md:8.1%}  {'OK' if ok else 'no'}")


if __name__ == "__main__":
    main()
