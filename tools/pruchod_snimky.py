#!/usr/bin/env python3
"""A walk through the web app with two Livelox screenshots (docs/snimky-livelox.md): a separate instance with the
demo races where Pohora has neither map, a pair of made-up screenshots of Pohora (tools/snimek.py: zoom 2, the page
of Livelox around the map, the map nudged by a few pixels and the course left faint on the one without, as on real
screenshots), and the steps for tools/shot.mjs.

  OB_INSTANCE=/data/snimky-livelox python tools/pruchod_snimky.py OUT_DIR HOST_OUT_DIR      (in the dev container)
    OUT_DIR: where the screenshots and shots.json go (inside the container); HOST_OUT_DIR: the same folder as Chrome
    on the host sees it (the files are given to the upload fields by that path)
  then the web app (port 8010) and the worker on that instance, and
  node tools/shot.mjs OUT_DIR/shots.json OUT_DIR --base http://localhost:8010/ob --user snimky --pass PASSWORD
    (PASSWORD: printed at the end; a new random one each run unless OB_WALK_PASSWORD is set)
"""
import json
import os
import secrets
import shutil
import sys

import numpy as np
from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import snimek  # noqa: E402

from webapp import db as dbm  # noqa: E402
from webapp.config import Config  # noqa: E402
from webapp.seed import REGNO, seed_demo  # noqa: E402

USER = "snimky"
# the walk account lives only in a throwaway dev instance; its password is not kept in the code
PASSWORD = os.environ.get("OB_WALK_PASSWORD") or secrets.token_urlsafe(12)
ZOOM, SHIFT = 2.0, (6, 3)


def main():
    out, host = sys.argv[1], sys.argv[2].rstrip("/")
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
    con.commit()
    entries = seed_demo(con, conf, uid, refit=False)
    con.execute("DELETE FROM jobs")                  # the four demo analyses are not part of the walk
    entry = entries["pohora"]
    cls = con.execute("SELECT c.* FROM classes c JOIN entries e ON e.class_id = c.id WHERE e.id = ?", (entry,)).fetchone()
    ev = con.execute("SELECT * FROM events WHERE id = ?", (cls["event_id"],)).fetchone()
    for f in (cls["course_file"], ev["maponly_file"]):
        if f and os.path.exists(conf.path(f)):
            os.remove(conf.path(f))
    con.execute("UPDATE classes SET course_file = NULL, course_source = NULL, course_rms = NULL WHERE id = ?",
                (cls["id"],))
    con.execute("UPDATE events SET maponly_file = NULL, maponly_source = NULL, maponly_by = NULL WHERE id = ?",
                (ev["id"],))
    con.execute("DELETE FROM screens")
    con.execute("DELETE FROM analyses WHERE entry_id = ?", (entry,))
    con.commit()

    m = snimek.load(snimek.sources(["pohora"])[0], np.random.default_rng(100))
    a, _, t = snimek.screens(m, ZOOM)
    b = snimek.faint(m, dict(t, ox=t["ox"] + SHIFT[0], oy=t["oy"] + SHIFT[1]))
    a.save(os.path.join(out, "livelox-trat.png"))
    b.save(os.path.join(out, "livelox-bez-trate.png"))
    shutil.copyfile(os.path.join(ROOT, "data", "pohora", "maponly.kmz"), os.path.join(out, "maponly.kmz"))

    race, prefix = f"/races/{entry}", "/ob"
    tab = "document.querySelector('a[href=\"#podklady\"]').click(); window.scrollTo(0, 0)"
    card = ("document.querySelector('a[href=\"#podklady\"]').click();"
            " document.querySelector('input[name=screen_course]').closest('.karta').scrollIntoView();"
            " document.querySelector('input[name=screen_course]').closest('.karta').querySelector('details').open = true")
    send = "document.querySelector('input[name=screen_course]').form.submit()"
    send_kmz = "document.querySelector('input[name=maponly]').form.submit()"
    jobs_say = lambda text: f"fetch('{prefix}/jobs').then(r => r.text()).then(t => t.includes({json.dumps(text)}))"
    analysed = (f"fetch('{prefix}/jobs.json?entry={entry}').then(r => r.json())"
                ".then(d => d.active === 0 && d.analysis !== '')")
    shots = [
        dict(name="01-podklady-karta-1440", path=race, wait=1500, eval=card),
        dict(name="02-podklady-karta-390", path=race, width=390, height=844, scale=2, wait=1500, eval=card),
        dict(name="03-vybrane-snimky-1440", path=race, wait=1500, eval=card,
             upload=dict(selector="input[name=screen_course]", file=f"{host}/livelox-trat.png")),
        dict(name="04-odeslano-1440", stay=True, wait=1000,
             upload=dict(selector="input[name=screen_maponly]", file=f"{host}/livelox-bez-trate.png"),
             eval=send, load=True),
        dict(name="05-ulohy-usazeno-1440", path="/jobs", wait=1000, until=jobs_say("Mapa bez tratě uložena"),
             timeout=900000),
        dict(name="06-podklady-ze-snimku-1440", path=race, wait=1500, eval=tab),
        dict(name="07-zavod-postupy-ze-snimku-1440", path=race, wait=4000, until=analysed, timeout=2400000),
        dict(name="08-zavod-postupy-ze-snimku-390", path=race, width=390, height=844, scale=2, wait=4000),
        dict(name="09-orez-1440", path=race + "/fotka?snimek=1", wait=3000),
        dict(name="10-orez-390", path=race + "/fotka?snimek=1", width=390, height=844, scale=2, wait=3000),
        dict(name="11-kmz-misto-snimku-1440", path=race, wait=1500, eval=tab,
             upload=dict(selector="input[name=maponly]", file=f"{host}/maponly.kmz")),
        dict(name="12-odeslano-kmz-1440", stay=True, eval=send_kmz, load=True, wait=2000),
        dict(name="13-zavod-po-kmz-1440", path=race, wait=4000, until=analysed, timeout=2400000),
    ]
    with open(os.path.join(out, "shots.json"), "w", encoding="utf-8") as f:
        json.dump(shots, f, ensure_ascii=False, indent=1)
    print("entry", entry, "shots", len(shots))
    print("login:", USER, PASSWORD)


if __name__ == "__main__":
    main()
