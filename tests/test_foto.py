"""Photos of a paper map (oroute/georef.py on what a phone gives): EXIF orientation, size, light, perspective.
The made-up photos come from tools/fotka.py, where the truth is known."""
import io
import os
import sys

import numpy as np
import pytest
from PIL import Image

from oroute import georef

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fotka  # noqa: E402


def jpeg(im, orientation=1, quality=90):
    return io.BytesIO(fotka.jpeg(im, orientation, quality))


def test_photo_is_turned_upright_by_its_exif_orientation():
    im = Image.new("RGB", (600, 400), (255, 255, 255))
    im.paste((255, 0, 0), (0, 0, 100, 100))                   # red in the top left corner as the photo is seen
    for orientation in (6, 3):
        stored = fotka.displayed(im, 1).transpose(Image.ROTATE_90 if orientation == 6 else Image.ROTATE_180)
        got = georef.open_image(jpeg(stored, orientation))
        assert got.size == (600, 400)
        assert got.getpixel((20, 20))[0] > 200 and got.getpixel((20, 20))[1] < 60


def test_big_photo_is_made_smaller_on_opening():
    im = Image.new("RGB", (8400, 1200), (250, 250, 250))
    got = georef.open_image(jpeg(im))
    assert max(got.size) == georef.MAX_SIDE_PX and abs(got.size[1] - 1200 * georef.MAX_SIDE_PX / 8400) <= 1


def test_homography_is_exact_on_exact_points_and_a_mirror_is_not_sane():
    rng = np.random.default_rng(5)
    M = np.array([[2.1, -0.4, 30.0], [0.5, 1.8, -20.0], [1e-4, -2e-4, 1.0]])
    src = rng.uniform(-400, 400, (9, 2))
    got = georef.homography(src, georef.apply_h(M, src))
    assert np.abs(got - M).max() < 1e-6
    assert georef.h_sane(M, (800, 800))
    assert not georef.h_sane(np.diag([1.0, -1.0, 1.0]), (800, 800))                # mirrored
    assert not georef.h_sane(np.array([[1, 0, 0], [0, 0.3, 0], [0, 0, 1.0]]), (800, 800))   # squashed too much


def test_light_is_evened_out_under_a_shadow_and_a_tint():
    im = np.full((300, 400, 3), 250, np.float32)
    im[140:160, 50:350] = (180, 70, 245)                                  # a purple band across both halves
    light = np.where(np.arange(400) < 200, 1.0, 0.45)[None, :, None] * np.array([1.0, 0.85, 0.7])   # warm, shadow
    photo = Image.fromarray((im * light).astype(np.uint8))
    assert not georef.loose_purple(photo)[150, 300]                        # in the shadow it is not purple any more
    flat = georef.flatten_light(photo)
    assert georef.loose_purple(flat)[150, 100] and georef.loose_purple(flat)[150, 300]
    paper = np.asarray(flat)[[30, 30], [100, 300]].astype(int)
    assert (paper > 225).all() and np.ptp(paper) < 20                       # white paper in both halves


@pytest.fixture(scope="module")
def pohora():
    return fotka.load(fotka.sources(["pohora"])[0], np.random.default_rng(100))


def photo(m, **p):
    """A small made-up photo (1 Mpx), opened as the app opens it, and the truth in its pixels."""
    params = dict(fotka.BASE, mpx=1.0, **p)
    im, o, ph, q = fotka.make_photo(m, params, seed=3)
    opened = georef.open_image(jpeg(im, o, q))
    small = fotka._small(fotka.displayed(im, o)), fotka._small(im)
    return (opened, fotka.to_opened(ph.forward(m["ctrl_px"]), ph, o, *small, opened),
            fotka.to_opened(ph.forward(m["corners_px"]), ph, o, *small, opened))


def test_sheet_corners_are_found_on_the_table(pohora):
    im, _, corners = photo(pohora, tilt=20, rot=30, light=0.6)
    quad = georef.paper_quad(im)
    assert quad is not None
    # every true corner of the sheet has a found corner within 1 % of the photo's size
    d = np.hypot(*(np.asarray(quad)[:, None, :] - corners[None, :, :]).transpose(2, 0, 1))
    assert d.min(0).max() < 0.01 * max(im.size)
    # no table around the map: no sheet
    assert georef.paper_quad(im.crop((200, 150, 900, 650))) is None


def test_slanted_photo_in_a_shadow_lands_and_is_straightened(pohora):
    im, ctrl, corners = photo(pohora, tilt=25, rot=200, light=0.5, kelvin=5000, bg=0.25)
    gm, f = georef.place(im, pohora["controls"], pohora["lat0"], pohora["lon0"])
    assert f["kind"] == "paper" and f["n"] >= 15 and f["rms"] < 20
    err = np.hypot(*(georef.to_metres(f, im.size, corners) - pohora["corners_xy"]).T)
    assert err.max() < 40
    # the straightened picture of the KMZ: north up, and the circles where the controls are on the ground
    assert gm.rot == 0 and gm.header_px == 0
    to_ll = lambda xy: (pohora["lat0"] + xy[:, 1] / gm.ky, pohora["lon0"] + xy[:, 0] / (gm.kx))
    u, v = gm.latlon_to_px(*to_ll(pohora["ctrl_xy"]))
    circles, r = georef.find_circles(gm.image, photo=True)
    c = np.array([x[:2] for x in circles])
    near = np.hypot(c[None, :, 0] - np.asarray(u)[:, None], c[None, :, 1] - np.asarray(v)[:, None]).min(1)
    assert np.median(near) < 0.5 * r and (near < 1.5 * r).mean() > 0.8


def test_sprint_map_with_smaller_circles():
    """A control circle of a sprint map is 24 m across (6 mm at 1:4 000), not 75 m: the scale read from the
    circle size is three times off, and the pairs are tried with the other sizes."""
    from test_georef import R, ground, picture
    rng = np.random.default_rng(11)
    centres = [(120, 110), (300, 90), (520, 140), (760, 100), (800, 320), (640, 380), (430, 300), (250, 420),
               (110, 560), (380, 600), (600, 590), (820, 600)]
    im = picture(centres)
    scale = 24.0 / (2 * R)
    controls = [tuple(p + rng.normal(0, 3, 2)) for p in ground(centres, im.size, scale=scale)]
    circles, r = georef.find_circles(im)
    f = georef.fit(circles, controls, r, im.size)
    assert f["n"] == 12 and abs(f["scale"] / scale - 1) < 0.03


def test_a_bent_sheet_maps_both_ways():
    """to_metres and from_metres of a fit with a bent sheet (paper-bent) are each other's inverse."""
    Q = georef.homography([(-400, -300), (400, -300), (400, 300), (-400, 300)],
                          [(-390, -310), (405, -295), (395, 305), (-410, 290)])
    S = np.array([[2.0, -0.3, 120.0], [0.3, 2.0, -40.0], [0, 0, 1]])
    f = dict(Q=Q.tolist(), S=S.tolist(), bend=[0, 0.03, 400, 300])
    px = np.array([(10.0, 20.0), (700.0, 100.0), (420.0, 560.0), (790.0, 590.0)])
    back = georef.from_metres(f, (800, 600), georef.to_metres(f, (800, 600), px))
    assert np.abs(back - px).max() < 1e-6


@pytest.mark.slow
@pytest.mark.parametrize("name", ["pohora", "petrvald"])
def test_the_whole_set_of_made_up_photos(name):
    """Every case of tools/fotka.py (each distortion alone and the combinations) on a map with the real track at
    the official times, at 3 Mpx: how many land, and how far their corners are from the truth. The full set (eight
    maps, 12 Mpx) is kontrola/foto/sada.sh, an hour and a half."""
    m = fotka.load(fotka.sources([name])[0], np.random.default_rng(100))
    rows = []
    for j, (case, p) in enumerate(fotka.cases()):
        row = fotka.run_one(m, dict(p, mpx=min(p["mpx"], 3.0)), seed=j)
        rows.append((case, row))
    placed = [r for _, r in rows if r["ok"]]
    good = [r for r in placed if r["corner_max"] <= fotka.GOOD_CORNER_M]
    print(name, [(c, r["ok"], r["corner_max"]) for c, r in rows])
    assert len(placed) >= 0.9 * len(rows) and len(good) >= 0.8 * len(rows)
    assert all(r["ctrl_median"] <= 20 for r in placed)
