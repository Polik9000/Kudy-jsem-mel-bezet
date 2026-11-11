"""Official times first: put the punches on the GPS track from the organiser's split times.

Without official times the punch at a control is guessed from the closest GPS approach
(analysis.find_punches). That goes wrong when the runner hangs around a control or the finish
(Pohora: finish found 43 s late). When the organiser's times are known they are the truth, and
the track is only cut at those moments.

official = {"start_utc": "2025-05-17T11:18:00+00:00",
            "cumulative": [84, 587, ..., 3022]}     seconds from the start to each control and,
                                                    last, to the finish; None = punch missing

apply() returns the track with one extra sample at every official moment (interpolated, so the
leg times are exactly the official ones even if the watch records every few seconds) and the punch
indices. If the times cannot be used (other number of controls than read from the map, recording
does not cover the race, positions far from the controls) it returns punch None and says why;
the caller then falls back to find_punches.

A recording that covers only a part of the race (the watch was started a few controls late or stopped
before the finish) is used for that part when it shows at least MIN_COVERED of the controls: the
moments outside it get the first or last recorded position, so every leg keeps its official time,
and info["no_data"] lists the course points the recording does not show.
"""
import datetime as dt

import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
except ImportError:  # e.g. Windows Application Control blocks scipy.optimize's compiled files: do without it
    def linear_sum_assignment(cost):
        """The cheapest one-to-one assignment (Hungarian algorithm, small matrices); same answer as scipy's:
        (rows, cols) with rows sorted."""
        c = np.asarray(cost, float)
        flip = c.shape[0] > c.shape[1]
        if flip:
            c = c.T
        n, m = c.shape
        u, v = np.zeros(n + 1), np.zeros(m + 1)
        way, match = np.zeros(m + 1, int), np.zeros(m + 1, int)      # match[j]: row (1-based) holding column j
        for i in range(1, n + 1):
            match[0], j0 = i, 0
            minv, used = np.full(m + 1, np.inf), np.zeros(m + 1, bool)
            while True:
                used[j0] = True
                i0, delta, j1 = match[j0], np.inf, 0
                for j in range(1, m + 1):
                    if not used[j]:
                        cur = c[i0 - 1, j - 1] - u[i0] - v[j]
                        if cur < minv[j]:
                            minv[j], way[j] = cur, j0
                        if minv[j] < delta:
                            delta, j1 = minv[j], j
                for j in range(m + 1):
                    if used[j]:
                        u[match[j]] += delta
                        v[j] -= delta
                    else:
                        minv[j] -= delta
                j0 = j1
                if match[j0] == 0:
                    break
            while j0:
                j1 = way[j0]
                match[j0], j0 = match[j1], j1
        pairs = sorted((match[j] - 1, j - 1) for j in range(1, m + 1) if match[j])
        rows = np.array([r for r, _ in pairs], int)
        cols = np.array([k for _, k in pairs], int)
        if flip:
            rows, cols = cols, rows
            o = np.argsort(rows)
            rows, cols = rows[o], cols[o]
        return rows, cols

PAD_S = 30.0       # watch started this much late / stopped this much early is still accepted
MAX_SHIFT_S = 60   # largest clock difference between the timing system and the watch that is tried
MAX_MISS_M = 60.0  # median distance from the controls at the official moments above which the times are not trusted
MIN_COVERED = 0.5  # share of the controls a recording must show for the official times to be used on the part it has
MAX_OPEN = 6       # controls outside the recording whose order is left to the purple lines (course.fill_order)


def _interp_xy(t, x, y, q):
    return np.interp(q, t, x), np.interp(q, t, y)


def clock_shift(t, x, y, points, moments):
    """Seconds to add to the official moments so the track is closest to the controls at them.

    moments[k] belongs to points[k] (controls only, no start/finish). Returns (shift, median miss in m).
    The timing clock and the watch can differ by a few seconds; a shift is only used when it is
    clearly better than none.
    """
    pts = np.asarray(points, float)
    q = np.asarray(moments, float)

    def miss(s):
        qx, qy = _interp_xy(t, x, y, q + s)
        return float(np.median(np.hypot(qx - pts[:, 0], qy - pts[:, 1])))

    zero = miss(0.0)
    if len(q) < 4:
        return 0.0, zero
    best = min(range(-MAX_SHIFT_S, MAX_SHIFT_S + 1), key=lambda s: (miss(s), abs(s)))
    return (float(best), miss(best)) if miss(best) < zero - 5.0 else (0.0, zero)


def punch_places(track, official):
    """Where the watch was at each official control punch: [(lat, lon) or None] (not the start and the finish;
    None where the punch is missing or the recording does not show that moment). No clock difference is
    corrected: the caller looks around these places (course.find_missing)."""
    cum = official.get("cumulative") or []
    start = dt.datetime.fromisoformat(official["start_utc"])
    rec = track["start"] if track["start"].tzinfo else track["start"].replace(tzinfo=dt.timezone.utc)
    t0 = (start - rec).total_seconds()
    t = track["t"]
    out = []
    for c in cum[:-1]:
        if c is None or not (t[0] <= t0 + c <= t[-1]):
            out.append(None)
        else:
            out.append((float(np.interp(t0 + c, t, track["lat"])), float(np.interp(t0 + c, t, track["lon"]))))
    return out


def order_controls(track, geomap, circles, official):
    """The order of the course from the organiser's split times: which control circle was punched when.

    circles: [(x, y)] in metres, the control circles read from the map, in any order. At every official punch
    time the watch says where the runner was, and the circle there is that control. Every punch gets a circle
    of its own so that the distances add up to the least; the clock difference between the timing system and
    the watch is the one that brings the track closest to the circles (as clock_shift does once the order is
    known). One missing punch gets the circle that is left.
    Returns (order as indices into circles, info) or (None, info with the reason): another number of circles
    than controls in the results, no finish time, more than one punch missing, a recording that does not cover
    the race, or a track that is far from the circles at the official moments.
    A recording that shows at least MIN_COVERED of the controls gives the order of those; the others (up to
    MAX_OPEN) are None in the order, for the caller to place by the purple lines (course.fill_order).
    """
    cum = official.get("cumulative") or []
    info = dict(used=False)
    n = len(cum) - 1
    if n != len(circles) or n < 1:
        info["reason"] = f"official results have {n} controls, {len(circles)} circles were read from the map"
        return None, info
    if cum[-1] is None:
        info["reason"] = "no official finish time"
        return None, info
    known = [k for k in range(n) if cum[k] is not None]
    if n - len(known) > 1 or not known:
        info["reason"] = f"{n - len(known)} punches are missing in the official results"
        return None, info
    start = dt.datetime.fromisoformat(official["start_utc"])
    rec = track["start"] if track["start"].tzinfo else track["start"].replace(tzinfo=dt.timezone.utc)
    t0 = (start - rec).total_seconds()
    t = track["t"]
    x, y = geomap.to_xy(track["lat"], track["lon"])
    x, y = np.asarray(x), np.asarray(y)
    pts = np.asarray(circles, float)
    q = t0 + np.array([cum[k] for k in known], float)

    def dist(s):
        qx, qy = _interp_xy(t, x, y, q + s)
        return np.hypot(qx[:, None] - pts[None, :, 0], qy[:, None] - pts[None, :, 1])

    def miss(s):
        return float(np.median(dist(s).min(axis=1)))

    shift = 0.0
    if len(known) >= 4:
        best = min(range(-MAX_SHIFT_S, MAX_SHIFT_S + 1), key=lambda s: (miss(s), abs(s)))
        if miss(best) < miss(0.0) - 5.0:
            shift = float(best)
    whole = not (t0 + shift < t[0] - PAD_S or t0 + shift + cum[-1] > t[-1] + PAD_S)
    at = known
    if not whole:
        # only a part of the race was recorded: the punches inside the recording say which circle is which
        seen = (q >= t[0] - PAD_S) & (q <= t[-1] + PAD_S)
        if seen.sum() < max(2.0, MIN_COVERED * n) or n - seen.sum() > MAX_OPEN:
            info["reason"] = "the recording does not cover the official race time"
            return None, info
        q, at, shift = q[seen], [k for k, s in zip(known, seen) if s], 0.0
        if len(at) >= 4:
            best = min(range(-MAX_SHIFT_S, MAX_SHIFT_S + 1), key=lambda s: (miss(s), abs(s)))
            if miss(best) < miss(0.0) - 5.0:
                shift = float(best)
    d = dist(shift)
    rows, cols = linear_sum_assignment(d)
    far = float(np.median(d[rows, cols]))
    info.update(clock_shift_s=shift, median_miss_m=round(far, 1))
    if far > MAX_MISS_M:
        info["reason"] = f"at the official times the track is {far:.0f} m from the control circles (median)"
        return None, info
    order = [None] * n
    for r, c in zip(rows, cols):
        order[at[r]] = int(c)
    if whole and None in order:
        order[order.index(None)] = (set(range(n)) - set(order)).pop()
    info["used"] = True
    return order, info


def insert_samples(track, moments):
    """Track with a sample at each moment (s from track start); returns (track, index of each moment).
    Moments up to PAD_S outside the recording get the first / last recorded position."""
    t = track["t"]
    new = np.array(sorted(set(float(m) for m in moments) - set(t.tolist())))
    tt = np.sort(np.r_[t, new])
    out = dict(track)
    out["t"] = tt
    for k in ("lat", "lon", "alt", "dist", "hr"):
        out[k] = np.interp(tt, t, track[k])  # outside the recording np.interp repeats the end value
    idx = [int(np.searchsorted(tt, float(m))) for m in moments]
    return out, idx


def apply(track, geomap, points, official):
    """points: [(x, y)] in metres for start, controls..., finish (as analysis.find_punches takes them).
    Returns (track, punch or None, info)."""
    cum = official.get("cumulative") or []
    info = dict(used=False)
    if len(cum) != len(points) - 1:
        info["reason"] = (f"official results have {len(cum) - 1} controls, the course read from the map has "
                          f"{len(points) - 2}")
        return track, None, info
    if cum[-1] is None:
        info["reason"] = "no official finish time"
        return track, None, info
    start = dt.datetime.fromisoformat(official["start_utc"])
    rec = track["start"] if track["start"].tzinfo else track["start"].replace(tzinfo=dt.timezone.utc)
    t0 = (start - rec).total_seconds()
    t = track["t"]
    x, y = geomap.to_xy(track["lat"], track["lon"])
    x, y = np.asarray(x), np.asarray(y)

    known = [k for k in range(1, len(points) - 1) if cum[k - 1] is not None]
    shift, miss = (clock_shift(t, x, y, [points[k] for k in known], [t0 + cum[k - 1] for k in known])
                   if known else (0.0, 0.0))
    first, last = t0 + shift, t0 + shift + cum[-1]
    outside = []
    if first < t[0] - PAD_S or last > t[-1] + PAD_S:
        # a part of the race may still be on the recording: the controls punched inside it
        seen = [k for k in known if t[0] - PAD_S <= t0 + cum[k - 1] <= t[-1] + PAD_S]
        if len(seen) < max(2.0, MIN_COVERED * (len(points) - 2)):
            info.update(clock_shift_s=shift, median_miss_m=round(miss, 1))
            info["reason"] = (f"the recording does not cover the official race time (start {first - t[0]:+.0f} s "
                              f"from the start of the recording, finish {last - t[-1]:+.0f} s from its end)")
            return track, None, info
        shift, miss = clock_shift(t, x, y, [points[k] for k in seen], [t0 + cum[k - 1] for k in seen])
        first, last = t0 + shift, t0 + shift + cum[-1]
        outside = [k for k, m in enumerate([first] + [None if c is None else first + c for c in cum])
                   if m is not None and not t[0] - PAD_S <= m <= t[-1] + PAD_S]
        known = seen
    info.update(clock_shift_s=shift, median_miss_m=round(miss, 1))
    if known and miss > MAX_MISS_M:
        info["reason"] = f"at the official times the track is {miss:.0f} m from the controls (median)"
        return track, None, info

    moments = [first] + [None if c is None else first + c for c in cum]
    track2, idx = insert_samples(track, [m for m in moments if m is not None])
    it = iter(idx)
    punch = [None if m is None else next(it) for m in moments]
    # missing punches: closest GPS approach between the neighbouring official punches
    x2, y2 = geomap.to_xy(track2["lat"], track2["lon"])
    for k, p in enumerate(punch):
        if p is None:
            lo = punch[k - 1]
            hi = next(q for q in punch[k + 1:] if q is not None)
            d = np.hypot(np.asarray(x2)[lo:hi + 1] - points[k][0], np.asarray(y2)[lo:hi + 1] - points[k][1])
            punch[k] = lo + int(np.argmin(d))
    info.update(used=True, missing=[k for k, m in enumerate(moments) if m is None])
    if outside:
        info.update(no_data=outside, recorded=dict(start_s=round(t[0] - first), end_s=round(t[-1] - first),
                                                   race_s=round(last - first)))
    return track2, punch, info


def no_data_legs(info, n_legs):
    """The legs (numbered from 1) a partly recorded race has no track for: those that begin or end at a
    course point outside the recording (info: what apply() returned)."""
    out = set((info or {}).get("no_data") or [])
    return {k for k in range(1, n_legs + 1) if k in out or k - 1 in out}
