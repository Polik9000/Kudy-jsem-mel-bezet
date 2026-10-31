"""Point symbols of an orienteering map read from the picture of the map without course: a knoll, a boulder,
a distinct tree, a small depression ... by their colour, size and shape. No recognition of text or of
control descriptions; rules and geometry only.

A symbol covers the same ground at every map scale (its "footprint", ISOM 2017-2 part 2.11.2: the symbols of
a 1:10 000 map are those of 1:15 000 enlarged), so the sizes below are in metres and one set of rules reads
maps of any resolution. The numbers are those of ISOM 2017-2 (the Czech edition of ČSOS):

  109 small knoll            brown dot, 7.5 m          "knoll"
  111 small depression       brown U, 12 x 6 m          "depression"
  112 pit                    brown V, 10.5 x 12 m       "pit"
  115 prominent landform     brown triangle, 13.5 m     "landform"
  204/205 boulder            black dot, 6 to 9 m        "boulder"
  303 waterhole              blue V, 10.5 x 12 m        "water_pit"
  311 well, fountain, tank   blue square, 12 m          "well"
  417 prominent large tree   green ring, 13.5 m         "tree"
  525 small tower, stand     black T, 15 m              "stand"
  530/531 man-made object    black ring or cross, 12 m  "object"

A symbol is only taken when it stands alone: one connected patch of its colour of the right size. One that
touches a contour, a path or another symbol is missed; a false one is worse than a missing one. From a map
with more than SHARP_M_PER_PX metres per pixel only the knoll and the tree are read (there a V is six pixels,
and a small thicket looks like the green dot); the rest needs a sharp picture.
Not read at all: 527 feeder, 526 cairn, 312 spring, 207 boulder cluster, 110 elongated knoll, and 418
prominent bush (a green dot: on the one sharp map at hand every green dot found was a tree of an orchard,
symbol 413, which is an area and no place).
Black symbols that stand in a row with others of their height are letters of the title or the legend of the
map, not symbols.

How well this works on the four races of data/ is in docs/validace.md.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

SHARP_M_PER_PX = 0.9     # all symbols but the knoll and the tree are read only from pictures at least this sharp
COARSE = ("knoll", "tree")
TOL = (0.68, 1.4)        # a symbol may be this much smaller or larger than its footprint
KNOLL_MIN_M = 6.0        # a knoll is at least this far across: smaller brown dots are other symbols (broken
                         # ground, the dots of a small erosion gully)
DOT_FILL = 0.62          # a dot fills at least this share of its bounding box (a disc: 0.79) ...
SQUARE_FILL = 0.92       # ... and less than this (a small building is a full square)
DISC = 0.86              # on a sharp picture a dot agrees this much with a disc of its area (a square: 0.84)
HOLE = 0.16              # a ring has a hole of at least this share of its bounding box ...
TRIANGLE_HOLE = 0.03     # ... the outline of a triangle a smaller one (as drawn by ISOM: 0.05)
STROKE_FILL = 0.6        # a symbol of strokes fills less than this of its bounding box
MATCH = 0.5              # ... and agrees with its drawn shape at least this much (intersection over union)
STROKE_M = 2.7           # how thick the strokes of a symbol are drawn (0.18 mm at 1:15 000)
SHAPES = "UVTX"

# colour -> (kind, footprint width m, height m, what it is: dot | ring | triangle | a stroke shape)
RULES = {
    "brown": [("knoll", 7.5, 7.5, "dot"), ("landform", 13.5, 11.5, "triangle"), ("depression", 12.0, 6.0, "U"),
              ("pit", 10.5, 12.0, "V")],
    "green": [("tree", 13.5, 13.5, "ring")],
    "blue": [("well", 12.0, 12.0, "ring"), ("water_pit", 10.5, 12.0, "V")],
    "black": [("boulder", 7.5, 7.5, "dot"), ("object", 12.0, 12.0, "ring"), ("stand", 15.0, 15.0, "T"),
              ("object", 12.0, 12.0, "X")],
}


def colours(rgb):
    """Boolean masks of the four colours symbols are drawn in: brown, green (the saturated green of symbols
    and stripes, not the fills of vegetation), blue, black."""
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    return dict(brown=(r > 150) & (g > 60) & (g < 140) & (b < 90) & (r - b > 90),
                green=(g > 150) & (r < 90) & (b < 110),
                blue=(b > 180) & (r < 120),
                black=((r + g + b) < 150) & (mx - mn < 45))   # the black of the map, not the grey of its legend


def _shape(kind, w, h, s):
    """A stroke symbol drawn into a box of w x h pixels with strokes s pixels thick (boolean)."""
    im = Image.new("1", (w, h), 0)
    d = ImageDraw.Draw(im)
    r, b, a = w - 1, h - 1, s / 2
    if kind == "U":                      # the lower half of a ring
        d.arc([0, -b, r, b], 0, 180, fill=1, width=s)
    elif kind == "V":
        d.line([(a, 0), (r / 2, b - a), (r - a, 0)], fill=1, width=s)
    elif kind == "T":
        d.line([(0, a), (r, a)], fill=1, width=s)
        d.line([(r / 2, 0), (r / 2, b)], fill=1, width=s)
    elif kind == "X":
        d.line([(a / 2, a / 2), (r - a / 2, b - a / 2)], fill=1, width=s)
        d.line([(a / 2, b - a / 2), (r - a / 2, a / 2)], fill=1, width=s)
    return np.array(im, bool)


def _match(part, kinds, mpp):
    """The stroke shape of `kinds` a patch looks like most, when it agrees with it at least MATCH and clearly
    more than with the others; else None. The shapes are drawn at the size of the patch."""
    s = max(2, int(round(STROKE_M / mpp)))
    iou = {}
    for k in kinds:
        shape = _shape(k, part.shape[1], part.shape[0], s)
        iou[k] = (part & shape).sum() / max((part | shape).sum(), 1)
    order = sorted(iou, key=iou.get, reverse=True)
    best = order[0]
    if iou[best] >= MATCH and (len(order) == 1 or iou[best] >= iou[order[1]] + 0.08):
        return best
    return None


def _disc(part):
    """How much a patch agrees with a disc of the same area around its centre (intersection over union)."""
    v, u = np.nonzero(part)
    yy, xx = np.mgrid[0:part.shape[0], 0:part.shape[1]]
    disc = (xx - u.mean()) ** 2 + (yy - v.mean()) ** 2 <= part.sum() / np.pi
    return (part & disc).sum() / max((part | disc).sum(), 1)


def _triangle(part):
    """An outline that is wide at the bottom and narrow at the top."""
    q = max(1, part.shape[0] // 4)
    top, low = part[:q].any(0).nonzero()[0], part[-q:].any(0).nonzero()[0]
    return len(top) > 0 and len(low) > 0 and np.ptp(top) < 0.5 * np.ptp(low)


def _strokes(part, kind):
    """What the agreement with the drawn shape does not tell: a cross has ink in all four corners (one dash of
    a path lying askew has it in two), a T has its bar right across the top and only the stem below (the
    arrow of another symbol comes to a point at the top)."""
    h, w = part.shape
    if kind == "X":
        a, b = max(1, h // 3), max(1, w // 3)
        return bool(part[:a, :b].any() and part[:a, -b:].any() and part[-a:, :b].any() and part[-a:, -b:].any())
    if kind == "T":
        top = part[:max(1, h // 4)].any(0).nonzero()[0]
        return bool(len(top) and np.ptp(top) >= 0.8 * (w - 1) and part[h // 2:].any(0).sum() <= 0.45 * w)
    return True


def find(rgb, mpp, header_px=0, skip=None):
    """The point symbols of a map picture: [dict(kind, px=(u, v), size=(width m, height m))].
    rgb: H x W x 3 uint8, mpp: metres per pixel, header_px: rows at the top that are not map, skip: boolean
    mask of where not to look (beyond the edge of the map, where its title and legend are; areas that must
    not be entered, where small black squares are houses)."""
    sharp = mpp <= SHARP_M_PER_PX
    masks = colours(rgb)
    H, W = rgb.shape[:2]
    out = []
    for colour, mask in masks.items():
        mask = mask.copy()
        mask[:header_px] = False
        lab, n = ndi.label(mask, structure=np.ones((3, 3)))
        rules = [r for r in RULES[colour] if sharp or r[0] in COARSE]
        if not n or not rules:
            continue
        biggest = max(max(w, h) for _, w, h, _ in rules) * TOL[1] / mpp
        boxes = ndi.find_objects(lab)
        # top, bottom, left, right of every patch, to tell letters (patches in a row) from symbols
        tb = np.array([(s[0].start, s[0].stop, s[1].start, s[1].stop) for s in boxes]) if colour == "black" else None
        for k, sl in enumerate(boxes, 1):
            hp, wp = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if max(hp, wp) > biggest or min(hp, wp) < 3:
                continue
            part = lab[sl] == k
            if skip is not None and skip[sl][part].any():
                continue
            w, h, area = wp * mpp, hp * mpp, float(part.sum())
            hole = float(ndi.binary_fill_holes(part).sum() - area) / (wp * hp)
            fill = area / (wp * hp)
            fits = [r for r in rules if TOL[0] * r[1] <= w <= TOL[1] * r[1] and TOL[0] * r[2] <= h <= TOL[1] * r[2]]
            if fits and tb is not None:
                tall = tb[:, 1] - tb[:, 0]
                level = np.abs((tb[:, 0] + tb[:, 1]) / 2 - (sl[0].start + sl[0].stop) / 2) < 0.4 * hp
                side = np.maximum(tb[:, 2] - sl[1].stop, sl[1].start - tb[:, 3])      # gap to the left or right
                if (level & (tall > 0.6 * hp) & (tall < 1.6 * hp) & (side >= 0) & (side < 1.2 * wp)).any():
                    continue
            strokes = [r[3] for r in fits if r[3] in SHAPES]
            looks = _match(part, strokes, mpp) if strokes and hole == 0 and fill < STROKE_FILL else None
            for kind, _, _, what in fits:
                if what == "dot":
                    ok = DOT_FILL <= fill < SQUARE_FILL and hole == 0 and (kind != "knoll" or min(w, h) >= KNOLL_MIN_M) \
                        and max(w, h) <= 1.35 * min(w, h) \
                        and (not sharp or _disc(part) >= DISC)
                    if ok and colour != "black":
                        # a piece of a contour between two paths is a brown patch of this size too: a real
                        # dot has no black line right next to it
                        a, b = max(sl[0].start - 1, 0), max(sl[1].start - 1, 0)
                        c, e = min(sl[0].stop + 1, H), min(sl[1].stop + 1, W)
                        own = ndi.binary_dilation(lab[a:c, b:e] == k, structure=np.ones((3, 3)))
                        ok = not (own & masks["black"][a:c, b:e]).any()
                elif what == "ring":
                    ok = hole >= HOLE and max(w, h) <= 1.45 * min(w, h)
                elif what == "triangle":
                    ok = hole >= TRIANGLE_HOLE and _triangle(part)
                else:
                    ok = looks == what and _strokes(part, what)
                if ok:
                    out.append(dict(kind=kind, px=(sl[1].start + (wp - 1) / 2, sl[0].start + (hp - 1) / 2), size=(w, h)))
                    break
    return out
