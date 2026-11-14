#!/usr/bin/env python3
"""Height in a Garmin .fit against the terrain model, and whether it can say where the track really was (issue 41).

Measurement only: nothing in oroute/ uses it (docs/validace.md, section 25).

    python tools/fit_vyska.py RUN.fit [RUN2.fit ...] [--dem auto|cuzk|aws] [--json OUT.json]
    python tools/fit_vyska.py --zavod pohora petrvald [--posun]

For every recording it prints what the file holds (which height field, how often, whether the watch lists a
barometer) and how the height behaves: the noise around a 15 s average (a barometer: tenths of a metre, a GPS
height: metres), and against the terrain model along the track (ČÚZK DMR 5G in the Czech Republic, AWS Terrain
Tiles elsewhere): RMS after a constant offset, the linear drift in m/h and the RMS after it, and the slope over
50 m of distance (RMS of the difference, correlation, climb).

--posun (shift search): for the whole track and for stretches of WINDOW_M of it, every shift in a +-SHIFT_M grid of
SHIFT_STEP_M is tried and the height profile under the shifted track (averaged like the barometer) is compared with
the barometer, after the best offset and linear drift are taken out, so only the shape counts. The best shift, how
sharp the minimum is (the best RMS against the best one at least SECOND_M away) and how much relief the stretch has
decide whether a stretch is trusted (confident()); the whole track by whole_trusted(). Races of data/ with official
ORIS times in tests/fixtures/oris (Pohora, Petřvald) or with --oficialni JSON are the truth: how far the track is
from the control circles at the punch times before and after the correction. --zkusebni-posun DX DY moves the track
by a known amount first: the search should find it back.

Races are folders of data/ (course.kmz, run.fit), see docs/data-lokalne.md; the elevation is cached in
kontrola/fit_vyska/ (not in git). Elevation needs the network the first time (ČÚZK, AWS).
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from scipy.ndimage import uniform_filter1d

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import dem as demmod  # noqa: E402

SMOOTH_S = 15            # the barometer (and the terrain under the track) averaged over this many seconds
STEP_M = 50.0            # slope compared over this distance along the track
WINDOW_M = 800.0         # stretch of the track whose profile is matched in the shift search
SHIFT_M = 40.0           # shifts tried up to this far in x and in y ...
SHIFT_STEP_M = 2.0       # ... in steps of this
SECOND_M = 10.0          # the second best shift is the best one at least this far from the best
# a shift is trusted only with all of these (docs/validace.md, section 25)
MIN_RELIEF_M = 4.0       # the terrain under the stretch varies at least this much (std): no shift on flat ground
MIN_SHARPNESS = 1.5      # second best RMS / best RMS
MAX_TRUST_M = 30.0       # and the shift is no larger than this (larger ones were never right)
NONSENSE_M = 40.0        # a best shift this large (or on the edge of the grid) counts as nonsense
# the shift of the whole track is trusted with ČÚZK, hilly ground and a barometer that follows the terrain
WHOLE_RELIEF_M = 7.0     # std of the terrain height along the track (compare()["relief_m"])
WHOLE_SLOPE_CORR = 0.85  # correlation of the slope over STEP_M, barometer against terrain
MOVING_MS = 0.5          # slower than this the runner stands: those seconds are left out of the drift fit
REGNO = "BFM0903"        # the author's ORIS registration, as in tests/test_official_races.py
ORIS = {"pohora": (202420, "2025-05-17"), "petrvald": (215134, "2026-03-28")}
R_EARTH = 6371000.0


# ----------------------------------------------------------------------------------------------------------- the file

def read_fit(path):
    """Records and what the watch says about itself: dict t (s), lat, lon, alt_enh, alt (NaN where missing),
    product, sensors (local_device_type of device_info), sport."""
    import fitdecode
    rows, sensors, product, sport = [], set(), None, None
    with fitdecode.FitReader(path) as f:
        for fr in f:
            if not isinstance(fr, fitdecode.FitDataMessage):
                continue
            v = {fd.name: fd.value for fd in fr.fields}
            if fr.name == "record" and v.get("timestamp") is not None:
                lat, lon = v.get("position_lat"), v.get("position_long")
                ok = lat is not None and lon is not None
                rows.append((v["timestamp"], lat * 180 / 2**31 if ok else np.nan, lon * 180 / 2**31 if ok else np.nan,
                             _num(v.get("enhanced_altitude")), _num(v.get("altitude"))))
            elif fr.name == "device_info":
                if v.get("local_device_type"):
                    sensors.add(str(v["local_device_type"]))
                if v.get("device_index") == "creator" and v.get("garmin_product"):
                    product = str(v["garmin_product"])
            elif fr.name == "file_id" and product is None and v.get("garmin_product"):
                product = str(v["garmin_product"])
            elif fr.name == "sport" and v.get("sport"):
                sport = str(v["sport"])
    if len(rows) < 10:
        raise ValueError(f"{path}: too few records")
    t0 = rows[0][0]
    col = lambda i: np.array([r[i] for r in rows], float)
    return dict(start=t0, t=np.array([(r[0] - t0).total_seconds() for r in rows]), lat=col(1), lon=col(2),
                alt_enh=col(3), alt=col(4), product=product, sensors=sorted(sensors), sport=sport)


def _num(v):
    return float(v) if isinstance(v, (int, float)) else np.nan


def height_field(rec):
    """(name, values) of the height the app reads (oroute/fitload.py: enhanced_altitude, else altitude)."""
    if np.isfinite(rec["alt_enh"]).any():
        return "enhanced_altitude", rec["alt_enh"]
    return "altitude", rec["alt"]


def per_second(rec, alt):
    """The recording on a 1 s grid (positions and height interpolated), only where it has both."""
    ok = np.isfinite(rec["lat"]) & np.isfinite(alt)
    t = rec["t"][ok]
    g = np.arange(math.ceil(t[0]), math.floor(t[-1]) + 1, 1.0)
    return dict(t=g, lat=np.interp(g, t, rec["lat"][ok]), lon=np.interp(g, t, rec["lon"][ok]),
                alt=np.interp(g, t, alt[ok]))


def smooth(v, s=SMOOTH_S):
    return uniform_filter1d(np.asarray(v, float), size=int(s), mode="nearest")


def file_facts(rec):
    """What is in the file and how the height behaves on its own (no terrain model needed)."""
    name, alt = height_field(rec)
    dt = np.diff(rec["t"])
    step = np.diff(np.unique(np.round(alt[np.isfinite(alt)], 3)))
    s = per_second(rec, alt)
    noise = float(np.std(s["alt"] - smooth(s["alt"])))
    return dict(product=rec["product"], sensors=rec["sensors"], field=name, records=len(rec["t"]),
                interval_s=float(np.median(dt)), max_gap_s=float(dt.max()),
                both_fields=bool(np.isfinite(rec["alt_enh"]).any() and np.isfinite(rec["alt"]).any()),
                resolution_m=float(np.median(step[:50])) if len(step) else None, noise_1s_m=noise,
                barometer_listed="barometer" in rec["sensors"], barometer_like=noise < 0.7)


# --------------------------------------------------------------------------------------------- against the terrain

def local(lat, lon, lat0, lon0):
    kx = R_EARTH * math.cos(math.radians(lat0)) * math.pi / 180
    ky = R_EARTH * math.pi / 180
    return (np.asarray(lon) - lon0) * kx, (np.asarray(lat) - lat0) * ky, kx, ky


def load_terrain(s, source, cache_dir, dem_smooth_m=demmod.CUZK_SMOOTH_M):
    n, so = float(s["lat"].max()), float(s["lat"].min())
    e, w = float(s["lon"].max()), float(s["lon"].min())
    pad = 120.0 / 111195.0   # the shift search reads up to SHIFT_M beside the track
    padx = pad / math.cos(math.radians((n + so) / 2))
    os.makedirs(cache_dir, exist_ok=True)
    box = (n + pad, so - pad, e + padx, w - padx)
    if source == "cuzk" or (source == "auto" and demmod.in_czechia(*box)):
        try:
            return demmod.CuzkDEM(*box, cache=os.path.join(cache_dir, "dem_cuzk.npz"), smooth_m=dem_smooth_m)
        except demmod.DemError:
            if source == "cuzk":
                raise
    return demmod.TerrariumDEM(*box, cache=os.path.join(cache_dir, "dem_cache.npz"))


def along(s):
    """Distance along the track (m) from the positions."""
    x, y, _, _ = local(s["lat"], s["lon"], s["lat"][0], s["lon"][0])
    return np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])


def compare(s, terrain):
    """Height of the watch (smoothed SMOOTH_S) against the terrain under the track (smoothed the same way)."""
    baro = smooth(s["alt"])
    ground = smooth(terrain.height(s["lat"], s["lon"]))
    d = baro - ground
    th = s["t"] / 3600.0
    out = dict(offset_m=float(np.median(d)), rms_const_m=float(np.sqrt(np.mean((d - d.mean()) ** 2))))
    # drift: a straight line in time, fitted where the runner moves (standing at the start the GPS wanders)
    dist = along(s)
    speed = np.gradient(dist, s["t"])
    mv = smooth(speed) > MOVING_MS
    A = np.vstack([np.ones(mv.sum()), th[mv]]).T
    coef, *_ = np.linalg.lstsq(A, d[mv], rcond=None)
    rest = d - (coef[0] + coef[1] * th)
    out.update(drift_m_per_h=float(coef[1]), drift_total_m=float(coef[1] * (th[-1] - th[0])),
               rms_drift_m=float(np.sqrt(np.mean(rest[mv] ** 2))), hours=float(th[-1] - th[0]))
    # slope over STEP_M of distance: what the speed model uses (changes of height, not the height)
    q = np.arange(0.0, dist[-1], STEP_M)
    keep = np.concatenate([[True], np.diff(dist) > 0])
    hb, hg = np.interp(q, dist[keep], baro[keep]), np.interp(q, dist[keep], ground[keep])
    gb, gg = np.diff(hb) / STEP_M, np.diff(hg) / STEP_M
    out.update(km=float(dist[-1] / 1000), slope_rms_pct=float(100 * np.sqrt(np.mean((gb - gg) ** 2))),
               slope_corr=float(np.corrcoef(gb, gg)[0, 1]) if len(gb) > 3 else float("nan"),
               climb_baro_m=float(np.clip(np.diff(hb), 0, None).sum()),
               climb_dem_m=float(np.clip(np.diff(hg), 0, None).sum()),
               relief_m=float(np.std(hg)))
    return out


# -------------------------------------------------------------------------------------------------- shift search

def shifts(limit=SHIFT_M, step=SHIFT_STEP_M):
    v = np.arange(-limit, limit + step / 2, step)
    dx, dy = np.meshgrid(v, v)
    return dx.ravel(), dy.ravel()


def score_shifts(x, y, h, height_xy, dx, dy, smooth_s=SMOOTH_S):
    """RMS of (barometer - terrain under the shifted points) for every shift. x, y, h are seconds of the track;
    the terrain under it is averaged over smooth_s like the barometer, and the best offset and linear drift are
    taken out: only the shape of the profile counts."""
    t = np.arange(len(h), dtype=float)
    A = np.vstack([np.ones(len(t)), t - t.mean()]).T
    P = A @ np.linalg.pinv(A)          # projection on offset + drift
    out = np.empty(len(dx))
    for k in range(len(dx)):
        r = h - smooth(height_xy(x + dx[k], y + dy[k]), smooth_s)
        r = r - P @ r
        out[k] = np.sqrt(np.mean(r ** 2))
    return out


def best_shift(x, y, h, height_xy, dx=None, dy=None, smooth_s=SMOOTH_S):
    """The shift whose terrain profile fits the barometer best, and how sure that is.
    Returns dict dx, dy, rms_best, rms_zero, rms_second, sharpness, relief, edge."""
    if dx is None:
        dx, dy = shifts()
    sc = score_shifts(x, y, h, height_xy, dx, dy, smooth_s)
    k = int(np.argmin(sc))
    far = np.hypot(dx - dx[k], dy - dy[k]) >= SECOND_M
    zero = int(np.argmin(np.hypot(dx, dy)))
    g0 = smooth(height_xy(x, y), smooth_s)
    # relief: how much the terrain under the stretch varies once a straight climb is removed
    sdist = np.arange(len(g0))
    trend = np.polyval(np.polyfit(sdist, g0, 1), sdist) if len(g0) > 2 else g0.mean()
    lim = max(abs(dx).max(), abs(dy).max())
    return dict(dx=float(dx[k]), dy=float(dy[k]), rms_best=float(sc[k]), rms_zero=float(sc[zero]),
                rms_second=float(sc[far].min()), sharpness=float(sc[far].min() / max(sc[k], 1e-6)),
                relief=float(np.std(g0 - trend)), edge=bool(abs(dx[k]) >= lim or abs(dy[k]) >= lim))


def confident(b):
    """Whether a shift found by best_shift may be used."""
    return (b["relief"] >= MIN_RELIEF_M and b["sharpness"] >= MIN_SHARPNESS and not b["edge"]
            and math.hypot(b["dx"], b["dy"]) <= MAX_TRUST_M)


def whole_trusted(dem_source, vs_dem, whole):
    """Whether the shift of the whole track says something (docs/validace.md, section 25): on flat ground, with the
    coarse AWS heights or where the barometer does not follow the terrain (a town: DMR 5G has no buildings) it
    does not."""
    return (dem_source == "cuzk" and vs_dem["relief_m"] >= WHOLE_RELIEF_M and vs_dem["slope_corr"] >= WHOLE_SLOPE_CORR
            and not whole["edge"])


def nonsense(b):
    return b["edge"] or math.hypot(b["dx"], b["dy"]) > NONSENSE_M


def windows(dist, length=WINDOW_M):
    """(start, end) distances of the overlapping stretches (overlapping by half); a short track is one stretch."""
    step = length / 2
    if dist[-1] <= length:
        return [(0.0, float(dist[-1]))]
    starts = np.arange(0.0, dist[-1] - length / 2, step)
    return [(float(a), float(min(a + length, dist[-1]))) for a in starts]


def search(s, terrain, smooth_s=SMOOTH_S, window_m=WINDOW_M):
    """Shift search on the whole track and on its stretches. Returns dict(whole, windows=[...], shift_x, shift_y):
    shift_x/shift_y per second of s = the average of the trusted shifts of the stretches covering it (0 where none)."""
    lat0, lon0 = float(s["lat"].mean()), float(s["lon"].mean())
    x, y, kx, ky = local(s["lat"], s["lon"], lat0, lon0)
    height_xy = lambda X, Y: terrain.height(np.asarray(Y) / ky + lat0, np.asarray(X) / kx + lon0)
    h = smooth(s["alt"], smooth_s)
    dist = along(s)
    dx, dy = shifts()
    whole = best_shift(x, y, h, height_xy, dx, dy, smooth_s)
    wins = []
    sx, sy, n = np.zeros(len(s["t"])), np.zeros(len(s["t"])), np.zeros(len(s["t"]))
    for a, b in windows(dist, window_m):
        m = (dist >= a) & (dist <= b)
        if m.sum() < 3 * smooth_s:
            continue
        r = best_shift(x[m], y[m], h[m], height_xy, dx, dy, smooth_s)
        r.update(start_m=a, end_m=b, trusted=confident(r), nonsense=nonsense(r))
        wins.append(r)
        if r["trusted"]:
            sx[m] += r["dx"]
            sy[m] += r["dy"]
            n[m] += 1
    n1 = np.maximum(n, 1)
    return dict(whole=whole, windows=wins, shift_x=sx / n1, shift_y=sy / n1, x=x, y=y, lat0=lat0, lon0=lon0,
                kx=kx, ky=ky)


# ------------------------------------------------------------------------------------------- truth: the controls

def official_times(folder, path=None):
    """dict(start_utc, cumulative) from --oficialni or the ORIS answers in tests/fixtures/oris."""
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    if folder not in ORIS:
        return None
    from webapp import oris
    class_id, date = ORIS[folder]
    with open(os.path.join(HERE, "tests", "fixtures", "oris", f"getSplits_{class_id}.json"), encoding="utf-8") as f:
        sp = oris.parse_splits(json.load(f)["Data"], REGNO)
    return dict(start_utc=oris.start_utc(date, sp["start_local"]).isoformat(), cumulative=sp["cumulative"])


def control_truth(course_kmz, fit_path, official):
    """Control circles of the map in the order of the official punches: (lat, lon of the circles, punch seconds of
    the recording clock incl. the clock difference, info). None when the official times do not fit."""
    import datetime as dt

    from oroute.course import detect_course
    from oroute.fitload import load_track
    from oroute.kmzmap import GeoMap
    from oroute.official import order_controls
    gm, tr = GeoMap.from_kmz(course_kmz), load_track(fit_path)
    u0, v0 = gm.latlon_to_px(tr["lat"][:1], tr["lon"][:1])
    det = detect_course(gm, start_hint_px=(u0[0], v0[0]))
    xy = lambda p: tuple(float(c) for c in gm.to_xy(*gm.px_to_latlon(p[0], p[1])))
    fx, fy = xy(det["finish"])
    circles = [xy(c) for c in det["controls"] if np.hypot(xy(c)[0] - fx, xy(c)[1] - fy) >= 25.0]
    order, info = order_controls(tr, gm, circles, official)
    if order is None:
        return None
    start = dt.datetime.fromisoformat(official["start_utc"])
    rec = tr["start"] if tr["start"].tzinfo else tr["start"].replace(tzinfo=dt.timezone.utc)
    t0 = (start - rec).total_seconds() + info["clock_shift_s"]
    pts, times = [], []
    for k, c in enumerate(official["cumulative"][:-1]):
        if c is None or order[k] is None:
            continue
        lat, lon = gm.from_xy(*circles[order[k]])
        pts.append((float(lat), float(lon)))
        times.append(t0 + c)
    return np.array(pts), np.array(times), info


def misses(s, found, pts, times):
    """Distance (m) from each control to the track at its punch time: before and after the shift correction."""
    lat0, lon0, kx, ky = found["lat0"], found["lon0"], found["kx"], found["ky"]
    cx, cy = (pts[:, 1] - lon0) * kx, (pts[:, 0] - lat0) * ky
    ok = (times >= s["t"][0]) & (times <= s["t"][-1])
    q = times[ok]
    px, py = np.interp(q, s["t"], found["x"]), np.interp(q, s["t"], found["y"])
    sx, sy = np.interp(q, s["t"], found["shift_x"]), np.interp(q, s["t"], found["shift_y"])
    wx, wy = found["whole"]["dx"], found["whole"]["dy"]
    return dict(before=np.hypot(px - cx[ok], py - cy[ok]), after=np.hypot(px + sx - cx[ok], py + sy - cy[ok]),
                whole=np.hypot(px + wx - cx[ok], py + wy - cy[ok]),
                mean_dx=float(np.mean(cx[ok] - px)), mean_dy=float(np.mean(cy[ok] - py)))


# ------------------------------------------------------------------------------------------------------ the runs

def analyse(name, fit_path, source, cache_root, posun=False, course=None, official=None, smooth_s=SMOOTH_S,
            dem_smooth_m=demmod.CUZK_SMOOTH_M, window_m=WINDOW_M, test_shift=None):
    rec = read_fit(fit_path)
    out = dict(name=name, file=file_facts(rec))
    _, alt = height_field(rec)
    s = per_second(rec, alt)
    if test_shift:
        # the whole track moved by a known (dx, dy) in metres, as a misplaced map would move it: the search
        # should answer about (-dx, -dy) on top of what it finds on the real track
        _, _, kx, ky = local(s["lat"][:1], s["lon"][:1], float(s["lat"][0]), float(s["lon"][0]))
        s["lat"], s["lon"] = s["lat"] + test_shift[1] / ky, s["lon"] + test_shift[0] / kx
        out["test_shift"] = list(test_shift)
    terrain = load_terrain(s, source, os.path.join(cache_root, name), dem_smooth_m)
    out["dem"] = terrain.source
    out["vs_dem"] = compare(s, terrain)
    if posun:
        found = search(s, terrain, smooth_s, window_m)
        w = found["windows"]
        out["shift"] = dict(
            whole=found["whole"], whole_trusted=whole_trusted(terrain.source, out["vs_dem"], found["whole"]),
            windows=len(w), trusted=sum(x["trusted"] for x in w), nonsense=sum(x["nonsense"] for x in w),
            flat=sum(x["relief"] < MIN_RELIEF_M for x in w),
            trusted_shift_m=[round(math.hypot(x["dx"], x["dy"]), 1) for x in w if x["trusted"]], detail=w)
        if course and official:
            truth = control_truth(course, fit_path, official)
            if truth is not None:
                m = misses(s, found, truth[0], truth[1])
                out["controls"] = {k: _pct(v) for k, v in m.items() if k in ("before", "after", "whole")}
                out["controls"].update(n=int(len(m["before"])), map_offset_m=[round(m["mean_dx"], 1),
                                       round(m["mean_dy"], 1)], better=int((m["after"] < m["before"] - 1).sum()),
                                       worse=int((m["after"] > m["before"] + 1).sum()))
    return out


def _pct(v):
    return dict(median=float(np.median(v)), p90=float(np.percentile(v, 90)), mean=float(np.mean(v)))


def f1(v, unit=""):
    return "" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:.1f}{unit}".replace(".", ",")


def print_tables(results):
    print("| Záznam | Hodinky | Pole | Barometr v souboru | Interval | Rozlišení | Šum 1 s | Výškopis | Posun | "
          "RMS po posunu | Drift | RMS po driftu | Sklon RMS | Korelace sklonu | Stoupání hodinky / model |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        f, v = r["file"], r["vs_dem"]
        print(f"| {r['name']} | {f['product']} | {f['field']} | {'ano' if f['barometer_listed'] else 'ne'} | "
              f"{f1(f['interval_s'], ' s')} | {f1(f['resolution_m'], ' m')} | {f1(f['noise_1s_m'], ' m')} | {r['dem']} | "
              f"{f1(v['offset_m'], ' m')} | {f1(v['rms_const_m'], ' m')} | {f1(v['drift_m_per_h'], ' m/h')} | "
              f"{f1(v['rms_drift_m'], ' m')} | {f1(v['slope_rms_pct'], ' %')} | {v['slope_corr']:.2f} | "
              f"{v['climb_baro_m']:.0f} / {v['climb_dem_m']:.0f} m |")
    sh = [r for r in results if "shift" in r]
    if not sh:
        return
    print()
    print("| Záznam | Celá stopa: posun | ostrost | věřit | Úseků | důvěryhodných | na rovině | nesmyslných | "
          "Kontroly: chyba před (medián / 90 %) | po | celou stopou | lepší / horší |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sh:
        s, c = r["shift"], r.get("controls")
        w = s["whole"]
        ctl = ("| " + " | ".join(f"{f1(c[k]['median'])} / {f1(c[k]['p90'])} m" for k in ("before", "after", "whole"))
               + f" | {c['better']} / {c['worse']} z {c['n']} |") if c else "| | | | |"
        print(f"| {r['name']} | {w['dx']:+.0f}, {w['dy']:+.0f} m | {f1(w['sharpness'])} | "
              f"{'ano' if s['whole_trusted'] else 'ne'} | {s['windows']} | "
              f"{s['trusted']} | {s['flat']} | {s['nonsense']} {ctl}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fit", nargs="*", help=".fit files")
    ap.add_argument("--zavod", nargs="*", default=[], help="races of data/ (folders with run.fit, course.kmz)")
    ap.add_argument("--dem", default="auto", choices=("auto", "cuzk", "aws"))
    ap.add_argument("--posun", action="store_true", help="also the shift search (and the controls where known)")
    ap.add_argument("--oficialni", help="JSON {start_utc, cumulative} for a single --zavod without ORIS fixture")
    ap.add_argument("--cache", default=os.path.join(HERE, "kontrola", "fit_vyska"))
    ap.add_argument("--json", help="write all numbers here")
    ap.add_argument("--hladit-s", type=int, default=SMOOTH_S, help="shift search: barometer averaged over (s)")
    ap.add_argument("--dem-hladit-m", type=float, default=demmod.CUZK_SMOOTH_M, help="ČÚZK smoothed by (m)")
    ap.add_argument("--okno-m", type=float, default=WINDOW_M, help="shift search: length of a stretch (m)")
    ap.add_argument("--zkusebni-posun", type=float, nargs=2, metavar=("DX", "DY"),
                    help="move the whole track by DX, DY metres first (does the search find it back?)")
    a = ap.parse_args()
    from tests.races import DATA
    jobs = [(os.path.splitext(os.path.basename(p))[0], p, None, None) for p in a.fit]
    for z in a.zavod:
        d = os.path.join(DATA, z)
        jobs.append((z, os.path.join(d, "run.fit"), os.path.join(d, "course.kmz"),
                     official_times(z, a.oficialni if len(a.zavod) == 1 else None)))
    results = []
    for name, fit, course, official in jobs:
        try:
            results.append(analyse(name, fit, a.dem, a.cache, a.posun, course, official, a.hladit_s, a.dem_hladit_m,
                                   a.okno_m, a.zkusebni_posun))
        except Exception as err:  # one bad file (no GPS, no elevation) must not stop the others
            print(f"{name}: {type(err).__name__}: {err}", file=sys.stderr)
    print_tables(results)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
