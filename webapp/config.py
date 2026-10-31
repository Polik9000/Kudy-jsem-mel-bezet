"""Settings, all from environment variables so the same code runs in Docker and on the club server.

OB_INSTANCE      folder for the database and everything uploaded or computed (default: ./instance)
OB_SECRET_KEY    Flask session key (default: a random one, generated once and kept in the instance folder);
                 the registration codes are computed from it too (services/accounts.py)
OB_MAX_UPLOAD_MB largest upload accepted (default 4096, a whole Garmin export is big)
OB_ORIS_URL      ORIS API endpoint
OB_URL_PREFIX    path the app is served under (default /ob, next to the club site; empty = at the root)
OB_CLUB_URL      the club site the pages link to (default https://skobfm.vzdyonline.cz)
OB_CLUB_NAME     name of the club in the title and header of every page (default SKOB Frýdek-Místek)
OB_CLUB_LOGO     file name of the club logo in webapp/static (default skob-logo.svg)
OB_DEM           elevation source: auto (ČÚZK DMR 5G for Czech maps, AWS tiles elsewhere and as fallback),
                 aws (AWS tiles only, as before), cuzk (ČÚZK only, fail when it does not answer); default auto
OB_OSM           1 = fetch railways, motorways and fences from OpenStreetMap as barriers (default 1), 0 = never
OB_OSM_FENCES    1 = fences and walls from OpenStreetMap count as hard to cross (default 0: not verified to help)
OB_CLUB_PRIOR    1 = a runner's terrain factors start from the average of the club instead of the ISOM values
                 (needs three other runners with data in the terrain; default 0, see docs/validace.md)
OB_REGISTRATION  0 closes the registration (otherwise it is open to those with the code of their number)
OB_BACKUP_DIR    where flask backup puts the backups (default: backups/ in the instance folder; docs/provoz.md)
OB_BACKUP_KEEP   how many backups are kept (default 14)
OB_CRON_AT, OB_CRON_TZ, OB_CRON_ORIS, OB_CRON_BACKUP  the daily jobs of webapp/cron.py (docs/provoz.md)
"""
import os
import secrets
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root: analyze.py, bestroute.py, oroute/


class Config:
    def __init__(self, instance=None):
        self.instance = os.path.abspath(instance or os.environ.get("OB_INSTANCE") or os.path.join(ROOT, "instance"))
        self.max_upload = int(os.environ.get("OB_MAX_UPLOAD_MB", "4096")) * 1024 * 1024
        self.oris_url = os.environ.get("OB_ORIS_URL", "https://oris.ceskyorientak.cz/API/")
        self.url_prefix = os.environ.get("OB_URL_PREFIX", "/ob").rstrip("/")
        self.dem = os.environ.get("OB_DEM", "auto").lower()
        if self.dem not in ("aws", "cuzk", "auto"):
            self.dem = "auto"
        self.osm = os.environ.get("OB_OSM", "1") != "0"
        self.osm_fences = os.environ.get("OB_OSM_FENCES", "0") == "1"
        self.club_prior = os.environ.get("OB_CLUB_PRIOR", "0") == "1"
        self.oris_client = None  # tests: an object with user/entries/event/splits answering from saved responses
        self.osm_fetch = None    # tests: function(south, west, north, east) instead of oroute.osm.for_box
        os.makedirs(self.instance, exist_ok=True)

    @property
    def db_path(self):
        return os.path.join(self.instance, "app.db")

    @property
    def dem_sources(self):
        """Which elevation sources may be used (for the attribution in the page footer)."""
        return {"aws": ("aws",), "cuzk": ("cuzk",)}.get(self.dem, ("cuzk", "aws"))

    def path(self, *parts):
        """Absolute path inside the instance folder (files are stored in the database as relative paths)."""
        return os.path.join(self.instance, *parts)

    def secret_key(self):
        key = os.environ.get("OB_SECRET_KEY")
        if key:
            return key
        f = self.path("secret_key")
        try:
            # created exactly once, even when several server processes start together
            with os.fdopen(os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as fh:
                fh.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        for _ in range(50):  # another process may still be writing it
            with open(f) as fh:
                key = fh.read().strip()
            if key:
                return key
            time.sleep(0.02)
        raise RuntimeError(f"empty secret key file {f}")
