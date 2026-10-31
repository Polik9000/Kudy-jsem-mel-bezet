"""Point symbols read from a drawn map picture (oroute/symbols.py): every kind at two resolutions, and the
things that look like symbols and are none."""
import collections

import numpy as np
from PIL import Image, ImageDraw

from oroute import symbols

BROWN, GREEN, BLUE, BLACK, GREY = (200, 104, 24), (48, 216, 24), (0, 208, 208), (0, 0, 0), (80, 72, 72)
# kind -> where it is drawn on the sheet (centre, in metres from the top left corner)
PLACES = {"knoll": (30, 30), "depression": (70, 30), "pit": (110, 30), "landform": (150, 30), "tree": (30, 80),
          "stand": (70, 80), "object": (110, 80), "boulder": (150, 80), "well": (30, 130), "water_pit": (70, 130)}


def sheet(mpp, extra=True):
    """A white sheet of 200 x 180 m with one symbol of every kind, each of the size ISOM gives it."""
    im = Image.new("RGB", (int(200 / mpp), int(180 / mpp)), "white")
    d = ImageDraw.Draw(im)
    s = max(2, int(round(2.7 / mpp)))

    def box(kind, w, h):
        x, y = PLACES[kind][0] / mpp, PLACES[kind][1] / mpp
        return [round(x - w / mpp / 2), round(y - h / mpp / 2), round(x + w / mpp / 2), round(y + h / mpp / 2)]
    d.ellipse(box("knoll", 7.5, 7.5), fill=BROWN)
    x0, y0, x1, y1 = box("depression", 12, 6)
    d.arc([x0, y0 - (y1 - y0), x1, y1], 0, 180, fill=BROWN, width=s)
    x0, y0, x1, y1 = box("pit", 10.5, 12)
    d.line([(x0 + s / 2, y0), ((x0 + x1) / 2, y1 - s / 2), (x1 - s / 2, y0)], fill=BROWN, width=s)
    x0, y0, x1, y1 = box("landform", 13.5, 11.5)
    d.polygon([(x0, y1), ((x0 + x1) / 2, y0), (x1, y1)], outline=BROWN, width=s)
    d.ellipse(box("tree", 13.5, 13.5), outline=GREEN, width=s)
    x0, y0, x1, y1 = box("stand", 15, 15)
    d.line([(x0, y0 + s / 2), (x1, y0 + s / 2)], fill=BLACK, width=s)
    d.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fill=BLACK, width=s)
    x0, y0, x1, y1 = box("object", 12, 12)
    d.line([(x0, y0), (x1, y1)], fill=BLACK, width=s)
    d.line([(x0, y1), (x1, y0)], fill=BLACK, width=s)
    d.ellipse(box("boulder", 7.5, 7.5), fill=BLACK)
    d.rectangle(box("well", 12, 12), outline=BLUE, width=s)
    x0, y0, x1, y1 = box("water_pit", 10.5, 12)
    d.line([(x0 + s / 2, y0), ((x0 + x1) / 2, y1 - s / 2), (x1 - s / 2, y0)], fill=BLUE, width=s)
    if extra:
        # things that are no symbols: a contour and a knoll sitting on it, the dashes of a path, a house, a
        # field of small dots, the trees of an orchard, a path lying askew, a word of the legend
        d.line([(0, 160 / mpp), (60 / mpp, 150 / mpp), (120 / mpp, 162 / mpp)], fill=BROWN, width=s)
        d.ellipse([round(58 / mpp), round(146 / mpp), round(65.5 / mpp), round(153.5 / mpp)], fill=BROWN)
        for x in range(110, 190, 12):
            d.line([(x / mpp, 110 / mpp), ((x + 8) / mpp, 114 / mpp)], fill=BLACK, width=s)
        d.rectangle([round(180 / mpp), round(20 / mpp), round(188 / mpp), round(28 / mpp)], fill=BLACK)
        for x in range(150, 190, 6):
            d.ellipse([round(x / mpp), round(140 / mpp), round((x + 3) / mpp), round(143 / mpp)], fill=BROWN)
        for x in range(120, 190, 14):
            for y in (155, 169):
                d.ellipse([round(x / mpp), round(y / mpp), round((x + 8) / mpp), round((y + 8) / mpp)], fill=GREEN)
        for x in (100, 118, 136):
            d.line([(x / mpp, 60 / mpp), ((x + 12) / mpp, 60 / mpp)], fill=GREY, width=s)
            d.line([((x + 6) / mpp, 60 / mpp), ((x + 6) / mpp, 72 / mpp)], fill=GREY, width=s)
    return np.asarray(im)


def test_every_symbol_is_read_from_a_sharp_map_and_nothing_else():
    mpp = 0.6
    found = symbols.find(sheet(mpp), mpp)
    assert collections.Counter(f["kind"] for f in found) == collections.Counter(list(PLACES))
    for f in found:
        x, y = PLACES[f["kind"]]
        assert abs(f["px"][0] * mpp - x) < 2.5 and abs(f["px"][1] * mpp - y) < 2.5, f
    # where symbols are not looked for (areas that must not be entered), none is found
    skip = np.zeros(sheet(mpp).shape[:2], bool)
    skip[:int(100 / mpp)] = True
    assert {f["kind"] for f in symbols.find(sheet(mpp), mpp, skip=skip)} == {"well", "water_pit"}


def test_coarse_map_gives_only_the_knoll_and_the_tree():
    """At 1.33 m per pixel a V is six pixels and a small thicket looks like a dot: only what stays readable."""
    mpp = 1.33
    found = symbols.find(sheet(mpp), mpp)
    assert sorted(f["kind"] for f in found) == ["knoll", "tree"]
    for f in found:
        x, y = PLACES[f["kind"]]
        assert abs(f["px"][0] * mpp - x) < 3 and abs(f["px"][1] * mpp - y) < 3


def test_letters_in_a_row_are_not_stands():
    mpp = 0.6
    im = Image.new("RGB", (300, 200), "white")
    d = ImageDraw.Draw(im)
    for x in (40, 75, 110):                       # "T T T" in the black of the map: a title, not three stands
        d.line([(x, 50), (x + 25, 50)], fill=BLACK, width=4)
        d.line([(x + 12, 50), (x + 12, 75)], fill=BLACK, width=4)
    d.line([(200, 120), (225, 120)], fill=BLACK, width=4)       # one T alone is a stand
    d.line([(212, 120), (212, 145)], fill=BLACK, width=4)
    found = symbols.find(np.asarray(im), mpp)
    assert [f["kind"] for f in found] == ["stand"] and abs(found[0]["px"][0] - 212) < 3
