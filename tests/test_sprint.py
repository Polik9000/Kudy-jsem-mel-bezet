"""Sprint maps (ISSprOM 2019) on a made-up picture: a grey building narrower than 9 m is a building, not a
path; a paved area and a passage under a roof are run like a street. A forest map has none of that grey."""
import numpy as np
from PIL import Image, ImageFilter

from oroute import terrain as T
from oroute.routing import Grid
from oroute.speedmodel import SpeedModel

MPP = 0.4                                     # m per pixel of a sprint map from Livelox (1:4 000)
H, W = 300, 400
PAVED, GREY, CANOPY, BLACK = (239, 204, 170), (128, 129, 132), (208, 210, 211), (35, 31, 32)


def sprint_picture():
    rgb = np.empty((H, W, 3), np.uint8)
    rgb[:] = PAVED
    rgb[40:260, 185:200] = BLACK                 # a house 6 m wide across the way, with its black outline ...
    rgb[42:258, 187:198] = GREY                  # ... and the grey inside
    rgb[100:200, 300:340] = BLACK                # a second, wider house
    rgb[102:198, 302:338] = GREY
    rgb[230:250, 40:90] = CANOPY                 # a passage under a roof
    return rgb


def test_a_narrow_grey_house_is_a_building_and_the_paving_is_run_like_a_street():
    rgb = sprint_picture()
    building, canopy = T.sprint_greys(rgb, MPP)
    assert building is not None and building[150, 192] and canopy[240, 60]
    cls = T.classify(rgb, 0, MPP)
    assert cls[150, 192] == T.BUILDING and cls[150, 186] == T.BUILDING     # inside and on the outline
    assert cls[150, 320] == T.BUILDING
    assert cls[150, 100] == T.PATH and cls[240, 60] == T.PATH             # paved area, passage
    assert not (cls[40:260, 185:200] == T.PATH).any()                      # the house is no path


def test_the_best_route_goes_round_the_house_not_through_it():
    rgb = sprint_picture()
    cls = T.classify(rgb, 0, MPP)
    grid = Grid(cls, np.zeros((H, W), np.float32), MPP, SpeedModel(), step=2)
    t, pts = grid.route((120.0, 150.0), (260.0, 150.0))
    assert np.isfinite(t)
    vs = [v for u, v in pts if 183 <= u <= 202]
    assert vs and all(v < 50 or v > 250 for v in vs)       # past the house at either end (a grid cell may cut its corner)


def test_a_forest_map_is_no_sprint_map():
    rgb = np.full((H, W, 3), 255, np.uint8)
    rgb[:, :150] = (254, 219, 162)                                       # rough open land
    rgb[140:146, :] = BLACK                                              # a road ...
    for c in range(20, W, 30):
        rgb[:, c:c + 2] = BLACK                                          # ... and many paths
    soft = np.asarray(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(1.2)))   # antialiased edges: grey
    assert T.sprint_greys(soft, 1.33) == (None, None)
    assert not T.paved(np.array([[PAVED]], np.uint8))[0, 0]               # the sprint brown counts only on a sprint map
    assert T.paved(np.array([[PAVED]], np.uint8), sprint=True)[0, 0]
    assert not T.paved(np.array([[(254, 219, 162)]], np.uint8), sprint=True)[0, 0]   # rough open is not paved


def walled_picture():
    """A sprint map with a yard closed in by a thick wall (ISSprOM 515) except for a gate, a low wall drawn with
    dots (513) across a second way, and a dashed path (no wall) across a third."""
    rgb = np.empty((H, W, 3), np.uint8)
    rgb[:] = PAVED
    rgb[10:30, 10:40] = BLACK                    # one grey house, so that the map is read as a sprint map
    rgb[12:28, 12:38] = GREY
    rgb[100:160, 300:380] = BLACK
    rgb[102:158, 302:378] = GREY
    rgb[60:64, 100:250] = BLACK                  # the yard: a wall 1.6 m thick (4 px) ...
    rgb[200:204, 100:250] = BLACK
    rgb[60:204, 100:104] = BLACK
    rgb[60:120, 246:250] = BLACK                 # ... with a gate 12 m wide in its east side (v 120 to 150)
    rgb[150:204, 246:250] = BLACK
    rgb[229:232, 20:200] = BLACK                 # a low wall 1.2 m thick (3 px) ...
    for u in range(25, 200, 20):
        rgb[233:238, u - 2:u + 3] = BLACK        # ... with its dots, 2 m across, beside it
    for u in range(20, 200, 15):
        rgb[270:272, u:u + 10] = BLACK           # a dashed path: dashes 4 m long
    return np.asarray(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(0.6)))


def test_a_thick_wall_is_a_building_a_dotted_one_a_low_wall_and_dashes_no_wall():
    rgb = walled_picture()
    building, _ = T.sprint_greys(rgb, MPP)
    hard, low = T.sprint_walls(rgb, building, MPP)
    assert hard[62, 170] and hard[130, 102] and not hard[135, 248]        # the wall, but not its gate
    assert low[231, 100] and not hard[231, 100]
    assert not hard[271, 60] and not low[271, 60]                         # the dashes are no wall
    assert not hard[20, 25] and not low[20, 25]                           # nor the outline of a house
    cls = T.classify(rgb, 0, MPP)
    assert cls[62, 170] == T.BUILDING and cls[130, 102] == T.BUILDING
    assert cls[135, 248] != T.BUILDING


def test_a_wall_on_a_blurred_screenshot_stays_a_wall_when_the_blur_is_known():
    """A map cut out of a screenshot the browser zoomed is blurrier than the export: a wall reads thinner than it is
    and drops under the 1.25 m of a wall, unless the extra blur (GeoMap.blur_m, oroute/pair.py) is taken into
    account. (Only in part: the faint tails of the blurred ink are lost under the threshold of ink, so a wall just
    over 1.25 m can still be lost.) A dashed path stays no wall either way."""
    mpp = 0.2                                                              # a sharp sprint map (SZL has 0.27)
    rgb = np.empty((H, W, 3), np.uint8)
    rgb[:] = 255                                                           # open white ground (on the light brown
    # of a paving the blurred edge of a line is no grey, and some of its ink is lost: see docs/co-zbyva.md)
    rgb[150:250, 280:390] = BLACK                                          # a grey house: a sprint map
    rgb[152:248, 282:388] = GREY
    rgb[77:85, 20:260] = BLACK                                             # a wall 1.6 m thick (8 px)
    for u in range(20, 260, 30):
        rgb[270:274, u:u + 20] = BLACK                                     # a dashed path 0.8 m (4 m dashes)
    sharp = np.asarray(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(0.6)))
    extra = 0.25                                                           # metres: a screenshot zoomed 1.5 times
    blurred = np.asarray(Image.fromarray(sharp).filter(ImageFilter.GaussianBlur(extra / mpp)))
    building, _ = T.sprint_greys(sharp, mpp)
    assert T.sprint_walls(sharp, building, mpp)[0][80, 150]
    assert not T.sprint_walls(blurred, building, mpp)[0][80, 150]          # lost without knowing the blur
    hard, low = T.sprint_walls(blurred, building, mpp, blur_m=extra)
    assert hard[80, 150] and not hard[272, 30] and not low[272, 30]


def test_the_route_into_the_yard_goes_through_its_gate_and_a_low_wall_costs_a_few_seconds():
    from oroute import mapdata

    class Map:
        image = walled_picture()
        m_per_px_x = MPP
    cls = T.classify(Map.image, 0, MPP)
    obs = mapdata.obstacles(Map, cls)
    assert obs["walls"][62, 170] and obs["climb"][231, 100] and not obs["climb"][271, 60]
    assert obs["cls"][231, 100] != T.PATH                                  # a low wall is no path
    flat = np.zeros((H, W), np.float32)
    barriers = dict(forbidden=[], hard=[], crossings=[], areas=[], mask=obs["blocked"], hard_mask=obs["hard"],
                    wall_mask=obs["walls"], climb_mask=obs["climb"])
    for step in (2, 4):                          # a coarse grid must not jump the wall either
        grid = Grid(obs["cls"], flat, MPP, SpeedModel(), step=step, barriers=barriers)
        t, pts = grid.route((60.0, 130.0), (170.0, 130.0))                 # from outside the west wall into the yard
        assert np.isfinite(t)
        assert max(u for u, v in pts) > 240                                # round to the gate in the east
        assert all(not (98 <= u <= 106) for u, v in pts if 64 <= v <= 200)   # never across the west wall
    grid = Grid(obs["cls"], flat, MPP, SpeedModel(), step=2, barriers=barriers)
    over, _ = grid.route((100.0, 220.0), (100.0, 245.0))                  # straight over the low wall
    free = Grid(obs["cls"], flat, MPP, SpeedModel(), step=2, barriers=dict(barriers, climb_mask=None))
    plain, _ = free.route((100.0, 220.0), (100.0, 245.0))
    assert 3.0 <= over - plain <= 9.0


def test_a_control_on_a_wall_is_reached_from_either_side():
    from oroute import mapdata

    class Map:
        image = walled_picture()
        m_per_px_x = MPP
    cls = T.classify(Map.image, 0, MPP)
    corner = (102.0, 62.0)                                                 # the north-west corner of the yard wall
    shut, open_ = mapdata.obstacles(Map, cls), mapdata.obstacles(Map, cls, open_at=[corner])
    assert shut["walls"][62, 102] and shut["cls"][62, 102] == T.BUILDING
    assert not open_["walls"][62, 102] and open_["cls"][62, 102] != T.BUILDING
    assert open_["walls"][62, 170] and open_["walls"][130, 102]           # the rest of the wall stays
    flat = np.zeros((H, W), np.float32)
    o = open_
    grid = Grid(o["cls"], flat, MPP, SpeedModel(), step=2,
                barriers=dict(forbidden=[], hard=[], crossings=[], areas=[], mask=o["blocked"], hard_mask=o["hard"],
                              wall_mask=o["walls"], climb_mask=o["climb"]))
    t_out, _ = grid.route((80.0, 40.0), corner)                           # from outside the yard
    t_in, _ = grid.route((130.0, 90.0), corner)                           # from inside it
    assert t_out < 15 and t_in < 15, (t_out, t_in)
