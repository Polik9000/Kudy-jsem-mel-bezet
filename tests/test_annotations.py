"""How the runner's notes change the reading of a leg and the legs used for the speed model."""
import numpy as np

from oroute import annotations as ann
from oroute import terrain as T

STOP = dict(dur=90.0, lat=50.0, lon=18.0)


def leg(time=300.0, est_loss=100.0, stops=(STOP,), best=180.0, line=200.0):
    return dict(time=time, est_loss=est_loss, stops=list(stops), best_time=best, line_time=line)


def test_plain_leg():
    r = ann.read_leg(leg())
    assert r["deliberate_s"] == 0 and r["time_net"] == 300
    assert (r["loss_total"], r["loss_route"], r["loss_exec"]) == (120, 20, 100)
    assert r["parts"] == dict(route=20, mistake=100, fatigue=0, deliberate=0)
    assert not r["in_model"]  # 100 s estimated loss: not a clean leg


def test_deliberate_stop_is_not_a_mistake():
    r = ann.read_leg(leg(), dict(deliberate_stop=1))
    assert r["deliberate_s"] == 90 and r["time_net"] == 210
    assert r["loss_exec"] == 10 and r["loss_total"] == 30 and r["loss_route"] == 20
    assert r["parts"] == dict(route=20, mistake=10, fatigue=0, deliberate=90)
    assert r["est_loss"] == 10 and r["in_model"]  # without the stop the leg is clean


def test_refreshment_stop_is_deliberate_without_a_note():
    near = (50.0002, 18.0)   # about 22 m from the stop
    far = (50.001, 18.0)     # about 111 m
    assert ann.read_leg(leg(), None, [far])["deliberate_s"] == 0
    r = ann.read_leg(leg(), None, [far, near])
    assert r["deliberate_s"] == 90 and r["refreshment_s"] == 90 and r["in_model"]
    # two stops, only the one at the refreshment point counts
    other = dict(dur=40.0, lat=50.01, lon=18.0)
    assert ann.read_leg(leg(stops=(STOP, other)), None, [near])["deliberate_s"] == 90
    assert ann.read_leg(leg(stops=(STOP, other)), dict(deliberate_stop=1), [near])["deliberate_s"] == 130


def test_lost_contact_makes_the_whole_loss_a_mistake():
    r = ann.read_leg(leg(est_loss=10.0), dict(lost_contact=1))
    assert r["parts"]["route"] == 0 and r["parts"]["mistake"] == 120
    assert not r["in_model"]  # even though the estimated loss is small


def test_fatigue():
    assert ann.read_leg(leg(est_loss=10.0), dict(fatigue=3))["in_model"]
    r = ann.read_leg(leg(est_loss=10.0), dict(fatigue=4))
    assert r["parts"] == dict(route=20, mistake=0, fatigue=100, deliberate=0) and not r["in_model"]


def test_parts_never_exceed_the_net_loss():
    # a longer line (route loss 60 s) run faster than the model expects (execution -40 s): 20 s lost in all
    r = ann.read_leg(leg(time=200.0, est_loss=0.0, stops=(), best=180.0, line=240.0))
    assert (r["loss_total"], r["loss_route"], r["loss_exec"]) == (20, 60, -40)
    assert r["parts"] == dict(route=20, mistake=0, fatigue=0, deliberate=0)
    # faster than the best route of the model: nothing lost
    assert sum(ann.read_leg(leg(time=170.0, est_loss=0.0, stops=()))["parts"].values()) == 0


def test_without_routes_only_the_estimate():
    r = ann.read_leg(dict(time=300.0, est_loss=100.0, stops=[STOP]), dict(deliberate_stop=1))
    assert r["loss_total"] is None and r["parts"] == dict(route=0, mistake=10, fatigue=0, deliberate=90)


def samples():
    """Three legs with 4 GPS samples each; legs 1 and 3 clean, leg 2 with 100 s of loss."""
    leg_of = np.repeat([1, 2, 3], 4)
    return dict(dist=np.arange(12.0), dt=np.full(12, 2.0), grade=np.zeros(12), leg=leg_of,
                cls=np.array([T.FOREST, T.WALK, T.FOREST, T.SLOW] * 3), line_d=np.arange(6.0),
                line_cls=np.full(6, T.FOREST), line_grade=np.zeros(6), line_leg=np.repeat([1, 2, 3], 2),
                leg_ids=np.array([1, 2, 3]), leg_times=np.array([100.0, 300.0, 120.0]),
                est_loss=np.array([0.0, 100.0, 5.0]), title="Race", date="2026-05-01")


def reads(notes=None, stops=()):
    s = samples()
    return {int(k): ann.read_leg(dict(time=float(t), est_loss=float(e), stops=list(stops)), (notes or {}).get(int(k)))
            for k, t, e in zip(s["leg_ids"], s["leg_times"], s["est_loss"])}


def test_model_race_without_notes_is_the_clean_legs():
    race = ann.model_race(samples(), reads())
    assert list(race["leg_ids"]) == [1, 3] and list(race["leg_times"]) == [100.0, 120.0]
    assert list(race["leg"]) == [1] * 4 + [3] * 4 and list(race["line_leg"]) == [1, 1, 3, 3]
    assert race["title"] == "Race" and race["date"] == "2026-05-01"


def test_model_race_notes_add_and_remove_legs():
    notes = {1: dict(lost_contact=1), 2: dict(deliberate_stop=1)}
    race = ann.model_race(samples(), reads(notes, stops=[STOP]), notes)
    # leg 1 is out (lost contact), leg 2 is in: its 90 s stop was on purpose, and its time is counted without it
    assert list(race["leg_ids"]) == [2, 3] and list(race["leg_times"]) == [210.0, 120.0]


def test_model_race_green_around_drops_green_samples():
    notes = {3: dict(green="around")}
    race = ann.model_race(samples(), reads(notes), notes)
    assert list(race["leg"]) == [1] * 4 + [3] * 2          # leg 3 keeps only its two forest samples
    assert set(race["cls"][race["leg"] == 3]) == {T.FOREST}
    assert list(race["line_leg"]) == [1, 1, 3, 3]          # the line (used for scaling) is unchanged
    assert ann.model_race(samples(), reads({1: dict(fatigue=5), 3: dict(lost_contact=1)})) is None


def test_wandering_is_a_mistake_not_a_route_choice():
    # the track strays 205 m off the line and is much longer than the best route: that line was not chosen
    lg = leg(stops=(), est_loss=40.0) | dict(max_dev=205.0, line=dict(dist=1300.0), best=dict(dist=600.0))
    lg.update(best_time=180.0, line_time=260.0)
    r = ann.read_leg(lg)
    assert r["parts"]["route"] == 0 and r["parts"]["mistake"] == 120 and r["why"] == "wander"
    # a drift off the bearing counts the same, however long the line
    r = ann.read_leg(leg(stops=()) | dict(mistake=dict(type="drift")))
    assert r["parts"]["route"] == 0 and r["why"] == "wander"


def test_loops_at_the_control_move_from_route_to_mistake():
    # an overshoot: 80 s of the "route" loss are the loop within 100 m of the control
    lg = leg(stops=(), best=180.0, line=300.0) | dict(mistake=dict(type="overshoot"), zone_excess=80.0)
    r = ann.read_leg(lg)
    assert r["parts"]["route"] == 40 and r["parts"]["mistake"] == 80 and r["why"] == "control"
    # never more than the route loss there was
    r = ann.read_leg(lg | dict(zone_excess=500.0))
    assert r["parts"]["route"] == 0 and r["parts"]["mistake"] == 120
    # a slow leg without a mistake in the map keeps its route choice
    r = ann.read_leg(leg(stops=()) | dict(mistake=dict(type="slow"), zone_excess=80.0))
    assert r["parts"]["route"] == 20 and r["why"] is None
