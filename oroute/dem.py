"""Elevation for the map area.

Two sources, both behind the same `height(lat, lon)`:

TerrariumDEM  AWS Terrain Tiles (Mapzen "terrarium" PNG tiles, s3.amazonaws.com/elevation-tiles-prod).
              Works everywhere. Zoom 15 (~3 m pixels) resampled from ~30 m data, so it shows hills and
              valleys but not small gullies, banks or pits.
CuzkDEM       ČÚZK DMR 5G, the Czech terrain model from airborne laser scanning (2 m grid, height error
              0.18 m in open terrain, 0.3 m in forest). Open data, CC BY 4.0, © ČÚZK. Czech Republic only.
              Read from the public ArcGIS ImageServer of ČÚZK: one request per map, the answer is cached.

load_dem(..., source) picks one: "aws", "cuzk" (fail when ČÚZK has no data or does not answer) or "auto"
(ČÚZK for maps inside the Czech Republic, AWS otherwise and as the fallback). The Polish 1 m LiDAR (GUGiK)
is not wired in; `load_dem_grid` takes any object with height(lat, lon).
"""
import io
import math
import os
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
CUZK_URL = "https://ags.cuzk.gov.cz/arcgis2/rest/services/dmr5g/ImageServer/exportImage"
CUZK_BBOX = (48.55, 51.06, 12.09, 18.87)   # south, north, west, east: a box around the Czech Republic
CUZK_CELL_M = 2.5                          # requested pixel size (the source grid is 2 m)
CUZK_MAX_PX = 4000                         # the service returns at most 4100 x 15000 pixels per request
# The speed model learned its slopes from the watch barometer smoothed over 15 s, and routes are priced
# in 2 m steps: on the raw 2 m LiDAR grid every ditch and bank would count as climb (Petřvald: 409 m along
# the track against 279 m by the barometer). Smoothing by 10 m keeps gullies and removes that noise; it is
# also where the heights agree best with the barometer (docs/validace.md).
CUZK_SMOOTH_M = 10.0
AGENT = "OB-tracker (club route analysis)"


class DemError(Exception):
    pass


def _tile_xy(lat, lon, z):
    n = 2 ** z
    x = (np.asarray(lon) + 180) / 360 * n
    y = (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n
    return x, y


class TerrariumDEM:
    source = "aws"

    def __init__(self, north, south, east, west, z=15, cache=None):
        self.z = z
        x0, y0 = _tile_xy(north, west, z)
        x1, y1 = _tile_xy(south, east, z)
        self.tx0, self.ty0 = int(x0), int(y0)
        nx, ny = int(x1) - self.tx0 + 1, int(y1) - self.ty0 + 1
        if cache and os.path.exists(cache):
            d = np.load(cache)
            if int(d["tx0"]) == self.tx0 and int(d["ty0"]) == self.ty0 and d["h"].shape == (256 * ny, 256 * nx):
                self.h = d["h"]
                return
        h = np.zeros((256 * ny, 256 * nx))
        for j in range(ny):
            for i in range(nx):
                u = URL.format(z=z, x=self.tx0 + i, y=self.ty0 + j)
                im = np.asarray(Image.open(io.BytesIO(urllib.request.urlopen(u, timeout=60).read()))
                                .convert("RGB")).astype(float)
                h[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768
        self.h = h
        if cache:
            np.savez_compressed(cache, h=h, tx0=self.tx0, ty0=self.ty0, z=z)

    def height(self, lat, lon):
        x, y = _tile_xy(lat, lon, self.z)
        px = (x - self.tx0) * 256 - 0.5
        py = (y - self.ty0) * 256 - 0.5
        return map_coordinates(self.h, [np.ravel(py), np.ravel(px)], order=1, mode="nearest").reshape(np.shape(lat))


def _cuzk_fetch(south, north, west, east, width, height, timeout=90):
    """One exportImage request: heights as a float32 TIFF in WGS 84 (bytes)."""
    q = urllib.parse.urlencode(dict(
        bbox=f"{west},{south},{east},{north}", bboxSR=4326, imageSR=4326, size=f"{width},{height}",
        format="tiff", pixelType="F32", interpolation="RSP_BilinearInterpolation", f="image"))
    req = urllib.request.Request(f"{CUZK_URL}?{q}", headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def in_czechia(north, south, east, west):
    """Whether the whole box lies inside the rough box of the Czech Republic (the service has no data outside)."""
    s, n, w, e = CUZK_BBOX
    return s <= south and north <= n and w <= west and east <= e


class CuzkDEM:
    """DMR 5G of ČÚZK for a box: a regular lat/lon grid of heights. fetch(south, north, west, east, width,
    height) -> TIFF bytes can be replaced (tests read a stored answer)."""
    source = "cuzk"

    def __init__(self, north, south, east, west, cache=None, pad_m=60.0, fetch=None, smooth_m=CUZK_SMOOTH_M):
        self.h = self._load(north, south, east, west, cache, pad_m, fetch or _cuzk_fetch)
        if smooth_m:
            from scipy.ndimage import gaussian_filter
            cell = (self.n - self.s) * 111195.0 / self.h.shape[0]
            self.h = gaussian_filter(np.asarray(self.h, float), smooth_m / cell, mode="nearest")

    def _load(self, north, south, east, west, cache, pad_m, fetch):
        """The raw grid (as the service gave it); sets self.n, s, e, w to where it lies."""
        ky = 111195.0
        kx = ky * math.cos(math.radians((north + south) / 2))
        n, s = north + pad_m / ky, south - pad_m / ky
        e, w = east + pad_m / kx, west - pad_m / kx
        if cache and os.path.exists(cache):
            d = np.load(cache)
            if all(abs(float(d[k]) - v) < 1e-9 for k, v in (("qn", n), ("qs", s), ("qe", e), ("qw", w))):
                self.n, self.s, self.e, self.w = (float(d[k]) for k in "nsew")
                return d["h"]
        # the service answers with pixels that are square in degrees (it widens the box when the size asks
        # for anything else), so ask for exactly that: one pixel = CUZK_CELL_M in latitude
        deg = CUZK_CELL_M / ky
        width = int(min(CUZK_MAX_PX * 3, max(16, math.ceil((e - w) / deg))))
        height = int(min(CUZK_MAX_PX, max(16, math.ceil((n - s) / deg))))
        try:
            raw = fetch(s, n, w, e, width, height)
            im = Image.open(io.BytesIO(raw))
            h = np.asarray(im, dtype=float)
            # where the picture really lies: GeoTIFF tie point (pixel 0,0 -> lon, lat) and pixel size
            tie, scale = im.tag_v2.get(33922), im.tag_v2.get(33550)
        except Exception as err:  # no answer, no data for the box (empty TIFF), not a picture ...
            raise DemError(f"ČÚZK DMR 5G: {err}") from err
        if h.ndim != 2 or h.shape[0] < 2 or h.shape[1] < 2 or not tie or not scale:
            raise DemError("ČÚZK DMR 5G: the answer is not a georeferenced height raster")
        gw, gn = tie[3] - tie[0] * scale[0], tie[4] + tie[1] * scale[1]
        ge, gs = gw + h.shape[1] * scale[0], gn - h.shape[0] * scale[1]
        if gw > w + 1e-6 or ge < e - 1e-6 or gs > s + 1e-6 or gn < n - 1e-6:
            raise DemError("ČÚZK DMR 5G: the answer does not cover the map")
        qn, qs, qe, qw = n, s, e, w
        n, s, e, w = gn, gs, ge, gw
        # no data comes as NaN or as a huge negative number; real heights in the Czech Republic are 115..1603 m
        bad = ~np.isfinite(h) | (h < -100) | (h > 3000)
        if bad.mean() > 0.01:
            raise DemError(f"ČÚZK DMR 5G: {100 * bad.mean():.0f} % of the area has no data")
        if bad.any():
            from scipy.ndimage import distance_transform_edt
            _, (iy, ix) = distance_transform_edt(bad, return_indices=True)
            h = h[iy, ix]
        self.n, self.s, self.e, self.w = n, s, e, w
        if cache:
            np.savez_compressed(cache, h=h.astype(np.float32), n=n, s=s, e=e, w=w, qn=qn, qs=qs, qe=qe, qw=qw)
        return h

    def height(self, lat, lon):
        H, W = self.h.shape
        py = (self.n - np.asarray(lat, float)) / (self.n - self.s) * H - 0.5
        px = (np.asarray(lon, float) - self.w) / (self.e - self.w) * W - 0.5
        return map_coordinates(self.h, [np.ravel(py), np.ravel(px)], order=1, mode="nearest").reshape(np.shape(lat))


def load_dem(north, south, east, west, cache_dir, source="aws", log=print):
    """The elevation model for a box, cached in cache_dir (dem_cache.npz for AWS, dem_cuzk.npz for ČÚZK).

    source: "aws" | "cuzk" | "auto" (ČÚZK inside the Czech Republic, AWS otherwise and when ČÚZK fails).
    The object has .source ("aws" or "cuzk") and height(lat, lon)."""
    aws = lambda: TerrariumDEM(north, south, east, west, cache=os.path.join(cache_dir, "dem_cache.npz"))
    if source == "aws":
        return aws()
    if source not in ("cuzk", "auto"):
        raise ValueError(f"unknown elevation source {source!r}")
    if source == "auto" and not in_czechia(north, south, east, west):
        return aws()
    try:
        return CuzkDEM(north, south, east, west, cache=os.path.join(cache_dir, "dem_cuzk.npz"))
    except DemError as err:
        if source == "cuzk":
            raise
        log(f"{err}; falling back to AWS Terrain Tiles")
        return aws()


def load_dem_grid(geomap, dem, step=1):
    """Height (m) at every `step`-th map pixel, shape (H//step, W//step)."""
    v, u = np.mgrid[0:geomap.H:step, 0:geomap.W:step].astype(float)
    lat, lon = geomap.px_to_latlon(u + (step - 1) / 2, v + (step - 1) / 2)
    return dem.height(lat, lon)
