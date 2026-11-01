"""The help page "Jak na to" (webapp/views/napoveda.py), and the single-activity zip of Garmin Connect it advises."""
import io
import os
import zipfile

from conftest import csrf
from races import inputs
from test_web_races import synced, work


def test_help_page_is_open_and_linked_from_the_header_and_the_empty_list(app, client):
    html = client.get("/jak-na-to").get_data(as_text=True)               # without logging in
    for words in ("Exportovat soubor", "Export Your Data", "Request Data Export", "48 hodin až 30 dní",
                  "tři čárky", "Mapa s tratí", "Pouze mapa", "Když Livelox stažení nedovolí", "fotka papírové mapy",
                  "Ctrl+Shift+M", "5000 × 4000", "Capture full size screenshot", "Mapu neposouvej ani nepřibližuj",
                  "Snímek z Livelox s tratí", "Snímek z Livelox bez tratě", "nesdílej je dál",
                  "Schválná zastávka", "Ztráta kontaktu s mapou", "Únava", "Průměrný běžec",
                  "Ztratil jsem se u kontroly", "Nedalo se minout", "Neměl jsi hádat směr ke kontrole",
                  "Rozbor po závodě"):
        assert words in html, words
    for gone in ("OB postupy", "Exportovat originál", "Google Earth (KMZ)"):   # not advised any more
        assert gone not in html, gone
    assert "<img" not in html.split("ikona-nadpis")[1].split("<footer")[0]       # (no pictures of other sites)
    assert 'href="/jak-na-to"' in client.get("/login").get_data(as_text=True)


def test_empty_race_list_points_to_the_help(app, client, user):
    html = client.get("/").get_data(as_text=True)
    assert "Zatím tu nejsou žádné závody" in html and html.count('href="/jak-na-to"') == 3   # both menus and the list


def _one_run_zip(folder):
    """What Garmin Connect gives for "Exportovat soubor" of one activity: a zip with its .fit."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z, open(inputs(folder)[2], "rb") as f:
        z.writestr("21915848383_ACTIVITY.fit", f.read())
    return buf.getvalue()


def test_zip_of_one_activity_is_a_run_not_an_account_export(app, client, user):
    """A zip with one .fit is imported like the .fit: nothing of an earlier Garmin export is dropped for it."""
    con, _ = synced(app, client, user)
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        for folder in ("pohora", "azymut-e4"):
            with open(inputs(folder)[2], "rb") as f:
                z.writestr(f"{folder}.fit", f.read())
    export = io.BytesIO()
    with zipfile.ZipFile(export, "w") as z:
        z.writestr("DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip", inner.getvalue())
    client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(export.getvalue()), "export.zip")),
                content_type="multipart/form-data")
    work(app)
    kept = con.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    client.post("/upload", data=dict(csrf_token=csrf(client), files=(io.BytesIO(_one_run_zip("azymut-e5")), "a.zip")),
                content_type="multipart/form-data")
    work(app)
    job = con.execute("SELECT * FROM jobs WHERE kind = 'import_upload' ORDER BY id DESC").fetchone()
    assert job["status"] == "done", job["error"]
    assert job["message"].startswith("Aktivita uložena.") and "Smazáno" not in job["message"]
    rows = con.execute("SELECT source FROM activities ORDER BY id").fetchall()
    assert len(rows) == kept + 1 and rows[-1]["source"] == "fit"
    assert os.listdir(app.config["OB"].path("incoming")) == []


def test_race_page_takes_the_zip_of_one_activity(app, client, user):
    con, _ = synced(app, client, user)
    e = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                    " WHERE ev.oris_id = 8989").fetchone()["id"]
    html = client.get(f"/races/{e}").get_data(as_text=True)
    assert 'accept=".fit,.zip"' in html
    # the three ways to the map, best first
    heads = ["1a. Mapa s tratí (KMZ)", "1b. Mapa bez tratě (KMZ)", "2. Dva snímky z Livelox", "3. Fotka papírové mapy"]
    assert [html.index(h) for h in heads] == sorted(html.index(h) for h in heads)
    one = (io.BytesIO(_one_run_zip("pohora")), "x.zip")
    r = client.post(f"/races/{e}/files", data=dict(csrf_token=csrf(client), fit=one),
                    content_type="multipart/form-data", follow_redirects=True)
    assert "Běh je nahraný a spárovaný s tímhle závodem." in r.get_data(as_text=True)
    assert con.execute("SELECT activity_id FROM entries WHERE id = ?", (e,)).fetchone()[0] is not None
    # a whole export there is refused with a pointer to the upload page
    two = io.BytesIO()
    with zipfile.ZipFile(two, "w") as z:
        for folder in ("pohora", "azymut-e4"):
            with open(inputs(folder)[2], "rb") as f:
                z.writestr(f"{folder}.fit", f.read())
    r = client.post(f"/races/{e}/files", data=dict(csrf_token=csrf(client), fit=(io.BytesIO(two.getvalue()), "y.zip")),
                    content_type="multipart/form-data", follow_redirects=True)
    assert "Celý export z Garminu nahraj v Nahrát běhy." in r.get_data(as_text=True)
