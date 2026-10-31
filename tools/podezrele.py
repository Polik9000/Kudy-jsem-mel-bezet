#!/usr/bin/env python3
"""Where the map was most likely read wrong, without looking at pictures: the legs the runner ran clearly
faster than the "best" route of the model takes. A cliff or a fence read as a path, a forbidden crossing the
runner took, terrain priced too slow: all of them make the best route of the model slower than the run.

usage: python3 tools/podezrele.py OUT_DIR [OUT_DIR ...] [--out DIR] [--name podezrele] [--pictures 40]
                                  [--notes FILE]

OUT_DIR   output folders of analysed races (run_race.py): analysis.json, best/best.json, and when they are
          there best/relocate.json (wandering at the control) and race.json (dict(slug, title, extra, maponly,
          course, model_sha), written by the script that ran the round: the maps, for the columns read from
          the map and for the pictures)
--out     where NAME.md, NAME.csv and the pictures (NAME/) go (default: kontrola)
--notes   CSV "slug;leg;cause" with what the pictures showed, put into the list as its last column
          (default: OUT/NAME-priciny.csv when it is there)

Two groups of suspects, both judged only on legs with data and without standing or wandering (there the
ratio says nothing):
  A  actual / best.time at least FASTER below the median of that ratio in the same race (one race is faster
     or slower than the model as a whole; the median takes that out) and at least MIN_S seconds in it
  B  the model prices the runner's own track more than OVER above the time it really took (and MIN_S):
     the terrain under the track is read slower than it is
The model has to be one and the same for every race in the list (race.json: model_sha); a mix is an error.

A suspect is no proof: the model is slower than a runner on a path by design. The picture decides.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FASTER = 0.15        # group A: the ratio actual / best is this much below the median of the race ...
OVER = 0.15          # group B: the model time of the own track is this much above the actual time ...
MIN_S = 10.0         # ... and the difference is at least this many seconds
MIN_LEGS = 3         # a race with fewer clean legs than this has no median to compare with
STOOD = ("stop", "zone", "entries", "ratio")   # flag codes of analyze.py that mean standing or wandering
FENCE_M = 3.0        # the best route runs "on a fence" within this distance of one
OOB_M = 5.0          # ... and "at an area out of bounds" within this distance of olive
OFF_M = 40.0         # a leg whose track is farther than this from a control when it was punched does not show
                     # the leg (a second map in the same picture, a control read in the wrong place)


def mmss(s):
    s = int(round(s))
    return f"{'-' if s < 0 else ''}{abs(s) // 60}:{abs(s) % 60:02d}"


def load(folder):
    """One analysed race: dict(folder, slug, title, extra, model, info, legs=[dict(...)])."""
    read = lambda *p: json.load(open(os.path.join(folder, *p), encoding="utf-8"))
    best, A = read("best", "best.json"), read("analysis.json")
    info = read("race.json") if os.path.exists(os.path.join(folder, "race.json")) else {}
    lost = {}
    if os.path.exists(os.path.join(folder, "best", "relocate.json")):
        lost = {c["leg"]: c.get("lost") for c in read("best", "relocate.json")["controls"]}
    personal = ((best.get("model") or {}).get("notes") or {}).get("personal")
    model = info.get("model_sha") or (hashlib.sha1(json.dumps(personal, sort_keys=True).encode()).hexdigest()
                                      if personal else None)
    by_leg = {l["leg"]: l for l in A["legs"]}
    miss = _off_control(A)
    legs = []
    for b in best["legs"]:
        a = by_leg.get(b["leg"], {})
        why = None
        if b.get("no_data") or a.get("no_data"):
            why = "no_data"
        elif a.get("mistake"):
            why = "mistake"
        elif set(a.get("flag_codes") or []) & set(STOOD):
            why = "flags " + ",".join(sorted(set(a["flag_codes"]) & set(STOOD)))
        elif lost.get(b["leg"]):
            why = "lost"
        # (not the start: a recording often begins before the start triangle, and the first leg allows for that)
        elif b["leg"] < len(best["legs"]) and OFF_M < max(miss.get(b["leg"] - 1, 0.0) if b["leg"] > 1 else 0.0,
                                                          miss.get(b["leg"], 0.0)):
            why = "track off the controls"
        elif b.get("no_route") or not (b.get("best") or {}).get("time") or not b.get("actual"):
            why = "no route"
        legs.append(dict(leg=b["leg"], name=b["name"], actual=float(b.get("actual") or 0.0),
                         best=float((b.get("best") or {}).get("time") or 0.0),
                         yours=float((b.get("yours") or {}).get("time") or 0.0),
                         dist=float((b.get("best") or {}).get("dist") or 0.0),
                         path_m=float(((b.get("best") or {}).get("mix") or {}).get("path/road", 0.0)),
                         route=b.get("route") or [], left_out=why))
    slug = info.get("slug") or os.path.basename(os.path.normpath(folder))
    return dict(folder=folder, slug=slug, title=info.get("title") or best.get("title") or slug,
                extra=bool(info.get("extra")), model=model, info=info, legs=legs)


def _off_control(A):
    """{control number: metres between the control and the track where it was punched}, from analysis.json
    (course, track and punch = the index into the track at every control); {} when they are not there."""
    try:
        course, track, punch = A["course"], A["track"], A["punch"]
        lat, lon = np.asarray(track["lat"], float), np.asarray(track["lon"], float)
    except (KeyError, TypeError):
        return {}
    out = {}
    for k, (c, i) in enumerate(zip(course, punch)):
        if i is None or not 0 <= int(i) < len(lat):
            continue
        dy = (lat[int(i)] - c["lat"]) * 111320.0
        dx = (lon[int(i)] - c["lon"]) * 111320.0 * np.cos(np.radians(c["lat"]))
        out[k] = float(np.hypot(dx, dy))
    return out


def suspects(races):
    """(rows, summary): the suspicious legs of the races, most suspicious first, and one line per race.

    rows: dict(race, slug, leg, name, groups ("A", "B" or "A+B"), actual, best, yours, ratio, norm (the ratio
    over the median of the race), diff_s (how much faster than the median makes of the best route, or for
    group B alone how much the model overprices the track), score, dist, path_m).
    summary: dict(slug, legs, clean, median, off (mean distance of the normalised ratio from 1), a, b)."""
    models = {r["model"] for r in races if r["model"]}
    if len(models) > 1:
        raise SystemExit("OB-ERROR mixed_models: the races were priced with different personal models ("
                         + ", ".join(f"{r['slug']}: {str(r['model'])[:8]}" for r in races) + "); run them again with one")
    rows, summary = [], []
    for r in races:
        clean = [l for l in r["legs"] if not l["left_out"]]
        line = dict(slug=r["slug"], extra=r["extra"], legs=len(r["legs"]), clean=len(clean), median=None, off=None,
                    a=0, b=0)
        summary.append(line)
        if len(clean) < MIN_LEGS:
            continue
        ratio = np.array([l["actual"] / l["best"] for l in clean])
        med = float(np.median(ratio))
        line.update(median=med, off=float(np.mean(np.abs(ratio / med - 1.0))))
        for l, q in zip(clean, ratio):
            norm = q / med
            ahead = med * l["best"] - l["actual"]
            in_a = norm <= 1.0 - FASTER and ahead >= MIN_S
            in_b = l["yours"] > (1.0 + OVER) * l["actual"] and l["yours"] - l["actual"] >= MIN_S
            if not (in_a or in_b):
                continue
            line["a"] += in_a
            line["b"] += in_b
            score = max(1.0 - norm if in_a else 0.0, 1.0 - l["actual"] / l["yours"] if in_b else 0.0)
            rows.append(dict(race=r["title"], slug=r["slug"], extra=r["extra"], folder=r["folder"], leg=l["leg"],
                             name=l["name"], groups="+".join(g for g, on in (("A", in_a), ("B", in_b)) if on),
                             actual=l["actual"], best=l["best"], yours=l["yours"], ratio=float(q), norm=float(norm),
                             diff_s=float(ahead if in_a else l["yours"] - l["actual"]), score=float(score),
                             dist=l["dist"], path_m=l["path_m"], route=l["route"], fence_m=None, oob_m=None,
                             picture=None, cause=""))
    rows.sort(key=lambda x: -x["score"])
    return rows, summary


def _along(pts, mpp, step_m=2.0):
    """Points every step_m metres along a polyline in map pixels: (u, v) as integer arrays."""
    p = np.asarray(pts, float)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))] * mpp
    q = np.arange(0, s[-1] + 1e-9, step_m)
    return np.round(np.interp(q, s, p[:, 0])).astype(int), np.round(np.interp(q, s, p[:, 1])).astype(int)


def from_map(rows, races, pictures, folder):
    """Fill in what needs the map: metres of the best route on a fence and at an area out of bounds, and the
    picture of the leg for the first `pictures` rows (copied from OUT_DIR/useky when the round drew it)."""
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(HERE, "tools"))
    from kontrola import Race  # tools/kontrola.py
    from oroute import relocate
    by_slug = {r["slug"]: r for r in races}
    os.makedirs(folder, exist_ok=True)
    for old in os.listdir(folder):
        os.remove(os.path.join(folder, old))
    rank = {id(row): n for n, row in enumerate(rows, 1)}
    for slug in dict.fromkeys(row["slug"] for row in rows):
        r = by_slug[slug]
        if not r["info"].get("maponly"):
            continue
        race = Race(r["folder"], os.path.join(HERE, r["info"]["maponly"]), os.path.join(HERE, r["info"]["course"]))
        mpp = race.mpp
        at_fence = relocate._grow(race.obs["hard"], FENCE_M / mpp)
        at_oob = relocate._grow(relocate.out_of_bounds(race.rgb, race.cls, mpp), OOB_M / mpp)
        H, W = race.cls.shape
        for row in (x for x in rows if x["slug"] == slug):
            if len(row["route"]) > 1:
                u, v = _along(race.px(row["route"]), mpp)
                u, v = np.clip(u, 0, W - 1), np.clip(v, 0, H - 1)
                row.update(fence_m=float(at_fence[v, u].sum() * 2.0), oob_m=float(at_oob[v, u].sum() * 2.0))
            if rank[id(row)] <= pictures:
                name = f"{row['leg']:02d}_{row['name']}.jpg"
                drawn = os.path.join(r["folder"], "useky", name)
                target = os.path.join(folder, f"{rank[id(row)]:02d}_{slug}_{row['name']}.jpg")
                if os.path.exists(drawn):
                    shutil.copyfile(drawn, target)
                else:
                    os.makedirs(os.path.join(r["folder"], "useky"), exist_ok=True)
                    race.leg(row["leg"], os.path.join(r["folder"], "useky"))
                    shutil.copyfile(drawn, target)
                row["picture"] = os.path.basename(target)
        del race


def write(rows, summary, races, out, name):
    """NAME.md (for reading) and NAME.csv (for comparing two runs)."""
    m = lambda x: "–" if x is None else f"{x:.0f}"
    head = ["#", "závod", "úsek", "skupina", "skutečný", "nejlepší (model)", "tvoje stopa (model)", "poměr",
            "k mediánu", "rozdíl s", "délka m", "po cestě m", "na plotu m", "u zakázané plochy m", "výřez", "příčina"]
    lines = ["# Podezřelé úseky: kde je nejspíš špatně přečtená mapa", "",
             f"Vytvořil `tools/podezrele.py` z {len(races)} závodů ({sum(s['legs'] for s in summary)} úseků). "
             f"Model: `{next((r['model'] for r in races if r['model']), 'neznámý')[:12]}`"
             + (f", kód `{races[0]['info'].get('commit')}`" if races and races[0]["info"].get("commit") else "") + ".", "",
             f"- **A**: skutečný čas / čas nejlepšího postupu je aspoň o {FASTER:.0%} pod mediánem závodu a jde aspoň "
             f"o {MIN_S:.0f} s (na úseku jsem byl zřetelně rychlejší, než model dovolí nejlepšímu postupu).",
             f"- **B**: model oceňuje moji stopu o víc než {OVER:.0%} (a {MIN_S:.0f} s) nad skutečný čas (terén pod "
             "stopou čte pomalejší, než je).",
             "- Úseky bez dat, se stáním nebo s blouděním se nepočítají, ani do mediánu.",
             "- Podezřelý úsek není důkaz chyby: na cestě je model z principu pomalejší než běžec. Rozhoduje výřez.", "",
             "## Závody", "",
             "| závod | úseků | počítaných | medián poměru | průměrná odchylka od mediánu | A | B |",
             "|---|---|---|---|---|---|---|"]
    for s in summary:
        lines.append(f"| {s['slug']}{' (extra)' if s['extra'] else ''} | {s['legs']} | {s['clean']} | "
                     + (f"{s['median']:.2f} | {s['off']:.1%}" if s["median"] else "– | –") + f" | {s['a']} | {s['b']} |")
    for label, pick in (("původní (data/)", lambda s: not s["extra"]), ("extra (data-extra/)", lambda s: s["extra"]),
                        ("všechny", lambda s: True)):
        part = [s for s in summary if pick(s)]
        if part:
            w = [s for s in part if s["off"] is not None]
            off = sum(s["off"] * s["clean"] for s in w) / max(sum(s["clean"] for s in w), 1)
            lines.append(f"| **{label}** | {sum(s['legs'] for s in part)} | {sum(s['clean'] for s in part)} | | "
                         f"{off:.1%} | {sum(s['a'] for s in part)} | {sum(s['b'] for s in part)} |")
    lines += ["", f"## Seznam ({len(rows)} úseků, od nejpodezřelejšího)", "",
              "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for n, r in enumerate(rows, 1):
        pic = f"[{r['picture']}]({name}/{r['picture']})" if r["picture"] else ""
        lines.append(f"| {n} | {r['slug']} | {r['name']} | {r['groups']} | {mmss(r['actual'])} | {mmss(r['best'])} | "
                     f"{mmss(r['yours'])} | {r['ratio']:.2f} | {r['norm']:.2f} | {r['diff_s']:.0f} | {r['dist']:.0f} | "
                     f"{r['path_m']:.0f} | {m(r['fence_m'])} | {m(r['oob_m'])} | {pic} | {r['cause']} |")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, name + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    keys = ["slug", "leg", "name", "groups", "actual", "best", "yours", "ratio", "norm", "diff_s", "score", "dist",
            "path_m", "fence_m", "oob_m", "picture", "cause"]
    with open(os.path.join(out, name + ".csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["rank", *keys])
        for n, r in enumerate(rows, 1):
            w.writerow([n, *(round(r[k], 3) if isinstance(r[k], float) else r[k] for k in keys)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--out", default=os.path.join(HERE, "kontrola"))
    ap.add_argument("--name", default="podezrele")
    ap.add_argument("--pictures", type=int, default=40)
    ap.add_argument("--notes")
    a = ap.parse_args()
    races = [load(f) for f in a.folders if os.path.exists(os.path.join(f, "best", "best.json"))]
    rows, summary = suspects(races)
    notes = a.notes or os.path.join(a.out, a.name + "-priciny.csv")
    if os.path.exists(notes):
        with open(notes, encoding="utf-8", newline="") as f:
            said = {(x[0].strip(), x[1].strip()): x[2].strip() for x in csv.reader(f, delimiter=";") if len(x) >= 3}
        for r in rows:
            r["cause"] = said.get((r["slug"], r["name"]), "")
    from_map(rows, races, a.pictures, os.path.join(a.out, a.name))
    write(rows, summary, races, a.out, a.name)
    for s in summary:
        print(f"{s['slug']}: {s['clean']} of {s['legs']} legs judged, median "
              + (f"{s['median']:.2f}" if s["median"] else "-") + f", A {s['a']}, B {s['b']}")
    print(f"{len(rows)} suspicious legs ({sum(s['a'] for s in summary)} A, {sum(s['b'] for s in summary)} B) of "
          f"{sum(s['clean'] for s in summary)} judged in {len(races)} races -> {os.path.join(a.out, a.name)}.md")


if __name__ == "__main__":
    main()
