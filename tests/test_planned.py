"""The planned route of a leg priced by the speed model (oroute/planned.py) on made-up terrain, and the
sentence that compares it with the best route and with what was run."""
import numpy as np

from oroute import planned
from oroute import terrain as T
from oroute.routing import route_metrics
from oroute.speedmodel import SpeedModel

MPP = 1.5


def world(h=100, w=220):
    """Open land in the west, green to walk through in the east; flat."""
    cls = np.full((h, w), T.OPEN, np.uint8)
    cls[:, 110:] = T.WALK
    return cls, np.zeros((h, w))


def test_straight_line_over_fast_and_slow_terrain_takes_the_expected_time():
    cls, hgt = world()
    m = SpeedModel()
    line = [(10.0, 50.0), (210.0, 50.0)]             # 150 m of open land, then 150 m of green
    want = 150 / (m.v_flat * m.factors[T.OPEN]) + 150 / (m.v_flat * m.factors[T.WALK])
    P = planned.price(line, cls, lambda u, v: np.zeros(u.shape), MPP, m)
    assert abs(P["time"] - want) / want < 0.015 and abs(P["dist"] - 300) < 0.01 and P["climb"] == 0
    assert abs(P["mix"]["open land"] - 150) <= 2 and abs(P["mix"]["green (walk)"] - 150) <= 2
    # the cut-out of the map around the line gives the same numbers as the whole map does for the other routes
    assert P == route_metrics(line, cls, hgt, MPP, m)
    # the same line the other way round on a slope: uphill is slower, by what the model says about climbing
    slope = lambda u, v: 0.1 * MPP * u                # 10 % up to the east
    up = planned.price(line, cls, slope, MPP, m)
    down = planned.price(line[::-1], cls, slope, MPP, m)
    assert abs(up["climb"] - 30) < 0.5 and down["climb"] == 0
    assert abs(up["time"] - want * (1 + m.up_k * 0.1)) / up["time"] < 0.015 and down["time"] < want < up["time"]


def test_line_that_leaves_the_map_is_priced_like_on_the_whole_map():
    cls, hgt = world()
    m = SpeedModel()
    line = [(-30.0, 20.0), (60.0, -15.0), (260.0, 130.0)]
    assert planned.price(line, cls, lambda u, v: np.zeros(u.shape), MPP, m) == route_metrics(line, cls, hgt, MPP, m)


def test_how_far_the_track_ran_from_the_plan():
    plan = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]
    on = [(x, 3.0) for x in range(0, 100, 5)] + [(97.0, y) for y in range(0, 100, 5)]
    assert planned.off_plan(on, plan) <= 3.0
    cut = [(d, d) for d in range(0, 101, 5)]          # the diagonal: 71 m from the corner of the plan
    assert 40 < planned.off_plan(cut, plan) <= 50
    assert planned.off_plan([], plan) is None


def test_sentence_about_the_plan():
    m = SpeedModel()
    forest = lambda time, dist, climb=10.0: dict(time=time, dist=dist, climb=climb, mix={"forest (runnable)": dist})
    B = forest(200, 600)
    say = lambda P, Y, actual, off=None: planned.explain(P, B, Y, actual, m, off, "cs")
    # as fast as the best route and run without a loss
    assert say(forest(205, 610), forest(205, 610), 210) == "Plán byl dobrý a úsek jsi zaběhl bez ztráty."
    # a good plan, the time was lost while running it: on the plan, or away from it
    text = say(forest(205, 610), forest(205, 610), 290, off=12.0)
    assert text == "Plán byl dobrý, ztráta 1:25 vznikla při provedení: plánu ses držel, jen pomaleji, než odpovídá " \
                   "tvému tempu."
    assert say(forest(205, 610), forest(260, 800), 290, off=85.0).endswith("od plánu ses odchýlil až o 85 m.")
    # a slower plan says what makes it slower: the thing that costs most
    assert say(forest(225, 610, 50.0), forest(225, 610), 230) == \
        "Plán byl o 0:25 pomalejší než nejlepší postup, hlavně kvůli 40 m stoupání navíc."
    assert "hlavně proto, že je o 200 m delší" in say(forest(270, 800), forest(270, 800), 270)
    green = dict(time=260, dist=620, climb=10.0, mix={"forest (runnable)": 500, "green (walk)": 120})
    assert "hlavně kvůli 120 m v zelené nebo bažině navíc" in say(green, green, 260)
    paths = dict(B, mix={"path/road": 400, "forest (runnable)": 200})
    assert "o 400 m méně po cestách" in planned.explain(forest(240, 600), paths, forest(240, 600), 240, m, None, "cs")
    # ... and when more was lost on top of it
    text = say(forest(225, 610, 50.0), forest(225, 610), 300, off=10.0)
    assert "pomalejší než nejlepší postup" in text and "Dalších 1:15 jsi ztratil při provedení" in text
    # the runner did not run the plan and what they ran was faster
    text = say(forest(270, 800), forest(210, 620), 215, off=120.0)
    assert text.endswith("Plán jsi neběžel (až 120 m od něj) a postup, který jsi běžel, byl o 1:00 rychlejší.")
    # a hand-drawn line that beats the best route found: said, not hidden
    assert say(forest(170, 560), forest(205, 610), 210).startswith("Plán vychází o 0:30 rychlejší")
    # the English wording follows the same rules
    assert planned.explain(forest(205, 610), B, forest(205, 610), 210, m, None, "en") == \
        "The plan was good and you ran the leg without a loss."


def test_plan_through_what_the_best_route_must_not_says_so():
    from oroute.routing import crossed
    m = SpeedModel()
    M = lambda time, dist: dict(time=time, dist=dist, climb=10.0, mix={"forest (runnable)": dist})
    P, B = M(170, 400), M(200, 480)
    rail = [dict(kind="line", what="railway", px=(1.0, 2.0))]
    cs = planned.explain(P, B, B, 200, m, lang="cs", through=rail)
    assert cs == "Plán vychází o 0:30 rychlejší než nejlepší postup, protože kříží železnici mimo přechod, kudy " \
                 "nejlepší postup nesmí."
    assert "railway" in planned.explain(P, B, B, 200, m, through=rail)
    # a plan that is not faster still says what it goes through; without anything in the way nothing changes
    S = M(260, 520)
    slow = planned.explain(S, B, B, 262, m, lang="cs", through=[dict(kind="enclosure", what="enclosure", px=(1, 2))])
    assert slow.endswith("Pozor: plán vede přes oplocenku, kudy nejlepší postup nesmí.")
    assert planned.explain(S, B, B, 262, m, lang="cs") == planned.explain(S, B, B, 262, m, lang="cs", through=[])
    # the line of a plan across fenced ground and across a forbidden line away from its crossing
    pen = np.zeros((200, 300), bool)
    pen[80:120, 100:160] = True
    found = crossed([(20.0, 100.0), (280.0, 100.0)], dict(forbidden=[[(220.0, 0.0), (220.0, 199.0)]], hard=[],
                                                          crossings=[(220.0, 20.0)], areas=[], mask=pen,
                                                          origin=[dict(source="osm", what="railway")]), 1.5)
    assert sorted(c["what"] for c in found) == ["enclosure", "railway"]


def test_a_plan_over_a_fence_pays_the_crossing_the_best_route_would():
    hard = np.zeros((100, 200), bool)
    hard[:, 100:102] = True                          # a fence across the way
    px = np.array([[10.0, 50.0], [190.0, 50.0]])
    assert planned.fence_crossings(px, hard) == 1
    assert planned.fence_crossings(np.array([[10.0, 50.0], [190.0, 50.0], [10.0, 60.0]]), hard) == 2
    assert planned.fence_crossings(px, np.zeros((100, 200), bool)) == 0
