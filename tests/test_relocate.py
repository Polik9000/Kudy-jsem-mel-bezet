"""Catching features around a control and wandering near it (oroute/relocate.py) on made-up terrain."""
import numpy as np

from oroute import relocate as R
from oroute import terrain as T
from oroute.speedmodel import SpeedModel
from webapp import texts

MPP = 1.33
CTRL = (200.0, 200.0)


def forest(side=400):
    return np.full((side, side), T.FOREST, np.uint8), np.zeros((side, side), bool), np.zeros((side, side))


def found(cls, blue, hgt, source="aws", barriers=None, approach=180.0):
    cands = R.describe(R.candidates(cls, blue, hgt, MPP, CTRL, source), cls, hgt, MPP, CTRL, SpeedModel(), barriers)
    return cands, *R.choose(cands, approach, MPP)


def kinds(feats):
    return sorted(f["kind"] for f in feats)


def test_junction_path_pond_building_and_clearing_are_found_with_bearings():
    cls, blue, hgt = forest()
    cls[258:261, 60:340] = T.PATH                    # a path running west-east 78 m south of the control ...
    cls[150:340, 139:142] = T.PATH                   # ... crossed by one running north-south: a junction in the south-west
    cls[130:142, 245:257] = T.BUILDING               # a house in the north-east
    cls[190:215, 270:300] = T.WATER                  # a pond in the east
    cls[140:160, 120:145] = T.OPEN                   # a small clearing in the north-west
    cands, feats, attack = found(cls, blue, hgt)
    by = {f["kind"]: f for f in feats}
    assert len(feats) == 4 and {"junction", "pond", "building"} <= set(by)
    j = by["junction"]
    assert abs(j["px"][0] - 140) < 4 and abs(j["px"][1] - 259) < 4
    assert abs(j["dist"] - np.hypot(60, 59) * MPP) < 6 and abs(j["az"] - 225) < 5 and abs(j["back_az"] - 45) < 5
    assert abs(by["pond"]["az"] - 90) < 8 and abs(by["building"]["az"] - 38) < 8
    assert [abs(f["az"] - 307) < 2 for f in cands if f["kind"] == "clearing"] == [True]
    # the path itself is a line: the point given is the nearest one, straight south
    path = next(f for f in cands if f["kind"] == "path")
    assert abs(path["az"] - 180) < 3 and abs(path["dist"] - 58 * MPP) < 4 and path["ok"]
    # the leg comes from the south: the junction lies on the way in, the house behind the control does not
    assert attack["kind"] == "junction"
    assert R.choose(cands, 20.0, MPP)[1]["kind"] == "building"
    # Czech wording: where it lies, and how to get from it to the control
    w = texts.feature(dict(kind="junction", lat=1, lon=2, dist=79.6, az=224.0, back_az=44.0, dh=6.0, point=True))
    assert w["where"] == "křížení cest 80 m od kontroly na azimut 225°"
    assert w["back"] == "z křížení cest 80 m na azimut 45°, mírně do kopce"
    assert texts.feature(dict(kind="stream", lat=1, lon=2, dist=20, az=358, back_az=178, dh=-9.0, point=False)) \
        ["where"] == "vodoteč, nejblíž 20 m od kontroly na azimut 0°"


def test_mosaic_of_open_land_and_short_black_marks_give_nothing():
    cls, blue, hgt = forest()
    cls[140:260:8, 40:360] = T.ROUGH_OPEN            # thin strips of half-open land: no clearing among them
    cls[150:153, 230:250] = T.PATH                   # a short black mark (a cliff, a ditch): not a path to catch
    cands, feats, attack = found(cls, blue, hgt)
    assert feats == [] and attack is None and not [f for f in cands if f["kind"] in ("clearing", "path", "junction")]


def test_feature_behind_water_or_a_forbidden_line_is_left_out():
    cls, blue, hgt = forest()
    cls[258:261, 60:340] = T.PATH
    cls[150:340, 139:142] = T.PATH
    cls[130:133, 60:340] = T.PATH                    # a second junction in the north-west
    cls[60:150, 139:142] = T.PATH
    assert kinds(found(cls, blue, hgt)[1]).count("junction") == 2
    lake = cls.copy()
    lake[225:245, 0:400] = T.WATER                   # a river between the control and everything in the south
    cands, feats, attack = found(lake, blue, hgt)
    assert [f["ok"] for f in cands if f["kind"] == "junction" and f["px"][1] > 245] == [False]
    assert all(f["px"][1] < 225 for f in feats) and attack is None
    # the same with a line that must not be crossed (a railway), unless there is a crossing next to the way
    rail = dict(forbidden=[[(0.0, 235.0), (399.0, 235.0)]], hard=[], crossings=[], areas=[])
    assert all(f["px"][1] < 235 for f in found(cls, blue, hgt, barriers=rail)[1])
    rail["crossings"] = [(170.0, 235.0)]
    assert any(f["px"][1] > 245 for f in found(cls, blue, hgt, barriers=rail)[1])


def test_stream_is_a_long_blue_line_and_marsh_dashes_are_not():
    cls, blue, hgt = forest()
    blue[150:152, 40:360] = True                     # a stream 66 m north of the control
    for v in range(240, 300, 5):
        blue[v, 180:195] = True                      # marsh: short dashes
    cls[100:320, 259:262] = T.PATH                   # a path that crosses the stream in the north-east
    cands, feats, _ = found(cls, blue, hgt)
    stream = [f for f in cands if f["kind"] == "stream"]
    assert len(stream) == 1 and abs(stream[0]["az"]) < 3 or abs(stream[0]["az"] - 360) < 3
    assert abs(stream[0]["dist"] - 49 * MPP) < 4
    cross = [f for f in cands if f["kind"] == "stream_path"]
    assert len(cross) == 1 and abs(cross[0]["px"][0] - 260) < 4 and abs(cross[0]["px"][1] - 150) < 4
    assert "stream_path" in kinds(feats) and "stream" in kinds(feats)


def test_hilltop_needs_a_clear_top():
    cls, blue, hgt = forest()
    v, u = np.mgrid[0:400, 0:400]
    hill = 8.0 * np.exp(-((u - 260) ** 2 + (v - 140) ** 2) / (2 * 22.0 ** 2))        # 8 m high, about 60 m across
    cands, feats, _ = found(cls, blue, 300 + hill, source="cuzk")
    top = [f for f in cands if f["kind"] == "hilltop"]
    assert len(top) == 1 and abs(top[0]["px"][0] - 260) < 5 and abs(top[0]["px"][1] - 140) < 5
    assert top[0]["dh"] < -6                         # the control lies below it
    # a slope with a bump of one metre is no hilltop, and the coarse elevation needs twice the height
    assert not [f for f in R.candidates(cls, blue, 300 + 0.05 * u + hill / 8, MPP, CTRL, "cuzk") if f["kind"] == "hilltop"]
    assert not [f for f in R.candidates(cls, blue, 300 + hill / 2, MPP, CTRL, "aws") if f["kind"] == "hilltop"]
    # the knoll of the map (the brown dot, ISOM 109) is another thing and has another name
    assert texts.FEATURES["hilltop"][0] == "vrchol" and texts.FEATURES["knoll"][0] == "kupka"


def test_end_of_a_path_is_not_a_junction_and_a_dashed_track_has_no_ends_in_it():
    cls, blue, hgt = forest()
    cls[258:261, 0:261] = T.PATH                     # a path from the west that stops south-east of the control
    cands, feats, _ = found(cls, blue, hgt)
    ends = [f for f in cands if f["kind"] == "path_end"]
    assert len(ends) == 1 and abs(ends[0]["px"][0] - 258) < 6 and abs(ends[0]["px"][1] - 259) < 3
    assert not [f for f in cands if f["kind"] == "junction"] and "path_end" in kinds(feats)
    assert texts.feature(dict(ends[0], lat=1, lon=2, point=True))["where"].startswith("konec cesty ")
    # a path that stops before it comes level with the control: its nearest point is its end, named once
    cls, blue, hgt = forest()
    cls[258:261, 0:151] = T.PATH
    assert kinds(found(cls, blue, hgt)[1]) == ["path_end"]
    # a track drawn in dashes right across the cut-out: one line, no end anywhere in it
    cls, blue, hgt = forest()
    for u in range(60, 340, 9):
        cls[258:261, u:u + 6] = T.PATH
    cands = R.candidates(cls, blue, hgt, MPP, CTRL)
    assert "path" in kinds(cands) and [f for f in cands if f["kind"] == "path_end" and 90 < f["px"][0] < 310] == []
    # two paths that meet stay a junction, and the spur that ends 40 m from it is an end of its own
    cls, blue, hgt = forest()
    cls[258:261, 0:400] = T.PATH
    cls[0:400, 139:142] = T.PATH
    cls[228:261, 259:262] = T.PATH
    ks = kinds(R.candidates(cls, blue, hgt, MPP, CTRL))
    assert ks.count("junction") == 2 and ks.count("path_end") == 1          # where they cross, and where the spur leaves


def fenced_sheet(ticks=True):
    """A picture of forest with a rectangle of black line (30 x 24 px, about 40 x 32 m) north-east of the
    control, ticks standing inwards from it as a fence has them, and the terrain classes read from it."""
    rgb = np.full((400, 400, 3), 255, np.uint8)
    cls = np.full((400, 400), T.FOREST, np.uint8)
    black = np.zeros((400, 400), bool)
    black[140:142, 240:272] = black[164:166, 240:272] = True
    black[140:166, 240:242] = black[140:166, 270:272] = True
    if ticks:
        for u in (248, 256, 264):
            black[142:146, u:u + 2] = True           # ticks of 5 m on the upper side, pointing in
            black[160:164, u:u + 2] = True
    rgb[black] = 0
    cls[black] = T.PATH                              # the terrain reader takes every black line for a path
    return rgb, cls


def test_enclosure_is_the_ground_a_fence_closes_in_and_its_corners_are_no_junctions():
    rgb, cls = fenced_sheet()
    blue, hgt = np.zeros((400, 400), bool), np.zeros((400, 400))
    fenced, pens = R.enclosures(rgb, cls, MPP)
    assert len(pens) == 1 and abs(pens[0][0] - 255.5) < 3 and abs(pens[0][1] - 152.5) < 3
    assert 500 < pens[0][2] < 1400 and fenced[152, 255] and fenced[140, 255] and not fenced[200, 200]
    cands = R.describe(R.candidates(cls, blue, hgt, MPP, CTRL, rgb=rgb), cls, hgt, MPP, CTRL, SpeedModel())
    assert kinds(cands) == ["enclosure"]             # no junction at a corner or a tick, no path, no path end
    feats, attack = R.choose(cands, 45.0, MPP)
    assert attack["kind"] == "enclosure"
    assert texts.feature(dict(cands[0], lat=1, lon=2, point=True))["where"].startswith("oplocenka ")
    # the same rectangle without ticks is a loop of paths (or the outline of a roof): no enclosure
    rgb, cls = fenced_sheet(ticks=False)
    assert R.enclosures(rgb, cls, MPP)[1] == []
    # ground that must not be entered is no enclosure, whatever is drawn around it
    rgb, cls = fenced_sheet()
    inside = (slice(142, 164), slice(242, 270))
    rgb[inside][cls[inside] == T.FOREST] = (171, 165, 54)
    cls[inside][cls[inside] == T.FOREST] = T.OOB
    assert R.enclosures(rgb, cls, MPP)[1] == []


def test_grey_print_around_the_map_is_no_path_and_a_paved_road_is_no_open_land():
    cls, blue, hgt = forest()
    rgb = np.full((400, 400, 3), 255, np.uint8)
    cls[258:261, 0:400] = cls[0:400, 139:142] = T.PATH       # two paths in the black of the map
    cls[100:103, 150:400] = cls[60:140, 300:303] = T.PATH    # the strokes of a title, read as paths too ...
    cls[130:142, 245:257] = T.BUILDING                       # ... and a block of a printed code, read as a house
    rgb[cls == T.PATH] = (35, 31, 32)
    rgb[100:103, 150:400] = rgb[60:140, 300:303] = rgb[130:142, 245:257] = (80, 72, 72)      # ... both grey
    seen = R.candidates(cls, blue, hgt, MPP, CTRL)           # without the picture every dark line is a path
    assert kinds(seen).count("junction") == 2 and "building" in kinds(seen)
    seen = R.candidates(cls, blue, hgt, MPP, CTRL, rgb=rgb)
    assert kinds(seen).count("junction") == 1 and "building" not in kinds(seen)
    assert all(f["px"][1] > 200 or f["px"][0] < 150 for f in seen)
    # a paved road east of the control, light brown between two black lines: a path to hit, not open land
    cls, blue, hgt = forest()
    rgb = np.full((400, 400, 3), 255, np.uint8)
    cls[0:400, 290:340] = T.OPEN                             # the terrain reader runs it like open land
    rgb[0:400, 290:340] = (226, 170, 125)
    cls[0:400, 288:290] = cls[0:400, 340:342] = T.PATH
    rgb[cls == T.PATH] = (35, 31, 32)
    assert "open_edge" in kinds(R.candidates(cls, blue, hgt, MPP, CTRL))
    assert "open_edge" not in kinds(R.candidates(cls, blue, hgt, MPP, CTRL, rgb=rgb))
    b = stop(cls, blue, hgt, 90.0, rgb)["ahead"]
    assert b["kind"] == "path" and abs(b["dist"] - 88 * MPP) < 5
    # and yellow land behind a black line is still stopped at by the line (the two are one thing)
    rgb[0:400, 290:340] = (253, 190, 79)
    assert stop(cls, blue, hgt, 90.0, rgb)["ahead"]["kind"] == "path"


def stop(cls, blue, hgt, travel_az, rgb=None):
    """The parts of the backstop by their side, each with where it lies seen from the control; None without one."""
    L = R.layers(cls, blue, MPP, rgb)
    cands = R.describe(R.candidates(cls, blue, hgt, MPP, CTRL, rgb=rgb, L=L), cls, hgt, MPP, CTRL, SpeedModel())
    R.choose(cands, (travel_az + 180.0) % 360.0, MPP)
    b = R.beyond(L, cands, CTRL, travel_az, MPP)
    return {q["side"]: R._place(q, hgt, MPP, CTRL) for q in b["parts"]} if b else None


def test_backstop_is_what_lies_across_the_way_on_to_the_left_straight_on_and_to_the_right():
    cls, blue, hgt = forest()
    cls[110:113, 40:360] = T.PATH                    # a path across, 90 px (120 m) north of the control
    b = stop(cls, blue, hgt, 0.0)                    # running north
    assert set(b) == {"left", "ahead", "right"} and {q["kind"] for q in b.values()} == {"path"}
    assert abs(b["ahead"]["dist"] - 89 * MPP) < 5 and len(b["ahead"]["line"]) == 5
    assert b["left"]["az"] > 300 and b["right"]["az"] < 60
    assert stop(cls, blue, hgt, 180.0) is None       # running south: nothing within 200 m
    # running east along the path: it lies beside the way, only the rays to the left meet it
    assert set(stop(cls, blue, hgt, 90.0)) == {"left"}
    # a stream nearer than the path stops the runner first, on every side
    blue[150:152, 40:360] = True
    assert {q["kind"] for q in stop(cls, blue, hgt, 0.0).values()} == {"stream"}
    # ... and a house straight ahead, nearer than both, before that; beside it the stream still does
    cls[160:172, 195:207] = T.BUILDING
    b = stop(cls, blue, hgt, 0.0)
    assert b["ahead"]["kind"] == "building" and 35 < b["ahead"]["dist"] < 55 and b["left"]["kind"] == "stream"
    # the path one came by, going on past the control, is not across the way: no backstop
    cls, blue, hgt = forest()
    cls[20:380, 199:202] = T.PATH
    assert stop(cls, blue, hgt, 0.0) is None
    # ... but where it bends across the way it is one
    cls[110:113, 199:330] = T.PATH
    cls[20:110, 199:202] = T.FOREST
    b = stop(cls, blue, hgt, 0.0)
    assert b["right"]["kind"] == "path" and "left" not in b
    # the end of a path and a boulder can be run past 20 m to the side: points are no backstops
    cls, blue, hgt = forest()
    cls[130:133, 150:197] = T.PATH                   # ends north-west of the control, short of the way on
    L = R.layers(cls, blue, MPP)
    cands = R.describe(R.candidates(cls, blue, hgt, MPP, CTRL, found=[dict(kind="boulder", px=(200, 140), size=(3, 3))],
                                    L=L), cls, hgt, MPP, CTRL, SpeedModel())
    assert {"path_end", "boulder"} <= set(kinds(cands)) and R.beyond(L, cands, CTRL, 0.0, MPP) is None
    # fenced ground straight ahead is one: the fence is hit wherever one runs on
    rgb, cls = fenced_sheet()
    blue, hgt = np.zeros((400, 400), bool), np.zeros((400, 400))
    assert stop(cls, blue, hgt, 49.0, rgb)["ahead"]["kind"] == "enclosure"


def test_backstop_in_words():
    part = lambda side, kind, dist: dict(side=side, kind=kind, lat=1, lon=2, dist=dist, line=[[1, 2], [1, 3]])
    w = texts.beyond(dict(az=1.0, back_az=181.0, within=200.0,
                          parts=[part("left", "path", 131.2), part("ahead", "path", 118.4), part("right", "path", 124.0)]))
    assert w["label"] == "cesta napříč 118–131 m za kontrolou"
    assert w["text"] == "cesta napříč 118–131 m za kontrolou. Kdo tam doběhne, kontrolu přeběhl a vrací se na azimut 180°"
    assert [q["label"] for q in w["parts"]][1] == "rovně cesta 118 m za kontrolou"
    assert w["parts"][0]["line"] == [[1, 2], [1, 3]]
    w = texts.beyond(dict(az=330.0, back_az=150.0, within=200.0,
                          parts=[part("left", "path", 12.0), part("right", "enclosure", 22.3)]))
    assert w["label"] == "vlevo cesta 12 m, vpravo oplocenka 22 m; rovně nic do 200 m"
    # a result of before the backstop had parts was one point: not shown (the page offers to find them again)
    assert texts.beyond(dict(kind="path", lat=1, lon=2, dist=118.4, az=1.0, back_az=181.0)) is None
    assert texts.beyond(None) is None


def test_track_through_what_the_routes_must_not_in_words():
    w = texts.crossed([dict(kind="line", what="railway", at=[49.1, 18.1]),
                       dict(kind="enclosure", what="enclosure", at=[49.2, 18.2])])
    assert w["at"] == [[49.1, 18.1], [49.2, 18.2]]
    assert w["text"].startswith("Tvoje stopa kříží železnici mimo přechod a vede přes oplocenku. Nejlepší postup tudy nesmí")
    assert "„Železnice a dálnice“" in w["text"]
    assert texts.crossed([]) is None and texts.crossed(None) is None


def test_way_in_follows_the_best_route_and_the_attack_point_lies_on_it():
    # the leg starts in the north-west, but its best route swings round and comes to the control from the east
    route = [(60.0, 60.0), (330.0, 80.0), (340.0, 200.0), (290.0, 200.0)]
    az, tail = R.way_in(route, CTRL, MPP)
    assert abs(az - 90) < 3 and tail[0] == CTRL and tail[1] == (290.0, 200.0)
    assert R.way_in([(201.0, 200.0)], CTRL, MPP)[0] is None          # too short to have a direction
    # a last bend 20 m before the control does not turn the direction
    az2, _ = R.way_in([(340.0, 200.0), (212.0, 200.0), (208.0, 190.0)], CTRL, MPP)
    assert abs(az2 - 90) < 12
    cls, blue, hgt = forest()
    cls[250:253, 0:400] = T.PATH
    cls[0:400, 245:248] = T.PATH                     # a junction south-east of the control, off the route
    cls[194:206, 262:274] = T.BUILDING               # a house the route passes, 90 m before the control
    cands = R.describe(R.candidates(cls, blue, hgt, MPP, CTRL), cls, hgt, MPP, CTRL, SpeedModel())
    assert R.choose(cands, az, MPP)[1]["kind"] == "junction"            # by direction alone: the better feature
    assert R.choose(cands, az, MPP, route=tail)[1]["kind"] == "building"  # with the route: what the route passes
    # nothing before the control: no attack point, whatever lies behind it
    assert R.choose(cands, 270.0, MPP)[1] is None


def track(points, speed=3.0):
    """A track through the points (metres), one sample every ~6 m at `speed`: t, x, y."""
    xs, ys = [points[0][0]], [points[0][1]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = max(1, int(np.hypot(x1 - x0, y1 - y0) / 6))
        xs += list(np.linspace(x0, x1, n + 1)[1:])
        ys += list(np.linspace(y0, y1, n + 1)[1:])
    x, y = np.array(xs), np.array(ys)
    t = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)) / speed)]
    return t, x, y


def test_wandering_is_found_where_the_direct_way_in_ended():
    ctrl = (0.0, 0.0)
    # straight in from 400 m: nothing
    t, x, y = track([(400, 0), (0, 0)])
    assert R.wandering(t, x, y, 0, len(t) - 1, ctrl, 3.0) is None
    # in to 60 m, then off to the north for 150 m and back
    t, x, y = track([(400, 0), (60, 0), (60, 150), (0, 0)])
    w = R.wandering(t, x, y, 0, len(t) - 1, ctrl, 3.0)
    assert w is not None and abs(w["dist"] - 60) < 15 and abs(x[w["i"]] - 60) < 15 and abs(y[w["i"]]) < 30
    assert 200 < w["extra_m"] < 260 and 60 < w["extra_s"] < 95
    # the same shape far from the control is a route choice, not wandering near the control
    t, x, y = track([(900, 0), (600, 0), (600, 150), (500, 0), (0, 0)])
    assert R.wandering(t, x, y, 0, len(t) - 1, ctrl, 3.0) is None
    # a leg that lost no time is not looked at
    t, x, y = track([(400, 0), (60, 0), (60, 150), (0, 0)])
    assert R.wandering(t, x, y, 0, len(t) - 1, ctrl, 3.0, est_loss=10.0) is None


def test_nearest_feature_to_the_wandering_track_and_its_wording():
    cls, blue, hgt = forest()
    cls[258:261, 60:340] = T.PATH
    cls[150:340, 139:142] = T.PATH                   # junction at (140, 259)
    cands, _, _ = found(cls, blue, hgt)
    walk = [(u, 240.0) for u in range(260, 150, -5)]         # wandering west, south of the control
    f, metres, k = R.nearest_help(cands, walk, MPP)
    assert f["kind"] == "junction" and abs(metres - np.hypot(15, 19) * MPP) < 6 and walk[k][0] == 155
    assert R.nearest_help(cands, [(390.0, 20.0)], MPP) is None                # nothing within 120 m of that corner
    r = texts.relocate(dict(features=[], lost=dict(
        i=40, lat=49.6, lon=18.3, dist=58.0, extra_m=240.0, extra_s=83.0,
        near=dict(kind="junction", lat=49.61, lon=18.31, dist=95.0, az=320.0, back_az=140.0, dh=1.0, point=True,
                  track_m=61.0, i=52))))
    assert r["lost"]["text"] == ("U téhle kontroly jsi bloudil: přímý směr k ní jsi opustil 58 m před ní, naběhal jsi "
                                 "240 m navíc a stálo to asi 1:23. Byl jsi 61 m od křížení cest, odkud vede ke kontrole "
                                 "přímý azimut 140° (95 m, po rovině).")
    assert r["lost"]["at"] == [49.6, 18.3] and r["features"] == []
    assert "neminul blíž než 120 m" in texts.relocate(dict(features=[], lost=dict(
        i=1, lat=1, lon=2, dist=58.0, extra_m=240.0, extra_s=83.0, near=None)))["lost"]["text"]
    assert texts.relocate(None) is None


def fence_sheet(mpp=0.6, side=420):
    """A map with a fence (a line with ticks to one side) across it, and what must not be read as one."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (side, side), (194, 225, 192))     # light green: white would be the margin of the sheet
    d = ImageDraw.Draw(im)
    px = lambda m: m / mpp
    d.line([40, 60, 380, 60], fill=(0, 0, 0), width=3)                      # a fence: ticks every 25 m, leaning
    for u in range(70, 380, int(px(25))):
        d.line([u, 60, u + px(3), 60 + px(6)], fill=(0, 0, 0), width=2)
    for u in range(40, 380, int(px(12))):                                   # a dashed path: no ticks
        d.line([u, 130, u + px(9), 130], fill=(0, 0, 0), width=3)
    d.line([40, 200, 380, 200], fill=(0, 0, 0), width=4)                    # a railway: bars across the line
    for u in range(60, 380, int(px(12))):
        d.line([u, 200 - px(4), u, 200 + px(4)], fill=(0, 0, 0), width=2)
    d.line([40, 270, 380, 270], fill=(0, 0, 0), width=3)                    # a path with two paths branching off
    d.line([150, 270, 150, 270 + px(40)], fill=(0, 0, 0), width=3)
    d.line([260, 270, 260, 270 + px(40)], fill=(0, 0, 0), width=3)
    d.line([40, 350, 380, 350], fill=(194, 96, 46), width=3)                # a contour with slope lines: brown
    for u in range(70, 380, int(px(25))):
        d.line([u, 350, u, 350 + px(5)], fill=(194, 96, 46), width=2)
    rgb = np.asarray(im)
    # the classes by hand (on so small a sheet terrain.classify takes the margin for the edge of the map)
    cls = np.where(rgb.sum(-1) < 150, T.PATH, T.SLOW).astype(np.uint8)
    return rgb, cls


def test_fence_is_a_line_with_ticks_to_one_side_and_nothing_else_is():
    mpp = 0.6
    rgb, cls = fence_sheet(mpp)
    mask, found = R.fences(rgb, cls, mpp)
    assert len(found) == 1 and mask[59:62, 80:360].any(1).all() and mask[59:62, 80:360].mean() > 0.8
    assert not mask[100:].any()                      # dashed path, railway, branching path, contour: no fence
    # a fence is no path for the routes, and crossing it costs time
    from PIL import Image

    from oroute import mapdata
    from oroute.kmzmap import GeoMap
    gm = GeoMap(Image.fromarray(rgb), 50.001, 50.0, 18.001, 18.0)
    gm.m_per_px_x = gm.m_per_px_y = mpp
    obs = mapdata.obstacles(gm, cls)
    assert (cls[59:62, 80:360] == T.PATH).any() and not (obs["cls"][59:62, 80:360] == T.PATH).any()
    assert (obs["cls"][129:132, 60:360] == T.PATH).any() and obs["hard"][60, 200] and not obs["blocked"].any()
    # the black line around ground that must not be entered is the outline of that ground, no path
    olive = rgb.copy()
    olive[290:330, 60:360] = (171, 165, 54)
    olive[287:290, 60:360] = 0
    cls3 = np.where(olive.sum(-1) < 150, T.PATH, T.SLOW).astype(np.uint8)
    cls3[290:330, 60:360] = T.OOB
    gm3 = GeoMap(Image.fromarray(olive), 50.001, 50.0, 18.001, 18.0)
    gm3.m_per_px_x = gm3.m_per_px_y = mpp
    obs = mapdata.obstacles(gm3, cls3)
    assert (cls3[287:290, 80:340] == T.PATH).all() and not (obs["cls"][287:290, 80:340] == T.PATH).any()
    assert (obs["cls"][269:272, 60:140] == T.PATH).all()         # the path 10 m away from it stays one
    # two ticks are not enough to tell
    rgb2 = rgb.copy()
    rgb2[63:80, 150:] = (194, 225, 192)
    assert R.fences(rgb2, cls, mpp)[1] == []
    # ... and in words
    assert texts.FEATURES["fence"][0] == "plot" and "fence" in R.BACKSTOPS


def test_backstop_is_not_the_clearing_the_control_stands_at_and_a_far_one_needs_most_rays():
    cls, blue, hgt = forest()
    cls[178:200, 180:222] = T.OPEN                   # the control stands at the edge of this clearing ...
    cls[120:124, 60:340] = T.PATH                    # ... and a path runs across 100 m north of it
    L = R.layers(cls, blue, MPP)
    cands = R.candidates(cls, blue, hgt, MPP, CTRL, L=L)
    stop = R.beyond(L, cands, CTRL, 0.0, MPP)
    assert stop and {q["kind"] for q in stop["parts"]} == {"path"}
    # a path 180 m away that only a few rays of a part reach is no backstop of that part
    cls, blue, hgt = forest()
    cls[62:66, 196:260] = T.PATH
    L = R.layers(cls, blue, MPP)
    assert R.beyond(L, R.candidates(cls, blue, hgt, MPP, CTRL, L=L), CTRL, 0.0, MPP) is None


def test_attack_point_lies_inside_its_leg_and_a_short_leg_has_none():
    cls, blue, hgt = forest()
    cls[250:253, 0:400] = T.PATH
    cls[0:400, 245:248] = T.PATH                     # a junction 91 m south-east of the control
    cands = R.describe(R.candidates(cls, blue, hgt, MPP, CTRL), cls, hgt, MPP, CTRL, SpeedModel())
    before = lambda leg_m: (CTRL[0] + leg_m / MPP * np.sin(np.radians(135)), CTRL[1] - leg_m / MPP * np.cos(np.radians(135)))
    pick = lambda leg_m: R.choose(cands, 135.0, MPP, prev=before(leg_m), leg_m=leg_m)[1]
    assert pick(300.0)["kind"] == "junction" and abs(pick(300.0)["dist"] - 91) < 4
    assert pick(131.0)["kind"] == "junction"         # 91 m is just within 70 % of the leg
    # a leg of 120 m: the junction lies 91 m before the control, which is at the control before. No attack point.
    assert pick(120.0) is None
    # ... and the features around the control are the same whatever the leg is
    assert kinds(R.choose(cands, 135.0, MPP, prev=before(120.0), leg_m=120.0)[0]) == kinds(R.choose(cands, 135.0, MPP)[0])
    # a leg under 80 m has none, however well a point lies; one of 82 m has it only 25 m clear of the control before
    near = [dict(kind="junction", px=(CTRL[0] + 23.0, CTRL[1] + 23.0), dist=43.3, az=135.0, back_az=315.0, dh=0.0, ok=True)]
    assert R.choose(near, 135.0, MPP, prev=before(75.0), leg_m=75.0)[1] is None
    assert R.choose(near, 135.0, MPP, prev=before(82.0), leg_m=82.0)[1]["kind"] == "junction"
    far = [dict(near[0], px=(CTRL[0] + 30.0, CTRL[1] + 30.0), dist=56.4)]       # 56 m before the control: 26 m from the last
    assert R.choose(far, 135.0, MPP, prev=before(82.0), leg_m=82.0)[1]["kind"] == "junction"
    assert R.choose(far, 135.0, MPP, prev=before(80.5), leg_m=80.5)[1] is None   # 24 m from it


def test_feature_behind_fenced_ground_is_left_out_or_given_with_the_way_round():
    cls, blue, hgt = forest()
    cls[258:261, 60:340] = T.PATH
    cls[150:340, 139:142] = T.PATH                   # a junction 112 m south-west of the control ...
    cls[130:133, 60:340] = T.PATH
    cls[60:150, 259:262] = T.PATH                    # ... and one 120 m north-east of it
    walls = lambda mask: dict(forbidden=[], hard=[], crossings=[], areas=[], mask=mask)
    sw = lambda cands: next(f for f in cands if f["kind"] == "junction" and f["px"][1] > 200)
    ne = lambda cands: next(f for f in cands if f["kind"] == "junction" and f["px"][1] < 200)
    # nothing in between: the straight bearing, no way round
    cands, feats, _ = found(cls, blue, hgt, barriers=walls(np.zeros(cls.shape, bool)))
    assert sw(cands)["ok"] and "via" not in sw(cands) and kinds(feats).count("junction") == 2
    # a small piece of fenced ground on the straight line: the way round it is hardly longer, and is given
    pen = np.zeros(cls.shape, bool)
    pen[215:245, 150:190] = True
    cands, feats, _ = found(cls, blue, hgt, barriers=walls(pen))
    j = sw(cands)
    assert j["ok"] and j["dist"] < j["walk"] <= 1.3 * j["dist"] and len(j["via"]) >= 3
    assert not any(pen[int(round(v)), int(round(u))] for u, v in j["via"])
    assert abs(j["via"][-1][0] - CTRL[0]) < 4 and abs(j["via"][-1][1] - CTRL[1]) < 4
    assert R._apart(j["first_az"], j["back_az"]) > 10          # one sets off to the side of the straight bearing
    assert "via" not in ne(cands) and ne(cands)["ok"]          # the junction on the other side is not concerned
    w = texts.feature(dict(j, lat=1, lon=2, point=True, via=[[1, 2], [3, 4]]))
    assert w["back"].startswith(f"z křížení cest obchůzkou {j['walk']:.0f} m, nejdřív na azimut ")
    assert "přímo je překážka" in w["back"]
    assert w["via"] == [[1, 2], [3, 4]] and w["where"].startswith("křížení cest 11")
    # a long piece of it: the way round is far more than 1.3 times the straight line, the junction is no help
    pen[215:245, 30:330] = True
    cands, feats, _ = found(cls, blue, hgt, barriers=walls(pen))
    assert not sw(cands)["ok"] and all(f["px"][1] < 215 for f in feats) and ne(cands)["ok"]
    # fenced ground beside the line changes nothing, and the fenced ground itself is come to from its near edge
    side = np.zeros(cls.shape, bool)
    side[215:245, 230:300] = True
    cands, feats, _ = found(cls, blue, hgt, barriers=walls(side))
    assert sw(cands)["ok"] and "via" not in sw(cands)
    pen = [dict(kind="enclosure", px=(265.0, 230.0), size=1500.0)]
    own = R.describe(pen, cls, hgt, MPP, CTRL, SpeedModel(), walls(side))[0]
    assert own["ok"] and own["edge"] and "via" not in own and abs(own["dist"] - 47) < 5 and own["px"][1] < 220
    # ... and at 47 m from the control its edge is worth as much as a point 60 m away, not marked down as too near
    own["crowd"] = 0
    feats, _ = R.choose([own], 0.0, MPP)
    assert own["score"] == R.BASE["enclosure"]
    # a line that only clips the corner of the fenced ground: the way round is the straight line, the bearing stays
    corner = np.zeros(cls.shape, bool)
    corner[222:240, 160:176] = True
    cands, feats, _ = found(cls, blue, hgt, barriers=walls(corner))
    assert sw(cands)["ok"] and "via" not in sw(cands)
    assert texts.feature(dict(own, lat=1, lon=2, point=False))["where"].startswith("oplocenka, nejblíž 4")


def test_fenced_ground_with_a_control_in_it_can_be_entered():
    from oroute import mapdata

    class Sheet:
        m_per_px_x, W, H = MPP, 400, 400

    rgb, cls = fenced_sheet()
    Sheet.image = rgb
    obs = mapdata.obstacles(Sheet, cls)
    assert len(obs["pens"]) == 1 and obs["blocked"][152, 255] and obs["fenced"][152, 255]
    # a control stands in it: the fence has a gate, or it is no fence. The ground is not kept out of any more.
    obs = mapdata.obstacles(Sheet, cls, open_at=[(255.0, 152.0), (60.0, 60.0)])
    assert obs["pens"] == [] and not obs["blocked"].any() and not obs["fenced"].any()
    # a control beside it changes nothing, and the same holds when only a part of the map is read
    obs = mapdata.obstacles(Sheet, cls, open_at=[(200.0, 200.0)])
    assert len(obs["pens"]) == 1 and obs["blocked"][152, 255]
    box = (200, 100, 320, 220)
    assert mapdata.obstacles(Sheet, cls, box)["blocked"][152, 255]
    assert not mapdata.obstacles(Sheet, cls, box, open_at=[(255.0, 152.0)])["blocked"].any()
