"""Fenced ground and magnetic north lines on made-up pictures (night 25. 10., the race in Bělá): north lines that
lean in a turned picture are no streams, and every pen a route could cross is kept out of."""
import math

import numpy as np
from PIL import Image, ImageDraw

from oroute import mapdata
from oroute import relocate as R
from oroute import terrain as T
from oroute.routing import Grid
from oroute.speedmodel import SpeedModel

BLUE, BLACK = T.LINE["blue"], T.LINE["black"]
GREEN = (194, 225, 192)
YELLOW = (254, 219, 162)


# ---------------------------------------------------------------------------------------------- north lines
def north_sheet(angle=3.0, side=600, spacing=120):
    """Light green map with north lines leaning `angle` degrees (going down they move right, as on a map turned
    anticlockwise in its picture), broken for a name every 150 px, and a dashed stream across one of them.
    Returns the picture and the masks of what was drawn."""
    im = Image.new("RGB", (side, side), GREEN)
    d = ImageDraw.Draw(im)
    lines = Image.new("1", (side, side), 0)
    dl = ImageDraw.Draw(lines)
    t = math.tan(math.radians(angle))
    for x0 in range(-200, side + 200, spacing):
        for y in range(0, side, 150):            # 140 px of line, then a gap of 10 for a name
            p, q = (x0 + y * t, y), (x0 + (y + 140) * t, y + 140)
            d.line([p, q], fill=BLUE, width=2)
            dl.line([p, q], fill=1, width=2)
    stream = Image.new("1", (side, side), 0)
    ds = ImageDraw.Draw(stream)
    a, b = np.array([100.0, 520.0]), np.array([470.0, 130.0])
    n = int(np.hypot(*(b - a)))
    for s in range(0, n, 16):                    # dashes of 12 px, gaps of 4 (ISOM 306)
        p, q = a + (b - a) * s / n, a + (b - a) * min(s + 12, n) / n
        d.line([tuple(p), tuple(q)], fill=BLUE, width=2)
        ds.line([tuple(p), tuple(q)], fill=1, width=2)
    return np.asarray(im).copy(), np.array(lines, bool), np.array(stream, bool)


def test_leaning_north_lines_are_found_and_a_dashed_stream_across_them_stays():
    rgb, lines, stream = north_sheet()
    n = T.north_lines(rgb)
    assert abs(n["angle_deg"] + 3.0) < 0.15                  # north is 3 degrees left of up in the picture
    assert abs(n["spacing_px"] - 120 * math.cos(math.radians(3.0))) < 1.5
    north_only = lines & ~R._grow(stream, 4)
    assert (n["mask"] & north_only).sum() >= 0.95 * north_only.sum()
    blue = R.stream_mask(rgb)
    assert (blue & stream).sum() >= 0.95 * stream.sum()      # the stream, also where it crosses a north line
    assert (blue & north_only).sum() <= 0.03 * north_only.sum()
    # a bearing against the picture becomes one to the north of the map
    turned = R.north_bearings(dict(az=90.0, parts=[dict(back_az=10.0)]), n["angle_deg"])
    assert abs(turned["az"] - 93.0) < 0.2 and abs(turned["parts"][0]["back_az"] - 13.0) < 0.2
    # the old way (columns of pixels) found none of them: with the lines upright it still finds them all
    up, lines_up, _ = north_sheet(angle=0.0)
    m = T.north_lines(up)
    assert abs(m["angle_deg"]) < 0.05 and (m["mask"] & lines_up).sum() >= 0.95 * (lines_up & ~R._grow(stream, 4)).sum()


def test_a_blue_area_or_a_single_stream_makes_no_north_lines():
    rgb = np.full((400, 400, 3), GREEN, np.uint8)
    rgb[100:300, 100:140] = BLUE                    # a pond
    for v in range(150, 250, 3):
        rgb[v, 200:300] = BLUE                      # marsh
    rgb[:, 350:352] = BLUE                          # one straight ditch, but broken and only 60 % of the map
    rgb[160:320, 350:352] = GREEN
    assert not T.north_lines(rgb)["mask"].any()


# ---------------------------------------------------------------------------------------------- pens
class Sheet:
    """What mapdata.obstacles needs of a map."""

    def __init__(self, rgb, mpp):
        self.image, self.m_per_px_x = rgb, mpp
        self.H, self.W = rgb.shape[:2]


def pen(draw, pts, every=8, tick=4, width=3, gap=None, pairs=False):
    """A fence round the polygon pts with ticks standing inwards every `every` px. gap = (side, start, end): no
    line nor ticks there along that side (a gate). pairs: the ticks two by two (an impassable fence)."""
    cx, cy = np.mean(pts, axis=0)
    for k in range(len(pts)):
        p, q = np.array(pts[k], float), np.array(pts[(k + 1) % len(pts)], float)
        L = float(np.hypot(*(q - p)))
        along = (q - p) / L
        normal = np.array([-along[1], along[0]])
        if normal @ (np.array([cx, cy]) - p) < 0:
            normal = -normal
        cut = gap if gap and gap[0] == k else None
        pieces = [(0.0, L)] if not cut else [(0.0, cut[1]), (cut[2], L)]
        for s0, s1 in pieces:
            draw.line([tuple(p + along * s0), tuple(p + along * s1)], fill=BLACK, width=width)
            for s in np.arange(s0 + every / 2, s1 - 2, every):
                for o in ((0.0, 5.0) if pairs else (0.0,)):
                    f = p + along * (s + o)
                    draw.line([tuple(f), tuple(f + normal * (tick + width / 2))], fill=BLACK, width=width - 1)


def coarse_sheet(side=300):
    """A screenshot-like picture at 1 m per pixel: forest, the lines 3 px thick, slightly blurred."""
    im = Image.new("RGB", (side, side), (255, 255, 255))
    return im, ImageDraw.Draw(im)


def classes(rgb):
    cls = np.full(rgb.shape[:2], T.FOREST, np.uint8)
    cls[(rgb.astype(int).sum(-1) < 300)] = T.PATH        # every black line is a path to the terrain reader
    return cls


def blur(im):
    from PIL import ImageFilter
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.6))).copy()


def test_pens_with_a_gate_a_point_or_of_20000_m2_are_kept_out_of_and_a_loop_of_paths_is_not():
    mpp = 1.0
    im, d = coarse_sheet(420)
    d.polygon([(20, 40), (160, 40), (160, 100), (20, 100)], fill=YELLOW)
    pen(d, [(20, 40), (160, 40), (160, 100), (20, 100)], gap=(0, 65, 75))          # a gate of 10 m in the top
    d.polygon([(200, 30), (260, 120), (170, 120)], fill=YELLOW)
    pen(d, [(200, 30), (260, 120), (170, 120)])                                     # a triangle, its point narrow
    d.rectangle([40, 200, 200, 330], fill=YELLOW)
    pen(d, [(40, 200), (200, 200), (200, 330), (40, 330)], every=12)                # 160 x 130 m = 20 800 m2
    d.rectangle([260, 220, 380, 320], outline=BLACK, width=3)                       # a loop of tracks ...
    d.line([(320, 160), (320, 220)], fill=BLACK, width=3)                           # ... with tracks off it
    d.line([(380, 270), (415, 270)], fill=BLACK, width=3)
    rgb = blur(im)
    obs = mapdata.obstacles(Sheet(rgb, mpp), classes(rgb))
    b = obs["blocked"]
    assert b[70, 90] and b[70, 25] and b[70, 155] and b[42, 90]     # the pen with the gate, all of it
    assert b[110, 205] and b[55, 200] and b[45, 200]                # the triangle up to its point
    assert b[265, 120] and b[205, 120]                              # the large one, to its fence
    assert not b[270, 320] and not b[215, 320]                      # the loop of tracks is open
    assert len(obs["pens"]) == 3
    # a path 6 m outside a fence stays a path one can run along
    assert not b[100 + 3 + 6, 80]


def test_a_control_opens_only_the_pen_it_stands_in():
    mpp = 1.0
    im, d = coarse_sheet(300)
    for x0 in (40, 140):                                            # two pens side by side, 8 m apart
        d.polygon([(x0, 60), (x0 + 92, 60), (x0 + 92, 140), (x0, 140)], fill=YELLOW)
        pen(d, [(x0, 60), (x0 + 92, 60), (x0 + 92, 140), (x0, 140)])
    rgb = blur(im)
    sheet, cls = Sheet(rgb, mpp), classes(rgb)
    obs = mapdata.obstacles(sheet, cls, open_at=[(80.0, 100.0)])            # in the left one
    assert not obs["blocked"][100, 80] and obs["blocked"][100, 185] and len(obs["pens"]) == 1
    obs = mapdata.obstacles(sheet, cls, open_at=[(86.0, 150.0)])            # outside, 8 m below its fence
    assert obs["blocked"][100, 80] and obs["blocked"][100, 185]
    obs = mapdata.obstacles(sheet, cls, open_at=[(86.0, 141.0)])            # at its fence: that pen opens ...
    assert not obs["blocked"][141, 86] and not obs["blocked"][100, 80]
    assert obs["blocked"][100, 185]                                           # ... the one beside it does not


def test_an_impassable_fence_is_kept_out_of_and_a_fence_is_hard():
    mpp = 0.6
    im = Image.new("RGB", (420, 300), (255, 255, 255))
    d = ImageDraw.Draw(im)
    pen(d, [(20, 80), (400, 80)], every=30, tick=6, width=3, pairs=True)    # ticks in pairs: impassable (518)
    pen(d, [(20, 220), (400, 220)], every=30, tick=6, width=3)              # a fence (516)
    rgb = np.asarray(im).copy()
    obs = mapdata.obstacles(Sheet(rgb, mpp), classes(rgb))
    assert obs["blocked"][80, 200] and not obs["hard"][80, 200]
    assert obs["hard"][220, 200] and not obs["blocked"][220, 200]
    assert not obs["blocked"][80 - 12, 200]                        # 7 m beside it one runs on


def test_the_best_route_and_its_alternatives_go_round_a_pen():
    mpp = 1.0
    im, d = coarse_sheet(300)
    d.polygon([(110, 60), (190, 60), (190, 240), (110, 240)], fill=YELLOW)
    pen(d, [(110, 60), (190, 60), (190, 240), (110, 240)])
    rgb = blur(im)
    obs = mapdata.obstacles(Sheet(rgb, mpp), classes(rgb))
    cls = obs["cls"]
    cls[(cls == T.PATH)] = T.FOREST                          # (only the fence was drawn)
    barriers = dict(forbidden=[], hard=[], crossings=[], areas=[], mask=obs["blocked"], hard_mask=obs["hard"])
    g = Grid(cls, np.zeros(cls.shape), mpp, SpeedModel(), barriers=barriers)
    a, b = (40.0, 150.0), (260.0, 150.0)
    t, pts = g.route(a, b)
    inside = lambda p: 112 <= p[0] <= 188 and 62 <= p[1] <= 238
    assert np.isfinite(t) and not any(inside(p) for p in pts)
    alts = g.alternatives(a, b, k=2, best=(t, pts))
    assert alts and all(not any(inside(p) for p in q) for _, q in alts)
