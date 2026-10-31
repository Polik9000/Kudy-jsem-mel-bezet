"""The joint speed model in the log of speed (tools/jointfit.py) on made-up runners with known speeds,
and the club prior for a new runner. The comparison on the real races is in docs/validace.md."""
import datetime as dt
import os
import sys

import numpy as np

from oroute import personal
from oroute import terrain as T
from oroute.speedmodel import PRIOR_FACTORS, SpeedModel

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import jointfit as J  # noqa: E402

TODAY = dt.date(2026, 10, 6)
TRUE = {T.PATH: 1.0, T.FOREST: 0.70, T.SLOW: 0.45, T.OPEN: 0.95}
V0, K_CROSS = 3.4, 1.5


def race(seed, n=2400, date="2026-09-01", classes=(T.PATH, T.FOREST, T.SLOW, T.OPEN), noise=0.12):
    """A made-up race: steps of 2 s in stretches of one terrain, speed by TRUE, slope and cross slope."""
    rng = np.random.default_rng(seed)
    cls = np.repeat(rng.choice(classes, n // 40 + 1), 40)[:n].astype(np.uint8)
    grade = np.repeat(rng.normal(0, 0.05, n // 20 + 1), 20)[:n]
    cross = np.abs(np.repeat(rng.normal(0, 0.08, n // 20 + 1), 20)[:n])
    m = SpeedModel(up_k=3.4, down_gain=0.0, steep_down=1.6)
    v = V0 * np.array([TRUE[c] for c in cls]) / m.slope_mult(grade) * np.exp(-K_CROSS * cross + rng.normal(0, noise, n))
    dt_s = np.full(n, 2.0)
    leg = np.repeat(np.arange(1, n // 200 + 2), 200)[:n]
    shares = np.zeros((n, len(T.NAMES)), np.float32)
    shares[np.arange(n), cls] = 1
    ids = np.unique(leg)
    return dict(dist=v * dt_s, dt=dt_s, cls=cls, grade=grade, cross=cross, tsec=np.cumsum(dt_s), leg=leg, shares=shares,
                title=f"race {seed}", date=date, leg_ids=ids,
                leg_times=np.array([dt_s[leg == k].sum() for k in ids]),
                line_d=v * dt_s, line_cls=cls, line_grade=grade, line_leg=leg)


SLOPE = dict(up_k=3.4, down_gain=0.0, steep_down=1.6)


def slope_file(tmp_path):
    import json
    p = tmp_path / "slope.json"
    p.write_text(json.dumps(SLOPE))
    return str(p)


def test_windows_never_cross_a_leg_and_keep_the_totals():
    r = race(1)
    w = J.windows(r, 15.0)
    assert abs(w["dt"].sum() - r["dt"].sum()) < 1e-6 and abs(w["dist"].sum() - r["dist"].sum()) < 1e-6
    assert np.all(w["dt"] <= 16.0) and len(w["dt"]) < len(r["dt"]) / 6
    assert np.allclose(w["S"].sum(1), 1.0, atol=1e-5)
    one = J.windows(r, 0)
    assert len(one["dt"]) == len(r["dt"])


def test_joint_fit_recovers_known_factors_and_cross_slope(tmp_path):
    races = [race(s) for s in (1, 2, 3)]
    j = J.fit(races, slope=slope_file(tmp_path), today=TODAY, cross=True)
    for c, f in TRUE.items():
        assert abs(j.model.factors[c] / f - 1) < 0.06, (T.NAMES[c], j.model.factors[c])
    assert abs(j.k_cross - K_CROSS) < 0.35 and j.k_tired == 0.0
    assert abs(j.model.v_flat / V0 - 1) < 0.08
    # terrain nobody ran in stays at the ISOM value, with the uncertainty of the prior
    assert abs(j.model.factors[T.MARSH] - PRIOR_FACTORS[T.MARSH]) < 1e-6
    assert j.se["marsh"] > 0.2 > j.se["forest (runnable)"]
    assert j.model.notes["terrain"]["forest (runnable)"]["seconds"] > 1000
    # without the cross term the missing slowdown is spread over the factors; the fit still runs
    plain = J.fit(races, slope=slope_file(tmp_path), today=TODAY)
    assert plain.k_cross == 0.0 and plain.model.factors[T.FOREST] < 0.8


def test_little_data_stays_near_the_prior_and_a_club_prior_replaces_isom(tmp_path):
    few = race(5, n=400, classes=(T.PATH, T.SLOW))               # 5 minutes of data in light green
    lots = race(6, n=4000, classes=(T.PATH, T.SLOW))
    a = J.fit([few], slope=slope_file(tmp_path), today=TODAY).model.factors[T.SLOW]
    b = J.fit([lots], slope=slope_file(tmp_path), today=TODAY).model.factors[T.SLOW]
    assert abs(b - TRUE[T.SLOW]) < abs(a - TRUE[T.SLOW]) + 0.02 and PRIOR_FACTORS[T.SLOW] >= a > TRUE[T.SLOW] - 0.03
    club = J.fit([few], slope=slope_file(tmp_path), today=TODAY, prior={T.MARSH: 0.3}).model.factors
    assert abs(club[T.MARSH] - 0.3) < 1e-6 and abs(club[T.WALK] - PRIOR_FACTORS[T.WALK]) < 1e-6


def test_leave_one_race_out_runs_for_every_variant(tmp_path):
    races = [race(s, n=1200) for s in (1, 2, 3)]
    res = J.check(races, today=TODAY, slope=slope_file(tmp_path))
    assert list(res) == list(J.VARIANTS)
    for name, v in res.items():
        assert len(v["rows"]) == 3 and v["leg_mae"] < 25, name
    # the data were made with a cross slope: the variant that models it predicts the legs best
    assert res["... + příčný sklon"]["leg_mae"] <= min(v["leg_mae"] for v in res.values()) + 0.3


def test_stepwise_model_takes_a_club_prior_too(tmp_path):
    few = race(7, n=300, classes=(T.PATH, T.FOREST))
    isom = personal.fit([dict(few)], slope=slope_file(tmp_path), today=TODAY)
    club = personal.fit([dict(few)], slope=slope_file(tmp_path), today=TODAY, prior={T.FOREST: 0.5})
    # 10 minutes in the forest: the factor sits between the data (0.70) and the prior it started from
    assert club.factors[T.FOREST] < isom.factors[T.FOREST]
    assert club.notes["terrain"]["forest (runnable)"]["prior"] == 0.5
    assert isom.notes["terrain"]["forest (runnable)"]["prior"] == PRIOR_FACTORS[T.FOREST]
