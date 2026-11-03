"""Protection of the forms (CSRF), apart from the login (webapp/auth.py), so the login can be swapped for the
club site's own without losing it.

Every POST, PUT, PATCH and DELETE has to carry the token of the session, as the form field `csrf_token` or the
header `X-CSRF-Token`; templates get it from `csrf_token()`.
"""
import hmac
import secrets

from flask import abort, request, session

from .i18n import _


def check_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
        if not hmac.compare_digest(sent, session.get("csrf", "")) or not sent:
            abort(400, _("Neplatný formulář (CSRF), načti stránku znovu."))


def csrf_token():
    """The token of the session (made on first use)."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def init_app(app):
    app.before_request(check_csrf)
    app.context_processor(lambda: dict(csrf_token=csrf_token))
