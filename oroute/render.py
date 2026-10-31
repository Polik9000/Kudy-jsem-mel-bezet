"""Draw the track, course and mistake markers on the map image."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LEG_COLORS = [(230, 25, 75), (0, 130, 200)]
STOP = (140, 0, 160)


def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def speed_color(v, vref):
    """Red (stopped) -> orange -> dark blue (at/above your normal speed).
    Avoids green, which disappears on the forest colour of the map."""
    f = float(np.clip(v / (1.1 * vref), 0, 1))
    stops = [(0.0, (215, 25, 30)), (0.45, (245, 150, 20)), (1.0, (25, 50, 190))]
    for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
        if f <= f1:
            w = (f - f0) / (f1 - f0)
            return tuple(int(a + (b - a) * w) for a, b in zip(c0, c1))
    return stops[-1][1]


def draw_overlay(geomap, track, legs, punch_idx, points_px, speed, vref, mode="leg", scale=2):
    """mode='leg' colours legs alternately; mode='speed' colours by running speed."""
    W, H = geomap.W * scale, geomap.H * scale
    im = geomap.image.resize((W, H), Image.LANCZOS)
    # fade the map a little so the track stands out
    im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.25)
    d = ImageDraw.Draw(im, "RGBA")
    u, v = geomap.latlon_to_px(track["lat"], track["lon"])
    u, v = u * scale, v * scale
    for l in legs:  # white halo under the track
        d.line(list(zip(u[l["a"]:l["b"] + 1], v[l["a"]:l["b"] + 1])), fill=(255, 255, 255, 200),
               width=5 * scale, joint="curve")
    for l in legs:
        for i in range(l["a"], l["b"]):
            col = LEG_COLORS[l["leg"] % 2] if mode == "leg" else speed_color(speed[i], vref)
            d.line([(u[i], v[i]), (u[i + 1], v[i + 1])], fill=col + (235,), width=3 * scale)
    for l in legs:
        for s, e in l["stops"]:
            if track["t"][e] - track["t"][s] < 10:
                continue
            cx, cy = u[s:e + 1].mean(), v[s:e + 1].mean()
            r = (4 + min(e - s, 40) * 0.4) * scale
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=STOP + (255,), width=scale * 2)
    for i in punch_idx:
        r = 3 * scale
        d.ellipse([u[i] - r, v[i] - r, u[i] + r, v[i] + r], fill=(0, 0, 0, 255))
    return im


def crop_leg(im, geomap, track, leg, points_px, scale=2, pad_m=120, title=None):
    u, v = geomap.latlon_to_px(track["lat"][leg["a"]:leg["b"] + 1], track["lon"][leg["a"]:leg["b"] + 1])
    k = leg["leg"]
    xs = np.r_[u, points_px[k - 1][0], points_px[k][0]] * scale
    ys = np.r_[v, points_px[k - 1][1], points_px[k][1]] * scale
    pad = pad_m / geomap.m_per_px_x * scale
    box = [int(max(xs.min() - pad, 0)), int(max(ys.min() - pad, 0)),
           int(min(xs.max() + pad, im.width)), int(min(ys.max() + pad, im.height))]
    c = im.crop(box)
    c.info["title"] = title
    return c


def contact_sheet(images, cols=2, width=900, bg=(255, 255, 255)):
    thumbs = []
    for im in images:
        s = width / im.width
        t = im.resize((width, max(1, int(im.height * s))), Image.LANCZOS)
        if im.info.get("title"):
            d = ImageDraw.Draw(t, "RGBA")
            f = _font(26)
            d.rectangle([0, 0, d.textlength(im.info["title"], font=f) + 20, 40], fill=(255, 255, 255, 230))
            d.text((10, 6), im.info["title"], fill=(0, 0, 0), font=f)
        thumbs.append(t)
    rows = [thumbs[i:i + cols] for i in range(0, len(thumbs), cols)]
    H = sum(max(t.height for t in r) for r in rows) + 10 * (len(rows) + 1)
    sheet = Image.new("RGB", (cols * width + 10 * (cols + 1), H), bg)
    y = 10
    for r in rows:
        x = 10
        for t in r:
            sheet.paste(t, (x, y))
            x += width + 10
        y += max(t.height for t in r) + 10
    return sheet
