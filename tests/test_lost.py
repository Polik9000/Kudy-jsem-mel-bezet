"""oroute/lost.py: the advice for a runner lost at a control, on made-up scenes of 1 m cells with hand-worked numbers.
Rows grow to the south, columns to the east; a bearing is clockwise from north (up)."""
import math

import numpy as np
import pytest
from races import inputs

from oroute import lost
from webapp import texts


def scene(n=300, ctrl=(150.0, 150.0), prev=None, points=(), attack=None):
    """An empty scene n x n cells of 1 m with the control at ctrl (col, row); add lines with S[kind][...] = True."""
    S = dict(shape=[n, n], s=1, cell=1.0, origin=[50.0, 18.0], A=[[0.0, -1.0], [1.0, 0.0], [ctrl[0], ctrl[1]]],
             ctrl=list(ctrl), prev=list(prev) if prev else None, points=list(points), k=3)
    S["imp"] = np.zeros((n, n), bool)
    for k in lost.LINES:
        S[k] = np.zeros((n, n), bool)
    if attack:
        S["attack"] = attack
    return S


def pick(a):
    return a["helpers"][a["pick"]]


# ------------------------------------------------------------------------------------------ bearings
def test_bearings_and_compass_words():
    assert lost.bearing(1, -1) == pytest.approx(45.0)
    assert lost.bearing(0, 1) == pytest.approx(180.0)
    assert lost.bearing(-1, 0) == pytest.approx(270.0)
    assert lost.bearing(0, -1) == pytest.approx(0.0)
    assert texts.compass(22.4) == "sever"
    assert texts.compass(22.6) == "severovýchod"
    assert texts.compass(359.0) == "sever"
    assert texts.compass(200.0) == "jih"
    assert texts.compass(250.0) == "západ"
    assert texts.about(57) == 55 and texts.about(123) == 120 and texts.about(2) == 5


def test_distance_and_bearing_from_the_runner_and_from_the_control():
    # a path east to west 60 m north of the control; the runner 60 m south of it: the path is 120 m north of them
    S = scene()
    S["path"][90, :] = True
    a = lost.advise(S, (150.0, 210.0), 25.0)
    h = pick(a)
    assert h["kind"] == "path" and h["sure"]
    assert h["dist"] == pytest.approx(120.0, abs=1.0) and h["az"] == pytest.approx(0.0, abs=1.0)
    assert h["cdist"] == pytest.approx(60.0, abs=1.0) and h["caz"] == pytest.approx(0.0, abs=1.0)
    assert h["link"]["type"] == "direct"
    assert h["link"]["dist"] == pytest.approx(60.0, abs=1.0) and h["link"]["az_off"] == pytest.approx(180.0, abs=1.0)


# ------------------------------------------------------------------------------------------ which feature
def test_the_most_certain_wins_not_the_nearest():
    # a long path 60 m north, a knoll 30 m south: from a circle of 50 m the knoll is easily missed, the path never
    knoll = dict(kind="knoll", at=[150.0, 180.0], r=8.0, base=0.6, on=[])
    S = scene(points=[knoll])
    S["path"][90, :] = True
    a = lost.advise(S, None, 50.0)
    h = pick(a)
    assert h["kind"] == "path" and h["share"] == 1.0
    k = [f for f in a["helpers"] if f["kind"] == "knoll"]
    assert not k or (k[0]["share"] < lost.SURE and not k[0]["sure"])


def test_a_short_path_is_no_sure_line_a_long_stream_is():
    # the path is 40 m long: of nine rays across a circle of 50 m (12.5 m apart) three meet it
    S = scene()
    S["path"][90, 130:171] = True
    S["stream"][220, :] = True
    a = lost.advise(S, None, 50.0)
    h = pick(a)
    assert h["kind"] == "stream" and h["sure"]
    p = [f for f in a["helpers"] if f["kind"] == "path"]
    assert all(not f["sure"] for f in p)
    assert all(f["share"] == pytest.approx(3 / 9) for f in p if abs(f["az"]) < 5)


def test_nothing_inside_fenced_ground_is_offered():
    S = scene()
    S["imp"][60:111, :] = True             # fenced ground from 40 to 90 m north of the control, all across
    S["path"][80, :] = True                # a path inside it
    S["stream"][220, :] = True
    a = lost.advise(S, None, 25.0)
    assert all(f["kind"] != "path" for f in a["helpers"])
    assert pick(a)["kind"] == "stream"


def test_a_tap_inside_fenced_ground_is_moved_out():
    S = scene()
    S["imp"][100:131, 100:201] = True
    S["stream"][220, :] = True
    a = lost.advise(S, (150.0, 110.0), 25.0)
    assert a["snapped"] and not S["imp"][int(a["pos"][1]), int(a["pos"][0])]
    assert texts.lost_note(lost.public(S, a)).startswith("Tam, kam jsi ťukl, se nesmí")


def test_the_way_round_fenced_ground_or_none():
    # fenced ground 60 m wide between a point 90 m north and the control: round it at most 1.5 times straight
    S = scene()
    S["imp"][100:141, 120:181] = True
    r = lost._to_control(S, (150.0, 60.0))
    assert r is not None and r["via"] is not None
    assert 90.0 < r["dist"] <= 1.5 * 90.0 + 2.0
    assert lost.apart(r["az"], 180.0) > 10.0           # not straight into the fence
    S = scene()
    S["imp"][100:141, 40:261] = True                    # 220 m wide: too far round
    assert lost._to_control(S, (150.0, 60.0)) is None


def test_what_is_crossed_on_the_way():
    # a short path 80 m north (crossed on the straight line, but too short to catch from the circle), the stream
    # all across 120 m north
    S = scene()
    S["path"][70, 135:166] = True
    S["stream"][30, :] = True
    a = lost.advise(S, None, 25.0)
    h = pick(a)
    assert h["kind"] == "stream" and h["dist"] == pytest.approx(120.0, abs=1.0)
    assert [k for k, m in h["seen"]] == ["path"] and h["seen"][0][1] == pytest.approx(80.0, abs=1.0)
    first = texts.lost_advice(dict(lost.public(S, a), no_runner=False))[0]
    assert first == "Měl jsi jít na sever k vodoteči (asi 120 m, azimut 0°, po 80 m bys přešel cestu)."


def test_only_what_lies_before_the_feature_is_passed_on_the_way():
    # a slanting stream: the rays meet it at different distances; what lies beyond the point the advice goes to on
    # its own ray is not "on the way" (it was, when the limit was the median of all the rays)
    S = scene()
    for c in range(300):
        r = int(round(110 - 0.5 * (c - 150)))
        if 0 <= r < 300:
            S["stream"][r, c] = True
    S["path"][30, 100:150] = True
    a = lost.advise(S, (150.0, 150.0), 50.0)
    h = pick(a)
    assert all(m < h["dist"] for _, m in h["seen"])


# ------------------------------------------------------------------------------------------ from the line to the control
def test_along_the_line_the_control_on_the_right():
    # a path north to south 30 m west of the control; the runner 100 m south and 50 m east of the control
    S = scene()
    S["path"][:, 120] = True
    a = lost.advise(S, (200.0, 250.0), 25.0)
    h = pick(a)
    assert h["kind"] == "path" and h["az"] == pytest.approx(270.0, abs=1.0) and h["dist"] == pytest.approx(80.0, abs=1.0)
    link = h["link"]
    assert link["type"] == "near" and link["side"] == "right"
    assert link["along"] == pytest.approx(100.0, abs=2.0) and link["dist"] == pytest.approx(30.0, abs=1.0)
    assert link["az"] == pytest.approx(0.0, abs=1.0) and link["az_off"] == pytest.approx(90.0, abs=1.0)
    said = texts.lost_advice(lost.public(S, a))
    assert said[1] == "Pak podél ní na sever asi 100 m, kontrola byla 30 m vpravo."


def test_along_the_line_to_a_junction_then_a_bearing():
    # the path 90 m north of the control, a junction on it 30 m to the east: 95 m from the control at 198 degrees
    j = dict(kind="junction", at=[180.0, 60.0], r=8.0, base=1.0, on=["path"])
    S = scene(points=[j])
    S["path"][60, :] = True
    S["path"][:60, 180] = True
    a = lost.advise(S, None, 25.0)
    h = pick(a)
    assert h["kind"] == "path" and h["az"] == pytest.approx(0.0, abs=1.0)
    link = h["link"]
    assert link["type"] == "point" and link["point"] == "junction"
    assert link["along"] == pytest.approx(30.0, abs=1.5) and link["az"] == pytest.approx(90.0, abs=1.0)
    assert link["dist"] == pytest.approx(math.hypot(30, 90), abs=1.0)
    assert link["az_off"] == pytest.approx(198.4, abs=1.0)
    assert texts.lost_advice(lost.public(S, a))[1] == \
        "Pak podél ní na východ ke křížení cest (asi 30 m), odtud kontrola 95 m na azimut 200°."


def test_a_long_line_through_the_circle_is_sure():
    # a path north to south through the control; the runner 70 m south of it, 12 m beside the path, unsure by 30 m:
    # from half of the circle the path is behind, but anywhere in it the runner is at most 30 m from it
    S = scene()
    S["path"][:, 150] = True
    a = lost.advise(S, (162.0, 220.0), 30.0)
    h = pick(a)
    assert h["kind"] == "path" and h["sure"] and h.get("inside") and not a["relocate_first"]
    assert h["dist"] == pytest.approx(12.0, abs=1.0) and h["az"] == pytest.approx(270.0, abs=1.0)
    said = texts.lost_advice(lost.public(S, a))
    assert said[0] == "Do 30 m od tebe vedla cesta (nejblíž na západ, asi 10 m): měl jsi ji najít."
    assert said[1] == "Pak podél ní na sever asi 70 m, kontrola byla přímo u ní."
    a = lost.advise(S, (153.0, 220.0), 30.0)
    assert texts.lost_advice(lost.public(S, a))[0] == "Byl jsi u cesty, měl ses jí držet."
    # a short piece of path in the circle is no such line
    S = scene()
    S["path"][200:240, 150] = True
    a = lost.advise(S, (162.0, 220.0), 30.0)
    assert all(not f.get("inside") for f in a["helpers"])


# ------------------------------------------------------------------------------------------ go back first
def test_far_from_any_sure_line_go_back_to_it_first():
    # the runner 100 m south of the control, unsure by 25 m, came from the south; a stream all across 40 m behind
    # them and a path 230 m ahead (130 m beyond the control)
    S = scene(prev=(150.0, 299.0))
    S["stream"][290, :] = True
    S["path"][20, :] = True
    a = lost.advise(S, (150.0, 250.0), 25.0, came_from=180.0)
    h = pick(a)
    assert h["kind"] == "stream" and a["relocate_first"] and a["back"]
    said = texts.lost_advice(lost.public(S, a))
    assert said[0] == ("Neměl jsi hádat směr ke kontrole. Nejdřív ses měl vrátit na jih k vodoteči (asi 40 m, azimut 180°), "
                       "ta se nedala minout.")
    assert said[1] == "Odtud kontrola 140 m na azimut 0°."


def test_near_a_sure_line_no_going_back():
    S = scene()
    S["path"][170, :] = True               # 20 m south of the runner at the control, circle 25 m
    a = lost.advise(S, (150.0, 150.0), 25.0)
    assert pick(a)["kind"] == "path" and not a["relocate_first"]


def test_nothing_sure_go_back_to_the_attack_point():
    S = scene(attack=dict(kind="junction", at=[150.0, 230.0]))
    a = lost.advise(S, (150.0, 150.0), 25.0)
    assert a["pick"] is None
    said = texts.lost_advice(lost.public(S, a))
    assert said[0] == "Kolem nebylo nic, čeho by ses dal jistě chytit."
    assert said[1] == ("Měl ses vrátit na náběhový bod (křížení cest 80 m na azimut 180°) a začít znovu odtud: "
                       "kontrola byla 80 m na azimut 0°.")


def test_too_far_from_the_control():
    S = scene()
    a = lost.advise(S, (150.0, 470.0), 25.0)
    assert a["far"]
    assert texts.lost_advice(lost.public(S, a))[0].startswith("Tohle místo je dál než 300 m od kontroly")


def test_the_description_is_shown():
    S = scene()
    S["path"][90, :] = True
    said = texts.lost_advice(lost.public(S, lost.advise(S, None, 25.0), "kupka, severní úpatí"))
    assert said[-1] == "Podle popisu jsi hledal: kupka, severní úpatí."
    assert len(said) <= 3


# ------------------------------------------------------------------------------------------ after the race
def _track(centre_m, n_loops=1):
    """A track from 200 m south of the control up to it at 3 m/s, with a loop of 15 m radius (60 s) centre_m north
    of where it passes; in cells of a scene with the control at (150, 150)."""
    cols, rows = [], []
    for y in np.arange(350.0, 150.0 + centre_m, -3.0):
        cols.append(150.0)
        rows.append(y)
    cy = rows[-1]
    for k in range(60 * n_loops):
        a = 2 * math.pi * k / 60.0
        cols.append(150.0 + 15.0 * math.sin(a))
        rows.append(cy - 15.0 + 15.0 * math.cos(a))
    for y in np.arange(cy, 150.0, -3.0 if cy > 150 else 3.0):
        cols.append(150.0)
        rows.append(y)
    cols.append(150.0)
    rows.append(150.0)
    return cols, rows, list(range(len(cols)))


def test_a_loop_near_the_control_is_found_a_far_one_not():
    S = scene()
    cols, rows, t = _track(50.0)
    m = lost.moments(S, cols, rows, t, 0, len(t) - 1, 3.0)
    assert len(m) >= 1 and all(lost.AT_CONTROL_M <= x["dist"] <= lost.NEAR_LOST_M for x in m)
    assert any(x["dist"] <= 70.0 for x in m)
    cols, rows, t = _track(150.0)
    S2 = scene(n=500)
    m = lost.moments(S2, cols, rows, t, 0, len(t) - 1, 3.0)
    assert m == []


def test_a_place_is_named_by_the_mistake_the_analysis_found_there():
    S = scene()
    cols, rows, t = _track(50.0)
    plain = lost.moments(S, cols, rows, t, 0, len(t) - 1, 3.0)
    i = plain[0]["i"] + 5                      # the kind of mistake found a few seconds into the same place
    named = lost.moments(S, cols, rows, t, 0, len(t) - 1, 3.0, anchors=[(i, "mistake:circling")])
    assert named[0]["i"] == plain[0]["i"] and named[0]["why"] == "mistake:circling"


def test_looking_back_says_what_was_there():
    S = scene()
    S["path"][195, :] = True             # crossed 45 m south of the control on the way in
    cols, rows, t = _track(50.0)
    got = lost.look_back(S, cols, rows, t, 0, len(t) - 1, 3.0, anchors=[(len(t) // 2, "mistake:circling")])
    assert got
    said = texts.lost_moment(lost.public_moment(S, got[0]))
    assert said["head"].endswith("m od kontroly kroužil jsi.") or said["head"].endswith("otočil ses.") or \
        "kontroly" in said["head"]
    assert said["back"]


# ------------------------------------------------------------------------------------------ the map
def test_the_cells_of_a_scene_follow_the_map():
    from oroute.kmzmap import GeoMap
    gm = GeoMap.from_kmz(inputs("pohora")[1])
    box, s = (400, 300, 900, 760), 3
    meta = lost.affine(gm, box, s)
    for u, v in ((410.0, 310.0), (650.5, 520.25), (880.0, 750.0)):
        la, lo = gm.px_to_latlon(u, v)
        c, r = lost.to_cell(meta, float(la), float(lo))
        assert c == pytest.approx((u - box[0]) / s - 0.5, abs=0.05)
        assert r == pytest.approx((v - box[1]) / s - 0.5, abs=0.05)
        la2, lo2 = lost.to_latlon(meta, c, r)
        assert la2 == pytest.approx(float(la), abs=2e-6) and lo2 == pytest.approx(float(lo), abs=2e-6)


def test_scenes_are_saved_and_loaded(tmp_path):
    S = scene()
    S["path"][90, :] = True
    meta = {k: v for k, v in S.items() if k not in lost.LINES + ("imp", "k")}
    arrays = {k: S[k] for k in lost.LINES + ("imp",)}
    lost.save(str(tmp_path / "lost.json"), str(tmp_path / "lost.npz"), {3: (meta, arrays)}, stamp=[1, 2])
    sc = lost.Scene.load(str(tmp_path / "lost.json"), str(tmp_path / "lost.npz"))
    assert sc.controls == [3] and sc.meta["stamp"] == [1, 2] and sc.meta["version"] == lost.VERSION
    T = sc.control(3)
    assert T["path"][90].all() and not T["path"][91].any()
    a = lost.advice(sc, 3, None, None, 25.0)
    assert a["helpers"][a["pick"]]["kind"] == "path"
    assert sc.control(9) is None
