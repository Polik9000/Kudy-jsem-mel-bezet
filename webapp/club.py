"""The club: its name, logo and the links to its site (skob-results). Its pages are keyed by ORIS ids, the same
ids we keep in events.oris_id and users.oris_user_id; the mapping is the table in docs/pruzkum.md."""
import os
from urllib.parse import urlencode

# OB_LOCAL=1 (the app on one's own computer, also the default of docker-compose.yml): no club unless one is set
_LOCAL = os.environ.get("OB_LOCAL", "0") == "1"
BASE = os.environ.get("OB_CLUB_URL", "" if _LOCAL else "https://skobfm.vzdyonline.cz").rstrip("/")
# in the title and the header of every page
NAME = os.environ.get("OB_CLUB_NAME", "Kudy jsem měl běžet" if _LOCAL else "SKOB Frýdek-Místek")
LOGO = os.environ.get("OB_CLUB_LOGO", "ob-logo.svg" if _LOCAL else "skob-logo.svg")  # in webapp/static: header, icon
ENABLED = bool(BASE)  # OB_CLUB_URL="" (the app on one's own computer): no links to a club site at all


def home():
    return BASE + "/" if ENABLED else None


def event(oris_id):
    """The club page of a race (results and entries of the club's runners)."""
    return f"{BASE}/zavod/oris-{int(oris_id)}" if oris_id and ENABLED else None


def member(oris_user_id):
    return f"{BASE}/clen/{int(oris_user_id)}" if oris_user_id and ENABLED else None


def archive(oris_user_id, season=None):
    """All results of a member, optionally one season."""
    if not oris_user_id or not ENABLED:
        return None
    q = dict(clen=int(oris_user_id))
    if season:
        q["season"] = int(season)
    return f"{BASE}/archiv?{urlencode(q)}"
