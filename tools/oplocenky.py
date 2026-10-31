#!/usr/bin/env python3
"""Where do the routes of a race go through fenced ground or over a fence? A check by eye of what
oroute/relocate.enclosures and fences read, against every line the analysis draws.

usage: python3 tools/oplocenky.py OUT_DIR MAPONLY.kmz [--out DIR] [--min-m 5]

OUT_DIR  output folder of run_race.py (analysis.json, best/best.json with --alternatives and --generic) and,
         when there, ztraceny/rady/rady.json of oroute.lost (the advice of "Ztratil jsem se u kontroly").

For every leg and every line of it (best route, each alternative, the average runner, the advice of the lost
page) it finds where the line runs at least --min-m metres inside ground that black closes in, whether or not
enclosures() took it as an enclosure, and why it did not ("plocha", "tvar", "okraj", "oob", "podil_cerne",
"paleta", "zoubky N"), or where it crosses a fence that closes nothing in (hard, 90 s), or fenced ground
opened because a control lies in it. Writes DIR/oplocenky.txt and one picture per find: the map, and the same
with the ground (magenta when it is an enclosure, orange when not) and the line.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import mapdata, relocate  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402
from oroute.render import _font  # noqa: E402


def lines_of(out, gm):
    """[(leg name, what, [(u, v), ...])] of every line drawn for the race."""
    px = lambda pts: [tuple(float(a) for a in gm.latlon_to_px(p[0], p[1])) for p in pts]
    with open(os.path.join(out, "best", "best.json"), encoding="utf-8") as f:
        B = json.load(f)
    found = []
    for leg in B["legs"]:
        if leg.get("route"):
            found.append((leg["name"], "nejlepší", px(leg["route"])))
        for n, a in enumerate(leg.get("alternatives") or [], 1):
            if a.get("route"):
                found.append((leg["name"], f"možnost {n + 1}", px(a["route"])))
        g = leg.get("generic") or {}
        if g.get("route"):
            found.append((leg["name"], "průměrný běžec", px(g["route"])))
    rj = os.path.join(out, "ztraceny", "rady", "rady.json")
    if os.path.exists(rj):
        with open(rj, encoding="utf-8") as f:
            for item in json.load(f):
                for what, a in [("ztracený", item["live"])] + [(f"ztracený zpět {i + 1}", m["advice"])
                                                                for i, m in enumerate(item.get("back") or [])]:
                    if a and a.get("route") and len(a["route"]) > 1:
                        found.append((f"kontrola {item['k']}", what, px(a["route"])))
    return found


def samples(line, step=0.5):
    """Points along a polyline of pixels every `step` pixels."""
    out = []
    for (u0, v0), (u1, v1) in zip(line[:-1], line[1:]):
        n = max(1, int(np.hypot(u1 - u0, v1 - v0) / step))
        t = np.arange(n) / n
        out.append(np.c_[u0 + t * (u1 - u0), v0 + t * (v1 - v0)])
    out.append(np.array([line[-1]]))
    return np.vstack(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("maponly")
    ap.add_argument("--out", dest="dest")
    ap.add_argument("--min-m", type=float, default=5.0)
    args = ap.parse_args()
    dest = args.dest or os.path.join(args.out, "oplocenky")
    os.makedirs(dest, exist_ok=True)
    gm = GeoMap.from_kmz(args.maponly)
    mpp = gm.m_per_px_x
    rgb = np.asarray(gm.image)
    H, W = rgb.shape[:2]
    cls = mapdata.terrain(gm, args.maponly, os.path.join(args.out, "terrain_cache.npz"))
    with open(os.path.join(args.out, "analysis.json"), encoding="utf-8") as f:
        A = json.load(f)
    ctrl = [tuple(float(a) for a in gm.latlon_to_px(c["lat"], c["lon"])) for c in A["course"]]
    why = {}
    relocate.enclosures(rgb, cls, mpp, grow_m=relocate.ROUTE_FENCE_M, why=why)
    obs = mapdata.obstacles(gm, cls, open_at=ctrl)
    shut = mapdata.obstacles(gm, cls)["blocked"]       # (without the controls: what was opened)
    holes = why["holes"]
    reason = {d["i"]: d for d in why["list"]}
    inner = ndi.binary_erosion(holes > 0, iterations=max(1, int(round(2.0 / mpp))))
    lab = np.where(inner, holes, 0)
    hard = ndi.binary_dilation(obs["hard"], iterations=1)
    report, n = [], 0
    for leg, what, line in lines_of(args.out, gm):
        if len(line) < 2:
            continue
        p = samples(line)
        u = np.clip(p[:, 0].round().astype(int), 0, W - 1)
        v = np.clip(p[:, 1].round().astype(int), 0, H - 1)
        ids, counts = np.unique(lab[v, u], return_counts=True)
        hits = []
        for i, c in zip(ids, counts):
            m = c * 0.5 * mpp
            if i == 0 or m < args.min_m or i not in reason:
                continue
            d = reason[i]
            k = d["reason"]
            if k == "ok":
                k = "ok, ale otevřená (kontrola)" if not obs["blocked"][int(d["v"]), int(d["u"])] and \
                    shut[int(d["v"]), int(d["u"])] else "ok (neprůchozí)"
            hits.append((f"plocha {d['area']:.0f} m2 u ({d['u']:.0f}, {d['v']:.0f}): {m:.0f} m uvnitř; {k}", i))
        on_hard = hard[v, u]
        crossings = int((on_hard[1:] & ~on_hard[:-1]).sum())
        if crossings:
            k = np.nonzero(on_hard)[0][0]
            hits.append((f"přes plot (hard, 90 s) {crossings}x, první u ({u[k]}, {v[k]})", None))
        for text, i in hits:
            n += 1
            report.append(f"{leg} {what}: {text}  [{n:03d}.jpg]")
            _picture(dest, n, rgb, holes == i if i else hard, line, mpp, reason.get(i, {}).get("reason") == "ok",
                     f"{leg} {what}: {text}")
    with open(os.path.join(dest, "oplocenky.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
        f.write(f"\nvšechny uzavřené plochy nad 50 m2 a proč (ne)jsou oplocenka ({len(why['list'])}):\n")
        for d in sorted(why["list"], key=lambda d: -d["area"]):
            f.write(f"  ({d['u']:.0f}, {d['v']:.0f}) {d['area']:.0f} m2: {d['reason']}\n")
    print("\n".join(report) or "nic")
    print(f"{n} nálezů, obrázky v {dest}")
    # every ground closed in by black of 100 m2 or more with a black ring, on contact sheets with the reason
    big = [d for d in why["list"] if d["area"] >= 100 and not d["reason"].startswith(("okraj", "oob"))
           and (d["reason"].startswith("ok") or not d["reason"].startswith("podil_cerne")
                or float(d["reason"].split()[1]) >= 0.4)]
    if os.environ.get("JEN_PRIJATE"):
        big = [d for d in big if d["reason"].startswith("ok")]
    if os.environ.get("JEN_ODMITNUTE"):
        big = [d for d in big if not d["reason"].startswith("ok")]
    _sheets(dest, rgb, holes, big, mpp)


def _sheets(dest, rgb, holes, found, mpp, tile=300, cols=4, rows=3):
    H, W = holes.shape
    objs = ndi.find_objects(holes)
    for s in range(0, len(found), cols * rows):
        sheet = Image.new("RGB", (cols * tile * 2 + (cols - 1) * 12, rows * (tile + 20)), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for j, f in enumerate(found[s:s + cols * rows]):
            sl = objs[f["i"] - 1]
            pad = int(15 / mpp)
            u0, v0 = max(sl[1].start - pad, 0), max(sl[0].start - pad, 0)
            u1, v1 = min(sl[1].stop + pad, W), min(sl[0].stop + pad, H)
            side = max(u1 - u0, v1 - v0)
            u1, v1 = min(u0 + side, W), min(v0 + side, H)
            cut = rgb[v0:v1, u0:u1]
            shown = cut.copy()
            m = holes[v0:v1, u0:u1] == f["i"]
            col = (230, 0, 200) if f["reason"].startswith("ok") else (255, 130, 0)
            shown[m] = (shown[m] * 0.4 + np.array(col) * 0.6).astype(np.uint8)
            fit = lambda a: Image.fromarray(a).resize((tile, tile), Image.LANCZOS)
            x, y = (j % cols) * (tile * 2 + 12), (j // cols) * (tile + 20)
            sheet.paste(fit(cut), (x, y + 20))
            sheet.paste(fit(shown), (x + tile, y + 20))
            d.text((x + 2, y + 3), f"({f['u']:.0f},{f['v']:.0f}) {f['area']:.0f} m2: {f['reason']}", fill=(0, 0, 0),
                   font=_font(12))
        sheet.save(os.path.join(dest, f"plochy_{s // (cols * rows) + 1}.jpg"), quality=85)


def _picture(dest, n, rgb, mask, line, mpp, ok, title):
    H, W = mask.shape
    vs, us = np.nonzero(mask)
    lu, lv = np.array([p[0] for p in line]), np.array([p[1] for p in line])
    if len(us):
        cu, cv = us.mean(), vs.mean()
        half = max(us.max() - us.min(), vs.max() - vs.min()) / 2 + 40 / mpp
    else:
        cu, cv, half = lu.mean(), lv.mean(), 80 / mpp
    half = min(half, 250 / mpp)
    u0, v0 = int(max(cu - half, 0)), int(max(cv - half, 0))
    u1, v1 = int(min(cu + half, W)), int(min(cv + half, H))
    cut = rgb[v0:v1, u0:u1]
    shown = cut.copy()
    m = mask[v0:v1, u0:u1]
    shown[m] = (shown[m] * 0.35 + np.array((230, 0, 200) if ok else (255, 130, 0)) * 0.65).astype(np.uint8)
    s = 450.0 / max(u1 - u0, v1 - v0)
    size = (max(1, int((u1 - u0) * s)), max(1, int((v1 - v0) * s)))
    a = Image.fromarray(cut).resize(size, Image.LANCZOS)
    b = Image.fromarray(shown).resize(size, Image.LANCZOS)
    for im in (a, b):
        d = ImageDraw.Draw(im, "RGBA")
        d.line([((x - u0) * s, (y - v0) * s) for x, y in line], fill=(20, 70, 220, 200), width=3)
    out = Image.new("RGB", (size[0] * 2 + 10, size[1] + 26), (255, 255, 255))
    out.paste(a, (0, 26))
    out.paste(b, (size[0] + 10, 26))
    ImageDraw.Draw(out).text((4, 4), title[:150], fill=(0, 0, 0), font=_font(13))
    out.save(os.path.join(dest, f"{n:03d}.jpg"), quality=88)


if __name__ == "__main__":
    main()
