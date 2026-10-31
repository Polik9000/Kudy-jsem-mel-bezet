"""A photo of the paper map through the web app: what the upload form takes, what the worker says, replacing
a photo with a KMZ, placing a photo by hand."""
import io
import os

import pytest
from conftest import csrf
from PIL import Image
from races import inputs
from test_web_races import synced, work


def entry(app, client, user, run=True):
    """The runner's entry of Pohora (ORIS 8989), with the run from the watch when run=True."""
    con, _ = synced(app, client, user)
    mine = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 8989").fetchone()["id"]
    if run:
        with open(inputs("pohora")[2], "rb") as f:
            client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(f.read()), "run.fit")),
                        content_type="multipart/form-data")
        work(app)
        con.execute("DELETE FROM jobs")
        con.commit()
    return con, mine


def send(client, entry_id, name, data, kind="course"):
    return client.post(f"/races/{entry_id}/map", data=dict(csrf_token=csrf(client), kind=kind,
                                                            kmz=(io.BytesIO(data), name)),
                       content_type="multipart/form-data", follow_redirects=True).get_data(as_text=True)


def jpeg_bytes(size=(1000, 800), pad=0):
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 255, 255)).save(buf, "JPEG")
    return buf.getvalue() + b"\0" * pad


def test_heic_photo_gets_a_sentence_on_what_to_do(app, client, user):
    con, mine = entry(app, client, user, run=False)
    html = send(client, mine, "IMG_0042.HEIC", b"\0\0\0\x18ftypheic\0\0\0\0mif1heic")
    assert "formátu HEIC" in html and "Nejkompatibilnější" in html
    assert not con.execute("SELECT 1 FROM jobs WHERE kind = 'georef_map'").fetchone()


@pytest.mark.needs_data
def test_heic_renamed_to_jpg_and_a_big_photo(app, client, user):
    con, mine = entry(app, client, user)
    assert "formátu HEIC" in send(client, mine, "mapa.jpg", b"\0\0\0\x18ftypheic\0\0\0\0mif1heic" + b"\0" * 2000)
    # a 60 MB photo (a phone JPEG with a lot of data after the picture) goes through the upload limit
    assert "Usazuje se na pozadí" in send(client, mine, "mapa.jpg", jpeg_bytes(pad=60 * 1024 * 1024))
    assert con.execute("SELECT 1 FROM jobs WHERE kind = 'georef_map'").fetchone()
    work(app)
    assert not os.listdir(app.config["OB"].path("incoming"))


# --- photos made up from the Pohora map (tools/fotka.py), placed through the web app -------------------------

import sys  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import fotka  # noqa: E402

from oroute import georef  # noqa: E402


@pytest.fixture(scope="module")
def pohora():
    return fotka.load(fotka.sources(["pohora"])[0], np.random.default_rng(100))


def made_photo(m, **p):
    """(JPEG bytes, the controls in pixels of the photo as the app keeps it) of a small made-up photo."""
    im, o, ph, q = fotka.make_photo(m, dict(fotka.BASE, mpx=0.8, **p), seed=5)
    data = fotka.jpeg(im, o, q)
    opened = georef.open_image(io.BytesIO(data))
    ctrl = fotka.to_opened(ph.forward(m["ctrl_px"]), ph, o, fotka._small(fotka.displayed(im, o)), fotka._small(im),
                           opened)
    return data, ctrl


def job(con, kind="georef_map"):
    return con.execute("SELECT * FROM jobs WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,)).fetchone()


def course_of(con, entry_id):
    return con.execute("SELECT c.* FROM classes c JOIN entries e ON e.class_id = c.id WHERE e.id = ?",
                       (entry_id,)).fetchone()


@pytest.mark.needs_data
def test_photo_lands_then_a_kmz_replaces_it(app, client, user, pohora):
    con, mine = entry(app, client, user)
    data, _ = made_photo(pohora, tilt=15, light=0.6, kelvin=5000, bg=0.25)
    assert "Usazuje se na pozadí" in send(client, mine, "IMG_2041.jpg", data)
    work(app)
    j = job(con)
    assert j["status"] == "done" and "Mapa usazena podle" in j["message"], j["error"]
    c = course_of(con, mine)
    assert c["course_source"] == "photo" and c["course_rms"] < 20 and c["course_n"] >= 14
    conf = app.config["OB"]
    assert os.path.exists(conf.path(c["course_file"] + ".course.json"))
    photo = con.execute("SELECT file FROM photos WHERE entry_id = ?", (mine,)).fetchone()["file"]
    assert os.path.exists(conf.path(photo))
    page = client.get(f"/races/{mine}").get_data(as_text=True)
    assert "z fotky" in page and "přesnost asi ±" in page and "Usadit fotku ručně" in page
    assert con.execute("SELECT 1 FROM jobs WHERE kind = 'analyse' AND entry_id = ?", (mine,)).fetchone()
    # what the runner drew stays when the map changes
    con.execute("INSERT INTO leg_notes (entry_id, leg_n, text) VALUES (?, 3, 'tady jsem bloudil')", (mine,))
    con.execute("DELETE FROM jobs")
    con.commit()
    with open(inputs("pohora")[0], "rb") as f:
        assert "Nahradila mapu z fotky" in send(client, mine, "course.kmz", f.read())
    c = course_of(con, mine)
    assert c["course_source"] == "kmz" and c["course_rms"] is None
    assert not os.path.exists(conf.path(c["course_file"] + ".course.json")) and not os.path.exists(conf.path(photo))
    assert not con.execute("SELECT 1 FROM photos").fetchone()
    assert con.execute("SELECT 1 FROM jobs WHERE kind = 'analyse' AND entry_id = ?", (mine,)).fetchone()
    assert con.execute("SELECT text FROM leg_notes WHERE entry_id = ?", (mine,)).fetchone()[0] == "tady jsem bloudil"
    assert "přesnost asi ±" not in client.get(f"/races/{mine}").get_data(as_text=True)
    # and a photo after that is not used
    assert "už je mapa z KMZ" in send(client, mine, "IMG_2042.jpg", data)
    assert not job(con)


@pytest.mark.needs_data
def test_photo_is_not_used_over_a_kmz_that_came_meanwhile(app, client, user, pohora):
    con, mine = entry(app, client, user)
    data, _ = made_photo(pohora)
    send(client, mine, "IMG_1.jpg", data)
    with open(inputs("pohora")[0], "rb") as f:          # a KMZ arrives before the worker gets to the photo
        send(client, mine, "course.kmz", f.read())
    work(app)
    j = job(con)
    assert j["status"] == "done" and "už je mapa z KMZ" in j["message"]
    assert course_of(con, mine)["course_source"] == "kmz"


@pytest.mark.needs_data
def test_of_two_photos_the_one_that_fits_better_stays(app, client, user, pohora):
    con, mine = entry(app, client, user)
    data, _ = made_photo(pohora, tilt=10)
    send(client, mine, "IMG_1.jpg", data)
    work(app)
    cid = course_of(con, mine)["id"]
    con.execute("UPDATE classes SET course_rms = 1.0 WHERE id = ?", (cid,))     # as if another runner's fitted 1 m
    con.commit()
    before = course_of(con, mine)["course_file"]
    send(client, mine, "IMG_2.jpg", data)
    work(app)
    assert "menší odchylkou (1 m)" in job(con)["message"] and course_of(con, mine)["course_rms"] == 1.0
    con.execute("UPDATE classes SET course_rms = 99.0 WHERE id = ?", (cid,))
    con.commit()
    send(client, mine, "IMG_3.jpg", data)
    work(app)
    assert "Nahradila předchozí mapu z fotky" in job(con)["message"] and course_of(con, mine)["course_rms"] < 20
    assert course_of(con, mine)["course_file"] == before


def check(client, entry_id, pts):
    return client.post(f"/races/{entry_id}/fotka/body", json=dict(points=[dict(control=n, u=u, v=v) for n, u, v in pts]),
                       headers={"X-CSRF-Token": csrf(client)}).get_json()


@pytest.mark.needs_data
def test_placing_a_photo_by_hand(app, client, user, pohora):
    con, mine = entry(app, client, user)
    # the photo landed by itself; the runner places it again by hand (to correct it, or as if it had not landed)
    data, ctrl = made_photo(pohora, tilt=12, rot=20)
    send(client, mine, "IMG_1.jpg", data)
    work(app)
    con.execute("DELETE FROM jobs")
    con.commit()
    page = client.get(f"/races/{mine}/fotka").get_data(as_text=True)
    assert "Klikni aspoň na 4 kontroly" in page
    assert client.get(f"/races/{mine}/fotka.jpg").status_code == 200
    # five controls spread over the course: the ones farthest west, east, south, north, and from the middle
    g = np.array([c for c in pohora["controls"]])
    pick = sorted({int(g[:, 0].argmin()), int(g[:, 0].argmax()), int(g[:, 1].argmin()), int(g[:, 1].argmax())})
    pick.append(max((k for k in range(len(g)) if k not in pick), key=lambda k: np.hypot(*(g[k] - g.mean(0)))))
    pts = [(str(k + 1), float(ctrl[k][0]), float(ctrl[k][1])) for k in pick]
    got = check(client, mine, pts[:3])
    assert not got["ok"] and not got.get("track")
    assert any("aspoň na 4" in p for p in got["problems"])
    got = check(client, mine, pts[:2] + [pts[0]])                         # the same control twice
    assert any("dvakrát" in p for p in got["problems"])
    # points on a line: three controls and a fourth between two of them
    mid = ("2", (pts[0][1] + pts[1][1]) / 2, (pts[0][2] + pts[1][2]) / 2)
    line = [pts[0], pts[1], mid, ("3", 2 * pts[1][1] - pts[0][1], 2 * pts[1][2] - pts[0][2])]
    assert any("přímce" in p for p in check(client, mine, line)["problems"])
    # one point on the wrong circle
    wrong = pts[:4] + [(pts[4][0], pts[4][1] + 120, pts[4][2] - 90)]
    got = check(client, mine, wrong)
    assert any(f"Kontrola {pts[4][0]} nesedí o" in p for p in got["problems"]), got
    got = check(client, mine, pts)
    assert got["ok"] and len(got["track"]) > 50 and max(got["deviation"].values()) < 40, got
    # the page remembers the points, and saving places the photo by them
    assert f'"{pts[4][0]}"' in client.get(f"/races/{mine}/fotka").get_data(as_text=True)
    r = client.post(f"/races/{mine}/fotka/ulozit", data=dict(csrf_token=csrf(client)), follow_redirects=True)
    assert "usazuje podle tvých bodů" in r.get_data(as_text=True)
    work(app)
    j = job(con)
    assert j["status"] == "done" and "podle 5 bodů" in j["message"], j["error"]
    c = course_of(con, mine)
    assert c["course_source"] == "manual" and c["course_rms"] < 25


# --- wrong inputs: a Czech sentence, nothing left running (docs/foto-mapy.md, part 7) --------------------------

@pytest.fixture(scope="module")
def others(pohora):
    from oroute.kmzmap import GeoMap
    maponly = dict(pohora, paper=GeoMap.from_kmz(inputs("pohora")[1]).image.crop((0, 145, 1510, 1037)))
    e5 = fotka.load(fotka.sources(["azymut-e5"])[0], np.random.default_rng(101))
    return {"bez-trate": maponly, "jina-kategorie": e5, "screenshot": GeoMap.from_kmz(inputs("pohora")[0]).image}


@pytest.mark.parametrize("kind,says", [
    ("rozmazana", "Fotka je rozmazaná"),
    ("tmava", "Fotka je moc tmavá"),
    ("bez-trate", "nejsou vidět fialová kolečka kontrol. Je to mapa s tratí?"),
    ("jina-kategorie", "neodpovídají tvé stopě"),
    ("pulka", "Vyfoť celou mapu"),
    ("dve-mapy", "dvě mapy"),
    ("screenshot", None),                     # a screenshot of Livelox is a picture like any other: it lands
])
@pytest.mark.needs_data
def test_wrong_photo_says_what_to_do(app, client, user, pohora, others, kind, says):
    con, mine = entry(app, client, user)
    data = fotka.bad_photo(kind, pohora, others.get(kind))
    assert "Usazuje se na pozadí" in send(client, mine, f"{kind}.jpg", data)
    work(app)
    j = job(con)
    if says is None:
        assert j["status"] == "done" and "Mapa usazena" in j["message"], j["error"]
        return
    assert j["status"] == "failed" and says in j["error"], j["error"]
    assert "\n" not in j["error"] and "Traceback" not in j["error"]            # one sentence, no listing
    assert not con.execute("SELECT 1 FROM jobs WHERE status IN ('queued', 'running')").fetchone()
    # the photo is kept: it can be placed by hand from the job list
    html = client.get("/jobs").get_data(as_text=True)
    assert "Usadit fotku ručně" in html and "Podrobnosti" not in html


@pytest.mark.needs_data
def test_glare_over_some_controls_lands_over_most_it_does_not(app, client, user, pohora):
    con, mine = entry(app, client, user)
    send(client, mine, "IMG_1.jpg", fotka.jpeg(*fotka.make_photo(pohora, dict(fotka.BASE, mpx=0.8, glare=5), 1)[:2], 90))
    work(app)
    assert job(con)["status"] == "done"                     # five controls under glare: the other eleven place it
    send(client, mine, "IMG_2.jpg", fotka.jpeg(*fotka.make_photo(pohora, dict(fotka.BASE, mpx=0.8, glare=13), 1)[:2], 90))
    work(app)
    j = job(con)
    assert j["status"] == "failed" and "odlesk nebo prst" in j["error"] and "usadit ručně" in j["error"]


@pytest.mark.needs_data
def test_photo_before_the_run_from_the_watch(app, client, user, pohora):
    con, mine = entry(app, client, user, run=False)
    data, _ = made_photo(pohora)
    assert "Nahraj nejdřív běh z hodinek" in send(client, mine, "IMG_1.jpg", data)
    assert not job(con)


@pytest.mark.needs_data
def test_photo_with_a_run_from_another_race(pohora):
    """The run paired with the race is from another day: at the official punch times there is no track."""
    from webapp import texts
    data, _ = made_photo(pohora)
    im = georef.open_image(io.BytesIO(data))
    from oroute.fitload import load_track
    track = load_track(inputs("azymut-e4")[2])
    with pytest.raises(georef.GeorefError) as e:
        georef.georeference(im, track, -86400.0 * 400, [60.0 * k for k in range(1, 18)])
    assert "běh z tohoto závodu" in texts.photo_failed(str(e.value), georef.photo_quality(im))
