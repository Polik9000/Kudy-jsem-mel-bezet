"""Load a runner's races from ORIS into the database: events, classes, Livelox ID, official times and splits.

sync_all (flask sync-oris-all, run once a day from cron or webapp/cron.py) does it for every account with a
registration number, as sparingly as ORIS deserves: one getUserEventEntries per account (getUser only for an
account whose ORIS id is not known yet), getEvent and getSplits only for races new to the database (and for a
recent race until its results are in), PAUSE_S before every request, and nothing for an account loaded in the
last SYNC_HOURS (by its button, its upload or the day before).

An account may have several numbers (a move to another club, services/regnos.py): the races of every ORIS person
id of its numbers are loaded, and the runner is found in the results under any of them. An entry to the umbrella
of a multi-stage event is spread over its stages (services/stages.py).
"""
import datetime as dt
import time

import click
from flask import current_app
from flask.cli import with_appcontext

from .. import oris
from ..db import dumps
from ..i18n import _
from . import matching, regnos, stages
from . import splits as class_splits

PAUSE_S = 0.4        # seconds before every request to ORIS
SYNC_HOURS = 20.0    # an account loaded this recently is left out of sync_all


def _json_or_null(value):
    return None if value is None else dumps(value)


def upsert_event(con, ev):
    row = con.execute("SELECT id FROM events WHERE oris_id = ?", (ev["oris_id"],)).fetchone()
    vals = (ev["name"], ev["date"], ev["place"], ev["discipline"], ev["livelox_id"], ev["lat"], ev["lon"],
            dumps(ev.get("links") or []), dumps(ev.get("locations") or []), ev.get("parent_id"))
    if row:
        con.execute("UPDATE events SET name=?, date=?, place=?, discipline=?, livelox_id=?, lat=?, lon=?, links=?,"
                    " locations=?, stage_parent=COALESCE(?, stage_parent) WHERE id=?", (*vals, row["id"]))
        return row["id"]
    return con.execute("INSERT INTO events (name, date, place, discipline, livelox_id, lat, lon, links, locations,"
                       " stage_parent, oris_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (*vals, ev["oris_id"])).lastrowid


def _free_name(con, event_id, name, oris_id, skip_id=None):
    """A class name nobody else in this race has. ORIS can list two classes of one race under the same name;
    the second one then gets its ORIS id behind the name (the database keeps one name per race)."""
    taken = con.execute("SELECT 1 FROM classes WHERE event_id = ? AND name = ? AND id IS NOT ?",
                        (event_id, name, skip_id)).fetchone()
    return f"{name} ({oris_id})" if taken else name


def upsert_class(con, event_id, c):
    row = con.execute("SELECT id FROM classes WHERE oris_id = ?", (c["oris_id"],)).fetchone()
    if row is None:
        # a class of this race added without the ORIS id (by hand, or by an older version): it is the same one
        row = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ? AND oris_id IS NULL",
                          (event_id, c["name"])).fetchone()
        if row:
            con.execute("UPDATE classes SET oris_id = ? WHERE id = ?", (c["oris_id"], row["id"]))
    name = _free_name(con, event_id, c["name"], c["oris_id"], row["id"] if row else None)
    vals = (name, c["distance_km"], c["climb_m"], c["controls"])
    if row:
        con.execute("UPDATE classes SET name=?, distance_km=?, climb_m=?, controls=? WHERE id=?", (*vals, row["id"]))
        return row["id"]
    return con.execute("INSERT INTO classes (name, distance_km, climb_m, controls, event_id, oris_id)"
                       " VALUES (?,?,?,?,?,?)", (*vals, event_id, c["oris_id"])).lastrowid


def _oris_ids(con, client, user, lookup, pause):
    """The ORIS person ids of the account, from each of its numbers (one person keeps one id across clubs; getUser
    answers only for the number of today, an old number keeps the id it had). lookup False: a known id is taken
    from the database. Raises ValueError when ORIS knows none of the numbers."""
    have = regnos.rows(con, user["id"])
    if not have:   # a database the list was not filled in yet
        have = [dict(regno=user["oris_regno"], oris_user_id=user["oris_user_id"], source="ucet")]
    ids, asked = [], False
    for r in have:
        uid = r["oris_user_id"]
        if r["source"] != "oris" and (lookup or not uid):
            if asked:
                time.sleep(pause)
            asked = True
            u = client.user(r["regno"])
            if u is not None:
                uid = u["oris_user_id"]
                con.execute("UPDATE user_regnos SET oris_user_id = ?, name = ? WHERE user_id = ? AND regno = ?",
                            (uid, u["name"], user["id"], r["regno"]))
                if r["regno"] == user["oris_regno"]:
                    con.execute("UPDATE users SET oris_user_id = ?, name = COALESCE(name, ?) WHERE id = ?",
                                (uid, u["name"], user["id"]))
        if uid and uid not in ids:
            ids.append(uid)
    if not ids:
        raise ValueError(_("Registrační číslo %(regno)s v ORIS není.", regno=user["oris_regno"] or have[0]["regno"]))
    if not user["oris_user_id"]:
        con.execute("UPDATE users SET oris_user_id = ? WHERE id = ?", (ids[0], user["id"]))
    return ids


def _take(con, client, user_id, e, mine, today, pause, done, ev=None):
    """One entry of the runner from ORIS (e as oris.parse_entries gives it): the race with all its classes,
    the entry, official times and the split times of the class. ev: getEvent of the race when already asked."""
    cls = con.execute("SELECT * FROM classes WHERE oris_id = ?", (e["class_id"],)).fetchone()
    if cls is None:
        if ev is None:
            time.sleep(pause)
            ev = client.event(e["event_id"])
        if ev["cancelled"]:
            return
        event_id = upsert_event(con, ev)
        # every class of the race: the runner may have run another one than the entry says (oris_class)
        for other in ev["classes"]:
            if other["oris_id"] != e["class_id"]:
                upsert_class(con, event_id, other)
        c = next((c for c in ev["classes"] if c["oris_id"] == e["class_id"]), None) \
            or dict(oris_id=e["class_id"], name=e["class_name"], distance_km=None, climb_m=None, controls=None)
        class_id = upsert_class(con, event_id, c)
    else:
        class_id, event_id = cls["id"], cls["event_id"]
    # the runner chose another class of this race themselves: their entry in ORIS does not undo that
    if con.execute("SELECT 1 FROM entries e JOIN classes c ON c.id = e.class_id WHERE e.user_id = ?"
                   " AND e.class_chosen = 1 AND c.event_id = ? AND e.class_id != ?",
                   (user_id, event_id, class_id)).fetchone():
        return
    entry = con.execute("SELECT * FROM entries WHERE user_id = ? AND class_id = ?", (user_id, class_id)).fetchone()
    if entry is None:
        entry_id = con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (user_id, class_id)).lastrowid
        done["new"] += 1
    else:
        entry_id = entry["id"]
    # results appear in ORIS within days of the race: ask once for a new entry, and again while it is recent.
    # The answer holds the whole class, so it is also kept for the split-time analysis (class_splits);
    # a class asked before the app kept them is asked once more.
    recent = (today - dt.date.fromisoformat(e["date"])).days <= 30
    again = entry is None or (entry["official_time_s"] is None and recent)
    if again or not con.execute("SELECT 1 FROM class_splits WHERE class_id = ?", (class_id,)).fetchone():
        time.sleep(pause)
        raw = client.class_splits_raw(e["class_id"])
        if class_splits.store(con, class_id, raw) is None and not recent:
            class_splits.store_none(con, class_id)  # old race without split times: do not ask again
        else:
            done["with_class"] += 1
        s = oris.parse_splits(raw, mine + ([e["regno"]] if e.get("regno") else []))
        if s and again:
            con.execute("UPDATE entries SET official_time_s=?, start_local=?, result_place=?, splits=? WHERE id=?",
                        (s["time_s"], s["start_local"], s["place"],
                         _json_or_null(oris.usable_splits(s)), entry_id))
            con.execute("UPDATE classes SET control_codes = ? WHERE id = ?", (dumps(s["control_codes"]), class_id))
            done["with_time"] += s["time_s"] is not None
            con.commit()
            matching.queue_analysis(con, entry_id)  # official times replace the GPS guess
    con.commit()


def _umbrella(con, client, e, pause):
    """(known() of the umbrella event when the entry is to one, else None; getEvent of the race when it had to
    be asked). Asked only for a race new to the database, or one an older version saved that may be an umbrella."""
    umb = stages.known(con, e["event_id"])
    if umb is not None:
        return umb, None
    cls = con.execute("SELECT event_id FROM classes WHERE oris_id = ?", (e["class_id"],)).fetchone()
    if cls is not None and not stages.suspect(con, cls["event_id"]):
        return None, None
    time.sleep(pause)
    ev = client.event(e["event_id"])
    if ev["stages"] and not ev["cancelled"]:
        return stages.remember(con, ev), None
    if cls is not None:
        stages.not_umbrella(con, cls["event_id"])
    return None, ev


def _spread(con, client, user_id, e, umb, listed, mine, today, pause, done):
    """An entry to an umbrella event: the runner ran its stages in the class of the same name. A stage ORIS
    lists the runner in (or the runner has already) is left as it is."""
    for sid in umb["stages"]:
        if sid in listed or con.execute(
                "SELECT 1 FROM entries n JOIN classes c ON c.id = n.class_id JOIN events ev ON ev.id = c.event_id"
                " WHERE n.user_id = ? AND ev.oris_id = ?", (user_id, sid)).fetchone():
            continue
        row = con.execute("SELECT c.oris_id, ev.date FROM classes c JOIN events ev ON ev.id = c.event_id"
                          " WHERE ev.oris_id = ? AND c.name = ? AND c.oris_id IS NOT NULL",
                          (sid, e["class_name"])).fetchone()
        ev = None
        if row is None:
            time.sleep(pause)
            ev = client.event(sid)
            c = next((c for c in ev["classes"] if c["name"] == e["class_name"]), None)
            if ev["cancelled"] or c is None:
                continue
            class_oris, date = c["oris_id"], ev["date"]
        else:
            class_oris, date = row["oris_id"], row["date"]
        if dt.date.fromisoformat(date) > today:
            continue
        _take(con, client, user_id, dict(e, event_id=sid, class_id=class_oris, date=date), mine, today, pause,
              done, ev)


def sync_user(con, conf, user_id, client=None, today=None, pause=PAUSE_S, lookup=True, progress=None):
    """Returns a short Czech message for the job list. Raises ValueError when the number is not in ORIS.
    lookup False: the ORIS id of the account is taken from the database when it is known (no getUser).
    progress(text): how far it is, in Czech (said between races, when everything of the last one is saved)."""
    client = client or oris.client(conf)
    today = today or dt.date.today()
    say = progress or (lambda text: None)
    user = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user["oris_regno"] and not regnos.rows(con, user_id):
        raise ValueError(_("V profilu chybí registrační číslo ORIS."))
    ids = _oris_ids(con, client, user, lookup, pause)
    entries, seen = [], set()
    for k, uid in enumerate(ids):
        if k:
            time.sleep(pause)
        for e in client.entries(uid):
            if (e["event_id"], e["class_id"]) in seen:
                continue
            seen.add((e["event_id"], e["class_id"]))
            entries.append(e)
            if e.get("regno"):
                regnos.learn(con, user_id, e["regno"], uid)   # an old club: its races carry the old number
    con.commit()
    mine = regnos.of(con, user_id)
    listed = {e["event_id"] for e in entries}
    done = dict(new=0, with_time=0, with_class=0)
    umbrellas = []
    say(_("zatím %(done)s z %(total)s závodů", done=0, total=len(entries)))
    for i, e in enumerate(entries, 1):
        if dt.date.fromisoformat(e["date"]) <= today:   # else entered, not run yet
            umb, ev = _umbrella(con, client, e, pause)
            if umb is not None:
                umbrellas.append((e, umb))   # after the others: first the stages ORIS lists the runner in
            else:
                _take(con, client, user_id, e, mine, today, pause, done, ev)
        say(_("zatím %(done)s z %(total)s závodů", done=i, total=len(entries)))
    for e, umb in umbrellas:
        _spread(con, client, user_id, e, umb, listed, mine, today, pause, done)
        stages.mark(con, umb["oris_id"], umb["stages"])
        con.commit()
        stages.retire(con, umb["oris_id"])
    con.execute("UPDATE users SET oris_synced_at = datetime('now') WHERE id = ?", (user_id,))
    con.commit()
    matching.match_user(con, user_id)
    total = con.execute("SELECT COUNT(*) FROM entries WHERE user_id = ?", (user_id,)).fetchone()[0]
    return (_("ORIS: %(total)s závodů (%(new)s nových), oficiální čas doplněn u %(with_time)s",
        total=total, new=done["new"], with_time=done["with_time"])
            + (_(", mezičasy kategorie načteny u %(with_class)s.", with_class=done["with_class"])
               if done["with_class"] else "."))


def sync_all(con, conf, client=None, pause=PAUSE_S, hours=SYNC_HOURS, now=None, log=print):
    """sync_user for every account with a registration number that was not loaded in the last `hours`, one
    after the other. An account that fails (not in ORIS, ORIS down) is reported and the others go on.
    Returns dict(done, skipped, failed)."""
    client = client or oris.client(conf)
    now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    out = dict(done=0, skipped=0, failed=0)
    users = con.execute("SELECT id, username, oris_regno, oris_synced_at FROM users WHERE oris_regno IS NOT NULL"
                        " ORDER BY id").fetchall()
    first = True
    for u in users:
        if u["oris_synced_at"] and hours > 0:
            last = dt.datetime.fromisoformat(u["oris_synced_at"])
            if (now - last).total_seconds() < hours * 3600:
                out["skipped"] += 1
                continue
        if not first:
            time.sleep(pause)
        first = False
        try:
            msg = sync_user(con, conf, u["id"], client, today=now.date(), pause=pause, lookup=False)
        except Exception as e:  # one account must not stop the others (ORIS down, number gone, a bad answer)
            con.rollback()
            out["failed"] += 1
            log(f"{u['oris_regno']}: {e}")
            continue
        out["done"] += 1
        log(f"{u['oris_regno']}: {msg}")
    return out


@click.command("sync-oris-all")
@click.option("--hours", type=float, default=SYNC_HOURS, show_default=True,
              help="leave out the accounts loaded from ORIS this many hours ago or less (0: none)")
@with_appcontext
def sync_all_command(hours):
    """Load the new races from ORIS of every account with a registration number (once a day from cron)."""
    from .. import db as dbm
    conf = current_app.config["OB"]
    con = dbm.connect(conf.db_path)
    try:
        r = sync_all(con, conf, hours=hours, log=click.echo)
    finally:
        con.close()
    click.echo(f"ORIS: {r['done']} accounts loaded, {r['skipped']} loaded recently, {r['failed']} failed")
    if r["failed"] and not r["done"]:
        raise SystemExit(1)
