"""The kind of mistake at a control from the shape of the track, and the suggested attack point
(oroute/mistakes.py), on made-up tracks: one for every row of the table in docs/pruzkum.md part 5."""
import numpy as np

from oroute import mistakes as M
from oroute import terrain as T
from oroute.analysis import smooth_speed, stops
from webapp import texts

START, CTRL = (0.0, 0.0), (400.0, 0.0)      # the leg runs east, 400 m
V = 3.0                                     # the runner's reference speed, m/s


def track(points, speeds):
    """A track through `points`, one sample per second, at `speeds[i]` m/s on the i-th piece
    (0 = stand still for points[i+1] seconds at points[i])."""
    xs, ys = [points[0][0]], [points[0][1]]
    for (p, q), v in zip(zip(points, points[1:]), speeds):
        if v == 0:
            n = int(q)
            xs += [xs[-1]] * n
            ys += [ys[-1]] * n
            continue
        (x0, y0), (x1, y1) = (xs[-1], ys[-1]), q
        n = max(1, int(round(np.hypot(x1 - x0, y1 - y0) / v)))
        xs += list(np.linspace(x0, x1, n + 1)[1:])
        ys += list(np.linspace(y0, y1, n + 1)[1:])
    x, y = np.array(xs), np.array(ys)
    return np.arange(len(x), dtype=float), x, y


def kind(t, x, y, est_loss=120.0):
    sp = smooth_speed(t, x, y)
    leg = dict(a=0, b=len(t) - 1, est_loss=est_loss, stops=stops(t, sp, 0, len(t) - 1))
    return M.classify(t, x, y, sp, leg, START, CTRL, V)


def test_clean_leg_is_not_classified():
    assert kind(*track([START, CTRL], [V]), est_loss=10.0) is None


def test_overshoot():
    # past the control at 20 m, 120 m further, then back
    t, x, y = track([START, (400, 20), (520, 30), CTRL], [V, V, V])
    m = kind(t, x, y)
    assert m["type"] == "overshoot" and m["miss"] < 25 and m["over"] > 100 and m["back"] > 60
    assert x[m["i"]] >= 500                                      # the mark is at the far point
    assert "přeběhnutí" == texts.mistake(dict(m, at=None))["label"]


def test_circling():
    ring = [(400 + 60 * np.cos(a), 60 * np.sin(a)) for a in np.linspace(np.pi, -1.5 * np.pi, 20)]
    m = kind(*track([START] + ring + [CTRL], [V] + [2.0] * len(ring)))
    assert m["type"] == "circling" and m["turn"] >= 360 and m["time"] >= 45
    assert "hledání v kruhu" == texts.mistake(dict(m, at=None))["label"]


def test_undershoot():
    # stops 90 m before the control for 40 s, then walks in
    m = kind(*track([START, (310, 0), 40, CTRL], [V, 0, 1.5]))
    assert m["type"] == "undershoot" and 80 < m["dist"] < 100 and m["stop"] >= 30
    assert "nedoběhnutí" == texts.mistake(dict(m, at=None))["label"]


def test_drift():
    # runs 70 m beside the line for the whole leg and turns in at a right angle
    m = kind(*track([START, (80, 70), (395, 70), CTRL], [V, V, V]))
    assert m["type"] == "drift" and m["dev"] >= 65
    assert "úhyb ze směru" == texts.mistake(dict(m, at=None))["label"]


def test_relocation():
    # mid-leg: stops for 30 s 60 m off the line, then turns by about 90 degrees towards the control
    m = kind(*track([START, (150, 0), (150, -60), 30, (260, -20), CTRL], [V, V, 0, V, V]))
    assert m["type"] == "relocation" and m["stop"] >= 25 and m["turn"] >= 60
    assert "zastavení" in texts.mistake(dict(m, at=None))["label"]


def test_slow():
    m = kind(*track([START, CTRL], [1.6]))
    assert m["type"] == "slow" and m["i"] is None
    assert "pomalu" in texts.mistake(dict(m, at=None))["label"]


def test_wording_has_the_numbers_and_survives_unknown_types():
    w = texts.mistake(dict(type="overshoot", miss=18.4, over=95.0, back=71.0, at=[49.5, 18.2]))
    assert "18 m" in w["text"] and "95 m" in w["text"] and "71 s" in w["text"] and w["at"] == [49.5, 18.2]
    assert texts.mistake(None) is None and texts.mistake(dict(type=None)) is None
    assert texts.mistake(dict(type="new-kind"))["label"] == "new-kind"
    assert "křížení cest 85 m" in texts.attack(dict(kind="junction", lat=1, lon=2, dist=85.0))["label"]


def paths(shape=(300, 300)):
    cls = np.full(shape, T.FOREST, np.uint8)
    cls[149:152, 20:280] = T.PATH                 # west-east path
    cls[30:270, 99:102] = T.PATH                  # north-south path: a crossroads at (100, 150)
    cls[60:63, 100:200] = T.PATH                  # a side path: a T-junction at (100, 61)
    return cls


def test_junctions_are_found_where_paths_meet():
    found = M.junctions(paths() == T.PATH)
    near = lambda p: any(abs(u - p[0]) < 4 and abs(v - p[1]) < 4 for u, v in found)
    assert near((100, 150)) and near((100, 61)) and len(found) == 2      # ends and bends are not junctions
    assert M.junctions(np.zeros((50, 50), bool)) == []
