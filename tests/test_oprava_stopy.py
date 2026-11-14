"""„Opravit moji stopu“: legs where the GPS failed are flagged, the runner draws where they really ran, the drawn line
stands for the track (bestroute.py --corrections) and the leg leaves the model; back to the GPS at any time."""
import json
import math
import os

import numpy as np
from conftest import csrf, post, register
from test_recompute import _fake_refit, _scripts
from test_web_races import con_of, work

from oroute.annotations import read_leg
from webapp.seed import seed_demo
from webapp.services import personal, results, runner


def send(client, url, body):
    return client.post(url, json=body, headers={"X-CSRF-Token": csrf(client)})


def _analysis(noise_m=3.0, seed=1):
    """analysis.json of a made-up race in town: three legs of 300 m due east at 3 m/s, one point a second, GPS noise
    of noise_m; on leg 2 the GPS jumps 60 m north for one second, on leg 3 the track ends 45 m beside the control."""
    rng = np.random.default_rng(seed)
    lat0, lon0 = 49.68, 18.35
    kx = 111320.0 * math.cos(math.radians(lat0))
    x = np.arange(0, 901, 3.0)
    y = np.zeros_like(x)
    y[150] += 60.0                                        # leg 2 (x 300..600): one jump
    y[-16:] += np.linspace(0, 45, 16)                     # leg 3: the end drifts 45 m north
    x, y = x + rng.normal(0, noise_m, len(x)), y + rng.normal(0, noise_m, len(x))
    t = list(range(len(x)))
    lat, lon = (lat0 + y / 110540.0).tolist(), (lon0 + x / kx).tolist()
    course = [dict(lat=lat0, lon=lon0 + d / kx) for d in (0, 300, 600, 900)]
    legs = [dict(leg=k, a=100 * (k - 1), b=100 * k) for k in (1, 2, 3)]
    return dict(track=dict(t=t, lat=lat, lon=lon), course=course, legs=legs)


def test_legs_where_the_gps_fails_are_flagged():
    A = _analysis()
    got = [results.gps_trouble(A, leg) for leg in A["legs"]]
    assert got[0] is None                                 # plain noise is fine
    assert got[1] and got[1]["jump_kmh"] > 30             # one jump of 60 m in a second
    assert got[2] and got[2]["far_m"] > 30 and got[2]["jump_kmh"] is None
    from webapp import texts
    assert texts.gps_trouble(got[1]).startswith("GPS tu asi zlobí: stopa skáče")
    assert "45 m od kontroly" in texts.gps_trouble(got[2]) or "od kontroly" in texts.gps_trouble(got[2])
    # more noise, no jump and the punch at the control: still nothing
    A = _analysis(noise_m=5.0, seed=7)
    assert results.gps_trouble(A, A["legs"][0]) is None


def test_a_drawn_leg_does_not_teach_the_model():
    leg = dict(time=80.0, est_loss=5.0, stops=[], best_time=70.0, line_time=75.0)
    assert read_leg(leg)["in_model"] and not read_leg(leg, dict(corrected="[[49.6, 18.3], [49.7, 18.4]]"))["in_model"]


def test_correction_is_used_for_the_routes_and_can_be_taken_back(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    con.execute("DELETE FROM jobs WHERE entry_id IS NOT ?", (entry,))
    con.commit()
    log, news = [], [True]
    fake = _scripts(log)
    seen = []

    def run(*cmd, on_line=None):
        if cmd[0] == "bestroute.py" and "--samples-only" not in cmd:
            fix = cmd[cmd.index("--corrections") + 1] if "--corrections" in cmd else None
            seen.append(json.load(open(fix)) if fix else None)
        return fake(*cmd, on_line=on_line)
    monkeypatch.setattr(runner, "_run", run)
    monkeypatch.setattr(personal, "refit", _fake_refit(log, news))
    work(app)
    assert seen == [None]
    drawn = [[49.6, 18.3], [49.601, 18.302], [49.602, 18.301]]
    r = send(client, f"/races/{entry}/legs/2/oprava", dict(line=drawn))
    assert r.status_code == 200
    leg2 = next(l for l in r.get_json()["legs"] if l["n"] == 2)
    assert leg2["note"]["corrected"] == drawn and not leg2["in_model"]
    job = con.execute("SELECT * FROM jobs WHERE entry_id = ? AND status = 'queued'", (entry,)).fetchone()
    assert job["kind"] == "analyse" and json.loads(job["payload"]) == dict(routes_only=True)
    work(app)
    assert seen[-1] == {"2": drawn}                                   # bestroute.py gets the drawn line for leg 2
    # the other notes of the leg stay when the note is saved, and the correction stays with them
    send(client, f"/races/{entry}/legs/2/note", dict(text="město, GPS skákala"))
    note = con.execute("SELECT * FROM leg_notes WHERE entry_id = ? AND leg_n = 2", (entry,)).fetchone()
    assert note["text"] == "město, GPS skákala" and json.loads(note["corrected"]) == drawn
    # back to the GPS
    r = send(client, f"/races/{entry}/legs/2/oprava", dict(line=None))
    assert next(l for l in r.get_json()["legs"] if l["n"] == 2)["note"]["corrected"] is None
    work(app)
    assert seen[-1] is None
    assert not os.path.exists(conf.path("races", f"entry_{entry}", "best", "corrections.json"))
    # bad input and somebody else's race
    assert send(client, f"/races/{entry}/legs/2/oprava", dict(line=[[91, 0], [0, 0]])).status_code == 400
    assert send(client, f"/races/{entry}/legs/99/oprava", dict(line=drawn)).status_code == 404
    post(client, "/logout")
    register(client, "BFM0001")
    assert send(client, f"/races/{entry}/legs/2/oprava", dict(line=drawn)).status_code == 404


def test_race_page_offers_the_correction(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["pohora"]
    monkeypatch.setattr(runner, "_run", _scripts([]))
    monkeypatch.setattr(personal, "refit", _fake_refit([], [True]))
    work(app)
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert 'id="b-oprava"' in html and "Opravit moji stopu" in html and 'id="p-gps"' in html
