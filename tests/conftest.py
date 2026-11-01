import json
import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from races import GOLDEN, ROOT, have_data, inputs  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
_done = {}


def pytest_collection_modifyitems(config, items):
    """Without the race data (public repo) the tests that need it, and the slow ones, are skipped."""
    if have_data():
        return
    skip = pytest.mark.skip(reason="needs the race maps and runs in data/ and tests/golden (not public)")
    for item in items:
        if "needs_data" in item.keywords or "slow" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _made_up_races_without_the_real_ones(monkeypatch):
    """Without the real races (the public repo) the demo races of webapp/seed.py are the made-up ones of
    tests/synthetic.py, at the same place and time."""
    if not have_data():
        import synthetic

        from webapp import seed
        monkeypatch.setattr(seed, "demo_dir", lambda folder: os.path.dirname(synthetic.inputs(folder)[0]))


def _run(*cmd):
    subprocess.run([sys.executable, *cmd], check=True, cwd=ROOT, capture_output=True)


def oris_fixture(name):
    with open(os.path.join(FIXTURES, "oris", name), encoding="utf-8") as f:
        return json.load(f)["Data"]


@pytest.fixture(scope="session")
def analysed(tmp_path_factory):
    """analysed(folder, official=None) -> output folder of analyze.py for that race (run once per session).
    official: dict for --official (oroute/official.py), None = punches from GPS as before."""
    def get(folder, official=None):
        key = ("a", folder, official is not None)
        if key not in _done:
            out = str(tmp_path_factory.mktemp(folder))
            course, _, fit = inputs(folder)
            extra = []
            if official is not None:
                with open(os.path.join(out, "official.json"), "w") as f:
                    json.dump(official, f)
                extra = ["--official", os.path.join(out, "official.json")]
            _run("analyze.py", course, fit, out, *extra)
            _done[key] = out
        return _done[key]
    return get


@pytest.fixture(scope="session")
def routed(analysed):
    """routed(folder, title, official=None) -> output folder of bestroute.py; elevation from tests/golden
    (no network)."""
    def get(folder, title, official=None):
        key = ("b", folder, official is not None)
        if key not in _done:
            out = analysed(folder, official)
            best = os.path.join(out, "best")
            os.makedirs(best, exist_ok=True)
            shutil.copyfile(os.path.join(GOLDEN, folder, "dem_cache.npz"), os.path.join(best, "dem_cache.npz"))
            _, maponly, fit = inputs(folder)
            extra = ["--official", os.path.join(out, "official.json")] if official is not None else []
            _run("bestroute.py", maponly, os.path.join(out, "course.json"), fit, best, "--title", title, *extra)
            _done[key] = best
        return _done[key]
    return get


# --- web app ---------------------------------------------------------------------------------------------

class FakeOris:
    """ORIS answering from the saved responses in tests/fixtures/oris (no network in tests)."""
    PEOPLE = {"BFM0001": dict(oris_user_id=90001, name="Klára Kolegyně"),
              "BFM0002": dict(oris_user_id=90002, name="Jan Druhý")}

    def user(self, regno):
        from webapp import oris
        if regno in self.PEOPLE:
            return dict(self.PEOPLE[regno])
        return oris.parse_user(oris_fixture("getUser.json" if regno == "BFM0903" else "getUser_missing.json"))

    def entries(self, uid):
        from webapp import oris
        if uid != 45118:
            return []
        return [e for e in oris.parse_entries(oris_fixture("getUserEventEntries.json")) if e["event_id"] != 10250]

    def event(self, oris_id):
        from webapp import oris
        return oris.parse_event(oris_fixture(f"getEvent_{oris_id}.json"))

    def class_splits_raw(self, class_id):
        return oris_fixture(f"getSplits_{class_id}.json")

    def splits(self, class_id, regno):
        from webapp import oris
        return oris.parse_splits(self.class_splits_raw(class_id), regno)


def invite(client, regno):
    """The registration code of a number, as the administrator would print it."""
    from webapp.services import accounts
    return accounts.invite_code(client.application.config["OB"], accounts.clean_regno(regno))


def register(client, regno="BFM0903", password="tajneheslo", code=None):
    return post(client, "/register", oris_regno=regno, password=password, password2=password,
                code=invite(client, regno) if code is None else code)


def clear_jobs(app):
    """Drop what is waiting in the queue (registration queues an ORIS sync; most tests do not want it)."""
    from webapp import db as dbm
    con = dbm.connect(app.config["OB"].db_path)
    con.execute("DELETE FROM jobs")
    con.commit()
    con.close()


def csrf(client, path="/login"):
    """The CSRF token of the session (every POST needs it)."""
    import re
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([0-9a-f]+)"', html).group(1)


def post(client, path, **form):
    return client.post(path, data=dict(form, csrf_token=csrf(client)))


@pytest.fixture
def app(tmp_path):
    from webapp import create_app
    app = create_app(str(tmp_path / "instance"))
    app.config["TESTING"] = True
    app.config["OB"].oris_client = FakeOris()
    app.config["OB"].dem = "aws"      # no network in tests: elevation only from the tiles stored in tests/golden
    app.config["OB"].osm = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app, client):
    """A registered and logged-in runner (BFM0903, as in the saved ORIS responses); returns the user id."""
    r = register(client)
    assert r.status_code == 302, r.get_data(as_text=True)
    clear_jobs(app)
    with client.session_transaction() as s:
        return s["user_id"]
