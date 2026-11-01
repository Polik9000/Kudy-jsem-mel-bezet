"""Two screenshots of Livelox, with and without the course (oroute/pair.py), on made-up screenshots of Pohora
(tools/snimek.py: the KMZ pictures zoomed, on the grey page of Livelox with its bar, list of runners and buttons)."""
import os
import sys

import numpy as np
import pytest

from oroute import georef, pair

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools"))
import snimek  # noqa: E402


@pytest.fixture(scope="module")
def pohora():
    return snimek.load(snimek.sources(["pohora"])[0], np.random.default_rng(100))


def place(m, a, b):
    return pair.place_pair(a, b, m["controls"], m["lat0"], m["lon0"])


@pytest.fixture(scope="module")
def placed(pohora):
    a, b, t = snimek.screens(pohora, 1.0)
    return a, b, t, place(pohora, a, b)


def test_the_screenshot_lands_and_only_the_map_is_kept(pohora, placed):
    a, b, t, r = placed
    assert r["reliable"] and r["notes"] == [] and not r["swapped"] and np.hypot(*r["shift"]) < 0.5
    assert r["fit"].get("H") is None and abs(r["res"] - pohora["m_per_px"]) / pohora["m_per_px"] < 0.03
    corners = georef.to_metres(r["fit"], a.size, snimek.paper_to_screen(t, pohora["corners_px"]))
    assert np.hypot(*(corners - pohora["corners_xy"]).T).max() < 30
    gm, img = r["maponly"]
    px = np.asarray(img)
    # no grey page, no bar, no list of runners: what is not the map is white (out of the map for the terrain)
    grey = (np.abs(px.astype(int) - snimek.UI["a"]["bg"]).max(-1) <= 6).mean()
    assert grey < 0.005                                 # (antialiased edges of black lines are grey too)
    assert gm.header_px == 0 and img.size == r["course"][1].size
    # the pixels kept are those of the KMZ picture without the course, where the map is (zoom 1)
    x0, y0 = r["box"][:2]
    p0 = snimek.screen_to_paper(t, [(x0, y0)])[0].astype(int)
    kmz = np.asarray(pohora["paper_maponly"].convert("RGB"))
    u, v = 700, 400                                     # a pixel in the middle of the map
    assert (np.abs(px[v, u].astype(int) - kmz[v + p0[1], u + p0[0]]) <= 2).all()
    assert 0.25 < r["accuracy"] / 10 < 6


def test_a_map_moved_between_the_two_is_put_back(pohora):
    a, b, t = snimek.screens(pohora, 1.0, shift=(15, 8))
    r = place(pohora, a, b)
    assert "shifted" in r["notes"] and np.hypot(r["shift"][0] - 15, r["shift"][1] - 8) < 1


def test_swapped_screenshots_are_swapped_back(pohora, placed):
    a, b, _, r0 = placed
    r = place(pohora, b, a)
    assert r["swapped"] and "swapped" in r["notes"]
    assert np.array_equal(np.asarray(r["maponly"][1]), np.asarray(r0["maponly"][1]))


@pytest.mark.parametrize("kind, code", [("velikost", "size"), ("priblizeni", "zoom"), ("otoceni", "zoom"),
                                        ("trat-v-bez", "course_in_maponly"), ("postupy", "routes")])
def test_pairs_that_cannot_be_used(pohora, kind, code):
    a, b, _ = snimek.bad_pair(kind, pohora)
    with pytest.raises(pair.PairError) as e:
        place(pohora, a, b)
    assert e.value.code == code


def test_the_map_without_course_of_another_race_does_not_belong(pohora):
    other = snimek.load(snimek.sources(["azymut-e5"])[0], np.random.default_rng(1))
    a, b, _ = snimek.bad_pair("jiny-zavod", pohora, other)
    with pytest.raises(pair.PairError) as e:
        place(pohora, a, b)
    assert e.value.code == "unrelated"


def test_a_coarse_screenshot_is_said_and_too_coarse_keeps_no_map(pohora):
    a, b, _ = snimek.bad_pair("malo-priblizeny", pohora)
    r = place(pohora, a, b)
    assert "coarse" in r["notes"] and r["maponly"] is not None and 2 < r["res"] <= 3
    a, b, _ = snimek.bad_pair("moc-malo-priblizeny", pohora)
    r = place(pohora, a, b)
    assert "coarse_stop" in r["notes"] and r["maponly"] is None and r["course"] is not None


def test_how_much_the_browser_zoomed_in(pohora):
    for z, lo, hi in ((1.0, 1.0, 1.25), (2.0, 1.7, 2.4)):
        _, b, t = snimek.screens(pohora, z)
        W, H = pohora["paper"].size
        box = (t["ox"], t["oy"], int(t["ox"] + W * z), int(t["oy"] + H * z))
        assert lo <= pair.zoom_of(b, box) <= hi


def test_the_map_is_found_on_another_page_layout(pohora):
    a, _, t = snimek.screens(pohora, 1.0, ui="b")
    s, k = pair.small(a)
    area = pair.map_area(s)
    W, H = pohora["paper"].size
    x0, y0, x1, y1 = (v * k[0] for v in area["box"])
    assert area["reliable"]
    # the box lies within the map picture and covers most of it (Pohora's white margin may stay out)
    assert x0 >= t["ox"] - 20 and y0 >= t["oy"] - 20 and x1 <= t["ox"] + W + 20 and y1 <= t["oy"] + H + 20
    assert (x1 - x0) * (y1 - y0) > 0.6 * W * H


@pytest.mark.parametrize("kind", ["slaba-trat", "polopruhledna-trat"])
def test_a_course_left_half_see_through_is_taken_out_not_refused(pohora, placed, kind):
    a, b, _ = snimek.bad_pair(kind, pohora)
    r = place(pohora, a, b)
    assert "faint_course" in r["notes"] and r["faint"] > 0.08
    # what is left of the course on the map kept: hardly any purple (the clean pair has none)
    left = pair.purple(np.asarray(r["maponly"][1])).mean()
    assert left < 0.0005
