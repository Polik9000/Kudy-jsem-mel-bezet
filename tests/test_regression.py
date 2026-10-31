"""The four races in data/ must keep giving the results they gave before the web app was added.

These run the real scripts (about 7 minutes for all four), so the whole module is marked slow:
    pytest -m slow            only these
    pytest -m "not slow"      everything else
"""
import os
import re

import pytest
from races import GOLDEN, IDS, RACES

pytestmark = pytest.mark.slow


def read(*path):
    with open(os.path.join(*path), "rb") as f:
        return f.read()


def seconds(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


@pytest.mark.parametrize("folder,title,total", RACES, ids=IDS)
def test_total_time(analysed, folder, title, total):
    report = read(analysed(folder), "report.md").decode("utf-8")
    assert seconds(re.search(r"Time start to finish: \*\*(\d+:\d\d)\*\*", report).group(1)) == total


@pytest.mark.parametrize("folder,title,total", RACES, ids=IDS)
def test_legs_unchanged(analysed, folder, title, total):
    for name in ("legs.csv", "course.json"):
        assert read(analysed(folder), name) == read(GOLDEN, folder, name), name


@pytest.mark.parametrize("folder,title,total", RACES, ids=IDS)
def test_best_routes_unchanged(routed, folder, title, total):
    assert read(routed(folder, title), "best_legs.csv") == read(GOLDEN, folder, "best_legs.csv")
