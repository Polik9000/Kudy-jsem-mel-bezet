"""Every registration number of an account (table user_regnos, docs/oris.md).

After a move to another club the runner gets a new number (BFM0903 -> ABC0903, sometimes other digits too). ORIS
keeps one person id for both: getUserEventEntries of that id lists the races under every number the runner had,
and the results of the old races carry the old number. getUser answers only for the number of today.

users.oris_regno stays the first number of the account (the login on the server, the triggers in schema.sql copy
it into user_regnos). Numbers seen in the runner's own ORIS entries are added by the ORIS sync ('oris'); in the
app on one's own computer the runner may add one in the profile ('rucne'). A number belongs to one account only.
"""
import re
import unicodedata

from .. import oris
from ..i18n import _
from . import accounts
from . import splits as class_splits


class Refused(ValueError):
    """The number cannot be added or removed; the message is a sentence for the page."""


def rows(con, user_id):
    """The numbers of the account, the number of the account first, then as they were added."""
    return con.execute("SELECT * FROM user_regnos WHERE user_id = ? ORDER BY source != 'ucet', added_at, regno",
                       (user_id,)).fetchall()


def of(con, user_id):
    """[number, ...] of the account, its first number first (also when the list misses it)."""
    first = con.execute("SELECT oris_regno FROM users WHERE id = ?", (user_id,)).fetchone()
    out = [first[0]] if first and first[0] else []
    return out + [r["regno"] for r in rows(con, user_id) if r["regno"] not in out]


def owner(con, regno):
    """Id of the account the number belongs to, or None."""
    row = con.execute("SELECT user_id FROM user_regnos WHERE regno = ? UNION SELECT id FROM users WHERE oris_regno = ?",
                      (regno, regno)).fetchone()
    return row[0] if row else None


def _plain(name):
    """'Tobiáš  Otta' and 'otta tobias' -> the same: no accents, any case, words in any order."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return " ".join(sorted(re.findall(r"\w+", text)))


def learn(con, user_id, regno, oris_user_id):
    """A number the runner was entered under in ORIS (their own entries: the same ORIS person). Added when no
    account has it yet. Returns whether it was added."""
    regno = accounts.clean_regno(regno)
    if not re.fullmatch(accounts.REGNO, regno) or owner(con, regno) is not None:
        return False
    con.execute("INSERT INTO user_regnos (user_id, regno, oris_user_id, source) VALUES (?, ?, ?, 'oris')",
                (user_id, regno, oris_user_id))
    return True


def add(con, conf, user, text, client=None):
    """Add another number to the account ("I moved to another club"). It is checked in ORIS: the number of today
    must belong to the same person (the same ORIS id or the same name), an old number ORIS no longer gives must
    be in the runner's own entries. Returns dict(regno, name); raises Refused."""
    regno = accounts.clean_regno(text)
    if not re.fullmatch(accounts.REGNO, regno):
        raise Refused(_("Registrační číslo má tvar tří písmen oddílu a čtyř číslic, např. BFM0000."))
    have = rows(con, user["id"])
    if not have and not user["oris_regno"]:
        raise Refused(_("Nejdřív zadej svoje registrační číslo ORIS."))
    who = owner(con, regno)
    if who == user["id"]:
        raise Refused(_("Číslo %(regno)s už máš.", regno=regno))
    if who is not None:
        raise Refused(_("Číslo %(regno)s patří jinému účtu.", regno=regno))
    client = client or oris.client(conf)
    ids = {r["oris_user_id"] for r in have if r["oris_user_id"]} | ({user["oris_user_id"]} - {None})
    try:
        person = client.user(regno)
        if person is None:
            # an old number: ORIS no longer gives it, but keeps the races the runner ran under it
            uid = next((i for i in sorted(ids) if any(e.get("regno") == regno for e in client.entries(i))), None)
            if uid is None:
                raise Refused(_("Registrační číslo %(regno)s v ORIS není ani mezi tvými závody.", regno=regno))
            person = dict(oris_user_id=uid, name=None)
    except oris.OrisError as e:
        raise Refused(_("ORIS teď neodpovídá, zkus číslo přidat později.")) from e
    names = {_plain(r["name"]) for r in have if r["name"]} | {_plain(user["name"])}
    if person["oris_user_id"] not in ids and _plain(person["name"]) not in names - {""}:
        raise Refused(_("Číslo %(regno)s patří v ORIS jménu %(name)s, ne tobě. Přidat jde jen tvoje vlastní číslo.",
                        regno=regno, name=person["name"]))
    con.execute("INSERT INTO user_regnos (user_id, regno, oris_user_id, name, source) VALUES (?, ?, ?, ?, 'rucne')",
                (user["id"], regno, person["oris_user_id"], person["name"]))
    con.commit()
    return dict(regno=regno, name=person["name"])


def races_under(con, user_id, regno):
    """How many of the runner's races have the number in the stored results of their class."""
    n = 0
    for r in con.execute("SELECT DISTINCT class_id FROM entries WHERE user_id = ?", (user_id,)):
        data = class_splits.load(con, r["class_id"]) or {}
        n += any((x.get("regno") or "").upper() == regno for x in data.get("runners", []))
    return n


def removable(con, user_id, regno):
    """Only a number added in the profile that no race of the account was found under (added by mistake)."""
    row = con.execute("SELECT source FROM user_regnos WHERE user_id = ? AND regno = ?", (user_id, regno)).fetchone()
    return bool(row) and row["source"] == "rucne" and races_under(con, user_id, regno) == 0


def remove(con, user_id, regno):
    if not removable(con, user_id, regno):
        raise Refused(_("Číslo %(regno)s smazat nejde: jsou pod ním závody, nebo je to číslo účtu.", regno=regno))
    con.execute("DELETE FROM user_regnos WHERE user_id = ? AND regno = ?", (user_id, regno))
    con.commit()
