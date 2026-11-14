"""Issue 12: the light / dark mode and the language are kept with the account, not only in the browser. The app on
one's own computer starts on another port each time (desktop/app.py) and the browser keeps localStorage per address
with the port, so a mode kept only there was gone after a restart."""
import pytest
from conftest import FakeOris, csrf, register

from webapp import club


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setenv("OB_LOCAL", "1")
    monkeypatch.setattr(club, "ENABLED", False)
    from webapp import create_app
    app = create_app(str(tmp_path / "instance"))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    app.config["OB"].osm = False
    return app


def _theme(client, mode):
    return client.post("/rezim", json={"rezim": mode}, headers={"X-CSRF-Token": csrf(client)})


def _html_tag(client, path="/o-aplikaci"):
    html = client.get(path).get_data(as_text=True)
    return html[html.index("<html"):html.index(">", html.index("<html")) + 1]


def test_mode_is_kept_for_the_next_start(local):
    first = local.test_client()
    assert "data-rezim" not in _html_tag(first)          # never chosen: the browser copy decides (ob.js)
    assert _theme(first, "tmavy").status_code == 204
    # the next start of the app: another port, so a new browser storage and no cookie of this session
    again = local.test_client()
    tag = _html_tag(again)
    assert 'data-rezim="tmavy"' in tag and 'data-theme="tmavy"' in tag
    assert _theme(again, "svetly").status_code == 204
    assert 'data-theme="svetly"' in _html_tag(local.test_client())
    assert _theme(again, "").status_code == 204          # as the device: no data-theme, but known to be chosen
    tag = _html_tag(local.test_client())
    assert 'data-rezim=""' in tag and "data-theme" not in tag


def test_mode_switch_checks_its_input(local):
    c = local.test_client()
    assert _theme(c, "ruzovy").status_code == 400
    assert c.post("/rezim", json={"rezim": "tmavy"}).status_code == 400     # no CSRF token
    assert "data-rezim" not in _html_tag(c)


def test_page_tells_the_script_where_to_keep_the_mode(local):
    html = local.test_client().get("/o-aplikaci").get_data(as_text=True)
    assert 'rezim: "/rezim"' in html
    head = html[:html.index("</head>")]
    # the copy in the browser is used only when the account has no mode yet
    assert 'hasAttribute("data-rezim")' in head and 'localStorage.getItem("ob-rezim")' in head


def test_accounts_on_the_server_keep_their_own_mode(app):
    a, b = app.test_client(), app.test_client()
    register(a, "BFM0903")
    assert _theme(a, "tmavy").status_code == 204
    assert 'data-theme="tmavy"' in _html_tag(a, "/")
    assert "data-theme" not in _html_tag(b, "/login")    # nobody signed in: nothing from the server
    assert _theme(b, "tmavy").status_code == 204          # accepted, kept only in that browser
    assert "data-theme" not in _html_tag(b, "/login")


def test_language_is_kept_with_the_account(local):
    first = local.test_client()
    first.get("/language/en?next=/o-aplikaci")
    again = local.test_client()                          # no ob_lang cookie
    assert 'lang="en"' in _html_tag(again)
    assert 'lang="cs"' in _html_tag(again, "/o-aplikaci?lang=cs")   # the address and the cookie still come first
