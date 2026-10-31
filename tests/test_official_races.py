"""Official ORIS times are the truth for start, controls and finish; the GPS track is cut at them."""
import json
import os

import numpy as np
import pytest
from conftest import oris_fixture
from races import GOLDEN, inputs

from oroute.course import detect_course
from oroute.fitload import load_track
from oroute.kmzmap import GeoMap
from oroute.official import order_controls
from webapp import oris

# data folder, ORIS class id, event date, official time
ORIS_RACES = [("pohora", 202420, "2025-05-17", 50 * 60 + 22), ("petrvald", 215134, "2026-03-28", 80 * 60 + 18)]


def official_for(class_id, date):
    s = oris.parse_splits(oris_fixture(f"getSplits_{class_id}.json"), "BFM0903")
    return dict(start_utc=oris.start_utc(date, s["start_local"]).isoformat(), cumulative=s["cumulative"]), s


@pytest.mark.slow
@pytest.mark.parametrize("folder,class_id,date,total", ORIS_RACES, ids=[r[0] for r in ORIS_RACES])
def test_total_is_official(analysed, folder, class_id, date, total):
    official, s = official_for(class_id, date)
    a = json.load(open(os.path.join(analysed(folder, official), "analysis.json")))
    assert a["official"]["used"], a["official"]
    assert round(a["total_time"]) == total
    # every leg time is the official split
    cum = np.cumsum([l["time"] for l in a["legs"]])
    want = np.array([c if c is not None else np.nan for c in s["cumulative"]])
    known = ~np.isnan(want)
    assert np.allclose(cum[known], want[known], atol=0.01)
    # and at those moments the runner really is at the controls
    assert a["official"]["median_miss_m"] < 25
    assert abs(a["official"]["clock_shift_s"]) <= 10
    # with official times the order of the controls comes from them (oroute.official.order_controls), not from
    # the purple lines: the course is the same one
    out = analysed(folder, official)
    with open(os.path.join(out, "course.json"), "rb") as f, open(os.path.join(GOLDEN, folder, "course.json"), "rb") as g:
        assert f.read() == g.read()


@pytest.mark.slow
@pytest.mark.parametrize("folder,class_id,date,total", ORIS_RACES, ids=[r[0] for r in ORIS_RACES])
def test_order_of_controls_from_official_times(folder, class_id, date, total):
    """Where the watch was at the official punch times says which circle is which control: the same order as
    the purple lines and the track give (tests/golden), found without searching through the lines."""
    official, _ = official_for(class_id, date)
    course, _, fit = inputs(folder)
    gm, tr = GeoMap.from_kmz(course), load_track(fit)
    u0, v0 = gm.latlon_to_px(tr["lat"][:1], tr["lon"][:1])
    det = detect_course(gm, start_hint_px=(u0[0], v0[0]))

    def xy(p):
        x, y = gm.to_xy(*gm.px_to_latlon(p[0], p[1]))
        return float(x), float(y)
    fx, fy = xy(det["finish"])
    circles = [c for c in det["controls"] if np.hypot(xy(c)[0] - fx, xy(c)[1] - fy) >= 25.0]
    order, info = order_controls(tr, gm, [xy(c) for c in circles], official)
    assert order is not None, info
    assert info["median_miss_m"] < 25 and abs(info["clock_shift_s"]) <= 10
    with open(os.path.join(GOLDEN, folder, "course.json")) as f:
        want = [c["px"] for c in json.load(f)["controls"]]
    assert [[round(circles[i][0], 1), round(circles[i][1], 1)] for i in order] == want
