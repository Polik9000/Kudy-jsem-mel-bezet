"""The settings of the interface: the language (the link in the menu) and the light / dark mode (the switch in the
header). Both are kept with the account, not only in the browser: the app on one's own computer starts on another
port each time, and the browser keeps its storage per address with the port."""
from urllib.parse import urlsplit

from flask import abort, g, redirect, request, url_for

from .. import get_db, i18n
from . import bp

THEMES = ("", "svetly", "tmavy")  # "" = as the device


def _back():
    """Where to go after the switch: the page the link was on (same site only), else the races."""
    nxt = request.args.get("next") or ""
    parts = urlsplit(nxt)
    if nxt.startswith("/") and not nxt.startswith("//") and not parts.netloc:
        return nxt
    return url_for("ob.races")


def _save(column, value):
    """Keep the setting with the signed-in runner (nobody signed in: the browser keeps it alone)."""
    if g.get("user") is None:
        return
    db = get_db()
    db.execute(f"UPDATE users SET {column} = ? WHERE id = ?", (value, g.user["id"]))
    db.commit()


@bp.route("/language/<code>")
def set_language(code):
    if code not in i18n.LANGS:
        abort(404)
    _save("lang", code)
    resp = redirect(_back())
    resp.set_cookie(i18n.COOKIE, code, max_age=365 * 24 * 3600, samesite="Lax", httponly=True)
    return resp


@bp.route("/rezim", methods=["POST"])
def set_theme():
    """The light / dark switch (static/ob.js): {"rezim": "svetly" | "tmavy" | ""}."""
    theme = (request.get_json(silent=True) or {}).get("rezim")
    if theme not in THEMES:
        abort(400)
    _save("theme", theme)  # "" is a choice too (as the device); NULL = never chosen
    return "", 204
