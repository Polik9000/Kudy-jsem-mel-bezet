"""Race length in the personal speed model (SpeedModel.dur_exp, oroute/personal.py fit_duration) on made-up
races whose speed follows a known exponent."""
import datetime as dt
import json

import numpy as np

from oroute import personal
from oroute import terrain as T
from oroute.speedmodel import SpeedModel

TODAY = dt.date(2026, 10, 6)
SLOPE = dict(up_k=3.4, down_gain=0.0, steep_down=1.6)


def slope_file(tmp_path):
    p = tmp_path / "slope.json"
    p.write_text(json.dumps(SLOPE))
    return str(p)


def race(seed, minutes, exp, n=1200):
    """Flat path and forest; every step is run at the speed of a race `minutes` long."""
    rng = np.random.default_rng(seed)
    cls = np.repeat(rng.choice([T.PATH, T.FOREST], n // 40 + 1), 40)[:n].astype(np.uint8)
    grade = np.zeros(n)
    v = 3.4 * np.where(cls == T.PATH, 1.0, 0.7) * (minutes / 60) ** -exp * np.exp(rng.normal(0, 0.05, n))
    dt_s = np.full(n, 2.0)
    leg = np.repeat(np.arange(1, n // 200 + 2), 200)[:n]
    ids = np.unique(leg)
    return dict(dist=v * dt_s, dt=dt_s, cls=cls, grade=grade, leg=leg, title=f"race {seed}", date="2026-09-01",
                leg_ids=ids, leg_times=np.array([dt_s[leg == k].sum() for k in ids]),
                line_d=v * dt_s, line_cls=cls, line_grade=grade, line_leg=leg, race_s=minutes * 60.0)


def test_exponent_moves_from_the_prior_toward_the_data(tmp_path):
    races = [race(s, m, 0.15) for s, m in enumerate((20, 35, 50, 70, 90, 110))]
    m = personal.fit([dict(r) for r in races], slope=slope_file(tmp_path), today=TODAY)
    assert personal.DUR_PRIOR < m.dur_exp < 0.15
    # with the factor the short and the long race both come out close to what was run
    for r in (races[0], races[-1]):
        a, b = personal.leg_times(m, r)
        assert abs(a.sum() / b.sum() - 1) < 0.06


def test_one_race_keeps_the_prior_and_no_length_keeps_the_old_model(tmp_path):
    one = personal.fit([dict(race(1, 45, 0.2))], slope=slope_file(tmp_path), today=TODAY)
    assert abs(one.dur_exp - personal.DUR_PRIOR) < 0.01
    plain = {k: v for k, v in race(1, 45, 0.2).items() if k != "race_s"}
    assert personal.fit([plain], slope=slope_file(tmp_path), today=TODAY).dur_exp == 0.0


def test_for_race_is_applied_once(tmp_path):
    m = SpeedModel(v_flat=3.0, dur_exp=0.06)
    r = m.for_race(1800)
    assert abs(r.v_flat - 3.0 * 0.5 ** -0.06) < 1e-9 and r.dur_exp == 0.0
    p = tmp_path / "m.json"
    r.save(p)
    back = SpeedModel.load(p)
    assert back.for_race(5400).v_flat == r.v_flat
    assert m.race_factor(None) == 1.0 and SpeedModel(dur_exp=0.06).race_factor(3600) == 1.0
