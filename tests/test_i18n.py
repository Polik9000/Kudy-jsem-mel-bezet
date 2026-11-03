"""The English interface: every text has an English counterpart, the language switch, the pages and the notes of the
analysis in English."""
import os
import re
import sys

from conftest import post, register

from webapp import db as dbm
from webapp import i18n, lang_en, texts
from webapp.services import jobs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import i18n_extract  # noqa: E402


def test_every_text_has_an_english_counterpart():
    no_page, no_js, extra, extra_js = i18n_extract.missing()
    assert not no_page, "add to webapp/lang_en.py EN: " + "; ".join(sorted(no_page))
    assert not no_js, "add to webapp/lang_en.py EN_JS: " + "; ".join(sorted(no_js))
    assert not extra and not extra_js, "no longer used: " + "; ".join(extra + extra_js)


def test_english_texts_keep_the_places_of_the_czech_ones():
    place = re.compile(r"%\(\w+\)[-+ #0-9.]*[a-z]")
    for catalog in (lang_en.EN, lang_en.EN_JS):
        for cs, en in catalog.items():
            assert sorted(place.findall(cs)) == sorted(place.findall(en)), cs
            assert en.strip(), cs


def test_czech_is_the_default_and_english_is_asked_for(client):
    assert i18n.lang() == "cs"
    html = client.get("/login").get_data(as_text=True)
    assert '<html lang="cs"' in html and "Přihlášení" in html
    en = client.get("/login?lang=en").get_data(as_text=True)
    assert '<html lang="en"' in en and "Log in" in en and "Přihlášení" not in en


def test_the_language_switch_remembers_the_choice(client):
    r = client.get("/language/en?next=/login")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert "ob_lang=en" in r.headers["Set-Cookie"]
    assert "Where I Should Have Run" in client.get("/login").get_data(as_text=True)
    client.get("/language/cs")
    assert "Kudy jsem měl běžet" in client.get("/login").get_data(as_text=True)
    assert client.get("/language/de").status_code == 404
    # only addresses of this site
    r = client.get("/language/en?next=//evil.example/")
    assert "evil.example" not in r.headers["Location"]


def test_the_menu_offers_both_languages(client):
    html = client.get("/login").get_data(as_text=True)
    assert 'lang="cs"' in html and ">CS<" in html and ">EN<" in html


CZECH_LETTERS = re.compile(r"[ěščřžťďňůĚŠČŘŽŤĎŇŮ]")
ALLOWED = ("ČÚZK", "Frýdek-Místek", "Tobiáš", "ob-tracker")


def _text_of(html):
    """The words a reader sees: no scripts, tags or names of the club and the author."""
    html = re.sub(r"<script.*?</script>|<svg.*?</svg>|<[^>]+>", " ", html, flags=re.S)
    for name in ALLOWED:
        html = html.replace(name, "")
    return html


def test_help_and_about_pages_in_english(client):
    client.get("/language/en")
    for url, words in (("/jak-na-to", ("Run from the watch (Garmin)", "Notes on a leg")),
                       ("/o-aplikaci", ("How it works", "Limits of the model"))):
        html = client.get(url).get_data(as_text=True)
        for w in words:
            assert w in html, (url, w)
        assert not CZECH_LETTERS.search(_text_of(html)), (url, CZECH_LETTERS.search(_text_of(html)))


def test_no_czech_is_left_on_the_pages_of_a_runner(app, client):
    client.get("/language/en")
    register(client)
    for url in ("/", "/jobs", "/upload", "/model", "/profile", "/races/new", "/races/oris", "/login", "/register",
                "/forgot"):
        r = client.get(url, follow_redirects=True)
        assert r.status_code == 200, url
        assert not CZECH_LETTERS.search(_text_of(r.get_data(as_text=True))), url


def test_pages_of_a_runner_in_english(app, client):
    client.get("/language/en")
    register(client)
    html = client.get("/").get_data(as_text=True)
    assert "Races" in html and "Load races from ORIS" in html and "Přehled" not in html
    assert "Background jobs" in client.get("/jobs").get_data(as_text=True)
    assert "Speed model" in html
    assert "Add a race by hand" in client.get("/races/new").get_data(as_text=True)


def test_flashed_messages_follow_the_language(client):
    client.get("/language/en")
    r = post(client, "/login", username="nobody", password="x")
    assert "Wrong name or password." in r.get_data(as_text=True)


def test_a_job_keeps_the_language_of_the_page_that_started_it(app, client):
    register(client)
    client.get("/language/en")
    client.post("/jobs/stop-all", data={}, follow_redirects=False)
    con = dbm.connect(app.config["OB"].db_path)
    first = con.execute("SELECT lang FROM jobs ORDER BY id").fetchone()["lang"]
    assert first == "cs"          # the registration was in Czech
    with i18n.use("en"):
        jid = jobs.enqueue(con, "refit_model", user_id=1)
    assert con.execute("SELECT lang FROM jobs WHERE id = ?", (jid,)).fetchone()["lang"] == "en"


def test_the_notes_of_the_analysis_in_english():
    with i18n.use("en"):
        m = texts.mistake(dict(type="overshoot", miss=18.4, over=95.0, back=71.0, at=None))
        assert m["label"] == "overshooting" and "18 m" in m["text"]
        assert texts.analysis_error("no_gps").startswith("The recording has no GPS track")
        assert texts.gps_trouble(dict(far_m=45)).startswith("The GPS is probably misbehaving")
        assert texts.confidence()["high"][0] == "certain"
        assert texts.photo_problem("same") == "You marked the same control twice."
        assert "Place the photo by hand" in texts.photo_failed("too few points: 3 circles in the picture, 9 controls", {})
        feat = texts.feature(dict(kind="junction", lat=1, lon=2, point=True, dist=85.0, az=215.0, back_az=35.0,
                                  dh=0.0, via=None))
        assert feat["where"] == "path junction 85 m from the control on bearing 215°"
        assert feat["back"] == "from the path junction, 85 m on bearing 35°, level"
    assert texts.mistake(dict(type="overshoot", miss=18.4, over=95.0, back=71.0, at=None))["label"] == "přeběhnutí"


def test_the_advice_of_the_lost_page_in_english():
    a = dict(far=False, pick=0, r=50, no_runner=False, relocate_first=False, back=False,
             helpers=[dict(kind="path", sure=True, dist=40.0, az=90.0, seen=[["stream", 30.0]], inside=False,
                           link=dict(type="near", dist=60.0, az=0.0, az_off=10.0, along=100.0, side="right"))],
             attack=None, desc=None)
    with i18n.use("en"):
        out = texts.lost_advice(a)
    assert out[0] == ("You should have gone east to the path (about 40 m, bearing 90°, after 30 m you would have crossed "
                      "the stream).")
    assert out[1].startswith("Then along the path to the north for about 100 m")


def test_plural_and_numbers():
    with i18n.use("en"):
        assert i18n.plural(1, "a", "b", "c") == "a" and i18n.plural(3, "a", "b", "c") == "c"
        assert i18n.num(2.75, 1) in ("2.8", "2.7") and i18n._n(2, "x %(n)s", "y %(n)s", "z %(n)s") == "z 2"
    assert i18n.plural(3, "a", "b", "c") == "b" and i18n.num(2.5, 1) == "2,5"
