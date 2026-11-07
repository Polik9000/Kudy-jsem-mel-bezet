"""Cutting off the start and the end of a recording where the GPS was not there yet (oroute/gpstrim.py): a jump
of the GPS near the start or the end is cut off automatically, a good track stays exactly as it is, and the runner
can turn it off or set the cut by hand on the race page."""
import datetime as dt
import glob
import json
import math
import os

import numpy as np
import pytest
from conftest import csrf
from races import DATA
from test_recompute import _fake_refit, _scripts
from test_web_races import con_of, work

from oroute import gpstrim
from oroute.fitload import load_track
from webapp import texts
from webapp.seed import seed_demo
from webapp.services import personal, runner

LAT0, LON0 = 49.68, 18.35
KX = 111320.0 * math.cos(math.radians(LAT0))


def track(x, y, t=None):
    """A track like load_track gives it from x, y in metres (one point a second unless t is given)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    t = np.arange(len(x), dtype=float) if t is None else np.asarray(t, float)
    return dict(start=dt.datetime(2026, 5, 17, 9, 0, tzinfo=dt.timezone.utc), t=t, lat=LAT0 + y / 110540.0,
                lon=LON0 + x / KX, alt=np.zeros(len(t)), dist=np.full(len(t), np.nan), hr=np.full(len(t), np.nan))


def run(n=1200, speed=3.0, noise=3.0, seed=1):
    """A run along a winding line at `speed` m/s with GPS noise of `noise` m."""
    rng = np.random.default_rng(seed)
    heading = 1.5 * np.sin(np.arange(n) / 60.0)
    x, y = np.cumsum(speed * np.cos(heading)), np.cumsum(speed * np.sin(heading))
    return x + rng.normal(0, noise, n), y + rng.normal(0, noise, n)


def test_a_good_track_is_left_as_it_is():
    for seed, noise, speed in ((1, 3.0, 3.0), (2, 6.0, 3.0), (3, 4.0, 7.5)):     # 7.5 m/s: a 27 km/h sprint
        tr = track(*run(noise=noise, speed=speed, seed=seed))
        out = gpstrim.apply(tr)
        assert not out["trim"]["head"] and not out["trim"]["tail"]
        for k in ("t", "lat", "lon"):
            assert np.array_equal(out[k], tr[k])
        assert out["start"] == tr["start"] and out["trim"]["mode"] == "auto"


def test_a_jump_at_the_start_is_cut_off():
    # 12 s of the watch wandering 220 m beside the start, then the GPS jumps to the runner (Zkouška sirén 2025)
    x, y = run()
    wx, wy = 150 + np.linspace(0, 25, 12), -170 + np.linspace(0, 20, 12)
    tr = track(np.r_[wx, x], np.r_[wy, y])
    a = gpstrim.find(tr["t"], tr["lat"], tr["lon"])
    assert a["start_s"] == 12 and a["end_s"] == tr["t"][-1] and a["start_why"]["jump_m"] > 200
    out = gpstrim.apply(tr)
    assert len(out["trim"]["head"]) == 12 and not out["trim"]["tail"]
    assert out["t"][0] == 0 and len(out["t"]) == len(tr["t"]) - 12
    assert out["start"] == tr["start"] + dt.timedelta(seconds=12)        # the clock of the track stays right
    assert out["lat"][0] == tr["lat"][12]
    assert texts.gps_trim(out["trim"]).startswith("Automaticky: začátek stopy uříznutý o 0:12 (GPS se ještě")


def test_a_jump_at_the_end_is_cut_off_and_a_gap_in_the_middle_is_not():
    x, y = run()
    t = np.arange(len(x), dtype=float)
    t[600:] += 40                                         # 40 s without GPS in the middle: 260 m in a straight line
    x[600:] += 140
    xe, ye = np.r_[x, x[-1] + 300], np.r_[y, y[-1] + 120]  # indoors after the finish: 320 m in 3 s
    tr = track(xe, ye, np.r_[t, t[-1] + 3])
    out = gpstrim.apply(tr)
    assert not out["trim"]["head"] and len(out["trim"]["tail"]) == 1
    assert out["trim"]["end_s"] == t[-1] and out["trim"]["auto"]["end_why"]["jump_m"] > 300
    assert [g["at_s"] for g in out["trim"]["gaps"]] == [599] and len(out["t"]) == len(t)
    assert "konec uříznutý o 0:03" in texts.gps_trim(out["trim"])


def test_off_and_by_hand():
    x, y = run()
    wx, wy = 150 + np.zeros(12), -170 + np.zeros(12)
    tr = track(np.r_[wx, x], np.r_[wy, y])
    off = gpstrim.apply(tr, "off")
    assert np.array_equal(off["t"], tr["t"]) and off["trim"]["mode"] == "off" and off["trim"]["auto"]["start_s"] == 12
    hand = gpstrim.apply(tr, "30:900")
    assert hand["trim"]["start_s"] == 30 and hand["trim"]["end_s"] == 900 and hand["t"][-1] == 870
    assert len(hand["trim"]["head"]) == 30 and texts.gps_trim(hand["trim"]).startswith("Ručně: začátek")
    assert gpstrim.apply(tr, ":600")["trim"]["start_s"] == 0
    assert gpstrim.parse("auto") == gpstrim.parse(None) == "auto" and gpstrim.parse("5:") == (5.0, None)
    for bad in ("nonsense", "100:120"):
        with pytest.raises(ValueError):
            gpstrim.parse(bad)


@pytest.mark.needs_data
def test_the_runs_of_the_test_races_are_not_cut():
    """The races of the regression tests: none has a GPS jump at the start or the end, so nothing of their
    analysis changes (checked on 31 races of the author's Garmin export too: only one is cut, a real jump)."""
    fits = sorted(glob.glob(os.path.join(DATA, "*", "run.fit")))
    assert fits
    for path in fits:
        tr = load_track(path)
        out = gpstrim.apply(tr)
        assert not out["trim"]["head"] and not out["trim"]["tail"], path
        assert np.array_equal(out["t"], tr["t"])


def test_runner_setting_holds_only_for_its_run():
    def info(v, activity=7):
        return dict(gps_trim=None if v is None else json.dumps(v), activity_id=activity)
    assert runner.gps_trim(info(None)) == "auto"
    assert runner.gps_trim(info(dict(activity=7, mode="off"))) == "off"
    assert runner.gps_trim(info(dict(activity=7, mode="manual", start_s=12, end_s=3000.5))) == "12.0:3000.5"
    assert runner.gps_trim(info(dict(activity=7, mode="manual", start_s=12, end_s=3000), activity=8)) == "auto"


@pytest.mark.needs_data
def test_race_page_sets_the_cut_and_the_analysis_is_done_again(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    con.execute("DELETE FROM jobs WHERE entry_id IS NOT ?", (entry,))
    con.commit()
    seen, fake = [], _scripts([])

    def run_(*cmd, on_line=None):
        fake(*cmd, on_line=on_line)
        if cmd[0] in ("analyze.py", "bestroute.py"):
            seen.append((cmd[0], cmd[cmd.index("--gps-trim") + 1]))
        if cmd[0] == "analyze.py":                 # what analyze.py writes about the cut
            path = os.path.join(cmd[3], "analysis.json")
            A = json.load(open(path))
            A["track"]["trim"] = dict(mode="auto", start_s=12.0, end_s=222.0, length_s=222.0, gaps=[],
                                      auto=dict(start_s=12.0, end_s=222.0, end_why=None,
                                                start_why=dict(jump_m=221, kmh=159, at_s=11)),
                                      head=[[49.61, 18.31, 0.0]], tail=[])
            json.dump(A, open(path, "w"))
    monkeypatch.setattr(runner, "_run", run_)
    monkeypatch.setattr(personal, "refit", _fake_refit([], [True]))
    work(app)
    assert ("analyze.py", "auto") in seen and ("bestroute.py", "auto") in seen
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert 'id="orez-gps"' in html and "GPS se ještě nechytila a pak skočila o 221 m" in html

    def send(**form):
        return client.post(f"/races/{entry}/gps-trim", data=dict(form, csrf_token=csrf(client, f"/races/{entry}")))
    seen.clear()
    assert send(mode="manual", start_s="30", end_s="200").status_code == 302
    row = con.execute("SELECT gps_trim, activity_id FROM entries WHERE id = ?", (entry,)).fetchone()
    assert json.loads(row["gps_trim"]) == dict(activity=row["activity_id"], mode="manual", start_s=30.0, end_s=200.0)
    job = con.execute("SELECT * FROM jobs WHERE entry_id = ? AND status = 'queued'", (entry,)).fetchone()
    assert job["kind"] == "analyse" and not json.loads(job["payload"]).get("routes_only")
    work(app)
    assert ("analyze.py", "30.0:200.0") in seen and ("bestroute.py", "30.0:200.0") in seen
    # back to automatic: nothing of the runner's own is kept
    send(mode="auto")
    assert con.execute("SELECT gps_trim FROM entries WHERE id = ?", (entry,)).fetchone()["gps_trim"] is None
    # bad input
    assert send(mode="cut it all").status_code == 400
    assert send(mode="manual", start_s="x", end_s="10").status_code == 400
    send(mode="manual", start_s="100", end_s="120")              # less than a minute left: refused
    assert con.execute("SELECT gps_trim FROM entries WHERE id = ?", (entry,)).fetchone()["gps_trim"] is None
