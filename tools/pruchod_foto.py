#!/usr/bin/env python3
"""A walk through the web app with a photo of the map (docs/foto-mapy.md): a separate instance with the demo
races where Pohora has no map with the course, two photos of that map (one that lands by itself, one that does
not), and the steps for tools/shot.mjs.

  OB_INSTANCE=/data/foto-mapy python tools/pruchod_foto.py OUT_DIR HOST_OUT_DIR      (in the dev container)
    OUT_DIR: where the photos and shots.json go (inside the container); HOST_OUT_DIR: the same folder as Chrome on
    the host sees it (the files are given to the upload fields by that path)
  then the web app (port 8010) and the worker on that instance, and
  node tools/shot.mjs OUT_DIR/shots.json OUT_DIR --base http://localhost:8010/ob --user foto --pass fotomapa1
"""
import io
import json
import os
import sys

import numpy as np
from werkzeug.security import generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fotka  # noqa: E402

from oroute import georef  # noqa: E402
from webapp import db as dbm  # noqa: E402
from webapp.config import Config  # noqa: E402
from webapp.seed import REGNO, seed_demo  # noqa: E402

USER, PASSWORD = "foto", "fotomapa1"
GOOD = dict(fotka.BASE, tilt=15, rot=-8, light=0.6, kelvin=5000, bg=0.2)
BAD_GLARE = 11            # glare over this many controls: it does not land by itself


def main():
    out, host = sys.argv[1], sys.argv[2].rstrip("/")
    os.makedirs(out, exist_ok=True)
    conf = Config()
    dbm.init(conf.db_path)
    con = dbm.connect(conf.db_path)
    row = con.execute("SELECT id FROM users WHERE username = ?", (USER,)).fetchone()
    uid = row["id"] if row else con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES (?,?,?)",
                                            (USER, generate_password_hash(PASSWORD), REGNO)).lastrowid
    con.commit()
    entries = seed_demo(con, conf, uid, refit=False)
    con.execute("DELETE FROM jobs")                  # the four demo analyses are not part of the walk
    entry = entries["pohora"]
    cls = con.execute("SELECT c.* FROM classes c JOIN entries e ON e.class_id = c.id WHERE e.id = ?", (entry,)).fetchone()
    if cls["course_file"] and os.path.exists(conf.path(cls["course_file"])):
        os.remove(conf.path(cls["course_file"]))
    con.execute("UPDATE classes SET course_file = NULL, course_source = NULL, course_rms = NULL WHERE id = ?",
                (cls["id"],))
    con.execute("DELETE FROM photos")
    con.execute("DELETE FROM analyses WHERE entry_id = ?", (entry,))
    con.commit()

    m = fotka.load(fotka.sources(["pohora"])[0], np.random.default_rng(100))
    im, o, ph, q = fotka.make_photo(m, GOOD, seed=11)
    with open(os.path.join(out, "IMG_dobra.jpg"), "wb") as f:
        f.write(fotka.jpeg(im, o, q, ph.focal35))
    bad = dict(GOOD, glare=BAD_GLARE)
    im, o, ph, q = fotka.make_photo(m, bad, seed=12)
    data = fotka.jpeg(im, o, q, ph.focal35)
    with open(os.path.join(out, "IMG_odlesky.jpg"), "wb") as f:
        f.write(data)
    opened = georef.open_image(io.BytesIO(data))
    ctrl = fotka.to_opened(ph.forward(m["ctrl_px"]), ph, o, fotka._small(fotka.displayed(im, o)), fotka._small(im),
                           opened)
    try:
        georef.place(opened, m["controls"], m["lat0"], m["lon0"])
        print("warning: the bad photo lands by itself; raise BAD_GLARE")
    except georef.GeorefError as e:
        print("the bad photo does not land:", e)
    # five controls spread over the course, clicked on the bad photo (the last one with a real mouse click)
    g = np.array(m["controls"])
    pick = sorted({int(g[:, 0].argmin()), int(g[:, 0].argmax()), int(g[:, 1].argmin()), int(g[:, 1].argmax())})
    pick.append(max((k for k in range(len(g)) if k not in pick), key=lambda k: np.hypot(*(g[k] - g.mean(0)))))
    pts = [[str(k + 1), round(float(ctrl[k][0]), 1), round(float(ctrl[k][1]), 1)] for k in pick]
    with open(os.path.join(out, "body.json"), "w") as f:
        json.dump(pts, f)
    race, prefix = f"/races/{entry}", "/ob"
    tab = "document.querySelector('a[href=\"#podklady\"]').click(); window.scrollTo(0, 0)"
    send_course = "document.querySelector('input[name=course]').form.submit()"
    jobs_say = lambda text: (f"fetch('{prefix}/jobs').then(r => r.text()).then(t => t.includes({json.dumps(text)}))")
    click_js = ("(async () => { for (const [n, u, v] of " + json.dumps(pts[:-1]) + ") {"
                " document.querySelector('[data-bod=\"' + n + '\"]').click();"
                " OB.map.fire('click', {latlng: L.latLng(-v, u)}); await new Promise(r => setTimeout(r, 900)); } })()")
    n, u, v = pts[-1]
    real_click = ("(() => { document.querySelector('[data-bod=\"" + n + "\"]').click();"
                  f" const p = OB.map.latLngToContainerPoint(L.latLng({-v}, {u}));"
                  " const r = document.getElementById('foto-mapa').getBoundingClientRect();"
                  " return [[r.left + p.x, r.top + p.y]]; })()")
    analysed = (f"fetch('{prefix}/jobs.json?entry={entry}').then(r => r.json())"
                ".then(d => d.active === 0 && d.analysis !== '')")
    shots = [
        dict(name="01-podklady-1440", path=race, wait=1500, eval=tab),
        dict(name="02-nahrana-fotka-1440", path=race, wait=1500, eval=tab,
             upload=dict(selector="input[name=course]", file=f"{host}/IMG_dobra.jpg")),
        dict(name="03-odeslano-1440", stay=True, eval=send_course, load=True, wait=1500),
        dict(name="04-ulohy-usazeno-1440", path="/jobs", wait=1000, until=jobs_say("Mapa usazena"), timeout=600000),
        dict(name="05-podklady-z-fotky-1440", path=race, wait=1500, eval=tab),
        dict(name="06-zavod-analyza-z-fotky-1440", path=race, wait=4000, until=analysed, timeout=1800000),
        dict(name="07-zavod-analyza-z-fotky-390", path=race, width=390, height=844, scale=2, wait=4000),
        dict(name="08-spatna-fotka-odeslana-1440", path=race, wait=1500, eval=tab,
             upload=dict(selector="input[name=course]", file=f"{host}/IMG_odlesky.jpg")),
        dict(name="09-odeslano-1440", stay=True, eval=send_course, load=True, wait=1500),
        dict(name="10-ulohy-neusazeno-1440", path="/jobs", wait=1000, until=jobs_say("Usadit fotku ručně"),
             timeout=600000),
        dict(name="11-rucne-prazdne-390", path=race + "/fotka", width=390, height=844, scale=2, wait=2500),
        dict(name="12-rucne-body-1440", path=race + "/fotka", wait=2500, eval=click_js, clickAt=real_click),
        dict(name="13-rucne-body-390", path=race + "/fotka", width=390, height=844, scale=2, wait=3500),
        dict(name="14-ulozeno-1440", path=race + "/fotka", wait=2500,
             eval="document.getElementById('foto-ulozit').form.submit()", load=True),
        dict(name="15-ulohy-rucne-1440", path="/jobs", wait=1000, until=jobs_say("bodů, které jsi označil"),
             timeout=600000),
        dict(name="16-zavod-rucne-1440", path=race, wait=4000, until=analysed, timeout=1800000),
        dict(name="17-kmz-misto-fotky-1440", path=race, wait=1500, eval=tab,
             upload=dict(selector="input[name=course]", file=f"{host}/course.kmz")),
        dict(name="18-odeslano-kmz-1440", stay=True, eval=send_course, load=True, wait=2000),
    ]
    with open(os.path.join(out, "shots.json"), "w", encoding="utf-8") as f:
        json.dump(shots, f, ensure_ascii=False, indent=1)
    import shutil
    shutil.copyfile(os.path.join(ROOT, "data", "pohora", "course.kmz"), os.path.join(out, "course.kmz"))
    print("entry", entry, "shots", len(shots))


if __name__ == "__main__":
    main()
