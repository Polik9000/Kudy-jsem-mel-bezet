"""Demo data: the four analysed races from data/ for one user.

    flask --app webapp.wsgi seed-demo USERNAME [--password ...]

Works offline: the two Czech races take their official times from the saved ORIS responses in
tests/fixtures/oris, the two Polish ones (not in ORIS) are entered as races added by hand.
"""
import json
import os
import shutil

import click
from werkzeug.security import generate_password_hash

from . import db as dbm
from . import oris
from .config import ROOT, Config
from .db import dumps
from .services import matching, storage, sync_oris
from .services import splits as class_splits

REGNO = "BFM0903"
DEMO = [
    dict(folder="azymut-e5", name="Azymut Cup 2026 - Day 5", date="2026-08-14", place="Boguchwała", cls="O3",
         time=76 * 60 + 57),
    dict(folder="azymut-e4", name="Azymut Cup 2026 - Day 4", date="2026-08-12", place="Białobrzegi", cls="O3",
         time=55 * 60 + 7),
    dict(folder="pohora", oris_event=8989, oris_class=202420),
    dict(folder="petrvald", oris_event=9827, oris_class=215134),
]


def demo_dir(folder):
    """Where the maps and the run of a demo race are: data/, or the folder OB_TEST_DATA."""
    return os.path.join(os.environ.get("OB_TEST_DATA") or os.path.join(ROOT, "data"), folder)


def _fixture(name):
    with open(os.path.join(ROOT, "tests", "fixtures", "oris", name), encoding="utf-8") as f:
        return json.load(f)["Data"]


def seed_demo(con, conf, user_id, refit=True):
    """Create the four races with their maps and activities and queue their analysis. Returns the entry ids
    by data folder. Safe to run twice."""
    out = {}
    for d in DEMO:
        if "oris_event" in d:
            ev = oris.parse_event(_fixture(f"getEvent_{d['oris_event']}.json"))
            event_id = sync_oris.upsert_event(con, ev)
            class_id = sync_oris.upsert_class(con, event_id,
                                              next(c for c in ev["classes"] if c["oris_id"] == d["oris_class"]))
            raw = _fixture(f"getSplits_{d['oris_class']}.json")
            class_splits.store(con, class_id, raw)
            s = oris.parse_splits(raw, REGNO)
            con.execute("UPDATE classes SET control_codes = ? WHERE id = ?", (dumps(s["control_codes"]), class_id))
            official = (s["time_s"], s["start_local"], s["place"], dumps(s["cumulative"]))
        else:
            row = con.execute("SELECT id FROM events WHERE name = ? AND date = ? AND created_by = ?",
                              (d["name"], d["date"], user_id)).fetchone()
            event_id = row["id"] if row else con.execute(
                "INSERT INTO events (name, date, place, created_by) VALUES (?,?,?,?)",
                (d["name"], d["date"], d["place"], user_id)).lastrowid
            row = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ?", (event_id, d["cls"])).fetchone()
            class_id = row["id"] if row else con.execute("INSERT INTO classes (event_id, name) VALUES (?, ?)",
                                                         (event_id, d["cls"])).lastrowid
            official = (d["time"], None, None, None)
        row = con.execute("SELECT id FROM entries WHERE user_id = ? AND class_id = ?", (user_id, class_id)).fetchone()
        entry_id = row["id"] if row else con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)",
                                                     (user_id, class_id)).lastrowid
        con.execute("UPDATE entries SET official_time_s = ?, start_local = ?, result_place = ?, splits = ? WHERE id = ?",
                    (*official, entry_id))
        src = demo_dir(d["folder"])
        for name, cid in (("maponly.kmz", None), ("course.kmz", class_id)):
            tmp = storage.incoming(conf, ".kmz")[1]
            shutil.copyfile(os.path.join(src, name), tmp)
            rel = storage.save_map(conf, tmp, event_id, cid)
            if cid is None:
                con.execute("UPDATE events SET maponly_file = ?, maponly_by = ? WHERE id = ?", (rel, user_id, event_id))
            else:
                con.execute("UPDATE classes SET course_file = ?, course_by = ? WHERE id = ?", (rel, user_id, class_id))
        with open(os.path.join(src, "run.fit"), "rb") as f:
            storage.save_activity(con, conf, user_id, f.read(), f"{d['folder']}.fit", "fit")
        con.commit()
        out[d["folder"]] = entry_id
    matching.match_user(con, user_id, queue=False)
    for entry_id in out.values():
        matching.queue_analysis(con, entry_id, refit=refit)
    return out


@click.command("seed-demo")
@click.argument("username")
@click.option("--password", help="needed when the user does not exist yet")
def seed_demo_command(username, password):
    """Load the four demo races from data/ for USERNAME and queue their analysis."""
    conf = Config()
    dbm.init(conf.db_path)
    con = dbm.connect(conf.db_path)
    row = con.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,)).fetchone()
    if row is None and con.execute("SELECT 1 FROM users WHERE oris_regno = ?", (REGNO,)).fetchone():
        # one account per registration number: the demo races belong to the account that has it
        other = con.execute("SELECT username FROM users WHERE oris_regno = ?", (REGNO,)).fetchone()["username"]
        raise click.UsageError(f"the registration number {REGNO} of the demo races already has the account "
                               f"{other!r}: run seed-demo {other}")
    if row is None:
        if not password or len(password) < 8:
            raise click.UsageError("the user does not exist: give --password (at least 8 characters) to create it")
        uid = con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES (?,?,?)",
                          (username, generate_password_hash(password), REGNO)).lastrowid
        con.commit()
    else:
        uid = row["id"]
    entries = seed_demo(con, conf, uid)
    click.echo(f"{len(entries)} races queued for analysis; the worker runs them (see the Úlohy page).")
