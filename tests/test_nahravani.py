"""One file that cannot be uploaded does not stop the others (issue 6): a pair of Livelox screenshots with one of
them wrong, several runs with one broken, a file the page left out for its size, and an upload larger than the
server takes."""
import datetime as dt
import io
import os

from conftest import csrf
from fitfile import fit_bytes
from PIL import Image
from test_web_photo import entry
from test_web_races import con_of, work


def _png(size):
    buf = io.BytesIO()
    Image.new("RGB", size, (250, 250, 250)).save(buf, "PNG")
    return buf.getvalue()


def _files(client, entry_id, **files):
    data = dict(csrf_token=csrf(client), **{k: (io.BytesIO(v[0]), v[1]) for k, v in files.items()})
    return client.post(f"/races/{entry_id}/files", data=data, content_type="multipart/form-data",
                       follow_redirects=True).get_data(as_text=True)


def test_a_wrong_screenshot_does_not_throw_away_the_other(app, client, user):
    con, mine = entry(app, client, user, run=False)
    # the screenshot without the course is too small (400 px at least): the one with the course is kept
    html = _files(client, mine, screen_course=(_png((1200, 900)), "trat.png"), screen_maponly=(_png((300, 200)), "bez.png"))
    assert "bez.png: " in html and "Snímky z Livelox jsou uložené" in html
    row = con.execute("SELECT * FROM pending_screens").fetchone()
    assert row["course_file"] and not row["maponly_file"]
    # and the other way round: not a picture at all
    con.execute("DELETE FROM pending_screens")
    con.commit()
    html = _files(client, mine, screen_course=(b"not a picture", "trat.pdf"), screen_maponly=(_png((1200, 900)), "bez.png"))
    assert "trat.pdf: snímek obrazovky má být obrázek" in html and "Snímek bez tratě je uložený" in html
    row = con.execute("SELECT * FROM pending_screens").fetchone()
    assert row["maponly_file"] and not row["course_file"]
    # both wrong: nothing is kept and each one is named
    con.execute("DELETE FROM pending_screens")
    con.commit()
    html = _files(client, mine, screen_course=(_png((200, 200)), "a.png"), screen_maponly=(_png((200, 300)), "b.png"))
    assert "a.png: " in html and "b.png: " in html
    assert "Snímky z Livelox jsou uložené" not in html and "Snímek bez tratě je uložený" not in html
    assert con.execute("SELECT COUNT(*) FROM pending_screens").fetchone()[0] == 0
    assert not os.listdir(app.config["OB"].path("incoming"))


def _run(minutes):
    start = dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.timezone.utc)
    return fit_bytes([(t, 49.5 + t * 1e-5, 16.7) for t in range(0, minutes * 60, 2)], start=start)


def test_of_several_runs_a_broken_one_does_not_stop_the_others(app, client, user):
    good = _run(20)
    files = [(io.BytesIO(good), "dobry.fit"), (io.BytesIO(b"not a fit at all"), "rozbity.fit"),
             (io.BytesIO(b"not a zip"), "export.zip"), (io.BytesIO(good[:40]), "useknuty.fit")]
    r = client.post("/upload", data=dict(csrf_token=csrf(client), files=files), content_type="multipart/form-data",
                    follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "rozbity.fit: není soubor z hodinek" in html and "export.zip: není zip" in html
    assert "Nahráno souborů: 2" in html
    con = con_of(app)
    assert [j["payload"] for j in con.execute("SELECT payload FROM jobs WHERE kind = 'import_upload'")] and \
        con.execute("SELECT COUNT(*) FROM jobs WHERE kind = 'import_upload'").fetchone()[0] == 2
    work(app)
    work(app)
    done = {j["status"] for j in con.execute("SELECT status FROM jobs WHERE kind = 'import_upload'")}
    assert done == {"done", "failed"}            # the cut one fails in its own job, the good one is in
    assert con.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1


def test_files_left_out_by_the_page_are_named(app, client, user):
    files = [(io.BytesIO(_run(10)), "beh.fit")]
    html = client.post("/upload", data=dict(csrf_token=csrf(client), files=files,
                                            vynechano=["velky.fit|52428800", "obrovsky.zip|4294967296"]),
                       content_type="multipart/form-data", follow_redirects=True).get_data(as_text=True)
    assert "velky.fit je větší než 50 MB" in html and "obrovsky.zip je větší než 4096 MB" in html
    assert "Nahráno souborů: 1" in html
    # the race form: the run left out, the screenshot sent
    con, mine = entry(app, client, user, run=False)
    data = dict(csrf_token=csrf(client), vynechano="hodinky.fit|52428800",
                screen_course=(io.BytesIO(_png((1200, 900))), "trat.png"))
    html = client.post(f"/races/{mine}/files", data=data, content_type="multipart/form-data",
                       follow_redirects=True).get_data(as_text=True)
    assert "hodinky.fit je větší než 50 MB" in html and "Vyber aspoň jeden soubor" not in html
    assert con.execute("SELECT course_file FROM pending_screens").fetchone()[0]


def test_an_upload_larger_than_the_server_takes_comes_back_with_a_message(app, client, user):
    app.config["MAX_CONTENT_LENGTH"] = 50_000
    token = csrf(client)
    r = client.post("/upload", data=dict(csrf_token=token, files=(io.BytesIO(b"\0" * 80_000), "beh.fit")),
                    content_type="multipart/form-data", headers={"Referer": "http://localhost/upload"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/upload")
    r = client.post("/upload", data=dict(csrf_token=token, files=(io.BytesIO(b"\0" * 80_000), "beh.fit")),
                    content_type="multipart/form-data", headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200 and r.get_json()["redirect"]
    app.config["MAX_CONTENT_LENGTH"] = None
    assert "dohromady větší, než server přijme" in client.get("/upload").get_data(as_text=True)
    # the pages know the limit, for the script to leave out what is larger
    app.config["MAX_CONTENT_LENGTH"] = 4096 * 1024 * 1024
    assert "maxUpload: 4294967296" in client.get("/upload").get_data(as_text=True)
