#!/usr/bin/env python3
"""Made-up phone photos of a map with the course, where the truth is known, and how well oroute.georef places
them.

usage: python3 tools/fotka.py OUT.csv [--maps "pohora;petrvald;..."] [--only NAME] [--save DIR] [--quick]
       python3 tools/fotka.py --souhrn A.csv [B.csv ...]     (markdown table per case, side by side)
       python3 tools/fotka.py --analyza OUT_DIR               (analyze.py: Livelox KMZ against a photo of it)
       python3 tools/fotka.py --rucne OUT.csv                 (every photo placed by hand: five clicks)

A photo is made from the picture of a KMZ with the course (data/*/course.kmz, data-extra/*, CLASS.kmz): the
paper (the picture without the Livelox title bar) is bent, rotated, seen by a tilted camera, laid on a table,
lit unevenly, tinted, blurred, cut, stored with an EXIF orientation... Every step is an exact mapping, so it is
known where every corner and every control of the paper lands in the photo.

The control positions the fit gets ("GPS at the punch"): for Pohora and Petřvald the real track at the
official ORIS times (tests/fixtures/oris), for the other maps the true positions with 8 m of noise.

For every photo: placed or not (and why), how many controls matched, RMS, the error of the four corners of the
map and of the controls in the photo against the truth (metres). One row per photo in OUT.csv.
"""
import argparse
import csv
import glob
import io
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the real races: data/ and tests/golden, or the folder OB_TEST_DATA (tests/README.md)
_EXT = os.environ.get("OB_TEST_DATA")
DATA = _EXT or os.path.join(ROOT, "data")
GOLDEN = os.path.join(_EXT, "golden") if _EXT else os.path.join(ROOT, "tests", "golden")
sys.path.insert(0, ROOT)

from oroute import georef  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402

if not hasattr(georef, "place"):     # the oroute/georef.py from before the photos (to measure where it started)
    def _local_frame(lat0, lon0):
        kx = georef.R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
        ky = georef.R_EARTH * math.pi / 180
        return lambda la, lo: ((np.asarray(lo) - lon0) * kx, (np.asarray(la) - lat0) * ky)

    def _place(image, controls, lat0, lon0):
        circles, r = georef.find_circles(image)
        f = georef.fit(circles, controls, r, image.size)
        return georef.geomap(image, f, lat0, lon0), f
    georef.local_frame, georef.place = _local_frame, _place
    georef.track_frame = lambda t: (float(np.nanmean(t["lat"])), float(np.nanmean(t["lon"])))

GPS_NOISE_M = 8.0
# the real track at the official punch times: (folder, ORIS class id, date); the runner is BFM0903
ORIS = {"pohora": (202420, "2025-05-17"), "petrvald": (215134, "2026-03-28")}
EXTRA = ["10. SZL MSKS, HA", "3. Zkouška sirén 2024_2025, HA", "Grand prix Silesia - E3, H16B",
         "Mistrovtsví oblasti MSK ve sprintu, H16"]

BASE = dict(tilt=0.0, rot=0.0, exif=1, bend=0.0, light=1.0, kelvin=6500, glare=False, degrade=False, bg=0.15,
            crop=0, mpx=12.0)
SINGLE = ([("tilt", v) for v in (10, 20, 30)] + [("rot", v) for v in (37, 90, 180, 250)]
          + [("exif", v) for v in (6, 3)] + [("bend", v) for v in (0.01, 0.02)]
          + [("light", v) for v in (0.4, 0.6, 0.8)] + [("kelvin", v) for v in (5000, 8000)]
          + [("glare", True), ("degrade", True)] + [("bg", v) for v in (0.1, 0.2, 0.3)]
          + [("crop", v) for v in (1, 2)] + [("mpx", 3.0)])
COMBOS = [
    dict(tilt=20, rot=37, light=0.6, kelvin=5000, bg=0.2),
    dict(tilt=30, bend=0.02, degrade=True, bg=0.25),
    dict(tilt=10, rot=180, exif=6, glare=True, kelvin=8000),
    dict(tilt=20, light=0.4, degrade=True, mpx=3.0),
    dict(tilt=15, bend=0.01, crop=1, light=0.7, bg=0.3),
    dict(tilt=25, rot=250, kelvin=5000, glare=True, degrade=True, mpx=3.0),
]


def cases():
    """(name, params) of the whole set for one map: the plain photo, each distortion alone, the combinations."""
    out = [("zaklad", dict(BASE))]
    for k, v in SINGLE:
        out.append((f"{k}={v}", dict(BASE, **{k: v})))
    for i, c in enumerate(COMBOS, 1):
        out.append((f"kombinace{i}", dict(BASE, **c)))
    return out


# --- the maps and their truth ---------------------------------------------------------------------------------

def sources(names=None):
    """dict(name, kmz, golden course.json or None) of the maps the set is made from."""
    out = []
    for d in sorted(glob.glob(os.path.join(DATA, "*", "course.kmz"))):
        name = os.path.basename(os.path.dirname(d))
        golden = os.path.join(GOLDEN, name, "course.json")
        out.append(dict(name=name, kmz=d, golden=golden if os.path.exists(golden) else None))
    for n in EXTRA:
        p = os.path.join(ROOT, "data-extra", n + ".kmz")
        if os.path.exists(p):
            out.append(dict(name=n, kmz=p, golden=None))
    return [s for s in out if not names or s["name"] in names]


def load(src, rng):
    """The paper, where its controls are on it and on the ground, and the positions the fit is given."""
    gm = GeoMap.from_kmz(src["kmz"])
    hp = gm.header_px
    paper = gm.image.crop((0, hp, gm.W, gm.H))
    if src["golden"]:
        with open(src["golden"], encoding="utf-8") as f:
            ctrl_gm = [c["px"] for c in json.load(f)["controls"]]
    else:
        from oroute.course import detect_course
        ctrl_gm = [c[:2] for c in detect_course(gm)["controls"]]
    ctrl_gm = np.array(ctrl_gm, float)
    corners_gm = np.array([(0, hp), (gm.W, hp), (gm.W, gm.H), (0, gm.H)], float)
    la, lo = gm.px_to_latlon(ctrl_gm[:, 0], ctrl_gm[:, 1])
    cla, clo = gm.px_to_latlon(corners_gm[:, 0], corners_gm[:, 1])
    radius = georef.find_circles(gm.image)[1]
    if src["name"] in ORIS:
        from oroute.fitload import load_track
        from webapp import oris
        cid, date = ORIS[src["name"]]
        track = load_track(os.path.join(os.path.dirname(src["kmz"]), "run.fit"))
        with open(os.path.join(ROOT, "tests", "fixtures", "oris", f"getSplits_{cid}.json"), encoding="utf-8") as f:
            s = oris.parse_splits(json.load(f)["Data"], "BFM0903")
        rec = track["start"].replace(tzinfo=oris.dt.timezone.utc)
        start = (oris.start_utc(date, s["start_local"]) - rec).total_seconds()
        lat0, lon0 = georef.track_frame(track)
        controls = georef.control_positions(track, georef.local_frame(lat0, lon0), start, s["cumulative"])
    else:
        lat0, lon0 = gm.lat0, gm.lon0
        x, y = georef.local_frame(lat0, lon0)(la, lo)
        controls = [tuple(p) for p in np.c_[x, y] + rng.normal(0, GPS_NOISE_M, (len(x), 2))]
    to_xy = georef.local_frame(lat0, lon0)
    return dict(paper=paper, ctrl_px=ctrl_gm - [0, hp], corners_px=corners_gm - [0, hp], radius=radius,
                ctrl_xy=np.c_[to_xy(la, lo)], corners_xy=np.c_[to_xy(cla, clo)], controls=controls,
                lat0=lat0, lon0=lon0, m_per_px=(gm.m_per_px_x + gm.m_per_px_y) / 2)


# --- the photo ------------------------------------------------------------------------------------------------

def _camera(Wp, Hp, rot_deg, tilt_deg):
    """(homography paper px -> picture plane of a camera tilted by tilt_deg, its focal length in paper px). A
    pinhole camera on the axis through the middle of the paper, as far from it as its focal length (0.75 x the
    paper's diagonal)."""
    T = np.array([[1, 0, -Wp / 2], [0, 1, -Hp / 2], [0, 0, 1]], float)
    a = math.radians(rot_deg)
    R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]], float)
    f = 0.75 * math.hypot(Wp, Hp)
    t = math.radians(tilt_deg)
    C = np.array([[f, 0, 0], [0, f * math.cos(t), 0], [0, math.sin(t), f]], float)
    return C @ R @ T, f


def _apply(H, pts):
    pts = np.asarray(pts, float)
    q = np.c_[pts, np.ones(len(pts))] @ H.T
    return q[:, :2] / q[:, 2:3]


class Photo:
    """Forward mapping paper px -> photo px (as displayed, before the EXIF orientation is applied)."""

    def __init__(self, paper_size, p):
        Wp, Hp = paper_size
        self.Wp, self.Hp, self.bend = Wp, Hp, p["bend"] * Wp
        H0, f = _camera(Wp, Hp, p["rot"], p["tilt"])
        quad = _apply(H0, self._bent(self._outline()))
        bw, bh = np.ptp(quad[:, 0]), np.ptp(quad[:, 1])
        area = 0.5 * abs(np.dot(quad[:, 0], np.roll(quad[:, 1], 1)) - np.dot(quad[:, 1], np.roll(quad[:, 0], 1)))
        long_side = math.sqrt(p["mpx"] * 1e6 * 4 / 3)
        W, H = (long_side, long_side * 3 / 4) if bw >= bh else (long_side * 3 / 4, long_side)
        # the optical axis through the middle of the photo, as in a phone: the paper fills what bg leaves, as long
        # as it fits in the frame
        mx, my = np.abs(quad[:, 0]).max(), np.abs(quad[:, 1]).max()
        s = min(math.sqrt((1 - p["bg"]) * W * H / area), 0.98 * W / 2 / mx, 0.98 * H / 2 / my)
        S = np.array([[s, 0, W / 2], [0, s, H / 2], [0, 0, 1]], float)
        self.H = S @ H0
        self.Hinv = np.linalg.inv(self.H)
        self.size = (int(round(W)), int(round(H)))
        self.focal35 = s * f / math.hypot(W, H) * 43.27     # the focal length a phone writes into EXIF (35 mm terms)
        self.x0 = 0                 # how far the paper is moved left out of the frame (crop)

    def _outline(self, n=40):
        t = np.linspace(0, 1, n, endpoint=False)
        W, H = self.Wp, self.Hp
        return np.r_[np.c_[t * W, 0 * t], np.c_[W + 0 * t, t * H], np.c_[W - t * W, H + 0 * t], np.c_[0 * t, H - t * H]]

    def _bent(self, pts):
        pts = np.array(pts, float)
        s = (pts[:, 0] - self.Wp / 2) / (self.Wp / 2)
        pts[:, 1] += self.bend * s ** 2
        return pts

    def forward(self, pts):
        q = _apply(self.H, self._bent(pts))
        q[:, 0] -= self.x0
        return q

    def backward_grid(self, rows, W):
        """Paper px (u, v) of photo pixel centres in the given rows (float32 arrays)."""
        yy, xx = np.meshgrid(np.asarray(rows, np.float32) + 0.5, np.arange(W, dtype=np.float32) + 0.5 + self.x0,
                             indexing="ij")
        Hi = self.Hinv.astype(np.float64)
        d = Hi[2, 0] * xx + Hi[2, 1] * yy + Hi[2, 2]
        u = (Hi[0, 0] * xx + Hi[0, 1] * yy + Hi[0, 2]) / d
        v = (Hi[1, 0] * xx + Hi[1, 1] * yy + Hi[1, 2]) / d
        s = (u - self.Wp / 2) / (self.Wp / 2)
        v = v - self.bend * s ** 2
        return u.astype(np.float32), v.astype(np.float32)


def _kelvin_rgb(T):
    """RGB of a black body at T kelvin (Tanner Helland's fit), 0..255."""
    t = T / 100.0
    r = 255.0 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255.0 if t >= 66 else (0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447828307)
    return np.clip([r, g, b], 0, 255)


def _table(size, rng):
    """A wooden table: brown with stripes, made small and blown up."""
    W, H = size
    w, h = max(8, W // 16), max(8, H // 16)
    y = np.arange(h)[:, None]
    stripes = 0.5 + 0.5 * np.sin(y / h * 40 + rng.normal(0, 0.6, (h, w)).cumsum(1) * 0.05)
    base = np.array([128, 90, 58], float)
    a = base[None, None, :] * (0.75 + 0.35 * stripes[..., None]) + rng.normal(0, 4, (h, w, 3))
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)


def make_photo(m, p, seed=0):
    """(PIL image as stored in the file, EXIF orientation, Photo mapping, JPEG quality)."""
    rng = np.random.default_rng(seed)
    ph = Photo(m["paper"].size, p)
    W, H = ph.size
    if p["crop"]:
        # the k leftmost controls out of the frame: the paper moved left so that the frame's edge lies halfway
        # between the k-th and the (k+1)-th control
        x = np.sort(ph.forward(m["ctrl_px"])[:, 0])
        ph.x0 = int((x[p["crop"] - 1] + x[p["crop"]]) / 2)
    paper = np.asarray(m["paper"], np.float32)
    out = _table((W, H), rng)
    step = max(1, 2_000_000 // W)
    for r0 in range(0, H, step):
        rows = range(r0, min(H, r0 + step))
        u, v = ph.backward_grid(rows, W)
        inside = (u >= 0) & (u < paper.shape[1] - 1) & (v >= 0) & (v < paper.shape[0] - 1)
        if not inside.any():
            continue
        for ch in range(3):
            got = ndi.map_coordinates(paper[..., ch], [v[inside], u[inside]], order=1)
            out[r0:r0 + len(rows), :, ch][inside] = got
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if p["light"] < 1:
        # a shadow over about half the map, soft edge, and a little vignetting
        a = math.radians(30)
        d = ((xx - W / 2) * math.cos(a) + (yy - H / 2) * math.sin(a)) / (0.06 * W)
        L = 1 - (1 - p["light"]) / (1 + np.exp(-d))
        L *= 1 - 0.12 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
        out *= L[..., None]
    if p["kelvin"] != 6500:
        out *= (_kelvin_rgb(p["kelvin"]) / _kelvin_rgb(6500)).astype(np.float32)[None, None, :]
    if p["glare"]:
        # a white spot over one control (True), or over that many spread along the course (a number)
        n = len(m["ctrl_px"])
        which = [n // 2] if p["glare"] is True else sorted({int(round(i)) for i in np.linspace(0, n - 1, p["glare"])})
        for k in which:
            c = ph.forward(m["ctrl_px"][[k]])[0]
            r_ph = m["radius"] * _local_scale(ph, m["ctrl_px"][k])
            g = 0.97 * np.exp(-((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / (2 * (1.6 * r_ph) ** 2))
            out = out * (1 - g[..., None]) + 255 * g[..., None]
    del xx, yy
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    del out
    if p["degrade"]:
        im = im.filter(ImageFilter.GaussianBlur(1.2))
        a = np.asarray(im, np.int16) + rng.normal(0, 6, (H, W, 1)).astype(np.int16)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if p["exif"] == 6:
        im = im.transpose(Image.ROTATE_90)       # exif_transpose turns it back by ROTATE_270
    elif p["exif"] == 3:
        im = im.transpose(Image.ROTATE_180)
    return im, p["exif"], ph, 60 if p["degrade"] else 90


def _local_scale(ph, pt):
    """Photo px per paper px around a paper point."""
    q = ph.forward(np.array([pt, [pt[0] + 10, pt[1]], [pt[0], pt[1] + 10]], float))
    return (np.hypot(*(q[1] - q[0])) + np.hypot(*(q[2] - q[0]))) / 20


def jpeg(im, orientation, quality, focal35=None):
    """The photo as a phone stores it: JPEG, the EXIF orientation, the focal length in 35 mm terms."""
    buf = io.BytesIO()
    kw = {}
    if orientation != 1 or focal35:
        ex = Image.Exif()
        if orientation != 1:
            ex[0x0112] = orientation
        if focal35:
            ex.get_ifd(0x8769)[0xA405] = int(round(focal35))
        kw["exif"] = ex.tobytes()
    im.save(buf, "JPEG", quality=quality, **kw)
    return buf.getvalue()


def to_opened(pts, ph, orientation, shown_small, stored_small, opened):
    """Displayed photo px -> px of the picture as georef.open_image gave it (it may or may not have applied the
    EXIF orientation, and it may have made it smaller): whichever of the two a small copy is closer to."""
    pts = np.asarray(pts, float)
    W, H = ph.size
    q, frame = pts, (W, H)
    if orientation != 1:
        small = _small(opened)
        if np.abs(small - stored_small).mean() < np.abs(small - shown_small).mean():
            q = np.c_[pts[:, 1], W - pts[:, 0]] if orientation == 6 else np.c_[W - pts[:, 0], H - pts[:, 1]]
            frame = (H, W) if orientation == 6 else (W, H)
    return q * (opened.size[0] / frame[0])


def _small(im):
    return np.asarray(im.convert("L").resize((64, 64)), float)


def displayed(im, orientation):
    """The stored picture as a viewer shows it."""
    return im.transpose(Image.ROTATE_270) if orientation == 6 else im.transpose(Image.ROTATE_180) \
        if orientation == 3 else im


# --- wrong inputs (docs/foto-mapy.md, part 7) ------------------------------------------------------------------

BAD = ["rozmazana", "tmava", "bez-trate", "jina-kategorie", "pulka", "odlesky", "dve-mapy", "screenshot"]


def bad_photo(kind, m, other=None, mpx=0.8, seed=0):
    """JPEG bytes of a wrong input made from the map m: rozmazana (blurred beyond reading), tmava (dark),
    bez-trate (other: a map without the course), jina-kategorie (other: the map of another course), pulka (only
    two controls in the frame), odlesky (glare over five controls), dve-mapy (two sheets on the table: the map cut
    in two, as at a map exchange), screenshot (the Livelox picture with its title bar in a phone's screen)."""
    p = dict(BASE, mpx=mpx)
    if kind in ("bez-trate", "jina-kategorie"):
        im, o, ph, q = make_photo(other, p, seed)
        return jpeg(im, o, q, ph.focal35)
    if kind == "pulka":
        p.update(crop=len(m["ctrl_px"]) - 2)
    if kind == "odlesky":
        p.update(glare=5)
    if kind == "dve-mapy":
        W, H = m["paper"].size
        halves = []
        for box in ((0, 0, W // 2 + 40, H), (W // 2 - 40, 0, W, H)):
            half = dict(m, paper=m["paper"].crop(box), ctrl_px=m["ctrl_px"] - [box[0], 0])
            im, _, ph, _ = make_photo(half, dict(p, bg=0.35, mpx=mpx / 2), seed)
            halves.append(im)
        both = Image.new("RGB", (halves[0].width + halves[1].width, max(h.height for h in halves)))
        both.paste(halves[0], (0, 0))
        both.paste(halves[1], (halves[0].width, 0))
        return jpeg(both, 1, 90)
    if kind == "screenshot":
        # 1170 x 2532 (a phone): status bar, the Livelox picture with its title bar, buttons under it
        shot = Image.new("RGB", (1170, 2532), (24, 24, 28))
        full = other.copy()
        full.thumbnail((1170, 2000))
        shot.paste(full, (0, 160))
        from PIL import ImageDraw
        d = ImageDraw.Draw(shot)
        for i in range(4):
            d.rounded_rectangle((60 + i * 280, 2300, 260 + i * 280, 2420), 30, fill=(70, 70, 80))
        return jpeg(shot, 1, 90)
    im, o, ph, q = make_photo(m, p, seed)
    if kind == "rozmazana":
        im = im.filter(ImageFilter.GaussianBlur(0.012 * max(im.size)))
    if kind == "tmava":
        im = Image.fromarray((np.asarray(im, np.float32) * 0.1).astype(np.uint8))
    return jpeg(im, o, q, ph.focal35)


def run_one(m, p, seed=0, save=None, name=""):
    t0 = time.time()
    im, orientation, ph, q = make_photo(m, p, seed)
    data = jpeg(im, orientation, q, ph.focal35)
    shown_small, stored_small = _small(displayed(im, orientation)), _small(im)
    if save:
        with open(os.path.join(save, name + ".jpg"), "wb") as f:
            f.write(data)
    del im
    t1 = time.time()
    row = dict(ok=0, reason="", n=0, controls=sum(c is not None for c in m["controls"]), rms="", corner_max="",
               corner_mean="", ctrl_median="", ctrl_max="", visible=0, kind="", edge_m="",
               photo_px=f"{ph.size[0]}x{ph.size[1]}",
               mb=round(len(data) / 1e6, 1))
    try:
        opened = georef.open_image(io.BytesIO(data))
        cp = to_opened(ph.forward(m["ctrl_px"]), ph, orientation, shown_small, stored_small, opened)
        kp = to_opened(ph.forward(m["corners_px"]), ph, orientation, shown_small, stored_small, opened)
        vis = (cp[:, 0] >= 0) & (cp[:, 0] < opened.size[0]) & (cp[:, 1] >= 0) & (cp[:, 1] < opened.size[1])
        row["visible"] = int(vis.sum())
        gm, f = georef.place(opened, m["controls"], m["lat0"], m["lon0"])
        ec = np.hypot(*(georef.to_metres(f, opened.size, kp) - m["corners_xy"]).T)
        ek = np.hypot(*(georef.to_metres(f, opened.size, cp[vis]) - m["ctrl_xy"][vis]).T)
        row.update(ok=1, n=f["n"], rms=round(f["rms"], 1), corner_max=round(float(ec.max()), 1),
                   corner_mean=round(float(ec.mean()), 1), ctrl_median=round(float(np.median(ek)), 1),
                   ctrl_max=round(float(ek.max()), 1), kind=f.get("kind", "similarity"),
                   edge_m=round(f.get("edge_m", 0.0), 1))
    except georef.GeorefError as e:
        row["reason"] = str(e)
    row["gen_s"], row["georef_s"] = round(t1 - t0, 1), round(time.time() - t1, 1)
    return row


FIELDS = ["map", "case", "ok", "reason", "n", "controls", "visible", "rms", "corner_max", "corner_mean",
          "ctrl_median", "ctrl_max", "kind", "edge_m", "photo_px", "mb", "gen_s", "georef_s"] + list(BASE)


# --- the analysis with the map from a photo against the one with the KMZ (part 5) ---------------------------------

ANALYSIS_PHOTO = dict(BASE, tilt=15, rot=20, light=0.6, kelvin=5000, bg=0.2)


def compare_analysis(name, out, p=ANALYSIS_PHOTO):
    """analyze.py with the Livelox KMZ and with the KMZ the web app makes from a made-up photo of it (the course
    from the placing, analyze.py --course), both with the official ORIS times. Returns rows per leg: what each
    gives and how far the controls of the photo are from those of the KMZ."""
    import subprocess

    from oroute.course import save_course
    from oroute.fitload import load_track
    from webapp import oris
    src = sources([name])[0]
    m = load(src, np.random.default_rng(100))
    cid, date = ORIS[name]
    with open(os.path.join(ROOT, "tests", "fixtures", "oris", f"getSplits_{cid}.json"), encoding="utf-8") as f:
        s = oris.parse_splits(json.load(f)["Data"], "BFM0903")
    official = dict(start_utc=oris.start_utc(date, s["start_local"]).isoformat(), cumulative=s["cumulative"])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "official.json"), "w", encoding="utf-8") as f:
        json.dump(official, f)
    fit_file = os.path.join(os.path.dirname(src["kmz"]), "run.fit")
    run = lambda kmz, where, *more: subprocess.run(
        [sys.executable, "analyze.py", kmz, fit_file, os.path.join(out, where), "--no-images", "--official",
         os.path.join(out, "official.json"), *more], cwd=ROOT, check=True, capture_output=True)
    run(src["kmz"], "kmz")
    im, o, ph, q = make_photo(m, p, seed=7)
    opened = georef.open_image(io.BytesIO(jpeg(im, o, q, ph.focal35)))
    track = load_track(fit_file)
    start = (oris.start_utc(date, s["start_local"]) - track["start"].replace(tzinfo=oris.dt.timezone.utc)).total_seconds()
    gm, f = georef.georeference(opened, track, start, s["cumulative"], course=True)
    georef.write_kmz(os.path.join(out, "photo.kmz"), gm.image, gm)
    save_course(os.path.join(out, "photo.course.json"), gm, f["course"])
    run(os.path.join(out, "photo.kmz"), "photo", "--course", os.path.join(out, "photo.course.json"))
    legs, pts = {}, {}
    for where in ("kmz", "photo"):
        with open(os.path.join(out, where, "legs.csv"), encoding="utf-8") as fh:
            legs[where] = list(csv.DictReader(fh))
        with open(os.path.join(out, where, "analysis.json"), encoding="utf-8") as fh:
            a = json.load(fh)
        pts[where] = [(c["lat"], c["lon"]) for c in a["course"]]
        legs[where + "_mistake"] = [(lg.get("mistake") or {}).get("kind") for lg in a["legs"]]
    k = georef.R_EARTH * math.pi / 180
    shift = [math.hypot((a[0] - b[0]) * k, (a[1] - b[1]) * k * math.cos(math.radians(a[0])))
             for a, b in zip(pts["kmz"], pts["photo"])]
    rows = []
    for i, (a, b) in enumerate(zip(legs["kmz"], legs["photo"])):
        rows.append(dict(map=name, leg=a["leg"], split_kmz=a["split"], split_photo=b["split"],
                         straight_kmz=a["straight_m"], straight_photo=b["straight_m"], run_kmz=a["run_m"],
                         run_photo=b["run_m"], loss_kmz=a["est_loss_s"], loss_photo=b["est_loss_s"],
                         mistake_kmz=legs["kmz_mistake"][i], mistake_photo=legs["photo_mistake"][i],
                         control_shift_m=round(shift[i + 1], 1) if i + 1 < len(shift) else ""))
    return rows, f


# --- placing by hand (part 4): five clicks on the photo --------------------------------------------------------

CLICK_PX = 3.0         # how far from the centre of a circle a finger lands (photo pixels)


def spread_controls(controls, k=5):
    """Indices of k controls spread over the course: farthest west, east, south, north, then from the middle."""
    g = np.array([c if c is not None else (np.nan, np.nan) for c in controls], float)
    ok = [i for i in range(len(g)) if np.isfinite(g[i]).all()]
    pick = []
    for f in (lambda i: g[i, 0], lambda i: -g[i, 0], lambda i: g[i, 1], lambda i: -g[i, 1]):
        i = min(ok, key=f)
        if i not in pick:
            pick.append(i)
    mid = np.nanmean(g, 0)
    for i in sorted(ok, key=lambda i: -np.hypot(*(g[i] - mid))):
        if len(pick) >= k:
            break
        if i not in pick:
            pick.append(i)
    return pick


def run_by_hand(m, p, seed=0):
    """The photo placed by hand: clicks on five controls spread over the course (true centre + CLICK_PX of
    noise), georef.fit_points with the edges of the sheet when they are found. Corner and control errors."""
    rng = np.random.default_rng(seed + 7)
    im, orientation, ph, q = make_photo(m, p, seed)
    data = jpeg(im, orientation, q, ph.focal35)
    shown_small, stored_small = _small(displayed(im, orientation)), _small(im)
    opened = georef.open_image(io.BytesIO(data))
    cp = to_opened(ph.forward(m["ctrl_px"]), ph, orientation, shown_small, stored_small, opened)
    kp = to_opened(ph.forward(m["corners_px"]), ph, orientation, shown_small, stored_small, opened)
    W, H = opened.size
    visible = [i for i in range(len(cp)) if 0 <= cp[i, 0] < W and 0 <= cp[i, 1] < H]
    pick = [visible[i] for i in spread_controls([m["controls"][i] for i in visible])]
    clicks = [tuple(cp[i] + rng.normal(0, CLICK_PX, 2)) for i in pick]
    got = georef.fit_points(clicks, [m["controls"][i] for i in pick], opened.size, georef.paper_quad(opened),
                            georef.photo_focal(opened))
    row = dict(ok=int(got["H"] is not None and not any(c in ("few", "line", "mirror") for c, _ in got["problems"])),
               kind=got["kind"] or "", rms=round(got["rms"] or 0, 1), problems=" ".join(c for c, _ in got["problems"]))
    if got["H"] is not None:
        f = dict(H=got["H"].tolist())
        row["corner_max"] = round(float(np.hypot(*(georef.to_metres(f, opened.size, kp) - m["corners_xy"]).T).max()), 1)
        vis = np.array(visible)
        row["ctrl_median"] = round(float(np.median(np.hypot(*(georef.to_metres(f, opened.size, cp[vis])
                                                               - m["ctrl_xy"][vis]).T))), 1)
    return row


GOOD_CORNER_M = 50.0   # a photo "placed well": every corner of the map within this of the truth


def summary(paths):
    """Markdown table: per case, how many photos were placed, how many well (corners within GOOD_CORNER_M), the
    median of the worst corner error and of the median control error; one column group per CSV."""
    tables = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            tables.append(list(csv.DictReader(f)))
    order = [c for c, _ in cases()]
    head = "| Fotka | " + " | ".join(f"{os.path.basename(p)}: usazeno / dobře / roh / kontroly" for p in paths) + " |"
    lines = [head, "|---|" + "---|" * len(paths)]

    def cell(rows):
        ok = [r for r in rows if r["ok"] == "1"]
        good = [r for r in ok if float(r["corner_max"]) <= GOOD_CORNER_M]
        med = lambda k: f"{np.median([float(r[k]) for r in ok]):.0f} m" if ok else "–"
        return f"{len(ok)}/{len(rows)} / {len(good)} / {med('corner_max')} / {med('ctrl_median')}"
    for case in order + ["celkem"]:
        cells = [cell([r for r in t if case == "celkem" or r["case"] == case]) for t in tables]
        lines.append(f"| {case} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--souhrn":
        print(summary(sys.argv[2:]))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--rucne":
        out, rows = sys.argv[2], []
        every = [x["name"] for x in sources()]
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, ["map", "case", "ok", "kind", "rms", "corner_max", "ctrl_median", "problems"])
            w.writeheader()
            for src in sources():
                k = every.index(src["name"])
                m = load(src, np.random.default_rng(100 + k))
                for j, (case, p) in enumerate(cases()):
                    row = dict(map=src["name"], case=case, **run_by_hand(m, p, seed=1000 * k + j))
                    w.writerow(row)
                    fh.flush()
                    rows.append(row)
                    print(src["name"], case, row, flush=True)
        good = [r for r in rows if r["ok"] and r.get("corner_max", 1e9) <= GOOD_CORNER_M]
        print("placed", sum(r["ok"] for r in rows), "of", len(rows), "well", len(good))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--analyza":
        out = sys.argv[2]
        rows = []
        for name in ("pohora", "petrvald"):
            got, f = compare_analysis(name, os.path.join(out, name))
            print(name, "placed", f["kind"], f["n"], "of", f["controls"], "rms", round(f["rms"], 1), flush=True)
            rows += got
        with open(os.path.join(out, "analyza.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--maps", help="map names separated by ; (default: all)")
    ap.add_argument("--only", help="only the cases whose name contains this")
    ap.add_argument("--save", help="folder to keep the photos in (JPEG)")
    ap.add_argument("--quick", action="store_true", help="photos of 3 Mpx instead of 12")
    a = ap.parse_args()
    if a.save:
        os.makedirs(a.save, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        every = [s["name"] for s in sources()]
        for src in sources(a.maps.split(";") if a.maps else None):
            k = every.index(src["name"])       # the same photos as in the whole set, whatever is left out
            m = load(src, np.random.default_rng(100 + k))
            for j, (case, p) in enumerate(cases()):
                if a.only and a.only not in case:
                    continue
                if a.quick:
                    p = dict(p, mpx=min(p["mpx"], 3.0))
                row = run_one(m, p, seed=1000 * k + j, save=a.save, name=f"{src['name']}-{case}")
                row.update(map=src["name"], case=case, **p)
                w.writerow(row)
                fh.flush()
                print(src["name"], case, "OK" if row["ok"] else "--", row["n"], "/", row["controls"], row["rms"],
                      row["corner_max"], row["ctrl_median"], row["reason"][:70], f"{row['georef_s']}s", flush=True)


if __name__ == "__main__":
    main()
