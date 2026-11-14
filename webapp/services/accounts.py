"""Who may make an account, a forgotten password, and removing an account with everything that belongs only
to it.

    flask --app webapp.wsgi invite REGNO [REGNO ...] [--site URL]
    flask --app webapp.wsgi reset-code REGNO [--site URL]
    flask --app webapp.wsgi delete-account NAME_OR_REGNO [--yes]

A forgotten password: the app has no e-mail, so the administrator prints a one-time code for the account
(`reset-code`) and hands it to the runner, who sets a new password with it on the page /forgot. Only the hash
of the code is kept; it is good for RESET_HOURS and for one use, and RESET_TRIES wrong tries make it void.

An account is made from a registration number, and those are public: the registration form also wants the
code of that number, which only the administrator can print (`invite`) and hands to the runner. The code is
computed from the secret key of the installation, so nothing is stored; once the number has its account the
code is of no use (one number has one account), and a new secret key makes all unused codes void.

What delete-account removes: the user row, their races (entries), activities and .fit files, analyses and their output
folders, notes, speed models, jobs; and races they added by hand (not from ORIS) that nobody else has,
with the maps of those races.
What stays, because it is shared by everyone at a race: ORIS events and classes, their maps, the split
times of the classes, refreshment points and forbidden lines (only the "who added it" is cleared).
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import shutil
import urllib.parse

import click
from werkzeug.security import check_password_hash, generate_password_hash

from .. import db as dbm
from ..config import Config

REGNO = r"[A-Z]{3}\d{4}"  # three letters of the club and four digits, e.g. BFM0903


def clean_regno(text):
    """A registration number as typed ('bfm 0903') -> as stored ('BFM0903')."""
    return re.sub(r"\s+", "", text or "").upper()


def invite_code(conf, regno):
    """The code that proves a registration number belongs to who registers with it: 8 letters and digits
    (40 bits) shown as XXXX-XXXX."""
    mac = hmac.new(conf.secret_key().encode(), f"invite:{regno}".encode(), hashlib.sha256).digest()
    code = base64.b32encode(mac[:5]).decode()
    return f"{code[:4]}-{code[4:]}"


def code_ok(conf, regno, sent):
    """Is `sent` (as typed: any case, with or without the dash and spaces) the code of the number?"""
    plain = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())
    return hmac.compare_digest(plain(sent or "").encode(), plain(invite_code(conf, regno)).encode())


RESET_HOURS = 24
RESET_TRIES = 5


def _plain(code):
    """A code as typed (any case, with or without the dash and spaces) -> its letters and digits."""
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def new_reset_code(con, user_id):
    """Make a one-time code for a new password of the account and keep its hash. Returns the code (XXXX-XXXX);
    an earlier code of the account stops working."""
    code = base64.b32encode(secrets.token_bytes(5)).decode()
    con.execute("UPDATE users SET reset_hash = ?, reset_until = datetime('now', ?), reset_tries = 0 WHERE id = ?",
                (generate_password_hash(code), f"+{RESET_HOURS} hours", user_id))
    con.commit()
    return f"{code[:4]}-{code[4:]}"


def use_reset_code(con, regno, code, password_hash):
    """Set the new password of the account with this registration number when `code` is its one-time code and
    still good. Returns whether it was done; the code is then used up."""
    row = con.execute("SELECT id, reset_hash FROM users WHERE oris_regno = ? AND reset_hash IS NOT NULL"
                      " AND reset_until > datetime('now') AND reset_tries < ?",
                      (clean_regno(regno), RESET_TRIES)).fetchone()
    if row is None:
        return False
    if not check_password_hash(row["reset_hash"], _plain(code)):
        con.execute("UPDATE users SET reset_tries = reset_tries + 1 WHERE id = ?", (row["id"],))
        con.commit()
        return False
    con.execute("UPDATE users SET password_hash = ?, reset_hash = NULL, reset_until = NULL, reset_tries = 0 WHERE id = ?",
                (password_hash, row["id"]))
    con.commit()
    return True


def find(con, who):
    """Accounts meant by a login name or a registration number, also another number of the account (a move
    to another club, services/regnos.py). One registration number has one account; databases older than that
    rule may hold more."""
    regno = who.replace(" ", "").upper()
    return con.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE OR oris_regno = ?"
                       " OR id IN (SELECT user_id FROM user_regnos WHERE regno = ?) ORDER BY id",
                       (who, regno, regno)).fetchall()


def summary(con, user_id):
    one = lambda sql: con.execute(sql, (user_id,)).fetchone()[0]
    return dict(races=one("SELECT COUNT(*) FROM entries WHERE user_id = ?"),
                activities=one("SELECT COUNT(*) FROM activities WHERE user_id = ?"),
                analyses=one("SELECT COUNT(*) FROM analyses a JOIN entries e ON e.id = a.entry_id WHERE e.user_id = ?"),
                notes=one("SELECT COUNT(*) FROM leg_notes n JOIN entries e ON e.id = n.entry_id WHERE e.user_id = ?"),
                models=one("SELECT COUNT(*) FROM speed_models WHERE user_id = ?"))


def delete_user(con, conf, user_id):
    """Delete the account. Returns the summary of what it had."""
    had = summary(con, user_id)
    files = [r["file"] for r in con.execute("SELECT file FROM activities WHERE user_id = ?", (user_id,))]
    # the photos of the map kept for placing by hand (their rows go with the entries)
    files += [r["file"] for r in con.execute("SELECT p.file FROM photos p JOIN entries e ON e.id = p.entry_id"
                                             " WHERE e.user_id = ?", (user_id,))]
    # the screenshots of Livelox kept for cutting out by hand and for one without the course coming later
    for r in con.execute("SELECT course_file, maponly_file FROM screens WHERE user_id = ?", (user_id,)):
        files += [f for f in (r["course_file"], r["maponly_file"], os.path.splitext(r["course_file"])[0] + "_nahled.jpg")
                  if f]
    folders = [os.path.join("races", f"entry_{r['id']}{end}")
               for r in con.execute("SELECT id FROM entries WHERE user_id = ?", (user_id,))
               for end in ("", ".new", ".old")]   # and runner._staged folders
    folders += [os.path.join("fit", f"user_{user_id}"), os.path.join("models", f"user_{user_id}")]
    # races added by hand that only this runner has: they go, with their maps and cached elevation
    own = [r["id"] for r in con.execute(
        "SELECT ev.id FROM events ev WHERE ev.oris_id IS NULL AND ev.created_by = ? AND NOT EXISTS"
        " (SELECT 1 FROM entries e JOIN classes c ON c.id = e.class_id WHERE c.event_id = ev.id AND e.user_id != ?)",
        (user_id, user_id))]
    for ev in own:
        folders.append(os.path.join("maps", f"event_{ev}"))
        files += [os.path.join("dem", f"event_{ev}.npz"), os.path.join("dem", f"event_{ev}_cuzk.npz"),
                  os.path.join("osm", f"event_{ev}.json"), os.path.join("terrain", f"event_{ev}.npz")]
        con.execute("DELETE FROM events WHERE id = ?", (ev,))
    # shared things stay; only who added them is forgotten
    for table, column in (("events", "maponly_by"), ("events", "created_by"), ("classes", "course_by"),
                          ("refreshments", "created_by"), ("barriers", "created_by")):
        con.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} = ?", (user_id,))
    con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    con.commit()
    for rel in files:
        try:
            os.remove(conf.path(rel))
        except OSError:
            pass
    for rel in folders:
        shutil.rmtree(conf.path(rel), ignore_errors=True)
    return had


@click.command("invite")
@click.argument("regnos", nargs=-1, required=True)
@click.option("--site", default="", help="address of the site, e.g. https://example.org, to print whole links")
def invite_command(regnos, site):
    """Print the registration code (and the link with the form filled in) of each registration number."""
    conf = Config()
    dbm.init(conf.db_path)
    con = dbm.connect(conf.db_path)
    regnos = [clean_regno(r) for r in regnos]
    bad = [r for r in regnos if not re.fullmatch(REGNO, r)]
    if bad:
        raise click.ClickException(f"not a registration number (three letters and four digits): {', '.join(bad)}")
    for regno in regnos:
        code = invite_code(conf, regno)
        link = f"{site.rstrip('/')}{conf.url_prefix}/register?" + urllib.parse.urlencode(dict(regno=regno, kod=code))
        has = con.execute("SELECT 1 FROM users WHERE oris_regno = ?", (regno,)).fetchone()
        click.echo(f"{regno}  {code}  {link}" + ("  (already has an account)" if has else ""))


@click.command("reset-code")
@click.argument("regno")
@click.option("--site", default="", help="address of the site, e.g. https://example.org, to print a whole link")
def reset_code_command(regno, site):
    """Print a one-time code for a new password of the account with registration number REGNO."""
    conf = Config()
    dbm.init(conf.db_path)
    con = dbm.connect(conf.db_path)
    regno = clean_regno(regno)
    user = con.execute("SELECT id FROM users WHERE oris_regno = ?", (regno,)).fetchone()
    if user is None:
        raise click.ClickException(f"no account with the registration number {regno!r}")
    code = new_reset_code(con, user["id"])
    link = f"{site.rstrip('/')}{conf.url_prefix}/forgot?" + urllib.parse.urlencode(dict(regno=regno))
    click.echo(f"{regno}  {code}  good for {RESET_HOURS} hours and one use  {link}")


@click.command("delete-account")
@click.argument("who")
@click.option("--yes", is_flag=True, help="really delete (without it the command only lists what would go)")
def delete_account_command(who, yes):
    """Delete the account(s) with login name or registration number WHO."""
    conf = Config()
    dbm.init(conf.db_path)
    con = dbm.connect(conf.db_path)
    users = find(con, who)
    if not users:
        raise click.ClickException(f"no account with the login name or registration number {who!r}")
    for u in users:
        s = summary(con, u["id"])
        click.echo(f"{u['username']} (registration number {u['oris_regno'] or '-'}): {s['races']} races, "
                   f"{s['activities']} activities, {s['analyses']} analyses, {s['notes']} notes, {s['models']} models")
        if yes:
            delete_user(con, conf, u["id"])
            click.echo("  deleted")
    if not yes:
        click.echo("nothing deleted; run again with --yes")
        return
    dbm.migrate(con)  # the rule "one account per registration number" can now be put on the database
    con.commit()
