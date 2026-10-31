"""Load GPS track points from a Garmin .fit file."""
import fitdecode
import numpy as np

from .errors import InputError

SEMI = 180.0 / 2**31


def load_track(path):
    """Return dict of numpy arrays: t (s from start), lat, lon, alt, dist, hr, plus start datetime.
    Raises InputError when the file cannot be read as a .fit (bad_fit) or has no record with a GPS position
    (no_gps: a watch without GPS, an indoor activity, a recording stopped before the first fix)."""
    rows = []
    try:
        with fitdecode.FitReader(path) as f:
            for fr in f:
                if not isinstance(fr, fitdecode.FitDataMessage) or fr.name != "record":
                    continue
                v = {fd.name: fd.value for fd in fr.fields}
                if v.get("position_lat") is None or v.get("position_long") is None:
                    continue
                rows.append((v["timestamp"], v["position_lat"] * SEMI, v["position_long"] * SEMI,
                             v.get("enhanced_altitude") or v.get("altitude") or np.nan,
                             v.get("distance") or np.nan, v.get("heart_rate") or np.nan))
    except fitdecode.FitError as e:
        raise InputError("bad_fit", f"the recording cannot be read as a .fit file ({type(e).__name__})") from e
    if len(rows) < 2:
        raise InputError("no_gps", "the recording has no GPS track (no record with a position)")
    t0 = rows[0][0]
    arr = lambda i: np.array([r[i] for r in rows], dtype=float)
    return {
        "start": t0,
        "t": np.array([(r[0] - t0).total_seconds() for r in rows]),
        "lat": arr(1), "lon": arr(2), "alt": arr(3), "dist": arr(4), "hr": arr(5),
    }
