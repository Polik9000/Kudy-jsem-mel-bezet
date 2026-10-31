"""What kind of mistake was made at a control, read from the shape of the GPS track (rules, no AI), and a
suggested attack point read from the paths of the map.

classify() looks at one leg that lost time and returns the first rule that fits (docs/pruzkum.md part 5):

  overshoot    the track passes within PASS_M of the control, runs on at least OVER_M and comes back
  circling     inside CIRCLE_M of the control the heading turns by TURN_DEG or more in total
  undershoot   a stop or a clear slow-down NEAR_LO..NEAR_HI m before the control, without running past it
  drift        most of the leg is run beside the straight line and the control is reached nearly at a right
               angle to the direction of the leg (the bearing was off)
  relocation   a stop followed by a change of direction of RELOC_DEG or more (finding where one is)
  slow         none of these: the line is reasonable, only slower than usual (fitness or footing, not the map)

The thresholds were set on the four races in data/ (see docs/validace.md); they are module constants so a
later tuning on more runners only changes numbers.
"""
import math

import numpy as np

MIN_LOSS_S = 40.0     # legs that lost less are not looked at
PASS_M = 40.0         # "passed the control": came this close ...
PASS_EARLY_S = 25.0   # ... at least this long before punching it
OVER_M = 35.0         # ran on this far past the control (along the direction of the leg) or away from it
CIRCLE_M = 100.0
TURN_DEG = 360.0
CIRCLE_MIN_S = 45.0
NEAR_LO, NEAR_HI = 40.0, 160.0
SLOW_SHARE = 0.45     # "clearly slower": below this share of the runner's reference speed ...
SLOW_MIN_S = 15.0     # ... for at least this long
DRIFT_MIN_LEG_M = 200.0
DRIFT_AT = 0.8        # where along the leg the side offset is measured
DRIFT_SIDE_M = 35.0   # side offset there, at least this and at least DRIFT_SIDE_SHARE of the leg length
DRIFT_SIDE_SHARE = 0.12
DRIFT_ANGLE_DEG = 50.0
DRIFT_FINAL_M = 40.0  # the final approach is the track from this far out
RELOC_STOP_S = 10.0
RELOC_DEG = 60.0
STEP_M = 12.0         # the track is thinned to steps of this length before headings are measured (GPS jitter)


def _thin(x, y, step=STEP_M):
    """Indices of the track points kept when walking in steps of at least `step` metres."""
    keep = [0]
    for i in range(1, len(x)):
        if math.hypot(x[i] - x[keep[-1]], y[i] - y[keep[-1]]) >= step:
            keep.append(i)
    return keep


def _turning(x, y):
    """Total absolute change of heading (degrees) along a track, measured on the thinned track."""
    k = _thin(x, y)
    if len(k) < 3:
        return 0.0
    h = np.arctan2(np.diff(y[k]), np.diff(x[k]))
    d = np.abs((np.diff(h) + np.pi) % (2 * np.pi) - np.pi)
    return float(np.degrees(d.sum()))


def _heading(x, y, i, j):
    return math.atan2(y[j] - y[i], x[j] - x[i])


def _angle(a, b):
    return abs(math.degrees((a - b + math.pi) % (2 * math.pi) - math.pi))


def classify(t, x, y, speed, leg, prev_xy, ctrl_xy, vref, min_loss=MIN_LOSS_S):
    """The kind of mistake on one leg, or None when the leg lost little.

    t, x, y, speed: the whole track (seconds, metres, m/s); leg: dict of analysis.analyse_legs/flag_legs
    (a, b, est_loss, stops); prev_xy, ctrl_xy: the two controls of the leg in metres; vref: the runner's
    reference speed. Returns dict(type, i = track index to mark, plus the numbers the wording uses).
    """
    if leg.get("est_loss", 0.0) < min_loss:
        return None
    a, b = leg["a"], leg["b"]
    if b - a < 4:
        return None
    xs, ys, ts, sp = x[a:b + 1], y[a:b + 1], t[a:b + 1], speed[a:b + 1]
    cx, cy = ctrl_xy
    L = math.hypot(cx - prev_xy[0], cy - prev_xy[1])
    ux, uy = ((cx - prev_xy[0]) / L, (cy - prev_xy[1]) / L) if L > 1 else (1.0, 0.0)
    d = np.hypot(xs - cx, ys - cy)
    along = (xs - cx) * ux + (ys - cy) * uy          # > 0: beyond the control in the direction of the leg
    side = (xs - prev_xy[0]) * uy - (ys - prev_xy[1]) * ux

    # --- overshoot: passed close, went on, came back
    close = np.nonzero(d <= PASS_M)[0]
    if len(close) and ts[-1] - ts[close[0]] >= PASS_EARLY_S:
        first = int(close[0])
        after = slice(first, len(d))
        far = first + int(np.argmax(d[after]))
        over = float(max(along[after].max(), 0.0))
        if d[far] >= PASS_M + OVER_M or over >= OVER_M:
            return dict(type="overshoot", i=a + far, miss=float(d[first:far + 1].min()), over=max(over, float(d[far])),
                        back=float(ts[-1] - ts[first]))

    # --- circling inside the control circle
    inside = np.nonzero(d <= CIRCLE_M)[0]
    if len(inside) >= 4:
        i0 = int(inside[0])
        turn = _turning(xs[i0:], ys[i0:])
        dur = float(ts[-1] - ts[i0])
        if turn >= TURN_DEG and dur >= CIRCLE_MIN_S:
            return dict(type="circling", i=b, turn=turn, time=dur)

    # --- undershoot: stopped or crawled before the control, never ran past it
    stops = [(s - a, e - a) for s, e in leg.get("stops") or []]
    near = (d >= NEAR_LO) & (d <= NEAR_HI) & (along < 0)
    best = None
    for s, e in stops:
        if near[s:e + 1].any():
            dur = float(ts[e] - ts[s])
            if best is None or dur > best[1]:
                best = (s, dur)
    if best is None and vref:
        slow = near & (sp < SLOW_SHARE * vref)
        run = 0
        for i in range(len(slow)):
            run = run + 1 if slow[i] else 0
            if run >= 2 and ts[i] - ts[i - run + 1] >= SLOW_MIN_S:
                best = (i - run + 1, float(ts[i] - ts[i - run + 1]))
                break
    if best is not None and along.max() < OVER_M:
        return dict(type="undershoot", i=a + best[0], dist=float(d[best[0]]), stop=best[1])

    # --- drift: beside the line for most of the leg, then in at a right angle
    if L >= DRIFT_MIN_LEG_M:
        prog = (xs - prev_xy[0]) * ux + (ys - prev_xy[1]) * uy
        k = int(np.argmax(prog >= DRIFT_AT * L)) if (prog >= DRIFT_AT * L).any() else None
        if k is not None and k < len(xs) - 2 and abs(side[k]) >= max(DRIFT_SIDE_M, DRIFT_SIDE_SHARE * L):
            # the direction of the last DRIFT_FINAL_M into the control
            j = next((i for i in range(len(xs) - 1, k - 1, -1) if d[i] >= DRIFT_FINAL_M), k)
            if _angle(_heading(xs, ys, j, len(xs) - 1), math.atan2(uy, ux)) >= DRIFT_ANGLE_DEG:
                return dict(type="drift", i=a + k, dev=float(np.abs(side[:k + 1]).max()))

    # --- relocation: a stop, then off in another direction
    for s, e in stops:
        if ts[e] - ts[s] < RELOC_STOP_S:
            continue
        before = next((i for i in range(s, -1, -1) if math.hypot(xs[s] - xs[i], ys[s] - ys[i]) >= 30), None)
        after = next((i for i in range(e, len(xs)) if math.hypot(xs[i] - xs[e], ys[i] - ys[e]) >= 30), None)
        if before is None or after is None:
            continue
        turn = _angle(_heading(xs, ys, before, s), _heading(xs, ys, e, after))
        if turn >= RELOC_DEG:
            return dict(type="relocation", i=a + s, stop=float(ts[e] - ts[s]), turn=turn)

    return dict(type="slow", i=None)


# --- path junctions (used by oroute.relocate) ----------------------------------------------------

RING_PX = 7     # radius of the circle on which the branches of a path are counted


def junctions(path_mask, ring=RING_PX):
    """Path junctions in a boolean mask of path pixels: [(u, v)] in mask pixels.

    Around every path pixel the path is sampled on a circle of radius `ring`; the number of separate arcs
    of path on that circle is the number of branches leaving the pixel. Three or more = a junction.
    Neighbouring junction pixels are merged into one point (their centre)."""
    from scipy import ndimage as ndi
    H, W = path_mask.shape
    vs, us = np.nonzero(path_mask)
    if not len(us):
        return []
    ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    du, dv = np.round(ring * np.cos(ang)).astype(int), np.round(ring * np.sin(ang)).astype(int)
    uu = np.clip(us[:, None] + du[None], 0, W - 1)
    vv = np.clip(vs[:, None] + dv[None], 0, H - 1)
    on = path_mask[vv, uu]
    branches = (on & ~np.roll(on, 1, axis=1)).sum(1)
    j = np.zeros((H, W), bool)
    j[vs[branches >= 3], us[branches >= 3]] = True
    lab, n = ndi.label(ndi.binary_dilation(j, iterations=2))
    if not n:
        return []
    return [(float(c[1]), float(c[0])) for c in ndi.center_of_mass(j, lab, range(1, n + 1))]
