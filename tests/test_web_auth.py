"""Accounts: registration, login, CSRF, pages only for logged-in users."""
from conftest import csrf, invite, post, register

from webapp import oris


def test_pages_need_login(client):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_register_login_logout(client):
    r = register(client, "bfm 0903", "dlouheheslo")
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    html = client.get("/").get_data(as_text=True)
    assert "Vítej, Tobiáš Otta" in html          # the name comes from ORIS
    assert post(client, "/logout").status_code == 302
    assert client.get("/").status_code == 302
    r = post(client, "/login", username="BFM0903", password="spatne")
    assert r.status_code == 200 and "Špatné jméno nebo heslo" in r.get_data(as_text=True)
    r = post(client, "/login", username="bfm0903", password="dlouheheslo")
    assert r.status_code == 302
    assert client.get("/").status_code == 200


def test_login_outlives_the_browser_window(client):
    register(client, "BFM0903", "dlouheheslo")
    post(client, "/logout")
    r = post(client, "/login", username="BFM0903", password="dlouheheslo")
    cookie = next(c for c in r.headers.getlist("Set-Cookie") if c.startswith("ob_session="))
    assert "Expires=" in cookie
    # the pages after it do not send the cookie again (once a day is enough to keep the login alive)
    client.get("/")
    assert not client.get("/").headers.getlist("Set-Cookie")


def test_account_takes_name_and_id_from_oris_and_queues_the_sync(app, client):
    from webapp import db as dbm
    register(client)
    con = dbm.connect(app.config["OB"].db_path)
    row = con.execute("SELECT * FROM users").fetchone()
    assert (row["username"], row["oris_regno"], row["oris_user_id"], row["name"]) == \
        ("BFM0903", "BFM0903", 45118, "Tobiáš Otta")
    assert [j["kind"] for j in con.execute("SELECT kind FROM jobs")] == ["sync_oris"]


def test_account_is_made_even_when_oris_is_down(app, client):
    class Down:
        def user(self, regno):
            raise oris.OrisError("ORIS getUser: timed out")
    app.config["OB"].oris_client = Down()
    assert register(client, "BFM0001", "dlouheheslo").status_code == 302
    assert "ORIS teď neodpovídá" in client.get("/").get_data(as_text=True)


def test_register_checks(client):
    def msg(regno, password="dlouheheslo", password2="dlouheheslo"):
        return post(client, "/register", oris_regno=regno, password=password, password2=password2,
                    code=invite(client, regno)).get_data(as_text=True)
    assert "aspoň 8 znaků" in msg("BFM0903", "kratke", "kratke")
    assert "neshodují" in msg("BFM0903", "dlouheheslo", "jineheslo1")
    assert "tří písmen" in msg("bob")
    assert "XXX0000 v ORIS není" in msg("XXX0000")
    register(client, "BFM0903", "dlouheheslo")
    post(client, "/logout")
    assert "už existuje" in msg("bfm0903")


def test_register_needs_the_code_of_the_number(app, client):
    """Registration numbers are public: without the administrator's code of that very number no account."""
    from webapp import db as dbm
    con = dbm.connect(app.config["OB"].db_path)
    count = lambda: con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    for code in ("", "AAAA-AAAA", invite(client, "BFM0001")):   # none, made up, somebody else's
        r = register(client, "BFM0903", "dlouheheslo", code=code)
        assert r.status_code == 200 and "Kód k tomuhle registračnímu číslu nesedí" in r.get_data(as_text=True)
    assert count() == 0
    # a taken number answers the same without the code: nobody learns who has an account
    register(client, "BFM0903", "dlouheheslo")
    post(client, "/logout")
    html = register(client, "BFM0903", "dlouheheslo", code="AAAA-AAAA").get_data(as_text=True)
    assert "nesedí" in html and "už existuje" not in html
    # the code as people type it: small letters, no dash, spaces around
    code = invite(client, "BFM0001")
    assert register(client, "bfm 0001", "dlouheheslo", code=f" {code.replace('-', '').lower()} ").status_code == 302
    assert count() == 2


def test_register_link_fills_the_form_in(client):
    html = client.get("/register?regno=BFM0001&kod=ABCD-2345").get_data(as_text=True)
    assert 'value="BFM0001"' in html and 'value="ABCD-2345"' in html


def test_post_without_csrf_is_refused(client):
    assert client.post("/login", data=dict(username="x", password="y")).status_code == 400
    csrf(client)
    assert client.post("/login", data=dict(username="x", password="y", csrf_token="wrong")).status_code == 400


def test_password_is_stored_hashed(app, client, user):
    from webapp import db as dbm
    con = dbm.connect(app.config["OB"].db_path)
    row = con.execute("SELECT * FROM users WHERE id = ?", (user,)).fetchone()
    assert row["username"] == "BFM0903" and "tajneheslo" not in row["password_hash"]


def test_profile_cannot_change_the_registration_number(app, client, user):
    """Used to be possible: the account then held the races of both runners, logged in with either number,
    and the owner of the second number could not register."""
    from webapp import db as dbm
    con = dbm.connect(app.config["OB"].db_path)
    r = post(client, "/profile", oris_regno="BFM0001", name="Tobiáš")
    assert r.status_code == 302
    row = con.execute("SELECT * FROM users WHERE id = ?", (user,)).fetchone()
    assert (row["username"], row["oris_regno"], row["name"]) == ("BFM0903", "BFM0903", "Tobiáš")
    assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0     # no races of BFM0001 are loaded
    html = client.get("/profile").get_data(as_text=True)
    assert 'name="oris_regno"' not in html and "BFM0903" in html and 'value="Tobiáš"' in html
    # the other number stays free for its owner, and does not log in to this account
    post(client, "/logout")
    assert post(client, "/login", username="BFM0001", password="tajneheslo").status_code == 200
    assert register(client, "BFM0001").status_code == 302


def test_login_does_not_redirect_elsewhere(client, user):
    post(client, "/logout")
    r = client.post("/login", data=dict(username="BFM0903", password="tajneheslo", csrf_token=csrf(client),
                                        next="//evil.example/"))
    assert r.status_code == 302 and "evil" not in r.headers["Location"]


def test_login_by_registration_number_finds_the_account_the_password_belongs_to(app, client):
    """A database from before "one account per number": two accounts of one runner share a registration
    number, and either can log in with the number."""
    from werkzeug.security import generate_password_hash

    from webapp import db as dbm
    con = dbm.connect(app.config["OB"].db_path)
    con.execute("DROP INDEX users_regno")
    for username, password in (("tobias", "prvni-heslo-1"), ("tobiasotta", "druhe-heslo-2")):
        con.execute("INSERT INTO users (username, password_hash, oris_regno) VALUES (?, ?, 'BFM0903')",
                    (username, generate_password_hash(password)))
    con.commit()

    def who(name, password):
        r = post(client, "/login", username=name, password=password)
        if r.status_code != 302:
            return None
        with client.session_transaction() as s:
            uid = s["user_id"]
        post(client, "/logout")
        return con.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()[0]
    assert who("BFM0903", "druhe-heslo-2") == "tobiasotta"       # used to fail: the number meant the older account
    assert who("bfm 0903", "prvni-heslo-1") == "tobias"
    assert who("tobiasotta", "druhe-heslo-2") == "tobiasotta" and who("Tobias", "prvni-heslo-1") == "tobias"
    assert who("BFM0903", "spatne-heslo") is None and who("tobias", "druhe-heslo-2") is None


def test_password_change(client):
    register(client, "BFM0903", "dlouheheslo")

    def change(**form):
        return client.post("/password", data=dict(form, csrf_token=csrf(client)),
                           follow_redirects=True).get_data(as_text=True)
    assert "Současné heslo nesedí" in change(current="jine", password="noveheslo1", password2="noveheslo1")
    assert "aspoň 8 znaků" in change(current="dlouheheslo", password="kratke", password2="kratke")
    assert "neshodují" in change(current="dlouheheslo", password="noveheslo1", password2="noveheslo2")
    assert "Heslo je změněné" in change(current="dlouheheslo", password="noveheslo1", password2="noveheslo1")
    post(client, "/logout")
    assert post(client, "/login", username="BFM0903", password="dlouheheslo").status_code == 200
    assert post(client, "/login", username="BFM0903", password="noveheslo1").status_code == 302


def test_forms_show_the_shape_of_a_registration_number(client):
    """Tobias's wish: an example of the format next to the field, in the login and in the registration."""
    for path in ("/login", "/register", "/forgot"):
        html = client.get(path).get_data(as_text=True)
        assert 'placeholder="BFM0000"' in html and "Tři písmena oddílu a čtyři číslice, např. BFM0000" in html, path
    html = post(client, "/register", oris_regno="903", password="dlouheheslo", password2="dlouheheslo",
                code="x").get_data(as_text=True)
    assert "např. BFM0000." in html


def test_forgotten_password_is_set_with_a_one_time_code(app, client, user, monkeypatch):
    from webapp import db as dbm
    from webapp.services import accounts
    monkeypatch.setenv("OB_INSTANCE", app.config["OB"].instance)
    con = dbm.connect(app.config["OB"].db_path)
    post(client, "/logout")
    assert client.get("/login").get_data(as_text=True).count("Zapomenuté heslo</a>") == 1
    run = app.test_cli_runner()
    assert run.invoke(args=["reset-code", "BFM0001"]).exit_code != 0             # no such account
    r = run.invoke(args=["reset-code", "bfm 0903", "--site", "https://klub.example"])
    assert r.exit_code == 0, r.output
    regno, code, *_, link = r.output.split()
    assert regno == "BFM0903" and link == "https://klub.example/ob/forgot?regno=BFM0903"
    row = con.execute("SELECT * FROM users WHERE id = ?", (user,)).fetchone()
    assert row["reset_hash"] and code not in "".join(str(v) for v in tuple(row))   # only its hash is kept
    assert 'value="BFM0903"' in client.get("/forgot?regno=BFM0903").get_data(as_text=True)

    def new(code, regno="BFM0903", password="uplnenoveheslo", again=None):
        return post(client, "/forgot", oris_regno=regno, code=code, password=password,
                    password2=password if again is None else again)
    refused = "nesedí nebo už neplatí"
    assert refused in new("AAAA-AAAA").get_data(as_text=True)                    # a wrong code
    assert refused in new(code, regno="BFM0001").get_data(as_text=True)          # somebody without an account
    assert "aspoň 8 znaků" in new(code, password="kratke").get_data(as_text=True)
    assert "neshodují" in new(code, again="jineheslo123").get_data(as_text=True)
    # the code as people type it; then the new password works and the old one does not
    assert new(f" {code.replace('-', '').lower()} ").status_code == 302
    assert post(client, "/login", username="BFM0903", password="tajneheslo").status_code == 200
    assert post(client, "/login", username="BFM0903", password="uplnenoveheslo").status_code == 302
    post(client, "/logout")
    assert refused in new(code, password="jestejineheslo").get_data(as_text=True)          # one use only
    # a code is good for a day ...
    code = accounts.new_reset_code(con, user)
    con.execute("UPDATE users SET reset_until = datetime('now', '-1 minute') WHERE id = ?", (user,))
    con.commit()
    assert refused in new(code).get_data(as_text=True)
    # ... and five wrong tries make it void, so it cannot be guessed
    code = accounts.new_reset_code(con, user)
    for _ in range(accounts.RESET_TRIES):
        assert refused in new("ZZZZ-ZZZZ").get_data(as_text=True)
    assert refused in new(code).get_data(as_text=True)
    assert post(client, "/login", username="BFM0903", password="uplnenoveheslo").status_code == 302


def test_old_database_gets_the_columns_of_the_reset_code(tmp_path):
    from webapp import db as dbm
    path = str(tmp_path / "app.db")
    con = dbm.connect(path)
    con.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT"
                      " NOT NULL, name TEXT, oris_regno TEXT, oris_user_id INTEGER, oris_synced_at TEXT, slope_file"
                      " TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));"
                      "INSERT INTO users (username, password_hash, oris_regno) VALUES ('tobias', 'x', 'BFM0903');")
    con.commit()
    dbm.init(path)
    assert tuple(con.execute("SELECT reset_hash, reset_until, reset_tries FROM users").fetchone()) == (None, None, 0)
