#!/usr/bin/env python3
"""Made-up pairs of Livelox screenshots (the map with the course and the same view with the course switched off),
where the truth is known, and how well oroute.pair turns them into a map without course.

usage: python3 tools/snimek.py OUT.csv [--maps "pohora;petrvald;..."] [--zooms "0.75;1;1.5;2;3"] [--routes]
                                [--save DIR] [--quick]
       python3 tools/snimek.py --souhrn A.csv [B.csv ...]       (markdown table per zoom)
       python3 tools/snimek.py --spatne OUT_DIR                 (every wrong input: what oroute.pair says)

A screenshot is made from the two pictures of a pair of Livelox KMZ (with the course, without it: the same pixels),
without the Livelox title bar of the export: the picture is scaled by the zoom with plain bilinear sampling (what
the browser does when the map is zoomed in), laid on the grey background of the page, and the bar, the list of
runners and the buttons of Livelox are drawn over it. Both screenshots of a pair get the same view; a variant moves
the map of the second one by a few pixels (the bar and the buttons stay). Every step is an exact mapping, so it is
known where every pixel of the map lies on the screenshot.

The control positions the fit gets: as in tools/fotka.py (the real track at the official ORIS times for Pohora and
Petřvald, the true positions with 8 m of noise elsewhere).

For every pair: placed or not (and why), the error of the corners of the map and of the controls (metres), the
terrain classes read from the screenshot against those read from the KMZ, and with --routes the best routes of
bestroute.py from the screenshot against those from the KMZ.
"""
import argparse
import csv
import glob
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fotka  # noqa: E402

from oroute.kmzmap import GeoMap  # noqa: E402

ZOOMS = (0.75, 1.0, 1.5, 2.0, 3.0)
VIEW_MAX = (8000, 6400)          # the largest screenshot made (device pixels: 4000 x 3200 CSS px at DPR 2)
SHIFTS = (0, 5, 15)              # how far the map of the screenshot without the course is moved (px)

# what the page of Livelox looks like around the map (device pixels at DPR 2); two variants, since the real
# colours are not known here
UI = {
    "a": dict(bg=(229, 229, 229), bar=(38, 50, 66), bar_h=112, panel=620, slider=True),
    "b": dict(bg=(204, 204, 204), bar=(246, 246, 246), bar_h=96, panel=0, slider=False),
}
SWATCHES = [(230, 25, 75), (0, 130, 200), (60, 180, 75), (245, 130, 48), (145, 30, 180), (70, 240, 240)]

# the races with a run: (folder or data-extra name, slug, ORIS event id of the official times or None)
EXTRA = {"Grand prix Silesia - E2, H16B": ("gps-e2", 8699), "Grand prix Silesia - E3, H16B": ("gps-e3", 8700),
         "Grand prix Silesia - E4, H16B": ("gps-e4", 8701),
         "Mistrovtsví oblasti MSK ve sprintu, H16": ("msk-sprint", 9053),
         "Slezská zimní liga, HA": ("szl-zabreh", 8955),
         "Žebříček B-Morava, oblastní žebříček, H16B": ("zebricek-b", 8505)}


def slug(name):
    """A short name without spaces for a map of data-extra (or the folder of data/)."""
    if name in EXTRA:
        return EXTRA[name][0]
    keep = "".join(c if c.isalnum() else "-" for c in name.lower())
    return "-".join(p for p in keep.split("-") if p)[:24]


def sources(names=None):
    """dict(name, slug, course, maponly, golden, fit, official, dem) of every pair of KMZ with and without the course:
    the four races of data/ and the pairs of data-extra/parovani.json."""
    out = []
    for d in sorted(glob.glob(os.path.join(ROOT, "data", "*", "course.kmz"))):
        folder = os.path.dirname(d)
        name = os.path.basename(folder)
        golden = os.path.join(ROOT, "tests", "golden", name, "course.json")
        out.append(dict(name=name, slug=name, course=d, maponly=os.path.join(folder, "maponly.kmz"),
                        golden=golden if os.path.exists(golden) else None, fit=os.path.join(folder, "run.fit"),
                        official=None, dem=os.path.join(ROOT, "tests", "golden", name, "dem_cache.npz")))
    pj = os.path.join(ROOT, "data-extra", "parovani.json")
    if os.path.exists(pj):
        with open(pj, encoding="utf-8") as f:
            pairs = json.load(f)
        for name, r in pairs.items():
            s = slug(name)
            fit = os.path.join(ROOT, r["fit"]) if r.get("fit") and name in EXTRA else None
            off = os.path.join(ROOT, "kontrola", "repro-new", str(EXTRA[name][1]), "official.json") if name in EXTRA \
                else None
            out.append(dict(name=name, slug=s, course=os.path.join(ROOT, r["course"]),
                            maponly=os.path.join(ROOT, r["maponly"]), golden=None, fit=fit,
                            official=off if off and os.path.exists(off) else None,
                            dem=os.path.join(ROOT, "kontrola", "dem", s + ".npz")))
    return [s for s in out if not names or s["name"] in names or s["slug"] in names]


def load(src, rng):
    """fotka.load for the map with the course, and the paper of the map without it (the same pixels)."""
    m = fotka.load(dict(name=src["name"], kmz=src["course"], golden=src["golden"]), rng)
    gm = GeoMap.from_kmz(src["maponly"])
    m["paper_maponly"] = gm.image.crop((0, gm.header_px, gm.W, gm.H))
    if m["paper_maponly"].size != m["paper"].size:
        raise ValueError(f"{src['name']}: the two KMZ pictures differ in size")
    m["gm_course"] = GeoMap.from_kmz(src["course"])
    m["gm_maponly"] = gm
    return m


# --- the screenshot -------------------------------------------------------------------------------------------

def view(size, zoom, ui="a", view_max=VIEW_MAX, margin=0.06):
    """(width, height of the screenshot, ox, oy): a pixel of the paper at (x, y) is at (x * zoom + ox, y * zoom + oy)
    on it (continuous coordinates). The map is in the middle of the space right of the list of runners and below
    the bar, with a margin of the background around it; a map larger than the screen is cut by it."""
    u = UI[ui]
    W, H = size[0] * zoom, size[1] * zoom
    vw = int(min(view_max[0], u["panel"] + W * (1 + 2 * margin)))
    vh = int(min(view_max[1], u["bar_h"] + H * (1 + 2 * margin)))
    ox = u["panel"] + (vw - u["panel"] - W) / 2
    oy = u["bar_h"] + (vh - u["bar_h"] - H) / 2
    return vw, vh, round(ox), round(oy)


def scaled(paper, zoom, size, ox, oy, bg):
    """The paper scaled by zoom with plain bilinear sampling (no smoothing on the way down either, as a browser
    draws a zoomed image), at (ox, oy) on a background of size."""
    return paper.convert("RGB").transform(size, Image.AFFINE, (1 / zoom, 0, -ox / zoom, 0, 1 / zoom, -oy / zoom),
                                          resample=Image.BILINEAR, fillcolor=bg)


def draw_ui(im, ui="a"):
    """The bar, the list of runners, the zoom buttons and the time slider of Livelox over the screenshot."""
    u = UI[ui]
    W, H = im.size
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 0, W, u["bar_h"]], fill=u["bar"])
    ink = (230, 230, 230) if sum(u["bar"]) < 380 else (60, 60, 60)
    d.rectangle([24, 28, 200, u["bar_h"] - 28], fill=(240, 120, 30))              # the logo
    for i, w in enumerate((260, 180, 320, 140)):                                    # menu items
        x = 260 + sum((260, 180, 320, 140)[:i]) + 40 * i
        d.rectangle([x, u["bar_h"] // 2 - 10, x + w, u["bar_h"] // 2 + 10], fill=ink)
    if u["panel"]:
        d.rectangle([0, u["bar_h"], u["panel"], H], fill=(255, 255, 255))
        d.line([u["panel"], u["bar_h"], u["panel"], H], fill=(200, 200, 200), width=2)
        for i in range(min(40, (H - u["bar_h"]) // 90)):
            y = u["bar_h"] + 40 + 90 * i
            d.ellipse([30, y, 70, y + 40], fill=SWATCHES[i % len(SWATCHES)])
            d.rectangle([100, y + 8, 100 + 180 + (i * 53) % 220, y + 30], fill=(50, 50, 50))
            d.rectangle([480, y + 8, 580, y + 30], fill=(120, 120, 120))
    x1 = W - 40
    for i, sign in enumerate("+-"):                                                 # zoom buttons
        y = u["bar_h"] + 40 + 110 * i
        d.rounded_rectangle([x1 - 90, y, x1, y + 90], 14, fill=(255, 255, 255), outline=(170, 170, 170), width=3)
        d.rectangle([x1 - 65, y + 41, x1 - 25, y + 49], fill=(40, 40, 40))
        if sign == "+":
            d.rectangle([x1 - 49, y + 25, x1 - 41, y + 65], fill=(40, 40, 40))
    if u["slider"]:
        d.rectangle([u["panel"], H - 100, W, H], fill=(20, 20, 20, 170))
        d.rectangle([u["panel"] + 200, H - 54, W - 200, H - 46], fill=(255, 255, 255))
        d.ellipse([u["panel"] + 900, H - 74, u["panel"] + 948, H - 26], fill=(220, 40, 40))
    return im


def screens(m, zoom, ui="a", shift=(0, 0), view_max=VIEW_MAX):
    """(screenshot with the course, screenshot without it, truth): the same view of both, the map of the second
    moved by shift. truth: dict(zoom, ox, oy) of the first (paper px -> screenshot px), shift."""
    vw, vh, ox, oy = view(m["paper"].size, zoom, ui, view_max)
    bg = UI[ui]["bg"]
    a = draw_ui(scaled(m["paper"], zoom, (vw, vh), ox, oy, bg), ui)
    b = draw_ui(scaled(m["paper_maponly"], zoom, (vw, vh), ox + shift[0], oy + shift[1], bg), ui)
    return a, b, dict(zoom=zoom, ox=ox, oy=oy, shift=tuple(shift), ui=ui)


def paper_to_screen(truth, pts):
    p = np.asarray(pts, float)
    return p * truth["zoom"] + [truth["ox"], truth["oy"]]


def screen_to_paper(truth, pts):
    p = np.asarray(pts, float)
    return (p - [truth["ox"], truth["oy"]]) / truth["zoom"]


# --- how well it works -----------------------------------------------------------------------------------------

GROUPS = {"cesty": (8,), "zelena": (1, 2, 3, 6), "zakazane": (10, 11), "voda": (9,)}   # terrain classes (T.*)


def truth_classes(m):
    """The terrain classes of the map without course, read from its KMZ as the app reads it (cached on m)."""
    if "cls_truth" not in m:
        from oroute import terrain as T
        gm = m["gm_maponly"]
        m["cls_truth"] = T.classify(np.asarray(gm.image.convert("RGB")), gm.header_px,
                                    (gm.m_per_px_x + gm.m_per_px_y) / 2)
    return m["cls_truth"]


CORRIDOR_M = 250.0


def corridor(m, shape, step, hp):
    """Pixels (on the grid of every step-th pixel of the KMZ picture from its title bar down) within CORRIDOR_M of
    the lines between consecutive controls."""
    img = Image.new("L", (shape[1], shape[0]), 0)
    pts = [tuple(p / step) for p in m["ctrl_px"]]
    w = max(1, int(2 * CORRIDOR_M / m["m_per_px"] / step))
    d = ImageDraw.Draw(img)
    d.line(pts, fill=255, width=w, joint="curve")
    for x, y in pts:
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
    return np.asarray(img) > 0


def compare_classes(m, r, truth, cls, step=2):
    """The classes read from the screenshot (cls, on the picture kept by place_pair) against those from the KMZ,
    pixel by pixel through the exact mapping of the made-up screenshot (so that an error of the placing does not
    count here; it is measured on its own): on every step-th pixel of the KMZ picture that the picture kept covers.
    dict(changed = share of pixels with another class, and per group of GROUPS: share of that group's pixels in the
    KMZ that changed; paths also with one pixel of room either way)."""
    from scipy import ndimage as ndi
    t_all = truth_classes(m)
    hp = m["gm_maponly"].header_px
    vv, uu = np.mgrid[hp:t_all.shape[0]:step, 0:t_all.shape[1]:step]
    s_xy = paper_to_screen(truth, np.c_[uu.ravel() + 0.5, vv.ravel() - hp + 0.5])
    x0, y0, x1, y1 = r["box"]
    h, w = cls.shape
    u = np.floor((s_xy[:, 0] - x0) * w / (x1 - x0)).astype(int)
    v = np.floor((s_xy[:, 1] - y0) * h / (y1 - y0)).astype(int)
    ok = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    t = t_all[vv.ravel(), uu.ravel()]
    s = np.full(t.shape, 255, np.uint8)
    s[ok] = cls[v[ok], u[ok]]
    shape = vv.shape
    t, s, ok = t.reshape(shape), s.reshape(shape), ok.reshape(shape)
    out = dict(covered=float(ok.mean()), changed_all=float((t != s)[ok].mean()) if ok.any() else None)
    # where the routes go: within CORRIDOR_M of the lines between the controls (the margin of the sheet around the
    # drawn map, its title and its legend are read differently from a KMZ and from a screenshot, and do not matter)
    ok &= corridor(m, vv.shape, step, hp)
    out["changed"] = float((t != s)[ok].mean()) if ok.any() else None
    for name, cl in GROUPS.items():
        tg, sg = np.isin(t, cl) & ok, np.isin(s, cl) & ok
        out[name] = float((tg ^ sg).sum() / max(1, tg.sum())) if tg.sum() else None
        if name == "cesty":
            near = (tg & ~ndi.binary_dilation(sg)) | (sg & ~ndi.binary_dilation(tg))
            out["cesty_1px"] = float(near.sum() / max(1, tg.sum())) if tg.sum() else None
    return out


# --- best routes: bestroute.py with the map from the screenshot against the one with the KMZ -----------------------

def course_json(src):
    """The course of a race in lat/lon (analyze.py of the KMZ with the course): the golden one of data/, or the
    newest from the night checks of data-extra."""
    if src["golden"]:
        return src["golden"]
    for n in (3, 2, 1):
        p = os.path.join(ROOT, "kontrola", f"kolo-{n}", src["slug"], "course.json")
        if os.path.exists(p):
            return p
    return None


def prep_dem(gm, src, out):
    """dem_cache.npz for the box of gm in out, cut from the tiles cached for the race (so that bestroute.py does not
    download anything and both runs read the same heights). False when the cache does not cover it."""
    from oroute.dem import _tile_xy
    if not os.path.exists(src["dem"]):
        return False
    d = np.load(src["dem"])
    z = int(d["z"])
    x0, y0 = (int(v) for v in _tile_xy(gm.n, gm.w, z))
    x1, y1 = (int(v) for v in _tile_xy(gm.s, gm.e, z))
    tx0, ty0 = int(d["tx0"]), int(d["ty0"])
    ny, nx = d["h"].shape[0] // 256, d["h"].shape[1] // 256
    if x0 < tx0 or y0 < ty0 or x1 >= tx0 + nx or y1 >= ty0 + ny:
        return False
    h = d["h"][(y0 - ty0) * 256:(y1 - ty0 + 1) * 256, (x0 - tx0) * 256:(x1 - tx0 + 1) * 256]
    os.makedirs(out, exist_ok=True)
    np.savez_compressed(os.path.join(out, "dem_cache.npz"), h=h, tx0=x0, ty0=y0, z=z)
    return True


def kept_to_kmz(m, r, truth, u, v):
    """Pixels of the picture kept by place_pair -> pixels of the KMZ picture (with its title bar), exactly."""
    x0, y0, x1, y1 = r["box"]
    w, h = r["maponly"][1].size
    sx = x0 + np.asarray(u, float) * (x1 - x0) / w
    sy = y0 + np.asarray(v, float) * (y1 - y0) / h
    p = screen_to_paper(truth, np.c_[sx, sy])
    return p[:, 0], p[:, 1] + m["gm_maponly"].header_px


def kmz_to_kept(m, r, truth, u, v):
    x0, y0, x1, y1 = r["box"]
    w, h = r["maponly"][1].size
    s_ = paper_to_screen(truth, np.c_[np.asarray(u, float), np.asarray(v, float) - m["gm_maponly"].header_px])
    return (s_[:, 0] - x0) * w / (x1 - x0), (s_[:, 1] - y0) * h / (y1 - y0)


def course_on_kept(m, r, truth, src, out):
    """The course of the race as the app reads it from the screenshot with the course: every control where its
    circle is on the picture kept (the KMZ position moved there through the exact mapping), in lat/lon of the
    placing of the screenshot. Written to out/course.json; its path."""
    with open(course_json(src), encoding="utf-8") as f:
        c = json.load(f)
    g0, gk = m["gm_maponly"], r["maponly"][0]
    pts = [c["start"]] + c["controls"] + [c["finish"]]
    u, v = g0.latlon_to_px(np.array([p["lat"] for p in pts]), np.array([p["lon"] for p in pts]))
    ku, kv = kmz_to_kept(m, r, truth, u, v)
    la, lo = gk.px_to_latlon(ku, kv)
    for p, a_, b_ in zip(pts, np.atleast_1d(la), np.atleast_1d(lo)):
        p["lat"], p["lon"] = float(a_), float(b_)
    path = os.path.join(out, "course.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(c, f)
    return path


def bestroute(kmz, src, out, course=None):
    """best.json of bestroute.py for a map without course (the course, the run and the official times of src), or
    None when it failed (the log is in out/log.txt)."""
    import subprocess
    os.makedirs(out, exist_ok=True)
    cmd = [sys.executable, "bestroute.py", kmz, course or course_json(src), src["fit"], out, "--title", src["slug"],
           "--no-images"]
    if src["official"]:
        cmd += ["--official", src["official"]]
    with open(os.path.join(out, "log.txt"), "w", encoding="utf-8") as log:
        code = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
    path = os.path.join(out, "best.json")
    if code != 0 or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ref_routes(src, base):
    """best.json with the KMZ without course (computed once per map, kept in base/ref/SLUG)."""
    out = os.path.join(base, "ref", src["slug"])
    path = os.path.join(out, "best.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(src["dem"]):
        import shutil
        shutil.copyfile(src["dem"], os.path.join(out, "dem_cache.npz"))
    return bestroute(src["maponly"], src, out)


def forbidden_metres(m, route, ends_m=10.0, to_kmz=None):
    """The longest piece of a route (lat, lon points) through what the KMZ makes impassable (water, out of bounds,
    buildings: the classes read from it, a pixel off their edge), in metres, leaving out ends_m at both ends (a
    control may lie in such an area and is reached from its edge). to_kmz(lat, lon) -> KMZ pixels (u, v): for a
    route found on the picture kept, through its own placing and the exact mapping (so that the error of the placing
    does not count); default: the KMZ's own placing."""
    from scipy import ndimage as ndi

    from oroute.routing import IMPASSABLE
    if len(route) < 2:
        return 0.0
    gm = m["gm_maponly"]
    if "imp_truth" not in m:
        m["imp_truth"] = ndi.binary_erosion(np.isin(truth_classes(m), IMPASSABLE))
    imp = m["imp_truth"]
    ll = np.asarray(route, float)
    xy = np.c_[gm.to_xy(ll[:, 0], ll[:, 1])]
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    if L[-1] <= 2 * ends_m:
        return 0.0
    s = np.arange(ends_m, L[-1] - ends_m, 1.0)
    lat_, lon_ = np.interp(s, L, ll[:, 0]), np.interp(s, L, ll[:, 1])
    u, v = to_kmz(lat_, lon_) if to_kmz else gm.latlon_to_px(lat_, lon_)
    u, v = np.floor(np.asarray(u)).astype(int), np.floor(np.asarray(v)).astype(int)
    ok = (u >= 0) & (u < imp.shape[1]) & (v >= 0) & (v < imp.shape[0])
    inside = np.zeros(len(s), bool)
    inside[ok] = imp[v[ok], u[ok]]
    if not inside.any():
        return 0.0
    lab, _ = ndi.label(inside)
    return float(np.bincount(lab)[1:].max())


def compare_routes(m, ref, got, to_kmz=None):
    """Per leg: best time from the screenshot minus from the KMZ. dict(best_legs = legs compared, best_over5 = how
    many differ by more than 5 s, best_share5 = share within 5 s, best_forbidden = legs whose route from the screenshot
    runs at least 5 m through what the KMZ forbids, best_diffs = the differences in seconds)."""
    n = over = bad = 0
    diffs = []
    for lr, lg in zip(ref["legs"], got["legs"]):
        br, bg = lr.get("best"), lg.get("best")
        if not br or not bg or br.get("time") is None or bg.get("time") is None:
            continue
        n += 1
        d = bg["time"] - br["time"]
        diffs.append(round(d, 1))
        over += abs(d) > 5
        if forbidden_metres(m, lg.get("route") or [], to_kmz=to_kmz) >= 5:
            bad += 1
    return dict(best_legs=n, best_over5=over, best_share5=round(1 - over / n, 3) if n else None,
                best_forbidden=bad, best_diffs=" ".join(str(d) for d in diffs))


FIELDS = ["map", "zoom", "shift", "ui", "ok", "reason", "notes", "size", "res", "zoom_est", "out_res", "n", "controls",
          "rms", "corner_max", "ctrl_median", "ctrl_max", "shift_err", "accuracy", "reliable", "changed", "changed_all",
          "cesty", "cesty_1px", "zelena", "zakazane", "voda", "covered", "best_legs", "best_over5", "best_share5",
          "best_forbidden", "best_diffs", "secs"]


def run_one(src, m, zoom, shift=(0, 0), ui="a", terrain=True, save=None, out_res=None, routes=None):
    """One pair: placed by oroute.pair, checked against the truth. Returns (row for the CSV, result of place_pair or
    None)."""
    from oroute import pair
    from oroute import terrain as T
    t0 = time.time()
    a, b, truth = screens(m, zoom, ui, shift)
    if save:
        os.makedirs(save, exist_ok=True)
        stem = os.path.join(save, f"{src['slug']}-z{zoom:g}-s{shift[0]}")
        a.save(stem + "-trat.png")
        b.save(stem + "-bez.png")
    row = dict(map=src["slug"], zoom=zoom, shift=shift[0], ui=ui, size=f"{a.size[0]}x{a.size[1]}")
    try:
        r = pair.place_pair(a, b, m["controls"], m["lat0"], m["lon0"], out_res=out_res)
    except pair.PairError as e:
        row.update(ok=0, reason=e.code + (" " + json.dumps(e.data, default=str) if e.data else ""),
                   secs=round(time.time() - t0, 1))
        return row, None
    f = r["fit"]
    size = a.size
    corners = fotka.georef.to_metres(f, size, paper_to_screen(truth, m["corners_px"]))
    cerr = np.hypot(*(corners - m["corners_xy"]).T)
    cs = paper_to_screen(truth, m["ctrl_px"])
    vis = (cs[:, 0] >= 0) & (cs[:, 0] < size[0]) & (cs[:, 1] >= 0) & (cs[:, 1] < size[1])
    kerr = np.hypot(*(fotka.georef.to_metres(f, size, cs[vis]) - m["ctrl_xy"][vis]).T) if vis.any() else np.array([])
    shift_err = (math.hypot(r["shift"][0] - shift[0], r["shift"][1] - shift[1]) if r["shift"] is not None else None)
    row.update(ok=1, notes=" ".join(r["notes"]), res=round(r["res"], 3), zoom_est=round(r["zoom"], 2),
               out_res=round(r["out_res"], 3),
               n=r["work_fit"]["n"], controls=r["work_fit"]["controls"], rms=round(r["work_fit"]["rms"], 1),
               corner_max=round(float(cerr.max()), 1),
               ctrl_median=round(float(np.median(kerr)), 1) if len(kerr) else None,
               ctrl_max=round(float(kerr.max()), 1) if len(kerr) else None,
               shift_err=round(shift_err, 2) if shift_err is not None else None, accuracy=round(r["accuracy"]),
               reliable=int(r["reliable"]))
    if terrain and r["maponly"] is not None:
        gm, img = r["maponly"]
        cls = T.classify(np.asarray(img), 0, r["out_res"], blur_m=gm.blur_m)
        r["cls"] = cls
        cmpd = compare_classes(m, r, truth, cls)
        row.update({k: (round(v, 4) if isinstance(v, float) else v) for k, v in cmpd.items()})
    if routes and r["maponly"] is not None and src["fit"] and course_json(src):
        ref = ref_routes(src, routes)
        out = os.path.join(routes, "snimek", f"{src['slug']}-z{zoom:g}-s{shift[0]}")
        kmz = os.path.join(out, "maponly.kmz")
        os.makedirs(out, exist_ok=True)
        gm, img = r["maponly"]
        fotka.georef.write_kmz(kmz, img, gm, png=True)
        prep_dem(gm, src, out)
        got = bestroute(kmz, src, out, course_on_kept(m, r, truth, src, out))

        def to_kmz(la, lo):
            return kept_to_kmz(m, r, truth, *gm.latlon_to_px(la, lo))
        if ref and got:
            row.update(compare_routes(m, ref, got, to_kmz))
        else:
            row["best_legs"] = "chyba" if ref else "chyba ref"
    row["secs"] = round(time.time() - t0, 1)
    return row, r


# --- wrong inputs ---------------------------------------------------------------------------------------------

BAD = ["velikost", "posun15", "priblizeni", "otoceni", "trat-v-bez", "slaba-trat", "polopruhledna-trat", "prohozene",
       "postupy",
       "postupy-zelene",
       "jiny-zavod", "malo-priblizeny", "moc-malo-priblizeny"]


def runner_routes(im, seed=3, n=6, colours=((230, 25, 75), (0, 90, 255), (255, 140, 0), (0, 200, 60)), width=7):
    """Routes of other runners over a screenshot: random walks across the map in the colours Livelox gives them,
    drawn half see-through (as Livelox draws them)."""
    rng = np.random.default_rng(seed)
    W, H = im.size
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for i in range(n):
        x, y = rng.uniform(0.3 * W, 0.7 * W), rng.uniform(0.3 * H, 0.7 * H)
        pts = [(x, y)]
        a = rng.uniform(0, 2 * math.pi)
        for _ in range(240):
            a += rng.normal(0, 0.4)
            x = float(np.clip(x + 25 * math.cos(a), 0, W))
            y = float(np.clip(y + 25 * math.sin(a), 0, H))
            pts.append((x, y))
        d.line(pts, fill=colours[i % len(colours)] + (210,), width=width, joint="curve")
    return Image.alpha_composite(im.convert("RGBA"), over).convert("RGB")


FAINT = 0.13             # how opaque Livelox leaves a course switched off (measured on real screenshots: 0.12-0.15)


def faint(m, t, alpha=FAINT):
    """The screenshot without the course as some views of Livelox give it: the course still there, alpha opaque."""
    pc = np.asarray(m["paper"].convert("RGB"), np.float32)
    pm = np.asarray(m["paper_maponly"].convert("RGB"), np.float32)
    paper = Image.fromarray(np.clip(pm * (1 - alpha) + pc * alpha + 0.5, 0, 255).astype(np.uint8))
    vw, vh, _, _ = view(m["paper"].size, t["zoom"], t["ui"])
    return draw_ui(scaled(paper, t["zoom"], (vw, vh), t["ox"], t["oy"], UI[t["ui"]]["bg"]), t["ui"])


def bad_pair(kind, m, other=None):
    """(screenshot with the course, screenshot without, what the app should say) for one wrong input. other: load()
    of another map (for "jiny-zavod")."""
    if kind == "malo-priblizeny":
        a, b, _ = screens(m, 0.6)
        return a, b, "coarse"
    if kind == "moc-malo-priblizeny":
        a, b, _ = screens(m, 0.4)
        return a, b, "coarse_stop"
    a, b, t = screens(m, 1.0, shift=(15, 8) if kind == "posun15" else (0, 0))
    if kind == "velikost":
        return a, b.crop((0, 0, b.size[0] - 10, b.size[1])), "size"
    if kind == "posun15":
        return a, b, "shifted"
    if kind in ("priblizeni", "otoceni"):
        vw, vh = a.size
        bg = UI[t["ui"]]["bg"]
        z = 1.05 if kind == "priblizeni" else 1.0
        cx, cy = vw / 2, vh / 2
        ang = math.radians(2.0 if kind == "otoceni" else 0.0)
        # screen -> paper: undo the zoom and the rotation about the middle of the screen, then the view
        c, sn = math.cos(ang), math.sin(ang)
        A = np.array([[c, sn, cx - c * cx - sn * cy], [-sn, c, cy + sn * cx - c * cy], [0, 0, 1]]) \
            @ np.array([[1 / z, 0, cx - cx / z], [0, 1 / z, cy - cy / z], [0, 0, 1]])
        P = np.array([[1 / t["zoom"], 0, -t["ox"] / t["zoom"]], [0, 1 / t["zoom"], -t["oy"] / t["zoom"]], [0, 0, 1]])
        M = P @ A
        im = m["paper_maponly"].convert("RGB").transform((vw, vh), Image.AFFINE, tuple(M[:2].ravel()),
                                                           resample=Image.BILINEAR, fillcolor=bg)
        return a, draw_ui(im, t["ui"]), "zoom"
    if kind == "slaba-trat":
        return a, faint(m, t), "faint_course"
    if kind == "polopruhledna-trat":
        return a, faint(m, t, 0.35), "faint_course"
    if kind == "trat-v-bez":
        return a, a.copy(), "course_in_maponly"
    if kind == "prohozene":
        return b, a, "swapped"
    if kind == "postupy":
        return runner_routes(a), runner_routes(b), "routes"
    if kind == "postupy-zelene":
        return (runner_routes(a, colours=((40, 180, 70),)), runner_routes(b, colours=((40, 180, 70),)), "routes")
    if kind == "jiny-zavod":
        _, b2, _ = screens(other, 1.0)
        b2 = b2.resize(a.size, Image.BILINEAR) if b2.size != a.size else b2
        return a, b2, "unrelated"
    raise ValueError(kind)


def spatne(out_dir, names=None):
    """Every wrong input on each map: what oroute.pair says (one line each), thumbnails in out_dir."""
    from oroute import pair
    rng = np.random.default_rng(7)
    srcs = sources(names or ["pohora", "azymut-e5"])
    other = load(sources(["azymut-e4"])[0], rng)
    os.makedirs(out_dir, exist_ok=True)
    for src in srcs:
        m = load(src, rng)
        for kind in BAD:
            a, b, want = bad_pair(kind, m, other)
            t0 = time.time()
            try:
                r = pair.place_pair(a, b, m["controls"], m["lat0"], m["lon0"])
                got = "placed " + " ".join(r["notes"])
                ok = want in r["notes"]
            except pair.PairError as e:
                got = f"PairError {e.code} {json.dumps(e.data, default=str)}"
                ok = e.code == want
            print(f"{src['slug']:10} {kind:20} want {want:18} {'OK ' if ok else 'BAD'} {got} ({time.time() - t0:.0f} s)",
                  flush=True)
            th = b.copy()
            th.thumbnail((800, 800))
            th.save(os.path.join(out_dir, f"{src['slug']}-{kind}.jpg"), quality=80)


def _num(r, k):
    v = r.get(k)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct(x):
    return "–" if x is None else f"{100 * x:.1f} %".replace(".", ",")


def summary(path):
    """Markdown tables of one CSV: per zoom (pairs without a shift), and per map at zoom 2."""
    import statistics as st
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    med = lambda xs: st.median(xs) if xs else None
    out = ["| Zvětšení | usazeno | rohy: medián / nejvíc | štítek ≥ chyba rohů | terén u tratě změněn (medián) | cesty "
           "(±1 px) | zelená | zakázané | úseky do 5 s | úseky přes zákaz KMZ |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for z in sorted({r["zoom"] for r in rows}, key=float):
        R = [r for r in rows if r["zoom"] == z and r["shift"] == "0"]
        ok = [r for r in R if r["ok"] == "1"]
        corner = [_num(r, "corner_max") for r in ok]
        label = sum(1 for r in ok if _num(r, "accuracy") >= _num(r, "corner_max"))
        col = lambda k: med([x for x in (_num(r, k) for r in ok) if x is not None])
        legs = sum(int(_num(r, "best_legs")) for r in ok if _num(r, "best_legs") is not None)
        over = sum(int(_num(r, "best_over5") or 0) for r in ok if _num(r, "best_legs") is not None)
        bad = sum(int(_num(r, "best_forbidden") or 0) for r in ok if _num(r, "best_legs") is not None)
        out.append(f"| {z.replace('.', ',')} | {len(ok)} z {len(R)} | "
                   + (f"{med(corner):.0f} m / {max(corner):.0f} m" if corner else "–") + f" | {label} z {len(ok)} | "
                   f"{_pct(col('changed'))} | {_pct(col('cesty_1px'))} | {_pct(col('zelena'))} | {_pct(col('zakazane'))} | "
                   + (f"{legs - over} z {legs} ({100 * (legs - over) / legs:.0f} %)" if legs else "–") + f" | {bad} |")
    out += ["", "| Mapa | zvětšení 1 | 1,5 | 2 | 3 |", "|---|---|---|---|---|"]
    for name in dict.fromkeys(r["map"] for r in rows):
        cells = []
        for z in ("1.0", "1.5", "2.0", "3.0"):
            r = next((r for r in rows if r["map"] == name and r["zoom"] == z and r["shift"] == "0"), None)
            if r is None:
                cells.append("–")
            elif r["ok"] != "1":
                cells.append("neusazeno: " + r["reason"].split(" ")[0])
            else:
                legs = _num(r, "best_legs")
                cells.append(f"rohy {_num(r, 'corner_max'):.0f} m, terén {_pct(_num(r, 'changed'))}"
                             + (f", úseky {int(legs - (_num(r, 'best_over5') or 0))}/{int(legs)}, zákaz "
                                f"{int(_num(r, 'best_forbidden') or 0)}" if legs else ""))
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    shifted = [r for r in rows if r["shift"] not in ("0", "")]
    if shifted:
        good = sum(1 for r in shifted if r["ok"] == "1" and (_num(r, "shift_err") or 0) < 1)
        out += ["", f"Posun mapy mezi snímky o 5 a 15 px (zvětšení 1): vyrovnán do 1 px u {good} z {len(shifted)} "
                    "dvojic."]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?")
    ap.add_argument("--maps")
    ap.add_argument("--zooms")
    ap.add_argument("--shifts", help="shifts of the second screenshot, default 0;5;15 at zoom 1 and 0 otherwise")
    ap.add_argument("--ui", default="a")
    ap.add_argument("--save")
    ap.add_argument("--no-terrain", action="store_true")
    ap.add_argument("--native", action="store_true", help="keep the map at the resolution of the KMZ (an experiment)")
    ap.add_argument("--routes", help="also bestroute.py from the screenshot against the KMZ; results in this folder")
    ap.add_argument("--spatne", metavar="DIR", help="every wrong input: what oroute.pair says")
    ap.add_argument("--souhrn", nargs="+", metavar="CSV", help="markdown tables of finished sets")
    a = ap.parse_args()
    if a.souhrn:
        for p in a.souhrn:
            print(f"### {p}\n\n{summary(p)}\n")
        return
    names = a.maps.split(";") if a.maps else None
    if a.spatne:
        return spatne(a.spatne, names)
    zooms = [float(z) for z in a.zooms.split(";")] if a.zooms else ZOOMS
    rng = np.random.default_rng(7)
    rows = []
    w = None
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        fh = open(a.out, "w", newline="", encoding="utf-8")
        w = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        w.writeheader()
    for src in sources(names):
        m = load(src, rng)
        for z in zooms:
            shifts = [int(s) for s in a.shifts.split(";")] if a.shifts else (SHIFTS if z == 1.0 else (0,))
            for sh in shifts:
                try:
                    row, _ = run_one(src, m, z, (sh, sh // 2), a.ui, not a.no_terrain, a.save,
                                     out_res=m["m_per_px"] if a.native else None, routes=a.routes)
                except Exception as e:          # one pair failing must not stop the set; the log has the trace
                    import traceback
                    traceback.print_exc()
                    row = dict(map=src["slug"], zoom=z, shift=sh, ui=a.ui, ok=0, reason=f"vyjimka {e!r}"[:300])
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
                if w:
                    w.writerow(row)
                    fh.flush()
        m.pop("cls_truth", None)
        m.pop("imp_truth", None)


if __name__ == "__main__":
    main()
