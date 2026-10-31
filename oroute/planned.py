"""Price the route a runner planned for a leg (a line drawn on the map) the way bestroute.py prices the best
route and the line that was run: same terrain, same elevation, same speed model, routing.route_metrics.

usage: python3 -m oroute.planned MAPONLY.kmz OUT_DIR PLANS.json RESULT.json
           [--dem aws|cuzk|auto] [--terrain-cache FILE] [--barriers FILE]

OUT_DIR      output folder of the race: analysis.json (analyze.py) and best/ (bestroute.py: best.json,
             speed_model.json and the elevation it used)
PLANS.json   {"legs": [{"leg": 3, "planned": [[lat, lon], ...]}, ...]}
RESULT.json  {"legs": [{"leg": 3, "plan": {time, dist, climb, ...}, "delta": s against the best route,
             "off_m": how far the track was from the plan, "crossed": [{kind, what, at: [lat, lon]}],
             "text_cs": ..., "text_en": ...}, ...]}

Pass --dem, --terrain-cache and --barriers as they were passed to bestroute.py: the plan is priced on the
terrain the best route was found on (mapdata.obstacles: a fence is no path), and what it goes through that
the best route must not (a railway away from a crossing, an out-of-bounds area, fenced ground:
routing.crossed) is said in the sentence and marked, as it is for the track.
"""
import argparse
import json
import os

import numpy as np

from . import mapdata
from . import terrain as T
from .kmzmap import GeoMap
from .routing import HARD_CROSS_S, crossed, route_metrics
from .speedmodel import SpeedModel

NOISE_S = 15.0     # routes closer than this in model time are equally good (as in bestroute.explain)
EXEC_S = 30.0      # slower than the model on a line by more than this = time lost in the execution
OFF_M = 40.0       # the track stayed on the plan when nine tenths of it ran within this distance of it
PAD_PX = 4         # the map is cut this far around a plan before it is priced
AROUND_M = 120.0   # the obstacles of the map are read this far around a plan
SLOW = [T.NAMES[c] for c in (T.SLOW, T.WALK, T.FIGHT, T.UNDERGROWTH, T.MARSH)]


def fence_crossings(px, hard):
    """How many times the line px (map pixels) climbs over a fence of the map (mapdata.obstacles hard)."""
    if not hard.any() or len(px) < 2:
        return 0
    H, W = hard.shape
    pts = []
    for (u0, v0), (u1, v1) in zip(px[:-1], px[1:]):
        k = max(1, int(np.hypot(u1 - u0, v1 - v0) * 2))
        t = np.arange(k) / k
        pts.append(np.c_[u0 + t * (u1 - u0), v0 + t * (v1 - v0)])
    p = np.vstack(pts)
    u = np.clip(p[:, 0].round().astype(int), 0, W - 1)
    v = np.clip(p[:, 1].round().astype(int), 0, H - 1)
    on = hard[v, u]
    return int((on[1:] & ~on[:-1]).sum())


def mmss(s):
    s = int(round(abs(s)))
    return f"{s // 60}:{s % 60:02d}"


def slow_m(m):
    return sum(v for k, v in m["mix"].items() if k in SLOW)


def path_m(m):
    return m["mix"].get(T.NAMES[T.PATH], 0.0)


def price(pts_px, cls, height_at, mpp, model):
    """route_metrics of a line in map px. height_at(u, v) gives the heights of a block of pixels, so only
    the part of the map around the line has to be looked up (the numbers are the same as on the whole map)."""
    pts = np.asarray(pts_px, float)
    H, W = cls.shape
    u0 = int(np.clip(np.floor(pts[:, 0].min()) - PAD_PX, 0, W - 1))
    v0 = int(np.clip(np.floor(pts[:, 1].min()) - PAD_PX, 0, H - 1))
    u1 = int(np.clip(np.ceil(pts[:, 0].max()) + PAD_PX + 1, u0 + 1, W))
    v1 = int(np.clip(np.ceil(pts[:, 1].max()) + PAD_PX + 1, v0 + 1, H))
    v, u = np.mgrid[v0:v1, u0:u1].astype(float)
    return route_metrics(pts - (u0, v0), cls[v0:v1, u0:u1], height_at(u, v), mpp, model)


def off_plan(track_xy, plan_xy):
    """How far the track ran from the planned line: the distance (m) nine tenths of its points stay within."""
    p, q = np.asarray(track_xy, float), np.asarray(plan_xy, float)
    if len(p) == 0 or len(q) < 2:
        return None
    a, d = q[:-1], np.diff(q, axis=0)
    n = np.maximum((d ** 2).sum(1), 1e-9)
    t = np.clip(((p[:, None] - a[None]) * d[None]).sum(-1) / n, 0, 1)
    near = a[None] + t[..., None] * d[None]
    return float(np.percentile(np.hypot(*(p[:, None] - near).transpose(2, 0, 1)).min(1), 90))


def _reason(P, B, model):
    """The main thing that makes the plan slower than the best route: (key, metres) or None. The candidates
    are compared by roughly how many seconds each costs."""
    pace = 1.0 / model.v_flat
    forest, green = model.factors[T.FOREST], model.factors[T.SLOW]
    out = []
    if P["climb"] - B["climb"] > 8:
        out.append(((P["climb"] - B["climb"]) * model.up_k * pace, "climb", P["climb"] - B["climb"]))
    if slow_m(P) - slow_m(B) > 30:
        out.append(((slow_m(P) - slow_m(B)) * pace * (1 / green - 1 / forest), "green", slow_m(P) - slow_m(B)))
    if path_m(B) - path_m(P) > 60:
        out.append(((path_m(B) - path_m(P)) * pace * (1 / forest - 1), "path", path_m(B) - path_m(P)))
    if P["dist"] - B["dist"] > max(50.0, 0.15 * B["dist"]):
        out.append(((P["dist"] - B["dist"]) * pace / forest, "dist", P["dist"] - B["dist"]))
    return max(out)[1:] if out else None


# the sentences explain() builds, per language (same rules, only the wording differs)
TXT = {
    "en": dict(
        slower="The plan was {t} slower than the best route",
        climb=", mainly because of {x:.0f} m more climb", green=", mainly because of {x:.0f} m more in green or marsh",
        path=", mainly because it has {x:.0f} m less on paths", dist=", mainly because it is {x:.0f} m longer",
        faster="The plan comes out {t} faster than the best route the model found: it probably leads through "
               "a place the model must not enter (an out-of-bounds area or a forbidden crossing), or the "
               "difference is noise of the model.",
        faster_through="The plan comes out {t} faster than the best route because it {w}, where the best route "
                       "must not go.",
        also_through=" Mind: the plan {w}, where the best route must not go.",
        through=dict(railway="crosses the railway away from a crossing", motorway="crosses the motorway away "
                     "from a crossing", manual="crosses a line drawn as forbidden",
                     area="leads through an out-of-bounds area", enclosure="leads through fenced ground"),
        good="The plan was good",
        good_exec=", the loss of {t} came from the execution",
        good_clean=" and you ran the leg without a loss.",
        more_exec=" Another {t} was lost in the execution",
        kept=": you kept to the plan, only slower than your pace on it.",
        left=": you left the plan by up to {x:.0f} m.",
        other=" You did not run the plan (up to {x:.0f} m from it) and the line you ran was {t} faster.",
        end="."),
    "cs": dict(
        slower="Plán byl o {t} pomalejší než nejlepší postup",
        climb=", hlavně kvůli {x:.0f} m stoupání navíc", green=", hlavně kvůli {x:.0f} m v zelené nebo bažině navíc",
        path=", hlavně proto, že vede o {x:.0f} m méně po cestách", dist=", hlavně proto, že je o {x:.0f} m delší",
        faster="Plán vychází o {t} rychlejší než nejlepší postup, který model našel: nejspíš vede místem, kam "
               "model nesmí (zakázaný prostor nebo přechod), nebo je rozdíl v šumu modelu.",
        faster_through="Plán vychází o {t} rychlejší než nejlepší postup, protože {w}, kudy nejlepší postup nesmí.",
        also_through=" Pozor: plán {w}, kudy nejlepší postup nesmí.",
        through=dict(railway="kříží železnici mimo přechod", motorway="kříží dálnici mimo přechod",
                     manual="kříží ručně nakreslenou zakázanou čáru", area="vede zakázaným prostorem",
                     enclosure="vede přes oplocenku"),
        good="Plán byl dobrý",
        good_exec=", ztráta {t} vznikla při provedení",
        good_clean=" a úsek jsi zaběhl bez ztráty.",
        more_exec=" Dalších {t} jsi ztratil při provedení",
        kept=": plánu ses držel, jen pomaleji, než odpovídá tvému tempu.",
        left=": od plánu ses odchýlil až o {x:.0f} m.",
        other=" Plán jsi neběžel (až {x:.0f} m od něj) a postup, který jsi běžel, byl o {t} rychlejší.",
        end="."),
}


def explain(P, B, Y, actual, model, off_m=None, lang="en", through=()):
    """One or two sentences on the plan (P) against the best route (B), the line that was run (Y) and the
    time the leg really took. P, B, Y: route_metrics; off_m: off_plan() of the track; through: what the plan
    goes through that the best route must not (routing.crossed)."""
    x = TXT[lang]
    d = P["time"] - B["time"]
    lost = actual - P["time"]                    # what the leg took beyond the plan at the runner's own pace
    how = x["end"] if off_m is None else x["kept"] if off_m <= OFF_M else x["left"].format(x=off_m)
    w = []
    for c in through:
        if c["what"] in x["through"] and x["through"][c["what"]] not in w:
            w.append(x["through"][c["what"]])
    w = (" a " if lang == "cs" else " and ").join(w)
    if d < -NOISE_S:
        return x["faster_through"].format(t=mmss(d), w=w) if w else x["faster"].format(t=mmss(d))
    also = x["also_through"].format(w=w) if w else ""
    if d <= NOISE_S:
        if lost > EXEC_S:
            return x["good"] + x["good_exec"].format(t=mmss(lost)) + how + also
        return x["good"] + x["good_clean"] + also
    why = _reason(P, B, model)
    out = x["slower"].format(t=mmss(d)) + (x[why[0]].format(x=why[1]) if why else "") + x["end"]
    if lost > EXEC_S:
        out += x["more_exec"].format(t=mmss(lost)) + how
    elif off_m is not None and off_m > OFF_M and P["time"] - Y["time"] > NOISE_S:
        out += x["other"].format(x=off_m, t=mmss(P["time"] - Y["time"]))
    return out + also


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kmz")
    ap.add_argument("out")
    ap.add_argument("plans")
    ap.add_argument("result")
    ap.add_argument("--dem", default="aws", choices=("aws", "cuzk", "auto"))
    ap.add_argument("--terrain-cache", metavar="FILE")
    ap.add_argument("--barriers", metavar="FILE")
    args = ap.parse_args()
    best_dir = os.path.join(args.out, "best")
    with open(os.path.join(best_dir, "best.json"), encoding="utf-8") as f:
        best = json.load(f)
    with open(os.path.join(args.out, "analysis.json"), encoding="utf-8") as f:
        analysis = json.load(f)
    with open(args.plans, encoding="utf-8") as f:
        plans = json.load(f)["legs"]
    gm = GeoMap.from_kmz(args.kmz)
    cls = mapdata.terrain(gm, args.kmz, args.terrain_cache)
    dem = mapdata.elevation(gm, best_dir, args.dem, used=best.get("dem"))
    model = SpeedModel.load(os.path.join(best_dir, "speed_model.json"))
    height_at = lambda u, v: dem.height(*gm.px_to_latlon(u, v))
    lines = mapdata.barriers(args.barriers, gm) if args.barriers else None
    pad = int(AROUND_M / gm.m_per_px_x)
    routes = {l["leg"]: l for l in best["legs"]}
    spans = {l["leg"]: (l["a"], l["b"]) for l in analysis["legs"]}
    track = analysis["track"]
    ctrl = [tuple(float(a) for a in gm.latlon_to_px(c["lat"], c["lon"])) for c in analysis.get("course") or []]
    out = []
    for p in plans:
        r = routes.get(p["leg"])
        if r is None or len(p["planned"]) < 2:
            continue
        la, lo = np.array(p["planned"], float).T
        px = np.c_[gm.latlon_to_px(la, lo)]
        # the terrain and the obstacles as the best route saw them, read around the plan only
        obs = mapdata.obstacles(gm, cls, (int(px[:, 0].min()) - pad, int(px[:, 1].min()) - pad,
                                          int(px[:, 0].max()) + pad, int(px[:, 1].max()) + pad), open_at=ctrl)
        P = price(px, obs["cls"], height_at, gm.m_per_px_x, model)
        # a fence the plan climbs over costs what it costs the best route (routing.HARD_CROSS_S)
        n = fence_crossings(px, obs["hard"])
        if n:
            P = dict(P, time=P["time"] + n * HARD_CROSS_S, fences=n)
        through = crossed([tuple(q) for q in px],
                          dict(lines or dict(forbidden=[], hard=[], crossings=[], areas=[]), mask=obs["blocked"]),
                          gm.m_per_px_x)
        a, b = spans[p["leg"]]
        off = off_plan(np.c_[gm.to_xy(np.array(track["lat"][a:b + 1]), np.array(track["lon"][a:b + 1]))],
                       np.c_[gm.to_xy(la, lo)])
        text = {lang: explain(P, r["best"], r["yours"], r["actual"], model, off, lang, through) for lang in TXT}
        at = lambda c: [round(float(v), 6) for v in gm.px_to_latlon(*c["px"])]
        out.append(dict(leg=p["leg"], plan=P, delta=P["time"] - r["best"]["time"], off_m=off,
                        crossed=[dict(kind=c["kind"], what=c["what"], at=at(c)) for c in through],
                        text_cs=text["cs"], text_en=text["en"]))
        print(f"{r['name']}: plan {mmss(P['time'])} ({P['dist']:.0f} m, +{P['climb']:.0f} m), best "
              f"{mmss(r['best']['time'])}\n   {text['en']}")
    with open(args.result, "w", encoding="utf-8") as f:
        json.dump(dict(legs=out), f)


if __name__ == "__main__":
    main()
