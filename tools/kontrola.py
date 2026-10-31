#!/usr/bin/env python3
"""Pictures for checking the best routes of an analysed race by eye, one per leg.

usage: python3 tools/kontrola.py OUT_DIR MAPONLY.kmz COURSE.kmz [--proti OLD_OUT_DIR]

OUT_DIR is the output folder of run_race.py (analysis.json, best/best.json; best/relocate.json and
best/barriers.json when they are there). Written into OUT_DIR:

  useky/NN_A-B.jpg     three views of the leg at a scale where the symbols of the map can be told apart:
                         1. the map without course, the best route (blue), the track (red), the other routes
                            (light blue, when bestroute.py ran with --alternatives)
                         2. the same over the terrain classes the map was read into (terrain.render_classes)
                         3. the same over the map with what stops a route: impassable ground of
                            mapdata.obstacles (magenta), lines hard to cross (orange), areas out of bounds
                            (olive), buildings (dark red), water (blue), paths as they were read (black),
                            forbidden lines and areas of barriers.json (red, purple), crossings (green)
                       The views lie side by side or below each other, whichever shows the leg larger.
  useky/NN_A-B_dK.jpg  a long leg once more in pieces along the best route (map | obstacles), full size
  prehled.jpg          the map with the course, the course as it was read (start, controls, finish) and the
                       track: do the circles sit on the print, does the track sit on the paths
  useky/seznam.txt     one line per leg: times, lengths, metres on paths, what the track went through, backstop

--proti OLD_OUT_DIR  says which pictures are the same, byte for byte, as in an earlier run (those need no
                     second look) and which changed.
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import mapdata  # noqa: E402
from oroute import terrain as T  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402
from oroute.render import _font  # noqa: E402

VIEW_PX = 1400       # no picture is larger than this on its longer side (larger ones are shrunk when looked at)
PX_PER_M = 2.3       # the scale aimed at: a map of 1.33 m per pixel three times enlarged
MIN_PX_PER_M = 1.3   # a leg that comes out smaller than this is also cut into pieces along the route
PIECE_M = 260.0      # ... this long
PAD_M = 55.0
BLUE, RED, CYAN, PURPLE = (20, 70, 220), (220, 30, 40), (0, 170, 220), (170, 40, 220)


def mmss(s):
    s = int(round(s))
    return f"{'-' if s < 0 else ''}{abs(s) // 60}:{abs(s) % 60:02d}"


class Race:
    def __init__(self, out, maponly, course):
        self.out = out
        with open(os.path.join(out, "analysis.json"), encoding="utf-8") as f:
            self.A = json.load(f)
        with open(os.path.join(out, "best", "best.json"), encoding="utf-8") as f:
            self.B = {l["leg"]: l for l in json.load(f)["legs"]}
        self.R = {}
        if os.path.exists(os.path.join(out, "best", "relocate.json")):
            with open(os.path.join(out, "best", "relocate.json"), encoding="utf-8") as f:
                self.R = {c["leg"]: c for c in json.load(f)["controls"]}
        self.gm = gm = GeoMap.from_kmz(maponly)
        self.course_kmz = course
        self.mpp = gm.m_per_px_x
        self.rgb = np.asarray(gm.image)
        cls = mapdata.terrain(gm, maponly, os.path.join(out, "terrain_cache.npz"))
        self.obs = mapdata.obstacles(gm, cls, open_at=[tuple(float(a) for a in gm.latlon_to_px(c["lat"], c["lon"]))
                                                       for c in self.A["course"]])
        self.cls = self.obs["cls"]
        self.px = lambda pts: [tuple(float(a) for a in gm.latlon_to_px(p[0], p[1])) for p in pts]
        self.ctrl = self.px([(c["lat"], c["lon"]) for c in self.A["course"]])
        tr = self.A["track"]
        self.track = list(zip(*(np.asarray(a, float) for a in gm.latlon_to_px(np.array(tr["lat"]), np.array(tr["lon"])))))
        self.barriers = None
        if os.path.exists(os.path.join(out, "best", "barriers.json")):
            self.barriers = mapdata.barriers(os.path.join(out, "best", "barriers.json"), gm)
        self.layers = self._layers()

    def _layers(self):
        """The three pictures of the whole map the views are cut from."""
        terrain = T.render_classes(self.cls)
        pale = (self.rgb.astype(np.float32) * 0.45 + 255 * 0.55).astype(np.uint8)
        tint = lambda mask, col, a: pale.__setitem__(mask, (pale[mask] * (1 - a) + np.array(col) * a).astype(np.uint8))
        tint(self.cls == T.PATH, (0, 0, 0), 0.75)
        tint(self.cls == T.OOB, (140, 135, 20), 0.6)
        tint(self.cls == T.WATER, (0, 90, 200), 0.7)
        tint(self.cls == T.BUILDING, (120, 0, 0), 0.8)
        if self.obs.get("hard") is not None and self.obs["hard"].any():
            from scipy.ndimage import binary_dilation
            tint(binary_dilation(self.obs["hard"], iterations=max(1, int(round(1.5 / self.mpp)))), (255, 110, 0), 0.9)
        if self.obs.get("outline") is not None:
            tint(self.obs["outline"], (255, 200, 0), 0.9)
        tint(self.obs["blocked"], (230, 0, 200), 0.55)
        if self.obs.get("climb") is not None and self.obs["climb"].any():
            # the passable walls of a sprint map: slow to climb over
            tint(self.obs["climb"], (0, 150, 150), 0.9)
        im = Image.fromarray(pale)
        if self.barriers:
            d = ImageDraw.Draw(im, "RGBA")
            for poly in self.barriers["areas"]:
                if len(poly) >= 3:
                    d.polygon(poly, fill=PURPLE + (110,), outline=PURPLE + (255,))
            for line in self.barriers["forbidden"]:
                d.line(line, fill=(255, 0, 0, 230), width=max(2, int(4 / self.mpp)))
            for line in self.barriers["hard"]:
                d.line(line, fill=(255, 130, 0, 230), width=max(2, int(4 / self.mpp)))
            r = 14.0 / self.mpp
            for u, v in self.barriers["crossings"]:
                d.ellipse([u - r, v - r, u + r, v + r], outline=(0, 160, 60, 255), width=2)
        return [self.rgb, terrain, np.asarray(im)]

    def lines(self, k):
        b, leg = self.B[k], self.A["legs"][k - 1]
        return dict(best=self.px(b["route"]), alts=[self.px(a["route"]) for a in b.get("alternatives") or []],
                    track=[] if leg.get("no_data") else self.track[leg["a"]:leg["b"] + 1])

    def view(self, layer, box, scale, L, k, sharp=False):
        """One layer cut to box = (u0, v0, u1, v1) and enlarged, with the lines of leg k drawn over it."""
        u0, v0, u1, v1 = box
        cut = Image.fromarray(layer[v0:v1, u0:u1])
        im = cut.resize((max(1, int((u1 - u0) * scale)), max(1, int((v1 - v0) * scale))),
                        Image.NEAREST if sharp else Image.LANCZOS)
        d = ImageDraw.Draw(im, "RGBA")
        P = lambda pts: [((u - u0) * scale, (v - v0) * scale) for u, v in pts]
        for a in L["alts"]:
            d.line(P(a), fill=(255, 255, 255, 200), width=5, joint="curve")
            d.line(P(a), fill=CYAN + (230,), width=2, joint="curve")
        if len(L["best"]) > 1:
            d.line(P(L["best"]), fill=(255, 255, 255, 215), width=7, joint="curve")
            d.line(P(L["best"]), fill=BLUE + (240,), width=3, joint="curve")
        if len(L["track"]) > 1:
            d.line(P(L["track"]), fill=RED + (230,), width=2, joint="curve")
        r = 24.0 / self.mpp * scale
        f = _font(18)
        for n in (k - 1, k):
            (x, y), = P([self.ctrl[n]])
            d.ellipse([x - r, y - r, x + r, y + r], outline=PURPLE + (255,), width=2)
            name = "S" if n == 0 else "F" if n == len(self.ctrl) - 1 else str(n)
            d.text((x + r * 0.75, y - r - 16), name, fill=PURPLE + (255,), font=f, stroke_width=2,
                   stroke_fill=(255, 255, 255, 255))
        return im

    def box(self, pts, pad_m=PAD_M):
        pad = pad_m / self.mpp
        us, vs = [p[0] for p in pts], [p[1] for p in pts]
        return (int(max(min(us) - pad, 0)), int(max(min(vs) - pad, self.gm.header_px)),
                int(min(max(us) + pad, self.gm.W)), int(min(max(vs) + pad, self.gm.H)))

    def say(self, k):
        b, leg = self.B[k], self.A["legs"][k - 1]
        path = b["best"]["mix"].get("path/road", 0.0)
        text = (f"{b['name']}: actual {mmss(b['actual'])}, best {mmss(b['best']['time'])} {b['best']['dist']:.0f} m "
                f"(path {path:.0f} m), track {mmss(b['yours']['time'])} {b['yours']['dist']:.0f} m")
        if leg.get("no_data"):
            text += ", NO DATA"
        if b.get("no_route"):
            text += ", NO ROUTE (straight line)"
        attack = (self.R.get(k) or {}).get("attack")
        if attack:
            text += f"; attack {attack['kind']} {attack['dist']:.0f} m"
        for a in b.get("alternatives") or []:
            text += f", alt {mmss(a['time'])}"
        for c in b.get("crossed") or []:
            text += f", track through {c['what']}"
        stop = (self.R.get(k) or {}).get("beyond")
        if stop:
            text += "; beyond " + ", ".join(f"{p['side']} {p['kind']} {p['dist']:.0f} m" for p in stop["parts"])
        return text

    def leg(self, k, folder):
        """Write the picture(s) of leg k; returns their file names."""
        L = self.lines(k)
        pts = L["best"] + L["track"] + [p for a in L["alts"] for p in a] + [self.ctrl[k - 1], self.ctrl[k]]
        u0, v0, u1, v1 = box = self.box(pts)
        w, h = u1 - u0, v1 - v0
        top = min(PX_PER_M * self.mpp, 3.0)
        # three views side by side or below each other: whichever shows the leg larger within VIEW_PX
        across = min(top, VIEW_PX / (3 * w + 8), (VIEW_PX - 30) / h)
        down = min(top, VIEW_PX / w, (VIEW_PX - 30) / (3 * h + 8))
        scale = max(across, down)
        views = [self.view(layer, box, scale, L, k, sharp=(n == 1)) for n, layer in enumerate(self.layers)]
        vw, vh = views[0].size
        sheet = Image.new("RGB", (3 * vw + 8, vh + 30) if across >= down else (vw, 3 * vh + 8 + 30), (255, 255, 255))
        for n, v in enumerate(views):
            sheet.paste(v, (n * (vw + 4), 30) if across >= down else (0, 30 + n * (vh + 4)))
        ImageDraw.Draw(sheet).text((6, 4), self.say(k)[:int(sheet.size[0] / 9.5)], fill=(0, 0, 0), font=_font(17))
        name = f"{k:02d}_{self.B[k]['name']}"
        sheet.save(os.path.join(folder, name + ".jpg"), quality=88)
        out = [name + ".jpg"]
        if scale / self.mpp < MIN_PX_PER_M and len(L["best"]) > 1:
            # a long leg: pieces along the best route, the map and the obstacles side by side at full size
            best = np.asarray(L["best"])
            along = np.r_[0, np.cumsum(np.hypot(*np.diff(best, axis=0).T))] * self.mpp
            n = int(np.ceil(along[-1] / PIECE_M))
            for i in range(n):
                part = best[(along >= i * along[-1] / n - 20) & (along <= (i + 1) * along[-1] / n + 20)]
                if len(part) < 2:
                    continue
                pb = self.box([tuple(p) for p in part], 70.0)
                s = min(top, (VIEW_PX - 4) / 2 / (pb[2] - pb[0]), VIEW_PX / (pb[3] - pb[1]))
                a, c = self.view(self.layers[0], pb, s, L, k), self.view(self.layers[2], pb, s, L, k)
                both = Image.new("RGB", (a.size[0] * 2 + 4, a.size[1]), (255, 255, 255))
                both.paste(a, (0, 0))
                both.paste(c, (a.size[0] + 4, 0))
                both.save(os.path.join(folder, f"{name}_d{i + 1}.jpg"), quality=88)
                out.append(f"{name}_d{i + 1}.jpg")
        return out

    def overview(self, path):
        """The map with the course, what was read as the course, and the track."""
        gm = GeoMap.from_kmz(self.course_kmz)
        s = min(1.0, VIEW_PX / max(gm.W, gm.H))
        im = gm.image.resize((int(gm.W * s), int(gm.H * s)), Image.LANCZOS)
        d = ImageDraw.Draw(im, "RGBA")
        tr = self.A["track"]
        u, v = gm.latlon_to_px(np.array(tr["lat"]), np.array(tr["lon"]))
        d.line(list(zip(u * s, v * s)), fill=RED + (200,), width=2)
        f = _font(16)
        for n, c in enumerate(self.A["course"]):
            x, y = (float(a) * s for a in gm.latlon_to_px(c["lat"], c["lon"]))
            d.line([x - 9, y, x + 9, y], fill=(0, 140, 0, 255), width=2)
            d.line([x, y - 9, x, y + 9], fill=(0, 140, 0, 255), width=2)
            name = "S" if n == 0 else "F" if n == len(self.A["course"]) - 1 else str(n)
            d.text((x + 10, y + 6), name, fill=(0, 110, 0, 255), font=f, stroke_width=2, stroke_fill=(255, 255, 255, 255))
        im.save(path, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("maponly")
    ap.add_argument("course")
    ap.add_argument("--proti", metavar="OLD_OUT_DIR", help="an earlier run to compare the pictures with")
    a = ap.parse_args()
    race = Race(a.out, a.maponly, a.course)
    folder = os.path.join(a.out, "useky")
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        os.remove(os.path.join(folder, old))
    files, said = [], []
    for k in sorted(race.B):
        files += race.leg(k, folder)
        said.append(race.say(k))
    with open(os.path.join(folder, "seznam.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(said) + "\n")
    race.overview(os.path.join(a.out, "prehled.jpg"))
    print("\n".join(said))
    print(f"{len(files)} pictures of {len(race.B)} legs in {folder}; enclosures: {len(race.obs['pens'])}, "
          f"fences: {len(race.obs.get('fences') or [])}")
    if a.proti:
        digest = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
        same = [n for n in files if digest(os.path.join(folder, n)) == digest(os.path.join(a.proti, "useky", n))]
        changed = [n for n in files if n not in same]
        with open(os.path.join(folder, "zmeny.txt"), "w", encoding="utf-8") as f:
            f.write("changed:\n" + "\n".join(changed) + "\nsame:\n" + "\n".join(same) + "\n")
        print(f"against {a.proti}: {len(same)} pictures the same, {len(changed)} changed: " + " ".join(changed))


if __name__ == "__main__":
    main()
