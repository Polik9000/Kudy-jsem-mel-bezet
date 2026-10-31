"""One personal speed model fitted on all your analysed races together.

Each run of bestroute.py saves the GPS samples of the legs you ran cleanly to
OUT/fit_samples.npz. This pools those files, weights each race by how recent it is
(half-life in days, newer races count more) and fits one SpeedModel:

- slope shape (uphill, downhill) stays from slope_prior.json (your ordinary Garmin runs),
- terrain factors are nudged from the ISOM priors toward your data, by how many
  (recency-weighted) seconds you spent in each terrain across all races,
- flat path speed is scaled so the model reproduces your total clean-leg time,
- race length: how much slower you run on a longer race (SpeedModel.dur_exp), from how far each race's
  clean legs are from the model, pulled toward Riegel's exponent (DUR_PRIOR) because a few races say
  little; then the flat speed is scaled again, now per race with its own length.

bestroute.py uses oroute/personal_model.json by default once it exists.

usage: python3 -m oroute.personal OUT.json RACE/fit_samples.npz ... [--half-life 365] [--check]
       --check also fits the model leaving each race out and predicts that race's clean legs.
"""
import argparse
import datetime as dt_
import os

import numpy as np

from .routing import route_pace
from .speedmodel import DURATION_REF_S, SpeedModel

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = 1   # what bestroute.py writes to leg_samples.npz; goes up when that changes for the same race (the web app
              # then reads the samples of every race again before "Přepočítat všechno" refits the model)
# race length: speed ~ duration ** -dur_exp. Riegel's T2 = T1 * (D2 / D1) ** 1.06 is 0.06 / 1.06 in these terms.
DUR_PRIOR = 0.057      # Riegel
DUR_SIGMA = 0.05       # how far a runner's exponent may be from Riegel's
RACE_SIGMA = 0.06      # how far one race's clean legs are from the model anyway (terrain, map, day), log units
DUR_MAX = 0.3


def load(paths):
    races = []
    for p in paths:
        d = np.load(p)
        races.append({k: d[k] for k in d.files if k not in ("title", "date")} |
                     dict(path=p, title=str(d["title"]), date=str(d["date"])))
    return races


def race_seconds(r):
    """How long the race took (race_s from bestroute; older sample files: the last sample's time since the
    start), None when the files do not say."""
    if "race_s" in r and float(r["race_s"]) > 0:
        return float(r["race_s"])
    if "tsec" in r and len(r["tsec"]):
        return float(np.max(r["tsec"]))
    return None


def leg_times(model, r):
    """Model time per clean leg on the line you ran (same measure as bestroute's "your line"), and actual."""
    t = route_pace(model.for_race(race_seconds(r)), r["line_cls"], r["line_grade"]) * r["line_d"]
    return np.array([t[r["line_leg"] == k].sum() for k in r["leg_ids"]]), r["leg_times"]


def fit(races, half_life=365.0, slope=os.path.join(HERE, "slope_prior.json"), today=None, prior=None):
    """prior: {class id: factor} to start the terrain factors from instead of the ISOM values (SpeedModel.fit)."""
    today = today or dt_.date.today()
    for r in races:
        age = (today - dt_.date.fromisoformat(r["date"])).days
        r["weight"] = 0.5 ** (max(age, 0) / half_life)
    cat = lambda k: np.concatenate([r[k] for r in races])
    w = np.concatenate([np.full(len(r["dist"]), r["weight"]) for r in races])
    model = SpeedModel.with_slope_prior(slope) if slope and os.path.exists(slope) else SpeedModel()
    if prior:
        model.factors.update(prior)
    model.fit(cat("dist"), cat("dt"), cat("cls"), cat("grade"), w=w, prior=prior)
    # scale: reproduce the (recency-weighted) total clean-leg time of all races
    tm = ta = 0.0
    for r in races:
        a, b = leg_times(model, r)
        tm += r["weight"] * a.sum()
        ta += r["weight"] * b.sum()
    model.v_flat *= tm / ta
    model.notes["clean_legs_scale"] = round(tm / ta, 3)
    fit_duration(model, races)
    model.notes["personal"] = dict(
        fitted=str(today), half_life_days=half_life,
        races=[dict(title=r["title"], date=r["date"], weight=round(r["weight"], 2),
                    clean_seconds=round(float(r["dt"].sum()))) for r in races])
    return model


def fit_duration(model, races):
    """Fit model.dur_exp from how far each race's clean legs are from the model (log of actual / model time)
    against the log of its length, with a free intercept and the exponent pulled toward DUR_PRIOR (ridge).
    One race fixes nothing but the intercept, so it gets the prior. Then v_flat is scaled so the races,
    each with its own length factor, reproduce their (recency-weighted) total clean-leg time again.
    Races without a known length are left out (dur_exp stays 0 when none has one)."""
    rows = []
    for r in races:
        d = race_seconds(r)
        if d:
            a, b = leg_times(model, r)
            if a.sum() > 0 and b.sum() > 0:
                rows.append((r["weight"], np.log(d / DURATION_REF_S), np.log(b.sum() / a.sum())))
    if not rows:
        return
    w, x, y = map(np.array, zip(*rows))
    lam = (RACE_SIGMA / DUR_SIGMA) ** 2
    A = np.array([[w.sum(), (w * x).sum()], [(w * x).sum(), (w * x * x).sum() + lam]])
    rhs = np.array([(w * y).sum(), (w * x * y).sum() + lam * DUR_PRIOR])
    b = float(np.clip(np.linalg.solve(A, rhs)[1], 0.0, DUR_MAX))
    model.dur_exp = round(b, 3)
    tm = ta = 0.0
    for r in races:
        a, t = leg_times(model, r)
        tm += r["weight"] * a.sum()
        ta += r["weight"] * t.sum()
    model.v_flat *= tm / ta
    model.notes["race_length"] = dict(
        dur_exp=model.dur_exp, prior=DUR_PRIOR, ref_s=DURATION_REF_S,
        races=[dict(minutes=round(float(np.exp(xi) * DURATION_REF_S / 60), 1),
                    slower_than_model=round(float(np.exp(yi) - 1), 3)) for xi, yi in zip(x, y)])


def check(races, half_life, slope=os.path.join(HERE, "slope_prior.json"), today=None):
    """Leave one race out, predict its clean legs. Returns rows per race."""
    rows = []
    for i, r in enumerate(races):
        others = [x for j, x in enumerate(races) if j != i]
        pooled = fit([dict(x) for x in others], half_life, slope=slope, today=today)
        own = fit([dict(r)], half_life, slope=slope, today=today)  # this race alone (in-sample, so flattering)
        prior = SpeedModel.with_slope_prior(slope) if slope and os.path.exists(slope) else SpeedModel()
        prior.v_flat, prior.dur_exp = pooled.v_flat, pooled.dur_exp  # textbook terrain factors, the pooled speed
        row = dict(title=r["title"])
        for name, m in (("pooled", pooled), ("own", own), ("textbook", prior)):
            a, b = leg_times(m, r)
            row[name] = dict(total_err=round(100 * (a.sum() - b.sum()) / b.sum(), 1),
                             leg_mae=round(100 * float(np.mean(np.abs(a - b) / b)), 1))
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("samples", nargs="+")
    ap.add_argument("--half-life", type=float, default=365.0)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    races = load(a.samples)
    model = fit(races, a.half_life)
    if a.check:
        model.notes["personal"]["leave_one_out"] = check(load(a.samples), a.half_life)
    model.save(a.out)
    print(f"v_flat {model.v_flat * 3.6:.1f} km/h (one-hour race), up_k {model.up_k}, race length exponent "
          f"{model.dur_exp} (30 min x{model.race_factor(1800):.3f}, 90 min x{model.race_factor(5400):.3f})")
    for r in model.notes["personal"]["races"]:
        print(f"  {r['date']} {r['title']}: weight {r['weight']}, {r['clean_seconds']} s clean")
    for k, o in sorted(model.notes["terrain"].items(), key=lambda kv: -kv[1]["seconds"]):
        print(f"  {k:24s} {o['seconds']:5d} s  data {o['implied']:.2f}  prior {o['prior']:.2f}  used {o['used']:.2f}"
              f"  -> {model.v_flat * o['used'] * 3.6:.1f} km/h")
    for row in model.notes["personal"].get("leave_one_out", []):
        print("  check", row)


if __name__ == "__main__":
    main()
