"""Reading .fit files and matching activities to races (the rule of garmin-matching/match.py)."""
import datetime as dt
import io
import zipfile

import pytest
from races import inputs

from oroute import garmin

UTC = dt.timezone.utc
# data folder, race date, official time (s): from garmin-matching/matches.csv
OFFICIAL = [("azymut-e5", "2026-08-14", 76 * 60 + 57), ("azymut-e4", "2026-08-12", 55 * 60 + 7),
            ("pohora", "2025-05-17", 50 * 60 + 22), ("petrvald", "2026-03-28", 80 * 60 + 18)]


def act(start, timer, sport="running", sub_sport="generic", has_gps=True, name=""):
    return dict(start=start, timer=timer, sport=sport, sub_sport=sub_sport, has_gps=has_gps, name=name)


def scanned(folder):
    info = garmin.scan_fit(inputs(folder)[2])
    return dict(info, has_gps="first_gps" in info, name=folder)


@pytest.mark.needs_data
def test_scan_fit():
    info = garmin.scan_fit(inputs("pohora")[2])
    assert info["type"] == "activity" and info["sport"] == "running"
    assert garmin.local(info["start"]).strftime("%Y-%m-%d %H:%M") == "2025-05-17 13:18"
    assert round(info["timer"]) == 53 * 60 + 20 and abs(info["first_gps"][0] - 49.5608) < 0.01
    with open(inputs("pohora")[2], "rb") as f:
        assert garmin.scan_fit(f.read())["timer"] == info["timer"]  # bytes work like a path
    assert "error" in garmin.scan_fit(b"not a fit file")


def test_four_races_find_their_activity():
    acts = [scanned(f) for f, _, _ in OFFICIAL]
    for folder, date, time_s in OFFICIAL:
        best, conf, note = garmin.match_race(dt.date.fromisoformat(date), time_s, acts)
        assert best["name"] == folder and conf == "high", (folder, conf, note)


def test_confidence_rules():
    day = dt.date(2026, 5, 2)
    noon = dt.datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    assert garmin.match_race(day, 3000, [act(noon - dt.timedelta(days=1), 3000)])[1] == "none"
    # a warm-up jog and the race: the race is clearly closer to the official time
    best, conf, _ = garmin.match_race(day, 3000, [act(noon - dt.timedelta(hours=1), 600, name="jog"),
                                                  act(noon, 3010, name="race")])
    assert best["name"] == "race" and conf == "high"
    # two runs both near the official time: only medium
    two = [act(noon - dt.timedelta(hours=2), 3100, name="a"), act(noon, 3050, name="b")]
    assert garmin.match_race(day, 3000, two)[1] == "medium"
    # ... unless the official start time tells them apart (12:00 local = 10:00 UTC in summer)
    best, conf, _ = garmin.match_race(day, 3000, two, start_local="12:01:00")
    assert best["name"] == "b" and conf == "high"
    assert garmin.match_race(day, 3000, [act(noon, 3000, sport="cycling")])[1] == "low"
    assert garmin.match_race(day, 3000, [act(noon, 600)])[1] == "low"          # far too short
    # a recording without GPS cannot be analysed: it is not paired, and never picked over one with a track
    assert garmin.match_race(day, 3000, [act(noon, 3000, has_gps=False)])[:2] == (None, "none")
    best, conf, _ = garmin.match_race(day, 3000, [act(noon, 3000, has_gps=False, name="blind"),
                                                  act(noon + dt.timedelta(minutes=30), 3100, name="seen")])
    assert best["name"] == "seen" and conf == "high"
    assert garmin.match_race(day, None, [act(noon, 3000)])[1] == "medium"      # no official time
    assert garmin.match_race(day, 3000, [act(noon, 3000, sub_sport="treadmill")])[1] == "low"


def test_local_date_decides():
    # 23:30 UTC on 1 May is already 2 May in Prague
    late = act(dt.datetime(2026, 5, 1, 23, 30, tzinfo=UTC), 3000)
    assert garmin.match_race(dt.date(2026, 5, 2), 3000, [late])[1] == "high"
    assert garmin.match_race(dt.date(2026, 5, 1), 3000, [late])[1] == "none"


def test_iter_fit_garmin_export(tmp_path):
    """A Garmin export keeps the .fit files in zips inside the zip."""
    fit = open(inputs("pohora")[2], "rb").read()
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("user_334249566521.fit", fit)
        z.writestr("readme.txt", "x")
    export = tmp_path / "export.zip"
    with zipfile.ZipFile(export, "w") as z:
        z.writestr("DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip", inner.getvalue())
        z.writestr("DI_CONNECT/DI-Connect-Fitness/summarizedActivities.json", "[]")
        z.writestr("loose.fit", fit)
    got = dict(garmin.iter_fit(str(export)))
    assert set(got) == {"user_334249566521.fit", "loose.fit"} and got["loose.fit"] == fit


def test_place_of_the_race_decides_between_activities():
    """ORIS gives the race centre: an activity that starts far from it is not the race."""
    day = dt.date(2026, 5, 2)
    noon = dt.datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    race = [(49.8302, 18.3727), (49.8336, 18.3731)]        # centre and one named place
    home = dict(act(noon - dt.timedelta(hours=3), 3050, name="home"), lat=49.68, lon=18.35)    # 17 km away
    there = dict(act(noon, 3100, name="race"), lat=49.8310, lon=18.3740)
    # both runs fit the official time: without the place the match is only "medium"
    assert garmin.match_race(day, 3000, [home, there])[1] == "medium"
    best, conf, note = garmin.match_race(day, 3000, [home, there], near=race)
    assert best["name"] == "race" and conf == "high" and "starts at the race" in note
    # the only activity that day is far away: kept, but never trusted
    best, conf, note = garmin.match_race(day, 3000, [dict(home, timer=3000)], near=race)
    assert best["name"] == "home" and conf == "low" and "17 km from the race" in note
    # no official time (relay): the activity nearest to the race wins
    best, _, _ = garmin.match_race(day, None, [dict(home, lat=49.87, lon=18.40), there], near=race)
    assert best["name"] == "race"
    # activities without a position are matched as before
    assert garmin.match_race(day, 3000, [act(noon, 3010)], near=race)[1] == "high"
    assert round(garmin.km_between(49.0, 18.0, 49.0, 18.1), 1) == 7.3
