"""Load a runner's races from ORIS into the database: events, classes, Livelox ID, official times and splits.

sync_all (flask sync-oris-all, run once a day from cron or webapp/cron.py) does it for every account with a
registration number, as sparingly as ORIS deserves: one getUserEventEntries per account (getUser only for an
account whose ORIS id is not known yet), getEvent and getSplits only for races new to the database (and for a
recent race until its results are in), PAUSE_S before every request, and nothing for an account loaded in the
last SYNC_HOURS (by its button, its upload or the day before).
"""
import datetime as dt
import time

import click
from flask import current_app
from flask.cli import with_appcontext

from .. import oris
from ..db import dumps
from . import matching
from . import splits as class_splits

PAUSE_S = 0.4        # seconds before every request to ORIS
SYNC_HOURS = 20.0    # an account loaded this recently is left out of sync_all


def upsert_event(con, ev):
    row = con.execute("SELECT id FROM events WHERE oris_id = ?", (ev["oris_id"],)).fetchone()
    vals = (ev["name"], ev["date"], ev["place"], ev["discipline"], ev["livelox_id"], ev["lat"], ev["lon"],
            dumps(ev.get("links") or []), dumps(ev.get("locations") or []))
    if row:
        con.execute("UPDATE events SET name=?, date=?, place=?, discipline=?, livelox_id=?, lat=?, lon=?, links=?,"
                    " locations=? WHERE id=?", (*vals, row["id"]))
        return row["id"]
    return con.execute("INSERT INTO events (name, date, place, discipline, livelox_id, lat, lon, links, locations,"
                       " oris_id) VALUES (?,?,?,?,?,?,?,?,?,?)", (*vals, ev["oris_id"])).lastrowid


def upsert_class(con, event_id, c):
    row = con.execute("SELECT id FROM classes WHERE oris_id = ?", (c["oris_id"],)).fetchone()
    vals = (c["name"], c["distance_km"], c["climb_m"], c["controls"])
    if row:
        con.execute("UPDATE classes SET name=?, distance_km=?, climb_m=?, controls=? WHERE id=?", (*vals, row["id"]))
        return row["id"]
    # a class of this race made earlier without the ORIS id (a race added by hand, a demo or a shared file):
    # take it over instead of adding a second one with the same name (UNIQUE event_id + name)
    row = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ?", (event_id, c["name"])).fetchone()
    if row:
        con.execute("UPDATE classes SET oris_id=?, distance_km=COALESCE(?, distance_km), climb_m=COALESCE(?, climb_m),"
                    " controls=COALESCE(?, controls) WHERE id=?", (c["oris_id"], *vals[1:], row["id"]))
        return row["id"]
    return con.execute("INSERT INTO classes (name, distance_km, climb_m, controls, event_id, oris_id)"
                       " VALUES (?,?,?,?,?,?)", (*vals, event_id, c["oris_id"])).lastrowid


def sync_user(con, conf, user_id, client=None, today=None, pause=PAUSE_S, lookup=True):
    """Returns a short Czech message for the job list. Raises ValueError when the number is not in ORIS.
    lookup False: the ORIS id of the account is taken from the database when it is known (no getUser)."""
    client = client or oris.client(conf)
    today = today or dt.date.today()
    user = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    regno = user["oris_regno"]
    if not regno:
        raise ValueError("V profilu chybí registrační číslo ORIS.")
    if lookup or not user["oris_user_id"]:
        u = client.user(regno)
        if u is None:
            raise ValueError(f"Registrační číslo {regno} v ORIS není.")
        con.execute("UPDATE users SET oris_user_id = ?, name = COALESCE(name, ?) WHERE id = ?",
                    (u["oris_user_id"], u["name"], user_id))
    else:
        u = dict(oris_user_id=user["oris_user_id"])
    new = with_time = with_class = 0
    for e in client.entries(u["oris_user_id"]):
        if dt.date.fromisoformat(e["date"]) > today:
            continue  # entered, not run yet
        cls = con.execute("SELECT * FROM classes WHERE oris_id = ?", (e["class_id"],)).fetchone()
        if cls is None:
            time.sleep(pause)
            ev = client.event(e["event_id"])
            if ev["cancelled"]:
                continue
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
            continue
        entry = con.execute("SELECT * FROM entries WHERE user_id = ? AND class_id = ?", (user_id, class_id)).fetchone()
        if entry is None:
            entry_id = con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (user_id, class_id)).lastrowid
            new += 1
        else:
            entry_id = entry["id"]
        # results appear in ORIS within days of the race: ask once for a new entry, and again while it is recent.
        # The answer holds the whole class, so it is also kept for the split-time analysis (class_splits);
        # a class asked before the app kept them is asked once more.
        recent = (today - dt.date.fromisoformat(e["date"])).days <= 30
        mine = entry is None or (entry["official_time_s"] is None and recent)
        if mine or not con.execute("SELECT 1 FROM class_splits WHERE class_id = ?", (class_id,)).fetchone():
            time.sleep(pause)
            raw = client.class_splits_raw(e["class_id"])
            if class_splits.store(con, class_id, raw) is None and not recent:
                class_splits.store_none(con, class_id)  # old race without split times: do not ask again
            else:
                with_class += 1
            s = oris.parse_splits(raw, regno)
            if s and mine:
                con.execute("UPDATE entries SET official_time_s=?, start_local=?, result_place=?, splits=? WHERE id=?",
                            (s["time_s"], s["start_local"], s["place"],
                             dumps(s["cumulative"]) if s["time_s"] is not None else None, entry_id))
                con.execute("UPDATE classes SET control_codes = ? WHERE id = ?", (dumps(s["control_codes"]), class_id))
                with_time += s["time_s"] is not None
                con.commit()
                matching.queue_analysis(con, entry_id)  # official times replace the GPS guess
        con.commit()
    con.execute("UPDATE users SET oris_synced_at = datetime('now') WHERE id = ?", (user_id,))
    con.commit()
    matching.match_user(con, user_id)
    total = con.execute("SELECT COUNT(*) FROM entries WHERE user_id = ?", (user_id,)).fetchone()[0]
    return (f"ORIS: {total} závodů ({new} nových), oficiální čas doplněn u {with_time}"
            + (f", mezičasy kategorie načteny u {with_class}." if with_class else "."))


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
