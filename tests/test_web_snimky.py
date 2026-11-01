"""Two screenshots of Livelox (with and without the course) through the web app: the upload form, the job that
places them (services/screens.py), the labels, the one without the course coming later, replacing it by a KMZ,
cutting the map out by hand, and every wrong input with its sentence."""
import io
import json
import os
import sys

import numpy as np
import pytest
from conftest import csrf
from races import inputs
from test_web_photo import entry, job, send

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import snimek  # noqa: E402

from webapp.services import jobs  # noqa: E402
from webapp.worker import Ctx, load_handlers  # noqa: E402


@pytest.fixture(scope="module")
def pohora():
    return snimek.load(snimek.sources(["pohora"])[0], np.random.default_rng(100))


@pytest.fixture(scope="module")
def pair_png(pohora):
    a, b, _ = snimek.screens(pohora, 1.0)
    return png(a), png(b)


def png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def upload(client, entry_id, course=None, maponly=None, names=("trat.png", "bez.png")):
    data = dict(csrf_token=csrf(client))
    if course is not None:
        data["screen_course"] = (io.BytesIO(course), names[0])
    if maponly is not None:
        data["screen_maponly"] = (io.BytesIO(maponly), names[1])
    return client.post(f"/races/{entry_id}/files", data=data, content_type="multipart/form-data",
                       follow_redirects=True).get_data(as_text=True)


def work_georef(app):
    """Run the waiting jobs except the analyses they queue (those would find the best routes: minutes)."""
    load_handlers()
    ctx = Ctx(app.config["OB"])
    while True:
        j = jobs.claim(ctx.con)
        if j is None:
            break
        if j["kind"] == "analyse":                       # back in the queue, untouched
            ctx.con.execute("UPDATE jobs SET status = 'queued', started_at = NULL WHERE id = ?", (j["id"],))
            ctx.con.commit()
            break
        try:
            jobs.finish(ctx.con, j["id"], jobs.HANDLERS[j["kind"]](ctx, j))
        except jobs.Refused as e:
            ctx.con.rollback()
            jobs.fail(ctx.con, j["id"], str(e))
    ctx.con.close()


def event_of(con, entry_id):
    return con.execute("SELECT ev.* FROM events ev JOIN classes c ON c.event_id = ev.id JOIN entries e"
                       " ON e.class_id = c.id WHERE e.id = ?", (entry_id,)).fetchone()


def class_of(con, entry_id):
    return con.execute("SELECT c.* FROM classes c JOIN entries e ON e.class_id = c.id WHERE e.id = ?",
                       (entry_id,)).fetchone()


@pytest.mark.needs_data
def test_two_screenshots_give_both_maps_then_a_kmz_replaces_the_one_without_course(app, client, user, pair_png):
    con, mine = entry(app, client, user)
    assert "Snímky jsou nahrané" in upload(client, mine, *pair_png)
    work_georef(app)
    j = job(con)
    assert j["status"] == "done", j["error"]
    assert "Snímek s tratí usazen podle" in j["message"] and "Mapa bez tratě uložena pro celý závod" in j["message"]
    ev, c = event_of(con, mine), class_of(con, mine)
    assert ev["maponly_source"] == "snimek" and ev["maponly_by"] is not None and 0.9 < ev["maponly_res_m"] < 1.6
    assert 10 <= ev["maponly_acc_m"] < 60
    assert c["course_source"] == "screen" and c["course_n"] >= 14
    conf = app.config["OB"]
    shot = con.execute("SELECT * FROM screens").fetchone()
    assert os.path.exists(conf.path(shot["course_file"])) and os.path.exists(conf.path(shot["maponly_file"]))
    assert not os.listdir(conf.path("incoming"))
    assert con.execute("SELECT 1 FROM jobs WHERE kind = 'analyse' AND entry_id = ? AND status = 'queued'",
                       (mine,)).fetchone()
    page = client.get(f"/races/{mine}").get_data(as_text=True)
    assert "ze snímku Livelox, přesnost asi ±" in page and "m na pixel" in page and "Oříznout snímek" in page
    assert "z snímku" not in page
    # the KMZ without course replaces it, and the screenshots kept go
    con.execute("DELETE FROM jobs")
    con.commit()
    with open(inputs("pohora")[1], "rb") as f:
        assert "Nahradila mapu ze snímku Livelox" in send(client, mine, "maponly.kmz", f.read(), kind="maponly")
    ev = event_of(con, mine)
    assert ev["maponly_source"] == "kmz" and ev["maponly_acc_m"] is None
    assert not con.execute("SELECT 1 FROM screens").fetchone() and not os.path.exists(conf.path(shot["course_file"]))
    assert con.execute("SELECT 1 FROM jobs WHERE kind = 'analyse' AND entry_id = ?", (mine,)).fetchone()
    # a screenshot without course after that is not used; the one with the course still is
    con.execute("DELETE FROM jobs")
    con.commit()
    html = upload(client, mine, *pair_png)
    assert "KMZ, která je přesnější. Snímek bez tratě se nepoužil" in html
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and "Mapa bez tratě" not in j["message"]
    assert event_of(con, mine)["maponly_source"] == "kmz"


@pytest.mark.needs_data
def test_the_one_without_course_can_come_later(app, client, user, pair_png):
    con, mine = entry(app, client, user)
    # alone and first: it has nothing to be placed by
    assert "Nahraj nejdřív oba snímky" in upload(client, mine, maponly=pair_png[1])
    assert not job(con)
    upload(client, mine, course=pair_png[0])
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and "Snímek s tratí usazen" in j["message"], j["error"]
    assert class_of(con, mine)["course_source"] == "screen" and event_of(con, mine)["maponly_file"] is None
    upload(client, mine, maponly=pair_png[1])
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and "Mapa bez tratě uložena" in j["message"], j["error"]
    assert event_of(con, mine)["maponly_source"] == "snimek"


@pytest.mark.needs_data
def test_screenshots_need_the_run_and_official_times(app, client, user, pair_png):
    con, mine = entry(app, client, user, run=False)
    assert "chybí běh z hodinek" in upload(client, mine, *pair_png)
    assert not job(con)


@pytest.fixture(scope="module")
def other():
    return snimek.load(snimek.sources(["azymut-e5"])[0], np.random.default_rng(1))


@pytest.mark.parametrize("kind, said", [
    ("velikost", "Snímky nemají stejnou velikost"),
    ("priblizeni", "změnilo přiblížení nebo natočení mapy"),
    ("otoceni", "změnilo přiblížení nebo natočení mapy"),
    ("trat-v-bez", "Na snímku bez tratě je pořád vidět trať"),
    ("postupy", "Vypni v Livelox ostatní běžce"),
    ("jiny-zavod", "Snímky k sobě nepatří"),
])
@pytest.mark.needs_data
def test_wrong_pairs_get_one_sentence(app, client, user, pohora, other, kind, said):
    con, mine = entry(app, client, user)
    a, b, _ = snimek.bad_pair(kind, pohora, other)
    upload(client, mine, png(a), png(b))
    work_georef(app)
    j = job(con)
    assert j["status"] == "failed" and said in j["error"] and "\n" not in j["error"], j["error"]
    assert class_of(con, mine)["course_file"] is None and event_of(con, mine)["maponly_file"] is None
    assert not os.listdir(app.config["OB"].path("incoming"))
    assert not con.execute("SELECT 1 FROM jobs WHERE status IN ('queued', 'running')").fetchone()


@pytest.mark.parametrize("kind, said, maponly", [
    ("prohozene", "prohodil jsem je", True),
    ("posun15", "Mapa se mezi snímky posunula o", True),
    ("malo-priblizeny", "Snímek je málo přiblížený", True),
    ("moc-malo-priblizeny", "mapu bez tratě z něj nedělám", False),
])
@pytest.mark.needs_data
def test_pairs_that_are_used_with_a_note(app, client, user, pohora, kind, said, maponly):
    con, mine = entry(app, client, user)
    a, b, _ = snimek.bad_pair(kind, pohora)
    upload(client, mine, png(a), png(b))
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and said in j["message"], j["error"]
    assert (event_of(con, mine)["maponly_source"] == "snimek") == maponly
    assert class_of(con, mine)["course_source"] == "screen"


@pytest.mark.needs_data
def test_the_map_cut_out_by_hand(app, client, user, pair_png):
    con, mine = entry(app, client, user)
    upload(client, mine, *pair_png)
    work_georef(app)
    shot = con.execute("SELECT * FROM screens").fetchone()
    box = json.loads(shot["info"])["box"]
    page = client.get(f"/races/{mine}/fotka?snimek=1").get_data(as_text=True)
    assert "Oříznout snímek z Livelox" in page and "crop.js" in page
    img = client.get(f"/races/{mine}/fotka/snimek.jpg")
    assert img.status_code == 200 and img.mimetype == "image/jpeg"
    con.execute("DELETE FROM jobs")
    con.commit()
    # too small a rectangle is refused, a good one queues the job again with it
    html = client.post(f"/races/{mine}/fotka/orez", data=dict(csrf_token=csrf(client), x0=10, y0=10, x1=60, y1=60),
                       follow_redirects=True).get_data(as_text=True)
    assert "Obdélník je moc malý" in html and not job(con)
    x0, y0, x1, y1 = box
    html = client.post(f"/races/{mine}/fotka/orez", data=dict(csrf_token=csrf(client), x0=x0 - 30, y0=y0 - 30,
                                                              x1=x1 + 30, y1=y1 + 30), follow_redirects=True)
    assert "usazují znovu" in html.get_data(as_text=True)
    assert json.loads(job(con)["payload"])["crop"] == [x0 - 30, y0 - 30, x1 + 30, y1 + 30]
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and "Mapa bez tratě uložena" in j["message"], j["error"]
    shot = con.execute("SELECT * FROM screens").fetchone()
    assert json.loads(shot["crop"]) == [x0 - 30, y0 - 30, x1 + 30, y1 + 30] and shot["maponly_file"]


@pytest.mark.needs_data
def test_a_photo_does_not_replace_a_screenshot_that_fits_better(app, client, user, pair_png):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fotka
    from test_web_photo import made_photo
    con, mine = entry(app, client, user)
    upload(client, mine, *pair_png)
    work_georef(app)
    assert class_of(con, mine)["course_source"] == "screen"
    con.execute("UPDATE classes SET course_rms = 1.0 WHERE id = ?", (class_of(con, mine)["id"],))
    con.execute("DELETE FROM jobs")
    con.commit()
    data, _ = made_photo(fotka.load(fotka.sources(["pohora"])[0], np.random.default_rng(100)))
    send(client, mine, "IMG_1.jpg", data)
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and "už je mapa ze snímku Livelox s menší odchylkou" in j["message"], j["error"]
    assert class_of(con, mine)["course_source"] == "screen"


@pytest.mark.needs_data
def test_a_faint_course_left_on_the_one_without_is_taken_out(app, client, user, pohora):
    con, mine = entry(app, client, user)
    a, b, _ = snimek.bad_pair("slaba-trat", pohora)
    upload(client, mine, png(a), png(b))
    work_georef(app)
    j = job(con)
    assert j["status"] == "done" and "byla trať pořád slabě vidět" in j["message"], j["error"]
    assert event_of(con, mine)["maponly_source"] == "snimek"
