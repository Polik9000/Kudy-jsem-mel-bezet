"""Cutting off the start and the end of a recording where the GPS was not there yet (or any more).

When the watch is started before it has a good fix, its first positions wander tens of metres around and then
jump to where the runner really is: on the map a straight line from nowhere to the start. The same can happen
at the end (indoors after the finish). find() looks for such a jump in the first and the last HEAD_S seconds:
over WINDOW_S at least JUMP_M at more than JUMP_KMH, faster than anybody runs. The part before the jump at the
start (after it at the end) is cut off. A track without such a jump is left exactly as it is.

A gap in the middle of the race is never cut (the legs around it would lose their time): the leg says "GPS tu
asi zlobí" and the runner can draw where they really ran ("Opravit moji stopu").

Times here are seconds from the first position of the recording as the watch wrote it (the untrimmed track):
they do not move when the cut changes, so a cut set by hand stays where it was set.
"""
import numpy as np

HEAD_S = 180.0      # only this far from the start (the end) of the recording a jump is cut off
WINDOW_S = 5.0      # the speed of a jump is measured over at least this long (one second of GPS noise is not one)
JUMP_M = 50.0       # ... over at least this distance
JUMP_KMH = 45.0     # ... and faster than this (a sprint finish is 25 km/h; GPS noise adds 10 or so)
MIN_LEFT_S = 60.0   # never cut so much that less than this is left


def _xy(lat, lon):
    kx = 111320.0 * np.cos(np.radians(float(np.nanmedian(lat))))
    return (np.asarray(lon) - lon[0]) * kx, (np.asarray(lat) - lat[0]) * 110540.0


def jumps(t, lat, lon):
    """[(i, j)] index pairs of the stretches where the track moves faster than JUMP_KMH over at least JUMP_M:
    from i the first point at least WINDOW_S later is j (or the next point after a longer gap)."""
    t = np.asarray(t, float)
    x, y = _xy(lat, lon)
    j = np.searchsorted(t, t + WINDOW_S)
    j = np.maximum(np.minimum(j, len(t) - 1), np.minimum(np.arange(len(t)) + 1, len(t) - 1))
    i = np.arange(len(t))
    ok = j > i
    d = np.hypot(x[j] - x[i], y[j] - y[i])
    v = d / np.maximum(t[j] - t[i], 1e-6) * 3.6
    bad = ok & (d >= JUMP_M) & (v > JUMP_KMH)
    return [(int(a), int(b)) for a, b in zip(i[bad], j[bad])]


def _biggest_step(x, y, i, j):
    """Index k in [i, j) of the longest single step k -> k + 1."""
    s = np.hypot(np.diff(x[i:j + 1]), np.diff(y[i:j + 1]))
    return i + int(np.argmax(s))


def find(t, lat, lon):
    """Where to cut the recording automatically: dict(start_s, end_s, start_why, end_why) in seconds of t
    (t[0] and t[-1] when nothing is cut; *_why: None, or dict(jump_m, kmh, at_s) of the jump cut off)."""
    t = np.asarray(t, float)
    out = dict(start_s=float(t[0]), end_s=float(t[-1]), start_why=None, end_why=None)
    if len(t) < 3:
        return out
    x, y = _xy(lat, lon)
    found = jumps(t, lat, lon)

    def why(k):
        d = float(np.hypot(x[k + 1] - x[k], y[k + 1] - y[k]))
        return dict(jump_m=round(d), kmh=round(d / max(t[k + 1] - t[k], 1e-6) * 3.6), at_s=round(float(t[k]) - t[0]))
    head = [(i, j) for i, j in found if t[j] - t[0] <= HEAD_S]
    if head:
        i, j = head[-1]                       # the last jump near the start: everything before it was not there yet
        k = _biggest_step(x, y, i, j)
        if t[-1] - t[k + 1] >= MIN_LEFT_S:
            out.update(start_s=float(t[k + 1]), start_why=why(k))
    tail = [(i, j) for i, j in found if t[-1] - t[i] <= HEAD_S and t[i] >= out["start_s"]]
    if tail:
        i, j = tail[0]                        # the first jump near the end: everything after it is gone
        k = _biggest_step(x, y, i, j)
        if t[k] - out["start_s"] >= MIN_LEFT_S:
            out.update(end_s=float(t[k]), end_why=why(k))
    return out


def gaps(t, lat, lon, min_s=30.0, min_m=100.0):
    """Gaps in the recording of at least min_s with the track at least min_m further (a straight line on the
    map): [dict(at_s, dur_s, dist_m)], at_s in seconds of t. Only to tell the runner: nothing is cut there."""
    t = np.asarray(t, float)
    if len(t) < 2:
        return []
    x, y = _xy(lat, lon)
    dt = np.diff(t)
    d = np.hypot(np.diff(x), np.diff(y))
    return [dict(at_s=round(float(t[k])), dur_s=round(float(dt[k])), dist_m=round(float(d[k])))
            for k in np.nonzero((dt >= min_s) & (d >= min_m))[0]]


def parse(value):
    """The cut as the scripts take it (--gps-trim): None or "auto" (cut what find() finds), "off" (keep it all)
    or "FROM:TO" in seconds from the first position (either may be empty: keep that end as it is).
    Returns "auto", "off" or (from_s or None, to_s or None). Raises ValueError on anything else."""
    if value in (None, "", "auto"):
        return "auto"
    if value == "off":
        return "off"
    a, sep, b = str(value).partition(":")
    if not sep:
        raise ValueError(f"--gps-trim: auto, off or FROM:TO (seconds), not {value!r}")
    lo = float(a) if a.strip() else None
    hi = float(b) if b.strip() else None
    if lo is not None and hi is not None and hi - lo < MIN_LEFT_S:
        raise ValueError(f"--gps-trim: less than {MIN_LEFT_S:.0f} s of the track would be left")
    return lo, hi


def apply(track, setting="auto"):
    """The track (fitload.load_track) cut as setting says (parse). The times start again at 0 at the first point
    kept, and track["start"] is its moment. track["trim"] says what was done: mode, start_s/end_s kept (seconds of
    the untrimmed track), its whole length, what the automatic cut would be (auto), the gaps in the middle and
    the points cut off ([[lat, lon, s]], for the map)."""
    import datetime as dt
    mode = parse(setting) if not isinstance(setting, tuple) else setting
    t = np.asarray(track["t"], float)
    auto = find(t, track["lat"], track["lon"])
    if mode == "auto":
        lo, hi = auto["start_s"], auto["end_s"]
    elif mode == "off":
        lo, hi = float(t[0]), float(t[-1])
    else:
        lo = float(t[0]) if mode[0] is None else max(float(t[0]), mode[0])
        hi = float(t[-1]) if mode[1] is None else min(float(t[-1]), mode[1])
    keep = (t >= lo - 1e-6) & (t <= hi + 1e-6)
    if keep.sum() < 2:
        keep = np.ones(len(t), bool)              # a cut that leaves nothing: keep it all
    a, b = int(np.argmax(keep)), len(t) - 1 - int(np.argmax(keep[::-1]))

    def pts(sl):
        return [[round(float(track["lat"][i]), 6), round(float(track["lon"][i]), 6), round(float(t[i]), 1)]
                for i in range(len(t))[sl]]
    info = dict(mode=mode if isinstance(mode, str) else "manual", start_s=float(t[a]), end_s=float(t[b]),
                length_s=float(t[-1]), auto=auto, gaps=gaps(t[a:b + 1], track["lat"][a:b + 1], track["lon"][a:b + 1]),
                head=pts(slice(0, a)), tail=pts(slice(b + 1, None)))
    out = {k: (v[a:b + 1] if isinstance(v, np.ndarray) and len(v) == len(t) else v) for k, v in track.items()}
    out["t"] = t[a:b + 1] - t[a]
    out["start"] = track["start"] + dt.timedelta(seconds=float(t[a]))
    out["trim"] = info
    return out
