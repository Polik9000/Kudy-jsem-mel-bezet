"""A race with only the map with the course: the terrain is read from it with the course taken out
(oroute/occlusion.py), the page says so, and a map without course replaces it."""
import os

import numpy as np
from conftest import post
from test_web_races import _fake_scripts, con_of, work

from oroute import occlusion
from oroute.kmzmap import GeoMap
from webapp.seed import seed_demo
from webapp.services import personal, runner


def _picture():
    """Green and white stripes, a purple line over them, a red line over the other way."""
    a = np.zeros((200, 300, 3), np.uint8)
    a[:] = (255, 255, 255)
    a[:, 100:200] = (205, 245, 205)
    a[95:101, :] = (180, 70, 245)
    a[:, 50:56] = (216, 26, 34)
    return a


def test_mask_finds_the_course_and_the_red_line():
    a = _picture()
    m = occlusion.mask(a)
    assert m[97, 10] and m[10, 52] and not m[10, 10]
    assert not occlusion.mask(a, red=False)[10, 52]


def test_fill_gives_back_the_terrain_under_the_lines():
    a = _picture()
    out, m, share = occlusion.repair(a)
    assert tuple(out[97, 10]) == (255, 255, 255) and tuple(out[97, 150]) == (205, 245, 205)
    assert tuple(out[10, 52]) == (255, 255, 255)
    assert 0 < share < 0.2
    for variant in occlusion.VARIANTS:
        o = occlusion.fill(a, m, variant)
        assert o.shape == a.shape and not occlusion.mask(o, grow=0).any()


def test_only_the_map_with_course(app, client, user, monkeypatch):
    con, conf = con_of(app), app.config["OB"]
    entry = seed_demo(con, conf, user)["petrvald"]
    con.execute("DELETE FROM jobs WHERE entry_id IS NOT ?", (entry,))
    con.execute("UPDATE events SET maponly_file = NULL")
    con.commit()
    log, maps = [], []
    fake = _fake_scripts(con, entry, log)

    def run(*cmd, **kw):
        if cmd[0] == "bestroute.py" and "--samples-only" not in cmd:
            maps.append(cmd[1])
        if cmd[:2] == ("-m", "oroute.relocate"):
            maps.append("relocate")
        return fake(*cmd, **kw)

    monkeypatch.setattr(runner, "_run", run)
    monkeypatch.setattr(personal, "refit", lambda con, conf, uid, fresh=None: (None, True))
    work(app)
    assert con.execute("SELECT has_routes FROM analyses WHERE entry_id = ?", (entry,)).fetchone()[0] == 1
    # the terrain was read from a map derived from the one with the course, and no catching features were looked for
    assert len(maps) == 1 and os.sep + "terrain" + os.sep in maps[0] and "relocate" not in maps
    GeoMap.from_kmz(maps[0])
    html = client.get(f"/races/{entry}").get_data(as_text=True)
    assert "Postupy jsou odhadnuté z mapy s tratí" in html
    assert 'href="/races/%d/lost"' % entry not in html

    # a map without course replaces the estimate
    seed_demo(con, conf, user)
    del maps[:]
    post(client, f"/races/{entry}/reanalyse")
    work(app)
    assert maps and os.sep + "terrain" + os.sep not in maps[0] and "relocate" in maps
    assert "Postupy jsou odhadnuté z mapy s tratí" not in client.get(f"/races/{entry}").get_data(as_text=True)
