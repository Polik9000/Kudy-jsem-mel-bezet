"""tools/podezrele.py: the legs run clearly faster than the best route of the model are the suspects; legs
without data and legs with standing or wandering say nothing."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import podezrele  # noqa: E402


def race(tmp_path, legs, name="zavod", personal=None):
    """An output folder with best/best.json and analysis.json of legs given as
    dict(actual, best, yours=None, no_data=False, flags=(), mistake=None)."""
    out = tmp_path / name
    (out / "best").mkdir(parents=True)
    B, A = [], []
    for k, l in enumerate(legs, 1):
        B.append(dict(leg=k, name=f"{k - 1}-{k}", actual=l["actual"], no_data=bool(l.get("no_data")),
                      best=dict(time=l["best"], dist=300.0, mix={"path/road": 120.0}),
                      yours=dict(time=l.get("yours", l["best"]), dist=320.0), route=[]))
        A.append(dict(leg=k, flag_codes=list(l.get("flags", ())), mistake=l.get("mistake"), stop_time=0))
    model = dict(notes=dict(personal=personal)) if personal else {}
    (out / "best" / "best.json").write_text(json.dumps(dict(title=name, legs=B, model=model)), encoding="utf-8")
    (out / "analysis.json").write_text(json.dumps(dict(legs=A)), encoding="utf-8")
    return str(out)


ORDINARY = [dict(actual=130, best=100), dict(actual=128, best=100), dict(actual=133, best=100), dict(actual=131, best=100)]


def test_only_the_leg_run_clearly_faster_than_the_best_route_is_a_suspect(tmp_path):
    legs = [dict(actual=95, best=100),                                        # clearly faster than the model allows
            dict(actual=90, best=100, flags=("zone", "stop"), mistake=dict(type="circling")),    # wandering
            dict(actual=60, best=100, no_data=True)] + ORDINARY               # no track of the leg
    rows, summary = podezrele.suspects([podezrele.load(race(tmp_path, legs))])
    assert [(r["name"], r["groups"]) for r in rows] == [("0-1", "A")]
    assert rows[0]["norm"] == pytest.approx(95 / 100 / 1.30, abs=0.01) and rows[0]["diff_s"] == pytest.approx(35, abs=1)
    # the two legs left out do not move the median either
    assert summary[0]["clean"] == 5 and summary[0]["median"] == pytest.approx(1.30, abs=0.01) and summary[0]["a"] == 1


def test_a_short_leg_a_slow_race_and_an_overpriced_track(tmp_path):
    legs = [dict(actual=22, best=20),            # 15 % under the median, but only 4 s: noise
            dict(actual=200, best=100, yours=240),      # slower than the model: no suspect of group A, ...
            dict(actual=130, best=100, yours=160),      # ... the own track 23 % over the actual time: group B
            dict(actual=130, best=100, yours=140)] + ORDINARY
    rows, _ = podezrele.suspects([podezrele.load(race(tmp_path, legs))])
    assert [(r["name"], r["groups"]) for r in rows] == [("1-2", "B"), ("2-3", "B")] or \
        [(r["name"], r["groups"]) for r in rows] == [("2-3", "B"), ("1-2", "B")]
    # a race the runner ran slowly as a whole has no suspects: the median takes the whole race out
    slow = [dict(actual=2 * l["actual"], best=l["best"]) for l in ORDINARY]
    assert podezrele.suspects([podezrele.load(race(tmp_path, slow, "pomaly"))])[0] == []
    # too few clean legs: no median, nothing judged
    few = [dict(actual=50, best=100), dict(actual=130, best=100)]
    rows, summary = podezrele.suspects([podezrele.load(race(tmp_path, few, "kratky"))])
    assert rows == [] and summary[0]["median"] is None


def test_wandering_at_the_control_and_two_models_in_one_list(tmp_path):
    legs = [dict(actual=95, best=100)] + ORDINARY
    folder = race(tmp_path, legs, personal=dict(fitted="2026-10-06"))
    with open(os.path.join(folder, "best", "relocate.json"), "w", encoding="utf-8") as f:
        json.dump(dict(controls=[dict(leg=1, lost=dict(extra_s=40))]), f)
    assert podezrele.suspects([podezrele.load(folder)])[0] == []          # lost at the control: left out
    other = race(tmp_path, legs, "jiny", personal=dict(fitted="2026-11-01"))
    with pytest.raises(SystemExit, match="mixed_models"):
        podezrele.suspects([podezrele.load(folder), podezrele.load(other)])


def test_the_list_is_written_with_the_most_suspicious_leg_first(tmp_path):
    legs = [dict(actual=100, best=100), dict(actual=70, best=100, yours=75)] + ORDINARY
    races = [podezrele.load(race(tmp_path, legs))]
    rows, summary = podezrele.suspects(races)
    assert [r["name"] for r in rows] == ["1-2", "0-1"]
    podezrele.write(rows, summary, races, str(tmp_path / "out"), "podezrele")
    text = (tmp_path / "out" / "podezrele.md").read_text(encoding="utf-8")
    assert text.index("| 1 | zavod | 1-2 | A |") < text.index("| 2 | zavod | 0-1 | A |")
    assert (tmp_path / "out" / "podezrele.csv").read_text(encoding="utf-8").splitlines()[1].startswith("1;zavod;2;1-2;A;")


def test_a_leg_whose_track_does_not_come_to_its_control_is_left_out(tmp_path):
    legs = [dict(actual=95, best=100), dict(actual=95, best=100)] + ORDINARY
    folder = race(tmp_path, legs)
    with open(os.path.join(folder, "analysis.json"), encoding="utf-8") as f:
        A = json.load(f)
    # the course runs north, 100 m a leg; the track is at every control when it is punched, but at control 2
    # it is 90 m to the side (the control was read in the wrong place, or lies on another sheet of the picture)
    n = len(legs) + 1
    A["course"] = [dict(lat=50.0 + k * 0.0009, lon=18.0) for k in range(n)]
    # (and the recording begins 90 m from the start triangle, which says nothing against the first leg)
    A["track"] = dict(lat=[c["lat"] for c in A["course"]], lon=[18.0 + (0.00126 if k in (0, 2) else 0.0) for k in range(n)])
    A["punch"] = list(range(n))
    with open(os.path.join(folder, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(A, f)
    r = podezrele.load(folder)
    assert [l["left_out"] for l in r["legs"]][:4] == [None, "track off the controls", "track off the controls", None]
    assert [x["name"] for x in podezrele.suspects([r])[0]] == ["0-1"]
