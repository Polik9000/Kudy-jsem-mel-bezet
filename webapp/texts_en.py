"""English wording for the numbers and notes the analysis produces: the counterpart of webapp/texts.py, function for
function, used when the page is in English (texts.py hands over to this module when i18n.lang() is "en").

Czech needs grammar (cases, genders, plurals) that the sentences here do not, so these are written as English
sentences of their own and not translated word for word."""
import re

from .texts import about, bearing, mmss


def _plural(n, one, many):
    return one if n == 1 else many


# --- the analysis notes (oroute.analysis.flag_legs codes and friends) ------------------------------------------

CONFIDENCE = {"high": ("certain", "ob-ok"), "medium": ("probable", "ob-warn"), "low": ("uncertain", "ob-bad"),
              "manual": ("manual", "ob-ok"), "none": ("none", ""), None: ("none", "")}


def match_note(note):
    """The notes of the matching are English already (services/matching.py)."""
    return note or ""


def flags(leg, vref, deliberate_s=0.0):
    out = []
    for c in leg.get("flag_codes") or []:
        if c == "ratio":
            out.append(f"route {leg['ratio']:.1f}× longer than the straight line")
        elif c == "entries":
            out.append(f"{leg['zone_entries']}× within 100 m of the control (overshooting, circling)")
        elif c == "zone":
            out.append(f"about {leg['zone_excess']:.0f} s extra at the control")
        elif c == "stop" and leg["stop_time"] - deliberate_s > 15:
            out.append(f"standing {leg['stop_time'] - deliberate_s:.0f} s")
        elif c == "slow":
            out.append(f"slow ({leg['speed'] * 3.6:.1f} km/h, usually {vref * 3.6:.1f})")
        elif c == "no_data":
            out.append("no recording from the watch (not enough data)")
    return out


def gps_trouble(g):
    if not g:
        return None
    why = []
    if g.get("far_m") and g["far_m"] > 30:
        why.append(f"at the punch the track is {g['far_m']} m from the control")
    if g.get("jump_kmh"):
        why.append(f"the track jumps ({g['jump_kmh']} km/h)")
    return "The GPS is probably misbehaving here: " + " and ".join(why) + ". If you know where you ran, correct the track."


MISTAKES = {
    "overshoot": ("overshooting", "You passed the control by {miss:.0f} m, ran on for another {over:.0f} m and came back "
                                  "({back:.0f} s from passing the control to the punch)."),
    "undershoot": ("falling short", "About {dist:.0f} m before the control you slowed down or stood still ({stop:.0f} s) "
                                    "and searched; the control was further on in the direction of travel."),
    "drift": ("drifting off line", "For most of the leg you ran beside the straight line (up to {dev:.0f} m to the side) "
                                   "and came into the control almost at right angles to the direction of travel."),
    "circling": ("searching in circles", "Within 100 m of the control you turned {turn:.0f}° in total and spent "
                                         "{time:.0f} s there."),
    "relocation": ("stopping to relocate", "You stood for {stop:.0f} s and then changed direction by {turn:.0f}°: "
                                           "you were working out where you were again."),
    "slow": ("slow, no map error", "The track goes sensibly, just slower than the terrain suggests: more likely fitness "
                                   "or harder ground than the map."),
}


def mistake(m, read=None, note=None):
    if not m or not m.get("type"):
        return None
    label, text = MISTAKES.get(m["type"], (m["type"], ""))
    try:
        text = text.format(**m)
    except (KeyError, IndexError, ValueError):
        pass
    return dict(type=m["type"], label=label, text=text, at=m.get("at"))


# --- relocating features, catching features, "I am lost at the control" ---------------------------------------------------

# kind -> name of the feature
FEATURES = {
    "junction": "path junction", "path_end": "end of a path", "path": "path", "stream_path": "path crossing a stream",
    "stream": "stream", "pond": "lake or pond", "building": "building", "enclosure": "forestry fence", "fence": "fence",
    "settlement": "edge of the out-of-bounds area (built-up)", "clearing": "clearing", "open_edge": "edge of an open area",
    "hilltop": "hilltop", "knoll": "knoll", "depression": "depression", "pit": "pit",
    "landform": "prominent landform", "boulder": "boulder", "water_pit": "waterhole", "well": "well or water reservoir",
    "tree": "prominent tree", "stand": "hunting tower", "object": "prominent man-made object",
}


def feature_name(kind):
    return FEATURES.get(kind, kind)


def attack(a):
    if not a:
        return None
    kind = FEATURES.get(a.get("kind"), "point on a path")
    return dict(lat=a["lat"], lon=a["lon"], label=f"{kind} {a['dist']:.0f} m before the control")


def slope(dh, dist):
    grade = dh / max(dist, 1.0)
    if abs(dh) < 3 or abs(grade) < 0.04:
        return "level"
    return ("gently " if abs(grade) < 0.12 else "") + ("uphill" if dh > 0 else "downhill")


def feature(f):
    name = feature_name(f["kind"])
    nearest = "" if f["point"] else ", nearest point"
    if f.get("via"):
        back = (f"from the {name} by a detour of {f['walk']:.0f} m, first on bearing {bearing(f['first_az'])} "
                f"(the obstacle is straight ahead), {slope(f['dh'], f['dist'])}")
    else:
        back = f"from the {name}, {f['dist']:.0f} m on bearing {bearing(f['back_az'])}, {slope(f['dh'], f['dist'])}"
    return dict(kind=f["kind"], lat=f["lat"], lon=f["lon"], point=f["point"], label=name,
                where=f"{name}{nearest} {f['dist']:.0f} m from the control on bearing {bearing(f['az'])}",
                back=back, via=f.get("via"))


def relocate(r):
    if not r:
        return None
    lost = None
    if r.get("lost"):
        l = r["lost"]
        text = (f"You got lost at this control: you left the direct line to it {l['dist']:.0f} m before it, ran "
                f"{l['extra_m']:.0f} m extra and it cost about {mmss(l['extra_s'])}.")
        near = l.get("near")
        if near:
            name = feature_name(near["kind"])
            if near.get("via"):
                text += (f" You were {near['track_m']:.0f} m from the {name}, from where the control is reached by a "
                         f"detour of {near['walk']:.0f} m, first on bearing {bearing(near['first_az'])} "
                         "(the obstacle is straight ahead).")
            else:
                text += (f" You were {near['track_m']:.0f} m from the {name}, from where a direct bearing of "
                         f"{bearing(near['back_az'])} leads to the control ({near['dist']:.0f} m, "
                         f"{slope(near['dh'], near['dist'])}).")
        else:
            text += " You passed no relocating feature closer than 120 m."
        lost = dict(i=l["i"], at=[l["lat"], l["lon"]], text=text,
                    near=dict(lat=near["lat"], lon=near["lon"], i=near["i"], via=near.get("via")) if near else None)
    return dict(features=[feature(f) for f in r.get("features") or []], lost=lost)


SIDES = {"left": "to the left", "ahead": "straight on", "right": "to the right"}


def beyond(b):
    if not b or not b.get("parts"):
        return None
    name = lambda q: feature_name(q["kind"])
    got = {q["side"]: q for q in b["parts"]}
    if len(got) == 3 and len({q["kind"] for q in got.values()}) == 1:
        near, far = (f(round(q["dist"]) for q in got.values()) for f in (min, max))
        label = f"{name(got['ahead'])} across {near if near == far else f'{near}–{far}'} m beyond the control"
    else:
        label = ", ".join(f"{name(got[s])} {SIDES[s]} {got[s]['dist']:.0f} m" for s in SIDES if s in got)
        none = [SIDES[s] for s in SIDES if s not in got]
        if none:
            label += f"; nothing {' and '.join(none)} within {b.get('within', 200):.0f} m"
    return dict(label=label,
                text=f"{label}. Whoever gets there has overshot the control and returns on bearing {bearing(b['back_az'])}",
                parts=[dict(lat=q["lat"], lon=q["lon"], line=q.get("line") or [],
                            label=f"{name(q)} {SIDES[q['side']]} {q['dist']:.0f} m beyond the control") for q in b["parts"]])


# kind -> (name, whether it is a line one crosses)
LOST_NAMES = {
    "path": ("path", True), "stream": ("stream", True), "fence": ("fence", False),
    "settlement": ("edge of the out-of-bounds area", False), "open_edge": ("edge of an open area", True),
    "pond": ("lake or pond", False), "building": ("building", False), "wall": ("wall", False),
    "junction": ("path junction", False), "path_end": ("end of the path", False),
    "stream_path": ("path crossing a stream", False), "clearing": ("clearing", False), "hilltop": ("hilltop", False),
    "knoll": ("knoll", False), "depression": ("depression", False), "pit": ("pit", False),
    "landform": ("prominent landform", False), "boulder": ("boulder", False), "water_pit": ("waterhole", False),
    "well": ("well or water reservoir", False), "tree": ("prominent tree", False), "stand": ("hunting tower", False),
    "object": ("prominent man-made object", False),
}
COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")
LOST_WHY = {"mistake:overshoot": "overshot the control", "mistake:undershoot": "stopped short of the control",
            "mistake:drift": "came in from the side", "mistake:circling": "circled",
            "mistake:relocation": "stopped and looked for where you were", "mistake:slow": "slowed down",
            "stop": "stopped", "slow": "slowed down", "loop": "circled", "turn": "turned round",
            "lost": "lost contact with the map here"}


def lost_name(kind):
    return LOST_NAMES.get(kind, (kind, False))[0]


def compass(deg):
    return COMPASS[int((deg % 360.0 + 22.5) // 45.0) % 8]


def _ln(kind):
    return LOST_NAMES.get(kind, (kind, False))


def _seen(seen):
    out = []
    for i, (kind, m) in enumerate(seen[:2]):
        name, crosses = _ln(kind)
        out.append(f"after {about(m)} m {'you would have ' if i == 0 else ''}{'crossed' if crosses else 'passed'} "
                   f"the {name}")
    return ", ".join(out)


def _from_line(h):
    link, (name, _crosses) = h["link"], _ln(h["kind"])
    if link["type"] == "near" and h["kind"] not in ("building", "pond", "wall", "settlement"):
        if link.get("az") is not None and link.get("along"):
            where = f"right at the {name}" if link["dist"] < 8 else \
                f"{about(link['dist'])} m to the {'right' if link.get('side') == 'right' else 'left'}"
            if link["dist"] > 40:
                where += f" on bearing {bearing(link['az_off'])}"
            return f"Then along the {name} to the {compass(link['az'])} for about {about(link['along'])} m; the control was {where}."
        return f"The control was {about(link['dist'])} m from the {name} on bearing {bearing(link['az_off'])}."
    if link["type"] == "point":
        p = _ln(link["point"])[0]
        return (f"Then along the {name} to the {compass(link['az'])}, to the {p} (about {about(link['along'])} m), and from "
                f"there the control was {about(link['dist'])} m on bearing {bearing(link['az_off'])}.")
    if link.get("round"):
        return (f"From there it was about {about(link['dist'])} m to the control by a detour, first on bearing "
                f"{bearing(link['az_off'])} (the obstacle was straight ahead).")
    return f"From there the control was {about(link['dist'])} m on bearing {bearing(link['az_off'])}."


def lost_advice(a):
    if a is None:
        return []
    if a.get("far"):
        return ["This place is more than 300 m from the control. Tap closer to the control; from here you should have "
                "gone back to the last place where you knew where you were."]
    out = []
    t = a.get("attack")
    if a.get("pick") is None:
        out.append("There was nothing around you could have caught onto for certain.")
        if t and t.get("to"):
            out.append(f"You should have gone back to the attack point ({lost_name(t['kind'])}, {about(t['dist'])} m on "
                       f"bearing {bearing(t['az'])}) and started again from there: the control was {about(t['to']['dist'])} m "
                       f"on bearing {bearing(t['to']['az'])}.")
    else:
        h = a["helpers"][a["pick"]]
        name = _ln(h["kind"])[0]
        way = f"about {about(h['dist'])} m, bearing {bearing(h['az'])}"
        if h.get("seen"):
            way += ", " + _seen(h["seen"])
        if a.get("no_runner"):
            first = (f"If you did not know where you were at the control: to the {compass(h['az'])} there was a {name} "
                     f"within {about(h['dist'] + a['r'])} m" + (", which you could not miss." if h["sure"] else "."))
        elif h.get("inside"):
            first = (f"Within {about(a['r'])} m of you there was a {name} (nearest to the {compass(h['az'])}, about "
                     f"{about(h['dist'])} m): you should have found it." if h["dist"] >= 8 else
                     f"You were at the {name}; you should have kept to it.")
        elif not h["sure"]:
            first = f"Nothing could be caught for certain from here; the best was to go {compass(h['az'])} to the {name} ({way})."
        elif a.get("relocate_first"):
            go = "gone back" if a.get("back") else "walked"
            first = (f"You should not have guessed the direction to the control. First you should have {go} "
                     f"{compass(h['az'])} to the {name} ({way}); you could not miss it.")
        else:
            first = f"You should have gone {compass(h['az'])} to the {name} ({way})."
        out += [first, _from_line(h)]
        if not h["sure"] and t and t.get("to") and not a.get("no_runner"):
            out[-1] += (f" If you had not found it, you should have gone back to the attack point ({lost_name(t['kind'])}, "
                        f"{about(t['dist'])} m on bearing {bearing(t['az'])}).")
    if a.get("desc"):
        out.append(f"From the description you were looking for: {a['desc']}.")
    return out[:3]


def lost_note(a):
    return "Where you tapped is off limits (forestry fence, out-of-bounds area, water); I am taking the nearest place outside." \
        if a and a.get("snapped") else None


def lost_moment(m):
    why = LOST_WHY.get(m["why"], LOST_WHY.get(m["why"].split(":")[0], "hesitated"))
    head = f"{about(m['dist'])} m from the control you {why}."
    near = [f"{lost_name(k)} {about(d)} m to the {compass(az)}" for k, d, az in m.get("near") or []]
    seen = ("You should have seen: " + ", ".join(near) + ".") if near else "Within 30 m there was nothing certain."
    crossed = [f"{lost_name(k)} {about(d)} m before that" for k, d in m.get("crossed") or []]
    if crossed:
        seen += " You had crossed: " + ", ".join(crossed) + "."
    return dict(head=head, seen=seen, back=lost_advice(m["advice"]))


CROSSED = {
    "railway": ("crosses a railway outside a crossing",
                "If crossing was allowed, switch “Railways and motorways” to “do not use” in the race settings."),
    "motorway": ("crosses a motorway outside a crossing",
                 "If crossing was allowed, switch “Railways and motorways” to “do not use” in the race settings."),
    "manual": ("crosses a impassable line drawn by hand",
               "If the line should not be there, whoever drew it can delete it in the race settings."),
    "area": ("goes through a out-of-bounds area from the map hatching",
             "If it was allowed there, switch “Out-of-bounds areas from the map” to “do not use” in the race settings."),
    "enclosure": ("goes across a forestry fence",
                  "The app treats a forestry fence as impassable; if there is no fence or it has a gate, take the "
                  "difference with a pinch of salt."),
}


def crossed(found):
    known = [c for c in found or [] if c.get("what") in CROSSED]
    if not known:
        return None
    did, advice = [], []
    for c in known:
        for item, seen in zip(CROSSED[c["what"]], (did, advice)):
            if item not in seen:
                seen.append(item)
    return dict(at=[c["at"] for c in known],
                text=f"Your track {' and '.join(did)}. The best route must not go there, so it goes round and may come "
                     f"out slower than your track. {' '.join(advice)}")


# --- errors and problems of what the runner uploaded ------------------------------------------------------------

ANALYSIS_ERRORS = {
    "bad_fit": "The run file could not be read: it is not a valid .fit recording. Upload it from the watch again.",
    "no_gps": "The recording has no GPS track (the watch had no signal, the activity was indoors, or another recording "
              "is assigned to the race). Choose or upload another run for the race.",
    "no_course_print": "The file has no printed course: the map with the course has no purple control circles. Most "
                       "likely a map without the course was uploaded in its place; upload the map with the course of "
                       "your category.",
    "no_start": "The start (purple triangle) could not be found on the map with the course. Check that it is the map "
                "with the course of your category and that the whole start is visible on it.",
    "no_finish": "The finish (double circle) could not be found on the map with the course. Check that it is the map "
                 "with the course of your category and that the whole finish is visible on it.",
    "track_off_course": "The recording from the watch does not pass the controls of this course: most likely another run "
                        "is assigned to the race, the map is of another category, or the recording does not cover the "
                        "time of the race. Check the assigned run and the map with the course.",
}


def analysis_error(code, detail=""):
    text = ANALYSIS_ERRORS.get(code, "The analysis failed.")
    m = re.search(r"it is (\d+) m from the controls \(median\) and (\d+) of (\d+) legs", detail or "")
    if code == "track_off_course" and m:
        text += f" (The track is at best {m.group(1)} m from the controls, median; {m.group(2)} of {m.group(3)} legs are missing.)"
    m = re.search(r"start ([+-]\d+) s from the start of the recording, finish ([+-]\d+) s from its end", detail or "")
    if code == "track_off_course" and m:
        a, b = int(m.group(1)), int(m.group(2))
        text += (" The recording does not cover the time of the race: "
                 + ", ".join(p for p in (f"it starts {mmss(-a)} after the start" if a < 0 else "",
                                         f"it ends {mmss(b)} before the finish" if b > 0 else "") if p) + ".")
    return text


BY_HAND = "You can also place the photo by hand by clicking a few controls (the link Place the photo by hand)."
PHOTO_PROBLEMS = {
    "few": "Click at least 4 controls, as far from each other as possible (the corners of the course).",
    "line": "The points lie almost on a line, and a map cannot be placed from them. Add controls away from that line.",
    "mirror": "The points come out as a mirror image of the map. Check that every point is on the right control.",
    "same": "You marked the same control twice.",
}


def photo_problem(code, name=None, metres=None):
    if code == "loose":
        return (f"The points do not fit together (by up to {metres:.0f} m). Check that each is on the right control, or "
                "add another control; with more points the app can tell which one does not fit.")
    if code == "far":
        who = "Start" if name == "S" else "Finish" if name == "C" else f"Control {name}"
        return f"{who} is off by {metres:.0f} m. Did you click the right circle?"
    return PHOTO_PROBLEMS[code]


def photo_failed(reason, quality, by_hand=False):
    if by_hand:
        codes = re.findall(r"few|line|mirror", reason)
        return "The points are not enough to place the map. " + (" ".join(PHOTO_PROBLEMS[c] for c in codes) or "Try other controls.")
    if quality.get("sheets", 0) >= 2:
        return ("The photo seems to show two maps (front and back, or a map change). Upload each one separately; we cannot "
                "join a map on two sheets yet.")
    if quality.get("dark"):
        return "The photo is too dark and the control circles cannot be found on it. Take the photo again in daylight, without flash."
    if quality.get("blurry"):
        return ("The photo is blurred and the control circles cannot be found on it. Take it again in focus (hold the phone "
                "still and tap the map to focus).")
    m = re.match(r"too few points: (\d+) circles in the picture, (\d+) controls", reason)
    if m and int(m.group(2)) < 4:
        return ("Your track from the watch does not run at the official punch times (the recording does not start at the "
                "time of your start according to ORIS). Is it a run from this race? Upload the right .fit, then the photo again.")
    if m:
        n = int(m.group(1))
        return (f"{n} control {_plural(n, 'circle is', 'circles are')} visible on the photo, your course has {m.group(2)}. "
                f"Take a photo of the whole map. {BY_HAND}")
    m = re.match(r"the circles in the picture do not fit the track: (\d+) of (\d+) controls matched(?: \((\d+) circles\))?",
                 reason)
    if m:
        n, total, seen = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
        covered = ("a glare or a finger covers the circles, or the map is cut off" if seen < 0.7 * total
                   else "a glare or a finger covers the circles")
        return (f"The circles on the photo do not match your track: only {n} of {total} controls fit ({seen} "
                f"{_plural(seen, 'circle', 'circles')} visible on the photo). Either it is the map of another category or a "
                f"run from another race, or {covered}. Take a photo of the whole map without glare. {BY_HAND}")
    if reason.startswith("no control circles"):
        return ("No purple control circles are visible on the photo. Is it a map with the course? Upload a map without the "
                "course as a KMZ from Livelox.")
    m = re.match(r"the fit is too loose: (\d+) m RMS on (\d+) controls", reason)
    if m:
        return f"The placement is inaccurate (deviation {m.group(1)} m on {m.group(2)} controls). {BY_HAND}"
    return "The photo could not be placed: " + georef_reason(reason)


SAME_VIEW = "Take both screenshots one right after the other from the same view, just switch the course off (do not move or zoom the map)."
SCREEN_FAILED = {
    "size": "The screenshots are not the same size. Take both from the same view, just switch the course off.",
    "no_course": ("The course (purple control circles) is not visible on the screenshots. One screenshot should have the "
                  "course, the other the same view with the course switched off."),
    "course_in_maponly": "The screenshot without the course still shows the course. Switch it off in Livelox and take it again.",
    "routes": ("The screenshots show runners' routes (coloured lines across the map). Switch the other runners off in Livelox "
               "(and yourself) and take both screenshots again."),
    "zoom": "The zoom or rotation of the map changed between the screenshots. " + SAME_VIEW,
    "unrelated": ("The screenshots do not belong together: they differ outside the course. Is the screenshot without the "
                  "course from the same race and the same view? " + SAME_VIEW),
}
SCREEN_CROP = ("If the app took a piece of the Livelox page (the bar, the list of runners) for the map, crop the screenshot "
               "by hand (the link Crop the screenshot).")
SCREEN_NOTES = {
    "swapped": "The screenshots were swapped (the course was on the second one); I swapped them back.",
    "coarse": ("The screenshot is not zoomed in much ({res} m per pixel) and the terrain is harder to read from it. Zoom in on "
               "the map and cover a larger area."),
    "coarse_stop": ("The screenshot is zoomed in too little ({res} m per pixel): I am not making the map without the course "
                    "from it, the best routes would come out wrong. Zoom in on the map and cover a larger area."),
    "faint_course": ("The course was still faintly visible (transparent) on the screenshot without the course; I removed its "
                     "colour. If the course can be switched off completely in Livelox, the map will be cleaner."),
    "unsure_area": ("I could not tell for certain where the map ends and the Livelox page begins on the screenshot. Look at "
                    "the map, and if a piece of the bar or the background is in it, crop the screenshot by hand (the link "
                    "Crop the screenshot)."),
}


def screen_failed(code, data=None):
    data = data or {}
    if code == "far":
        return f"The map moved by {data.get('px', 0):.0f} px between the screenshots. " + SAME_VIEW
    if code == "no_fit":
        reason = data.get("reason", "")
        if reason.startswith("no control circles"):
            return "No control circles are visible on the screenshot with the course. Is the course of your category switched on in Livelox?"
        m = re.match(r"the circles in the picture do not fit the track: (\d+) of (\d+) controls matched", reason)
        if m:
            return (f"The circles on the screenshot do not match your track: only {m.group(1)} of {m.group(2)} controls fit. "
                    "Is it the course of your category and a run from this race? The whole course should be visible on the "
                    "screenshot.")
        m = re.match(r"too few points: (\d+) circles in the picture, (\d+) controls", reason)
        if m and int(m.group(2)) >= 4:
            n = int(m.group(1))
            return (f"{n} control {_plural(n, 'circle is', 'circles are')} visible on the screenshot, your course has "
                    f"{m.group(2)}. Zoom out so that the whole course is visible.")
        return "The screenshot with the course could not be placed: " + georef_reason(reason)
    return SCREEN_FAILED[code]


def screen_note(code, res=None):
    if code not in SCREEN_NOTES:
        return None
    return SCREEN_NOTES[code].format(res=f"{res:.1f}" if res else "?")


def georef_reason(reason):
    m = re.fullmatch(r"too few points: (\d+) circles in the picture, (\d+) controls with a punch time", reason)
    if m:
        return f"{m.group(1)} control circles are visible in the picture and the splits have {m.group(2)} controls; that is too few."
    m = re.fullmatch(r"the circles in the picture do not fit the track: (\d+) of (\d+) controls matched"
                     r"(?: \(\d+ circles\))?", reason)
    if m:
        return (f"the circles in the picture do not match your track (only {m.group(1)} of {m.group(2)} controls fit). "
                "Is it the map of this category and a run from this race?")
    m = re.fullmatch(r"the fit is too loose: (\d+) m RMS on (\d+) controls", reason)
    if m:
        return f"the placement is too inaccurate (deviation {m.group(1)} m on {m.group(2)} controls)."
    if reason.startswith("no control circles"):
        return "no purple control circles are visible in the picture (is it a map with the course?)."
    return reason


def official_reason(reason):
    m = re.fullmatch(r"official results have (-?\d+) controls, the course read from the map has (\d+)", reason or "")
    if m:
        return f"ORIS has {m.group(1)} controls, {m.group(2)} were read from the map"
    if reason and reason.startswith("the recording does not cover"):
        return "the recording from the watch does not cover the official time of the race"
    m = re.fullmatch(r"at the official times the track is (\d+) m from the controls \(median\)", reason or "")
    if m:
        return f"at the official times the track is {m.group(1)} m from the controls"
    if reason == "no official finish time":
        return "ORIS has no finish time"
    return reason or ""
