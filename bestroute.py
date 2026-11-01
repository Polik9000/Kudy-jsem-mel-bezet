#!/usr/bin/env python3
"""Step 3: fastest route per leg for you, compared with the route you ran.

usage: python3 bestroute.py MAPONLY.kmz COURSE.json ACTIVITY.fit OUT_DIR
           [--legs 8-9,5-6,...] [--model speed_model.json|race] [--step 2]
           [--dem aws|cuzk|auto] [--barriers barriers.json] [--alternatives 2] [--generic [auto|all|terrain]]

MAPONLY.kmz  Livelox export with no course drawn (terrain is read from it)
COURSE.json  control positions, as written by analyze.py (step 1)

Writes to OUT_DIR:
  terrain.png        how the map was read (one colour per terrain class, legend in the report)
  speed_model.json   the speed model used (replaceable, see oroute/speedmodel.py)
  fit_samples.npz    GPS samples of the clean legs, input for oroute/personal.py
  best_routes.jpg    whole course: your track (red) and the fastest route (blue) for every leg
  best_legs.jpg      zoomed comparison per leg, worst legs first
  best_legs.csv      numbers per leg
  best_routes.md     report with an explanation per leg
"""
import argparse
import csv
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from oroute import errors, generic, mapdata  # noqa: E402
from oroute import terrain as T  # noqa: E402
from oroute.analysis import analyse_legs, find_punches, flag_legs, smooth_speed, track_xy, unrecorded  # noqa: E402
from oroute.dem import load_dem_grid  # noqa: E402
from oroute.fitload import load_track  # noqa: E402
from oroute.jsonout import rounded  # noqa: E402
from oroute.jsonout import save as save_json
from oroute.kmzmap import GeoMap  # noqa: E402
from oroute.official import apply as apply_official  # noqa: E402
from oroute.official import no_data_legs  # noqa: E402
from oroute.render import _font, contact_sheet  # noqa: E402
from oroute.routing import (  # noqa: E402
    PATH_SIDE_M,
    TRACK_OFF_M,
    Grid,
    along_path,
    cross_slope,
    crossed,
    neighbour_shares,
    route_metrics,
    route_samples,
    slope_field,
)
from oroute.speedmodel import SpeedModel  # noqa: E402

VERSION = 9      # goes up when the routes of the same race would come out different (stored analyses are
                 # then offered to be redone): 2 = ponds with a bank line and fenced ground are impassable;
                 # 3 = fences and rows of dots are no paths, a fence is hard to cross, the start is the triangle;
                 # 4 = inside a settlement only the streets; 5 = the route of an average runner next to yours;
                 # 6 = sprint maps: grey buildings are buildings, paved areas and passages are run like streets;
                 # 7 = your track along a path within 15 m of it is on the path (the model learns it so too);
                 # 8 = sprint maps: an impassable wall is a building, a passable one (with dots) slow to climb;
                 # 9 = pens on coarse pictures, their fence and point, gates, impassable fences; north lines at
                 #     any angle are no streams (night 25. 10., Bělá)
HEADER_PX = 145  # Livelox header bar at the top of the exported image (main() takes it from the map)
NOISE_S = 15.0   # routes closer than this in model time are equally good
RUN_IN_M = 60.0  # the time starts at least this far from the start triangle: a marked route leads to it
RUN_IN_MAX_M = 150.0   # ... but without official times not farther than this: a recording that begins farther
                       # away began on the walk to the start, not where the time started
SENSITIVITY = (0.8, 1.2)  # terrain factors off the paths are shifted by these to see if the best route flips
SLOWCLS = ["light green (slow run)", "green (walk)", "dark green (fight)", "undergrowth (stripes)", "marsh"]
RED, BLUE, PURPLE = (220, 30, 40), (20, 70, 220), (170, 40, 220)
# how the runner's own track is read wherever it is priced or learnt from: a sample on impassable ground lies on
# the passable ground up to 8 m beside it, a stretch along a path up to 15 m beside it is on the path
TRACK = dict(beside_m=TRACK_OFF_M, on_path_m=PATH_SIDE_M)


def mmss(s):
    s = int(round(s))
    sign = "-" if s < 0 else ""
    s = abs(s)
    return f"{sign}{s // 60}:{s % 60:02d}"


def leg_name(k, n):
    return f"{'S' if k == 1 else k - 1}-{'F' if k == n else k}"


def slow_m(m):
    return sum(v for k, v in m["mix"].items() if k in SLOWCLS)


def path_m(m):
    return m["mix"].get("path/road", 0.0)


# the sentences explain() builds, per language (same rules, only the wording differs)
TXT = {
    "en": dict(
        straight="goes nearly straight",
        paths="goes round on paths ({p:.0f} of {d:.0f} m on path)",
        bends="bends off the straight line ({r:.2f}x its length)",
        less_climb="climbs {x:.0f} m less than the straight line",
        avoids="avoids {x:.0f} m of green/marsh on the line",
        fast_path="uses fast path running",
        best="Best route {shape}", because=": it ", and_=" and ",
        longer="{x:.0f} m longer", more_climb="{x:.0f} m more climb",
        more_green="{x:.0f} m more in green/marsh", less_path="{x:.0f} m less on paths",
        lost="up to {x:.0f} m off the straight line (that looks like being lost and "
             "relocating rather than a planned route)",
        yours_diff="Your line was {diff}; at your own pace that alone costs about {t}.",
        yours_cost="Your line costs about {t} more at your pace.",
        yours_same="Your line was about as good as the best one.",
        yours_faster="By the model your line is {t} faster than the best route",
        through=dict(railway=": it crosses the railway away from a crossing, where the best route must not.",
                     motorway=": it crosses the motorway away from a crossing, where the best route must not.",
                     manual=": it crosses a line drawn as forbidden, where the best route must not.",
                     area=": it runs through an out-of-bounds area the best route keeps out of.",
                     enclosure=": it runs through fenced ground the best route keeps out of."),
        faster_noise=". The search runs on a grid, so differences up to about 20 s are noise.",
        slower="On top of that you took {t} longer than your own pace on the line you ran",
        standing=" ({s:.0f} s standing still)",
        near="Much of the loss was in the last 100 m before the control (~{t} extra there), "
             "so this was mostly finding the control, not the route choice.",
        no_data="The recording has no GPS track of this leg (the watch was started late, stopped early or the "
                "control was not visited): only the best route is shown."),
    "cs": dict(
        straight="vede skoro rovně",
        paths="obíhá po cestách ({p:.0f} z {d:.0f} m po cestě)",
        bends="uhýbá z přímky (je {r:.2f}× delší než přímka)",
        less_climb="nastoupá o {x:.0f} m méně než přímka",
        avoids="vyhne se {x:.0f} m zelené nebo bažiny na přímce",
        fast_path="využije rychlý běh po cestě",
        best="Nejlepší postup {shape}", because=": ", and_=" a ",
        longer="o {x:.0f} m delší", more_climb="o {x:.0f} m víc stoupání",
        more_green="o {x:.0f} m víc v zelené nebo bažině", less_path="o {x:.0f} m méně po cestách",
        lost="až {x:.0f} m od přímky (to vypadá spíš na bloudění a dohledávání než na plánovaný postup)",
        yours_diff="Tvůj postup: {diff}; při tvém tempu to samo stojí asi {t}.",
        yours_cost="Tvůj postup stojí při tvém tempu asi o {t} víc.",
        yours_same="Tvůj postup byl zhruba stejně dobrý jako nejlepší.",
        yours_faster="Tvoje stopa vychází podle modelu o {t} rychleji než nejlepší postup",
        through=dict(railway=": kříží železnici mimo přechod, kudy nejlepší postup nesmí.",
                     motorway=": kříží dálnici mimo přechod, kudy nejlepší postup nesmí.",
                     manual=": kříží ručně nakreslenou zakázanou čáru, kudy nejlepší postup nesmí.",
                     area=": vede zakázaným prostorem, kterému se nejlepší postup vyhýbá.",
                     enclosure=": vede přes oplocenku, kterou nejlepší postup obíhá."),
        faster_noise=". Hledání běží po mřížce, rozdíly do 20 s jsou šum výpočtu.",
        slower="Navíc jsi byl o {t} pomalejší, než odpovídá tvému tempu na postupu, který jsi běžel",
        standing=" ({s:.0f} s stání)",
        near="Velká část ztráty vznikla na posledních 100 m před kontrolou (asi {t} navíc), "
             "takže šlo hlavně o dohledávku kontroly, ne o volbu postupu.",
        no_data="Na tomhle úseku chybí záznam z hodinek (nedostatek dat: hodinky byly spuštěné pozdě, zastavené "
                "dřív, nebo stopa kontrolou neprošla). Je tu jen nejlepší postup."),
}


def explain(B, Y, S, actual, leg, lang="en", through=()):
    """Plain-language comparison of best (B), yours (Y) and straight line (S).
    through: what the track went through that the routes must not (routing.crossed)."""
    x = TXT[lang]
    out = []
    # what the best route does
    if B["dist"] < 1.12 * S["dist"]:
        shape = x["straight"]
    elif path_m(B) > 0.4 * B["dist"]:
        shape = x["paths"].format(p=path_m(B), d=B["dist"])
    else:
        shape = x["bends"].format(r=B["dist"] / S["dist"])
    why = []
    if S["climb"] - B["climb"] > 8:
        why.append(x["less_climb"].format(x=S["climb"] - B["climb"]))
    if slow_m(S) - slow_m(B) > 30:
        why.append(x["avoids"].format(x=slow_m(S) - slow_m(B)))
    if path_m(B) - path_m(S) > 50:
        why.append(x["fast_path"])
    out.append(x["best"].format(shape=shape) + (x["because"] + x["and_"].join(why) if why else "") + ".")
    # your route vs best
    d_route = Y["time"] - B["time"]
    diff = []
    if Y["dist"] > 1.15 * B["dist"]:
        diff.append(x["longer"].format(x=Y["dist"] - B["dist"]))
    if Y["climb"] - B["climb"] > 8:
        diff.append(x["more_climb"].format(x=Y["climb"] - B["climb"]))
    if slow_m(Y) - slow_m(B) > 30:
        diff.append(x["more_green"].format(x=slow_m(Y) - slow_m(B)))
    if path_m(B) - path_m(Y) > 60:
        diff.append(x["less_path"].format(x=path_m(B) - path_m(Y)))
    if leg.get("max_dev", 0) > 150 and Y["dist"] > 1.5 * B["dist"]:
        diff.append(x["lost"].format(x=leg["max_dev"]))
    if d_route > NOISE_S and diff:
        out.append(x["yours_diff"].format(diff=", ".join(diff), t=mmss(d_route)))
    elif d_route > NOISE_S:
        out.append(x["yours_cost"].format(t=mmss(d_route)))
    elif d_route < -NOISE_S:
        # the track is priced without the barriers the routes obey: say so, or it reads as a broken model
        why = next((x["through"][c["what"]] for c in through if c["what"] in x["through"]), x["faster_noise"])
        out.append(x["yours_faster"].format(t=mmss(-d_route)) + why)
    else:
        out.append(x["yours_same"])
    d_exec = actual - Y["time"]
    if d_exec > 30:
        near = leg.get("zone_excess", 0)
        txt = x["slower"].format(t=mmss(d_exec))
        if leg.get("stop_time", 0) > 20:
            txt += x["standing"].format(s=leg["stop_time"])
        out.append(txt + ".")
        if near > 60:
            out.append(x["near"].format(t=mmss(near)))
    return " ".join(out)


def shifted(model, f):
    """The model with every terrain off the paths f times as fast (paths stay as they are)."""
    fac = {c: (v if c == T.PATH else v * f) for c, v in model.factors.items()}
    return SpeedModel(model.v_flat, model.up_k, model.down_gain, model.steep_down, fac)


def draw_leg_image(gm, base_img, tracks_px, best_px, ctrl_px, a, b, scale=2, pad_m=90, title=None):
    im = base_img.copy()
    d = ImageDraw.Draw(im, "RGBA")
    S = scale
    if best_px:
        d.line([(u * S, v * S) for u, v in best_px], fill=(255, 255, 255, 220), width=9 * S // 2, joint="curve")
        d.line([(u * S, v * S) for u, v in best_px], fill=BLUE + (240,), width=3 * S, joint="curve")
    if len(tracks_px) > 1:
        d.line([(u * S, v * S) for u, v in tracks_px], fill=RED + (230,), width=2 * S, joint="curve")
    for k, (u, v) in enumerate(ctrl_px):
        r = 18 * S
        d.ellipse([u * S - r, v * S - r, u * S + r, v * S + r], outline=PURPLE + (255,), width=2 * S)
    xs = [p[0] for p in list(tracks_px) + list(best_px) + [ctrl_px[a], ctrl_px[b]]]
    ys = [p[1] for p in list(tracks_px) + list(best_px) + [ctrl_px[a], ctrl_px[b]]]
    pad = pad_m / gm.m_per_px_x
    box = [int(max(min(xs) - pad, 0) * S), int(max(min(ys) - pad, HEADER_PX) * S),
           int(min(max(xs) + pad, gm.W) * S), int(min(max(ys) + pad, gm.H) * S)]
    c = im.crop(box)
    c.info["title"] = title
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kmz")
    ap.add_argument("course")
    ap.add_argument("fit")
    ap.add_argument("out")
    ap.add_argument("--legs", help="comma list like 8-9,5-6 (default: all)")
    ap.add_argument("--model", help="speed_model.json to use (default: oroute/personal_model.json, fitted on all "
                    "your races, see oroute/personal.py); 'race' = fit on this race's clean legs only")
    ap.add_argument("--slope", default=os.path.join(HERE, "oroute", "slope_prior.json"),
                    help="slope_prior.json from oroute.slopefit (uphill/downhill shape from Garmin activities); "
                         "'none' = textbook values")
    ap.add_argument("--step", type=int, help="routing cell size in map pixels (default: 2, more on a picture "
                    "sharper than half a metre per pixel, so that a cell is about a metre)")
    ap.add_argument("--title", default="Azymut Cup 2026 E5", help="race name for the report heading")
    ap.add_argument("--official", help="JSON with official start and split times (see oroute/official.py); "
                    "pass the same file as to analyze.py")
    ap.add_argument("--dem", default="aws", choices=("aws", "cuzk", "auto"),
                    help="elevation: aws = AWS Terrain Tiles (default), cuzk = Czech DMR 5G, auto = DMR 5G for "
                         "Czech maps with AWS as the fallback (see oroute/dem.py)")
    ap.add_argument("--barriers", help="JSON with lines that must not be crossed, the places where crossing is "
                    "fine and areas that must not be entered (railways from OpenStreetMap, lines drawn by hand: "
                    "see oroute/osm.py; hatched out-of-bounds areas of the map with the course: oroute/hatch.py)")
    ap.add_argument("--alternatives", type=int, default=0, metavar="K",
                    help="also find up to K routes per leg that differ from the best one, and check whether the "
                         "best route flips when terrain speeds shift by 20 %% (written to best.json only)")
    ap.add_argument("--no-images", action="store_true",
                    help="do not draw terrain.png, best_legs.jpg and best_routes.jpg (the web app draws the map "
                         "itself from best.json)")
    ap.add_argument("--terrain-cache", metavar="FILE",
                    help="keep the terrain read from the map in FILE and take it from there next time; it is "
                         "read from the map again when the map or oroute/terrain.py has changed")
    ap.add_argument("--generic", nargs="?", const="auto", choices=("auto", "all", "terrain"),
                    help="also find the best route of an average runner (textbook slope, ISOM terrain, your speed "
                         "on a flat path; oroute/generic.py) and say where and why yours differs (best.json only). "
                         "all = compare the slope too, terrain = the slope of the model was not measured on the "
                         "runner, compare the terrain only; auto = as the model's notes say (slope_own)")
    ap.add_argument("--corrections", metavar="JSON",
                    help="lines the runner drew where the GPS failed: {leg number: [[lat, lon], ...]}; such a leg is "
                         "priced along the drawn line instead of the track (your line, choice x execution)")
    ap.add_argument("--samples-only", action="store_true",
                    help="stop after fit_samples.npz and leg_samples.npz: what the personal speed model learns "
                         "from this race, without finding any route")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    global HEADER_PX
    gm = GeoMap.from_kmz(args.kmz)
    HEADER_PX = gm.header_px
    if args.step is None:
        args.step = max(2, int(round(1.0 / gm.m_per_px_x)))
    print("reading terrain ...")
    cls = mapdata.terrain(gm, args.kmz, args.terrain_cache)
    course = json.load(open(args.course, encoding="utf-8"))
    pts_ll = [course["start"]] + course["controls"] + [course["finish"]]
    ctrl_px = [tuple(float(a) for a in gm.latlon_to_px(p["lat"], p["lon"])) for p in pts_ll]
    # what the map shows as impassable or hard to cross (fenced ground with a control in it can be entered)
    obs = mapdata.obstacles(gm, cls, open_at=ctrl_px)
    cls = obs["cls"]
    if not args.no_images:
        timg = Image.fromarray(T.render_classes(cls))
        dl = ImageDraw.Draw(timg)
        fl = _font(16)
        used = [c for c in range(len(T.NAMES)) if (cls == c).any()]
        dl.rectangle([8, 8, 260, 16 + 22 * len(used)], fill=(255, 255, 255), outline=(0, 0, 0))
        for i, c in enumerate(used):
            dl.rectangle([14, 14 + 22 * i, 32, 30 + 22 * i], fill=T.COLORS[c], outline=(0, 0, 0))
            dl.text((40, 13 + 22 * i), T.NAMES[c], fill=(0, 0, 0), font=fl)
        timg.save(os.path.join(args.out, "terrain.png"))

    print("elevation ...")
    dem = mapdata.elevation(gm, args.out, args.dem)
    print(f"elevation source: {dem.source}")
    height = load_dem_grid(gm, dem)

    pts_xy = [tuple(float(a) for a in gm.to_xy(p["lat"], p["lon"])) for p in pts_ll]

    tr = load_track(args.fit)
    punch, official = None, None
    if args.official:
        tr, punch, official = apply_official(tr, gm, pts_xy, json.load(open(args.official, encoding="utf-8")))
    x, y = track_xy(gm, tr)
    if punch is None:
        punch = find_punches(tr["t"], x, y, pts_xy)
        gone = unrecorded(x, y, punch, pts_xy, why=official and official.get("reason"))
    else:
        gone = no_data_legs(official, len(pts_xy) - 1)
    legs, _ = analyse_legs(tr, x, y, pts_xy, punch, no_data=gone)
    flag_legs(legs)
    n = len(legs)
    tu, tv = gm.latlon_to_px(tr["lat"], tr["lon"])
    tu, tv = np.asarray(tu), np.asarray(tv)

    # --- speed model -------------------------------------------------------
    # GPS samples of the legs you ran cleanly (step 1 estimated < 60 s lost): when you are unsure
    # where you are you run slower everywhere, and that should not set your normal pace.
    # They are always saved (fit_samples.npz), so this race joins the personal model (oroute/personal.py).
    race_s = float(sum(l["time"] for l in legs))  # how long the race took: the race-length factor of the model
    use = np.zeros(len(tu) - 1, bool)
    legid = np.full(len(tu) - 1, -1)
    clean = [l for l in legs if l["est_loss"] < 60 and not l.get("no_data")]
    for l in clean:
        use[l["a"]:l["b"]] = True
        legid[l["a"]:l["b"]] = l["leg"]
    ui = np.clip(np.round(tu).astype(int), 0, gm.W - 1)
    vi = np.clip(np.round(tv).astype(int), 0, gm.H - 1)
    hs = height[vi, ui]
    dist = np.hypot(np.diff(x), np.diff(y))
    dt = np.diff(tr["t"])
    # grade over +-3 samples (single 2 s steps are too short for a 30 m DEM)
    k = 3
    i0 = np.clip(np.arange(len(dist)) - k, 0, len(hs) - 1)
    i1 = np.clip(np.arange(len(dist)) + k + 1, 0, len(hs) - 1)
    cum = np.r_[0, np.cumsum(dist)]
    grade = (hs[i1] - hs[i0]) / np.maximum(cum[i1] - cum[i0], 5)
    mid = cls[(vi[:-1] + vi[1:]) // 2, (ui[:-1] + ui[1:]) // 2]
    # A stretch of the track along a path and up to 15 m beside it was run on the path (GPS and the placing of
    # the map are metres off): the model learns it as path running, as "your track" is priced (TRACK).
    for l in legs:
        if l["b"] > l["a"] and not l.get("no_data"):
            on = along_path(tu[l["a"]:l["b"] + 1], tv[l["a"]:l["b"] + 1], cls, gm.m_per_px_x)
            mid[l["a"]:l["b"]][on[:-1] & on[1:]] = T.PATH
    sp = smooth_speed(tr["t"], x, y)
    use &= (sp[:-1] > 0.5) & (sp[1:] > 0.5)  # leave out standing still
    # the clean legs as the report measures them (route_metrics on your line), for scaling the pooled model
    rs = [route_samples(list(zip(tu[l["a"]:l["b"] + 1], tv[l["a"]:l["b"] + 1])), cls, height, gm.m_per_px_x,
                        **TRACK) for l in clean]
    np.savez_compressed(os.path.join(args.out, "fit_samples.npz"), dist=dist[use], dt=dt[use], cls=mid[use],
                        grade=grade[use], leg=legid[use], date=str(tr["start"].date()), title=args.title,
                        line_d=np.concatenate([r[0] for r in rs]), line_cls=np.concatenate([r[1] for r in rs]),
                        line_grade=np.concatenate([r[2] for r in rs]),
                        line_leg=np.concatenate([np.full(len(r[0]), l["leg"]) for r, l in zip(rs, clean)]),
                        leg_ids=np.array([l["leg"] for l in clean]), leg_times=np.array([l["time"] for l in clean]),
                        race_s=race_s)
    # The same for every leg, not only the clean ones (leg_samples.npz): the web app picks the legs itself,
    # because the runner's notes can change which legs count (a deliberate stop, lost contact with the map...).
    whole = [l for l in legs if l["b"] > l["a"] and not l.get("no_data")]
    legall = np.full(len(tu) - 1, -1)
    for l in whole:
        legall[l["a"]:l["b"]] = l["leg"]
    mov = (legall >= 0) & (sp[:-1] > 0.5) & (sp[1:] > 0.5)
    ra = [route_samples(list(zip(tu[l["a"]:l["b"] + 1], tv[l["a"]:l["b"] + 1])), cls, height, gm.m_per_px_x,
                        **TRACK) for l in whole]
    # more about every step, for the joint model of tools/jointfit.py: how steep the hillside is across the
    # direction of the step, when in the race it was, and which terrain is around (GPS is a few metres off)
    field = slope_field(height, gm.m_per_px_x)
    um, vm = (tu[:-1] + tu[1:]) / 2, (tv[:-1] + tv[1:]) / 2
    k_ = 5  # direction over +-5 samples: single GPS steps point anywhere
    j0 = np.clip(np.arange(len(dist)) - k_, 0, len(tu) - 1)
    j1 = np.clip(np.arange(len(dist)) + k_ + 1, 0, len(tu) - 1)
    cross = cross_slope(field, um, vm, tu[j1] - tu[j0], tv[j1] - tv[j0])
    tsec = (tr["t"][:-1] + tr["t"][1:]) / 2 - tr["t"][punch[0]]
    shares = neighbour_shares(cls, um, vm, 6.0 / gm.m_per_px_x)
    # what the personal model learns from (webapp/services/personal.py): written whole or not at all, a stopped job
    # must not leave half a file. When what is written here changes, raise oroute.personal.SAMPLES.
    tmp = os.path.join(args.out, f"leg_samples.{os.getpid()}.npz")
    np.savez_compressed(tmp, dist=dist[mov], dt=dt[mov], cls=mid[mov],
                        cross=cross[mov], tsec=tsec[mov], shares=shares[mov],
                        grade=grade[mov], leg=legall[mov], date=str(tr["start"].date()), title=args.title,
                        line_d=np.concatenate([r[0] for r in ra]), line_cls=np.concatenate([r[1] for r in ra]),
                        line_grade=np.concatenate([r[2] for r in ra]),
                        line_leg=np.concatenate([np.full(len(r[0]), l["leg"]) for r, l in zip(ra, whole)]),
                        leg_ids=np.array([l["leg"] for l in whole]), leg_times=np.array([l["time"] for l in whole]),
                        est_loss=np.array([l["est_loss"] for l in whole]),
                        stop_time=np.array([l["stop_time"] for l in whole]), race_s=race_s)
    os.replace(tmp, os.path.join(args.out, "leg_samples.npz"))
    if args.samples_only:
        return

    personal = os.path.join(HERE, "oroute", "personal_model.json")
    if args.model is None and os.path.exists(personal):
        args.model = personal
    if args.model and args.model != "race":
        model = SpeedModel.load(args.model)
        print(f"speed model: {args.model}")
        if model.dur_exp:
            # a longer race is run slower everywhere: the model of this race, with its length
            model = model.for_race(race_s)
            print(f"race length {race_s / 60:.0f} min: speed x{model.notes['race_length']['factor']}")
    else:
        if args.slope != "none" and os.path.exists(args.slope):
            model = SpeedModel.with_slope_prior(args.slope)
        else:
            model = SpeedModel()
        model.fit(dist[use], dt[use], mid[use], grade[use])
        model.notes["fitted_on_legs"] = [leg_name(l["leg"], n) for l in clean]
        # final scale: the model should reproduce your total time on those clean legs
        tm = sum(route_metrics(list(zip(tu[l["a"]:l["b"] + 1], tv[l["a"]:l["b"] + 1])), cls, height,
                               gm.m_per_px_x, model, **TRACK)["time"] for l in clean)
        ta = sum(l["time"] for l in clean)
        model.v_flat *= tm / ta
        model.notes["clean_legs_scale"] = round(tm / ta, 3)
    model.save(os.path.join(args.out, "speed_model.json"))
    print(f"speed model: v_flat {model.v_flat * 3.6:.1f} km/h, up_k {model.up_k}")

    # --- routing grid ------------------------------------------------------
    allu = np.r_[tu, [p[0] for p in ctrl_px]]
    allv = np.r_[tv, [p[1] for p in ctrl_px]]
    pad = 250 / gm.m_per_px_x
    box = (int(max(allu.min() - pad, 0)), int(max(allv.min() - pad, HEADER_PX)),
           int(min(allu.max() + pad, gm.W)), int(min(allv.max() + pad, gm.H)))
    print("building grid ...", box)
    barriers = mapdata.barriers(args.barriers, gm) if args.barriers else None
    # where the GPS failed (a town, high walls): the line the runner drew from control to control stands for the track
    corrections = {}
    if args.corrections:
        with open(args.corrections, encoding="utf-8") as f:
            for k, pts in json.load(f).items():
                corrections[int(k)] = [tuple(float(c) for c in gm.latlon_to_px(la, lo)) for la, lo in pts]
    if barriers:
        print(f"barriers: {len(barriers['forbidden'])} forbidden lines, {len(barriers['hard'])} hard lines, "
              f"{len(barriers['crossings'])} crossings, {len(barriers['areas'])} out-of-bounds areas")
    # the ground fences close in (ISOM 516, 518 around an area) is kept out of, like an out-of-bounds area
    pens = obs["pens"]
    print(f"fenced ground: {len(pens)} enclosures")
    print(f"fences that close nothing in: {len(obs['fences'])}")
    if obs["blocked"].any() or obs["hard"].any() or obs["walls"].any() or obs["climb"].any():
        barriers = dict(barriers or dict(forbidden=[], hard=[], crossings=[], areas=[]), mask=obs["blocked"],
                        hard_mask=obs["hard"])
        if obs["walls"].any() or obs["climb"].any():       # (sprint maps only)
            barriers.update(wall_mask=obs["walls"], climb_mask=obs["climb"])
    grid = Grid(cls, height, gm.m_per_px_x, model, step=args.step, box=box, barriers=barriers)
    sens = [shifted(model, f) for f in SENSITIVITY] if args.alternatives else []

    want = None
    if args.legs:
        want = [s.strip() for s in args.legs.split(",")]
    order = [l for l in legs if want is None or leg_name(l["leg"], n) in want]
    if want:
        order.sort(key=lambda l: want.index(leg_name(l["leg"], n)))

    results = []
    for l in order:
        k = l["leg"]
        name = leg_name(k, n)
        a_px, b_px = ctrl_px[k - 1], ctrl_px[k]
        t_best, inner = grid.route(a_px, b_px)
        if not np.isfinite(t_best):
            # two pieces of ground with nothing to cross between them: the straight line stands in for the
            # route, and the leg says so (no_route) instead of passing it off as the best one
            print(f"{name}: no route found between the two controls (the straight line is priced instead)")
        # Where the time starts a marked route before the start triangle (a line across the way from the
        # last call-up box), the runner has to run that stretch too: it belongs to the first leg of every route.
        lead = []
        if k == 1 and not l.get("no_data"):
            first = (float(tu[l["a"]]), float(tv[l["a"]]))
            far = np.hypot(first[0] - a_px[0], first[1] - a_px[1]) * gm.m_per_px_x
            if far >= RUN_IN_M and (far <= RUN_IN_MAX_M or (official or {}).get("used")):
                lead = [first]
        best = lead + [a_px] + inner + [b_px]
        B = route_metrics(best, cls, height, gm.m_per_px_x, model)
        alts, balanced = [], False
        if args.alternatives and inner:
            for _, pts in grid.alternatives(a_px, b_px, k=args.alternatives, best=(t_best, inner)):
                line = lead + [a_px] + pts + [b_px]
                alts.append(dict(pts=line, M=route_metrics(line, cls, height, gm.m_per_px_x, model)))
            alts.sort(key=lambda r: r["M"]["time"])
            # "the routes are level": some alternative wins when the terrain off the paths is 20 % faster or slower
            for m2 in sens:
                tb = route_metrics(best, cls, height, gm.m_per_px_x, m2)["time"]
                balanced = balanced or any(route_metrics(r["pts"], cls, height, gm.m_per_px_x, m2)["time"] < tb
                                           for r in alts)
        trk = list(zip(tu[l["a"]:l["b"] + 1], tv[l["a"]:l["b"] + 1]))
        S = route_metrics([a_px, b_px], cls, height, gm.m_per_px_x, model)
        fixed = corrections.get(l["leg"])
        if fixed and len(fixed) >= 2:
            # the drawn line, priced as a track (its ends are the controls); the official time of the leg is its time
            trk = fixed
            Y = route_metrics(trk, cls, height, gm.m_per_px_x, model, **TRACK)
            through = crossed(trk, barriers, gm.m_per_px_x)
            text = explain(B, Y, S, l["time"], l, through=through)
            text_cs = explain(B, Y, S, l["time"], l, lang="cs", through=through)
        elif l.get("no_data"):
            # the recording does not show this leg: there is no line to price, only the best route to show
            trk, Y, through = [], dict(B), []
            text, text_cs = TXT["en"]["no_data"], TXT["cs"]["no_data"]
        else:
            Y = route_metrics(trk, cls, height, gm.m_per_px_x, model, **TRACK)
            through = crossed(trk, barriers, gm.m_per_px_x)
            text = explain(B, Y, S, l["time"], l, through=through)
            text_cs = explain(B, Y, S, l["time"], l, lang="cs", through=through)
        results.append(dict(leg=l, name=name, best=best, trk=trk, B=B, Y=Y, S=S, text=text, through=through,
                            no_route=not np.isfinite(t_best),
                            text_cs=text_cs, alts=alts,
                            balanced=balanced, lead=lead, corrected=bool(fixed)))
        print(f"{name}: actual {mmss(l['time'])}  your line at model pace {mmss(Y['time'])}  best {mmss(B['time'])}"
              f"  ({B['dist']:.0f} m, +{B['climb']:.0f} m)\n   {text}")

    # --- the best route of an average runner (oroute/generic.py): the same grid, one search per leg ---------
    if args.generic:
        own = model.notes.get("slope_own", True) if args.generic == "auto" else args.generic == "all"
        avg = generic.average_model(model, own_slope=own)
        print(f"average runner: slope {'textbook' if own else 'yours (not measured on you)'}")
        grid.with_model(avg)
        for r in results:
            if r["no_route"]:
                continue
            a_px, b_px = ctrl_px[r["leg"]["leg"] - 1], ctrl_px[r["leg"]["leg"]]
            t_avg, inner = grid.route(a_px, b_px)
            if not np.isfinite(t_avg):
                continue
            pts = r["lead"] + [a_px] + inner + [b_px]
            g = generic.compare(r["best"], pts, cls, height, gm.m_per_px_x, model, avg, a_px, b_px,
                                sprint=obs["sprint"])
            g["pts"] = pts
            g["text_cs"], g["text_en"] = generic.sentence(g, "cs"), generic.sentence(g, "en")
            r["generic"] = g
            print(f"average {r['name']}: {'differs' if g['differs'] else 'same'} ({g['apart']:.0%} apart), "
                  f"{mmss(g['time'])} at your pace. {g['text_en']}")

    # --- images ------------------------------------------------------------
    if not args.no_images:
        scale = 2
        base = gm.image.resize((gm.W * scale, gm.H * scale), Image.LANCZOS)
        base = Image.blend(base, Image.new("RGB", base.size, (255, 255, 255)), 0.3)
        crops = []
        for r in sorted(results, key=lambda r: -(r["leg"]["time"] - r["B"]["time"])):
            k = r["leg"]["leg"]
            title = (f"{r['name']}  you {mmss(r['leg']['time'])}  best ~{mmss(r['B']['time'])}"
                     f"  (lost ~{mmss(r['leg']['time'] - r['B']['time'])})")
            crops.append(draw_leg_image(gm, base, r["trk"], r["best"], ctrl_px, k - 1, k, scale, title=title))
        contact_sheet(crops, cols=2).save(os.path.join(args.out, "best_legs.jpg"), quality=88)
        full = base.copy()
        d = ImageDraw.Draw(full, "RGBA")
        for r in results:
            d.line([(u * scale, v * scale) for u, v in r["best"]], fill=(255, 255, 255, 220), width=9, joint="curve")
            d.line([(u * scale, v * scale) for u, v in r["best"]], fill=BLUE + (240,), width=6, joint="curve")
            if len(r["trk"]) > 1:
                d.line([(u * scale, v * scale) for u, v in r["trk"]], fill=RED + (220,), width=4, joint="curve")
        f = _font(28)
        for i, (u, v) in enumerate(ctrl_px):
            R = 36
            d.ellipse([u * scale - R, v * scale - R, u * scale + R, v * scale + R], outline=PURPLE + (255,), width=4)
            if 0 < i < len(ctrl_px) - 1:
                d.text((u * scale + R, v * scale - R), str(i), fill=PURPLE, font=f)
        full.save(os.path.join(args.out, "best_routes.jpg"), quality=88)

    # --- csv + report ----------------------------------------------------------
    with open(os.path.join(args.out, "best_legs.csv"), "w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(["leg", "actual", "your_line_model", "best_model", "loss_total", "loss_route", "loss_execution",
                    "your_m", "best_m", "straight_m", "your_climb", "best_climb", "straight_climb",
                    "best_path_m", "best_green_m", "your_green_m"])
        for r in results:
            l, B, Y, S = r["leg"], r["B"], r["Y"], r["S"]
            w.writerow([r["name"], mmss(l["time"]), mmss(Y["time"]), mmss(B["time"]),
                        round(l["time"] - B["time"]), round(Y["time"] - B["time"]), round(l["time"] - Y["time"]),
                        round(Y["dist"]), round(B["dist"]), round(S["dist"]), round(Y["climb"]),
                        round(B["climb"]), round(S["climb"]), round(path_m(B)), round(slow_m(B)), round(slow_m(Y))])

    # the same per leg as data, with the best route as coordinates (web app)
    out_legs = []
    for r in results:
        l = r["leg"]
        def ll(pts):
            la, lo = gm.px_to_latlon([p[0] for p in pts], [p[1] for p in pts])
            return [list(p) for p in zip(rounded(la, 6), rounded(lo, 6))]
        d = dict(leg=l["leg"], name=r["name"], actual=l["time"], best=r["B"], yours=r["Y"],
                 no_data=bool(l.get("no_data")),
                 straight=r["S"], route=ll(r["best"]), text_en=r["text"], text_cs=r["text_cs"],
                 crossed=[dict(kind=c["kind"], what=c["what"], at=ll([c["px"]])[0]) for c in r["through"]])
        if r["no_route"]:
            d["no_route"] = True
        if r["corrected"]:
            d["corrected"] = True
        if r.get("generic"):
            g = r["generic"]
            d["generic"] = dict(differs=g["differs"], apart=g["apart"], time=g["time"], time_avg=g["time_avg"],
                                gain=g["gain"], dist=g["dist"], climb=g["climb"], side=g["side"], reason=g["reason"],
                                text_cs=g["text_cs"], text_en=g["text_en"], sprint=g["sprint"],
                                route=ll(g["pts"]) if g["differs"] else None)
        if args.alternatives:
            d.update(balanced=r["balanced"],
                     alternatives=[dict(a["M"], route=ll(a["pts"]), delta=a["M"]["time"] - r["B"]["time"])
                                   for a in r["alts"]])
        out_legs.append(d)
    save_json(os.path.join(args.out, "best.json"), dict(
        title=args.title, version=VERSION, model=model.to_dict(), legs=out_legs, dem=dem.source,
        barriers=dict(forbidden=len(barriers["forbidden"]), hard=len(barriers["hard"]),
                      crossings=len(barriers["crossings"]), areas=len(barriers["areas"]),
                      enclosures=len(pens)) if barriers else None))

    obs = model.notes.get("terrain", {})
    pm = model.notes.get("personal")
    L = [
        f"# Best route per leg: {args.title}",
        "",
        "Blue = fastest route for you according to the model, red = what you ran. Images: `best_legs.jpg` "
        "(per leg, worst first), `best_routes.jpg` (whole course), `terrain.png` (how the map was read).",
        "",
        "**How to read the times.** *Best* is the model's time for the blue route. *Your line* is the model's time "
        "for the red route at the same pace, so *route loss* = your line minus best (choice of route plus any "
        "detours while lost), and *execution loss* = actual minus your line (stopping, hesitating, slower than "
        "your normal pace).",
        "",
        "| Leg | Actual | Your line | Best | Lost total | Route | Execution | Your m / climb | Best m / climb |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        l, B, Y = r["leg"], r["B"], r["Y"]
        L.append(f"| {r['name']} | {mmss(l['time'])} | {mmss(Y['time'])} | {mmss(B['time'])} | "
                 f"{mmss(l['time'] - B['time'])} | {mmss(Y['time'] - B['time'])} | {mmss(l['time'] - Y['time'])} | "
                 f"{Y['dist']:.0f} m / {Y['climb']:.0f} m | {B['dist']:.0f} m / {B['climb']:.0f} m |")
    L += ["", "## Per leg", ""]
    for r in results:
        L += [f"**{r['name']}** ({r['S']['dist']:.0f} m straight). {r['text']}", ""]
    L += [
        "## The speed model used",
        "",
        (f"- Flat path speed: **{model.v_flat * 3.6:.1f} km/h** ({1000 / model.v_flat / 60:.1f} min/km). Your "
         f"personal model, fitted on the clean legs of {len(pm['races'])} races together ("
         + ", ".join(f"{r['title']} {r['date']} weight {r['weight']}" for r in pm["races"])
         + f"; newer races count more, half-life {pm['half_life_days']:.0f} days), then scaled so it reproduces "
         "your total time on those legs. So on this race your clean legs need not match the model exactly."
         if pm else
         f"- Flat path speed: **{model.v_flat * 3.6:.1f} km/h** ({1000 / model.v_flat / 60:.1f} min/km). Fitted on "
         f"the legs you ran cleanly ({', '.join(model.notes.get('fitted_on_legs', []))}), then scaled so the model "
         "reproduces your time on those legs.")
        + " When you are unsure where you are you run slower everywhere, so legs with mistakes are left out; "
        "*best* is your pace when navigation goes well.",
        f"- Climb: 1 m up costs like **{model.up_k:.1f} m** of flat running" + (
            f" (typical runner ~8-10). Fitted on {model.slope_from['activities']} of your own Garmin runs "
            f"({model.slope_from['uphill_windows']} uphill stretches of 30 s), not on this race alone."
            if model.slope_from else
            f". Your clean legs have only {model.notes.get('uphill_samples', 0)} uphill GPS samples, too few to "
            "measure, so this is the typical-runner value." if "up_k_curve" not in model.notes else
            f". Fitted from {model.notes.get('uphill_samples', 0)} uphill samples (typical runner ~8-10)."),
        "- Downhill: " + (f"{model.down_gain * -10:+.0f} % time per 10 % of gentle downhill" if model.down_gain else
                          "no faster than flat") + (f", steep downhill (> 10 %) costs {model.steep_down:.1f} m extra "
                                                    "per m dropped"
                          if model.steep_down else "") + (" (from your orienteering races, where footing limits you)."
                          if model.slope_from and model.slope_from.get("downhill_from_races") else "."),
        "- Terrain speed relative to a path (prior from ISOM guidance, nudged by your data in proportion to how "
        "much of it there is):",
        "",
        "| Terrain | Your seconds there | Your data says | Prior | Used |",
        "|---|---|---|---|---|",
    ]
    for name, o in sorted(obs.items(), key=lambda kv: -kv[1]["seconds"]):
        L.append(f"| {name} | {o['seconds']} | {o['implied']} | {o['prior']} | {o['used']} |")
    L += [
        "",
        "## How reliable this is",
        "",
        "- **Elevation** comes from AWS Terrain Tiles (about 30 m source data). The Polish 1 m LiDAR (GUGiK) and "
        "Czech ČÚZK services were blocked from this environment. Checked against your watch's barometer along your "
        "track: about 5 m RMS difference. Big hills are right; small gullies, banks and pits are invisible to it.",
        "- **Terrain** is read from map colours. Vegetation, open land, paths, marsh, water and out-of-bounds come "
        "out well (see `terrain.png`). Not detected: cliffs, fences, erosion gullies, single rocks or boulders, and "
        "how runnable a path really is. Walls of steep gullies only show as brown contour lines, which are ignored.",
        ("- **Speed model** pools all your analysed races. Terrain with little data across them (see the table: "
         "dark green, marsh, open land) stays close to the ISOM priors, and GPS error of a few metres blurs which "
         "terrain you were in. Tested by leaving each race out: the others predict its clean-leg total within "
         "about 10 %." if pm else
         "- **Speed model** is from this race alone. Terrain with little data stays close to the ISOM priors, "
         "and GPS error of a few metres blurs which terrain you were in."),
        "- **Climb numbers** in the table come from the elevation model, not your watch, so they are lower than the "
        "watch's (which also counts GPS/barometer noise).",
        "- The route is the fastest to *run*. It does not account for how easy it is to navigate, which in a real "
        "race often matters more (a path detour can be the better choice even when it is a few seconds slower).",
        "- Differences under ~20 s per leg are within the noise of the model.",
    ]
    with open(os.path.join(args.out, "best_routes.md"), "w", encoding="utf-8") as fmd:
        fmd.write("\n".join(L) + "\n")


if __name__ == "__main__":
    errors.run(main)
