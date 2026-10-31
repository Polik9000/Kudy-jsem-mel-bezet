"""Checks of the "best routes" on small made-up terrains (seconds, no network): internal consistency,
barriers, alternatives and the sensitivity to terrain speeds (docs/pruzkum.md part 6)."""
import numpy as np

from bestroute import shifted
from oroute import terrain as T
from oroute.routing import ALT_MAX_SLOWER, Grid, crossed, route_metrics
from oroute.speedmodel import SpeedModel

MPP = 1.5


def world(h=200, w=300):
    return np.full((h, w), T.FOREST, np.uint8), np.zeros((h, w))


def crosses(pts, x):
    """Number of times a route in map px goes from one side of the vertical line u = x to the other."""
    side = np.sign(np.array([p[0] for p in pts]) - x)
    side = side[side != 0]
    return int((np.diff(side) != 0).sum())


def test_straight_in_open_forest_and_never_slower_than_any_other_line():
    cls, hgt = world()
    m = SpeedModel()
    g = Grid(cls, hgt, MPP, m)
    a, b = (20.0, 100.0), (280.0, 100.0)
    t, pts = g.route(a, b)
    best = route_metrics([a] + pts + [b], cls, hgt, MPP, m)
    straight = route_metrics([a, b], cls, hgt, MPP, m)
    assert abs(best["time"] - straight["time"]) / straight["time"] < 0.02
    # the best route is never slower than a line somebody ran, priced with the same model
    rng = np.random.default_rng(1)
    for _ in range(20):
        mid = [(float(u), float(rng.uniform(10, 190))) for u in np.linspace(40, 260, 6)]
        other = route_metrics([a] + mid + [b], cls, hgt, MPP, m)
        assert best["time"] <= other["time"] * 1.01


def test_route_takes_the_path_round_the_green():
    cls, hgt = world()
    cls[40:160, 100:200] = T.WALK                       # a block of green on the straight line
    cls[20:23, 20:281] = T.PATH                         # a path round it
    cls[20:101, 20:23] = T.PATH
    cls[20:101, 278:281] = T.PATH
    m = SpeedModel()
    a, b = (21.0, 100.0), (279.0, 100.0)
    g = Grid(cls, hgt, MPP, m)
    _, pts = g.route(a, b)
    best = route_metrics([a] + pts + [b], cls, hgt, MPP, m)
    straight = route_metrics([a, b], cls, hgt, MPP, m)
    assert best["time"] < straight["time"] and best["mix"].get("green (walk)", 0) < 5
    # loss by route choice + loss by execution = total loss, whatever the actual time was
    actual, line = 400.0, straight["time"]
    assert abs((line - best["time"]) + (actual - line) - (actual - best["time"])) < 1e-9


def test_uphill_costs_more_than_downhill():
    cls, hgt = world()
    hgt[:] = np.linspace(0, 30, cls.shape[1])[None, :]   # rises to the east
    m = SpeedModel()
    g = Grid(cls, hgt, MPP, m)
    up, _ = g.route((20.0, 100.0), (280.0, 100.0))
    down, _ = g.route((280.0, 100.0), (20.0, 100.0))
    assert up > down * 1.2


def test_forbidden_line_is_only_crossed_at_a_crossing():
    cls, hgt = world()
    m = SpeedModel()
    a, b = (40.0, 60.0), (260.0, 60.0)
    rail = [(150.0, 0.0), (150.0, 199.0)]                # a railway right across the map
    free, _ = Grid(cls, hgt, MPP, m).route(a, b)
    # no crossing at all: the control behind the line cannot be reached
    t, pts = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[rail], hard=[], crossings=[])).route(a, b)
    assert not np.isfinite(t) and pts == []
    # a level crossing far down: the route goes there, and crosses exactly once, at the crossing
    g = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[rail], hard=[], crossings=[(150.0, 170.0)]))
    t, pts = g.route(a, b)
    assert np.isfinite(t) and t > free * 1.3 and crosses(pts, 150) == 1
    at = min(pts, key=lambda p: abs(p[0] - 150))
    assert abs(at[1] - 170) * MPP < 15


def test_hard_line_costs_time_but_can_be_crossed():
    cls, hgt = world()
    m = SpeedModel()
    a, b = (40.0, 60.0), (260.0, 60.0)
    fence = [(150.0, 0.0), (150.0, 199.0)]
    free, _ = Grid(cls, hgt, MPP, m).route(a, b)
    hard, pts = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[fence], crossings=[])).route(a, b)
    assert 60 < hard - free < 130 and crosses(pts, 150) == 1
    # with a gap (gate) nearby the route uses it instead of climbing the fence
    gate, pts = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[fence], crossings=[(150.0, 90.0)])).route(a, b)
    assert gate - free < 30 and abs(min(pts, key=lambda p: abs(p[0] - 150))[1] - 90) * MPP < 15


def test_masked_ground_is_kept_out_of_and_a_crossing_does_not_open_it():
    cls, hgt = world()
    m = SpeedModel()
    a, b = (40.0, 100.0), (260.0, 100.0)
    pen = np.zeros(cls.shape, bool)
    pen[60:140, 130:170] = True                          # fenced ground on the straight line
    free, _ = Grid(cls, hgt, MPP, m).route(a, b)
    g = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[], crossings=[(150.0, 100.0)], mask=pen))
    t, pts = g.route(a, b)
    assert np.isfinite(t) and t > free * 1.05
    assert not any(130 <= u < 170 and 60 <= v < 140 for u, v in pts)
    # a strip right across, two cells thick (no move of the grid jumps it), leaves no way round
    wall = np.zeros(cls.shape, bool)
    wall[:, 149:152] = True
    t, pts = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[], crossings=[], mask=wall)).route(a, b)
    assert not np.isfinite(t)
    # a control inside the mask is come to from its edge
    t, pts = g.route(a, (150.0, 100.0))
    assert np.isfinite(t) and pts[-1][0] < 131


def test_crossed_tells_what_a_track_went_through():
    rail = [(150.0, 0.0), (150.0, 199.0)]
    b = dict(forbidden=[rail], hard=[], crossings=[(150.0, 170.0)], areas=[], origin=[dict(source="osm", what="railway")])
    straight = [(40.0 + 5 * i, 60.0) for i in range(45)]              # west to east across the line
    c = crossed(straight, b, MPP)
    assert [x["what"] for x in c] == ["railway"] and c[0]["kind"] == "line"
    assert abs(c[0]["px"][0] - 150) < 1e-6 and abs(c[0]["px"][1] - 60) < 1e-6
    # at the crossing it is allowed
    assert crossed([(40.0 + 5 * i, 172.0) for i in range(45)], b, MPP) == []
    # a track along the line that wobbles over it (GPS) did not cross it
    along = [(150.0 + (3 if i % 2 else -3), 5.0 + 4 * i) for i in range(30)]
    assert crossed(along, b, MPP) == []
    # a line without a name was drawn by hand; a hard line is not forbidden
    assert crossed(straight, dict(forbidden=[rail], hard=[], crossings=[]), MPP)[0]["what"] == "manual"
    assert crossed(straight, dict(forbidden=[], hard=[rail], crossings=[]), MPP) == []
    # fenced ground and an out-of-bounds area: entered when the track runs well inside, not along the edge
    pen = np.zeros((200, 300), bool)
    pen[40:80, 130:170] = True
    assert [x["what"] for x in crossed(straight, dict(mask=pen), MPP)] == ["enclosure"]
    assert crossed([(40.0 + 5 * i, 42.0) for i in range(45)], dict(mask=pen), MPP) == []
    area = [(130.0, 40.0), (170.0, 40.0), (170.0, 80.0), (130.0, 80.0)]
    assert [x["kind"] for x in crossed(straight, dict(areas=[area]), MPP)] == ["area"]
    assert crossed(straight, None, MPP) == [] and crossed(straight[:1], b, MPP) == []


def lake_world():
    """A lake in the middle: round it to the north through forest or to the south along a path."""
    cls, hgt = world()
    cls[60:140, 110:190] = T.WATER
    cls[150:153, 20:281] = T.PATH
    return cls, hgt


def test_alternatives_are_different_routes_with_honest_times():
    cls, hgt = lake_world()
    m = SpeedModel()
    a, b = (30.0, 100.0), (270.0, 100.0)
    g = Grid(cls, hgt, MPP, m)
    t, pts = g.route(a, b)
    alts = g.alternatives(a, b, k=2, best=(t, pts))
    assert 1 <= len(alts) <= 2
    side = lambda p: np.sign(np.mean([v for u, v in p if 110 < u < 190]) - 100)
    assert side(alts[0][1]) != side(pts)                 # the other way round the lake
    for ta, pa in alts:
        assert t - 1e-6 <= ta <= t * (1 + ALT_MAX_SLOWER) + 30
        # the time given is the real one, not the penalised one the search used
        real = route_metrics([a] + pa + [b], cls, hgt, MPP, m)["time"]
        assert abs(real - ta) / ta < 0.05
    assert g.alternatives(a, b, k=0, best=(t, pts)) == []
    # nothing to offer where every route has to squeeze through the same gap
    cls2, _ = world()
    cls2[:, 148:152] = T.WATER
    cls2[98:103, 148:152] = T.FOREST
    g2 = Grid(cls2, hgt, MPP, m)
    assert g2.alternatives((140.0, 100.0), (160.0, 100.0), k=2) == []


def test_level_routes_flip_when_terrain_speeds_shift():
    cls, hgt = lake_world()
    m = SpeedModel()
    a, b = (30.0, 100.0), (270.0, 100.0)
    g = Grid(cls, hgt, MPP, m)
    t, pts = g.route(a, b)
    best = [a] + pts + [b]
    alt = [a] + g.alternatives(a, b, k=1, best=(t, pts))[0][1] + [b]
    price = lambda line, model: route_metrics(line, cls, hgt, MPP, model)["time"]
    gap = price(alt, m) - price(best, m)
    assert gap >= 0
    # off-path terrain 20 % faster or slower moves the two routes against each other ...
    moves = [price(alt, shifted(m, f)) - price(best, shifted(m, f)) for f in (0.8, 1.2)]
    assert min(moves) < gap < max(moves)
    # ... and the paths themselves keep their speed
    assert shifted(m, 0.8).factors[T.PATH] == m.factors[T.PATH]
    assert abs(shifted(m, 0.8).factors[T.FOREST] - 0.8 * m.factors[T.FOREST]) < 1e-12


def test_hard_line_given_as_a_picture_costs_a_crossing_and_keeps_the_path_beside_it():
    cls, hgt = world()
    m = SpeedModel()
    a, b = (40.0, 60.0), (260.0, 60.0)
    fence = np.zeros(cls.shape, bool)
    fence[:, 150:152] = True
    free, _ = Grid(cls, hgt, MPP, m).route(a, b)
    hard, pts = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[], crossings=[], hard_mask=fence)).route(a, b)
    assert 50 < hard - free < 140 and crosses(pts, 150.5) == 1
    # a gap in the fence is used; a path running 6 m beside the fence is as fast as without it
    fence[80:96] = False
    gap, pts = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[], crossings=[], hard_mask=fence)).route(a, b)
    assert gap - free < 30 and 80 <= min(pts, key=lambda p: abs(p[0] - 150.5))[1] <= 96
    cls[:, 146] = T.PATH
    up, down = (146.0, 20.0), (146.0, 180.0)
    fence[:] = False
    fence[:, 150:152] = True
    beside, _ = Grid(cls, hgt, MPP, m, barriers=dict(forbidden=[], hard=[], crossings=[], hard_mask=fence)).route(up, down)
    alone, _ = Grid(cls, hgt, MPP, m).route(up, down)
    assert abs(beside - alone) < 2.0


def test_a_control_walled_in_is_reached_as_near_as_one_can_get():
    cls, hgt = world()
    cls[80:120, 180:220] = T.WATER                   # a pond ...
    cls[95:105, 195:205] = T.FOREST                  # ... with an island the control stands on
    g = Grid(cls, hgt, MPP, SpeedModel())
    shore = lambda p: max(abs(p[0] - 200), abs(p[1] - 100)) <= 23 and cls[int(p[1]), int(p[0])] != T.WATER
    t, pts = g.route((30.0, 100.0), (200.0, 100.0))
    # no way to the island: the route ends at the shore next to it, it is not missing (a straight line
    # through the water would be drawn in its place)
    assert np.isfinite(t) and len(pts) > 20 and shore(pts[-1])
    assert route_metrics(pts, cls, hgt, MPP, SpeedModel())["mix"].get(T.NAMES[T.WATER], 0.0) == 0.0
    t2, back = g.route((200.0, 100.0), (30.0, 100.0))
    assert np.isfinite(t2) and shore(back[0]) and abs(t2 - t) < 0.1 * t
    # two points on the island are joined on the island, as before
    t3, on = g.route((197.0, 97.0), (203.0, 103.0))
    assert np.isfinite(t3) and all(195 <= u <= 205 and 95 <= v <= 105 for u, v in on)
    # two large pieces of ground with water right across between them: no route, as before
    cls[:, 100:104] = T.WATER
    assert not np.isfinite(Grid(cls, hgt, MPP, SpeedModel()).route((30.0, 100.0), (150.0, 100.0))[0])


def test_a_track_a_few_metres_inside_a_garden_is_priced_as_the_street_beside_it():
    cls, hgt = world()
    m = SpeedModel()
    cls[90:110] = T.OOB                              # gardens on both sides ...
    cls[97:103] = T.OPEN                             # ... of a street 9 m wide
    street = [(20.0, 100.0), (280.0, 100.0)]
    drift = [(20.0, 100.0), (100.0, 105.0), (200.0, 95.0), (280.0, 100.0)]      # GPS: up to 4 m into the gardens
    on = route_metrics(street, cls, hgt, MPP, m)
    plain = route_metrics(drift, cls, hgt, MPP, m)
    beside = route_metrics(drift, cls, hgt, MPP, m, beside_m=8.0)
    assert plain["time"] > 1.3 * on["time"]          # as it was: the samples in the gardens at a walk
    assert abs(beside["time"] - on["time"]) < 0.03 * on["time"] and T.NAMES[T.OOB] not in beside["mix"]
    # a line 20 m deep in ground out of bounds is not next to anything: priced at a walk as before
    deep = np.full((200, 300), T.OOB, np.uint8)
    deep[:20] = T.FOREST
    far = [(20.0, 60.0), (280.0, 60.0)]
    assert route_metrics(far, deep, hgt, MPP, m, beside_m=8.0)["time"] == route_metrics(far, deep, hgt, MPP, m)["time"]
    # and a best route (no beside_m) is priced exactly as it runs
    assert route_metrics(drift, cls, hgt, MPP, m)["mix"][T.NAMES[T.OOB]] > 50


def test_a_track_along_a_path_a_few_metres_beside_it_is_on_the_path_and_one_across_it_is_not():
    """GPS or the placing of the map puts a track 10 m beside the path it was run on: priced as the path. A track
    that crosses the path, or runs further away from it, keeps the terrain under it (decided on 11 Oct 2026)."""
    from oroute.routing import PATH_SIDE_M, along_path, route_samples
    cls = np.full((200, 300), T.FOREST, np.uint8)
    cls[100, 20:280] = T.PATH                                   # a path from west to east, 1 m per pixel
    hgt = np.zeros(cls.shape, np.float32)
    beside = [(30.0, 110.0), (270.0, 110.0)]                    # 10 m south of it, all along
    d, c, _, _ = route_samples(beside, cls, hgt, 1.0, on_path_m=PATH_SIDE_M)
    assert (c == T.PATH).mean() > 0.9
    d, c, _, _ = route_samples(beside, cls, hgt, 1.0)           # without the rule: forest, as before
    assert not (c == T.PATH).any()
    across = [(150.0, 20.0), (150.0, 180.0)]                    # straight across the path
    assert not along_path(*np.array(_dense(across)).T, cls, 1.0).any()
    far = [(30.0, 125.0), (270.0, 125.0)]                       # 25 m beside it: another way
    assert not along_path(*np.array(_dense(far)).T, cls, 1.0).any()
    short = [(110.0, 150.0), (140.0, 110.0), (160.0, 110.0), (190.0, 150.0)]  # up to it, 20 m along, away
    on = along_path(*np.array(_dense(short)).T, cls, 1.0)
    assert not on.any()


def _dense(pts, step=2.0):
    out = []
    for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
        n = max(1, int(np.hypot(u1 - u0, v1 - v0) / step))
        out += [(u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * k / n) for k in range(n)]
    return out + [pts[-1]]
