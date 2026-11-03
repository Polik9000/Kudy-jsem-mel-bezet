"""The switch between the Czech and the English interface (the link in the menu)."""
from urllib.parse import urlsplit

from flask import abort, redirect, request, url_for

from .. import i18n
from . import bp


def _back():
    """Where to go after the switch: the page the link was on (same site only), else the races."""
    nxt = request.args.get("next") or ""
    parts = urlsplit(nxt)
    if nxt.startswith("/") and not nxt.startswith("//") and not parts.netloc:
        return nxt
    return url_for("ob.races")


@bp.route("/language/<code>")
def set_language(code):
    if code not in i18n.LANGS:
        abort(404)
    resp = redirect(_back())
    resp.set_cookie(i18n.COOKIE, code, max_age=365 * 24 * 3600, samesite="Lax", httponly=True)
    return resp
