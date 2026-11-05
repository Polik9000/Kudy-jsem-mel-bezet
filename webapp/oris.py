"""ORIS (Czech orienteering information system) public API: the runner's races, classes, Livelox ID, splits.

Plain HTTP + JSON, no key needed. Methods used: getUser, getUserEventEntries, getEvent, getSplits.
The parse_* functions are pure (JSON in, plain dicts out) so they are tested on saved responses.
"""
import datetime as dt
import json
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")  # ORIS start and finish times are local time


class OrisError(Exception):
    pass


def seconds(text):
    """'58:37', '80:18', '1:02:03' -> seconds; '', None, 'DISK', 'MP' -> None."""
    if not text:
        return None
    parts = str(text).strip().split(":")
    if not 2 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
        return None
    s = 0
    for p in parts:
        s = s * 60 + int(p)
    return s


def _num(v):
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else None
    except ValueError:
        return None


def _items(d):
    """ORIS returns {} / {'Key_1': {...}} for lists, and [] when empty."""
    return list(d.values()) if isinstance(d, dict) else list(d or [])


def parse_user(data):
    if not data:
        return None
    return dict(oris_user_id=int(data["ID"]), name=f"{data.get('FirstName', '')} {data.get('LastName', '')}".strip())


def parse_entries(data):
    return [dict(event_id=int(e["EventID"]), class_id=int(e["ClassID"]), class_name=e["ClassDesc"],
                 date=e["EventDate"]) for e in _items(data)]


def _links(d):
    """[{name, url}] of the links of an event (old map, online results ...)."""
    out = []
    for l in _items(d):
        st = l.get("SourceType") if isinstance(l.get("SourceType"), dict) else {}
        url = (l.get("Url") or "").strip()
        if url.startswith(("http://", "https://")):
            out.append(dict(name=(l.get("OtherDescCZ") or st.get("NameCZ") or "odkaz").strip(), url=url))
    return out


def _locations(d):
    """[{name, lat, lon}] of the named places of an event (centre, parking, start ...)."""
    out = []
    for l in _items(d):
        lat, lon = _num(l.get("GPSLat")), _num(l.get("GPSLon"))
        if lat is not None and lon is not None and (lat or lon):
            out.append(dict(name=(l.get("NameCZ") or l.get("Letter") or "").strip(), lat=lat, lon=lon))
    return out


def parse_event(data):
    d = data
    return dict(
        oris_id=int(d["ID"]), name=d["Name"], date=d["Date"], place=d.get("Place") or None,
        discipline=(d.get("Discipline") or {}).get("NameCZ") if isinstance(d.get("Discipline"), dict) else None,
        livelox_id=_valid_livelox_id(d.get("LiveloxID")), lat=_num(d.get("GPSLat")), lon=_num(d.get("GPSLon")),
        cancelled=str(d.get("Cancelled", "0")) == "1",
        links=_links(d.get("Links")), locations=_locations(d.get("Locations")),
        classes=[dict(oris_id=int(c["ID"]), name=c["Name"], distance_km=_num(c.get("Distance")),
                      climb_m=_num(c.get("Climbing")), controls=int(_num(c.get("Controls")) or 0) or None)
                 for c in _items(d.get("Classes"))])


def _codes(data):
    codes = [c.get("ControlCode") or "" for c in _items(data.get("Controls"))]
    return codes[:-1] if codes and codes[-1] == "" else codes  # the last "control" is the finish


def parse_class_splits(data):
    """The official times of everyone in a class: dict(control_codes, runners). A runner is dict(name, regno,
    club, place, start_local, time_s (None = not classified), status ("OK" or what ORIS wrote instead of a
    time), cum = seconds from the start to each control and, last, to the finish; None = no punch).
    None when the class has no split times."""
    if not data or not isinstance(data, dict) or not _items(data.get("Splits")):
        return None
    codes = _codes(data)
    runners = []
    for p in _items(data.get("Splits")):
        time_s = seconds(p.get("ResTime"))
        cum = [seconds(p.get(f"TotalTime{i}")) for i in range(1, len(codes) + 1)]
        # a disqualified runner still has a finish time on the clock (start and finish times of day)
        finish = time_s
        if finish is None and p.get("StartTime") and p.get("FinishTime"):
            a, b = seconds(p["StartTime"]), seconds(p["FinishTime"])
            finish = b - a if a is not None and b is not None and b > a else None
        runners.append(dict(
            name=(p.get("ResName") or "").strip(), regno=(p.get("RegNo") or "").upper() or None,
            club=(p.get("ResClub") or "").strip() or None, place=(p.get("ResPlace") or "").strip(". ") or None,
            start_local=p.get("StartTime") or None, time_s=time_s,
            status="OK" if time_s is not None else (str(p.get("ResTime") or "").strip() or "?"),
            cum=cum + [finish]))
    return dict(control_codes=codes, runners=runners)


def results_url(oris_id):
    return f"https://oris.ceskyorientak.cz/Vysledky?id={oris_id}" if oris_id else None


def oresults_url(links):
    """The OResults page of the event when ORIS links to it."""
    for l in links or []:
        if "oresults.eu/events/" in l.get("url", ""):
            return l["url"].split("?")[0]
    return None


def parse_splits(data, regno):
    """One runner's official times in a class, or None when the class has no splits for them.

    Returns dict(control_codes, start_local 'HH:MM:SS', time_s, place,
                 cumulative = seconds from the start to each control and last to the finish; None = no punch).
    """
    if not data or not isinstance(data, dict):
        return None
    row = next((p for p in _items(data.get("Splits")) if (p.get("RegNo") or "").upper() == regno.upper()), None)
    if row is None:
        return None
    codes = _codes(data)
    time_s = seconds(row.get("ResTime"))
    cum = [seconds(row.get(f"TotalTime{i}")) for i in range(1, len(codes) + 1)]
    return dict(control_codes=codes, start_local=row.get("StartTime") or None, time_s=time_s,
                place=(row.get("ResPlace") or "").strip(". ") or None, cumulative=cum + [time_s])


def start_utc(date, start_local):
    """Event date + local start time -> timezone-aware UTC datetime."""
    h, m, *s = (int(p) for p in start_local.split(":"))
    local = dt.datetime.combine(dt.date.fromisoformat(date), dt.time(h, m, s[0] if s else 0), tzinfo=TZ)
    return local.astimezone(dt.timezone.utc)


def _valid_livelox_id(value):
    """Return a usable Livelox event ID, treating ORIS's 0 / "0" as missing."""
    if value is None:
        return None
    value = str(value).strip()
    return value if value and value != "0" else None


def livelox_url(livelox_id):
    livelox_id = _valid_livelox_id(livelox_id)
    return f"https://www.livelox.com/Events/Show/{livelox_id}" if livelox_id else None


def event_url(oris_id):
    return f"https://oris.ceskyorientak.cz/Zavod?id={oris_id}" if oris_id else None


class Oris:
    def __init__(self, url="https://oris.ceskyorientak.cz/API/", timeout=30):
        self.url, self.timeout = url, timeout

    def call(self, method, **params):
        q = urllib.parse.urlencode(dict(format="json", method=method, **params))
        req = urllib.request.Request(f"{self.url}?{q}", headers={"User-Agent": "OB-tracker (club route analysis)"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except (OSError, ValueError) as e:
            raise OrisError(f"ORIS {method}: {e}") from e
        if body.get("Status") != "OK":
            raise OrisError(f"ORIS {method}: {body.get('Status')}")
        return body.get("Data")

    def user(self, regno):
        return parse_user(self.call("getUser", rgnum=regno))

    def entries(self, oris_user_id):
        return parse_entries(self.call("getUserEventEntries", userid=oris_user_id))

    def event(self, oris_id):
        return parse_event(self.call("getEvent", id=oris_id))

    def splits(self, class_id, regno):
        return parse_splits(self.class_splits_raw(class_id), regno)

    def class_splits_raw(self, class_id):
        """The getSplits answer of a class as ORIS sent it (parse with parse_splits / parse_class_splits)."""
        return self.call("getSplits", classid=class_id)


def client(conf):
    """The ORIS client of this installation (tests put a fake one answering from saved responses into conf)."""
    return getattr(conf, "oris_client", None) or Oris(conf.oris_url)
