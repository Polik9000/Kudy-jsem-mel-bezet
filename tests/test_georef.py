"""Placing a picture of a map without a KMZ (oroute/georef.py): control circles from the picture, their
positions from the track at the official punch times, similarity transform by RANSAC + least squares."""
import math

import numpy as np
import pytest
from conftest import oris_fixture
from PIL import Image, ImageDraw
from races import inputs

from oroute import georef
from oroute.fitload import load_track
from oroute.kmzmap import GeoMap
from webapp import oris

PURPLE = (180, 70, 245)
R = 14            # circle radius in the made-up picture; 75 m across in the terrain -> 2.68 m per pixel


def picture(centres, extra=(), size=(900, 700)):
    im = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, size[0], 37):                       # some map content that is not purple
        d.line([(x, 0), (x + 120, size[1])], fill=(194, 96, 46), width=1)
    pts = list(centres) + list(extra)
    for (u, v) in pts:
        d.ellipse([u - R, v - R, u + R, v + R], outline=PURPLE, width=3)
    for (a, b) in zip(centres, centres[1:]):              # leg lines, stopping short of the circles
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > 3 * R:
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            d.line([(a[0] + ux * (R + 4), a[1] + uy * (R + 4)), (b[0] - ux * (R + 4), b[1] - uy * (R + 4))],
                   fill=PURPLE, width=2)
    return im


def ground(pts, size, scale=2.6, angle=math.radians(12), tx=300.0, ty=-200.0):
    """Where picture points lie on the ground for a known similarity transform (east, north in metres)."""
    f = dict(scale=scale, scale_y=scale, angle=angle, tx=tx, ty=ty)
    return georef.to_metres(f, size, pts)


def test_similarity_is_exact_on_exact_points():
    rng = np.random.default_rng(3)
    src = rng.uniform(-300, 300, (8, 2))
    p = (2.6, math.radians(-23), 150.0, -40.0)
    s, ang, tx, ty = georef.similarity(src, georef.apply_similarity(p, src))
    assert abs(s - 2.6) < 1e-9 and abs(ang - p[1]) < 1e-9 and abs(tx - 150) < 1e-6 and abs(ty + 40) < 1e-6
    with pytest.raises(georef.GeorefError):
        georef.similarity([[1, 1], [1, 1]], [[0, 0], [5, 5]])


def test_fit_finds_which_circle_is_which_control():
    rng = np.random.default_rng(7)
    centres = [(120, 110), (300, 90), (520, 140), (760, 100), (800, 320), (640, 380), (430, 300), (250, 420),
               (110, 560), (380, 600), (600, 590), (820, 600)]
    im = picture(centres[:-1], extra=[(60, 300), (480, 480)])     # the last control has no circle; two fakes
    truth = ground(centres, im.size)
    controls = [tuple(p + rng.normal(0, 6, 2)) for p in truth]    # GPS at the punch: 6 m noise
    controls[3] = None                                            # a missing punch
    circles, r = georef.find_circles(im)
    assert abs(r - R) <= 2 and len(circles) >= 12
    f = georef.fit(circles, controls, r, im.size)
    assert f["n"] == 10 and f["rms"] < 12 and f["shear"] < 0.05
    assert abs(f["scale"] - 2.6) / 2.6 < 0.03 and abs(math.degrees(f["angle"]) - 12) < 1.5
    # every matched control got its own circle, and the transform puts all circles where they belong
    assert sorted(k for k, _ in f["pairs"]) == [0, 1, 2, 4, 5, 6, 7, 8, 9, 10]
    got = georef.to_metres(f, im.size, centres)
    assert np.hypot(*(got - truth).T).max() < 12
    # the same as a map: KML box + rotation, read back through a KMZ
    gm = georef.geomap(im, f, 49.5, 18.2)
    assert gm.header_px == 0 and abs(gm.rot - math.degrees(f["angle"])) < 1e-9
    lat, lon = gm.px_to_latlon([c[0] for c in centres], [c[1] for c in centres])
    kx = georef.R_EARTH * math.cos(math.radians(49.5)) * math.pi / 180
    ky = georef.R_EARTH * math.pi / 180
    back = np.c_[(np.asarray(lon) - 18.2) * kx, (np.asarray(lat) - 49.5) * ky]
    assert np.hypot(*(back - got).T).max() < 0.5


@pytest.mark.needs_data
def test_kmz_written_from_a_picture_reads_like_a_livelox_one(tmp_path):
    im = picture([(100, 100), (300, 200)], size=(400, 300))
    gm = GeoMap(im, 49.51, 49.50, 18.22, 18.20, rotation=-4.5, header_px=0)
    path = str(tmp_path / "course.kmz")
    georef.write_kmz(path, im, gm)
    back = GeoMap.from_kmz(path)
    assert back.header_px == 0 and (back.W, back.H) == (400, 300)
    assert abs(back.n - 49.51) < 1e-8 and abs(back.rot + 4.5) < 1e-5
    # a Livelox export has no such mark: its title bar is skipped as before
    assert GeoMap.from_kmz(inputs("pohora")[0]).header_px == 145


def test_reasons_when_it_cannot_be_done():
    blank = Image.new("RGB", (300, 300), (255, 255, 255))
    with pytest.raises(georef.GeorefError, match="no control circles"):
        georef.find_circles(blank)
    with pytest.raises(georef.GeorefError, match="too few"):
        georef.fit([(10, 10, 14)], [(0.0, 0.0), None], 14, (300, 300))
    # circles that have nothing to do with the track
    rng = np.random.default_rng(1)
    circles = [(float(u), float(v), 14) for u, v in rng.uniform(50, 650, (10, 2))]
    controls = [tuple(p) for p in rng.uniform(-1500, 1500, (10, 2))]
    with pytest.raises(georef.GeorefError):
        georef.fit(circles, controls, 14, (700, 700))


def test_control_positions_from_the_track():
    t = np.arange(0, 100.0)
    track = dict(t=t, lat=49.5 + t * 1e-5, lon=18.2 + t * 2e-5)
    pos = georef.control_positions(track, lambda la, lo: (np.asarray(lo) * 1000, np.asarray(la) * 1000), 10.0,
                                   [20, None, 50.5, 500, 60])
    assert pos[1] is None and pos[3] is None and len(pos) == 4          # the last time is the finish
    assert abs(pos[0][0] - (18.2 + 30 * 2e-5) * 1000) < 1e-6 and abs(pos[2][1] - (49.5 + 60.5e-5) * 1000) < 1e-6


def test_loose_purple_takes_printed_magenta_but_not_map_colours():
    a = np.array([[(160, 40, 140), (200, 60, 200), (255, 255, 255), (194, 96, 46), (30, 120, 50), (0, 173, 238),
                   (35, 31, 32), (253, 190, 79)]], np.uint8)
    assert georef.loose_purple(a).tolist() == [[True, True, False, False, False, False, False, False]]


@pytest.mark.slow
@pytest.mark.parametrize("folder,class_id,date", [("pohora", 202420, "2025-05-17"), ("petrvald", 215134, "2026-03-28")])
def test_real_map_lands_where_its_kmz_says(folder, class_id, date):
    """Forget the georeference of the Livelox KMZ, find it again from the picture, the runner's track and the
    official ORIS times, and compare with what the KMZ says."""
    course = inputs(folder)[0]
    truth = GeoMap.from_kmz(course)
    track = load_track(inputs(folder)[2])
    s = oris.parse_splits(oris_fixture(f"getSplits_{class_id}.json"), "BFM0903")
    start = (oris.start_utc(date, s["start_local"]) - track["start"].replace(tzinfo=oris.dt.timezone.utc)).total_seconds()
    gm, f = georef.georeference(truth.image, track, start, s["cumulative"])
    assert f["n"] >= 0.7 * f["controls"] and f["rms"] < 20
    # the four corners of the picture and its middle land within 25 m of where the KMZ puts them
    us, vs = [0, truth.W, 0, truth.W, truth.W / 2], [145, 145, truth.H, truth.H, truth.H / 2]
    la1, lo1 = truth.px_to_latlon(us, vs)
    la2, lo2 = gm.px_to_latlon(us, vs)
    err = np.hypot((np.asarray(la1) - la2) * 111195, (np.asarray(lo1) - lo2) * 111195 * math.cos(math.radians(la1[0])))
    print(folder, "corner errors (m)", np.round(err, 1), "rms", round(f["rms"], 1), "matched", f["n"], "of", f["controls"],
          "scale", round(f["scale"], 3), "vs", round(truth.m_per_px_x, 3))
    assert err.max() < 25 and abs(f["scale"] / truth.m_per_px_x - 1) < 0.02
    assert abs(gm.rot - truth.rot) < 1.0


def test_a_screenshot_is_placed_flat_even_where_the_controls_ask_for_a_perspective():
    """GPS points that a homography fits better than the flat transform (here made so on purpose): a photo would get
    that perspective, a screenshot (straight by nature) keeps the flat fit."""
    centres = [(120, 110), (300, 90), (520, 140), (760, 100), (800, 320), (640, 380), (430, 300), (250, 420),
               (110, 560), (380, 600), (600, 590), (820, 600)]
    im = picture(centres)
    flat = ground(centres, im.size)
    # a perspective squash along the picture's x axis: up to ~20 m at the edges
    W = im.size[0]
    controls = [(x * (1 + 0.04 * (u - W / 2) / W), y) for (x, y), (u, v) in zip(flat, centres)]
    _, photo = georef.place(im, controls, 49.5, 18.2)
    gm, f = georef.place(im, controls, 49.5, 18.2, screen=True)
    assert photo["kind"] == "homography"
    assert f["kind"] == "similarity" and f.get("H") is None and not f["photo"] and gm.header_px == 0


def test_crop_frame_places_a_cut_and_scaled_part_where_the_whole_picture_was():
    size = (900, 700)
    f = dict(scale=2.6, scale_y=2.62, angle=math.radians(-7), tx=300.0, ty=-200.0)
    box = (130, 85, 730, 565)
    out = (400, 320)                                    # 600 x 480 px made 1.5 times smaller
    g = georef.crop_frame(f, size, box, out)
    pts = np.array([(130, 85), (730, 565), (400, 300), (612.5, 141.25)])
    want = georef.to_metres(f, size, pts)
    got = georef.to_metres(g, out, (pts - box[:2]) * [out[0] / 600, out[1] / 480])
    assert np.abs(got - want).max() < 1e-6
    with pytest.raises(ValueError):
        georef.crop_frame(dict(f, H=np.eye(3).tolist()), size, box, out)


def test_a_map_without_course_is_kept_without_loss(tmp_path):
    rng = np.random.default_rng(5)
    im = Image.fromarray(rng.integers(0, 256, (120, 160, 3), dtype=np.uint8))
    gm = GeoMap(im, 49.51, 49.50, 18.22, 18.20, rotation=3.0, header_px=0)
    path = str(tmp_path / "maponly.kmz")
    georef.write_kmz(path, im, gm, png=True)
    back = GeoMap.from_kmz(path)
    assert back.header_px == 0 and np.array_equal(np.asarray(back.image.convert("RGB")), np.asarray(im))
