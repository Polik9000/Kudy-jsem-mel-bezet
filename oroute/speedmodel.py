"""Runner speed model: how many seconds per metre for a given terrain class and slope.

Kept separate on purpose: everything else only calls `SpeedModel.pace(cls, grade)`,
so this can be replaced by a model fitted on a full Garmin export later.

pace = 1 / (v_flat * terrain_factor[cls]) * slope_mult(grade)

- v_flat: speed on a path on flat ground (m/s), fitted to the runner.
- terrain_factor: speed on that terrain relative to a path. Priors follow the ISOM
  guidance (light green 60-80 % of runnable forest, green 20-60 %, dark green < 20 %),
  then nudged toward what the runner's own GPS shows (shrunk by how much data there is).
- slope_mult: uphill costs `up_k` metres of flat running per metre of climb
  (Naismith-style; typical runners ~8-10, strong climbers less). Gentle downhill is a
  bit faster than flat, steep downhill (> 10 %) gets slower again.
  `SpeedModel.with_slope_prior("slope_prior.json")` takes these three numbers from the
  runner's own Garmin activities (see slopefit.py) instead of the textbook values; fit()
  then leaves them alone, because one race has far fewer hills than a year of training.
- race length: on a long race you run every metre a bit slower than on a short one (you pace yourself
  from the start; the speed does not drop during the race, docs/validace.md). The speed of a race that
  takes D seconds is v_flat * (D / DURATION_REF_S) ** -dur_exp, so v_flat is the speed of a one-hour
  race. dur_exp is fitted across your races (oroute/personal.py) from Riegel's prior;
  `for_race(D)` gives the model of one race with that factor folded into v_flat.
"""
import json

import numpy as np

from . import terrain as T

PRIOR_FACTORS = {
    T.PATH: 1.00, T.OPEN: 0.85, T.ROUGH_OPEN: 0.78, T.FOREST: 0.75, T.UNDERGROWTH: 0.60,
    T.SLOW: 0.55, T.MARSH: 0.45, T.WALK: 0.30, T.FIGHT: 0.10,
    T.WATER: 0.0, T.OOB: 0.0, T.BUILDING: 0.0,
}


DURATION_REF_S = 3600.0   # v_flat is the speed of a race this long

PRIOR_SIGMA = 0.25     # how far a runner's terrain factor typically is from the ISOM value (log scale)
INDEPENDENT_S = 15.0   # seconds of running that count as one independent observation of the speed


def wmedian(x, w):
    """Weighted median (plain median when all weights are equal)."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    o = np.argsort(x)
    c = np.cumsum(w[o])
    return float(x[o][np.searchsorted(c, 0.5 * c[-1])])


class SpeedModel:
    def __init__(self, v_flat=3.5, up_k=9.0, down_gain=2.5, steep_down=3.0, factors=None, notes=None,
                 dur_exp=0.0):
        self.v_flat = v_flat
        self.dur_exp = dur_exp
        self.up_k = up_k
        self.down_gain = down_gain
        self.steep_down = steep_down
        self.factors = dict(PRIOR_FACTORS if factors is None else factors)
        self.notes = notes or {}
        self.slope_from = self.notes.get("slope_from")  # set when slope comes from slope_prior.json

    @classmethod
    def with_slope_prior(cls, path, **kw):
        d = json.load(open(path, encoding="utf-8"))
        m = cls(up_k=d["up_k"], down_gain=d["down_gain"], steep_down=d["steep_down"], **kw)
        m.slope_from = m.notes["slope_from"] = dict(
            file=path, activities=d.get("activities"), uphill_windows=d.get("uphill_windows"),
            downhill_from_races=d.get("downhill_from_races"), fitted=d.get("fitted"))
        return m

    # --- core -----------------------------------------------------------------
    def race_factor(self, race_s):
        """Speed of a race that takes race_s seconds relative to a one-hour race (1 when unknown)."""
        if not race_s or race_s <= 0 or not self.dur_exp:
            return 1.0
        return float((race_s / DURATION_REF_S) ** -self.dur_exp)

    def for_race(self, race_s):
        """The model of one race: the race-length factor folded into v_flat (and dur_exp 0, so it is never
        applied twice when this model is saved and loaded again)."""
        m = SpeedModel(self.v_flat * self.race_factor(race_s), self.up_k, self.down_gain, self.steep_down,
                       self.factors, json.loads(json.dumps(self.notes)))
        m.slope_from = self.slope_from
        if self.dur_exp and race_s:
            m.notes["race_length"] = dict(race_s=round(float(race_s)), dur_exp=self.dur_exp,
                                          factor=round(self.race_factor(race_s), 3), v_flat_1h=self.v_flat)
        return m

    def slope_mult(self, grade):
        g = np.clip(np.asarray(grade, float), -1, 1)
        d = -g
        down = np.where(d <= 0.10, 1 - self.down_gain * d,
                        1 - self.down_gain * 0.10 + self.steep_down * (d - 0.10))
        return np.where(g >= 0, 1 + self.up_k * g, down)

    def factor_array(self, cls):
        lut = np.zeros(256)
        for c, f in self.factors.items():
            lut[c] = f
        return lut[np.asarray(cls, np.uint8)]

    def pace(self, cls, grade=0.0):
        """Seconds per metre; inf where the terrain is impassable."""
        f = self.factor_array(cls)
        with np.errstate(divide="ignore"):
            p = np.where(f > 0, 1.0 / (self.v_flat * np.maximum(f, 1e-9)), np.inf)
        return p * self.slope_mult(grade)

    # --- fitting --------------------------------------------------------------
    def fit(self, dist, dt, cls, grade, min_speed=0.3, shrink_s=300.0, w=None, prior=None):
        """Fit to GPS samples (one per track step). dist m, dt s, cls terrain id, grade dz/dist.

        Only moving samples are used. Fits v_flat (median), up_k (grid search on
        uphill samples), then nudges each terrain factor toward the data.
        w: optional weight per sample (e.g. recency when pooling several races); medians
        become weighted medians and "seconds of data" become weighted seconds.
        prior: {class id: factor} the terrain factors start from instead of the ISOM values (the average
        of the club for a runner with little data); classes not in it keep the ISOM value.
        """
        priors = {**PRIOR_FACTORS, **(prior or {})}
        dist, dt, cls, grade = map(np.asarray, (dist, dt, cls, grade))
        w = np.ones(len(dist)) if w is None else np.asarray(w, float)
        v = dist / np.maximum(dt, 1e-6)
        ok = (v > min_speed) & (v < 8) & (dt > 0) & (self.factor_array(cls) > 0)
        dist, dt, cls, grade, v, w = dist[ok], dt[ok], cls[ok], grade[ok], v[ok], w[ok]

        def vflat_for(model):
            return wmedian(v * model.slope_mult(grade) / model.factor_array(cls), w)

        # up_k: pick the value where uphill and flat samples imply the same flat speed
        best = None
        prior_k = self.up_k
        for k in np.arange(1.0, 15.01, 0.5):
            self.up_k = k
            r = np.log(v * self.slope_mult(grade) / self.factor_array(cls))
            up = grade > 0.05
            flat = np.abs(grade) < 0.03
            if up.sum() < 60 or flat.sum() < 60 or self.slope_from:
                break  # too little data, or slope already fitted on Garmin activities: keep the prior
            err = abs(wmedian(r[up], w[up]) - wmedian(r[flat], w[flat]))
            if best is None or err < best[0]:
                best = (err, k)
            self.notes.setdefault("up_k_curve", {})[float(k)] = round(float(err), 3)
        n_up = int((grade > 0.05).sum())
        self.up_k = best[1] if best else prior_k
        self.v_flat = vflat_for(self)

        # terrain factors: shrink the observed ratio toward the prior by amount of data
        obs = {}
        for c in np.unique(cls):
            m = cls == c
            secs = float((dt[m] * w[m]).sum())
            implied = wmedian(v[m] * self.slope_mult(grade[m]), w[m]) / self.v_flat
            ws = secs / (secs + shrink_s)
            prior = priors[int(c)]
            new = float(np.exp((1 - ws) * np.log(prior) + ws * np.log(max(implied, 0.05))))
            self.factors[int(c)] = new
            obs[T.NAMES[int(c)]] = dict(seconds=round(secs), implied=round(float(implied), 2), prior=prior,
                                        rel_se=round(self._rel_se(v[m] * self.slope_mult(grade[m]), dt[m], w[m], ws), 3))
        # keep path = 1.0 as the reference, so v_flat stays "speed on a flat path"
        ref = self.factors[T.PATH]
        for c in self.factors:
            self.factors[c] /= ref
        for k, o in obs.items():
            o["used"] = round(self.factors[T.NAMES.index(k)], 2)
        self.v_flat = vflat_for(self)
        self.notes.update(samples=int(ok.sum()), uphill_samples=n_up, terrain=obs)
        return self

    @staticmethod
    def _rel_se(v, dt, w, ws):
        """Relative uncertainty (1 sigma, as a fraction) of a terrain factor: the spread of the samples and how
        many independent ones there are, blended with the uncertainty of the ISOM prior by the same weight
        the factor itself uses. Only reported (notes), it does not change the model."""
        lv = np.log(np.maximum(v, 1e-3))
        med = wmedian(lv, w)
        sigma = 1.4826 * wmedian(np.abs(lv - med), w)                # robust spread of log speed
        n_eff = max(float((dt * w).sum()) / INDEPENDENT_S, 1.0)      # neighbouring GPS steps are not independent
        se_data = 1.2533 * sigma / np.sqrt(n_eff)                    # standard error of a median
        return float(np.sqrt((ws * se_data) ** 2 + ((1 - ws) * PRIOR_SIGMA) ** 2))

    # --- io -------------------------------------------------------------------
    def to_dict(self):
        return dict(v_flat=self.v_flat, up_k=self.up_k, down_gain=self.down_gain, steep_down=self.steep_down,
                    factors={T.NAMES[c]: f for c, f in self.factors.items()}, notes=self.notes,
                    dur_exp=self.dur_exp)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        d = json.load(open(path, encoding="utf-8"))
        fac = {T.NAMES.index(k): v for k, v in d["factors"].items()}
        return cls(d["v_flat"], d["up_k"], d["down_gain"], d["steep_down"], fac, d.get("notes"), d.get("dur_exp", 0.0))
