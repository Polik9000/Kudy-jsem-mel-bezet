"""Out-of-bounds areas read from the purple cross-hatching of the map with the course (oroute/hatch.py):
a drawn map (seconds), the four maps in data/ and the routes keeping out of the areas."""
import numpy as np
import pytest
from PIL import Image, ImageDraw
from races import inputs

from oroute import hatch
from oroute import terrain as T
from oroute.kmzmap import GeoMap
from oroute.routing import Grid
from oroute.speedmodel import SpeedModel

PURPLE = (180, 70, 245)
FIELD = (150, 120, 330, 240)   # the hatched rectangle of the drawn map: x0, y0, x1, y1


def drawn_map(hatched=True, road=False, w=500, h=400):
    """A white sheet, 1.33 m per pixel, with a course (circles, legs, an "8") and optionally a hatched field.
    hatched="vertical": the field is hatched with parallel vertical lines instead of crossed ones."""
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    if hatched:
        lines = Image.new("L", (w, h), 0)
        dl = ImageDraw.Draw(lines)
        for k in range(0, w, 6) if hatched == "vertical" else ():      # lines straight up, 6 px (8 m) apart
            dl.line([(k, 0), (k, h)], fill=255, width=2)
        for k in range(-h, w + h, 12) if hatched is True else ():      # two families at 45 degrees, 12 px apart along x
            dl.line([(k, 0), (k + h, h)], fill=255, width=2)
            dl.line([(k, h), (k + h, 0)], fill=255, width=2)
        field = Image.new("L", (w, h), 0)
        ImageDraw.Draw(field).rectangle(FIELD, fill=255)
        im.paste(PURPLE, mask=Image.composite(lines, Image.new("L", (w, h), 0), field))
    for cx, cy in ((60, 60), (420, 80), (400, 330), (80, 320)):
        d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=PURPLE, width=3)
    d.line([(82, 60), (398, 80)], fill=PURPLE, width=3)
    d.line([(420, 102), (400, 308)], fill=PURPLE, width=3)
    d.line([(378, 330), (102, 320)], fill=PURPLE, width=3)
    for cy in (300, 318):                          # an "8" next to a control: two closed loops
        d.ellipse([120, cy - 9, 136, cy + 9], outline=PURPLE, width=3)
    if road:                                       # a black road across the field: the purple disappears under it
        d.line([(100, 170), (400, 195)], fill=(35, 31, 32), width=4)
    k = 1.33 / 111195.0
    return GeoMap(im, 50.0 + h * k / 2, 50.0 - h * k / 2, 18.0 + w * k / 2 / 0.643, 18.0 - w * k / 2 / 0.643)


def test_vertical_hatching_is_found_and_lone_vertical_strokes_are_not():
    """Parallel vertical lines (older maps, sprints): no closed cells, found by their even spacing."""
    gm = drawn_map(hatched="vertical", road=True)
    d = ImageDraw.Draw(gm.image)
    extra = [(30, 150, 30, 260), (36, 150, 36, 260),                # a "11" and a leg that runs straight north
             (460, 120, 460, 300)]
    extra += [(x, 350, x, 385) for x in (200, 206, 221, 226, 244, 262, 268)]     # letters: many strokes, uneven
    for x0, y0, x1, y1 in extra:
        d.line([(x0, y0), (x1, y1)], fill=PURPLE, width=2)
    areas = hatch.detect(gm)
    assert len(areas) == 1 and areas[0]["lines"] == "vertical"
    found = raster(areas, (gm.H, gm.W))
    truth = np.zeros_like(found)
    truth[FIELD[1]:FIELD[3], FIELD[0]:FIELD[2]] = True
    assert (found & truth).sum() / (found | truth).sum() > 0.8
    assert 25 <= areas[0]["cells"] <= 31 and 7 < areas[0]["cell_m"] < 9
    # five lines are not a hatching yet
    few = drawn_map(hatched=False)
    for x in range(200, 230, 6):
        ImageDraw.Draw(few.image).line([(x, 150), (x, 250)], fill=PURPLE, width=2)
    assert hatch.detect(few) == []
    # crossed hatching is still read as before, once
    assert [r.get("lines") for r in hatch.detect(drawn_map())] == [None]


def raster(areas, shape):
    im = Image.new("1", shape[::-1], 0)
    for r in areas:
        ImageDraw.Draw(im).polygon(r["px"], fill=1)
    return np.array(im, bool)


@pytest.mark.parametrize("road", [False, True])
def test_hatched_field_is_found(road):
    gm = drawn_map(road=road)
    areas = hatch.detect(gm)
    assert len(areas) == 1
    found = raster(areas, (gm.H, gm.W))
    truth = np.zeros_like(found)
    truth[FIELD[1]:FIELD[3], FIELD[0]:FIELD[2]] = True
    assert (found & truth).sum() / (found | truth).sum() > 0.8
    assert areas[0]["cells"] >= 50 and 7 < areas[0]["cell_m"] < 11 and abs(areas[0]["area_m2"] - 38200) < 6000
    rings = hatch.to_latlon(gm, areas)
    assert len(rings) == 1 and all(49.99 < la < 50.01 and 17.99 < lo < 18.01 for la, lo in rings[0])


def test_course_alone_is_not_hatching():
    assert hatch.detect(drawn_map(hatched=False)) == []
    assert hatch.detect(drawn_map(hatched=False, road=True)) == []


@pytest.mark.parametrize("folder", ["azymut-e5", "azymut-e4", "pohora"])
def test_maps_without_hatching_give_nothing(folder):
    assert hatch.detect(GeoMap.from_kmz(inputs(folder)[0])) == []


@pytest.mark.slow
def test_petrvald_fields_and_the_road_are_out_of_bounds():
    """Petřvald H18 has five hatched fields and a hatched road along the southern edge of the map."""
    gm = GeoMap.from_kmz(inputs("petrvald")[0])
    areas = hatch.detect(gm)
    found = raster(areas, (gm.H, gm.W))
    inside = dict(big_field=(2425, 2150), field_at_17=(2640, 1920), field_by_the_pond=(1110, 1790),
                  field_by_the_railway=(2790, 1500), road_west=(700, 2820), road_east=(1900, 3495))
    for name, (u, v) in inside.items():
        assert found[v, u], name
    for name, (u, v) in dict(forest=(1500, 1500), control_17=(2520, 1790), finish=(2080, 2400),
                             legend=(4200, 1200), title=(1000, 350)).items():
        assert not found[v, u], name
    assert 5 <= len(areas) <= 12 and 45000 < sum(r["area_m2"] for r in areas) < 75000
    assert all(14 < r["cell_m"] < 17 for r in areas)


def test_route_keeps_out_of_an_area():
    cls, hgt = np.full((200, 300), T.FOREST, np.uint8), np.zeros((200, 300))
    m = SpeedModel()
    a, b = (40.0, 100.0), (260.0, 100.0)
    field = [(120.0, 40.0), (180.0, 40.0), (180.0, 160.0), (120.0, 160.0)]
    free, _ = Grid(cls, hgt, 1.5, m).route(a, b)
    # a crossing point (a level crossing of a railway nearby) does not open an area
    g = Grid(cls, hgt, 1.5, m, barriers=dict(forbidden=[], hard=[], crossings=[(150.0, 100.0)], areas=[field]))
    t, pts = g.route(a, b)
    assert np.isfinite(t) and t > free * 1.1
    assert not any(120 < u < 180 and 40 < v < 160 for u, v in pts)
    # a control inside the area is still reached: from the nearest place outside
    t, pts = g.route(a, (150.0, 100.0))
    assert np.isfinite(t) and pts
