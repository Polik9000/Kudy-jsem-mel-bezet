"""oroute.official on a made-up track: the punches are put at the official moments."""
import datetime as dt

import numpy as np

from oroute import official as off


class FakeMap:
    """1 degree = 1000 m, enough for apply()."""
    def to_xy(self, lat, lon):
        return np.asarray(lon) * 1000.0, np.asarray(lat) * 1000.0


def straight_track(n=601, every=5):
    """Runs east at 2 m/s, one sample every `every` seconds; controls at x = 200, 400, ... m."""
    t = np.arange(0, n, every, dtype=float)
    return dict(start=dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.timezone.utc), t=t, lat=np.zeros(len(t)),
                lon=2.0 * t / 1000.0, alt=np.zeros(len(t)), dist=2.0 * t, hr=np.full(len(t), np.nan))


POINTS = [(0.0, 0.0), (200.0, 0.0), (400.0, 0.0), (600.0, 0.0), (800.0, 0.0), (1000.0, 0.0), (1100.0, 0.0)]


def test_apply_cuts_at_official_moments():
    tr = straight_track()
    official = dict(start_utc="2026-01-01T10:00:00+00:00", cumulative=[101, 199, 302, 398, 503, 551])
    tr2, punch, info = off.apply(tr, FakeMap(), POINTS, official)
    assert info["used"] and info["clock_shift_s"] == 0
    # times that fall between samples are interpolated in, so the splits are exact
    assert [float(tr2["t"][i]) for i in punch] == [0, 101, 199, 302, 398, 503, 551]
    assert abs(tr2["lon"][punch[1]] * 1000 - 202) < 1e-6


def test_apply_finds_clock_difference():
    tr = straight_track()
    # the timing system is 20 s ahead of the watch: official start 09:59:40 for a run that starts at 10:00:00
    official = dict(start_utc="2026-01-01T09:59:40+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    tr2, punch, info = off.apply(tr, FakeMap(), POINTS, official)
    assert info["used"] and info["clock_shift_s"] == 20
    assert [float(tr2["t"][i]) for i in punch] == [0, 100, 200, 300, 400, 500, 550]


def test_apply_missing_punch_uses_gps():
    tr = straight_track()
    official = dict(start_utc="2026-01-01T10:00:00+00:00", cumulative=[100, None, 300, 400, 500, 550])
    tr2, punch, info = off.apply(tr, FakeMap(), POINTS, official)
    assert info["used"] and info["missing"] == [2]
    assert float(tr2["t"][punch[2]]) == 200  # closest GPS approach to the control at x = 400 m


def test_apply_refuses_what_does_not_fit():
    tr = straight_track()
    wrong_count = dict(start_utc="2026-01-01T10:00:00+00:00", cumulative=[100, 200, 550])
    assert off.apply(tr, FakeMap(), POINTS, wrong_count)[1] is None
    other_day = dict(start_utc="2026-01-02T10:00:00+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    _, punch, info = off.apply(tr, FakeMap(), POINTS, other_day)
    assert punch is None and "does not cover" in info["reason"]
    # right time, but the runner is nowhere near the controls at the official moments
    far = [(0.0, 0.0)] + [(x, 500.0) for x, _ in POINTS[1:-1]] + [POINTS[-1]]
    ok = dict(start_utc="2026-01-01T10:00:00+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    _, punch, info = off.apply(tr, FakeMap(), far, ok)
    assert punch is None and "from the controls" in info["reason"]


def test_apply_pads_a_watch_started_late():
    tr = straight_track()
    # official start 10 s before the recording begins: the first position is held, the total stays official
    official = dict(start_utc="2026-01-01T09:59:50+00:00", cumulative=[110, 210, 310, 410, 510, 560])
    tr2, punch, info = off.apply(tr, FakeMap(), POINTS, official)
    assert info["used"]
    assert float(tr2["t"][punch[-1]] - tr2["t"][punch[0]]) == 560


def test_partly_recorded_race_keeps_its_official_times_and_marks_the_legs_without_track():
    from oroute.analysis import analyse_legs, flag_legs
    tr = straight_track()
    # the watch was started 300 s after the start of the race: the start and the first two controls are missing
    official = dict(start_utc="2026-01-01T09:55:00+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    pts = [(-600.0, 0.0), (-400.0, 0.0), (-200.0, 0.0), (0.0, 0.0), (200.0, 0.0), (400.0, 0.0), (500.0, 0.0)]
    tr2, punch, info = off.apply(tr, FakeMap(), pts, official)
    assert info["used"] and info["no_data"] == [0, 1, 2] and info["recorded"]["start_s"] == 300
    assert [float(tr2["t"][i]) for i in punch] == [-300, -200, -100, 0, 100, 200, 250]
    gone = off.no_data_legs(info, 6)
    assert gone == {1, 2, 3}                       # the leg into the first recorded control has no track either
    x, y = FakeMap().to_xy(tr2["lat"], tr2["lon"])
    legs, _ = analyse_legs(tr2, x, y, pts, punch, no_data=gone)
    vref, rref = flag_legs(legs)
    assert abs(vref - 2.0) < 0.05 and [l["time"] for l in legs] == [100, 100, 100, 100, 100, 50]
    assert [l.get("no_data", False) for l in legs] == [True, True, True, False, False, False]
    assert legs[0]["flag_codes"] == ["no_data"] and legs[0]["est_loss"] == 0
    for l in legs:
        assert all(np.isfinite(v) for v in l.values() if isinstance(v, (int, float))), l
    # too little of the race on the recording: the official times are not used at all
    late = dict(official, start_utc="2026-01-01T09:52:00+00:00")
    assert "does not cover" in off.apply(tr, FakeMap(), pts, late)[2]["reason"]


def test_track_cut_at_closest_approaches_says_which_legs_it_does_not_show():
    import pytest

    from oroute.analysis import analyse_legs, find_punches, flag_legs, unrecorded
    from oroute.errors import InputError
    tr = straight_track()
    x, y = FakeMap().to_xy(tr["lat"], tr["lon"])
    side = [(0.0, 0.0), (200.0, 0.0), (400.0, 300.0), (600.0, 0.0), (800.0, 0.0), (1000.0, 0.0), (1100.0, 0.0)]
    punch = find_punches(tr["t"], x, y, side)
    assert unrecorded(x, y, punch, side) == {2, 3}          # the control 300 m off the track, both its legs
    assert unrecorded(x, y, find_punches(tr["t"], x, y, POINTS), POINTS) == set()
    away = [(px, py + 400.0) for px, py in POINTS]
    with pytest.raises(InputError) as e:
        unrecorded(x, y, find_punches(tr["t"], x, y, away), away, why="the recording does not cover the race")
    assert e.value.code == "track_off_course" and "does not cover" in e.value.text
    # a sprint with no leg over 60 m still has a reference speed
    short = [(40.0 * k, 0.0) for k in range(8)]
    legs, _ = analyse_legs(tr, x, y, short, find_punches(tr["t"], x, y, short))
    assert abs(flag_legs(legs)[0] - 2.0) < 0.1
