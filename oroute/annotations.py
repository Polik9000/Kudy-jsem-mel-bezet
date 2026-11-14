"""What the runner says about a leg changes how its time loss is read and which legs teach the speed model.

Notes per leg (all optional):
  deliberate_stop  the stops on this leg were on purpose (drink, shoelace, helping someone)
  lost_contact     lost contact with the map
  green            "through" = really ran through the green, "around" = went round it
  fatigue          1..5
Stops within REFRESH_RADIUS of a refreshment point count as deliberate without any note.

Rules (read_leg, model_race):
  deliberate stop   its seconds are not a mistake: taken off the execution loss and off the leg time the
                    speed model sees; the leg can then count as a clean one
  lost contact      the whole loss of the leg is a mistake (not a route choice); never used for the model
  green "around"    the leg's GPS samples that fall into green are left out of the model (GPS drift put
                    them there); "through" keeps them
  fatigue 4-5       the execution loss is put down to fatigue, not to a mistake; not used for the model

What the GPS track shows (without any note), so that "route choice" means what a runner means by it:
  wandering         the track strays far off the straight line and is much longer than the best route
                    (WANDER_DEV_M, WANDER_RATIO), or the kind of mistake is a drift off the bearing: the line that
                    was run was not chosen, so its whole loss is a mistake, none of it route choice
  near the control  overshoot, circling, undershoot, relocation (oroute.mistakes): the loops near the control
                    make the line longer, and the model prices them as route; up to the time lost within 100 m
                    of the control (zone_excess) moves from route choice to mistake
parts["why"] says which of these applied (None, "wander", "control", "lost_contact").
"""
import math

import numpy as np

from . import terrain as T

REFRESH_RADIUS = 30.0  # m
CLEAN_LOSS = 60.0      # s; a leg with less estimated loss is "clean" (same threshold as bestroute.py)
FATIGUE_FROM = 4
GREEN = (T.SLOW, T.WALK, T.FIGHT)
WANDER_DEV_M = 150.0   # the same test as the explanation of bestroute.py ("looks like being lost")
WANDER_RATIO = 1.5
CONTROL_MISTAKES = ("overshoot", "circling", "undershoot", "relocation")


def _metres(lat1, lon1, lat2, lon2):
    k = 111195.0
    return math.hypot((lat2 - lat1) * k, (lon2 - lon1) * k * math.cos(math.radians(lat1)))


def deliberate_seconds(stops, note=None, refreshments=()):
    """Seconds of the leg's stops that were on purpose. stops: [{dur, lat, lon}], refreshments: [(lat, lon)].
    Returns (seconds, seconds of those that are at a refreshment point)."""
    at_refresh = sum(s["dur"] for s in stops
                     if any(_metres(s["lat"], s["lon"], la, lo) <= REFRESH_RADIUS for la, lo in refreshments))
    if note and note.get("deliberate_stop"):
        return float(sum(s["dur"] for s in stops)), float(at_refresh)
    return float(at_refresh), float(at_refresh)


def read_leg(leg, note=None, refreshments=()):
    """How to read one leg given the runner's note.

    leg: time, est_loss, stops and, when the best route was computed, best_time (model time of the best
    route) and line_time (model time of the line that was run).
    Returns dict: deliberate_s, refreshment_s, time_net, est_loss (after the stop), in_model,
      loss_total / loss_route / loss_exec (None without routes),
      parts = seconds by cause: route (route choice), mistake, fatigue, deliberate;
      why = what moved route choice to mistake (see above), or None.
    """
    note = note or {}
    d, at_refresh = deliberate_seconds(leg.get("stops") or [], note, refreshments)
    d = min(d, leg["time"])
    net = leg["time"] - d
    est = max(0.0, leg["est_loss"] - d)
    lost = bool(note.get("lost_contact"))
    tired = (note.get("fatigue") or 0) >= FATIGUE_FROM
    # a line drawn by hand where the GPS failed is not a measurement: the model does not learn from that leg
    drawn = bool(note.get("corrected"))
    out = dict(deliberate_s=d, refreshment_s=at_refresh, time_net=net, est_loss=est,
               in_model=est < CLEAN_LOSS and not lost and not tired and not drawn,
               loss_total=None, loss_route=None, loss_exec=None)
    if leg.get("best_time") is not None and leg.get("line_time") is not None:
        out.update(loss_total=net - leg["best_time"], loss_route=leg["line_time"] - leg["best_time"],
                   loss_exec=net - leg["line_time"])
        # by cause, never more than the leg really lost (running faster than the model on a longer
        # line gives a negative execution loss; that cancels part of the route loss)
        total = max(0.0, out["loss_total"])
        route = min(max(0.0, out["loss_route"]), total)
        execution = total - route
    else:
        route, execution = 0.0, est
    why = None
    if lost:
        why = "lost_contact"
    elif route > 0:
        kind = (leg.get("mistake") or {}).get("type")
        line, best = leg.get("line") or {}, leg.get("best") or {}
        wander = (kind == "drift" or (leg.get("max_dev") or 0) > WANDER_DEV_M
                  and (line.get("dist") or 0) > WANDER_RATIO * (best.get("dist") or float("inf")))
        if wander:
            execution, route, why = execution + route, 0.0, "wander"
        elif kind in CONTROL_MISTAKES and (leg.get("zone_excess") or 0) > 0:
            moved = min(route, float(leg["zone_excess"]))
            execution, route, why = execution + moved, route - moved, "control"
    parts = dict(route=route, mistake=execution, fatigue=0.0, deliberate=d)
    if lost:
        parts.update(route=0.0, mistake=route + execution)
    elif tired:
        parts.update(mistake=0.0, fatigue=execution)
    out["why"] = why
    out["parts"] = parts
    return out


def model_race(samples, reads, notes=None):
    """One race for oroute.personal.fit: the legs that count, given how each was read.

    samples: arrays of leg_samples.npz (every leg of the race) plus title and date;
    reads: {leg number: read_leg(...)}; notes: {leg number: note}.
    Without notes and refreshment points this is exactly what bestroute.py saves as fit_samples.npz.
    Returns None when no leg counts.
    """
    notes = notes or {}
    ids = [int(k) for k in samples["leg_ids"]]
    keep = [k for k in ids if k in reads and reads[k]["in_model"]]
    if not keep:
        return None
    m = np.isin(samples["leg"], keep)
    around = [k for k in keep if (notes.get(k) or {}).get("green") == "around"]
    if around:
        m &= ~(np.isin(samples["leg"], around) & np.isin(samples["cls"], GREEN))
    lm = np.isin(samples["line_leg"], keep)
    sel = np.isin(ids, keep)
    race = {k: np.asarray(samples[k])[m] for k in ("dist", "dt", "cls", "grade", "leg")}
    race.update({k: np.asarray(samples[k])[lm] for k in ("line_d", "line_cls", "line_grade", "line_leg")})
    race.update(leg_ids=np.asarray(samples["leg_ids"])[sel],
                leg_times=np.array([reads[k]["time_net"] for k in keep], float),
                title=str(samples["title"]), date=str(samples["date"]))
    # how long the race took, for the race-length factor (older files: the last sample's time since the start)
    if "race_s" in samples:
        race["race_s"] = float(samples["race_s"])
    elif "tsec" in samples and len(samples["tsec"]):
        race["race_s"] = float(np.max(samples["tsec"]))
    return race
