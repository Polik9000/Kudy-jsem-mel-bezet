"""Why the best route is the best for *you*: the best route of an average runner next to yours.

The average runner is the textbook model (speedmodel.SpeedModel() as it is: ISOM terrain factors, the
textbook slope, about Naismith) at your own speed on a flat path, so the two routes differ by the shape of the
models only, not by fitness. When the runner has no slope of their own (no Garmin export: their slope is the
default prior), the average runner gets their slope too and only the terrain can differ.

On every leg the routing grid is searched once more with that model (no alternatives). The two routes differ
when either runs farther than APART_M from the other on more than APART_SHARE of its length. The reason is the
part of the models (uphill, downhill, one terrain) that moves the choice most towards your route: each part of
the average model is swapped for yours in turn (and back), and the change of the time difference of the two
routes is measured.

When the routes differ by how steeply they climb or descend only (not by how much, nor by terrain), the
sentence names the stretch of the average route with the most descent (or climb): what it runs on (a path or a
terrain) and whether it lies in a valley, on a ridge or on a slope (the heights HILL_SIDE_M to either side).
On a sprint map (sprint=True) the words of ISSprOM are used: open area, not meadow; paved areas, not paths.
"""
import numpy as np
from scipy.spatial import cKDTree

from . import terrain as T
from .routing import route_metrics, route_samples
from .speedmodel import SpeedModel

APART_M = 30.0        # two routes run apart where they are farther than this from each other ...
APART_SHARE = 0.2     # ... and they differ when that is more than this share of the length of one of them
LEVEL_S = 3.0         # the average route costs you at most this much more: both are as good for you
FACTOR_DIFF = 0.03    # terrain factors closer than this (relative) are the same
MIN_CLASS_M = 10.0    # a terrain counts as a reason only when one of the routes has this much of it
HILL_M = 8.0          # climbs closer than this are the same
CLASS_M = 25.0        # metres of one terrain closer than this are the same

HILL_WINDOW_M = 60.0  # the stretch of a route with the most descent (or climb) is this long (or the whole route)
HILL_SIDE_M = 25.0    # it lies in a valley when the ground this far to both sides of its middle is higher ...
HILL_SIDE_DH = 1.5    # ... by this much at least (on a ridge: lower), else on a slope
PATH_SHARE = 0.5      # ... and runs on a path when at least this share of it is path
STEEPER = 0.15        # one route descends (climbs) more steeply than the other when its grade is this much steeper
LONGER = 0.05         # ... and is longer when it is this much longer

PARTS_UP, PARTS_DOWN = ("up_k",), ("down_gain", "steep_down")


def average_model(model, own_slope=True):
    """The average runner for `model`: textbook slope and ISOM factors at the flat speed of the model.
    own_slope False: the slope of `model` was not measured on the runner, the average runner gets it too."""
    g = SpeedModel(v_flat=model.v_flat)
    if not own_slope:
        g.up_k, g.down_gain, g.steep_down = model.up_k, model.down_gain, model.steep_down
    g.notes = dict(average=True, own_slope=bool(own_slope))
    return g


def _copy(m, **kw):
    d = dict(v_flat=m.v_flat, up_k=m.up_k, down_gain=m.down_gain, steep_down=m.steep_down, factors=dict(m.factors))
    d.update(kw)
    return SpeedModel(**d)


def _dense(pts, step_px):
    pts = np.asarray(pts, float)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.r_[0, np.cumsum(seg)]
    q = np.arange(0, s[-1] + 1e-9, max(step_px, 1e-6))
    return np.c_[np.interp(q, s, pts[:, 0]), np.interp(q, s, pts[:, 1])]


def apart(p, q, mpp, far_m=APART_M, sample_m=2.0):
    """Share of the length of one route that runs farther than far_m from the other: the larger of the two
    (routes in map px)."""
    if len(p) < 2 or len(q) < 2:
        return 0.0
    a, b = _dense(p, sample_m / mpp), _dense(q, sample_m / mpp)
    da = cKDTree(b).query(a)[0] * mpp
    db = cKDTree(a).query(b)[0] * mpp
    return float(max((da > far_m).mean(), (db > far_m).mean()))


def side(route, ref, a, b):
    """'left' or 'right': on which side of `ref` the route runs, looking from a to b (map px, v down); None
    when it is not clearly one side."""
    ab = np.subtract(b, a)
    n = np.hypot(*ab)
    if n < 1e-9:
        return None

    def offset(pts):
        d = _dense(pts, 1.0) - np.asarray(a, float)
        return (ab[0] * d[:, 1] - ab[1] * d[:, 0]) / n        # > 0: right of a->b on the picture

    o = offset(route)
    o = o - np.interp(np.linspace(0, 1, len(o)), np.linspace(0, 1, len(offset(ref))), offset(ref))
    far = np.abs(o) > 3.0
    if not far.any():
        return None
    right = (o[far] > 0).mean()
    return "right" if right >= 0.75 else "left" if right <= 0.25 else None


def _grade(pts, cls, height, mpp, up=True):
    """Typical grade of the climbs (up) or descents of a route, weighted by length."""
    d, _, g, _ = route_samples(pts, cls, height, mpp)
    on = g > 0.02 if up else g < -0.02
    return float(np.average(g[on], weights=d[on])) if on.any() else (0.1 if up else -0.1)


def hill_stretch(pts, cls, height, mpp, up=False):
    """The stretch of a route (map px) with the most descent (up: climb) over HILL_WINDOW_M: dict(drop (m),
    grade (> 0), on (the terrain class it mostly runs on; T.PATH from PATH_SHARE), land ("valley", "ridge",
    "slope"), px (its middle)); None when the route does not go down (up) at all."""
    if len(pts) < 2:
        return None
    d, cm, g, h = route_samples(pts, cls, height, mpp)
    if not len(d):
        return None
    dh = np.diff(h) if up else -np.diff(h)
    n = max(1, min(len(d), int(round(HILL_WINDOW_M / max(float(np.median(d)), 1e-6)))))
    run = np.convolve(dh, np.ones(n), "valid")
    i = int(np.argmax(run))
    drop = float(run[i])
    if drop <= 0.5:
        return None
    sl = slice(i, i + n)
    length = float(d[sl].sum())
    path = float(d[sl][cm[sl] == T.PATH].sum()) >= PATH_SHARE * length
    if path:
        on = T.PATH
    else:
        ks, w = np.unique(cm[sl], return_counts=True)
        on = int(ks[np.argmax(w)])
    # the middle of the stretch, the direction of the route there, and the ground to either side
    p = _dense(pts, 2.0 / mpp)
    j = min(len(p) - 1, i + n // 2)
    a, b = p[max(j - 3, 0)], p[min(j + 3, len(p) - 1)]
    t = np.subtract(b, a)
    t = t / max(np.hypot(*t), 1e-9)
    side = np.array([-t[1], t[0]]) * (HILL_SIDE_M / mpp)
    hh, hw = height.shape[:2]
    at = lambda q: float(height[int(np.clip(round(q[1]), 0, hh - 1)), int(np.clip(round(q[0]), 0, hw - 1))])
    hm, hl, hr = at(p[j]), at(p[j] + side), at(p[j] - side)
    land = ("valley" if min(hl, hr) - hm >= HILL_SIDE_DH else "ridge" if hm - max(hl, hr) >= HILL_SIDE_DH
            else "slope")
    return dict(drop=round(drop, 1), grade=round(drop / max(length, 1e-6), 3), on=on, land=land,
                px=(float(p[j][0]), float(p[j][1])))


def _parts(model, avg, mixes):
    """The parts in which the two models differ: ('up',), ('down',), ('terrain', class id)."""
    out = []
    if abs(model.up_k - avg.up_k) > 1e-6:
        out.append(("up", None))
    if abs(model.down_gain - avg.down_gain) > 1e-6 or abs(model.steep_down - avg.steep_down) > 1e-6:
        out.append(("down", None))
    for c, f in model.factors.items():
        fa = avg.factors.get(c, 0.0)
        if c == T.PATH or f <= 0 or fa <= 0 or abs(f / fa - 1) < FACTOR_DIFF:
            continue
        if any(m.get(T.NAMES[c], 0.0) >= MIN_CLASS_M for m in mixes):
            out.append(("terrain", c))
    return out


def _swap(base, src, part):
    kind, c = part
    if kind == "up":
        return _copy(base, up_k=src.up_k)
    if kind == "down":
        return _copy(base, down_gain=src.down_gain, steep_down=src.steep_down)
    f = dict(base.factors)
    f[c] = src.factors[c]
    return _copy(base, factors=f)


def compare(mine, avg_route, cls, height, mpp, model, avg, a_px, b_px, sprint=False):
    """mine, avg_route: your best route and the average runner's (map px, the same ends). Returns a dict:
    differs, apart (share), time (the average route at your pace), gain (that minus your best), time_avg
    (the average route at the average pace), dist, climb, side, reason=dict(kind, cls, pct) or None,
    hill / hill_mine (hill_stretch of both routes, when the reason is uphill or downhill), sprint (the map is
    a sprint map: the words of the sentence), and the metrics of both routes under your model (M_mine, M_avg)."""
    M_mine = route_metrics(mine, cls, height, mpp, model)
    M_avg = route_metrics(avg_route, cls, height, mpp, model)
    t_avg_avg = route_metrics(avg_route, cls, height, mpp, avg)["time"]
    share = apart(mine, avg_route, mpp)
    out = dict(differs=share > APART_SHARE, apart=round(share, 3), time=M_avg["time"], time_avg=t_avg_avg,
               gain=M_avg["time"] - M_mine["time"], dist=M_avg["dist"], climb=M_avg["climb"],
               side=None, reason=None, hill=None, hill_mine=None, sprint=bool(sprint), M_mine=M_mine, M_avg=M_avg)
    if not out["differs"]:
        return out
    out["side"] = side(avg_route, mine, a_px, b_px)

    def delta(m):  # > 0: your route is the faster one under model m
        return route_metrics(avg_route, cls, height, mpp, m)["time"] - route_metrics(mine, cls, height, mpp, m)["time"]

    d_avg, d_mine = delta(avg), out["gain"]
    best, why = 0.0, None
    for part in _parts(model, avg, (M_mine["mix"], M_avg["mix"])):
        # the part of your model put into the average one, and the average part put into yours: the mean of both
        w = 0.5 * ((delta(_swap(avg, model, part)) - d_avg) + (d_mine - delta(_swap(model, avg, part))))
        if w > best:
            best, why = w, part
    if why is None:
        return out
    kind, c = why
    if kind in ("up", "down"):
        hilly = mine if (M_mine["climb"] >= M_avg["climb"]) == (kind == "up") else avg_route
        g = _grade(hilly, cls, height, mpp, up=kind == "up")
        pct = float(avg.slope_mult(g) / model.slope_mult(g) - 1)
        out["hill"] = hill_stretch(avg_route, cls, height, mpp, up=kind == "up")
        out["hill_mine"] = hill_stretch(mine, cls, height, mpp, up=kind == "up")
    else:
        pct = float(model.factors[c] / avg.factors[c] - 1)
    out["reason"] = dict(kind=kind, cls=None if c is None else T.NAMES[c], pct=round(pct, 3), weight=round(best, 1))
    return out


# --- sentences ------------------------------------------------------------------------------------------

def mmss(s):
    s = int(round(s))
    return f"{'-' if s < 0 else ''}{abs(s) // 60}:{abs(s) % 60:02d}"


CS_ACC = {T.FOREST: "les", T.SLOW: "světle zelenou", T.WALK: "zelenou", T.FIGHT: "tmavě zelenou",
          T.ROUGH_OPEN: "hrubou louku", T.OPEN: "louku", T.UNDERGROWTH: "podrost", T.MARSH: "bažinu"}
CS_GEN = {T.FOREST: "lesa", T.SLOW: "světle zelené", T.WALK: "zelené", T.FIGHT: "tmavě zelené",
          T.ROUGH_OPEN: "hrubé louky", T.OPEN: "louky", T.UNDERGROWTH: "podrostu", T.MARSH: "bažiny"}
CS_LOC = {T.FOREST: "v lese", T.SLOW: "ve světle zelené", T.WALK: "v zelené", T.FIGHT: "v tmavě zelené",
          T.ROUGH_OPEN: "na hrubé louce", T.OPEN: "na louce", T.UNDERGROWTH: "v podrostu", T.MARSH: "v bažině"}
EN = {T.FOREST: "forest", T.SLOW: "light green", T.WALK: "green", T.FIGHT: "dark green", T.ROUGH_OPEN: "rough open",
      T.OPEN: "open land", T.UNDERGROWTH: "undergrowth", T.MARSH: "marsh"}
# a sprint map (ISSprOM 2019) has open areas, not meadows (accusative, genitive, locative)
SPRINT_CS = {T.OPEN: ("otevřenou plochu", "otevřené plochy", "na otevřené ploše"),
             T.ROUGH_OPEN: ("hrubou otevřenou plochu", "hrubé otevřené plochy", "na hrubé otevřené ploše")}
SPRINT_EN = {T.OPEN: "open area", T.ROUGH_OPEN: "rough open area"}


def words(lang="cs", sprint=False):
    """(accusative, genitive, locative) of the terrain classes for the sentences (English: one form)."""
    if lang != "cs":
        en = {**EN, **SPRINT_EN} if sprint else EN
        return en, en, en
    acc, gen, loc = dict(CS_ACC), dict(CS_GEN), dict(CS_LOC)
    if sprint:
        for c, (a, g, lc) in SPRINT_CS.items():
            acc[c], gen[c], loc[c] = a, g, lc
    return acc, gen, loc


TXT = {
    "cs": dict(
        same="Tady by stejně běžel každý.",
        level="Běžec s průměrným modelem by {what}{side}; tobě by ten postup trval skoro stejně ({t} proti {you}).",
        lead="Běžec s průměrným modelem by {what}{side}; tobě by ten postup trval {t}.",
        mine="Pro tebe je rychlejší {what} ({you})",
        because=", protože {why}.",
        left=" vlevo", right=" vpravo",
        around_hill="kopec obíhal", over_hill="šel přes kopec", around="{acc} obíhal", over="běžel přes {acc}",
        more_path="běžel víc po cestách", less_path="běžel míň po cestách", other="běžel jinudy",
        detour="běžel oklikou", shortcut="běžel zkratkou",
        steep_down="seběhl {where}", gentle_down="klesal pozvolna {where}",
        steep_up="vyběhl prudce {where}", gentle_up="stoupal pozvolna {where}",
        valley="údolím", ridge="po hřbetu", slope="po svahu", path_slope="po cestě", path_valley="údolím po cestě",
        path_ridge="po cestě po hřbetu", other_where="{land} přes {acc}",
        y_over_hill="přes kopec", y_around_hill="kolem kopce", y_over="přes {acc}", y_around="kolem {gen}",
        y_path="po cestách", y_off_path="mimo cesty", y_other="tvůj nejlepší postup",
        y_longer="tvůj delší nejlepší postup", y_shorter="tvůj kratší nejlepší postup",
        y_gentle_down="tvůj nejlepší postup s mírnějším klesáním", y_steep_down="tvůj nejlepší postup s prudším klesáním",
        y_gentle_up="tvůj nejlepší postup s mírnějším stoupáním", y_steep_up="tvůj nejlepší postup s prudším stoupáním",
        up_fast="do kopce běžíš o {p} % rychleji než průměr", up_slow="do kopce jsi o {p} % pomalejší než průměr",
        down_fast="z kopce běžíš o {p} % rychleji než průměr", down_slow="z kopce jsi o {p} % pomalejší než průměr",
        t_fast="{loc} běžíš o {p} % rychleji než průměr", t_slow="{loc} jsi o {p} % pomalejší než průměr"),
    "en": dict(
        same="Any runner would take this route here.",
        level="A runner with the average model would {what}{side}; for you that route takes about as long "
              "({t} against {you}).",
        lead="A runner with the average model would {what}{side}; that route would take you {t}.",
        mine="For you it is faster {what} ({you})",
        because=", because {why}.",
        left=" on the left", right=" on the right",
        around_hill="go round the hill", over_hill="go over the hill", around="go round the {acc}",
        over="go through the {acc}", more_path="run more on paths", less_path="run less on paths",
        other="go another way", detour="take a detour", shortcut="take a shortcut",
        steep_down="run down {where}", gentle_down="go down gently {where}",
        steep_up="run up steeply {where}", gentle_up="climb gently {where}",
        valley="along the valley", ridge="along the ridge", slope="across the slope", path_slope="on the path",
        path_valley="along the valley on the path", path_ridge="on the path along the ridge",
        other_where="{land} across the {acc}",
        y_over_hill="over the hill", y_around_hill="round the hill", y_over="through the {acc}",
        y_around="round the {acc}", y_path="on the paths", y_off_path="off the paths", y_other="your best route",
        y_longer="your longer best route", y_shorter="your shorter best route",
        y_gentle_down="your best route with its gentler descent", y_steep_down="your best route with its steeper descent",
        y_gentle_up="your best route with its gentler climb", y_steep_up="your best route with its steeper climb",
        up_fast="you run uphill {p} % faster than average", up_slow="you are {p} % slower uphill than average",
        down_fast="you run downhill {p} % faster than average", down_slow="you are {p} % slower downhill than average",
        t_fast="you run {p} % faster than average in {loc}", t_slow="you are {p} % slower than average in {loc}"),
}
# ... and its paths are the paved areas and passages one runs on
SPRINT_TXT = {
    "cs": dict(more_path="běžel víc po zpevněných plochách", less_path="běžel míň po zpevněných plochách",
               y_path="po zpevněných plochách", y_off_path="mimo zpevněné plochy", path_slope="po zpevněné ploše",
               path_valley="údolím po zpevněné ploše", path_ridge="po zpevněné ploše po hřbetu"),
    "en": dict(more_path="run more on paved areas", less_path="run less on paved areas", y_path="on the paved areas",
               y_off_path="off the paved areas", path_slope="on the paved area",
               path_valley="along the valley on the paved area", path_ridge="on the paved area along the ridge"),
}


def _class_id(name):
    return T.NAMES.index(name) if name in T.NAMES else None


def _choice(r, why, x, acc):
    """(what the average runner does, what you do instead) for the leg: keys of x, or the phrase itself
    after a "=" for the stretch the average runner goes down (up) on."""
    A, M = r["M_avg"], r["M_mine"]
    dc = A["climb"] - M["climb"]
    c = _class_id(why["cls"]) if why and why["cls"] else None
    dm = A["mix"].get(why["cls"], 0.0) - M["mix"].get(why["cls"], 0.0) if c is not None else 0.0
    dp = A["mix"].get("path/road", 0.0) - M["mix"].get("path/road", 0.0)
    hill = bool(why) and why["kind"] in ("up", "down")
    if hill and abs(dc) >= HILL_M:
        return ("around_hill", "y_over_hill") if dc < 0 else ("over_hill", "y_around_hill")
    # (the forest is what is everywhere else: "round the forest" says nothing)
    if c is not None and c != T.FOREST and abs(dm) >= CLASS_M:
        return ("around", "y_over") if dm < 0 else ("over", "y_around")
    if abs(dp) >= CLASS_M:
        return ("more_path", "y_off_path") if dp > 0 else ("less_path", "y_path")
    if abs(dc) >= HILL_M:
        return ("around_hill", "y_over_hill") if dc < 0 else ("over_hill", "y_around_hill")
    ratio = A["dist"] / max(M["dist"], 1e-6)
    longer = "y_shorter" if ratio >= 1 + LONGER else "y_longer" if ratio <= 1 - LONGER else None
    h = r.get("hill") if hill else None
    if h:
        # the routes differ by how steeply they go down (up): where the average one does it, and on what
        where = (x[f"path_{h['land']}"] if h["on"] == T.PATH else x[h["land"]] if h["on"] == T.FOREST
                 else x["other_where"].format(land=x[h["land"]], acc=acc.get(h["on"], "")))
        hm = r.get("hill_mine")
        g_mine = hm["grade"] if hm else 0.0
        steep = g_mine <= h["grade"] * (1 - STEEPER) or (g_mine < h["grade"] * (1 + STEEPER) and not longer)
        what = x[f"{'steep' if steep else 'gentle'}_{why['kind']}"].format(where=where)
        if longer:
            mine = longer
        elif g_mine <= h["grade"] * (1 - STEEPER):
            mine = f"y_gentle_{why['kind']}"
        elif g_mine >= h["grade"] * (1 + STEEPER):
            mine = f"y_steep_{why['kind']}"
        else:
            mine = "y_other"
        return "=" + what, mine
    if longer:
        return ("detour", longer) if longer == "y_shorter" else ("shortcut", longer)
    return "other", "y_other"


def sentence(r, lang="cs"):
    """The sentence of compare() for the leg panel (r["sprint"]: in the words of a sprint map)."""
    sprint = bool(r.get("sprint"))
    x = dict(TXT[lang], **(SPRINT_TXT[lang] if sprint else {}))
    if not r["differs"]:
        return x["same"]
    sd = x.get(r["side"], "") if r["side"] else ""
    you, t = mmss(r["M_mine"]["time"]), mmss(r["time"])
    why = r["reason"]
    accs, gens, locs = words(lang, sprint)
    c = _class_id(why["cls"]) if why and why["cls"] else None
    acc, gen = accs.get(c, ""), gens.get(c, "")
    what, mine = _choice(r, why, x, accs)
    what = what[1:] if what.startswith("=") else x[what].format(acc=acc, gen=gen)
    if r["gain"] < LEVEL_S or why is None:
        return x["level"].format(what=what, side=sd, t=t, you=you)
    p = max(1, int(round(abs(why["pct"]) * 100)))
    fast = why["pct"] > 0
    if why["kind"] == "up":
        because = x["up_fast" if fast else "up_slow"].format(p=p)
    elif why["kind"] == "down":
        because = x["down_fast" if fast else "down_slow"].format(p=p)
    else:
        because = x["t_fast" if fast else "t_slow"].format(p=p, loc=locs.get(c, ""))
    return (x["lead"].format(what=what, side=sd, t=t) + " "
            + x["mine"].format(what=x[mine].format(acc=acc, gen=gen), you=you) + x["because"].format(why=because))
