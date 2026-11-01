"""The app logo and icons: "Kudy?". The straight purple course line from start (triangle) to control (circle) and
next to it the runner's red GPS track bent into a question mark: the way I ran against the way I could have run.

One geometry feeds both outputs, so the SVG on the web and the icons in the installers look the same and no
binary picture has to live in the repo:
    python desktop/icons.py build/icons      app.png, app.ico (Windows), app.icns (macOS)
    python desktop/icons.py --svg            writes webapp/static/ob-logo.svg and docs/logo.svg
"""
import math
import os
import sys

from PIL import Image, ImageDraw

PURPLE = "#C2185B"          # course overprint, the same as --accent on the download page
RED = "#E0262B"             # the GPS track
TILE = "#ffffff"
EDGE = "#d5dcd8"            # thin edge so the white tile is visible on a white desktop
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# all in a 256 x 256 box
DX = 6                                  # the drawing is a bit heavier on the left (triangle), so move it right
ARC_C, ARC_R = (128 + DX, 106), 44      # the bow of the question mark
ARC_FROM, ARC_TO = 167, 421.6           # degrees, y down, clockwise; the end is where the bow's tangent meets the stem
HOOK_CTRL, HOOK_END = (128 + DX, 156), (128 + DX, 174)
ROUTE_W = 15                            # diameter of one GPS point
ROUTE_STEP = 19                         # distance between the points along the track
LINE_W = 6                              # the straight course line
CONTROL_C, CONTROL_R, CONTROL_W = (128 + DX, 214), 17, 9
TRI_W = 9


def _arc_point(deg):
    a = math.radians(deg)
    return ARC_C[0] + ARC_R * math.cos(a), ARC_C[1] + ARC_R * math.sin(a)


def _triangle():
    x, y = _arc_point(ARC_FROM)
    return [(x, y - 21), (x + 22, y + 17), (x - 22, y + 17)]


def svg(tile=True):
    """The logo as SVG text. tile=False: only the purple course (for a header that has its own background)."""
    (sx, sy), (ex, ey) = _arc_point(ARC_FROM), _arc_point(ARC_TO)
    tri = " ".join(f"{x:.1f},{y:.1f}" for x, y in _triangle())
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">',
             "  <title>Kudy jsem měl běžet</title>"]
    if tile:
        lines.append(f'  <rect x="9.5" y="9.5" width="237" height="237" rx="52" fill="{TILE}"'
                     f' stroke="{EDGE}" stroke-width="3"/>')
    fill = TILE if tile else "none"
    (lx1, ly1), (lx2, ly2) = _course_line()
    lines += [
        f'  <line x1="{lx1:.1f}" y1="{ly1:.1f}" x2="{lx2:.1f}" y2="{ly2:.1f}" stroke="{PURPLE}" stroke-width="{LINE_W}"/>',
        f'  <path d="M{sx:.1f} {sy:.1f}A{ARC_R} {ARC_R} 0 1 1 {ex:.1f} {ey:.1f}'
        f'Q{HOOK_CTRL[0]} {HOOK_CTRL[1]} {HOOK_END[0]} {HOOK_END[1]}"'
        f' fill="none" stroke="{RED}" stroke-width="{ROUTE_W}" stroke-linecap="round" stroke-dasharray="0 {ROUTE_STEP}"/>',
        f'  <polygon points="{tri}" fill="{fill}" stroke="{PURPLE}" stroke-width="{TRI_W}" stroke-linejoin="round"/>',
        f'  <circle cx="{CONTROL_C[0]}" cy="{CONTROL_C[1]}" r="{CONTROL_R}" fill="none"'
        f' stroke="{PURPLE}" stroke-width="{CONTROL_W}"/>',
        "</svg>", ""]
    return "\n".join(lines)


def _course_line():
    """The straight line from the start to the control, from the edge of the triangle to the edge of the circle."""
    tri = _triangle()
    cx, cy = sum(p[0] for p in tri) / 3, sum(p[1] for p in tri) / 3
    dx, dy = CONTROL_C[0] - cx, CONTROL_C[1] - cy
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    t0 = (tri[1][1] + TRI_W / 2 - cy) / dy                 # leaves the triangle through its bottom side
    t1 = n - CONTROL_R - CONTROL_W / 2
    return (cx + dx * t0, cy + dy * t0), (cx + dx * t1, cy + dy * t1)


def _gps_points():
    """Points every ROUTE_STEP along the track, like stroke-dasharray="0 ROUTE_STEP" in the SVG."""
    pts = _route_points()
    out, since = [pts[0]], 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        since += math.hypot(x1 - x0, y1 - y0)
        if since >= ROUTE_STEP:
            out.append((x1, y1))
            since -= ROUTE_STEP
    return out


def _route_points():
    pts = [_arc_point(ARC_FROM + (ARC_TO - ARC_FROM) * i / 4000) for i in range(4001)]
    p0, p1, p2 = pts[-1], HOOK_CTRL, HOOK_END
    for i in range(1, 1001):
        t = i / 1000
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return pts


def draw(size, body=1.0):
    """The icon as a picture, size x size. body < 1 leaves a margin (macOS icons are 824 of 1024)."""
    ss = 4                                     # draw 4x bigger and scale down = smooth edges
    big = size * ss
    k = big * body / 256
    off = big * (1 - body) / 2
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def P(x, y):
        return off + x * k, off + y * k

    def dot(x, y, r, fill):
        cx, cy = P(x, y)
        d.ellipse([cx - r * k, cy - r * k, cx + r * k, cy + r * k], fill=fill)

    d.rounded_rectangle([*P(8, 8), *P(248, 248)], radius=52 * k, fill=EDGE)
    d.rounded_rectangle([*P(11, 11), *P(245, 245)], radius=49 * k, fill=TILE)
    a, b = _course_line()
    d.line([P(*a), P(*b)], fill=PURPLE, width=round(LINE_W * k))
    for x, y in _gps_points():
        dot(x, y, ROUTE_W / 2, RED)
    tri = _triangle()
    d.polygon([P(*p) for p in tri], fill=PURPLE)
    for a, b in zip(tri, tri[1:] + tri[:1]):
        d.line([P(*a), P(*b)], fill=PURPLE, width=round(TRI_W * k))
        dot(*a, TRI_W / 2, PURPLE)
    inner = _shrink(tri, TRI_W / 2)
    d.polygon([P(*p) for p in inner], fill=TILE)
    dot(*CONTROL_C, CONTROL_R + CONTROL_W / 2, PURPLE)
    dot(*CONTROL_C, CONTROL_R - CONTROL_W / 2, TILE)
    return im.resize((size, size), Image.LANCZOS)


def _shrink(tri, by):
    """The triangle moved inwards by `by` on every side (the white inside of the outlined start)."""
    cx = sum(p[0] for p in tri) / 3
    cy = sum(p[1] for p in tri) / 3
    # distance from the centre to a side
    (x1, y1), (x2, y2) = tri[1], tri[2]
    side = abs((x2 - x1) * (y1 - cy) - (x1 - cx) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)
    f = (side - by) / side
    return [(cx + (x - cx) * f, cy + (y - cy) * f) for x, y in tri]


def main(out):
    os.makedirs(out, exist_ok=True)
    full = draw(1024)
    full.save(os.path.join(out, "app.png"))
    full.save(os.path.join(out, "app.ico"), sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    draw(1024, body=824 / 1024).save(os.path.join(out, "app.icns"))


def write_svgs():
    for path, tile in ((os.path.join(ROOT, "webapp", "static", "ob-logo.svg"), True),
                       (os.path.join(ROOT, "docs", "logo.svg"), True)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg(tile))
        print(path)


if __name__ == "__main__":
    if sys.argv[1:] == ["--svg"]:
        write_svgs()
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("build", "icons"))
