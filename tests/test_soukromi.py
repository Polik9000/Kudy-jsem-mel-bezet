"""Nothing leaves the computer but what docs/soukromi.md lists (TODO 48)."""
import io
import json
import os
import re
import urllib.parse
import urllib.request

import numpy as np
import pytest
from PIL import Image

from oroute import dem, errors, mapdata, osm
from oroute.kmzmap import GeoMap
from webapp import oris, texts
from webapp.config import ROOT

# the hosts the app calls itself, and the links its pages show (the browser opens those when clicked)
CALLED = {"oris.ceskyorientak.cz", "ags.cuzk.gov.cz", "s3.amazonaws.com", "overpass-api.de",
          "overpass.private.coffee"}
LINKS = {"www.livelox.com", "www.openstreetmap.org", "github.com", "www.garmin.com", "skobfm.vzdyonline.cz",
         "127.0.0.1", "localhost", "example.org"}


def source_files():
    for folder in ("webapp", "oroute", "desktop"):
        for root, _, files in os.walk(os.path.join(ROOT, folder)):
            for f in files:
                if f.endswith((".py", ".html", ".js")) and "vendor" not in root and "__pycache__" not in root:
                    yield os.path.join(root, f)
    for f in ("analyze.py", "bestroute.py", "run_race.py"):
        yield os.path.join(ROOT, f)


def test_no_other_web_address_in_the_code():
    found = {}
    for path in source_files():
        with open(path, encoding="utf-8") as f:
            for host in re.findall(r"https?://([A-Za-z0-9.-]+)", f.read()):
                found.setdefault(host, path)
    unknown = {h: p for h, p in found.items()
               if h not in CALLED | LINKS and not h.endswith(("w3.org", "opengis.net", "google.com", "leafletjs.com"))}
    assert not unknown, f"a new web address: add it to docs/soukromi.md and to this test: {unknown}"


def test_the_table_lists_every_called_host():
    with open(os.path.join(ROOT, "docs", "soukromi.md"), encoding="utf-8") as f:
        text = f.read()
    for host in CALLED:
        assert host in text, host


class Spy:
    """urlopen that records the address and the body and answers with `reply`."""

    def __init__(self, reply=b"{}"):
        self.calls, self.reply = [], reply

    def __call__(self, req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        body = None if isinstance(req, str) else req.data
        self.calls.append((url, body))
        spy = self

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Resp(spy.reply)


def test_elevation_asks_only_for_tiles_or_a_box(monkeypatch, tmp_path):
    tile = io.BytesIO()
    Image.new("RGB", (256, 256), (128, 0, 0)).save(tile, "PNG")
    spy = Spy(tile.getvalue())
    monkeypatch.setattr(urllib.request, "urlopen", spy)
    dem.TerrariumDEM(49.60, 49.59, 16.80, 16.79, cache=str(tmp_path / "c.npz"))
    assert spy.calls
    for url, body in spy.calls:
        assert urllib.parse.urlparse(url).netloc == "s3.amazonaws.com" and body is None
        assert re.fullmatch(r"https://s3\.amazonaws\.com/elevation-tiles-prod/terrarium/\d+/\d+/\d+\.png", url)
    spy.calls.clear()
    with pytest.raises(Exception):      # a reply that is no TIFF: only the request matters here
        dem.CuzkDEM(49.60, 49.59, 16.80, 16.79, cache=str(tmp_path / "z.npz"))
    for url, body in spy.calls:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert urllib.parse.urlparse(url).netloc == "ags.cuzk.gov.cz" and body is None
        assert set(q) == {"bbox", "bboxSR", "imageSR", "size", "format", "pixelType", "interpolation", "f"}


def test_openstreetmap_asks_for_a_box_only(monkeypatch):
    spy = Spy(json.dumps({"elements": []}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", spy)
    osm.fetch(49.59, 16.79, 49.60, 16.80)
    (url, body), = spy.calls
    assert urllib.parse.urlparse(url).netloc == "overpass-api.de"
    query = urllib.parse.parse_qs(body.decode())["data"][0]
    assert "49.59" in query and "16.8" in query
    assert not re.search(r"(?i)fit|track|stopa|name~|user", query.replace("highway", ""))


def test_oris_gets_the_method_and_the_ids_only(monkeypatch):
    spy = Spy(json.dumps({"Status": "OK", "Data": {}}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", spy)
    client = oris.Oris()
    client.call("getUser", rgnum="BFM0903")
    client.call("getSplits", classid=202420)
    for url, body in spy.calls:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert urllib.parse.urlparse(url).netloc == "oris.ceskyorientak.cz" and body is None
        assert set(q) <= {"format", "method", "rgnum", "classid", "userid", "id"}


def test_without_internet_the_elevation_says_so_in_czech(monkeypatch, tmp_path):
    def down(*a, **k):
        raise OSError("Network is unreachable")
    monkeypatch.setattr(urllib.request, "urlopen", down)
    gm = GeoMap.__new__(GeoMap)
    gm.n, gm.s, gm.e, gm.w, gm.W, gm.H = 49.60, 49.59, 16.80, 16.79, 100, 100
    gm.px_to_latlon = lambda u, v: (np.array([49.6, 49.6, 49.59, 49.59]), np.array([16.79, 16.8, 16.79, 16.8]))
    with pytest.raises(errors.InputError) as e:
        mapdata.elevation(gm, str(tmp_path), "aws")
    assert e.value.code == "no_network"
    assert "nepodařilo stáhnout" in texts.analysis_error(e.value.code, e.value.text)
