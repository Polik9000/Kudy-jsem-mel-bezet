"""Write results as strict JSON: numpy values become plain numbers, NaN and infinity become null."""
import json
import math

import numpy as np


def plain(o):
    if isinstance(o, dict):
        return {str(k): plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [plain(v) for v in o]
    if isinstance(o, np.ndarray):
        return [plain(v) for v in o.tolist()]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    return o


def rounded(a, digits):
    return [None if not math.isfinite(v) else round(v, digits) for v in np.asarray(a, float).tolist()]


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plain(obj), f, ensure_ascii=False, allow_nan=False)
