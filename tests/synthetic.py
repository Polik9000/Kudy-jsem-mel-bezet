"""A made-up race for the tests that need "a race with a map with the course, a map without it and a run" but not
a real one. The real ones are other people's maps (Livelox, the organisers') and the author's own runs, so they are not
in the public repository (TODO 50).

Every made-up race lies where the real one did and starts when the real one did, so a run pairs with it by date, time
and place; its official time is the real one. The map is white with a purple course: circles, lines, the start
triangle and the double circle of the finish, as analyze.py reads them. Nothing in them is meant to give the real
results: tests that check those (times, routes, golden files) read real data and are skipped without it
(tests/races.py: have_data, OB_TEST_DATA)."""
import datetime as dt
import io
import math
import os
import tempfile
import zipfile

from fitfile import fit_bytes
from PIL import Image, ImageDraw

MPP = 1.33                       # metres per pixel, as Livelox exports
SIZE = (760, 620)
PURPLE = (180, 70, 245)
KY = 6371008.8 * math.pi / 180

# folder -> centre of the map, date, start (local), official time in seconds, number of controls; run_s: how long
# the recording is when it is not the official time (Azymut is not in ORIS: 76:57 typed in, 77:02 on the watch)
RACES = {
    "pohora": dict(lat=49.561590, lon=16.762241, date="2025-05-17", start="13:18:00", time_s=50 * 60 + 22, n=16),
    "petrvald": dict(lat=49.830190, lon=18.372692, date="2026-03-28", start="10:45:00", time_s=80 * 60 + 18, n=22),
    "azymut-e5": dict(lat=49.950000, lon=21.950000, date="2026-08-14", start="10:00:00", time_s=76 * 60 + 57,
                      run_s=77 * 60 + 2, n=14),
    "azymut-e4": dict(lat=49.900000, lon=21.900000, date="2026-08-12", start="10:00:00", time_s=55 * 60 + 7, n=12),
}


def points(n):
    """Pixels of the start, n controls and the finish: a winding line across the map."""
    w, h = SIZE
    cols = max(2, math.ceil(math.sqrt(n + 2)))
    out = []
    for i in range(n + 2):
        row, col = divmod(i, cols)
        col = col if row % 2 == 0 else cols - 1 - col
        rows = math.ceil((n + 2) / cols)
        out.append((110 + col * (w - 220) / max(1, cols - 1), 100 + row * (h - 200) / max(1, rows - 1)))
    return out


def _kmz(path, image, lat, lon):
    w, h = image.size
    kx = KY * math.cos(math.radians(lat))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    kml = ("<kml><GroundOverlay><Icon><href>map.png</href></Icon><LatLonBox>"
           f"<north>{lat + h * MPP / 2 / KY:.9f}</north><south>{lat - h * MPP / 2 / KY:.9f}</south>"
           f"<east>{lon + w * MPP / 2 / kx:.9f}</east><west>{lon - w * MPP / 2 / kx:.9f}</west>"
           "</LatLonBox></GroundOverlay></kml>")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("doc.kml", kml)
        z.writestr("map.png", buf.getvalue())


def _course_image(pts, r=28):
    im = Image.new("RGB", SIZE, (255, 255, 255))
    d = ImageDraw.Draw(im)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / n, (by - ay) / n
        d.line([ax + ux * (r + 6), ay + uy * (r + 6), bx - ux * (r + 6), by - uy * (r + 6)], fill=PURPLE, width=3)
    sx, sy = pts[0]
    d.polygon([(sx + 1.25 * r * math.sin(a), sy - 1.25 * r * math.cos(a)) for a in (0, 2.0944, 4.1888)],
              outline=PURPLE, width=3)
    for x, y in pts[1:-1]:
        d.ellipse([x - r, y - r, x + r, y + r], outline=PURPLE, width=3)
    fx, fy = pts[-1]
    for q in (r + 2, r - 5):
        d.ellipse([fx - q, fy - q, fx + q, fy + q], outline=PURPLE, width=3)
    return im


def _run(pts, spec, tz):
    """The run through the points in exactly the official time, a sample every 2 s, starting at the official start."""
    lat, lon = spec["lat"], spec["lon"]
    kx = KY * math.cos(math.radians(lat))
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    step = length / (spec.get("run_s", spec["time_s"]) / 2)          # pixels per sample
    out, t, carry = [], 0.0, 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, by - ay)
        pos = carry
        while pos < seg:
            x, y = ax + (bx - ax) * pos / seg, ay + (by - ay) * pos / seg
            out.append((t, lat - (y - SIZE[1] / 2) * MPP / KY, lon + (x - SIZE[0] / 2) * MPP / kx))
            t += 2.0
            pos += step
        carry = pos - seg
    h, m, s = (int(p) for p in spec["start"].split(":"))
    local = dt.datetime.combine(dt.date.fromisoformat(spec["date"]), dt.time(h, m, s), tzinfo=tz)
    return fit_bytes(out, start=local.astimezone(dt.timezone.utc))


def build(folder, dest):
    """Write course.kmz, maponly.kmz and run.fit of the made-up race `folder` into dest/folder; returns the folder."""
    from oroute.garmin import TZ
    spec = RACES[folder]
    out = os.path.join(dest, folder)
    os.makedirs(out, exist_ok=True)
    pts = points(spec["n"])
    _kmz(os.path.join(out, "course.kmz"), _course_image(pts), spec["lat"], spec["lon"])
    _kmz(os.path.join(out, "maponly.kmz"), Image.new("RGB", SIZE, (255, 255, 255)), spec["lat"], spec["lon"])
    with open(os.path.join(out, "run.fit"), "wb") as f:
        f.write(_run(pts, spec, TZ))
    return out


_cache = {}


def inputs(folder):
    """(course.kmz, maponly.kmz, run.fit) of a made-up race, made once per test session."""
    if "dir" not in _cache:
        _cache["dir"] = tempfile.mkdtemp(prefix="ob-synthetic-")
    d = os.path.join(_cache["dir"], folder)
    if not os.path.isdir(d):
        build(folder, _cache["dir"])
    return tuple(os.path.join(d, n) for n in ("course.kmz", "maponly.kmz", "run.fit"))
