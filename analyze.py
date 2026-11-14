#!/usr/bin/env python3
"""Analyse one orienteering run: Garmin .fit + Livelox KMZ (map with course).

usage: python3 analyze.py MAP.kmz ACTIVITY.fit OUT_DIR [--course course.json]

Writes to OUT_DIR:
  course.json        start/controls/finish read from the map (edit + pass back with --course)
  legs.csv           per-leg splits and mistake signals
  overlay_legs.jpg   track on the map, legs in alternating colours, stops of 10 s or more circled purple-dark
  overlay_speed.jpg  track coloured by speed (red = stopped, orange = slow, blue = your normal speed)
  legs_flagged.jpg   zoomed crops of legs flagged as likely mistakes
  report.md          readable summary
  analysis.json      the same numbers plus the track, punches and stops with coordinates (for the web app)

--official FILE: JSON with the organiser's times ({"start_utc": ..., "cumulative": [...]}, see oroute/official.py).
When given, the punches are taken from those times instead of the closest GPS approach.
--gps-trim auto|off|FROM:TO: the start and the end of the recording where the GPS was not there yet (or any more)
are cut off automatically (auto, the default; oroute/gpstrim.py), kept (off), or cut at the seconds given
(from the first position of the recording).
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oroute import errors, gpstrim  # noqa: E402
from oroute.analysis import analyse_legs, estimate_offset, find_punches, flag_legs, track_xy, unrecorded  # noqa: E402
from oroute.course import VERSION as COURSE_VERSION  # noqa: E402
from oroute.course import (  # noqa: E402
    detect_course,
    drop_extra,
    fill_order,
    find_missing,
    load_course,
    order_by_lines,
    order_by_track,
    save_course,
)
from oroute.fitload import load_track  # noqa: E402
from oroute.jsonout import rounded  # noqa: E402
from oroute.jsonout import save as save_json
from oroute.kmzmap import GeoMap  # noqa: E402
from oroute.mistakes import classify  # noqa: E402
from oroute.official import apply as apply_official  # noqa: E402
from oroute.official import no_data_legs, order_controls, punch_places  # noqa: E402
from oroute.render import contact_sheet, crop_leg, draw_overlay  # noqa: E402


def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def leg_name(k, n):
    a = "S" if k == 1 else str(k - 1)
    b = "F" if k == n else str(k)
    return f"{a}-{b}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kmz")
    ap.add_argument("fit")
    ap.add_argument("out")
    ap.add_argument("--course", help="course.json to use instead of reading the map")
    ap.add_argument("--no-gps-order", action="store_true",
                    help="keep the control order read from the purple lines only (default: corrected with the GPS track)")
    ap.add_argument("--official", help="JSON with official start and split times; used instead of GPS punch detection")
    ap.add_argument("--no-images", action="store_true",
                    help="do not draw the overlay pictures (the web app draws the map itself from analysis.json)")
    ap.add_argument("--gps-trim", default="auto",
                    help="auto (default): cut off a GPS jump at the start or the end; off; FROM:TO in seconds")
    ap.add_argument("--oris-controls", type=int,
                    help="number of controls of the class in ORIS; the course read from the map is checked against it "
                         "(with --official the number of split times is used)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    gm = GeoMap.from_kmz(args.kmz)
    tr = gpstrim.apply(load_track(args.fit), args.gps_trim)
    u0, v0 = gm.latlon_to_px(tr["lat"][:1], tr["lon"][:1])
    official_in = json.load(open(args.official, encoding="utf-8")) if args.official else None
    # how many controls the course has: the official split times, else the class in ORIS, else not known
    expected = args.oris_controls
    if official_in and official_in.get("cumulative"):
        expected = len(official_in["cumulative"]) - 1

    if args.course:
        c = load_course(args.course)
        if c.get("start") is None or c.get("finish") is None:
            raise errors.InputError("no_start" if c.get("start") is None else "no_finish",
                                    f"the course given ({len(c['controls'])} controls) has no start or no finish")
        pts_px = [c["start"]["px"]] + [p["px"] for p in c["controls"]] + [c["finish"]["px"]]
        line_scores = None
        # the latitude and longitude anew from the pixels: the map may have been placed again since (mapfix)
        save_course(os.path.join(args.out, "course.json"), gm,
                    {"start": c["start"]["px"], "controls": [p["px"] for p in c["controls"]],
                     "finish": c["finish"]["px"]})
        check = dict(found=len(c["controls"]), added=0, removed=0, expected=expected, source="manual")
    else:
        det = detect_course(gm, start_hint_px=(u0[0], v0[0]))
        if not det["controls"] and det["finish"] is None:
            raise errors.InputError("no_course_print", "no course is printed on the map: no purple control "
                                    f"circles were found ({int(det['mask'].sum())} purple pixels)")
        if det["finish"] is None:
            raise errors.InputError("no_finish", f"{len(det['controls'])} control circles were read from the map, "
                                    "but no finish (double circle); pass --course")
        if det["start"] is None:
            raise errors.InputError("no_start", f"{len(det['controls'])} control circles were read from the map, "
                                    "but no start triangle; pass --course")
        def px_xy(p):
            lat, lon = gm.px_to_latlon(p[0], p[1])
            xx, yy = gm.to_xy(lat, lon)
            return float(xx), float(yy)
        fx, fy = px_xy(det["finish"])
        circles = [c for c in det["controls"] if np.hypot(px_xy(c)[0] - fx, px_xy(c)[1] - fy) >= 25.0]
        check = dict(found=len(circles), added=0, removed=0, expected=expected, source="map")
        if official_in and expected and circles and len(circles) != expected:
            # the number of controls in the official results is the goal: a circle cut open for a detail of the
            # map is looked for where the watch was at its punch, a control number read as a circle is left out
            mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
            hints = []
            for p in punch_places(tr, official_in):
                uu, vv = gm.latlon_to_px(np.array([p[0]]), np.array([p[1]])) if p else (None, None)
                hints.append(None if p is None else (float(uu[0]), float(vv[0])))
            if len(circles) < expected:
                added, notes = find_missing(det["mask"], mpp, det["start"], circles, det["finish"], hints, expected)
                for n in notes:
                    if n.get("found"):
                        print(f"control {n['k']}: circle found where the watch was at the punch ({n['off_m']} m), "
                              f"{100 * n['cover']:.0f} % of its outline printed")
                det["controls"] = det["controls"] + added
                circles = circles + added
                check["added"] = len(added)
            else:
                extra_circles = drop_extra(circles, hints, expected, mpp)
                if extra_circles:
                    print(f"left out {len(extra_circles)} circle(s) far from every punch (a control number?)")
                det["controls"] = [c for c in det["controls"] if c not in extra_circles]
                circles = [c for c in circles if c not in extra_circles]
                check["removed"] = len(extra_circles)
        ordered = None
        if args.official and not args.no_gps_order:
            # Official times first: where the watch was at each official punch time says which circle is which
            # control. No search through the purple lines, so the number of controls does not matter; the
            # lines and the track then only check the order (order_by_track below).
            idx, how = order_controls(tr, gm, [px_xy(c) for c in circles], official_in)
            if idx is None:
                print(f"control order from the purple lines, not from the official times: {how['reason']}")
            else:
                idx = fill_order(det["mask"], det["start"], circles, det["finish"], idx)
                ordered = [circles[i] for i in idx]
                print(f"control order from the official times (track {how['median_miss_m']:.0f} m from the "
                      "circles at the punch times, median)")
        if ordered is None:
            ordered, line_scores = order_by_lines(det["mask"], det["start"], det["controls"], det["finish"])
        if not args.no_gps_order:
            tx, ty = track_xy(gm, tr)
            ordered, line_scores, dropped = order_by_track(det["mask"], det["start"], det["controls"],
                                                           det["finish"], ordered, px_xy, tx, ty)
            if dropped:
                print(f"dropped {len(dropped)} circle(s) lying on the finish circle")
        save_course(os.path.join(args.out, "course.json"), gm,
                    {"start": det["start"], "controls": ordered, "finish": det["finish"]})
        pts_px = [det["start"]] + [p[:2] for p in ordered] + [det["finish"]]

    pts = []
    for p in pts_px:
        lat, lon = gm.px_to_latlon(p[0], p[1])
        x, y = gm.to_xy(lat, lon)
        pts.append((float(x), float(y)))
    punch, official = None, None
    if args.official:
        tr, punch, official = apply_official(tr, gm, pts, official_in)
    x, y = track_xy(gm, tr)
    if punch is None:
        punch = find_punches(tr["t"], x, y, pts)
        # legs the recording does not show; a track that is no run of this course ends the analysis here
        gone = unrecorded(x, y, punch, pts, why=official and official.get("reason"))
    else:
        gone = no_data_legs(official, len(pts) - 1)
    off = estimate_offset(x, y, punch, pts)
    legs, speed = analyse_legs(tr, x, y, pts, punch, no_data=gone)
    vref, rref = flag_legs(legs)
    n = len(legs)
    if gone:
        print(f"no GPS data on {len(gone)} of {n} legs: " + ", ".join(leg_name(k, n) for k in sorted(gone)))

    # CSV
    with open(os.path.join(args.out, "legs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["leg", "split", "elapsed", "straight_m", "run_m", "route_ratio", "speed_kmh",
                    "climb_m", "time_last100m_s", "entries_100m", "stopped_s", "expected", "est_loss_s",
                    "flags"])
        el = 0
        for l in legs:
            el += l["time"]
            w.writerow([leg_name(l["leg"], n), mmss(l["time"]), mmss(el), round(l["straight"]),
                        round(l["run"]), round(l["ratio"], 2), round(l["speed"] * 3.6, 1),
                        round(l["climb"]), round(l["zone_time"]), l["zone_entries"],
                        round(l["stop_time"]), mmss(l["expected"]), round(l["est_loss"]),
                        "; ".join(l["flags"])])

    # images
    if not args.no_images:
        im_leg = draw_overlay(gm, tr, legs, punch, pts_px, speed, vref, mode="leg")
        im_leg.save(os.path.join(args.out, "overlay_legs.jpg"), quality=88)
        im_sp = draw_overlay(gm, tr, legs, punch, pts_px, speed, vref, mode="speed")
        im_sp.save(os.path.join(args.out, "overlay_speed.jpg"), quality=88)
        bad = sorted([l for l in legs if l["flags"]], key=lambda l: -l["est_loss"])
        if bad:
            crops = [crop_leg(draw_overlay(gm, tr, [l], punch, pts_px, speed, vref, mode="speed"), gm, tr, l, pts_px,
                              title=f"{leg_name(l['leg'], n)}  {mmss(l['time'])}  (~{mmss(l['est_loss'])} lost)")
                     for l in bad]
            contact_sheet(crops).save(os.path.join(args.out, "legs_flagged.jpg"), quality=88)

    # report
    total = tr["t"][punch[-1]] - tr["t"][punch[0]]
    loss = sum(l["est_loss"] for l in legs)
    lines = [
        f"# Run analysis: {os.path.basename(args.kmz)}",
        "",
        f"- Date: {tr['start']:%Y-%m-%d %H:%M} UTC",
        f"- Time start to finish: **{mmss(total)}**, GPS distance {sum(l['run'] for l in legs) / 1000:.2f} km"
        f" (straight-line course {sum(l['straight'] for l in legs) / 1000:.2f} km)",
        f"- Your normal running speed on this course (median over legs): {vref * 3.6:.1f} km/h;"
        f" normal route ratio used: {rref:.2f}",
        f"- Estimated time lost vs that pace: **~{mmss(loss)}**",
        f"- Map georeferencing check: median GPS-to-control offset {np.hypot(*off):.0f} m",
        "",
        "| Leg | Split | Straight | Ran | Ratio | Climb | Last 100 m | Stopped | Est. loss | Signals |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for l in legs:
        lines.append(f"| {leg_name(l['leg'], n)} | {mmss(l['time'])} | {l['straight']:.0f} m | {l['run']:.0f} m |"
                     f" {l['ratio']:.2f} | {l['climb']:.0f} m | {mmss(l['zone_time'])} | {l['stop_time']:.0f} s |"
                     f" {mmss(l['est_loss'])} | {'; '.join(l['flags'])} |")
    weak = [i + 1 for i, s in enumerate(line_scores[:-1]) if s < 0.5] if line_scores is not None else []
    if weak:
        lines += ["", f"Note: course order is uncertain around leg(s) {weak}; check course.json."]
    cut = tr["trim"]
    if cut["head"] or cut["tail"]:
        lines += ["", f"GPS track cut ({cut['mode']}): kept {mmss(cut['start_s'])} to {mmss(cut['end_s'])} of "
                  f"{mmss(cut['length_s'])} recorded."]
    if gone:
        lines += ["", "No GPS data on leg(s) " + ", ".join(leg_name(k, n) for k in sorted(gone))
                  + ": the recording does not show them (started late, stopped early or a control not visited)."]
    if official is not None:
        lines += ["", "Punch times: official split times." if official["used"] else
                  f"Punch times: from GPS; the official times were not used ({official['reason']})."]
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))

    # everything above once more as data, with coordinates (web app)
    t = tr["t"]
    out_legs = []
    for l in legs:
        d = dict(l, name=leg_name(l["leg"], n))
        d["stops"] = [dict(a=s, b=e, t0=t[s], dur=t[e] - t[s], lat=round(float(np.mean(tr["lat"][s:e + 1])), 6),
                           lon=round(float(np.mean(tr["lon"][s:e + 1])), 6)) for s, e in l["stops"]]
        # what kind of mistake it was, from the shape of the track (rules in oroute/mistakes.py)
        m = None if l.get("no_data") else classify(t, x, y, speed, l, pts[l["leg"] - 1], pts[l["leg"]], vref)
        if m is not None:
            i = m.pop("i")
            m["at"] = None if i is None else [round(float(tr["lat"][i]), 6), round(float(tr["lon"][i]), 6)]
        d["mistake"] = m
        out_legs.append(d)
    course_ll = [gm.px_to_latlon(p[0], p[1]) for p in pts_px]
    save_json(os.path.join(args.out, "analysis.json"), dict(
        start=tr["start"].isoformat(), total_time=total, est_loss=loss, vref=vref, rref=rref, offset_m=off,
        weak_order=weak, official=official, course_check=check, course_version=COURSE_VERSION,
        course=[dict(lat=round(float(la), 7), lon=round(float(lo), 7)) for la, lo in course_ll],
        track=dict(t=rounded(t, 2), lat=rounded(tr["lat"], 6), lon=rounded(tr["lon"], 6), speed=rounded(speed, 2),
                   trim=tr["trim"]),
        punch=punch, legs=out_legs))


if __name__ == "__main__":
    errors.run(main)
