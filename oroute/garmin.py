"""Garmin activities: read what a .fit file is, walk a Garmin export, match activities to races.

The same logic as the scripts in garmin-matching/ (scan_fit.py, extract_fit.py, match.py), as
functions that can be imported. The scripts are left as they are.
"""
import datetime as dt
import io
import math
import zipfile
from zoneinfo import ZoneInfo

import fitdecode

SEMI = 180.0 / 2**31
TZ = ZoneInfo("Europe/Prague")
RUN = {"running"}
MAX_FIT = 40 * 1024 * 1024          # bytes; larger members of an uploaded zip are skipped
MAX_INNER_ZIP = 3 * 1024 ** 3
NEAR_KM = 10.0                      # an activity that starts farther from the race centre is not the race


def km_between(lat1, lon1, lat2, lon2):
    """Distance in km (flat-earth approximation, fine up to tens of km)."""
    k = 111.195
    return math.hypot((lat2 - lat1) * k, (lon2 - lon1) * k * math.cos(math.radians((lat1 + lat2) / 2)))


def km_from(a, near):
    """How far the activity starts from the nearest of the places of the race [(lat, lon)]; None = unknown."""
    if not near or a.get("lat") is None or a.get("lon") is None:
        return None
    return min(km_between(a["lat"], a["lon"], la, lo) for la, lo in near)


def scan_fit(data):
    """What a .fit file is (bytes or path): type, start (UTC datetime), sport, timer and elapsed time,
    distance, first GPS position. Same fields as garmin-matching/scan_fit.py. Never raises: a broken
    file gives {"error": ...}."""
    info = {}
    try:
        with fitdecode.FitReader(io.BytesIO(data) if isinstance(data, bytes) else data,
                                 check_crc=fitdecode.CrcCheck.DISABLED) as f:
            for fr in f:
                if not isinstance(fr, fitdecode.FitDataMessage):
                    continue
                if fr.name == "file_id":
                    info["type"] = str(fr.get_value("type", fallback=None))
                    if info["type"] != "activity":
                        return info
                elif fr.name == "session":
                    v = {fd.name: fd.value for fd in fr.fields}
                    info.update(start=v.get("start_time") or info.get("start"),
                                sport=str(v.get("sport")), sub_sport=str(v.get("sub_sport")),
                                elapsed=v.get("total_elapsed_time"), timer=v.get("total_timer_time"),
                                dist=v.get("total_distance"))
                elif fr.name == "record" and "first_gps" not in info \
                        and fr.get_value("position_lat", fallback=None) is not None:
                    info["first_gps"] = [fr.get_value("position_lat") * SEMI, fr.get_value("position_long") * SEMI]
                    if info.get("start") is None:
                        info["start"] = fr.get_value("timestamp", fallback=None)
    except Exception as e:
        info["error"] = repr(e)[:120]
    return info


def iter_fit(src):
    """(name, bytes) of every .fit in a zip: a Garmin account export (the .fit files sit in zips inside
    the zip, under DI_CONNECT/DI-Connect-Uploaded-Files/) or a plain zip of .fit files."""
    def walk(zf, depth):
        for zi in zf.infolist():
            nm, low = zi.filename, zi.filename.lower()
            # sizes as the zip declares them: an activity is well under MAX_FIT, anything bigger is not one
            if low.endswith(".fit") and zi.file_size <= MAX_FIT:
                yield nm.rsplit("/", 1)[-1], zf.read(nm)
            elif low.endswith(".zip") and depth < 2 and zi.file_size <= MAX_INNER_ZIP:
                try:
                    inner = zipfile.ZipFile(io.BytesIO(zf.read(nm)))
                except zipfile.BadZipFile:
                    continue
                yield from walk(inner, depth + 1)
    with zipfile.ZipFile(src) as z:
        yield from walk(z, 0)


def single_fit(src):
    """(name, bytes) when the zip holds exactly one .fit (Garmin Connect, gear menu of one activity: "Exportovat
    soubor"), else None (a whole account export, even with one run in it, several runs, no run, or no zip at all).
    src: path or file."""
    try:
        with zipfile.ZipFile(src) as z:
            if any(n.startswith("DI_CONNECT") for n in z.namelist()):
                return None
        if hasattr(src, "seek"):
            src.seek(0)
        found = []
        for item in iter_fit(src):
            found.append(item)
            if len(found) > 1:
                return None
    except zipfile.BadZipFile:
        return None
    return found[0] if found else None


def local(start):
    """Activity start (UTC) as local time of the race region."""
    return (start if start.tzinfo else start.replace(tzinfo=dt.timezone.utc)).astimezone(TZ)


def match_race(date, time_s, acts, start_local=None, near=None):
    """Pick the activity that is the race. The rule of garmin-matching/match.py:

    activities on the race's local date (Europe/Prague); prefer running, then the one whose
    timer time is closest to the official race time. Confidence:
      high   = one plausible run, its duration within -2/+25 min of the race time
      medium = plausible, but several candidates or duration off
      low    = only a non-running or very different activity that day
      none   = no activity that day, or none with GPS (a recording without a track cannot be analysed: it is
               never picked, and when it is all there is that day the race stays without an activity)
    Added for the web app: when the official start time is known (start_local, "HH:MM:SS") and
    several runs are plausible, the one started within 10 min of it wins.
    near: [(lat, lon)] of the race (ORIS centre and named places). Activities that start more than
    NEAR_KM from all of them are left out when another one that day starts near the race (a warm-up
    jog at home, a second race the same day); a race without an official time is given to the
    activity nearest to the race; and a match that is far from the race is never better than "low".
    Activities need lat, lon for this; without near nothing changes.

    date: datetime.date; time_s: official time or None; acts: dicts with start (UTC datetime),
    sport, sub_sport, timer, has_gps. Returns (activity or None, confidence, note).
    """
    cands = [a for a in acts if a.get("start") is not None and local(a["start"]).date() == date]
    if not cands:
        return None, "none", "no activity that day"
    cands = [a for a in cands if a.get("has_gps", True)]
    if not cands:
        return None, "none", "only an activity without GPS that day"
    by_place = 0
    if near:
        close = [a for a in cands if km_from(a, near) is not None and km_from(a, near) <= NEAR_KM]
        if close and len(close) < len(cands):
            by_place, cands = len(cands), close
    rt = time_s or 0
    off = lambda a: abs((a["timer"] or 0) - rt)
    runs = [a for a in cands if a["sport"] in RUN and a["sub_sport"] != "treadmill"]
    pool = runs or cands
    best = min(pool, key=lambda a: off(a) if rt else (km_from(a, near) or 0.0))
    note = ""
    diff = ((best["timer"] or 0) - rt) / 60 if rt else None
    plaus = [a for a in runs if rt and -2 <= ((a["timer"] or 0) - rt) / 60 <= 25]
    if not runs:
        conf, note = "low", f"only {best['sport']} that day"
    elif diff is not None and -2 <= diff <= 25:
        others = [a for a in plaus if a is not best]
        clear = all(off(a) - abs(diff * 60) > 300 for a in others)
        conf = "high" if clear else "medium"
        if others:
            note = f"{len(plaus)} runs that day, picked the one closest to the race time"
            if start_local:
                h, m, *s = (int(p) for p in start_local.split(":"))
                want = h * 3600 + m * 60 + (s[0] if s else 0)
                gap = lambda a: abs(local(a["start"]).hour * 3600 + local(a["start"]).minute * 60
                                    + local(a["start"]).second - want)
                near = [a for a in plaus if gap(a) <= 600]
                if len(near) == 1:
                    best, conf = near[0], "high"
                    note = f"{len(plaus)} runs that day, picked the one started at the official start time"
    else:
        conf = "medium" if diff is None else "low"
        note = f"activity {diff:+.0f} min vs race time" if diff is not None else "no official time, matched by date only"
    if len(cands) > 1 and not note:
        note = f"{len(cands)} activities that day, picked the one matching the race time"
    far = km_from(best, near)
    if far is not None and far > NEAR_KM:
        conf, note = "low", f"activity starts {far:.0f} km from the race"
    elif by_place and not note:
        note = f"{by_place} activities that day, picked the one that starts at the race"
    return best, conf, note
