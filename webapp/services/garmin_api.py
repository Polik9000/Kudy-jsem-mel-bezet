"""Runs straight from the runner's Garmin Connect account, through Garmin's Personal API
(https://developer.garmin.com/gc-developer-program/personal/personal-api).

Only for the app on one's own computer. The runner creates a Personal API key in Garmin Connect
(https://connect.garmin.com/app/settings/personalApiToken) and pastes it into the app. The key and the
24-hour access token made from it are stored only in the app's data folder (instance/garmin/, readable only
by the runner) and are sent only to Garmin. No password, no server of ours.

The Personal API: POST the key to TOKEN_PATH ("Authorization: ApiKey <key>") gives a JWT valid 24 hours (no
refresh token: the key is posted again); then GET the Connect paths with "Authorization: Bearer <jwt>".
The activity list is /activitylist-service/activities/search/activities, the original file of an activity
(a zip with the .fit) /download-service/files/activity/<id>. Same paths as Garmin's own client
github.com/garmin/connect-personal-api-python (Apache-2.0), written here with urllib to need nothing new."""
import base64
import datetime as dt
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from oroute import garmin

from ..i18n import _

BASE_URL = os.environ.get("OB_GARMIN_API_URL", "https://personal.connectapi.garmin.com").rstrip("/")
TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"
LIST_PATH = "/activitylist-service/activities/search/activities"
DOWNLOAD_PATH = "/download-service/files/activity/{}"
KEY_PAGE = "https://connect.garmin.com/app/settings/personalApiToken"
TIMEOUT = 60
PAGE = 100            # activities per page of the list
MAX_LIST = 3000       # never more than this many activities in one list (about ten years of daily runs)
PAUSE_S = 0.2         # between two downloads: the Personal API publishes no rate limit, so go easy on it
REFRESH_S = 3600      # a cached token is taken while it has more than an hour left (as Garmin's client does)
# activity types (Garmin typeKey) offered first: what an orienteering race or a run is recorded as
RUN_TYPES = ("run", "orienteering", "hiking", "walking", "trail", "track")


class GarminApiError(Exception):
    """A Czech sentence for the page or the job list: what went wrong with Garmin."""


class KeyRejected(GarminApiError):
    """Garmin did not take the key (wrong, expired or deleted): the runner has to make a new one."""


# --- the key and the token, only in the data folder ---------------------------------------------------------

def _dir(conf):
    return conf.path("garmin")


def _key_file(conf, user_id):
    return os.path.join(_dir(conf), f"user_{user_id}.key")


def _token_file(conf, user_id):
    return os.path.join(_dir(conf), f"user_{user_id}.token.json")


def _write_private(path, text):
    """Write a file readable only by its owner (on Windows the data folder is in the runner's profile)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def clean_key(text):
    """The key as pasted: spaces and line breaks around it (and inside, from a wrapped copy) are not part of it."""
    return "".join((text or "").split())


def save_key(conf, user_id, key):
    key = clean_key(key)
    if len(key) < 16 or len(key) > 4096:
        raise GarminApiError(_("Tohle nevypadá jako klíč Personal API z Garmin Connect. Zkopíruj ho celý."))
    _write_private(_key_file(conf, user_id), key)
    try:
        os.remove(_token_file(conf, user_id))   # a token of an older key must not be used with the new one
    except OSError:
        pass


def has_key(conf, user_id):
    return os.path.exists(_key_file(conf, user_id))


def forget(conf, user_id):
    """Disconnect: delete the key and the token from the data folder (the key stays valid at Garmin until it
    expires or the runner deletes it there)."""
    for f in (_key_file(conf, user_id), _token_file(conf, user_id)):
        try:
            os.remove(f)
        except OSError:
            pass


def _key(conf, user_id):
    try:
        with open(_key_file(conf, user_id), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        raise KeyRejected(_("Účet Garmin není připojený: vlož klíč Personal API.")) from None


def _jwt_exp(token):
    """The `exp` claim of the JWT (seconds since the epoch), without checking the signature."""
    try:
        part = token.split(".")[1]
        return float(json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))["exp"])
    except (IndexError, KeyError, TypeError, ValueError) as e:
        raise GarminApiError(_("Garmin vrátil neznámou odpověď místo přístupového tokenu.")) from e


# --- HTTP ---------------------------------------------------------------------------------------------------

def _http(conf, method, url, headers):
    """(status, body bytes). Tests put a function(method, url, headers) into conf.garmin_fetch."""
    fake = getattr(conf, "garmin_fetch", None)
    if fake is not None:
        return fake(method, url, headers)
    req = urllib.request.Request(url, method=method, headers=dict(headers, **{"User-Agent": "Kudy-jsem-mel-bezet"}),
                                 data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except OSError as e:
        raise GarminApiError(_("Garmin Connect není dostupný (internet?): %(e)s", e=e)) from e


class Client:
    """Calls of one runner, with their key and the cached token."""

    def __init__(self, conf, user_id):
        self.conf, self.user_id = conf, user_id

    def _token(self, fresh=False):
        f = _token_file(self.conf, self.user_id)
        if not fresh:
            try:
                with open(f, encoding="utf-8") as fh:
                    c = json.load(fh)
                if c["exp"] - time.time() > REFRESH_S:
                    return c["token"]
            except (OSError, ValueError, KeyError, TypeError):
                pass
        status, body = _http(self.conf, "POST", BASE_URL + TOKEN_PATH,
                             {"Accept": "*/*", "Authorization": f"ApiKey {_key(self.conf, self.user_id)}"})
        if status in (400, 401, 403):
            raise KeyRejected(_("Garmin klíč nepřijal (je špatně zkopírovaný, vypršel, nebo byl smazaný)."
                              " Vytvoř v Garmin Connect nový a vlož ho znovu."))
        if status != 200:
            raise GarminApiError(_("Garmin Connect odpověděl chybou %(status)s při přihlášení klíčem.", status=status))
        token = body.decode("utf-8", "replace").strip()
        _write_private(f, json.dumps({"token": token, "exp": _jwt_exp(token)}))
        return token

    def _get(self, path, params=None, accept="application/json"):
        url = BASE_URL + path + ("?" + urllib.parse.urlencode(params) if params else "")
        for attempt in (0, 1):
            status, body = _http(self.conf, "GET", url,
                                 {"Accept": accept, "Authorization": f"Bearer {self._token(fresh=attempt == 1)}"})
            if status == 401 and attempt == 0:
                continue          # the token stopped working before it expired: one new one, then give up
            break
        if status == 429:
            raise GarminApiError(_("Garmin teď nechce odpovídat (příliš mnoho dotazů). Zkus to za chvíli."))
        if status in (401, 403):
            raise KeyRejected(_("Garmin přístup odmítl. Vytvoř v Garmin Connect nový klíč a vlož ho znovu."))
        if status != 200:
            raise GarminApiError(_("Garmin Connect odpověděl chybou %(status)s.", status=status))
        return body

    def activities(self, since=None, until=None, limit=MAX_LIST):
        """The account's activities (newest first) as Garmin lists them (dicts), from `since` (a date)."""
        out = []
        while len(out) < limit:
            params = {"start": len(out), "limit": min(PAGE, limit - len(out))}
            if since:
                params["startDate"] = since.isoformat()
            if until:
                params["endDate"] = until.isoformat()
            try:
                page = json.loads(self._get(LIST_PATH, params) or b"[]")
            except ValueError as e:
                raise GarminApiError(_("Garmin vrátil seznam aktivit, kterému appka nerozumí.")) from e
            if not isinstance(page, list) or not page:
                break
            out += page
            if len(page) < params["limit"]:
                break
        return out

    def fit(self, activity_id):
        """(file name, .fit bytes) of one activity: Garmin gives the original file in a zip."""
        aid = str(activity_id)
        if not aid.isdecimal():
            raise GarminApiError(_("Neplatné číslo aktivity."))
        body = self._get(DOWNLOAD_PATH.format(aid),
                         accept="application/zip, application/x-zip-compressed, application/octet-stream")
        if body[8:12] == b".FIT":
            return f"{aid}_ACTIVITY.fit", body
        one = garmin.single_fit(io.BytesIO(body))
        if one is None:
            raise GarminApiError(_("Aktivita %(aid)s: Garmin neposlal soubor .fit.", aid=aid))
        name = one[0] if one[0].lower().endswith(".fit") else f"{aid}_ACTIVITY.fit"
        return name, one[1]


# --- the list on the page -----------------------------------------------------------------------------------

def _start_utc(a):
    """Start of a listed activity (aware UTC datetime) from startTimeGMT, "2026-10-04 08:12:33"."""
    s = a.get("startTimeGMT") or a.get("startTimeGmt")
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(str(s).replace("T", " ")[:19]).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def is_run(type_key):
    return any(k in (type_key or "") for k in RUN_TYPES)


def offer(con, conf, user_id, days):
    """The account's activities of the last `days` days for the page: id, name, type, start, length, time,
    run (offered first), in_app (an activity starting within two minutes is already in the app)."""
    since = dt.date.today() - dt.timedelta(days=days)
    have = []
    for r in con.execute("SELECT start_utc FROM activities WHERE user_id = ? AND start_utc IS NOT NULL", (user_id,)):
        try:
            have.append(dt.datetime.fromisoformat(r["start_utc"]))
        except ValueError:
            pass
    rows = []
    for a in Client(conf, user_id).activities(since=since):
        aid = a.get("activityId")
        start = _start_utc(a)
        if aid is None or start is None:
            continue
        kind = (a.get("activityType") or {}).get("typeKey") or ""
        rows.append(dict(id=int(aid), name=(a.get("activityName") or "")[:120], type=kind, start=start.isoformat(),
                         km=(a.get("distance") or 0) / 1000, time_s=a.get("duration") or 0, run=is_run(kind),
                         in_app=any(abs((start - h).total_seconds()) < 120 for h in have)))
    return rows


def download_zip(conf, user_id, ids, path, progress=None):
    """Download the activities into a zip of .fit files at `path` (as a Garmin export would have them).
    Returns (downloaded, skipped: [(id, why)])."""
    c = Client(conf, user_id)
    got, skipped = 0, []
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for i, aid in enumerate(ids):
            if progress:
                progress(_("stahuji z Garmin Connect %(i)s/%(n)s", i=i + 1, n=len(ids)))
            try:
                name, data = c.fit(aid)
            except KeyRejected:
                raise
            except GarminApiError as e:
                skipped.append((aid, str(e)))
                continue
            z.writestr(name, data)
            got += 1
            if i + 1 < len(ids):
                time.sleep(PAUSE_S)
    return got, skipped
