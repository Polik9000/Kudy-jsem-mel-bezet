"""The best route of an average runner next to yours (oroute/generic.py) on a made-up map with a hill:
a runner strong uphill goes over the hill, the textbook model goes round it."""
import numpy as np

from oroute import generic as G
from oroute import terrain as T
from oroute.routing import Grid
from oroute.speedmodel import SpeedModel

H, W = 220, 320
A, B = (30.0, 110.0), (290.0, 110.0)


def hill_world(top=25.0, sigma=45.0):
    cls = np.full((H, W), T.FOREST, np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    hgt = top * np.exp(-((xx - 160) ** 2 + (yy - 110) ** 2) / (2 * sigma ** 2))
    return cls, hgt.astype(np.float32)


def strong_uphill():
    return SpeedModel(v_flat=3.5, up_k=1.0, down_gain=2.5, steep_down=1.0)


def both_routes(model, avg, cls, hgt, mpp=1.0):
    grid = Grid(cls, hgt, mpp, model, step=2)
    _, inner = grid.route(A, B)
    mine = [A] + inner + [B]
    grid.with_model(avg)
    _, inner = grid.route(A, B)
    return mine, [A] + inner + [B]


def test_strong_uphill_runner_goes_over_the_hill_and_the_average_one_round_it():
    cls, hgt = hill_world()
    model = strong_uphill()
    avg = G.average_model(model)
    assert (avg.up_k, avg.v_flat, avg.factors) == (9.0, 3.5, SpeedModel().factors)   # textbook, your speed
    mine, theirs = both_routes(model, avg, cls, hgt)
    r = G.compare(mine, theirs, cls, hgt, 1.0, model, avg, A, B)
    assert r["M_mine"]["climb"] > r["M_avg"]["climb"] + 10          # yours over the top, theirs round it
    assert r["differs"] and r["apart"] > G.APART_SHARE
    assert r["gain"] > G.LEVEL_S                                     # the average route costs you more
    assert r["reason"]["kind"] == "up" and r["reason"]["pct"] > 0.1   # uphill you are faster than average
    assert r["side"] in ("left", "right")
    cs = G.sentence(r, "cs")
    assert cs.startswith("Běžec s průměrným modelem by kopec obíhal (") or "by kopec obíhal vlevo" in cs \
        or "by kopec obíhal vpravo" in cs, cs
    assert "Pro tebe je rychlejší přes kopec (" in cs and "do kopce běžíš o" in cs, cs
    assert G.mmss(r["time"]) in cs and G.mmss(r["M_mine"]["time"]) in cs     # the times the page shows elsewhere
    assert "faster than average" in G.sentence(r, "en")


def test_without_an_own_slope_only_terrain_can_differ_and_here_everyone_runs_the_same():
    cls, hgt = hill_world()
    model = strong_uphill()
    avg = G.average_model(model, own_slope=False)       # the slope is the default prior: nothing to compare
    assert (avg.up_k, avg.down_gain, avg.steep_down) == (model.up_k, model.down_gain, model.steep_down)
    mine, theirs = both_routes(model, avg, cls, hgt)
    r = G.compare(mine, theirs, cls, hgt, 1.0, model, avg, A, B)
    assert not r["differs"] and r["reason"] is None
    assert G.sentence(r, "cs") == "Tady by stejně běžel každý."


def test_a_runner_fast_in_green_goes_through_it_and_the_reason_is_the_green():
    cls, hgt = hill_world(top=0.0)
    cls[60:160, 130:190] = T.WALK                       # a green block across the line
    f = dict(SpeedModel().factors)
    f[T.WALK] = 0.7                                     # walking pace in green for the average, a run for you
    model = SpeedModel(v_flat=3.5, factors=f)
    avg = G.average_model(model)
    mine, theirs = both_routes(model, avg, cls, hgt)
    r = G.compare(mine, theirs, cls, hgt, 1.0, model, avg, A, B)
    assert r["differs"] and r["reason"]["kind"] == "terrain" and r["reason"]["cls"] == "green (walk)"
    cs = G.sentence(r, "cs")
    assert "by zelenou obíhal" in cs, cs
    assert "Pro tebe je rychlejší přes zelenou" in cs and "v zelené běžíš o 133 % rychleji než průměr" in cs, cs


def test_apart_and_side():
    straight = [(0.0, 0.0), (100.0, 0.0)]
    bow = [(0.0, 0.0), (50.0, 60.0), (100.0, 0.0)]           # v grows downwards: below the line is on the right
    assert G.apart(straight, straight, 1.0) == 0.0
    assert G.apart(straight, bow, 1.0) > 0.3
    assert G.side(bow, straight, (0.0, 0.0), (100.0, 0.0)) == "right"
    assert G.side([(0.0, 0.0), (50.0, -60.0), (100.0, 0.0)], straight, (0.0, 0.0), (100.0, 0.0)) == "left"


def test_the_stretch_with_the_most_descent_lies_in_a_valley_on_a_path():
    cls = np.full((H, W), T.FOREST, np.uint8)
    cls[108:113, :] = T.PATH                                   # a path down the valley
    yy, xx = np.mgrid[0:H, 0:W]
    hgt = (60 - 0.15 * xx + 5 * (1 - np.exp(-((yy - 110) ** 2) / (2 * 15.0 ** 2)))).astype(np.float32)
    h = G.hill_stretch([A, B], cls, hgt, 1.0)
    assert h["land"] == "valley" and h["on"] == T.PATH and h["drop"] > 5 and 0.1 < h["grade"] < 0.2
    ridge = (60 - 0.15 * xx - 5 * (1 - np.exp(-((yy - 110) ** 2) / (2 * 15.0 ** 2)))).astype(np.float32)
    assert G.hill_stretch([A, B], cls, ridge, 1.0)["land"] == "ridge"
    assert G.hill_stretch([A, B], cls, hgt, 1.0, up=True) is None             # it only goes down


def leg(**kw):
    r = dict(differs=True, side="left", time=201.0, gain=16.0, sprint=False,
             M_mine=dict(time=185.0, climb=20.0, dist=400.0, mix={"forest (runnable)": 300.0}),
             M_avg=dict(time=201.0, climb=22.0, dist=410.0, mix={"forest (runnable)": 290.0, "path/road": 20.0}),
             reason=dict(kind="down", cls=None, pct=-0.21),
             hill=dict(drop=15.0, grade=0.2, on=T.PATH, land="valley"),
             hill_mine=dict(drop=8.0, grade=0.08, on=T.FOREST, land="slope"))
    r.update(kw)
    return r


def test_routes_that_differ_by_steepness_only_are_told_where_the_average_one_runs_down():
    cs = G.sentence(leg(), "cs")
    assert cs == ("Běžec s průměrným modelem by seběhl údolím po cestě vlevo; tobě by ten postup trval 3:21. "
                  "Pro tebe je rychlejší tvůj nejlepší postup s mírnějším klesáním (3:05), protože z kopce jsi "
                  "o 21 % pomalejší než průměr."), cs
    assert "run down along the valley on the path on the left" in G.sentence(leg(), "en")
    # the average route goes down gently and is longer (Grand prix Silesia E4, 6-7): yours is the shorter one
    e4 = G.sentence(leg(hill=dict(drop=8.9, grade=0.152, on=T.FOREST, land="slope"),
                        hill_mine=dict(drop=13.6, grade=0.227, on=T.FOREST, land="slope"),
                        M_avg=dict(time=201.0, climb=14.4, dist=454.0, mix={"forest (runnable)": 392.0, "path/road": 62.0}),
                        M_mine=dict(time=185.0, climb=15.2, dist=412.0,
                                   mix={"forest (runnable)": 360.0, "path/road": 52.0})),
                    "cs")
    assert "by klesal pozvolna po svahu vlevo" in e4 and "rychlejší tvůj kratší nejlepší postup (3:05)" in e4, e4
    # a forest leg about as fast: a detour, not "round the forest"
    lv = G.sentence(leg(gain=1.0, reason=dict(kind="terrain", cls="forest (runnable)", pct=0.04), hill=None,
                        M_avg=dict(time=186.0, climb=20.0, dist=440.0, mix={"forest (runnable)": 440.0}),
                        M_mine=dict(time=185.0, climb=20.0, dist=400.0, mix={"forest (runnable)": 400.0})), "cs")
    assert lv.startswith("Běžec s průměrným modelem by běžel oklikou vlevo; tobě by ten postup trval skoro stejně"), lv
    # about as fast for you: the same place, no "another way"
    level = G.sentence(leg(gain=2.0), "cs")
    assert level.startswith("Běžec s průměrným modelem by seběhl údolím po cestě vlevo; tobě by ten postup trval "
                            "skoro stejně"), level
    up = G.sentence(leg(reason=dict(kind="up", cls=None, pct=0.3), hill=dict(drop=12.0, grade=0.15, on=T.FOREST,
                                                                                   land="ridge"), hill_mine=None), "cs")
    assert "by vyběhl prudce po hřbetu vlevo" in up and "s mírnějším stoupáním" in up, up


def test_a_sprint_map_has_open_areas_and_paved_areas():
    r = leg(sprint=True, reason=dict(kind="terrain", cls="open land", pct=0.13), hill=None, hill_mine=None,
            M_mine=dict(time=45.0, climb=0.0, dist=70.0, mix={"open land": 60.0, "path/road": 10.0}),
            M_avg=dict(time=52.0, climb=0.0, dist=85.0, mix={"open land": 5.0, "path/road": 80.0}), time=52.0, gain=7.0)
    cs = G.sentence(r, "cs")
    assert "by otevřenou plochu obíhal vlevo" in cs and "přes otevřenou plochu" in cs, cs
    assert "na otevřené ploše běžíš o 13 % rychleji" in cs and "louk" not in cs, cs
    assert "round the open area" in G.sentence(r, "en") and "paved areas" in G.sentence(dict(r, reason=dict(
        kind="terrain", cls="forest (runnable)", pct=0.1)), "en")
    forest = G.sentence(dict(r, sprint=False), "cs")
    assert "by louku obíhal" in forest and "na louce" in forest
    paths = G.sentence(dict(r, reason=dict(kind="terrain", cls="forest (runnable)", pct=0.1)), "cs")
    assert "po zpevněných plochách" in paths and "cest" not in paths, paths


def test_the_model_page_names_the_reasons_of_a_sprint_in_its_words():
    from webapp.views.model import reason_label
    assert reason_label("terrain", "open land", 0.13, True) == "na otevřené ploše jsi rychlejší než průměr"
    assert reason_label("terrain", "open land", 0.13) == "na louce jsi rychlejší než průměr"
