#!/usr/bin/env python3
"""How often the best route of the runner differs from an average runner's (bestroute.py --generic), over the
output folders of analysed races, and pictures of the most interesting legs.

usage: python3 tools/pro_tebe.py OUT_DIR [OUT_DIR ...] [--pictures DIR] [--top 5] [--md FILE]

OUT_DIR    output folder of run_race.py --generic (analysis.json, best/best.json, race.json with the maps)
--pictures where the JPEGs of the --top legs go (at most 1600 px a side): the map without course, your best
           route (blue), the average runner's (dark grey, dotted), your track (red), the controls (purple)
--md       the tables as Markdown (default: printed)

The most interesting legs are the ones where the average route costs the runner the most (gain), at most two
from one race and each reason (uphill, downhill, a terrain) at most twice while others are left.
"""
import argparse
import json
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import generic  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402

MAX_PX = 1600
PAD_M = 60.0
BLUE, GREY, RED, PURPLE = (20, 70, 220), (45, 45, 55), (220, 30, 40), (170, 40, 220)
REASON_CS = {"up": "stoupání", "down": "klesání"}


def mmss(s):
    return generic.mmss(s)


def load(folder):
    read = lambda *p: json.load(open(os.path.join(folder, *p), encoding="utf-8"))
    info = read("race.json") if os.path.exists(os.path.join(folder, "race.json")) else {}
    best, A = read("best", "best.json"), read("analysis.json")
    return dict(folder=folder, slug=info.get("slug") or os.path.basename(folder.rstrip("/")),
                title=info.get("title") or best.get("title"), info=info, best=best, A=A)


def reason_text(r, sprint=False):
    if not r:
        return ""
    name = REASON_CS.get(r["kind"])
    if name is None:
        c = generic.T.NAMES.index(r["cls"]) if r["cls"] in generic.T.NAMES else None
        name = generic.words("cs", sprint)[2].get(c, r["cls"]).split(" ", 1)[-1]
    return f"{name} ({'+' if r['pct'] > 0 else '−'}{abs(r['pct']) * 100:.0f} %)"


def rows_of(race):
    out = []
    for l in race["best"]["legs"]:
        g = l.get("generic")
        if g is None:
            continue
        yours = g["differs"] and g["reason"] is not None and g["gain"] >= generic.LEVEL_S
        out.append(dict(race=race, leg=l, g=g, yours=yours, level=g["differs"] and not yours,
                        kind=(g["reason"] or {}).get("kind") if yours else None,
                        key=((g["reason"] or {}).get("kind"), (g["reason"] or {}).get("cls")) if yours else None))
    return out


def pick(rows, top):
    """The most interesting legs: largest gain, at most two per race and per reason while there are others."""
    cand = sorted((r for r in rows if r["yours"]), key=lambda r: -r["g"]["gain"])
    chosen, races, keys = [], Counter(), Counter()
    for limit in (1, 2, 99):
        for r in cand:
            if len(chosen) >= top:
                break
            if r in chosen or races[r["race"]["slug"]] >= min(limit, 2) or keys[r["key"]] >= limit:
                continue
            chosen.append(r)
            races[r["race"]["slug"]] += 1
            keys[r["key"]] += 1
    return chosen


def picture(r, path):
    race, l, g = r["race"], r["leg"], r["g"]
    gm = GeoMap.from_kmz(os.path.join(HERE, race["info"]["maponly"]))
    A = race["A"]
    leg = next(x for x in A["legs"] if x["leg"] == l["leg"])
    px = lambda ll: [tuple(float(a) for a in gm.latlon_to_px(la, lo)) for la, lo in ll]
    mine, avg = px(l["route"]), px(g["route"])
    tr = A["track"]
    trk = px(list(zip(tr["lat"][leg["a"]:leg["b"] + 1], tr["lon"][leg["a"]:leg["b"] + 1]))) if not l.get("no_data") else []
    ctrl = px([(c["lat"], c["lon"]) for c in A["course"]])
    pts = mine + avg + trk
    pad = PAD_M / gm.m_per_px_x
    box = (int(max(min(p[0] for p in pts) - pad, 0)), int(max(min(p[1] for p in pts) - pad, gm.header_px)),
           int(min(max(p[0] for p in pts) + pad, gm.W)), int(min(max(p[1] for p in pts) + pad, gm.H)))
    w, h = box[2] - box[0], box[3] - box[1]
    s = min(MAX_PX / max(w, h), 3.0)
    im = gm.image.crop(box).resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.25)
    d = ImageDraw.Draw(im, "RGBA")
    at = lambda line: [((u - box[0]) * s, (v - box[1]) * s) for u, v in line]
    lw = max(3, int(round(2.2 * s)))
    if len(trk) > 1:
        d.line(at(trk), fill=RED + (200,), width=lw, joint="curve")
    d.line(at(mine), fill=(255, 255, 255, 220), width=lw * 2 + 2, joint="curve")
    d.line(at(mine), fill=BLUE + (240,), width=lw + 1, joint="curve")
    a = at(avg)
    for k in range(0, len(a) - 1, 2):                     # dotted: every other piece
        d.line([a[k], a[k + 1]], fill=GREY + (240,), width=lw + 1)
    for u, v in at(ctrl):
        R = 22 / gm.m_per_px_x * s * 1.33
        d.ellipse([u - R, v - R, u + R, v + R], outline=PURPLE + (255,), width=max(2, lw // 2 + 1))
    # no title in the picture (the container has no font with Czech letters): the Markdown says what it shows
    im.convert("RGB").save(path, "JPEG", quality=85)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dirs", nargs="+")
    ap.add_argument("--pictures")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--md")
    a = ap.parse_args()
    races = [load(f) for f in a.out_dirs if os.path.exists(os.path.join(f, "best", "best.json"))]
    rows = [r for race in races for r in rows_of(race)]
    L = ["| Závod | Úseků | Liší se a pro tebe rychlejší | Liší se, ale skoro stejně | Důvody |", "|---|---|---|---|---|"]
    for race in races:
        rr = [r for r in rows if r["race"] is race]
        why = Counter(reason_text(r["g"]["reason"], r["g"].get("sprint")).split(" (")[0] for r in rr if r["yours"])
        L.append(f"| {race['title']} | {len(rr)} | {sum(r['yours'] for r in rr)} | {sum(r['level'] for r in rr)} | "
                 + ", ".join(f"{k} {n}×" for k, n in why.most_common()) + " |")
    why = Counter(reason_text(r["g"]["reason"], r["g"].get("sprint")).split(" (")[0] for r in rows if r["yours"])
    L.append(f"| **celkem** | **{len(rows)}** | **{sum(r['yours'] for r in rows)}** | **{sum(r['level'] for r in rows)}** | "
             + ", ".join(f"{k} {n}×" for k, n in why.most_common()) + " |")
    L += ["", "| Závod | Úsek | Tvůj nejlepší | Průměrný běžec (tvým tempem) | Rozdíl | Od sebe | Důvod | Věta |",
          "|---|---|---|---|---|---|---|---|"]
    for r in sorted((r for r in rows if r["g"]["differs"]), key=lambda r: -r["g"]["gain"]):
        g = r["g"]
        L.append(f"| {r['race']['title']} | {r['leg']['name']} | {mmss(g['time'] - g['gain'])} | {mmss(g['time'])} | "
                 f"{g['gain']:+.0f} s | {g['apart'] * 100:.0f} % | {reason_text(g['reason'], g.get('sprint'))} | "
                 f"{g['text_cs']} |")
    chosen = pick(rows, a.top)
    if a.pictures:
        os.makedirs(a.pictures, exist_ok=True)
        L += ["", "Vybrané úseky:", ""]
        for k, r in enumerate(chosen, 1):
            name = f"{k}_{r['race']['slug']}_{r['leg']['name']}.jpg"
            picture(r, os.path.join(a.pictures, name))
            L.append(f"{k}. {r['race']['title']}, {r['leg']['name']}: `{name}`. {r['g']['text_cs']}")
    text = "\n".join(L) + "\n"
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
