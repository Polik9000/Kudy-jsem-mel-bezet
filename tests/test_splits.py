"""Split-time analysis of a whole class (oroute/splits.py, the WinSplits method) and its page."""
import datetime as dt

from conftest import FakeOris, oris_fixture

from oroute import splits as S
from webapp import db as dbm
from webapp import oris
from webapp.services import charts, sync_oris
from webapp.services import splits as class_splits


def pohora():
    return oris.parse_class_splits(oris_fixture("getSplits_202420.json"))["runners"]


def test_leg_times():
    assert S.leg_times([84, 200, None, 400, 410]) == [84, 116, None, None, 10]
    assert S.leg_times([84, 80, 300]) == [84, None, 220]        # clock going back is not a time


def test_reference_is_the_mean_of_the_best_quarter():
    legs = [[100], [110], [120], [130], [200], [300], [400], [1000]]
    assert S.reference(legs) == [105.0]                          # 8 runners -> best 2
    assert S.reference([[100], [None]]) == [100.0]
    assert S.reference([[None], [None]]) == [None]


def test_mistake_needs_both_thresholds():
    ref = [100.0] * 9 + [1000.0]
    # the runner is at 80 % of the reference on every leg but two: normal 0.8, expected 125 s
    a = S.analyse([125] * 7 + [150, 170, 1270], ref)
    assert abs(a["normal"] - 0.8) < 1e-9
    kinds = [l["mistake"] for l in a["legs"]]
    assert kinds == [False] * 7 + [False, True, False]
    # +25 s: over 25 % of nothing but under 30 s; +45 s: both; +20 s of 1250: over neither
    assert abs(a["legs"][8]["loss"] - 45) < 1e-9 and abs(a["mistakes"] - 45) < 1e-9
    assert abs(a["clean"] - (sum([125] * 7 + [150, 170, 1270]) - 45)) < 1e-9
    # a long leg 60 s slower is over 30 s but under 25 %: not a mistake
    assert not S.analyse([125] * 9 + [1310], ref)["legs"][9]["mistake"]


def test_class_table_pohora():
    t = S.class_table(pohora(), "bfm0903")
    assert t["n_legs"] == 17 and len(t["runners"]) == 32 and t["me"] is not None
    me = t["runners"][t["me"]]
    assert me["time_s"] == 3022 and me["legs"][0] == 84 and sum(me["legs"]) == 3022
    # the reference is faster than the winner on no leg ... and the superman beats the winner
    assert all(b <= r for b, r in zip(t["best"], t["ref"]))
    winner = min(r["time_s"] for r in t["runners"] if r["time_s"])
    assert t["superman"] < winner
    assert 0.5 < me["analysis"]["normal"] < 0.8
    assert all(1 <= k <= 32 for k in t["ranks"])
    # the winner has a normal near 1 and few mistakes
    first = next(r for r in t["runners"] if r["place"] == "1")
    assert first["analysis"]["normal"] > 0.9
    # the reference cumulates
    assert abs(t["ref_cum"][-1] - sum(t["ref"])) < 1e-6


def test_spearman_and_rank_agreement():
    assert abs(S.spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-9
    assert abs(S.spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9
    assert S.spearman([1, 2], [1, 2]) is None and S.spearman([1, 1, 1], [1, 2, 3]) is None
    assert abs(S.spearman([1, 2, 2, 3], [1, 2, 2, 3]) - 1.0) < 1e-9          # ties
    # the class is uniformly 30 % slower than the model, except leg 3 where it needs twice the proportion
    model = [60, 120, 90, 200, 45, 300]
    ref = [m * 1.3 for m in model]
    ref[2] *= 2
    a = S.rank_agreement(model, ref, ["S-1", "1-2", "2-3", "3-4", "4-5", "5-F"])
    assert a["n"] == 6 and abs(a["scale"] - 1.3) < 1e-9
    assert a["legs"][0]["name"] == "2-3" and abs(a["legs"][0]["dev"] - 2.0) < 1e-9
    assert all(abs(l["dev"] - 1) < 1e-9 for l in a["legs"][1:])
    assert a["rho"] < 1.0
    assert S.rank_agreement([60, None, 90], [70, 80, None]) is None
    assert abs(S.race_speed([100, 200, None], [300, 500, 100]) - 800 / 300) < 1e-9


def test_charts_are_plain_svg():
    t = S.class_table(pohora(), "BFM0903")
    svg = str(charts.splits_chart(t["runners"], t["ref_cum"], t["me"], [3]))
    assert svg.startswith("<svg") and 'class="ja"' in svg and svg.count('class="ostatni"') == 31
    assert "http" not in svg and "<script" not in svg
    bars = str(charts.bars_chart([10, -5, 80], ["S-1", "1-2", "2-F"], {2}, ylabel="ztráta"))
    assert bars.count("<rect") == 3 and "sloupec zle" in bars
    assert charts.splits_chart([], [], None) is None and charts.bars_chart([], []) is None
    assert charts.ticks(0, 100) == [0, 20, 40, 60, 80, 100]


def test_splits_chart_keeps_lines_below_the_control_numbers():
    """No line runs above the plot into the numbers of the controls, and every line says who it is and how far
    behind the reference it is at each control (for the pointer)."""
    import re
    t = S.class_table(pohora(), "BFM0903")
    # a runner faster than the reference everywhere: the top of the plot is made for them
    fast = dict(name="Rychlík", cum=[c * 0.8 for c in t["ref_cum"]])
    svg = str(charts.splits_chart(t["runners"] + [fast], t["ref_cum"], t["me"], [3]))
    top = charts.SPLITS_TOP
    labels = [float(y) for y in re.findall(r'<text class="kontrola" x="[\d.]+" y="([\d.]+)"', svg)]
    assert len(labels) == t["n_legs"] - 1 and all(y < top for y in labels)
    ys = [float(y) for d in re.findall(r'class="(?:ostatni|ja)" d="([^"]+)"', svg)
          for y in re.findall(r'[ML][\d.]+ ([\d.-]+)', d)]
    assert ys and min(ys) >= top                                   # every line inside the plot
    hits = re.findall(r'class="zasah" d="[^"]+" data-jmeno="([^"]+)" data-body="([^"]+)"', svg)
    assert len(hits) == svg.count('class="ostatni"') + 1
    body = dict(hits)["Rychlík"].split(";")
    assert len(body) == t["n_legs"] and all(float(b.split(",")[1]) < 0 for b in body)   # ahead of the reference


def test_splits_tab_works_without_fit_and_map(app, client, user):
    con = dbm.connect(app.config["OB"].db_path)
    msg = sync_oris.sync_user(con, app.config["OB"], user, client=FakeOris(), today=dt.date(2026, 10, 6), pause=0)
    assert "mezičasy kategorie načteny u 2" in msg
    assert con.execute("SELECT COUNT(*) FROM class_splits").fetchone()[0] == 2
    eid = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                      " WHERE ev.oris_id = 8989").fetchone()["id"]
    html = client.get(f"/races/{eid}").get_data(as_text=True)
    assert "chybí aktivita" in html and 'id="mezicasy"' in html and 'id="map"' not in html
    assert "Normální výkon" in html and "Graf mezičasů" in html and html.count("<svg class=\"ob-graf\"") == 2
    assert "Závodník 01" in html and "32 běžců" in html
    # asking ORIS again is not needed: the class is stored
    class Once(FakeOris):
        def class_splits_raw(self, class_id):
            raise AssertionError("asked again")
    assert "(0 nových)" in sync_oris.sync_user(con, app.config["OB"], user, client=Once(), pause=0,
                                               today=dt.date(2026, 10, 6))


def test_view_without_the_runner_in_the_class(app):
    con = dbm.connect(app.config["OB"].db_path)
    con.execute("INSERT INTO events (name, date) VALUES ('x', '2025-05-17')")
    con.execute("INSERT INTO classes (event_id, name) VALUES (1, 'H16C')")
    class_splits.store(con, 1, oris_fixture("getSplits_202420.json"))
    sp = class_splits.view(con, dict(class_id=1), "XXX0000")
    assert sp["me"] is None and sp["n_runners"] == 32 and sp["chart"] is not None and sp["bars"] is None
    class_splits.store_none(con, 1)                   # does not overwrite what is stored
    assert class_splits.view(con, dict(class_id=1), None)["n_runners"] == 32
    con.execute("INSERT INTO classes (event_id, name) VALUES (1, 'D21')")
    class_splits.store_none(con, 2)
    assert class_splits.view(con, dict(class_id=2), "BFM0903") is None
    # the model orders the legs like the class: checked against the reference times
    t = class_splits.table(con, 1, "BFM0903")
    a = class_splits.agreement(t, [r * 1.5 for r in t["ref"]])
    assert a["rho"] > 0.999 and a["outliers"] == [] and "stejně jako kategorie" in a["verdict"]
    assert class_splits.agreement(t, [1.0, 2.0]) is None
