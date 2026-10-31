"""Livelox / Google Earth KMZ GroundOverlay: image + lat/lon <-> pixel transforms."""
import io
import math
import re
import zipfile

import numpy as np
from PIL import Image

R_EARTH = 6371008.8
LIVELOX_HEADER_PX = 145  # title bar at the top of every image exported from Livelox


class GeoMap:
    """Map image georeferenced by a KML LatLonBox (north/south/east/west + rotation).

    KML semantics: the image is stretched over the box, then rotated `rotation`
    degrees counter-clockwise about the box centre. We do the rotation in a local
    metric plane (east/north metres), which is what Google Earth / Livelox show.
    """

    def __init__(self, image, north, south, east, west, rotation=0.0, header_px=0, blur_m=0.0):
        self.image = image.convert("RGB")
        self.header_px = header_px  # rows at the top of the picture that are not map (the Livelox title bar)
        # how much more blurred the picture is than a Livelox export (metres, a gaussian sigma): a map cut out of
        # a screenshot the browser zoomed (oroute/pair.py); the widths of lines are read with it (terrain.py)
        self.blur_m = blur_m
        self.W, self.H = self.image.size
        self.n, self.s, self.e, self.w, self.rot = north, south, east, west, rotation
        self.lat0 = (north + south) / 2
        self.lon0 = (east + west) / 2
        self.kx = R_EARTH * math.cos(math.radians(self.lat0)) * math.pi / 180  # m per deg lon
        self.ky = R_EARTH * math.pi / 180  # m per deg lat
        self.width_m = (east - west) * self.kx
        self.height_m = (north - south) * self.ky
        self.m_per_px_x = self.width_m / self.W
        self.m_per_px_y = self.height_m / self.H

    @classmethod
    def from_kmz(cls, path):
        z = zipfile.ZipFile(path)
        kml_name = next(n for n in z.namelist() if n.lower().endswith(".kml"))
        kml = z.read(kml_name).decode("utf-8")
        get = lambda tag, d=None: float(re.search(rf"<{tag}>([^<]+)</{tag}>", kml).group(1)) \
            if re.search(rf"<{tag}>", kml) else d
        href = re.search(r"<href>([^<]+)</href>", kml).group(1).strip()
        img = Image.open(io.BytesIO(z.read(href)))
        # a Livelox export has a title bar of LIVELOX_HEADER_PX rows; a KMZ written by oroute.georef says so itself
        m = re.search(r"<!--\s*ob-header-px:\s*(\d+)\s*-->", kml)
        b = re.search(r"<!--\s*ob-blur-m:\s*([0-9.]+)\s*-->", kml)
        return cls(img, get("north"), get("south"), get("east"), get("west"), get("rotation", 0.0),
                   header_px=int(m.group(1)) if m else LIVELOX_HEADER_PX, blur_m=float(b.group(1)) if b else 0.0)

    # lat/lon -> local metres (east, north) relative to box centre
    def to_xy(self, lat, lon):
        return (np.asarray(lon) - self.lon0) * self.kx, (np.asarray(lat) - self.lat0) * self.ky

    def from_xy(self, x, y):
        return np.asarray(y) / self.ky + self.lat0, np.asarray(x) / self.kx + self.lon0

    def latlon_to_px(self, lat, lon):
        x, y = self.to_xy(lat, lon)
        a = math.radians(-self.rot)  # undo the CCW rotation
        xr = x * math.cos(a) - y * math.sin(a)
        yr = x * math.sin(a) + y * math.cos(a)
        u = (xr / self.width_m + 0.5) * self.W
        v = (0.5 - yr / self.height_m) * self.H
        return u, v

    def px_to_latlon(self, u, v):
        xr = (np.asarray(u, float) / self.W - 0.5) * self.width_m
        yr = (0.5 - np.asarray(v, float) / self.H) * self.height_m
        a = math.radians(self.rot)
        x = xr * math.cos(a) - yr * math.sin(a)
        y = xr * math.sin(a) + yr * math.cos(a)
        return self.from_xy(x, y)
