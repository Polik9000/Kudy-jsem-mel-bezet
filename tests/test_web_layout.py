"""The app layout, the /ob mount, security headers and optional external club links."""
import datetime as dt
import importlib
import os
import re

from conftest import FakeOris, clear_jobs, csrf, post, register
from races import ROOT

from webapp import club
from webapp import db as dbm
from webapp.services import runner, sync_oris


def read(*path):
    with open(os.path.join(ROOT, *path), "rb") as f:
        return f.read().replace(b"\r\n", b"\n")


def test_app_base_stylesheet_and_brand_assets_exist():
    assert read("webapp", "static", "base.css")
    assert read("webapp", "static", "ob-logo.svg")
    assert read("webapp", "static", "app-icons.svg")


def test_app_stylesheet_uses_shared_design_tokens():
    css = read("webapp", "static", "ob.css").decode("utf-8")
    for name in ("--brand:", "--accent:", "--support:", "--vtisk:", "--ink:", "--bg-page:"):
        assert name not in css, f"ob.css must not redefine {name}"
    for name in ("var(--vtisk)", "var(--support)", "var(--accent)", "var(--brand"):
        assert name in css


def test_page_has_the_app_layout_and_headers(client):
    r = client.get("/login")
    html = r.get_data(as_text=True)
    for piece in ('class="sitehead"', '<header class="site">', 'class="flagstrip"', 'class="sidemenu"',
                  '<details class="menu">', 'class="rezim-prepinac"', '<footer class="site">', 'id="i-kontrola"',
                  'localStorage.getItem("ob-rezim")', "base.css", "ob.css",
                  "ob-logo.svg", "<title>Přihlášení · Kudy jsem měl běžet</title>"):
        assert piece in html, piece
    assert html.index("base.css") < html.index("ob.css") < html.index("les.css")
    assert "skobfm.vzdyonline.cz" not in html
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "http" not in csp
    assert r.headers["X-Frame-Options"] == "DENY"
    # nothing is loaded from another origin
    assert 'src="http' not in html and "url(http" not in html and '<link rel="stylesheet" href="http' not in html


def test_static_files_are_served(client):
    for name in ("base.css", "ob.css", "les.css", "ob.js", "map.js", "ob-logo.svg", "app-icons.svg", "vendor/leaflet/leaflet.js"):
        assert client.get("/ob-static/" + name).status_code == 200, name
    for name in ("skob.css", "skob-logo.svg", "skob-ikony-sprite.svg", "kudy.css"):
        assert client.get("/ob-static/" + name).status_code == 404, name


def test_static_files_are_kept_by_the_browser(client):
    """Style sheets and scripts carry a hash of their content in the address and may be kept for a year;
    without the hash the browser has to ask every time. They come without a cookie."""
    html = client.get("/login").get_data(as_text=True)
    url = re.search(r'href="(/ob-static/ob\.css\?v=[0-9a-f]{10})"', html).group(1)
    r = client.get(url)
    assert r.status_code == 200 and "immutable" in r.headers["Cache-Control"] and "Set-Cookie" not in r.headers
    assert "immutable" not in client.get("/ob-static/ob.css").headers.get("Cache-Control", "")


def test_only_pages_about_jobs_load_themselves_again(client, user):
    """A page that reloads when a background job finishes throws away a chosen file or a half-filled form,
    so only the pages that show the state of the jobs ask for it (<body data-obnovit>, static/ob.js)."""
    for page in ("/", "/jobs"):
        assert "<body data-obnovit>" in client.get(page).get_data(as_text=True), page
    for page in ("/upload", "/profile", "/races/new", "/model"):
        assert "data-obnovit" not in client.get(page).get_data(as_text=True), page


def test_club_links(monkeypatch):
    monkeypatch.setattr(club, "BASE", "https://example.org")
    monkeypatch.setattr(club, "ENABLED", True)
    assert club.event(9827) == "https://example.org/zavod/oris-9827"
    assert club.member(45118) == "https://example.org/clen/45118"
    assert club.archive(45118, 2026) == "https://example.org/archiv?clen=45118&season=2026"
    assert club.event(None) is None and club.member(None) is None


def test_pages_link_to_the_club_site_and_back(app, client, user, monkeypatch):
    monkeypatch.setattr(club, "BASE", "https://skobfm.vzdyonline.cz")
    monkeypatch.setattr(club, "ENABLED", True)
    con = dbm.connect(app.config["OB"].db_path)
    sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    html = client.get("/").get_data(as_text=True)
    assert "https://skobfm.vzdyonline.cz/zavod/oris-9827" in html          # race -> club page of the race
    assert "https://skobfm.vzdyonline.cz/archiv?clen=45118" in html        # menu: my results
    assert "https://skobfm.vzdyonline.cz/clen/45118" in html               # menu: my card
    # the club site links here by ORIS ids
    r = client.get("/zavod/oris-9827")
    assert r.status_code == 302
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Mistrovství oblasti na dlouhé trati" in page
    assert "https://oresults.eu/events/2924" in page and "https://oris.ceskyorientak.cz/Vysledky?id=9827" in page
    r = client.get("/zavod/oris-123456")
    assert r.status_code == 404 and "nemáš" in r.get_data(as_text=True)
    assert client.get("/clen/45118").status_code == 302
    r = client.get("/clen/999")
    assert r.status_code == 403 and "jen ten, komu patří" in r.get_data(as_text=True)


def test_race_list_filters(app, client, user):
    con = dbm.connect(app.config["OB"].db_path)
    sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    html = client.get("/").get_data(as_text=True)
    assert html.count("chybí aktivita") == 2 and 'name="sezona"' in html
    only = client.get("/?sezona=2025").get_data(as_text=True)
    assert "na krátké trati" in only and "na dlouhé trati" not in only
    assert "Tomuhle filtru žádný závod neodpovídá" in client.get("/?jen=hotovo").get_data(as_text=True)


def test_app_is_mounted_under_ob(tmp_path, monkeypatch):
    monkeypatch.setenv("OB_INSTANCE", str(tmp_path / "instance"))
    monkeypatch.delenv("OB_URL_PREFIX", raising=False)
    import webapp.wsgi
    wsgi = importlib.reload(webapp.wsgi)
    c = wsgi.app.test_client()
    r = c.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/ob/")
    r = c.get("/ob/")
    assert r.status_code == 302 and "/ob/login" in r.headers["Location"]
    html = c.get("/ob/login").get_data(as_text=True)
    assert 'href="/ob/ob-static/base.css?v=' in html and 'href="/ob/register"' in html
    assert c.get("/login").status_code == 302          # outside the prefix: sent to /ob/


def test_old_database_gets_the_new_columns(tmp_path):
    """A database made by the first version of the app (no events.links ...) is upgraded on start."""
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE events (id INTEGER PRIMARY KEY, oris_id INTEGER UNIQUE, name TEXT NOT NULL,"
                      " date TEXT NOT NULL, lat REAL, lon REAL, maponly_file TEXT);"
                      "INSERT INTO events (name, date) VALUES ('starý závod', '2025-01-01');")
    con.commit()
    con.close()
    dbm.init(path)
    dbm.init(path)   # twice is fine
    con = dbm.connect(path)
    row = con.execute("SELECT * FROM events").fetchone()
    assert row["name"] == "starý závod" and row["osm_mode"] == "forbid" and row["links"] is None
    assert row["hatch_mode"] == "forbid"
    assert con.execute("SELECT COUNT(*) FROM barriers").fetchone()[0] == 0


def test_osm_fences_are_used_only_when_switched_on(app):
    import json

    from oroute import osm
    from webapp.services import barriers
    conf = app.config["OB"]
    con = dbm.connect(conf.db_path)
    with open(os.path.join(ROOT, "tests", "fixtures", "osm", "petrvald_overpass.json"), encoding="utf-8") as f:
        barriers.save_osm(conf, 7, dict(osm.parse(json.load(f)), fetched="2026-10-06"))
    b = barriers.for_routing(con, conf, 7, "forbid")
    assert [l["kind"] for l in b["lines"]] == ["forbidden", "forbidden"] and len(b["crossings"]) == 3
    assert {l["kind"] for l in barriers.for_routing(con, conf, 7, "penalty")["lines"]} == {"hard"}
    assert barriers.for_routing(con, conf, 7, "off") is None
    assert len(barriers.for_map(con, conf, 7, "forbid")[1]["lines"]) == 2
    conf.osm_fences = True
    kinds = [l["kind"] for l in barriers.for_routing(con, conf, 7, "forbid")["lines"]]
    assert kinds.count("forbidden") == 2 and kinds.count("hard") == 46
    assert barriers.for_routing(con, conf, 8, "forbid") is None          # nothing fetched for that event


def test_club_prior_needs_three_other_runners_with_data(app):
    from webapp.services import personal
    con = dbm.connect(app.config["OB"].db_path)

    def runner(regno, forest, seconds):
        uid = con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES (?, 'x', ?)",
                          (regno, regno)).lastrowid
        model = dict(v_flat=3.4, up_k=3.4, factors={"path/road": 1.0, "forest (runnable)": forest, "marsh": 0.45},
                     notes=dict(terrain={"forest (runnable)": dict(seconds=seconds), "marsh": dict(seconds=20)}))
        con.execute("INSERT INTO speed_models (user_id, model, file) VALUES (?, ?, 'x')", (uid, dbm.dumps(model)))
        return uid
    me = runner("BFM0903", 0.9, 5000)
    runner("BFM0001", 0.6, 900)
    runner("BFM0002", 0.8, 900)
    assert personal.club_prior(con, me) == {}                    # two others are not a club yet
    runner("BFM0003", 0.7, 900)
    runner("BFM0004", 0.2, 30)                                   # too little data: not counted
    prior = personal.club_prior(con, me)
    forest = 0                                                   # terrain.FOREST
    assert list(prior) == [forest] and abs(prior[forest] - (0.6 * 0.8 * 0.7) ** (1 / 3)) < 1e-9
    assert not app.config["OB"].club_prior                       # off unless OB_CLUB_PRIOR=1


def test_forbidden_lines_are_shared_by_the_event(app, client, user):
    con = dbm.connect(app.config["OB"].db_path)
    sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    mine = con.execute("SELECT e.id, c.event_id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 9827").fetchone()
    token = csrf(client)
    url = f"/races/{mine['id']}/barriers"
    line = [[49.83, 18.37], [49.831, 18.372], [49.832, 18.371]]
    r = client.post(url, json=dict(kind="forbidden", line=line), headers={"X-CSRF-Token": token})
    assert r.status_code == 200 and r.get_json()["barriers"][0]["line"] == line
    assert client.post(url, json=dict(kind="nonsense", line=line), headers={"X-CSRF-Token": token}).status_code == 400
    assert client.post(url, json=dict(line=[[49.83, 18.37]]), headers={"X-CSRF-Token": token}).status_code == 400
    assert client.post(url, json=dict(line=line)).status_code == 400          # no CSRF token
    html = client.get(f"/races/{mine['id']}").get_data(as_text=True)
    assert "zakázaná" in html and "Železnice a dálnice" in html
    # a clubmate at the same event sees the line too; someone who did not run it cannot touch it
    post(client, "/logout")
    register(client, "BFM0001")
    other = con.execute("SELECT id FROM users WHERE username = 'BFM0001'").fetchone()["id"]
    cls = con.execute("INSERT INTO classes (event_id, name) VALUES (?, 'D21C')", (mine["event_id"],)).lastrowid
    theirs = con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (other, cls)).lastrowid
    con.commit()
    html = client.get(f"/races/{theirs}").get_data(as_text=True)
    assert "zakázaná" in html and "Tobiáš Otta" in html                    # ... and who drew it
    assert client.post(url, json=dict(line=line), headers={"X-CSRF-Token": csrf(client)}).status_code == 404
    # the line is shared on purpose, so only whoever drew it may take it away
    bid = con.execute("SELECT id FROM barriers").fetchone()["id"]
    assert f"/barriers/{bid}/delete" not in html
    assert post(client, f"/races/{theirs}/barriers/{bid}/delete").status_code == 403
    token = csrf(client)
    assert client.delete(f"/races/{theirs}/barriers/{bid}", headers={"X-CSRF-Token": token}).status_code == 403
    shown = client.post(f"/races/{theirs}/barriers", json=dict(line=line), headers={"X-CSRF-Token": token}).get_json()
    assert [(b["by"], b["mine"]) for b in shown["barriers"]] == [("Tobiáš Otta", False), ("Klára Kolegyně", True)]
    assert con.execute("SELECT COUNT(*) FROM barriers").fetchone()[0] == 2
    # the same for a refreshment point
    con.execute("INSERT INTO refreshments (event_id, lat, lon, created_by) VALUES (?, 49.83, 18.37, ?)",
                (mine["event_id"], user))
    con.commit()
    rid = con.execute("SELECT id FROM refreshments").fetchone()["id"]
    assert client.delete(f"/races/{theirs}/refreshments/{rid}", headers={"X-CSRF-Token": token}).status_code == 403
    assert "občerstvovačka 1: přidal Tobiáš Otta" in client.get(f"/races/{theirs}").get_data(as_text=True)
    # a line whose author's account is gone can be removed by anyone at the event (or nobody could)
    con.execute("UPDATE barriers SET created_by = NULL WHERE id = ?", (bid,))
    con.commit()
    r = post(client, f"/races/{theirs}/barriers/{bid}/delete")
    assert r.status_code == 302 and con.execute("SELECT COUNT(*) FROM barriers").fetchone()[0] == 1
    assert post(client, f"/races/{theirs}/settings", osm_mode="x").status_code == 400


def test_settings_of_one_runner_do_not_recalculate_the_others(app, client, user):
    """Railways from OpenStreetMap and hatched areas: each runner sets them for their own analysis. The value of
    the race is for those who did not choose; only whoever uploaded the map without course changes it."""
    con = dbm.connect(app.config["OB"].db_path)
    sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    mine = con.execute("SELECT e.id, c.event_id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
                       " ON ev.id = c.event_id WHERE ev.oris_id = 9827").fetchone()
    event = mine["event_id"]
    post(client, "/logout")
    ids = {"BFM0903": mine["id"]}
    for regno in ("BFM0001", "BFM0002"):                        # two clubmates in another class of the race
        register(client, regno)
        post(client, "/logout")
        uid = con.execute("SELECT id FROM users WHERE username = ?", (regno,)).fetchone()["id"]
        cls = con.execute("INSERT INTO classes (event_id, name) VALUES (?, ?)", (event, "D21" + regno[-1])).lastrowid
        ids[regno] = con.execute("INSERT INTO entries (user_id, class_id) VALUES (?, ?)", (uid, cls)).lastrowid
        con.commit()
    for entry in ids.values():                                  # all three have best routes
        con.execute("INSERT INTO analyses (entry_id, has_routes) VALUES (?, 1)", (entry,))
    con.execute("UPDATE events SET maponly_file = 'maps/x.kmz', maponly_by = ? WHERE id = ?", (user, event))
    con.commit()
    clear_jobs(app)
    queued = lambda: sorted(r["entry_id"] for r in con.execute("SELECT entry_id FROM jobs WHERE status = 'queued'"))
    mode = lambda entry: runner.entry_info(con, entry)["osm_mode"]

    def login(regno):
        post(client, "/logout")
        assert post(client, "/login", username=regno, password="tajneheslo").status_code == 302

    # Klára switches the railways off for herself: only her routes are found again
    login("BFM0001")
    page = f"/races/{ids['BFM0001']}"
    assert post(client, page + "/settings", osm_mode="off", hatch_mode="").status_code == 302
    assert queued() == [ids["BFM0001"]]
    assert [mode(ids[r]) for r in ("BFM0903", "BFM0001", "BFM0002")] == ["forbid", "off", "forbid"]
    assert con.execute("SELECT osm_mode FROM events WHERE id = ?", (event,)).fetchone()[0] == "forbid"
    html = client.get(page).get_data(as_text=True)
    assert 'name="osm_mode" form="nastaveni-zavodu" value="off" checked' in html
    assert 'name="hatch_mode" form="nastaveni-zavodu" value="" checked' in html
    assert 'name="scope"' not in html and "Tobiáš Otta" in html             # who may change the value of the race
    # the value of the race is not hers to change
    assert post(client, page + "/settings", scope="event", osm_mode="penalty").status_code == 403
    assert post(client, page + "/settings", scope="event", osm_mode="").status_code == 400
    # choosing what already holds for her queues nothing; neither does saving the same again
    clear_jobs(app)
    assert post(client, page + "/settings", osm_mode="off", hatch_mode="forbid").status_code == 302
    assert queued() == []

    # Tobiáš uploaded the map without course: he changes the value of the race, and the routes are found again
    # for those who follow it (himself and Jan), not for Klára with her own setting
    login("BFM0903")
    page = f"/races/{ids['BFM0903']}"
    assert 'name="scope" value="event"' in client.get(page).get_data(as_text=True)
    assert post(client, page + "/settings", scope="event", osm_mode="penalty", hatch_mode="forbid").status_code == 302
    assert queued() == sorted([ids["BFM0903"], ids["BFM0002"]])
    assert [mode(ids[r]) for r in ("BFM0903", "BFM0001", "BFM0002")] == ["penalty", "off", "penalty"]
    # Klára goes back to "as the race": now she follows it again
    clear_jobs(app)
    login("BFM0001")
    assert post(client, f"/races/{ids['BFM0001']}/settings", osm_mode="").status_code == 302
    assert queued() == [ids["BFM0001"]] and mode(ids["BFM0001"]) == "penalty"


def test_old_database_gets_the_runners_own_settings(tmp_path):
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE entries (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, class_id INTEGER NOT NULL,"
                      " official_time_s INTEGER, start_local TEXT, result_place TEXT, splits TEXT, activity_id INTEGER,"
                      " match_confidence TEXT, match_note TEXT, UNIQUE (user_id, class_id));"
                      "INSERT INTO entries (user_id, class_id) VALUES (1, 1);")
    con.commit()
    dbm.init(path)
    assert tuple(con.execute("SELECT own_osm_mode, own_hatch_mode FROM entries").fetchone()) == (None, None)


def test_hatched_areas_are_kept_per_class_and_switched_per_event(app, client, user, tmp_path):
    """What oroute.hatch read from the map with the course: kept per class until that map is replaced,
    given to the routing, and switched off for the whole event in the settings."""
    from webapp.services import barriers
    conf = app.config["OB"]
    con = dbm.connect(conf.db_path)
    sync_oris.sync_user(con, conf, user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    mine = con.execute("SELECT e.id, e.class_id, c.event_id FROM entries e JOIN classes c ON c.id = e.class_id"
                       " JOIN events ev ON ev.id = c.event_id WHERE ev.oris_id = 9827").fetchone()
    cid, event = mine["class_id"], mine["event_id"]
    course = tmp_path / "course.kmz"
    course.write_bytes(b"first upload")
    ring = [[49.83, 18.37], [49.831, 18.372], [49.832, 18.371]]
    assert barriers.hatch_data(conf, cid) is None and barriers.hatch_areas(conf, cid, "forbid") == []
    barriers.save_hatch(conf, cid, str(course), [ring], "2026-10-07")
    assert barriers.hatch_areas(conf, cid, "forbid") == [ring] and barriers.hatch_areas(conf, cid, "off") == []
    assert barriers.hatch_data(conf, cid, str(course))["areas"] == [ring]
    assert barriers.for_routing(con, conf, event, "off", [ring]) == dict(lines=[], crossings=[], areas=[ring])
    assert barriers.for_routing(con, conf, event, "off", []) is None
    # the map with the course was uploaded again: the old reading no longer counts for the analysis
    course.write_bytes(b"second upload, another size")
    assert barriers.hatch_data(conf, cid, str(course)) is None and barriers.hatch_data(conf, cid) is not None
    # the settings of the race
    html = client.get(f"/races/{mine['id']}").get_data(as_text=True)
    assert "Zakázané prostory z mapy" in html and "zakázaných prostorů 1." in html
    url = f"/races/{mine['id']}/settings"
    assert post(client, url, hatch_mode="off").status_code == 302
    row = con.execute("SELECT own_hatch_mode, own_osm_mode FROM entries WHERE id = ?", (mine["id"],)).fetchone()
    assert (row["own_hatch_mode"], row["own_osm_mode"]) == ("off", None)
    assert post(client, url, hatch_mode="penalty").status_code == 400      # an area cannot be "only slow"
    assert post(client, url).status_code == 400                             # nothing to set


def test_only_lesni_klid_theme_is_loaded(client):
    """The app has one supported appearance; its own base and app styles load before Lesní klid."""
    html = client.get("/login").get_data(as_text=True)
    assert html.index("/base.css") < html.index("/ob.css") < html.index("/les.css")
    assert "/kudy.css" not in html and "/skob.css" not in html
    assert 'content="#10251E"' in html and "Kudy jsem měl běžet" in html
    assert client.get("/ob-static/les.css").status_code == 200
    for name in ("manrope-latin-wght-normal.woff2", "jetbrains-mono-latin-ext-wght-normal.woff2", "OFL-Manrope.txt"):
        assert client.get("/ob-static/fonts/" + name).status_code == 200, name
    assert 'class="bottomnav"' not in html


def test_about_page_and_bottom_navigation(client, user):
    html = client.get("/o-aplikaci").get_data(as_text=True)
    assert "Omezení modelu" in html and "Mřížka 2,7" in html and 'class="bottomnav"' in html
