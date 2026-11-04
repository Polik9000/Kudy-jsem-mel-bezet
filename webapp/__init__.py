"""Web layer of OB tracker: accounts, ORIS, uploads, job queue, map pages.

No calculations here: the analysis is the code in the repo root (analyze.py, bestroute.py)
and the `oroute` package, started by `webapp.worker`.

Two blueprints, so the pages can be mounted into another Flask site:
  auth  login / registration; replace it with the host site's own login (it only has to set g.user)
  ob    everything else
The CSRF protection of the forms is webapp/security.py, outside both, so it stays when auth is replaced.
"""
import datetime as dt
import hashlib
import os

from flask import Flask, current_app, g, request
from markupsafe import Markup

from . import club
from . import db as dbm
from .config import Config

# The version of the installers (0.3.5): the build writes webapp/_version.py from the git tag (workflow Instalátory).
# A Docker or source run keeps the date below, or OB_VERSION when it is set.
try:
    from ._version import VERSION
except ImportError:
    VERSION = os.environ.get("OB_VERSION") or "2026.10.21"
# the club site's policy (docs/design-klubovy-web.md): nothing from another origin, no framing
CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; form-action 'self'")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
_versions = {}  # static file -> (time of its last change, short hash of its content)


def static_version(filename):
    """Short hash of a static file's content. It goes into the file's address (?v=...), so the browser may
    keep the file for a year and still asks for a new one the moment it changes."""
    path = os.path.join(STATIC, filename)
    try:
        mtime = os.stat(path).st_mtime_ns
    except OSError:
        return None
    hit = _versions.get(filename)
    if hit is None or hit[0] != mtime:
        with open(path, "rb") as f:
            hit = _versions[filename] = (mtime, hashlib.sha1(f.read()).hexdigest()[:10])
    return hit[1]


def get_db():
    if "db" not in g:
        g.db = dbm.connect(current_app.config["OB"].db_path)
    return g.db


def cfg():
    return current_app.config["OB"]


def _close_db(exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def create_app(instance=None):
    conf = Config(instance)
    dbm.init(conf.db_path)
    app = Flask(__name__, static_folder=None)
    app.config.update(OB=conf, SECRET_KEY=conf.secret_key(), MAX_CONTENT_LENGTH=conf.max_upload,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_NAME="ob_session",  # its own cookie next to the club site on the same domain
                      # a login lasts 90 days from the last visit (auth.load_user sends the cookie again once
                      # a day), not on every answer: style sheets and scripts must stay free of cookies
                      PERMANENT_SESSION_LIFETIME=dt.timedelta(days=90), SESSION_REFRESH_EACH_REQUEST=False,
                      TEMPLATES_AUTO_RELOAD=bool(os.environ.get("OB_DEV")))
    app.teardown_appcontext(_close_db)

    with open(os.path.join(STATIC, "skob-ikony-sprite.svg"), encoding="utf-8") as f:
        sprite = Markup(f.read())

    def ikona(name, cls=""):
        """An icon of the club site's sprite (the <svg> with the symbols is at the top of every page)."""
        return Markup('<svg class="ikona %s" aria-hidden="true"><use href="#i-%s"></use></svg>') % (cls, name)

    @app.context_processor
    def _layout():
        return dict(sprite=sprite, ikona=ikona, club=club, app_version=VERSION, dem_sources=conf.dem_sources,
                    local_app=conf.local, data_dir=conf.instance)

    @app.url_defaults
    def _static_version(endpoint, values):
        if endpoint == "ob.static" and "v" not in values:
            v = static_version(values.get("filename", ""))
            if v:
                values["v"] = v

    @app.after_request
    def _headers(resp):
        if request.endpoint == "ob.static" and request.args.get("v") and resp.status_code in (200, 304):
            # the address changes with the content (static_version), so it never has to be asked for again
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    from . import i18n, security
    i18n.init_app(app)
    security.init_app(app)
    from .auth import bp as auth_bp
    from .views import bp as ob_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(ob_bp)
    from .seed import seed_demo_command
    from .services.accounts import delete_account_command, invite_command, reset_code_command
    from .services.backup import backup_command, restore_command
    from .services.sync_oris import sync_all_command
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(sync_all_command)
    app.cli.add_command(backup_command)
    app.cli.add_command(restore_command)
    app.cli.add_command(delete_account_command)
    app.cli.add_command(invite_command)
    app.cli.add_command(reset_code_command)
    return app
