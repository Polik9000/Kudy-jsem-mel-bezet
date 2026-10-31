"""Split a GPS track into legs and flag likely mistakes."""
import numpy as np

from .errors import InputError

NO_DATA_M = 150.0     # a control the track never came this close to was not recorded (or not visited)
OFF_COURSE_M = 30.0   # the track is not a run of this course when at its closest it stays this far from the
                      # controls (median; a run of the course comes within 10 m of most, GPS and all)


def track_xy(geomap, track):
    x, y = geomap.to_xy(track["lat"], track["lon"])
    return np.asarray(x), np.asarray(y)


def smooth_speed(t, x, y, win=3):
    """Speed (m/s) per point from a centred difference over +-win samples."""
    n = len(t)
    i0 = np.clip(np.arange(n) - win, 0, n - 1)
    i1 = np.clip(np.arange(n) + win, 0, n - 1)
    d = np.hypot(x[i1] - x[i0], y[i1] - y[i0])
    dt = np.maximum(t[i1] - t[i0], 1e-6)
    return d / dt


def find_punches(t, x, y, points, radius=25.0):
    """Punch index per course point (start, controls..., finish), in order.

    For each control, look forward from the previous punch for the first visit that
    comes within `radius` m (or within 15 m of the closest approach if GPS never
    gets that close) and take the closest point of that visit.
    """
    idx = [0]
    for k, (cx, cy) in enumerate(points[1:], start=1):
        lo = idx[-1]
        d = np.hypot(x[lo:] - cx, y[lo:] - cy)
        # don't let a later control be taken before this leg has really started
        thr = max(radius, d.min() + 15)
        inside = np.nonzero(d <= thr)[0]
        first = inside[0]
        end = first
        while end + 1 < len(d) and d[end + 1] <= thr + 20:
            end += 1
        j = first + int(np.argmin(d[first:end + 1]))
        if k == len(points) - 1:
            # finish = end of recording if it ends there, unless he stood around after finishing
            if d[-1] < thr + 40 and t[-1] - t[lo + j] < 30:
                j = len(d) - 1
        idx.append(lo + j)
    return idx


def unrecorded(x, y, punch_idx, points, why=None):
    """The legs (numbered from 1) of a track cut at the closest approaches (find_punches) that the recording
    does not show: a leg that ends where it began, and the legs to and from a control the track never came
    within NO_DATA_M of (the watch was started late or stopped early, or the control was not visited).

    Raises InputError when the track is not a run of this course at all: it stays far from most controls
    (another activity was paired with the race, or the recording covers too little of it). why: what is
    known about the recording already (the reason the official times were not used), added to the message."""
    miss = [float(np.hypot(x[i] - p[0], y[i] - p[1])) for i, p in zip(punch_idx, points)]
    bad = {k for k in range(1, len(points)) if miss[k] > NO_DATA_M}
    legs = {k for k in range(1, len(points)) if punch_idx[k] <= punch_idx[k - 1] or k in bad or k - 1 in bad}
    mid = float(np.median(miss[1:-1])) if len(points) > 2 else miss[-1]
    if mid > OFF_COURSE_M or 2 * len(legs) > len(points) - 1:
        raise InputError("track_off_course",
                         f"the track does not follow the course: at its closest it is {mid:.0f} m from the "
                         f"controls (median) and {len(legs)} of {len(points) - 1} legs are not on it"
                         + (f"; {why}" if why else ""))
    return legs


def estimate_offset(x, y, punch_idx, points):
    """Median offset (m) between control centres and the GPS position at punch."""
    dx = [points[k][0] - x[i] for k, i in enumerate(punch_idx)][1:-1]
    dy = [points[k][1] - y[i] for k, i in enumerate(punch_idx)][1:-1]
    return float(np.median(dx)), float(np.median(dy))


def stops(t, speed, lo, hi, vmax=0.7, min_dur=6.0):
    """Stretches inside [lo, hi] where speed stays below vmax for >= min_dur s."""
    out, s = [], None
    for i in range(lo, hi + 1):
        slow = speed[i] < vmax
        if slow and s is None:
            s = i
        if (not slow or i == hi) and s is not None:
            e = i if slow else i - 1
            if t[e] - t[s] >= min_dur:
                out.append((s, e))
            s = None
    return out


def analyse_legs(track, x, y, points, punch_idx, zone=100.0, no_data=()):
    """Per-leg metrics. points = [(x,y)] in metres for start, controls..., finish.
    no_data: the legs (numbered from 1) the recording does not show (unrecorded, official.no_data_legs): they
    keep their time and straight distance, are marked no_data and take no part in the reference speed."""
    t, alt = track["t"], track["alt"]
    speed = smooth_speed(t, x, y)
    legs = []
    for k in range(1, len(points)):
        a, b = punch_idx[k - 1], punch_idx[k]
        px, py = points[k - 1]
        cx, cy = points[k]
        straight = float(np.hypot(cx - px, cy - py))
        seg = np.hypot(np.diff(x[a:b + 1]), np.diff(y[a:b + 1]))
        run = float(seg.sum())
        dt = float(t[b] - t[a])
        # deviation from the straight line
        ux, uy = (cx - px) / max(straight, 1e-6), (cy - py) / max(straight, 1e-6)
        perp = (x[a:b + 1] - px) * uy - (y[a:b + 1] - py) * ux
        # climb
        da = np.diff(alt[a:b + 1])
        climb = float(np.nansum(np.clip(da, 0, None)))
        # control zone: last time we enter `zone` m around the control, and re-entries
        d = np.hypot(x[a:b + 1] - cx, y[a:b + 1] - cy)
        inz = d <= zone
        first_in = int(np.argmax(inz)) if inz.any() else len(d) - 1
        entries = int(np.sum(np.diff(inz.astype(int)) == 1)) + (1 if inz[0] else 0)
        zone_time = float(t[b] - t[a + first_in])
        zone_dist = float(seg[first_in:].sum()) if first_in < len(seg) else 0.0
        st = [(s, e) for s, e in stops(t, speed, a, b)
              if not (t[s] - t[a] < 5 or t[b] - t[e] < 5)]  # ignore stand-still right at punch
        stop_time = float(sum(t[e] - t[s] for s, e in st))
        legs.append(dict(
            leg=k, a=a, b=b, time=dt, straight=straight, run=run,
            ratio=run / straight if straight > 0 else np.nan,
            speed=run / dt if dt > 0 else np.nan,
            straight_pace=dt / straight * 1000 / 60 if straight > 0 else np.nan,  # min/km
            climb=climb, max_dev=float(np.max(np.abs(perp))),
            zone_time=zone_time, zone_dist=zone_dist, zone_entries=entries,
            stops=st, stop_time=stop_time,
        ))
        if k in no_data:
            # nothing measured on the track means anything here; numbers, not NaN, for whoever prints them
            legs[-1].update(no_data=True, run=0.0, ratio=0.0, speed=0.0, climb=0.0, max_dev=0.0, zone_time=0.0,
                            zone_dist=0.0, zone_entries=0, stops=[], stop_time=0.0)
    return legs, speed


def flag_legs(legs, zone=100.0):
    """Add simple mistake flags and a rough time-loss estimate per leg.

    Reference speed = median running speed over the legs. Expected leg time =
    straight distance * a 'normal' route ratio (median ratio, capped to 1.1..1.35)
    / reference speed. Loss components:
      - extra distance: run distance beyond the normal ratio, at reference speed
      - control zone: time in the last `zone` m beyond what reference speed needs
      - stops: time stood still mid-leg
    These overlap, so 'est_loss' is leg time minus expected time, not their sum.
    """
    seen = [l for l in legs if not l.get("no_data")]
    pool = [l for l in seen if l["straight"] > 60] or seen     # a sprint may have no leg over 60 m
    if not pool:
        raise InputError("track_off_course", "the recording shows no leg of the course")
    vref = float(np.median([l["speed"] for l in pool]))
    rref = float(np.clip(np.median([l["ratio"] for l in pool]), 1.1, 1.35))
    for l in legs:
        exp_t = l["straight"] * rref / vref
        l["expected"] = exp_t
        if l.get("no_data"):
            l.update(est_loss=0.0, extra_dist=0.0, zone_excess=0.0, flags=["no GPS data on this leg"],
                     flag_codes=["no_data"])
            continue
        l["est_loss"] = max(0.0, l["time"] - exp_t)
        l["extra_dist"] = max(0.0, l["run"] - l["straight"] * rref)
        l["zone_excess"] = max(0.0, l["zone_time"] - min(zone, l["straight"]) * 1.15 / vref)
        f, codes = [], []  # codes: the same signals as short names, for callers that word them themselves
        if l["ratio"] > 1.6 and l["straight"] > 60:
            f.append(f"route {l['ratio']:.1f}x the straight line")
            codes.append("ratio")
        if l["zone_entries"] > 1:
            f.append(f"entered the {int(zone)} m circle {l['zone_entries']}x (overshoot / circling)")
            codes.append("entries")
        if l["zone_excess"] > 30:
            f.append(f"~{l['zone_excess']:.0f}s extra near the control")
            codes.append("zone")
        if l["stop_time"] > 15:
            f.append(f"stood still {l['stop_time']:.0f}s mid-leg")
            codes.append("stop")
        if l["speed"] < 0.7 * vref:
            f.append(f"slow ({l['speed'] * 3.6:.1f} km/h vs your {vref * 3.6:.1f})")
            codes.append("slow")
        l["flags"] = f
        l["flag_codes"] = codes
    return vref, rref
