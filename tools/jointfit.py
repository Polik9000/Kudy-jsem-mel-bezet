"""Speed model fitted in one go in the logarithm of speed (docs/pruzkum.md part 2, improvement 1 to 4).

The fit of speedmodel.SpeedModel.fit goes step by step (flat speed, then each terrain by a median) and takes
the terrain of a GPS point from the single pixel under it. Here everything is estimated together:

    log v = log v0 + sum_c share_c * log f_c - log slope_mult(grade) - k_cross * cross - k_tired * hours + e

  share_c   how much of terrain c is around the track in the window (not one pixel: GPS is metres off)
  f_c       terrain factor against a path; pulled toward the ISOM value by a ridge penalty (a prior with
            standard deviation PRIOR_SIGMA in the log), so terrain with little data stays near the prior
  cross     how steep the hillside is across the direction of running (option)
  hours     time since the start (option: slowing down during the race)

The slope along the direction of running is not fitted here: it comes from the slope prior (ordinary Garmin
runs, oroute/slopefit.py), a race has too few hills. Samples are joined into windows of WIN_S seconds first.
The answer is a weighted ridge regression with Huber weights; its covariance gives the uncertainty of every
factor.

Every option is judged by leaving one race out (check): the other races predict the clean legs of the race
left out. docs/validace.md has the numbers that decided which options are on by default.

    python3 tools/jointfit.py RACE/leg_samples.npz ...        prints the leave-one-race-out table

A measuring tool: the app does not use it (the joint fit did not lower the error, docs/rozhodnuti.md).
"""
import argparse
import datetime as dt_
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from oroute import terrain as T  # noqa: E402
from oroute.speedmodel import INDEPENDENT_S, PRIOR_FACTORS, PRIOR_SIGMA, SpeedModel  # noqa: E402

HERE = os.path.join(ROOT, "oroute")    # slope_prior.json lives there
WIN_S = 15.0
CLASSES = [c for c, f in PRIOR_FACTORS.items() if f > 0]          # passable terrain, T.PATH first is the reference
CLEAN_LOSS = 60.0
HUBER = 1.5            # residuals beyond this many sigmas are down-weighted
CROSS_SIGMA = 2.0      # prior: k_cross is 0 +- this (per unit of slope; 0.2 slope -> +-40 % speed)
TIRED_SIGMA = 0.3      # prior: slowing per hour is 0 +- this (log units)


def load(paths, clean_only=True):
    """leg_samples.npz files of bestroute.py -> races (dicts of arrays). clean_only: keep the legs whose
    estimated loss is under CLEAN_LOSS, as the personal model does."""
    races = []
    for p in paths:
        d = np.load(p)
        r = {k: d[k] for k in d.files if k not in ("title", "date")}
        r.update(path=p, title=str(d["title"]), date=str(d["date"]))
        if clean_only:
            keep = r["leg_ids"][r["est_loss"] < CLEAN_LOSS]
            m = np.isin(r["leg"], keep)
            for k in ("dist", "dt", "cls", "grade", "leg", "cross", "tsec", "shares"):
                if k in r:
                    r[k] = r[k][m]
            lm = np.isin(r["line_leg"], keep)
            for k in ("line_d", "line_cls", "line_grade", "line_leg"):
                r[k] = r[k][lm]
            sel = np.isin(r["leg_ids"], keep)
            r["leg_times"], r["leg_ids"] = r["leg_times"][sel], r["leg_ids"][sel]
        races.append(r)
    return races


def windows(r, win_s=WIN_S, shares=True):
    """Join the steps of a race into windows of about win_s seconds (never across two legs).
    Returns dict of arrays: dist, dt, grade, cross, tsec, leg, S (window x class shares, columns CLASSES)."""
    n = len(r["dist"])
    onehot = np.zeros((n, len(T.NAMES)), np.float32)
    onehot[np.arange(n), r["cls"].astype(int)] = 1
    sh = r["shares"] if shares and "shares" in r else onehot
    cross = r["cross"] if "cross" in r else np.zeros(n)
    tsec = r["tsec"] if "tsec" in r else np.zeros(n)
    out = {k: [] for k in ("dist", "dt", "grade", "cross", "tsec", "leg", "S")}
    i = 0
    while i < n:
        j, acc = i, 0.0
        while j < n and r["leg"][j] == r["leg"][i]:
            acc += r["dt"][j]
            j += 1
            if acc >= win_s:
                break
        d = r["dist"][i:j]
        w = d / max(d.sum(), 1e-9)
        out["dist"].append(d.sum())
        out["dt"].append(r["dt"][i:j].sum())
        out["grade"].append(float((r["grade"][i:j] * w).sum()))
        out["cross"].append(float((cross[i:j] * w).sum()))
        out["tsec"].append(float((tsec[i:j] * w).sum()))
        out["leg"].append(r["leg"][i])
        out["S"].append((sh[i:j] * w[:, None]).sum(0)[CLASSES])
        i = j
    return {k: np.array(v) for k, v in out.items()}


class Joint:
    """Result of fit(): a SpeedModel plus the two optional terms and the uncertainty of the factors."""

    def __init__(self, model, k_cross=0.0, k_tired=0.0, se=None, sigma=None, n=0):
        self.model, self.k_cross, self.k_tired, self.se, self.sigma, self.n = model, k_cross, k_tired, se or {}, sigma, n

    def window_time(self, w):
        """Predicted seconds of each window of windows()."""
        m = self.model
        lf = np.log([m.factors[c] for c in CLASSES])
        S = w["S"] / np.maximum(w["S"].sum(1, keepdims=True), 1e-9)
        logv = np.log(m.v_flat) + S @ lf - np.log(m.slope_mult(w["grade"])) \
            - self.k_cross * w["cross"] - self.k_tired * w["tsec"] / 3600.0
        return w["dist"] / np.exp(logv)


def fit(races, slope=os.path.join(HERE, "slope_prior.json"), half_life=365.0, today=None, win_s=WIN_S,
        shares=True, cross=False, tired=False, prior=None, prior_sigma=PRIOR_SIGMA, rescale=True):
    """Fit the joint model on races (dicts as load() gives them). prior: {class id: factor} to use instead of
    the ISOM values (the club's average for a new runner). Returns Joint."""
    today = today or dt_.date.today()
    prior = {**PRIOR_FACTORS, **(prior or {})}
    base = SpeedModel.with_slope_prior(slope) if slope and os.path.exists(slope) else SpeedModel()
    X, y, wt, kept = [], [], [], []
    for r in races:
        age = (today - dt_.date.fromisoformat(r["date"])).days
        rw = 0.5 ** (max(age, 0) / half_life)
        w = windows(r, win_s, shares)
        v = w["dist"] / np.maximum(w["dt"], 1e-6)
        ok = (v > 0.3) & (v < 8) & (w["S"].sum(1) > 0.5)
        S = w["S"][ok] / w["S"][ok].sum(1, keepdims=True)
        cols = [np.ones(ok.sum()), *S[:, 1:].T]                       # CLASSES[0] is the path: the reference
        if cross:
            cols.append(-w["cross"][ok])
        if tired:
            cols.append(-w["tsec"][ok] / 3600.0)
        X.append(np.array(cols).T)
        y.append(np.log(v[ok]) + np.log(base.slope_mult(w["grade"][ok])))
        wt.append(rw * w["dt"][ok] / INDEPENDENT_S)
        kept.append((rw, {k: v[ok] for k, v in w.items()}))
    X, y, wt = np.vstack(X), np.concatenate(y), np.concatenate(wt)
    nc = len(CLASSES) - 1
    theta0 = np.r_[np.log(base.v_flat), [np.log(prior[c] / prior[CLASSES[0]]) for c in CLASSES[1:]],
                   [0.0] * (int(cross) + int(tired))]
    prec = np.r_[0.0, [1 / prior_sigma ** 2] * nc, [1 / CROSS_SIGMA ** 2] * int(cross), [1 / TIRED_SIGMA ** 2] * int(tired)]
    theta, sigma, hub = theta0.copy(), 0.35, np.ones(len(y))
    for _ in range(6):
        W = wt * hub
        A = (X * W[:, None]).T @ X / sigma ** 2 + np.diag(prec)
        b = (X * W[:, None]).T @ y / sigma ** 2 + prec * theta0
        theta = np.linalg.solve(A, b)
        res = y - X @ theta
        sigma = max(1.4826 * float(np.median(np.abs(res - np.median(res)))), 0.05)
        hub = np.minimum(1.0, HUBER * sigma / np.maximum(np.abs(res), 1e-9))
    cov = np.linalg.inv(A)
    factors = dict(PRIOR_FACTORS)
    factors[CLASSES[0]] = 1.0
    for c, t in zip(CLASSES[1:], theta[1:1 + nc]):
        factors[c] = float(np.exp(t))
    model = SpeedModel(float(np.exp(theta[0])), base.up_k, base.down_gain, base.steep_down, factors, dict(base.notes))
    model.slope_from = base.slope_from
    k = 1 + nc
    kc = float(theta[k]) if cross else 0.0
    kt = float(theta[k + int(cross)]) if tired else 0.0
    se = {T.NAMES[c]: float(np.sqrt(cov[i + 1, i + 1])) for i, c in enumerate(CLASSES[1:])}
    se[T.NAMES[CLASSES[0]]] = float(np.sqrt(cov[0, 0]))
    seconds = {T.NAMES[c]: float((X[:, i + 1] * wt).sum() * INDEPENDENT_S) for i, c in enumerate(CLASSES[1:])}
    seconds[T.NAMES[CLASSES[0]]] = float(((1 - X[:, 1:1 + nc].sum(1)) * wt).sum() * INDEPENDENT_S)
    model.notes["joint"] = dict(sigma=round(sigma, 3), windows=int(len(y)), win_s=win_s, shares=bool(shares),
                                k_cross=round(kc, 3), k_tired=round(kt, 3))
    model.notes["terrain"] = {T.NAMES[c]: dict(seconds=round(seconds[T.NAMES[c]]), prior=PRIOR_FACTORS[c],
                                               used=round(factors[c], 2), rel_se=round(se[T.NAMES[c]], 3))
                              for c in CLASSES}
    j = Joint(model, kc, kt, se, sigma, len(y))
    if rescale:
        # as the step-by-step model does: the flat speed is set so the (recency-weighted) total time of the
        # races it learned from comes out right; a mean in the log of speed alone favours the fast windows
        tm = sum(rw * j.window_time(w).sum() for rw, w in kept)
        ta = sum(rw * w["dt"].sum() for rw, w in kept)
        model.v_flat *= tm / ta
        model.notes["joint"]["scale"] = round(tm / ta, 3)
    return j


def leg_errors(pred, r, win_s=WIN_S, shares=True):
    """(total error %, mean absolute leg error %) of a predictor on the clean legs of race r.
    pred(windows) -> seconds per window."""
    w = windows(r, win_s, shares)
    t = pred(w)
    legs = np.unique(w["leg"])
    a = np.array([t[w["leg"] == k].sum() for k in legs])
    b = np.array([w["dt"][w["leg"] == k].sum() for k in legs])
    return 100 * (a.sum() - b.sum()) / b.sum(), 100 * float(np.mean(np.abs(a - b) / b))


def old_predictor(model):
    """The step-by-step model priced the same way: the class under the point, slope along the track."""
    def pred(w):
        return Joint(model).window_time(w)
    return pred


VARIANTS = {
    "po krocích (dosavadní)": None,
    "společný odhad, okna 1 krok, třída pod bodem": dict(win_s=0, shares=False),
    "společný odhad, okna 15 s, třída pod bodem": dict(win_s=15, shares=False),
    "společný odhad, okna 15 s, podíly tříd v okolí": dict(win_s=15, shares=True),
    "... + příčný sklon": dict(win_s=15, shares=True, cross=True),
    "... + únava": dict(win_s=15, shares=True, tired=True),
    "... + příčný sklon + únava": dict(win_s=15, shares=True, cross=True, tired=True),
}


def check(races, today=None, slope=os.path.join(HERE, "slope_prior.json"), variants=VARIANTS):
    """Leave one race out for every variant. Returns {variant: dict(rows=[(title, total %, leg mae %)],
    abs_total = mean |total error|, leg_mae = mean leg error, terms)}."""
    from oroute import personal
    out = {}
    for name, opt in variants.items():
        rows, terms = [], []
        for i, r in enumerate(races):
            others = [dict(x) for j, x in enumerate(races) if j != i]
            if opt is None:
                j = Joint(personal.fit(others, slope=slope, today=today))
                tot, mae = leg_errors(j.window_time, r, WIN_S, False)
            else:
                j = fit(others, slope=slope, today=today, **opt)
                # every variant is scored on the same windows (15 s) with the terrain it uses itself
                tot, mae = leg_errors(j.window_time, r, WIN_S, opt.get("shares", True))
                terms.append((j.k_cross, j.k_tired))
            rows.append((r["title"], round(float(tot), 1), round(float(mae), 1)))
        out[name] = dict(rows=rows, abs_total=round(float(np.mean([abs(x[1]) for x in rows])), 1),
                         leg_mae=round(float(np.mean([x[2] for x in rows])), 1), terms=terms)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("samples", nargs="+", help="leg_samples.npz of the analysed races")
    ap.add_argument("--today", help="YYYY-MM-DD for the recency weights (default: today)")
    a = ap.parse_args()
    today = dt_.date.fromisoformat(a.today) if a.today else None
    res = check(load(a.samples), today=today)
    for name, v in res.items():
        print(f"{name}: mean |total error| {v['abs_total']} %, mean leg error {v['leg_mae']} %")
        for title, tot, mae in v["rows"]:
            print(f"    {title:28s} total {tot:+6.1f} %   legs {mae:5.1f} %")
        if v["terms"] and any(k or t for k, t in v["terms"]):
            print("    k_cross, k_tired per fold:", [(round(k, 2), round(t, 2)) for k, t in v["terms"]])


if __name__ == "__main__":
    main()
