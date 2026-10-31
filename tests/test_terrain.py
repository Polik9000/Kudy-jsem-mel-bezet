"""Reading the terrain from a drawn piece of map (oroute/terrain.py): water with a bank line."""
import numpy as np

from oroute import terrain as T
from oroute.routing import Grid, route_metrics
from oroute.speedmodel import SpeedModel

BLUE, BLACK = T.LINE["blue"], T.LINE["black"]
GREEN = (194, 225, 192)      # light green all over: white would be read as the margin of the sheet (out of bounds)


def sheet(side):
    return np.full((side, side, 3), GREEN, np.uint8)


def pond(rgb, v0, v1, u0, u1, bank=3):
    """A pond drawn as ISOM 301: blue with a black bank line around it."""
    rgb[v0 - bank:v1 + bank, u0 - bank:u1 + bank] = BLACK
    rgb[v0:v1, u0:u1] = BLUE


def test_narrow_pond_with_a_bank_line_is_water_and_its_bank_is_no_path():
    mpp = 0.6                                        # as sharp as the map of Petřvald
    rgb = sheet(800)
    pond(rgb, 394, 406, 300, 500)                    # 7 m wide, 120 m long: too narrow for "wide blue is water"
    rgb[350:353, 200:600] = BLACK                    # a path 25 m north of it
    rgb[430:433, 200:600] = BLUE                     # a stream south of it, no bank line
    for v in range(500, 540, 6):                     # the dashes of a marsh
        rgb[v:v + 2, 300:500] = BLUE
    cls = T.classify(rgb, m_per_px=mpp)
    assert (cls[391:409, 303:497] == T.WATER).all()  # the pond with its bank (but for the square corners drawn here)
    assert not (cls[380:420, 285:515] == T.PATH).any()
    assert (cls[350:353, 210:590] == T.PATH).all()   # the path stays a path ...
    assert not (cls[425:438, 200:600] == T.WATER).any()      # ... and the stream and the marsh are no ponds
    assert not (cls[495:545, 300:500] == T.WATER).any() and (cls[505:535, 320:480] == T.MARSH).mean() > 0.5
    # the best route from one side of the pond to the other goes round its end, not over the bank
    hgt, m = np.zeros(cls.shape), SpeedModel()
    a, b = (400.0, 380.0), (400.0, 420.0)
    t, pts = Grid(cls, hgt, mpp, m, box=(160, 160, 640, 640)).route(a, b)
    assert np.isfinite(t) and min(abs(u - 400) for u, v in pts if 392 <= v <= 408) > 95
    # (the line between two cells of the grid may clip a corner of the bank: a sample or two, not the 11 m across)
    assert route_metrics([a] + pts + [b], cls, hgt, mpp, m)["mix"].get(T.NAMES[T.WATER], 0.0) <= 4.0


def test_a_path_along_a_pond_stays_and_blue_without_a_bank_is_judged_by_its_width():
    rgb = sheet(800)
    pond(rgb, 390, 410, 300, 500)
    rgb[370:373, 200:600] = BLACK                    # a path along the shore, 8 m from the bank (a dam)
    rgb[480:486, 300:500] = BLUE                     # blue 3.6 m wide with no bank line: a wide stream
    cls = T.classify(rgb, m_per_px=0.6)
    assert (cls[370:373, 210:590] == T.PATH).all() and (cls[388:412, 304:496] == T.WATER).all()
    assert not (cls[475:490, 300:500] == T.WATER).any()
    # at the resolution of a Livelox export a pond of the same size is 5 pixels wide: still a pond
    rgb = sheet(400)
    pond(rgb, 198, 203, 150, 250, bank=2)
    cls = T.classify(rgb, m_per_px=1.33)
    assert (cls[197:204, 150:250] == T.WATER).all() and not (cls[185:215, 140:260] == T.PATH).any()


def test_a_row_of_dots_is_no_path_and_a_dashed_path_is_one():
    rgb = sheet(300)
    for u in range(40, 260, 5):                      # the dotted edge of a stand (ISOM 416): dots 2 px, 5 px apart
        rgb[100:102, u:u + 2] = BLACK
    for u in range(40, 260, 10):                     # a footpath: dashes of 8 px with gaps of 2
        rgb[200:202, u:u + 8] = BLACK
    rgb[150:153, 40:260] = BLACK                     # a track: one solid line
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    assert not (cls[95:107] == T.PATH).any()
    assert (cls[200:202, 80:220] == T.PATH).mean() > 0.9 and (cls[150:153, 80:220] == T.PATH).all()
    # the same on a picture twice as sharp: the dots are twice as large there, and still dots
    big = sheet(600)
    for u in range(80, 520, 10):
        big[200:204, u:u + 4] = BLACK
    for u in range(80, 520, 20):
        big[400:404, u:u + 16] = BLACK
    cls = T.classify(big, m_per_px=T.REF_M_PER_PX / 2)
    assert not (cls[190:214] == T.PATH).any() and (cls[400:404, 120:480] == T.PATH).mean() > 0.9


def test_open_water_has_no_rim_of_marsh_and_marsh_hatching_stays_marsh():
    rgb = sheet(320)
    pond(rgb, 100, 108, 80, 140)                     # a narrow pond with a bank line
    rgb[200:230, 80:140] = BLUE                      # a wide pond without one
    for v in range(120, 200, 3):                     # marsh: thin blue lines 3 px apart
        rgb[v, 170:245] = BLUE
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    around = np.zeros(cls.shape, bool)
    around[88:120, 68:152] = around[188:242, 68:152] = True
    assert not ((cls == T.MARSH) & around).any()
    assert (cls[104, 85:135] == T.WATER).all() and (cls[215, 85:135] == T.WATER).all()
    assert (cls[130:190, 180:235] == T.MARSH).mean() > 0.9


OLIVE, PAVED = (171, 165, 54), (226, 170, 125)


def settlement(mpp):
    """A settlement (ISOM 520, olive) with what is drawn inside one: a paved street right through it (light
    brown between two black edges), the outline of a house, the fences between the plots (thin black lines,
    one from the northern edge down to the street, one from the street to the southern edge) and a track
    outside along its western side. Sizes in pixels of a map with 1.33 m per pixel, scaled to mpp."""
    k = T.REF_M_PER_PX / mpp
    n = lambda a: int(round(a * k))
    rgb = sheet(n(400))
    rgb[n(100):n(300), n(100):n(300)] = OLIVE
    rgb[n(193):n(207), n(60):n(340)] = BLACK         # the street, 13 m wide with its two edges ...
    rgb[n(195):n(205), n(60):n(340)] = PAVED
    rgb[n(130):n(160), n(150):n(190)] = BLACK        # the outline of a house: a thin line around olive
    rgb[n(132):n(158), n(152):n(188)] = OLIVE
    rgb[n(100):n(193), n(240):n(242)] = BLACK        # a fence between two plots, north of the street
    rgb[n(207):n(300), n(160):n(162)] = BLACK        # ... and one south of it
    rgb[n(40):n(360), n(70):n(72)] = BLACK           # a track outside, 40 m west of the settlement
    return rgb, n


def test_inside_a_settlement_only_the_paved_street_can_be_run():
    for mpp in (T.REF_M_PER_PX, 0.6):
        rgb, n = settlement(mpp)
        cls = T.classify(rgb, m_per_px=mpp)
        inside = np.zeros(cls.shape, bool)
        inside[n(100):n(300), n(100):n(300)] = True
        street = np.zeros(cls.shape, bool)
        street[n(190):n(210)] = True
        # the fences between the plots and the outline of the house are no paths: they are out of bounds like
        # the ground they stand on, and so no black inside the settlement is a path but the edges of the street
        assert not ((cls == T.PATH) & inside & ~street).any()
        assert (cls[n(102):n(190), n(240):n(242)] == T.OOB).all() and (cls[n(210):n(298), n(160):n(162)] == T.OOB).all()
        assert (cls[n(130):n(160), n(150):n(190)] == T.OOB).all()
        # the street stays what it was, and the track outside is a path as before
        assert np.isin(cls[n(196):n(204), n(105):n(295)], (T.OPEN, T.ROUGH_OPEN, T.PATH)).all()
        assert (cls[n(80):n(320), n(70):n(72)] == T.PATH).all()
        hgt, m = np.zeros(cls.shape), SpeedModel()
        g = Grid(cls, hgt, mpp, m, step=max(2, int(round(2 * T.REF_M_PER_PX / mpp))))
        # along the street right through the settlement ...
        t, pts = g.route((n(80), n(200)), (n(320), n(200)))
        assert np.isfinite(t) and all(n(190) <= v <= n(210) for u, v in pts if n(105) < u < n(295))
        # ... but not across it along the fences of the plots: the way from north to south goes round
        t, pts = g.route((n(200), n(70)), (n(200), n(330)))
        assert np.isfinite(t) and not any(n(104) < u < n(296) and n(104) < v < n(296) for u, v in pts)


def test_a_map_drawn_up_to_the_edge_of_its_picture_is_not_out_of_bounds_along_that_edge():
    rgb = sheet(400)                                 # the map fills the whole picture, as a sprint map often does
    rgb[200:203, 0:400] = BLACK                      # a path that runs out of the picture on both sides
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    assert not (cls == T.OOB).any()
    assert (cls[200:203, 2:398] == T.PATH).all() and cls[5, 5] == T.SLOW and cls[394, 200] == T.SLOW
    t, pts = Grid(cls, np.zeros(cls.shape), T.REF_M_PER_PX, SpeedModel()).route((10.0, 30.0), (390.0, 30.0))
    assert np.isfinite(t) and max(v for u, v in pts) < 60         # straight along the upper edge, not round a band
    # the white margin around a map that does not fill its picture stays out of bounds, as it was
    rgb = np.full((400, 400, 3), 255, np.uint8)
    rgb[100:300, 100:300] = GREEN
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    assert (cls[:90] == T.OOB).all() and (cls[:, 310:] == T.OOB).all() and (cls[110:290, 110:290] == T.SLOW).all()
    # a map that ends 53 m from the edge of its picture behind a white margin is map up to its last colour,
    # and the margin beyond it is not (it lost a band 85 m wide along the edge of the picture)
    rgb = np.full((400, 400, 3), 255, np.uint8)
    rgb[100:300, 100:360] = GREEN
    rgb[200:203, 100:360] = BLACK
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    assert (cls[110:290, 110:356] != T.OOB).all() and (cls[200:203, 110:354] == T.PATH).all()
    assert (cls[:, 368:] == T.OOB).all() and (cls[:90] == T.OOB).all()
    # ... and so does the header Livelox prints above the map
    rgb = sheet(400)
    cls = T.classify(rgb, header_px=100, m_per_px=T.REF_M_PER_PX)
    assert (cls[:100] == T.OOB).all() and (cls[102:398, 2:398] == T.SLOW).all()
    # a sheet with a frame line and print in its white margin: the margin is not closed in by them
    rgb = np.full((600, 600, 3), 255, np.uint8)
    rgb[150:450, 150:450] = GREEN
    rgb[6:9, 6:594] = rgb[591:594, 6:594] = rgb[6:594, 6:9] = rgb[6:594, 591:594] = BLACK    # the frame
    rgb[500:520, 100:400] = (90, 90, 90)                                                     # a line of grey print
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    assert (cls[20:130, 20:580] == T.OOB).all() and (cls[160:440, 160:440] == T.SLOW).all()


def test_a_north_line_across_a_pond_does_not_open_a_way_through_it():
    rgb = sheet(400)
    rgb[180:230, 120:280] = BLUE                     # a pond 213 m wide and 66 m from north to south ...
    rgb[:, 199:201] = BLUE                           # ... with a magnetic north line right across the map and it
    rgb[300:303, 40:360] = BLACK                     # a path south of the pond, which the north line crosses too
    cls = T.classify(rgb, m_per_px=T.REF_M_PER_PX)
    assert (cls[182:228, 122:278] == T.WATER).all()  # no strip of anything else through the water
    assert not (cls[:170, 195:205] == T.WATER).any() and not (cls[240:, 195:205] == T.WATER).any()
    assert (cls[300:303, 60:340] == T.PATH).mean() > 0.95
    # the way from the north shore to the south shore goes round the pond, not along the north line
    t, pts = Grid(cls, np.zeros(cls.shape), T.REF_M_PER_PX, SpeedModel()).route((200.0, 160.0), (200.0, 250.0))
    assert np.isfinite(t) and not any(125 < u < 275 and 185 < v < 225 for u, v in pts)
