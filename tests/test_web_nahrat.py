"""Nahrát (prompt 10): the run from three sources that switch in place and the maps of one race on one page. The old
addresses of Garmin Connect and of the watch send there, the last source is kept with the account, the link
„Doplnit“ opens Nahrát with its race picked and the maps sent from there come back to Nahrát."""
import io

from conftest import csrf
from races import inputs
from test_watch import local  # noqa: F401  (the app on one's own computer)
from test_web_photo import entry


def test_old_addresses_send_to_nahrat(local):  # noqa: F811
    c = local.test_client()
    c.get("/")
    r = c.get("/upload/garmin?dni=14")
    assert r.status_code == 302 and r.headers["Location"].endswith("/upload?zdroj=garmin&dni=14#zdroj=garmin")
    r = c.get("/upload/hodinky")
    assert r.status_code == 302 and r.headers["Location"].endswith("/upload?zdroj=hodinky#zdroj=hodinky")


def test_three_sources_and_the_last_one_is_kept(local):  # noqa: F811
    c = local.test_client()
    c.get("/")
    html = c.get("/upload").get_data(as_text=True)
    for src in ("pocitac", "garmin", "hodinky"):
        assert f'data-zdroj="{src}"' in html and f'data-zdroj-panel="{src}"' in html
    assert 'data-zdroj="pocitac"\n       aria-pressed="true"' in html          # nothing chosen yet: the files
    # an old link to the watch page: Nahrát opens on the watch, with its panel already in the page
    html = c.get("/upload?zdroj=hodinky").get_data(as_text=True)
    assert 'data-zdroj-panel="hodinky" data-nacteno' in html and "Nebo složka se soubory .fit" in html
    html = c.get("/upload").get_data(as_text=True)                            # ... and next time too
    assert 'data-zdroj-panel="hodinky" data-nacteno' in html and 'data-zdroj-panel="pocitac" hidden' in html
    # the switch of the page keeps the choice without loading the page
    assert c.post("/upload/zdroj", json=dict(zdroj="pocitac"), headers={"X-CSRF-Token": csrf(c, "/")}).status_code == 204
    assert 'data-zdroj-panel="pocitac" hidden' not in c.get("/upload").get_data(as_text=True)
    assert c.post("/upload/zdroj", json=dict(zdroj="usb"), headers={"X-CSRF-Token": csrf(c, "/")}).status_code == 400
    # the panels come one by one, for the script to put in place
    panel = c.get("/upload/panel/hodinky").get_data(as_text=True)
    assert "<html" not in panel and 'action="/upload/hodinky"' not in panel and "Zobrazit běhy" in panel
    assert c.get("/upload/panel/pocitac").status_code == 404


def test_only_files_on_the_server(app, client, user):
    html = client.get("/upload").get_data(as_text=True)
    assert 'data-zdroje' not in html and 'name="files"' in html
    assert client.post("/upload/zdroj", json=dict(zdroj="garmin"),
                       headers={"X-CSRF-Token": csrf(client, "/")}).status_code == 400


def test_doplnit_opens_nahrat_with_the_race_and_the_maps_come_back(app, client, user):
    con, mine = entry(app, client, user, run=False)
    race = client.get(f"/races/{mine}").get_data(as_text=True)
    assert f'href="/upload?zavod={mine}#mapa-zavodu"' in race           # „Doplnit“: the race lacks its maps
    assert f'/upload?zavod={mine}#mapa-zavodu' in client.get("/").get_data(as_text=True)
    html = client.get(f"/upload?zavod={mine}").get_data(as_text=True)
    assert f'<option value="{mine}" selected' in html
    assert f'action="/races/{mine}/files"' in html and 'name="zpet" value="nahrat"' in html
    for name in ("course", "maponly", "screen_course", "screen_maponly", "course_photo"):
        assert f'name="{name}"' in html                                  # the same fields as on the race page
    assert "Nemám KMZ z Livelox" in html
    # the map without the course from Nahrát: saved for the race, and back on Nahrát with the race still picked
    with open(inputs("pohora")[1], "rb") as f:
        r = client.post(f"/races/{mine}/files", data=dict(csrf_token=csrf(client), zpet="nahrat",
                                                          maponly=(io.BytesIO(f.read()), "mapa.kmz")),
                        content_type="multipart/form-data")
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/upload?zavod={mine}#mapa-zavodu")
    assert con.execute("SELECT ev.maponly_file FROM entries e JOIN classes c ON c.id = e.class_id"
                       " JOIN events ev ON ev.id = c.event_id WHERE e.id = ?", (mine,)).fetchone()[0]


def test_nahrat_in_english(app, client, user):
    client.get("/language/en")
    html = client.get("/upload").get_data(as_text=True)
    assert "Upload a run or a map" in html and "1. Run from the watch" in html
