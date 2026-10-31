"""The order of the controls on made-up courses: from the purple leg lines (the exact table, and the search
for courses too long for it) and from the official punch times."""
import random

import numpy as np
from test_official import POINTS, FakeMap, straight_track

from oroute import course as C
from oroute import official as off


def drawn_course(k, seed, size=1500, leave_out=()):
    """A picture with k controls scattered at random and a purple line from each to the next one.
    Returns (mask, start, controls in the order of the course, finish). leave_out: legs without a line."""
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < k + 2:
        p = rng.uniform(60, size - 60, 2)
        if all(np.hypot(*(p - q)) > 90 for q in pts):
            pts.append(p)
    mask = np.zeros((size, size), bool)
    for leg, (a, b) in enumerate(zip(pts, pts[1:])):
        if leg not in leave_out:
            n = int(np.hypot(*(b - a))) * 2
            mask[np.linspace(a[1], b[1], n).round().astype(int), np.linspace(a[0], b[0], n).round().astype(int)] = True
    return mask, tuple(pts[0]), [(float(p[0]), float(p[1]), 22.0) for p in pts[1:-1]], tuple(pts[-1])


def shuffled(controls, seed):
    out = list(controls)
    random.Random(seed).shuffle(out)
    return out


def test_table_and_search_agree_on_a_short_course():
    mask, start, controls, finish = drawn_course(9, seed=1)
    mixed = shuffled(controls, 1)
    ordered, scores = C.order_by_lines(mask, start, mixed, finish)
    assert ordered == controls and min(scores) > 0.95
    S = C._line_matrix(mask, [(start[0], start[1], 25)] + mixed + [(finish[0], finish[1], 30)])
    assert [mixed[i] for i in C._search_order(S, len(mixed))] == controls


def test_long_course_is_ordered_without_the_table_of_all_subsets():
    """30 controls: the table would need 2^30 * 30 * 16 bytes (about 500 GB)."""
    mask, start, controls, finish = drawn_course(30, seed=2)
    assert len(controls) > C.EXACT_UP_TO
    ordered, scores = C.order_by_lines(mask, start, shuffled(controls, 2), finish)
    assert ordered == controls and len(scores) == 31


def test_search_returns_every_control_when_lines_are_missing():
    """Legs without a line leave many equally good paths: the search still ends and returns every control once
    (the GPS track sorts the rest out)."""
    mask, start, controls, finish = drawn_course(26, seed=3, leave_out=(4, 5, 11, 12, 13, 20))
    mixed = shuffled(controls, 3)
    S = C._line_matrix(mask, [(start[0], start[1], 25)] + mixed + [(finish[0], finish[1], 30)])
    assert sorted(C._search_order(S, len(mixed))) == list(range(26))


# --- from the official punch times -------------------------------------------------------------------------

CIRCLES = POINTS[1:-1]                      # controls at x = 200 ... 1000 m, punched at 100 ... 500 s
MIXED = [CIRCLES[i] for i in (3, 0, 4, 1, 2)]
BACK = [1, 3, 4, 0, 2]                      # MIXED[BACK[k]] is control k + 1


def test_order_from_official_times():
    official = dict(start_utc="2026-01-01T10:00:00+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    order, info = off.order_controls(straight_track(), FakeMap(), MIXED, official)
    assert order == BACK and info["used"] and info["clock_shift_s"] == 0 and info["median_miss_m"] < 1


def test_order_from_official_times_with_another_clock_and_a_missing_punch():
    # the timing system is 20 s ahead of the watch, and the third punch is missing: it gets the circle left over
    official = dict(start_utc="2026-01-01T09:59:40+00:00", cumulative=[100, 200, None, 400, 500, 550])
    order, info = off.order_controls(straight_track(), FakeMap(), MIXED, official)
    assert order == BACK and info["clock_shift_s"] == 20


def test_order_is_not_taken_from_times_that_do_not_fit():
    tr = straight_track()
    ok = dict(start_utc="2026-01-01T10:00:00+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    assert "5 controls, 4 circles" in off.order_controls(tr, FakeMap(), MIXED[:4], ok)[1]["reason"]
    two = dict(ok, cumulative=[100, None, None, 400, 500, 550])
    assert off.order_controls(tr, FakeMap(), MIXED, two)[0] is None
    other_day = dict(ok, start_utc="2026-01-02T10:00:00+00:00")
    assert "does not cover" in off.order_controls(tr, FakeMap(), MIXED, other_day)[1]["reason"]
    far = [(x, 500.0) for x, _ in MIXED]
    order, info = off.order_controls(tr, FakeMap(), far, ok)
    assert order is None and "from the control circles" in info["reason"]


# --- the course read from a picture ------------------------------------------------------------------------

PURPLE = (180, 70, 245)
SPOTS = [(150, 560), (330, 470), (520, 560), (680, 380), (500, 200), (280, 220), (140, 130)]   # S, 1-5, F (pixels)


def printed(mpp, ring_m, bar=None, hatch=None, zero=None, size=(820, 700)):
    """A map picture with a course printed ring_m metres in circle radius at mpp metres per pixel: the start
    triangle at SPOTS[0], the controls joined by lines, the double circle of the finish. bar: a thick line
    (where the time starts, a marked route from the triangle), hatch: a box of cross-hatching (an area out of
    bounds), zero: the centre of a 0 of a control number. Returns (GeoMap, circle radius in pixels)."""
    import math

    from PIL import Image, ImageDraw

    from oroute.kmzmap import R_EARTH, GeoMap
    r = ring_m / mpp
    im = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(im)
    ring = lambda x, y, q: d.ellipse([x - q - 1.5, y - q - 1.5, x + q + 1.5, y + q + 1.5], outline=PURPLE, width=3)
    for (ax, ay), (bx, by) in zip(SPOTS, SPOTS[1:]):
        n = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / n, (by - ay) / n
        d.line([ax + ux * (r + 8), ay + uy * (r + 8), bx - ux * (r + 8), by - uy * (r + 8)], fill=PURPLE, width=3)
    sx, sy = SPOTS[0]
    d.polygon([(sx + 1.3 * r * math.sin(a), sy - 1.3 * r * math.cos(a)) for a in (0, 2.0944, 4.1888)],
              outline=PURPLE, width=3)
    for x, y in SPOTS[1:-1]:
        ring(x, y, r)
    for q in (r, 0.76 * r):
        ring(*SPOTS[-1], q)
    if bar:
        d.line(bar, fill=PURPLE, width=7)
    if hatch:
        x0, y0, x1, y1 = hatch
        w, h = x1 - x0, y1 - y0
        for k in range(-h, w, 7):
            a, b = max(k, 0), min(k + h, w)
            d.line([x0 + a, y0 + a - k, x0 + b, y0 + b - k], fill=PURPLE, width=2)
            d.line([x1 - a, y0 + a - k, x1 - b, y0 + b - k], fill=PURPLE, width=2)
    if zero:
        d.ellipse([zero[0] - 0.3 * r, zero[1] - 0.45 * r, zero[0] + 0.3 * r, zero[1] + 0.45 * r], outline=PURPLE, width=3)
    ky = R_EARTH * math.pi / 180
    kx = ky * math.cos(math.radians(50.0))
    return GeoMap(im, 50 + size[1] * mpp / 2 / ky, 50 - size[1] * mpp / 2 / ky, 18 + size[0] * mpp / 2 / kx,
                  18 - size[0] * mpp / 2 / kx), r


def read(gm, **kw):
    det = C.detect_course(gm, **kw)
    near = lambda p, q: np.hypot(p[0] - q[0], p[1] - q[1])
    found = sorted(min(range(1, 6), key=lambda k: near(c, SPOTS[k])) for c in det["controls"])
    return det, found, max((min(near(c, SPOTS[k]) for k in range(1, 6)) for c in det["controls"]), default=0.0)


def test_course_is_read_at_the_size_it_is_printed():
    # a forest map 1:10 000 (circles 37.5 m) and a sprint map 1:4 000 (12 m), with no word on where the run begins
    for mpp, ring_m in ((1.33, 37.5), (0.4, 12.0), (0.27, 12.0)):
        gm, r = printed(mpp, ring_m, zero=(380, 430))
        det, found, off_px = read(gm)
        assert found == [1, 2, 3, 4, 5] and off_px < 3, (mpp, found)
        assert np.hypot(det["finish"][0] - SPOTS[-1][0], det["finish"][1] - SPOTS[-1][1]) < 3
        assert np.hypot(det["start"][0] - SPOTS[0][0], det["start"][1] - SPOTS[0][1]) < 3
        assert abs(np.median([c[2] for c in det["controls"]]) - r) < 3


def test_start_is_the_triangle_wherever_the_recording_begins():
    # the time starts at a line a marked route away from the triangle and the watch is started there: the
    # start of the course is still the triangle; so it is when the watch was started somewhere else altogether
    gm, r = printed(1.33, 37.5, bar=[110, 650, 190, 650])
    for hint in ((150, 650), (700, 100), None):
        start = C.detect_course(gm, start_hint_px=hint)["start"]
        assert np.hypot(start[0] - SPOTS[0][0], start[1] - SPOTS[0][1]) < 3, hint


def test_hatching_is_no_control_and_a_map_without_course_has_none():
    from PIL import Image
    gm, _ = printed(0.4, 12.0, hatch=(560, 40, 780, 200))
    assert read(gm)[1] == [1, 2, 3, 4, 5]
    gm.image = Image.new("RGB", gm.image.size, (255, 255, 255))
    det = C.detect_course(gm, start_hint_px=(100, 100))
    assert det["controls"] == [] and det["finish"] is None and det["start"] is None


def test_controls_outside_the_recording_are_placed_by_the_lines():
    # the watch was started 300 s into the race: the first two punches are not on the recording
    official = dict(start_utc="2026-01-01T09:55:00+00:00", cumulative=[100, 200, 300, 400, 500, 550])
    circles = [(-400.0, 0.0), (-200.0, 0.0), (0.0, 0.0), (200.0, 0.0), (400.0, 0.0)]
    mixed = [circles[i] for i in (3, 0, 4, 1, 2)]
    order, info = off.order_controls(straight_track(), FakeMap(), mixed, official)
    assert info["used"] and order == [None, None, 4, 0, 2]
    # ... and the two circles left over go where the purple lines run
    mask, start, controls, finish = drawn_course(6, seed=3)
    assert C.fill_order(mask, start, controls, finish, [None, 1, 2, None, 4, 5]) == [0, 1, 2, 3, 4, 5]
    assert C.fill_order(mask, start, controls, finish, [0, 1, 2, 3, 4, 5]) == [0, 1, 2, 3, 4, 5]
    # a recording that shows less than half of the controls is not used
    late = dict(official, start_utc="2026-01-01T09:52:00+00:00")
    assert "does not cover" in off.order_controls(straight_track(), FakeMap(), mixed, late)[1]["reason"]
