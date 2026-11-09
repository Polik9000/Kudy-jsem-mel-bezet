"""Simple accounts: user name + password, session cookie.

The rest of the app only uses g.user (a row of `users`) and @login_required, so on the club
site this module can be swapped for one that fills g.user from the site's own login. The CSRF
token of every form is not here but in webapp/security.py, so it stays when this module goes.
"""
import datetime as dt
import functools
import os
import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import cfg, get_db, oris
from .i18n import _
from .services import accounts, jobs

bp = Blueprint("auth", __name__, template_folder="templates")


LOCAL_USER = "ja"  # the one runner of the app on one's own computer (OB_LOCAL=1)
LOGIN_PAGES = ("auth.login", "auth.register", "auth.forgot", "auth.password", "auth.account_delete", "auth.logout")


def local_user(db):
    """The runner of the app on one's own computer: made on the first start, never asked for a password."""
    row = db.execute("SELECT * FROM users WHERE username = ?", (LOCAL_USER,)).fetchone()
    if row is None:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, '!')", (LOCAL_USER,))
        db.commit()
        row = db.execute("SELECT * FROM users WHERE username = ?", (LOCAL_USER,)).fetchone()
    return row


@bp.before_app_request
def load_user():
    if request.endpoint == "ob.static":
        g.user = None  # style sheets and scripts are the same for everyone: no database for them
        return
    if cfg().local:
        # one runner on their own computer: no accounts, the login pages lead to the races
        g.user = local_user(get_db())
        if request.endpoint in LOGIN_PAGES:
            return redirect(url_for("ob.races"))
        return
    uid = session.get("user_id")
    g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None
    today = dt.date.today().isoformat()
    if g.user is not None and session.get("day") != today:
        session["day"] = today  # the cookie goes out again once a day, so the 90 days count from the last visit


def _log_in(user_id):
    """A fresh session for the user that outlives the browser window (PERMANENT_SESSION_LIFETIME)."""
    session.clear()
    session["user_id"] = user_id
    session.permanent = True


@bp.app_context_processor
def inject():
    return dict(user=g.get("user"), registration_open=registration_open())


def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **kw):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.full_path if request.method == "GET" else None))
        return view(*a, **kw)
    return wrapped


def _safe_next():
    nxt = request.values.get("next") or ""
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("ob.races")


def registration_open():
    return os.environ.get("OB_REGISTRATION", "1") != "0" and not cfg().local


@bp.route("/register", methods=["GET", "POST"])
def register():
    """An account is made from an ORIS registration number: the name and the ORIS id come from ORIS,
    the number is also the login name. Registration numbers are public, so the form also wants the code
    of the number, which the administrator hands out (services/accounts.py)."""
    if not registration_open():
        abort(404)
    if request.method == "POST":
        regno = accounts.clean_regno(request.form.get("oris_regno"))
        password = request.form.get("password", "")
        db = get_db()
        if not re.fullmatch(accounts.REGNO, regno):
            flash(_("Registrační číslo má tvar tří písmen oddílu a čtyř číslic, např. BFM0000."), "error")
        elif len(password) < 8:
            flash(_("Heslo musí mít aspoň 8 znaků."), "error")
        elif password != request.form.get("password2", ""):
            flash(_("Hesla se neshodují."), "error")
        elif not accounts.code_ok(cfg(), regno, request.form.get("code")):
            # before the check below: without the code nobody learns which numbers have an account
            flash(_("Kód k tomuhle registračnímu číslu nesedí. Kód ti dá správce aplikace."), "error")
        elif db.execute("SELECT 1 FROM users WHERE username = ? COLLATE NOCASE OR oris_regno = ?"
                        " UNION SELECT 1 FROM user_regnos WHERE regno = ?", (regno, regno, regno)).fetchone():
            flash(_("Účet s tímhle registračním číslem už existuje. Přihlas se."), "error")
        else:
            person, note = None, None
            try:
                person = oris.client(cfg()).user(regno)
                if person is None:
                    flash(_("Registrační číslo %(regno)s v ORIS není.", regno=regno), "error")
                    return render_template("ob/register.html")
            except oris.OrisError:
                note = _("ORIS teď neodpovídá; jméno a závody se doplní, až se ozve.")
            cur = db.execute("INSERT INTO users (username, password_hash, oris_regno, oris_user_id, name)"
                             " VALUES (?,?,?,?,?)",
                             (regno, generate_password_hash(password), regno,
                              person["oris_user_id"] if person else None, person["name"] if person else None))
            db.commit()
            _log_in(cur.lastrowid)
            jobs.enqueue(db, "sync_oris", user_id=cur.lastrowid)
            flash(note or _("Vítej, %(name)s. Účet je založený a tvoje závody se načítají z ORIS.",
                name=person['name']), "ok")
            return redirect(url_for("ob.races"))
    return render_template("ob/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        # The login name or the registration number, also another number of the account after a move to another
        # club (one number has one account; a database from before that rule may hold more, then the password
        # says which one is meant).
        db = get_db()
        found = db.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (name,)).fetchall()
        found += db.execute("SELECT * FROM users WHERE oris_regno = ? OR id IN (SELECT user_id FROM user_regnos"
                            " WHERE regno = ?) ORDER BY id", (accounts.clean_regno(name),) * 2).fetchall()
        row = next((r for r in found if check_password_hash(r["password_hash"], password)), None)
        if row:
            nxt = _safe_next()
            _log_in(row["id"])
            return redirect(nxt)
        flash(_("Špatné jméno nebo heslo."), "error")
    return render_template("ob/login.html", registration_open=registration_open())


@bp.route("/password", methods=["POST"])
@login_required
def password():
    """Change of the password from the profile page (the current one has to be given)."""
    new = request.form.get("password", "")
    if not check_password_hash(g.user["password_hash"], request.form.get("current", "")):
        flash(_("Současné heslo nesedí."), "error")
    elif len(new) < 8:
        flash(_("Nové heslo musí mít aspoň 8 znaků."), "error")
    elif new != request.form.get("password2", ""):
        flash(_("Nová hesla se neshodují."), "error")
    else:
        db = get_db()
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), g.user["id"]))
        db.commit()
        flash(_("Heslo je změněné."), "ok")
    return redirect(url_for("ob.profile"))


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """A new password without the old one: with the registration number and the one-time code the
    administrator printed for it (`reset-code`, services/accounts.py). There is no e-mail in the app."""
    if request.method == "POST":
        new = request.form.get("password", "")
        db = get_db()
        if len(new) < 8:
            flash(_("Nové heslo musí mít aspoň 8 znaků."), "error")
        elif new != request.form.get("password2", ""):
            flash(_("Nová hesla se neshodují."), "error")
        elif not accounts.use_reset_code(db, request.form.get("oris_regno"), request.form.get("code"),
                                         generate_password_hash(new)):
            # one answer for a wrong code, an old one and a number without an account
            flash(_("Kód k tomuhle registračnímu číslu nesedí nebo už neplatí. Nový ti dá správce aplikace."), "error")
        else:
            flash(_("Heslo je změněné. Přihlas se novým heslem."), "ok")
            return redirect(url_for("auth.login"))
    return render_template("ob/forgot.html")


@bp.route("/account/delete", methods=["POST"])
@login_required
def account_delete():
    """The runner closes their own account from the profile page (the password confirms it): the same as the
    command delete-account. What is shared by a race stays (services/accounts.py)."""
    if not check_password_hash(g.user["password_hash"], request.form.get("password", "")):
        flash(_("Heslo nesedí, účet zůstává."), "error")
        return redirect(url_for("ob.profile"))
    accounts.delete_user(get_db(), cfg(), g.user["id"])
    session.clear()
    flash(_("Účet je zrušený a tvoje data jsou smazaná."), "ok")
    return redirect(url_for("auth.login"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
