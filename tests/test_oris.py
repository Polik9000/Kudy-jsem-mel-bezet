"""ORIS responses (saved in tests/fixtures/oris, no network) -> the dicts the web app stores."""
import datetime as dt

from conftest import oris_fixture

from webapp import oris


def test_seconds():
    assert oris.seconds("58:37") == 58 * 60 + 37
    assert oris.seconds("80:18") == 80 * 60 + 18
    assert oris.seconds("1:02:03") == 3723
    assert oris.seconds("DISK") is None and oris.seconds("") is None and oris.seconds(None) is None


def test_user():
    assert oris.parse_user(oris_fixture("getUser.json")) == dict(oris_user_id=45118, name="Tobiáš Otta")
    assert oris.parse_user(oris_fixture("getUser_missing.json")) is None


def test_entries():
    e = {x["event_id"]: x for x in oris.parse_entries(oris_fixture("getUserEventEntries.json"))}
    assert e[8989] == dict(event_id=8989, class_id=202420, class_name="H16C", date="2025-05-17")
    assert e[9827]["class_name"] == "H18"


def test_event():
    ev = oris.parse_event(oris_fixture("getEvent_9827.json"))
    assert ev["name"] == "Mistrovství oblasti na dlouhé trati" and ev["date"] == "2026-03-28"
    assert ev["livelox_id"] == "182468" and ev["place"] == "Petřvald u Karviné"
    h18 = next(c for c in ev["classes"] if c["name"] == "H18")
    assert h18 == dict(oris_id=215134, name="H18", distance_km=7.88, climb_m=280.0, controls=19)
    assert oris.livelox_url(ev["livelox_id"]) == "https://www.livelox.com/Events/Show/182468"


def test_livelox_missing_id_is_not_linked():
    for value in (None, "", " ", 0, "0", " 0 "):
        assert oris.livelox_url(value) is None

    event = oris_fixture("getEvent_9827.json")
    for value in (None, "", " ", 0, "0", " 0 "):
        event["LiveloxID"] = value
        assert oris.parse_event(event)["livelox_id"] is None


def test_livelox_valid_id_is_preserved():
    assert oris.livelox_url("182468") == "https://www.livelox.com/Events/Show/182468"
    assert oris.livelox_url(182468) == "https://www.livelox.com/Events/Show/182468"


def test_splits_pohora():
    s = oris.parse_splits(oris_fixture("getSplits_202420.json"), "bfm0903")
    assert s["time_s"] == 50 * 60 + 22 and s["start_local"] == "13:18:00"
    assert len(s["control_codes"]) == 16 and s["control_codes"][0] == "153"
    # 16 controls + finish; the finish split is missing in ORIS and comes from the result time
    assert len(s["cumulative"]) == 17
    assert s["cumulative"][0] == 84 and s["cumulative"][15] == 50 * 60 + 12 and s["cumulative"][16] == 3022


def test_splits_other_runner():
    assert oris.parse_splits(oris_fixture("getSplits_202420.json"), "XXX0000") is None
    assert oris.parse_splits([], "BFM0903") is None


def test_start_utc():
    # summer time: 13:18 in Prague is 11:18 UTC; winter time: 11:03 is 10:03 UTC
    assert oris.start_utc("2025-05-17", "13:18:00") == dt.datetime(2025, 5, 17, 11, 18, tzinfo=dt.timezone.utc)
    assert oris.start_utc("2026-03-28", "11:03:00") == dt.datetime(2026, 3, 28, 10, 3, tzinfo=dt.timezone.utc)


def test_event_links_and_places():
    ev = oris.parse_event(oris_fixture("getEvent_9827.json"))
    assert dict(name="Online výsledky", url="https://oresults.eu/events/2924") in ev["links"]
    assert oris.oresults_url(ev["links"]) == "https://oresults.eu/events/2924"
    assert oris.oresults_url([]) is None
    centre = next(l for l in ev["locations"] if l["name"].startswith("Centrum"))
    assert abs(centre["lat"] - 49.8336) < 1e-3 and abs(centre["lon"] - 18.3731) < 1e-3
    assert oris.results_url(9827) == "https://oris.ceskyorientak.cz/Vysledky?id=9827"


def test_class_splits():
    c = oris.parse_class_splits(oris_fixture("getSplits_202420.json"))
    assert len(c["control_codes"]) == 16 and len(c["runners"]) == 32
    me = next(r for r in c["runners"] if r["regno"] == "BFM0903")
    assert me["time_s"] == 3022 and me["place"] == "15" and me["status"] == "OK" and len(me["cum"]) == 17
    assert me["cum"][0] == 84 and me["cum"][-1] == 3022
    winner = c["runners"][0]
    assert winner["place"] == "1" and winner["time_s"] == 32 * 60 + 48 and winner["cum"][-1] == winner["time_s"]
    out = [r for r in c["runners"] if r["status"] != "OK"]
    assert len(out) == 3 and all(r["time_s"] is None and r["place"] is None for r in out)
    # a disqualified runner with a missing punch: the gap is None, the clock time to the finish is kept
    dq = oris.parse_class_splits(oris_fixture("getSplits_215134.json"))["runners"][-1]
    assert dq["status"] == "DISK" and dq["cum"][7] is None and dq["cum"][8] == 39 * 60 + 28
    assert dq["cum"][-1] == 107 * 60 + 33
    assert oris.parse_class_splits({"Splits": [], "Controls": []}) is None
