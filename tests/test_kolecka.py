"""Control circles against the number of controls in ORIS: circles cut open for a detail of the map found where the
watch was at the punch (course.find_missing), a control number read as a circle left out (course.drop_extra), a thick
ring of a map exported at high resolution not taken for the finish, and what analyze.py writes about it
(course_check)."""
import json
import math
import os
import subprocess
import sys

import numpy as np
import synthetic
from PIL import Image, ImageDraw

from oroute import course as C
from oroute.kmzmap import R_EARTH, GeoMap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# control number -> the parts of its circle (degrees) that are not printed
CUTS = {
    1: [(0, 90)],                                   # 75 % printed: read as it is
    2: [(20, 150)],                                 # 64 %: too little for detect_course, found at the punch
    5: [(30, 100), (150, 220), (270, 340)],         # 43 % in three arcs: found at the punch
    4: [(0, 120), (180, 300)],                      # 33 %: too little even there
    6: [(0, 260)],                                  # 28 %: too little even there
}


def _hints(gm, centres, off_px=(9.0, -6.0)):
    """Where the watch was at the punches: the centres a few metres off."""
    return [(x + off_px[0], y + off_px[1]) for x, y in centres]


def _race(tmp_path, cuts=CUTS):
    kmz, fit, official, centres = synthetic.build_cut("pohora", str(tmp_path / "zavod"), cuts)
    return GeoMap.from_kmz(kmz), kmz, fit, official, centres


def _matched(found, centres, within=4.0):
    return sorted(k + 1 for k, (x, y) in enumerate(centres)
                  if any(math.hypot(c[0] - x, c[1] - y) <= within for c in found))


def test_cut_circles_are_found_where_the_watch_punched(tmp_path):
    gm, _kmz, _fit, _off, centres = _race(tmp_path)
    det = C.detect_course(gm)
    read = _matched(det["controls"], centres)
    assert read == [1, 3] + list(range(7, 17))                       # 2, 4, 5 and 6 are not read
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    added, notes = C.find_missing(det["mask"], mpp, det["start"], det["controls"], det["finish"],
                                  _hints(gm, centres), len(centres))
    assert _matched(added, centres) == [2, 5]
    by_k = {n["k"]: n for n in notes}
    assert by_k[2]["found"] and by_k[5]["found"] and not by_k[4]["found"] and not by_k[6]["found"]
    assert by_k[5]["line"] >= C.MISSING_LINE and by_k[5]["cover"] < C.MISSING_ALONE
    # nothing is looked for when the number already agrees
    assert C.find_missing(det["mask"], mpp, det["start"], det["controls"], det["finish"], _hints(gm, centres),
                          len(det["controls"])) == ([], [])


def test_no_circle_is_made_up_from_numbers_lines_or_hatching(tmp_path):
    # where the watch was at a "punch" there is a control number, a crossing of leg lines, or hatching: no circle
    gm, *_ = _race(tmp_path, cuts={})
    im = gm.image.convert("RGB")
    d = ImageDraw.Draw(im)
    purple = synthetic.PURPLE
    d.text((60, 560), "10", fill=purple, font_size=40)                       # a control number
    for k in range(-60, 60, 7):                                              # hatching of an out-of-bounds area
        d.line([640 + k, 470, 700 + k, 530], fill=purple, width=2)
    d.line([300, 540, 420, 600], fill=purple, width=3)                       # two leg lines crossing
    d.line([300, 600, 420, 540], fill=purple, width=3)
    gm.image = im
    det = C.detect_course(gm)
    n = len(det["controls"])
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    spots = [(80, 580), (670, 500), (360, 570)]
    added, _notes = C.find_missing(det["mask"], mpp, det["start"], det["controls"], det["finish"], spots, n + 3)
    assert added == []


def test_a_control_number_far_from_every_punch_is_left_out():
    controls = [(100.0, 100.0, 28), (300.0, 100.0, 28), (500.0, 100.0, 28), (310.0, 400.0, 28)]   # the last: a "0"
    hints = [(105.0, 98.0), (296.0, 104.0), (503.0, 95.0)]
    assert C.drop_extra(controls, hints, 3, 1.33) == [(310.0, 400.0, 28)]
    # not when a punch is missing (the circle may be that control), nor when leaving out does not give the number
    assert C.drop_extra(controls, hints[:2] + [None], 3, 1.33) == []
    assert C.drop_extra(controls + [(700.0, 400.0, 28)], hints, 4, 1.33) == []
    assert C.drop_extra(controls[:3], hints, 3, 1.33) == []


def test_a_thick_ring_of_a_fine_map_is_no_finish():
    # a forest course exported at 0.43 m per pixel: rings of 87 px drawn 7 px thick (Bohemia 2025 E1). Each ring
    # matches several radii by itself; they were all taken for finishes and only 2 of 11 controls were read.
    mpp, r, size = 0.43, 86.0, (1900, 1500)
    spots = [(250, 1250), (500, 900), (900, 1150), (1300, 900), (1650, 1200), (1600, 500), (1150, 300),
             (650, 350), (300, 600)]
    im = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(im)
    for x, y in spots[1:-1]:
        d.ellipse([x - r, y - r, x + r, y + r], outline=synthetic.PURPLE, width=7)
    fx, fy = spots[-1]
    for q in (r * 1.15, r * 0.85):
        d.ellipse([fx - q, fy - q, fx + q, fy + q], outline=synthetic.PURPLE, width=7)
    sx, sy = spots[0]
    d.polygon([(sx + 1.3 * r * math.sin(a), sy - 1.3 * r * math.cos(a)) for a in (0, 2.0944, 4.1888)],
              outline=synthetic.PURPLE, width=7)
    ky = R_EARTH * math.pi / 180
    kx = ky * math.cos(math.radians(50.0))
    gm = GeoMap(im, 50 + size[1] * mpp / 2 / ky, 50 - size[1] * mpp / 2 / ky, 18 + size[0] * mpp / 2 / kx,
                18 - size[0] * mpp / 2 / kx)
    det = C.detect_course(gm)
    assert _matched(det["controls"], spots[1:-1], within=6) == list(range(1, 8))
    assert det["finish"] is not None and math.hypot(det["finish"][0] - fx, det["finish"][1] - fy) < 6


def _analyse(kmz, fit, out, *extra):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "analyze.py"), kmz, fit, out, "--no-images", *extra],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    with open(os.path.join(out, "analysis.json"), encoding="utf-8") as f:
        return json.load(f), r.stdout


def test_analysis_says_how_the_course_agrees_with_oris(tmp_path):
    _gm, kmz, fit, official, centres = _race(tmp_path)
    A, said = _analyse(kmz, fit, str(tmp_path / "a"), "--official", official)
    assert A["course_check"] == dict(found=12, added=2, removed=0, expected=16, source="map")
    assert A["course_version"] == C.VERSION
    assert "control 2: circle found where the watch was at the punch" in said
    # without the official times the circles are not looked for, the number of ORIS is still compared
    A, _ = _analyse(kmz, fit, str(tmp_path / "b"), "--oris-controls", "16")
    assert A["course_check"] == dict(found=12, added=0, removed=0, expected=16, source="map")
    # a course given by hand is used as it is, and its latitude and longitude are written anew from its pixels
    with open(os.path.join(tmp_path / "a", "course.json"), encoding="utf-8") as f:
        given = json.load(f)
    given["controls"] = [dict(c, lat=0.0, lon=0.0) for c in given["controls"]]
    with open(tmp_path / "given.json", "w", encoding="utf-8") as f:
        json.dump(given, f)
    A, _ = _analyse(kmz, fit, str(tmp_path / "c"), "--official", official, "--course", str(tmp_path / "given.json"))
    assert A["course_check"]["source"] == "manual" and A["course_check"]["found"] == 14
    with open(os.path.join(tmp_path / "c", "course.json"), encoding="utf-8") as f:
        assert all(abs(c["lat"] - 49.56) < 0.01 for c in json.load(f)["controls"])
    assert np.isfinite(A["total_time"])
