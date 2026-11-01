"""The class a runner really ran (webapp/services/oris_class.py): "I ran another class" on the page of a race
from ORIS, and a race from ORIS added by its number or link. ORIS answers from tests/fixtures/oris; it is asked
once per race (getEvent) and once per class (getSplits)."""
import datetime as dt

from conftest import FakeOris, oris_fixture, post

from webapp import db as dbm
from webapp import oris
from webapp.services import oris_class, sync_oris


class Counting(FakeOris):
    """FakeOris that counts the calls; a class without a saved answer has no split times."""
    def __init__(self):
        self.calls = []

    def event(self, oris_id):
        self.calls.append(("getEvent", oris_id))
        return super().event(oris_id)

    def class_splits_raw(self, class_id):
        self.calls.append(("getSplits", class_id))
        try:
            return oris_fixture(f"getSplits_{class_id}.json")
        except FileNotFoundError:
            return {"Splits": {}}


def con_of(app):
    return dbm.connect(app.config["OB"].db_path)


def entry_of(con, oris_id):
    return con.execute("SELECT e.*, c.name AS cls FROM entries e JOIN classes c ON c.id = e.class_id"
                       " JOIN events ev ON ev.id = c.event_id WHERE ev.oris_id = ?", (oris_id,)).fetchall()


def test_another_class_takes_its_times_and_a_sync_does_not_undo_it(app, client, user):
    con, conf = con_of(app), app.config["OB"]
    fake = conf.oris_client = Counting()
    sync_oris.sync_user(con, conf, user, client=fake, today=dt.date(2026, 10, 6), pause=0)
    (e,) = entry_of(con, 8989)
    assert e["cls"] == "H16C" and e["official_time_s"] == 3022 and not e["class_chosen"]
    event_id = con.execute("SELECT event_id FROM classes WHERE id = ?", (e["class_id"],)).fetchone()[0]
    classes = {c["name"]: c["id"] for c in oris_class.event_classes(con, event_id)}
    assert set(classes) == {"D21C", "H16C"}           # every class of the race is kept with the one entered
    html = client.get(f"/races/{e['id']}").get_data(as_text=True)
    assert "Běžel jsem jinou kategorii" in html and f'<option value="{classes["D21C"]}">D21C</option>' in html

    con.execute("INSERT INTO leg_notes (entry_id, leg_n, text) VALUES (?, 1, 'jiná trať')", (e["id"],))
    con.commit()
    fake.calls.clear()
    r = post(client, f"/races/{e['id']}/class", class_id=classes["D21C"])
    assert r.status_code == 302 and r.headers["Location"].endswith("#kategorie")
    assert fake.calls == [("getSplits", 202411)]
    (e,) = entry_of(con, 8989)
    assert e["cls"] == "D21C" and e["class_chosen"] == 1 and e["official_time_s"] is None and e["splits"] is None
    assert not con.execute("SELECT 1 FROM leg_notes WHERE entry_id = ?", (e["id"],)).fetchone()
    html = client.get(f"/races/{e['id']}").get_data(as_text=True)
    assert "Ve výsledcích této kategorie v ORIS nejsi" in html and "kategorie D21C" in html

    # ORIS still has the entry in H16C: a sync keeps the class the runner chose
    sync_oris.sync_user(con, conf, user, client=fake, today=dt.date(2026, 10, 6), pause=0)
    assert [r["cls"] for r in entry_of(con, 8989)] == ["D21C"]

    # back to H16C: its times are in the database already, ORIS is not asked
    fake.calls.clear()
    post(client, f"/races/{e['id']}/class", class_id=classes["H16C"])
    assert fake.calls == []
    (e,) = entry_of(con, 8989)
    assert e["cls"] == "H16C" and e["official_time_s"] == 3022 and dbm.loads(e["splits"])[-1] == 3022


def test_the_classes_of_a_race_are_loaded_once_when_only_the_entered_one_is_known(app, client, user):
    con, conf = con_of(app), app.config["OB"]
    fake = conf.oris_client = Counting()
    sync_oris.sync_user(con, conf, user, client=fake, today=dt.date(2026, 10, 6), pause=0)
    (e,) = entry_of(con, 9827)
    con.execute("DELETE FROM classes WHERE name = 'D21'")          # a race synced before every class was kept
    con.commit()
    assert 'name="class_id"' not in client.get(f"/races/{e['id']}").get_data(as_text=True).split('id="kategorie"')[1][:900]
    fake.calls.clear()
    post(client, f"/races/{e['id']}/class")
    post(client, f"/races/{e['id']}/class")
    assert fake.calls == [("getEvent", 9827)]
    assert {c["name"] for c in oris_class.event_classes(con, con.execute(
        "SELECT event_id FROM classes WHERE id = ?", (e["class_id"],)).fetchone()[0])} == {"D21", "H18"}


def test_a_race_from_oris_is_added_by_its_link_with_the_chosen_class(app, client, user):
    con, conf = con_of(app), app.config["OB"]
    fake = conf.oris_client = Counting()
    assert oris_class.parse_ref("https://oris.ceskyorientak.cz/Zavod?id=9827&x=1") == 9827
    assert oris_class.parse_ref(" 9827 ") == 9827 and oris_class.parse_ref("zavod") is None
    assert "Zadej číslo závodu" in post(client, "/races/oris", zavod="nevím").get_data(as_text=True)
    r = post(client, "/races/oris", zavod="https://oris.ceskyorientak.cz/Zavod?id=9827")
    assert r.status_code == 302 and r.headers["Location"].endswith("/races/oris/9827")
    html = client.get("/races/oris/9827").get_data(as_text=True)
    assert "Mistrovství oblasti na dlouhé trati" in html and ">D21</option>" in html and ">H18</option>" in html
    h18 = con.execute("SELECT id FROM classes WHERE name = 'H18'").fetchone()[0]
    r = post(client, "/races/oris/9827", class_id=h18)
    (e,) = entry_of(con, 9827)
    assert r.headers["Location"].endswith(f"/races/{e['id']}")
    assert e["cls"] == "H18" and e["class_chosen"] == 1 and e["official_time_s"] == 4818
    assert fake.calls == [("getEvent", 9827), ("getSplits", 215134)]
    # again: nothing is asked and nothing is added, the page leads to the race
    post(client, "/races/oris", zavod="9827")
    html = post(client, "/races/oris/9827", class_id=h18).headers["Location"]
    assert html.endswith(f"/races/{e['id']}") and len(entry_of(con, 9827)) == 1
    assert fake.calls == [("getEvent", 9827), ("getSplits", 215134)]
    assert "Přidat závod podle ORIS" in client.get("/").get_data(as_text=True)


def test_a_race_oris_does_not_know_says_so(app, client, user):
    class Missing(Counting):
        def event(self, oris_id):
            raise oris.OrisError(f"ORIS getEvent: {oris_id}")
    app.config["OB"].oris_client = Missing()
    html = post(client, "/races/oris", zavod="123456").get_data(as_text=True)
    assert "se z ORIS načíst nepodařilo" in html
