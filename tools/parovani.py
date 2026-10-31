#!/usr/bin/env python3
"""Pair the maps in data-extra/ with the runs of a Garmin export, by position.

usage: python3 tools/parovani.py [--extra data-extra] [--export private/Garmin] [--work kontrola] [--again]

data-extra/ holds Livelox maps, two files per race: "NAME.kmz" (the map without course) and
"NAME, CLASS.kmz" (the map with the course of a class). The files carry no date, so the run of a race is
found by where it was: among the activities of the export that begin near the map, the one whose track
visits most of the control circles read from the map with the course (oroute.course.detect_course).

Writes EXTRA/parovani.json: {NAME: {course, maponly, fit, start, confidence, reason, candidates}} and prints
the table. The .fit files of the candidates are unpacked into WORK/fits/ (never into the repository's data).
The scan of the export and the circles of the maps are kept in WORK/, --again reads them anew.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import garmin  # noqa: E402
from oroute.course import detect_course  # noqa: E402
from oroute.fitload import load_track  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402

NEAR_KM = 3.0        # a run that begins farther from the edge of the map is not looked at
VISIT_M = 25.0       # a control was visited when the track came this close to its circle
MIN_INSIDE_S = 300   # a run with less of its track on the map than this is not the race
SURE, LIKELY = 0.8, 0.6   # share of the circles visited for "high" and "medium" ...
AHEAD = 0.25              # ... when the next best run visited this much less


def pairs(folder):
    """[(name of the race, map with course, map without course)]: a file is the course of the map whose
    name it begins with, followed by ", CLASS"."""
    stems = sorted(f[:-4] for f in os.listdir(folder) if f.lower().endswith(".kmz"))
    out = []
    for s in stems:
        base = [b for b in stems if s.startswith(b + ", ")]
        if base:
            b = max(base, key=len)
            out.append((s, os.path.join(folder, s + ".kmz"), os.path.join(folder, b + ".kmz")))
    return out


def _sources(export):
    """Every zip and loose .fit under the export folder (or the one file given)."""
    if os.path.isfile(export):
        yield export
        return
    for root, _, files in os.walk(export):
        for f in sorted(files):
            if f.lower().endswith((".zip", ".fit")):
                yield os.path.join(root, f)


def _files(src):
    if src.lower().endswith(".fit"):
        with open(src, "rb") as f:
            yield os.path.basename(src), f.read()
    else:
        yield from garmin.iter_fit(src)


def scan_export(export, cache, again=False):
    """[dict(src, name, start, sport, sub_sport, timer, elapsed, dist, lat, lon)] of the activities of the
    export; lat and lon (where the recording begins) are None for one without GPS."""
    if os.path.exists(cache) and not again:
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    acts, seen = [], 0
    for src in _sources(export):
        for name, data in _files(src):
            seen += 1
            info = garmin.scan_fit(data)
            if info.get("type") != "activity" or info.get("error") or not info.get("start"):
                continue
            gps = info.get("first_gps") or (None, None)
            acts.append(dict(src=os.path.relpath(src, HERE), name=name, start=info["start"].isoformat(),
                             sport=info.get("sport"), sub_sport=info.get("sub_sport"), timer=info.get("timer"),
                             elapsed=info.get("elapsed"), dist=info.get("dist"),
                             lat=gps[0], lon=gps[1]))
            if seen % 500 == 0:
                print(f"  {seen} files, {len(acts)} activities", flush=True)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(acts, f)
    return acts


def unpack(acts, dest):
    """Write the .fit of these activities into dest (those not there yet). Returns {name: path}."""
    os.makedirs(dest, exist_ok=True)
    want = {a["name"]: a["src"] for a in acts if not os.path.exists(os.path.join(dest, a["name"]))}
    for src in sorted(set(want.values())):
        for name, data in _files(os.path.join(HERE, src)):
            if want.get(name) == src:
                with open(os.path.join(dest, name), "wb") as f:
                    f.write(data)
    return {a["name"]: os.path.join(dest, a["name"]) for a in acts}


def circles(course, cache, again=False):
    """(GeoMap of the map with the course, [(x, y)] in metres of its start, controls and finish)."""
    gm = GeoMap.from_kmz(course)
    key = f"{os.path.basename(course)}/{os.path.getsize(course)}"
    known = {}
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            known = json.load(f)
    if key not in known or again:
        det = detect_course(gm)
        px = [c[:2] for c in det["controls"]] + [p for p in (det["start"], det["finish"]) if p is not None]
        known[key] = [[float(p[0]), float(p[1])] for p in px]
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(known, f)
    pts = []
    for u, v in known[key]:
        x, y = gm.to_xy(*gm.px_to_latlon(u, v))
        pts.append((float(x), float(y)))
    return gm, pts


def score(gm, pts, fit):
    """(share of the circles the track visited, seconds of the track on the map) of one run."""
    tr = load_track(fit)
    u, v = (np.asarray(a) for a in gm.latlon_to_px(tr["lat"], tr["lon"]))
    on = (u >= 0) & (u < gm.W) & (v >= gm.header_px) & (v < gm.H)
    dt = np.diff(tr["t"])
    inside = float(dt[on[:-1] & on[1:] & (dt < 30)].sum())
    if not pts or not on.any():
        return 0.0, inside
    x, y = (np.asarray(a) for a in gm.to_xy(tr["lat"], tr["lon"]))
    seen = [float(np.hypot(x - px, y - py).min()) <= VISIT_M for px, py in pts]
    return float(np.mean(seen)), inside


def choose(cands, n_circles):
    """(best candidate or None, confidence, reason in Czech). cands: dicts with visited and inside_s."""
    runs = sorted((c for c in cands if c["inside_s"] >= MIN_INSIDE_S), key=lambda c: (-c["visited"], -c["inside_s"]))
    if not runs:
        return None, "none", "žádný běh z exportu neleží aspoň pět minut na mapě"
    best, second = runs[0], (runs[1]["visited"] if len(runs) > 1 else 0.0)
    if not n_circles:
        return None, "none", "z mapy s tratí se nepodařilo přečíst kontroly, podle polohy samotné nepáruji"
    why = (f"stopa navštívila {best['visited'] * 100:.0f} % z {n_circles} koleček a byla na mapě "
           f"{best['inside_s'] / 60:.0f} min; další běh na téže mapě {second * 100:.0f} %"
           if len(runs) > 1 else
           f"jediný běh na mapě: navštívil {best['visited'] * 100:.0f} % z {n_circles} koleček, "
           f"na mapě {best['inside_s'] / 60:.0f} min")
    if best["visited"] >= SURE and best["visited"] - second >= AHEAD:
        return best, "high", why
    if best["visited"] >= LIKELY and best["visited"] - second >= AHEAD / 2:
        return best, "medium", why
    return None, "low", why + " (nejisté, mapa se přeskočí)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", default=os.path.join(HERE, "data-extra"))
    ap.add_argument("--export", default=os.path.join(HERE, "private", "Garmin"))
    ap.add_argument("--work", default=os.path.join(HERE, "kontrola"))
    ap.add_argument("--again", action="store_true", help="scan the export and read the circles again")
    a = ap.parse_args()
    if not os.path.isdir(a.extra) or not pairs(a.extra):
        sys.exit(f"no pairs of maps in {a.extra}")
    acts = scan_export(a.export, os.path.join(a.work, "export_scan.json"), a.again)
    print(f"{len(acts)} activities in the export, {sum(x['lat'] is not None for x in acts)} of them with GPS")
    acts = [x for x in acts if x["lat"] is not None]
    out = {}
    for name, course, maponly in pairs(a.extra):
        gm, pts = circles(course, os.path.join(a.work, "circles.json"), a.again)
        la, lo = gm.px_to_latlon([0, gm.W, 0, gm.W, gm.W / 2], [0, 0, gm.H, gm.H, gm.H / 2])
        reach = NEAR_KM + garmin.km_between(la[0], lo[0], la[4], lo[4])
        near = [x for x in acts if garmin.km_between(x["lat"], x["lon"], la[4], lo[4]) <= reach]
        fits = unpack(near, os.path.join(a.work, "fits"))
        cands = []
        for x in near:
            visited, inside = score(gm, pts, fits[x["name"]])
            cands.append(dict(fit=os.path.relpath(fits[x["name"]], HERE).replace(os.sep, "/"), start=x["start"],
                              sport=x["sport"], timer=x["timer"], visited=round(visited, 3), inside_s=round(inside)))
        best, conf, why = choose(cands, len(pts))
        out[name] = dict(course=os.path.relpath(course, HERE).replace(os.sep, "/"),
                         maponly=os.path.relpath(maponly, HERE).replace(os.sep, "/"),
                         fit=best["fit"] if best else None, start=best["start"] if best else None,
                         confidence=conf, reason=why, circles=len(pts),
                         candidates=sorted(cands, key=lambda c: -c["visited"])[:5])
        print(f"{name}: {conf}: {os.path.basename(best['fit']) if best else '-'}: {why}", flush=True)
    with open(os.path.join(a.extra, "parovani.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n| Mapa | Soubor .fit | Start záznamu (UTC) | Jistota | Důvod |\n|---|---|---|---|---|")
    for name, r in out.items():
        print(f"| {name} | {os.path.basename(r['fit']) if r['fit'] else '-'} | {(r['start'] or '-')[:16]} | "
              f"{r['confidence']} | {r['reason']} |")


if __name__ == "__main__":
    main()
