"""Slope part of the speed model, fitted on ordinary Garmin activities (training runs, races).

Races on a mapped course are few and often flat, so the uphill/downhill shape is learned here
from every foot activity instead. Each activity is cut into 30 s windows (watch distance,
barometric altitude smoothed over 15 s); each window's speed is divided by that activity's own
median speed on the flat (|grade| < 2 %), which removes effort and surface differences between
activities. What is left is how much slower or faster you get on a slope: the *shape* of
SpeedModel.slope_mult. Terrain factors (forest, marsh...) still come from races with maps.

    python3 -m oroute.slopefit GARMIN_EXPORT.zip|FIT_FOLDER slope_prior.json [--races matches.csv]

With --races (a CSV with a fit_file column, e.g. garmin-matching/matches.csv) the uphill part is
fitted on all runs but the downhill part only on orienteering races: downhill speed depends on
footing, and training runs are mostly on paths and roads where you can let go.
"""
import argparse
import io
import json
import os
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np

WIN = 30.0
BINS = np.arange(-0.30, 0.3001, 0.025)


def activity_windows(data, name="", sports=("running",)):
    """FIT bytes -> dict(sport, start, windows[N,3] = dt, dist, dz) or None."""
    import fitdecode
    recs, sport = [], None
    try:
        with fitdecode.FitReader(io.BytesIO(data), check_crc=fitdecode.CrcCheck.DISABLED) as f:
            for fr in f:
                if not isinstance(fr, fitdecode.FitDataMessage):
                    continue
                if fr.name == "file_id" and str(fr.get_value("type", fallback="")) != "activity":
                    return None
                if fr.name in ("sport", "session"):
                    sport = str(fr.get_value("sport", fallback=sport))
                elif fr.name == "record":
                    v = {fd.name: fd.value for fd in fr.fields}
                    alt = v.get("enhanced_altitude", v.get("altitude"))
                    if v.get("timestamp") is None or v.get("distance") is None or alt is None \
                            or v.get("position_lat") is None:
                        continue
                    recs.append((v["timestamp"].timestamp(), v["distance"], alt))
    except Exception:
        return None
    if sport not in sports or len(recs) < 100:
        return None
    t, d, z = np.array(recs, float).T
    g = np.arange(t[0], t[-1] + 1)
    zs = np.convolve(np.pad(np.interp(g, t, z), 7, mode="edge"), np.ones(15) / 15, "valid")
    zt = np.interp(t, g, zs)
    out, i, n = [], 0, len(t)
    while i < n - 1:
        j = i
        while j < n - 1 and t[j + 1] - t[i] <= WIN:
            j += 1
        if j == i:
            i += 1
            continue
        dt = t[j] - t[i]
        if dt >= 0.8 * WIN and np.diff(t[i:j + 1]).max() <= 10:  # no pause inside the window
            out.append((dt, d[j] - d[i], zt[j] - zt[i]))
        i = j
    return dict(file=name, sport=sport, start=float(t[0]), windows=np.array(out)) if out else None


def _iter_fit(src):
    """Yield (name, bytes) for every .fit in a folder, a zip, or a Garmin export zip (nested zips)."""
    if os.path.isdir(src):
        for x in sorted(os.listdir(src)):
            if x.endswith(".fit"):
                yield x, open(os.path.join(src, x), "rb").read()
        return
    def walk(zf):
        for nm in zf.namelist():
            if nm.endswith(".fit"):
                yield os.path.basename(nm), zf.read(nm)
            elif nm.endswith(".zip") and "Uploaded" in nm or nm.endswith(".zip") and nm.count("/") == 0:
                yield from walk(zipfile.ZipFile(io.BytesIO(zf.read(nm))))
    yield from walk(zipfile.ZipFile(src))


def _one(args):
    return activity_windows(*args)


def load_activities(src, sports=("running",)):
    with ProcessPoolExecutor() as ex:
        acts = [a for a in ex.map(_one, ((b, n, sports) for n, b in _iter_fit(src)), chunksize=40) if a]
    return acts


def relative_samples(acts, half_life_days=365.0, now=None):
    """Return grade, relative speed (vs that activity's flat median), weight (recency), activity index."""
    now = now or max(a["start"] for a in acts)
    G, R, W, A = [], [], [], []
    for k, a in enumerate(acts):
        dt, dist, dz = a["windows"].T
        v = dist / dt
        gr = dz / np.maximum(dist, 1)
        mov = (v > 0.6) & (v < 7) & (dist > 20) & (np.abs(gr) < 0.6)  # drop stops and GPS jumps
        flat = mov & (np.abs(gr) < 0.02)
        if flat.sum() < 10:
            continue
        w = 0.5 ** ((now - a["start"]) / 86400 / half_life_days) if half_life_days else 1.0
        G.append(gr[mov]); R.append(v[mov] / np.median(v[flat])); W.append(np.full(mov.sum(), w)); A.append(np.full(mov.sum(), k))
    return np.concatenate(G), np.concatenate(R), np.concatenate(W), np.concatenate(A)


def _wmedian(x, w):
    o = np.argsort(x)
    c = np.cumsum(w[o])
    return float(x[o][np.searchsorted(c, c[-1] / 2)])


def binned_curve(grade, rel, w, min_n=15):
    """Per 2.5 % grade bin: (grade, median pace multiplier = 1/relative speed, n)."""
    rows = []
    for lo in BINS[:-1]:
        m = (grade >= lo) & (grade < lo + 0.025)
        if m.sum() >= min_n:
            rows.append((float(np.median(grade[m])), _wmedian(1 / rel[m], w[m]), int(m.sum())))
    return rows


def fit_slope(curve):
    """Grid-fit SpeedModel's slope parameters (up_k, down_gain, steep_down) to a binned curve."""
    from .speedmodel import SpeedModel
    g = np.array([c[0] for c in curve]); y = np.log([c[1] for c in curve]); wt = np.sqrt([c[2] for c in curve])
    best = None
    m = SpeedModel()
    for up_k in np.arange(1.0, 12.01, 0.1):
        m.up_k = up_k
        up = g >= 0
        e_up = np.sum(wt[up] * (np.log(m.slope_mult(g[up])) - y[up]) ** 2)
        if best is None or e_up < best[0]:
            best = (e_up, up_k)
    up_k = best[1]
    best = None
    for dg in np.arange(-1.0, 3.01, 0.1):
        for sd in np.arange(0.0, 8.01, 0.1):
            m.down_gain, m.steep_down = dg, sd
            dn = g < 0
            e = np.sum(wt[dn] * (np.log(m.slope_mult(g[dn])) - y[dn]) ** 2)
            if best is None or e < best[0]:
                best = (e, dg, sd)
    return dict(up_k=round(float(up_k), 2), down_gain=round(float(best[1]), 2), steep_down=round(float(best[2]), 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="Garmin export zip, a zip of .fit files, or a folder of .fit files")
    ap.add_argument("out", help="slope_prior.json to write")
    ap.add_argument("--sports", default="running", help="comma list of FIT sports (default running; walking/hiking have another shape)")
    ap.add_argument("--half-life", type=float, default=365, help="recency weighting in days (0 = off)")
    ap.add_argument("--races", help="CSV with a fit_file column: fit downhill on these activities only")
    a = ap.parse_args()
    acts = load_activities(a.src, tuple(a.sports.split(",")))
    now = max(x["start"] for x in acts)
    g, r, w, k = relative_samples(acts, a.half_life, now)
    curve = binned_curve(g, r, w)
    p = fit_slope(curve)
    if a.races:
        import csv
        names = {row["fit_file"] for row in csv.DictReader(open(a.races, newline="", encoding="utf-8")) if row.get("fit_file")}
        ra = [x for x in acts if x["file"] in names]
        rg, rr, rw, rk = relative_samples(ra, a.half_life, now)
        rc = binned_curve(rg, rr, rw)
        pr = fit_slope(rc)
        p.update(down_gain=pr["down_gain"], steep_down=pr["steep_down"], downhill_from_races=int(len(np.unique(rk))),
                 race_up_k=pr["up_k"],
                 race_curve=[dict(grade=round(c[0], 3), pace_mult=round(c[1], 3), n=c[2]) for c in rc])
    p.update(source=os.path.basename(a.src), sports=a.sports, activities=int(len(np.unique(k))), windows=int(len(g)),
             uphill_windows=int((g > 0.05).sum()), downhill_windows=int((g < -0.05).sum()),
             half_life_days=a.half_life, fitted=time.strftime("%Y-%m-%d"),
             curve=[dict(grade=round(c[0], 3), pace_mult=round(c[1], 3), n=c[2]) for c in curve])
    json.dump(p, open(a.out, "w", encoding="utf-8"), indent=1)
    print(f"{p['activities']} activities, {p['windows']} windows: up_k {p['up_k']}, down_gain {p['down_gain']}, "
          f"steep_down {p['steep_down']}")


if __name__ == "__main__":
    main()
