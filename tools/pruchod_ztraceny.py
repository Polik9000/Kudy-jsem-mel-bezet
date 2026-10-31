#!/usr/bin/env python3
"""A walk through the page "Ztratil jsem se u kontroly" (docs/ztraceny-u-kontroly.md), a look back after the race:
a separate instance with one race that has the two maps and no run (the night race of data-extra/: only "where was
I", a tap on the map), its scenes prepared at once (runner.run_lost, no worker needed), and the steps for
tools/shot.mjs (a phone and a desktop).

  OB_INSTANCE=/data/ztraceny python tools/pruchod_ztraceny.py OUT_DIR [--bela]     (in the dev container)
  then the web app (port 8010) on that instance, and on the host
  node tools/shot.mjs OUT_DIR/shots.json OUT_DIR --base http://localhost:8010/ob --user ztraceny --pass PASSWORD
    (PASSWORD: printed at the end; a new random one each run unless OB_WALK_PASSWORD is set)

--bela   the race of Bělá (data-extra/bela/: maps, run.fit, official.json) with its run: the analysis is queued,
         run `python -m webapp.worker --once` in the same instance before the shots; and a race of the same maps
         dated tomorrow without a run (the race page then says the look back is after the race)
"""
import json
import os
import secrets
import shutil
import sys

from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from webapp import db as dbm  # noqa: E402
from webapp.config import Config  # noqa: E402
from webapp.seed import REGNO  # noqa: E402
from webapp.services import runner, storage  # noqa: E402

USER = "ztraceny"
PASSWORD = os.environ.get("OB_WALK_PASSWORD") or secrets.token_urlsafe(12)
NAME, CLS, DATE = "Mistrovství oblasti v nočním OB", "H14C", "2023-10-20"


def bela(con, conf, uid):
    """The race of Bělá with its run and official times, its analysis queued; and a copy of it dated tomorrow
    without a run. Returns (entry, entry of tomorrow)."""
    import datetime as dt
    d = os.path.join(ROOT, "data-extra", "bela")
    with open(os.path.join(d, "race.json"), encoding="utf-8") as f:
        meta = json.load(f)
    with open(os.path.join(d, "official.json"), encoding="utf-8") as f:
        official = json.load(f)
    from webapp import oris
    from webapp.services import jobs
    from webapp.services.storage import save_activity
    entries = []
    for date, run in ((meta["date"], True), ((dt.date.today() + dt.timedelta(days=1)).isoformat(), False)):
        name = "Oblastní žebříček, Bělá" + ("" if run else " (zítra)")
        row = con.execute("SELECT id FROM events WHERE name = ? AND date = ?", (name, date)).fetchone()
        event_id = row["id"] if row else con.execute(
            "INSERT INTO events (name, date, place, created_by) VALUES (?,?,?,?)",
            (name, date, "Bělá (okr. Opava)", uid)).lastrowid
        row = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ?", (event_id, meta["class"])).fetchone()
        class_id = row["id"] if row else con.execute("INSERT INTO classes (event_id, name) VALUES (?, ?)",
                                                     (event_id, meta["class"])).lastrowid
        row = con.execute("SELECT id FROM entries WHERE user_id = ? AND class_id = ?", (uid, class_id)).fetchone()
        entry = row["id"] if row else con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)",
                                                  (uid, class_id)).lastrowid
        for src, cid in (("maponly.kmz", None), ("course.kmz", class_id)):
            tmp = storage.incoming(conf, ".kmz")[1]
            shutil.copyfile(os.path.join(d, src), tmp)
            rel = storage.save_map(conf, tmp, event_id, cid)
            if cid is None:
                con.execute("UPDATE events SET maponly_file = ?, maponly_by = ? WHERE id = ?", (rel, uid, event_id))
            else:
                con.execute("UPDATE classes SET course_file = ?, course_by = ? WHERE id = ?", (rel, uid, class_id))
        if run:
            with open(os.path.join(d, "run.fit"), "rb") as f:
                act, _ = save_activity(con, conf, uid, f.read(), "bela.fit", "upload")
            start = dt.datetime.fromisoformat(official["start_utc"]).astimezone(oris.TZ) \
                if hasattr(oris, "TZ") else None
            con.execute("UPDATE entries SET activity_id = ?, splits = ?, start_local = ? WHERE id = ?",
                        (act, json.dumps(official["cumulative"]),
                         start.strftime("%H:%M:%S") if start else None, entry))
            con.commit()
            jobs.enqueue(con, "analyse", user_id=uid, entry_id=entry)
        entries.append(entry)
    con.commit()
    return entries


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    conf = Config()
    dbm.init(conf.db_path)
    con = dbm.connect(conf.db_path)
    row = con.execute("SELECT id FROM users WHERE username = ?", (USER,)).fetchone()
    if row:
        uid = row["id"]
        con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(PASSWORD), uid))
    else:
        uid = con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES (?,?,?)",
                          (USER, generate_password_hash(PASSWORD), REGNO)).lastrowid
    row = con.execute("SELECT id FROM events WHERE name = ? AND date = ?", (NAME, DATE)).fetchone()
    event_id = row["id"] if row else con.execute("INSERT INTO events (name, date, place, created_by) VALUES (?,?,?,?)",
                                                 (NAME, DATE, "Borovec", uid)).lastrowid
    row = con.execute("SELECT id FROM classes WHERE event_id = ? AND name = ?", (event_id, CLS)).fetchone()
    class_id = row["id"] if row else con.execute("INSERT INTO classes (event_id, name) VALUES (?, ?)",
                                                 (event_id, CLS)).lastrowid
    row = con.execute("SELECT id FROM entries WHERE user_id = ? AND class_id = ?", (uid, class_id)).fetchone()
    entry = row["id"] if row else con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)",
                                              (uid, class_id)).lastrowid
    for name, cid in ((f"{NAME}.kmz", None), (f"{NAME}, {CLS}.kmz", class_id)):
        tmp = storage.incoming(conf, ".kmz")[1]
        shutil.copyfile(os.path.join(ROOT, "data-extra", name), tmp)
        rel = storage.save_map(conf, tmp, event_id, cid)
        if cid is None:
            con.execute("UPDATE events SET maponly_file = ?, maponly_by = ? WHERE id = ?", (rel, uid, event_id))
        else:
            con.execute("UPDATE classes SET course_file = ?, course_by = ? WHERE id = ?", (rel, uid, class_id))
    con.execute("DELETE FROM jobs")
    con.commit()
    runner.run_lost(con, conf, entry)
    con.execute("INSERT OR REPLACE INTO leg_notes (entry_id, leg_n, control_desc) VALUES (?, 3, ?)",
                (entry, "rozcestí, západní cesta"))
    con.commit()

    extra = bela(con, conf, uid) if "--bela" in sys.argv[2:] else None

    page = f"/races/{entry}/ztraceny"
    # the map is centred on the control picked: a tap 110 px below the middle is a runner south of it
    tap = ("(function () { var r = document.getElementById('z-mapa').getBoundingClientRect();"
           " return [[r.left + r.width / 2, r.top + r.height / 2 + 110]]; })()")
    pick = "document.querySelector('.ob-ztr-cip[data-k=\"3\"]').click()"
    shots = [
        dict(name="ztraceny-mobil", path=page + "#k3", width=390, height=844, scale=2, wait=2500, eval=pick,
             clickAt=tap, full=True),
        dict(name="ztraceny-mobil-okoli", path=page + "#k5", width=390, height=844, scale=2, wait=2500,
             eval="document.getElementById('z-okoli').click()", full=True),
        dict(name="ztraceny-desktop", path=page + "#k3", width=1440, height=900, scale=1, wait=2500, eval=pick,
             clickAt=tap),
    ]
    if extra:
        b, tomorrow = extra
        # Bělá after the race: the places from the track (the default), control 4; tapping where one was; and the
        # page of the race tomorrow (no link, a sentence)
        bp = f"/races/{b}/ztraceny"
        shots += [
            dict(name="bela-po-zavode-mobil", path=bp + "#k4", width=390, height=844, scale=2, wait=4000, full=True),
            dict(name="bela-po-zavode-desktop", path=bp + "#k4", width=1440, height=900, scale=1, wait=4000),
            dict(name="bela-kde-jsem-byl-mobil", path=bp + "#k4", width=390, height=844, scale=2, wait=3000,
                 eval="document.getElementById('z-misto').click()", clickAt=tap, full=True),
            dict(name="bela-zitra-zavod", path=f"/races/{tomorrow}", width=1440, height=900, scale=1, wait=1500),
            dict(name="bela-zitra-ztraceny", path=f"/races/{tomorrow}/ztraceny", width=390, height=844, scale=2,
                 wait=1500, full=True),
        ]
    with open(os.path.join(out, "shots.json"), "w", encoding="utf-8") as f:
        json.dump(shots, f, ensure_ascii=False, indent=1)
    print(f"entry {entry}; user {USER}, password {PASSWORD}")


if __name__ == "__main__":
    main()
