"""Czech wording for the numbers and English notes the analysis produces. In an English page the same functions
answer from webapp/texts_en.py (see the end of this file)."""
import functools
import re

from . import i18n


def mmss(s, sign=False):
    """Seconds -> 'm:ss' (minutes may exceed 59, as orienteering results write them)."""
    if s is None:
        return ""
    neg = s < 0
    s = int(round(abs(s)))
    # a real minus sign, and no sign on a time that rounds to nothing ("−0:00" reads like a mistake)
    return ("\u2212" if neg and s else "+" if sign and s else "") + f"{s // 60}:{s % 60:02d}"


def parse_time(text):
    """'55:07', '1:20:18' or '' -> seconds or None; ValueError when it is not a time."""
    text = (text or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if not 2 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
        raise ValueError(text)
    s = 0
    for p in parts:
        s = s * 60 + int(p)
    return s


CONFIDENCE = {"high": ("jistá", "ob-ok"), "medium": ("pravděpodobná", "ob-warn"), "low": ("nejistá", "ob-bad"),
              "manual": ("ruční", "ob-ok"), "none": ("žádná", ""), None: ("žádná", "")}


def confidence():
    """CONFIDENCE in the language of the page: {key: (label, css class)}."""
    from . import texts_en
    return texts_en.CONFIDENCE if i18n.lang() == "en" else CONFIDENCE


def screen_crop():
    """The hint to crop a screenshot by hand."""
    from . import texts_en
    return texts_en.SCREEN_CROP if i18n.lang() == "en" else SCREEN_CROP


def lost_name(kind):
    """What the "I am lost" page calls a catching feature (in the list under the advice)."""
    from . import texts_en
    return texts_en.lost_name(kind) if i18n.lang() == "en" else LOST_NAMES.get(kind, (kind,))[0]

_NOTES = [
    (r"no activity that day", "ten den není žádná aktivita"),
    (r"only (\w+) that day", r"ten den je jen aktivita typu \1"),
    (r"(\d+) runs that day, picked the one closest to the race time",
     r"běhů ten den: \1, vybrán ten nejbližší oficiálnímu času"),
    (r"(\d+) runs that day, picked the one started at the official start time",
     r"běhů ten den: \1, vybrán ten odstartovaný v čase startu"),
    (r"activity [+-](\d+) min vs race time", r"běh se od oficiálního času liší o \1 min"),
    (r"no official time, matched by date only", "bez oficiálního času, spárováno jen podle data"),
    (r"activity has no GPS \(watch not started properly\?\)", "aktivita nemá GPS (hodinky nebyly správně spuštěné?)"),
    (r"only an activity without GPS that day",
     "ten den je jen aktivita bez GPS (hodinky bez signálu nebo spuštěné pozdě); nahraj jiný záznam"),
    (r"(\d+) activities that day, picked the one matching the race time",
     r"záznamů ten den: \1, vybrán ten, který odpovídá času závodu"),
    (r"activity starts (\d+) km from the race", r"aktivita začíná \1 km od centra závodu"),
    (r"(\d+) activities that day, picked the one that starts at the race",
     r"záznamů ten den: \1, vybrán ten, který začíná u centra závodu"),
]


def match_note(note):
    for pat, cs in _NOTES:
        if note and re.fullmatch(pat, note):
            return re.sub(pat, cs, note)
    return note or ""


def flags(leg, vref, deliberate_s=0.0):
    """The mistake signals of a leg (analysis.flag_legs codes) in Czech."""
    out = []
    for c in leg.get("flag_codes") or []:
        if c == "ratio":
            out.append(f"postup {leg['ratio']:.1f}× delší než přímka".replace(".", ","))
        elif c == "entries":
            out.append(f"{leg['zone_entries']}× vstup do 100 m okolo kontroly (přeběhnutí, kroužení)")
        elif c == "zone":
            out.append(f"asi {leg['zone_excess']:.0f} s navíc u kontroly")
        elif c == "stop" and leg["stop_time"] - deliberate_s > 15:
            out.append(f"stání {leg['stop_time'] - deliberate_s:.0f} s")
        elif c == "slow":
            out.append(f"pomalu ({leg['speed'] * 3.6:.1f} km/h, obvykle {vref * 3.6:.1f})".replace(".", ","))
        elif c == "no_data":
            out.append("chybí záznam z hodinek (nedostatek dat)")
    return out


def gps_trouble(g):
    """"GPS tu asi zlobí" with why (services/results.gps_trouble), or None."""
    if not g:
        return None
    why = []
    if g.get("far_m") and g["far_m"] > 30:
        why.append(f"u ražení je stopa {g['far_m']} m od kontroly")
    if g.get("jump_kmh"):
        why.append(f"stopa skáče ({g['jump_kmh']} km/h)")
    return "GPS tu asi zlobí: " + " a ".join(why) + ". Když víš, kudy jsi běžel, oprav si stopu."


def turns(deg):
    """A total change of heading as one can picture it: 'otočil asi dvakrát dokola'."""
    if deg is None:
        return "točil"
    k = deg / 360.0
    if k < 1.25:
        return "otočil asi jednou dokola"
    if k < 1.75:
        return "otočil asi jedenapůlkrát dokola"
    n = int(round(k))
    return f"otočil asi {({2: 'dvakrát', 3: 'třikrát', 4: 'čtyřikrát'}).get(n, f'{n}×')} dokola"


def mistake(m, read=None, note=None):
    """The kind of mistake at a control (oroute.mistakes.classify) in Czech: dict(label, text, at) or None."""
    if not m or not m.get("type"):
        return None
    label, text = MISTAKES.get(m["type"], (m["type"], ""))
    try:
        text = text.format(turns=turns(m.get("turn")), **m)
    except (KeyError, IndexError, ValueError):
        pass
    return dict(type=m["type"], label=label, text=text, at=m.get("at"))


def attack(a):
    """A suggested attack point (oroute.relocate, before it oroute.mistakes.attack_point) in Czech; it is an
    estimate read from the map."""
    if not a:
        return None
    kind = FEATURES.get(a.get("kind"), ("bod na cestě", "", ""))[0]
    return dict(lat=a["lat"], lon=a["lon"], label=f"{kind} {a['dist']:.0f} m před kontrolou")


# kind of a catching feature (oroute.relocate) -> (what it is, the preposition of "from it", its genitive).
# The names are those of ISOM 2017-2 in the Czech edition of ČSOS (the symbol numbers are in the comments);
# "oplocenka" is what runners call ground closed in by a fence.
FEATURES = {
    "junction": ("křížení cest", "z", "křížení cest"),                                  # 502-508 meeting
    "path_end": ("konec cesty", "z", "konce cesty"),
    "path": ("cesta", "z", "cesty"),                                                    # 502-508
    "stream_path": ("cesta přes vodoteč", "z", "přechodu cesty přes vodoteč"),
    "stream": ("vodoteč", "od", "vodoteče"),                                            # 304-306
    "pond": ("vodní plocha", "od", "vodní plochy"),                                     # 301, 302
    "building": ("budova", "od", "budovy"),                                             # 521
    "enclosure": ("oplocenka", "od", "oplocenky"),                                      # 516, 518 around an area
    "fence": ("plot", "od", "plotu"),                                                   # 516, 518 as a line
    "settlement": ("okraj zakázaného prostoru (zástavba)", "od", "okraje zakázaného prostoru"),   # 520
    "clearing": ("paseka", "z", "paseky"),                                              # 401, 403, small
    "open_edge": ("okraj otevřené plochy", "z", "okraje otevřené plochy"),              # 401-404
    "hilltop": ("vrchol", "z", "vrcholu"),                                              # from the elevation
    "knoll": ("kupka", "z", "kupky"),                                                   # 109
    "depression": ("prohlubeň", "z", "prohlubně"),                                      # 111
    "pit": ("jáma", "z", "jámy"),                                                       # 112
    "landform": ("výrazný terénní objekt", "od", "výrazného terénního objektu"),        # 115
    "boulder": ("balvan", "od", "balvanu"),                                             # 204, 205
    "water_pit": ("jáma s vodou", "od", "jámy s vodou"),                                # 303
    "well": ("studna nebo nádrž", "od", "studny nebo nádrže"),                          # 311
    "tree": ("výrazný strom", "od", "výrazného stromu"),                                # 417
    "stand": ("posed", "od", "posedu"),                                                 # 525
    "object": ("výrazný umělý objekt", "od", "výrazného umělého objektu"),              # 530, 531
}


def bearing(deg):
    """A bearing rounded to five degrees, as one sets it on a compass: '215°'."""
    return f"{int(round(deg / 5.0)) * 5 % 360}°"


def slope(dh, dist):
    """Going `dist` metres to a place `dh` metres higher, in words."""
    grade = dh / max(dist, 1.0)
    if abs(dh) < 3 or abs(grade) < 0.04:
        return "po rovině"
    return ("mírně " if abs(grade) < 0.12 else "") + ("do kopce" if dh > 0 else "z kopce")


def feature(f):
    """One catching feature in Czech: where it lies seen from the control, and how to get from it to the control.
    Where something one cannot go through lies on the straight line (f["via"]: the way round it), the way
    round is given, with the bearing to set off on: the straight bearing would lead into the obstacle."""
    name, prep, of_it = FEATURES.get(f["kind"], (f["kind"], "z", "toho místa"))
    nearest = "" if f["point"] else ", nejblíž"       # of a line the nearest point is given
    if f.get("via"):
        back = (f"{prep} {of_it} obchůzkou {f['walk']:.0f} m, nejdřív na azimut {bearing(f['first_az'])} "
                f"(přímo je překážka), {slope(f['dh'], f['dist'])}")
    else:
        back = f"{prep} {of_it} {f['dist']:.0f} m na azimut {bearing(f['back_az'])}, {slope(f['dh'], f['dist'])}"
    return dict(kind=f["kind"], lat=f["lat"], lon=f["lon"], point=f["point"], label=name,
                where=f"{name}{nearest} {f['dist']:.0f} m od kontroly na azimut {bearing(f['az'])}",
                back=back, via=f.get("via"))


def relocate(r):
    """What oroute.relocate found around the control of a leg, in Czech: the catching features, and when the
    track shows the runner was lost there, where and what was close by. None when it was not computed."""
    if not r:
        return None
    lost = None
    if r.get("lost"):
        l = r["lost"]
        text = (f"U téhle kontroly jsi bloudil: přímý směr k ní jsi opustil {l['dist']:.0f} m před ní, naběhal jsi "
                f"{l['extra_m']:.0f} m navíc a stálo to asi {mmss(l['extra_s'])}.")
        near = l.get("near")
        if near:
            of_it = FEATURES.get(near["kind"], (near["kind"], "z", "záchytného bodu"))[2]
            if near.get("via"):
                text += (f" Byl jsi {near['track_m']:.0f} m od {of_it}, odkud se ke kontrole jde obchůzkou "
                         f"{near['walk']:.0f} m, nejdřív na azimut {bearing(near['first_az'])} (přímo je překážka).")
            else:
                text += (f" Byl jsi {near['track_m']:.0f} m od {of_it}, odkud vede ke kontrole přímý azimut "
                         f"{bearing(near['back_az'])} ({near['dist']:.0f} m, {slope(near['dh'], near['dist'])}).")
        else:
            text += " Žádný záchytný bod jsi při tom neminul blíž než 120 m."
        lost = dict(i=l["i"], at=[l["lat"], l["lon"]], text=text,
                    near=dict(lat=near["lat"], lon=near["lon"], i=near["i"], via=near.get("via")) if near else None)
    return dict(features=[feature(f) for f in r.get("features") or []], lost=lost)


SIDES = {"left": "vlevo", "ahead": "rovně", "right": "vpravo"}


def beyond(b):
    """The backstop beyond the control (oroute.relocate.beyond) in Czech: what a runner who ran on past the
    control runs into to the left, straight on and to the right, and the bearing back. None when there is
    none, and for a result of before the backstop had parts (a single point)."""
    if not b or not b.get("parts"):
        return None
    name = lambda q: FEATURES.get(q["kind"], (q["kind"], "", ""))[0]
    got = {q["side"]: q for q in b["parts"]}
    if len(got) == 3 and len({q["kind"] for q in got.values()}) == 1:
        near, far = (f(round(q["dist"]) for q in got.values()) for f in (min, max))
        label = f"{name(got['ahead'])} napříč {near if near == far else f'{near}–{far}'} m za kontrolou"
    else:
        label = ", ".join(f"{SIDES[s]} {name(got[s])} {got[s]['dist']:.0f} m" for s in SIDES if s in got)
        none = [SIDES[s] for s in SIDES if s not in got]
        if none:
            label += f"; {' a '.join(none)} nic do {b.get('within', 200):.0f} m"
    return dict(label=label,
                text=f"{label}. Kdo tam doběhne, kontrolu přeběhl a vrací se na azimut {bearing(b['back_az'])}",
                parts=[dict(lat=q["lat"], lon=q["lon"], line=q.get("line") or [],
                            label=f"{SIDES[q['side']]} {name(q)} {q['dist']:.0f} m za kontrolou") for q in b["parts"]])


# "I am lost at the control" (oroute.lost): kind -> (what it is, "to it" with its preposition, "along it",
# what one passes on the way in the accusative, whether it is a line one crosses). Names as in FEATURES.
LOST_NAMES = {
    "path": ("cesta", "k cestě", "ní", "cestu", True),
    "stream": ("vodoteč", "k vodoteči", "ní", "vodoteč", True),
    "fence": ("plot", "k plotu", "něj", "plot", False),
    "settlement": ("okraj zakázaného prostoru", "k okraji zakázaného prostoru", "něj", "okraj zakázaného prostoru", False),
    "open_edge": ("okraj otevřené plochy", "k okraji otevřené plochy", "něj", "okraj otevřené plochy", True),
    "pond": ("vodní plocha", "k vodní ploše", "ní", "vodní plochu", False),
    "building": ("budova", "k budově", "ní", "budovu", False),
    "wall": ("zeď", "ke zdi", "ní", "zeď", False),
    "junction": ("křížení cest", "ke křížení cest", "něj", "křížení cest", False),
    "path_end": ("konec cesty", "ke konci cesty", "něj", "konec cesty", False),
    "stream_path": ("cesta přes vodoteč", "k přechodu cesty přes vodoteč", "něj", "přechod cesty přes vodoteč", False),
    "clearing": ("paseka", "k pasece", "ní", "paseku", False),
    "hilltop": ("vrchol", "k vrcholu", "něj", "vrchol", False),
    "knoll": ("kupka", "ke kupce", "ní", "kupku", False),
    "depression": ("prohlubeň", "k prohlubni", "ní", "prohlubeň", False),
    "pit": ("jáma", "k jámě", "ní", "jámu", False),
    "landform": ("výrazný terénní objekt", "k výraznému terénnímu objektu", "něj", "výrazný terénní objekt", False),
    "boulder": ("balvan", "k balvanu", "něj", "balvan", False),
    "water_pit": ("jáma s vodou", "k jámě s vodou", "ní", "jámu s vodou", False),
    "well": ("studna nebo nádrž", "ke studni nebo nádrži", "ní", "studnu nebo nádrž", False),
    "tree": ("výrazný strom", "k výraznému stromu", "něj", "výrazný strom", False),
    "stand": ("posed", "k posedu", "něj", "posed", False),
    "object": ("výrazný umělý objekt", "k výraznému umělému objektu", "něj", "výrazný umělý objekt", False),
}
COMPASS = ("sever", "severovýchod", "východ", "jihovýchod", "jih", "jihozápad", "západ", "severozápad")
LOST_WHY = {"mistake:overshoot": "přeběhl jsi kontrolu", "mistake:undershoot": "zastavil ses před kontrolou",
            "mistake:drift": "dobíhal jsi z boku", "mistake:circling": "kroužil jsi",
            "mistake:relocation": "zastavil ses a hledal, kde jsi", "mistake:slow": "zpomalil jsi",
            "stop": "zastavil ses", "slow": "zpomalil jsi", "loop": "kroužil jsi", "turn": "otočil ses",
            "lost": "tady jsi ztratil kontakt s mapou"}


def compass(deg):
    """One of the eight directions: 'sever' for 337.5..22.5 degrees."""
    return COMPASS[int((deg % 360.0 + 22.5) // 45.0) % 8]


def about(m):
    """A distance as said in the forest: to 5 m up to 100 m, to 10 m above."""
    step = 5 if m <= 100 else 10
    return max(step, int(round(m / step)) * step)


def _ln(kind):
    return LOST_NAMES.get(kind, (kind, f"k {kind}", "něj", kind, False))


NEUTER = {"junction"}  # "křížení cest"; the other names are masculine or feminine (LOST_NAMES[...][2])


def _rod(kind, m, f, n):
    """The word of the right gender for the feature: _rod(kind, "ten", "ta", "to")."""
    if kind in NEUTER:
        return n
    return f if _ln(kind)[2] == "ní" else m


def _seen(seen):
    """What is passed on the way: 'po 30 m bys přešel vodoteč, po 80 m minul křížení cest'."""
    out = []
    for i, (kind, m) in enumerate(seen[:2]):
        n = _ln(kind)
        out.append(f"po {about(m)} m {'bys ' if i == 0 else ''}{'přešel' if n[4] else 'minul'} {n[3]}")
    return ", ".join(out)


def _from_line(h):
    """The second sentence: from the feature to the control (oroute.lost._link). The page is a look back after
    the race (no aids are allowed during it): what the runner should have done, in the past tense."""
    link, n = h["link"], _ln(h["kind"])
    if link["type"] == "near" and h["kind"] not in ("building", "pond", "wall", "settlement"):
        if link.get("az") is not None and link.get("along"):
            where = "přímo u " + n[2] if link["dist"] < 8 else \
                f"{about(link['dist'])} m {'vpravo' if link.get('side') == 'right' else 'vlevo'}"
            if link["dist"] > 40:          # (farther than a glance: with the bearing, lost.LINK_NEAR_FAR_M)
                where += f" na azimut {bearing(link['az_off'])}"
            return f"Pak podél {n[2]} na {compass(link['az'])} asi {about(link['along'])} m, kontrola byla {where}."
        return f"Kontrola byla od {n[2]} {about(link['dist'])} m na azimut {bearing(link['az_off'])}."
    if link["type"] == "point":
        p = _ln(link["point"])
        return (f"Pak podél {n[2]} na {compass(link['az'])} {p[1]} (asi {about(link['along'])} m), odtud kontrola "
                f"{about(link['dist'])} m na azimut {bearing(link['az_off'])}.")
    if link.get("round"):
        return (f"Odtud ke kontrole asi {about(link['dist'])} m obchůzkou, nejdřív na azimut {bearing(link['az_off'])} "
                "(přímo byla překážka).")
    return f"Odtud kontrola {about(link['dist'])} m na azimut {bearing(link['az_off'])}."


def lost_advice(a):
    """The advice of oroute.lost.public in one to three Czech sentences (rules, no language model), in the past
    tense: what one should have done there (the page looks back at a race)."""
    if a is None:
        return []
    if a.get("far"):
        return ["Tohle místo je dál než 300 m od kontroly. Ťukni blíž ke kontrole; odsud ses měl vrátit na poslední "
                "místo, kde jsi věděl, kde jsi."]
    out = []
    t = a.get("attack")
    if a.get("pick") is None:
        out.append("Kolem nebylo nic, čeho by ses dal jistě chytit.")
        if t and t.get("to"):
            out.append(f"Měl ses vrátit na náběhový bod ({_ln(t['kind'])[0]} {about(t['dist'])} m na azimut "
                       f"{bearing(t['az'])}) a začít znovu odtud: kontrola byla {about(t['to']['dist'])} m na azimut "
                       f"{bearing(t['to']['az'])}.")
    else:
        h = a["helpers"][a["pick"]]
        n = _ln(h["kind"])
        way = f"asi {about(h['dist'])} m, azimut {bearing(h['az'])}"
        if h.get("seen"):
            way += ", " + _seen(h["seen"])
        if a.get("no_runner"):
            k = h["kind"]
            first = (f"Když jsi nevěděl, kde u kontroly jsi: na {compass(h['az'])} {_rod(k, 'byl', 'byla', 'bylo')} do "
                     f"{about(h['dist'] + a['r'])} m {n[0]}"
                     + (", " + _rod(k, "ten se nedal", "ta se nedala", "to se nedalo") + " minout." if h["sure"] else "."))
        elif h.get("inside"):
            k = h["kind"]
            it = _rod(k, "ho", "ji", "ho")
            of_it = FEATURES.get(k, (None, None, "zdi" if k == "wall" else n[0]))[2]
            led = _rod(k, "vedl", "vedla", "vedlo")
            first = (f"Do {about(a['r'])} m od tebe {led} {n[0]} (nejblíž na {compass(h['az'])}, asi {about(h['dist'])} m): "
                     f"měl jsi {it} najít." if h["dist"] >= 8 else
                     f"Byl jsi u {of_it}, měl ses {_rod(k, 'ho', 'jí', 'ho')} držet.")
        elif not h["sure"]:
            first = (f"Nic se odtud nedalo chytit úplně jistě; nejlepší bylo jít na {compass(h['az'])} {n[1]} ({way}).")
        elif a.get("relocate_first"):
            go = "ses měl vrátit" if a.get("back") else "jsi měl dojít"
            first = (f"Neměl jsi hádat směr ke kontrole. Nejdřív {go} na {compass(h['az'])} {n[1]} ({way}), "
                     f"{_rod(h['kind'], 'ten se nedal', 'ta se nedala', 'to se nedalo')} minout.")
        else:
            first = f"Měl jsi jít na {compass(h['az'])} {n[1]} ({way})."
        out += [first, _from_line(h)]
        if not h["sure"] and t and t.get("to") and not a.get("no_runner"):
            out[-1] += (f" Kdybys {_rod(h['kind'], 'ho', 'ji', 'ho')} nenašel, měl ses vrátit na náběhový bod "
                        f"({_ln(t['kind'])[0]}, {about(t['dist'])} m "
                        f"na azimut {bearing(t['az'])}).")
    if a.get("desc"):
        out.append(f"Podle popisu jsi hledal: {a['desc']}.")
    return out[:3]


def lost_note(a):
    """A line above the advice when the tap was where one must not be."""
    return "Tam, kam jsi ťukl, se nesmí (oplocenka, zakázaný prostor, voda); beru nejbližší místo venku." \
        if a and a.get("snapped") else None


def lost_moment(m):
    """A place of oroute.lost.look_back (public_moment) for the page: what happened, what was there to see, the way."""
    why = LOST_WHY.get(m["why"], LOST_WHY.get(m["why"].split(":")[0], "zaváhal jsi"))
    head = f"{about(m['dist'])} m od kontroly {why}."
    near = [f"{_ln(k)[0]} {about(d)} m na {compass(az)}" for k, d, az in m.get("near") or []]
    seen = ("Měl jsi vidět: " + ", ".join(near) + ".") if near else "Do 30 m kolem nebylo nic jistého."
    crossed = [f"{_ln(k)[3]} {about(d)} m předtím" for k, d in m.get("crossed") or []]
    if crossed:
        seen += " Přešel jsi " + ", ".join(crossed) + "."
    return dict(head=head, seen=seen, back=lost_advice(m["advice"]))


# what a track went through that the routes must not (oroute.routing.crossed) -> (what the track did, what to
# do about it when it was allowed)
CROSSED = {
    "railway": ("kříží železnici mimo přechod",
                "Když se přebíhat smělo, přepni v Nastavení závodu „Železnice a dálnice“ na „nepoužívat“."),
    "motorway": ("kříží dálnici mimo přechod",
                 "Když se přebíhat smělo, přepni v Nastavení závodu „Železnice a dálnice“ na „nepoužívat“."),
    "manual": ("kříží ručně nakreslenou zakázanou čáru",
               "Když tam čára být nemá, smaže ji v Nastavení závodu ten, kdo ji nakreslil."),
    "area": ("vede zakázaným prostorem ze šrafování mapy",
             "Když se tam smělo, přepni v Nastavení závodu „Zakázané prostory z mapy“ na „nepoužívat“."),
    "enclosure": ("vede přes oplocenku",
                  "Oplocenku bere aplikace jako neprůchodnou; když tam plot není nebo má branku, ber rozdíl s rezervou."),
}


def crossed(found):
    """What the runner's track went through that the best route must not, in Czech: dict(text, at=[[lat, lon]])
    or None. The track is priced without these barriers, so it can come out faster than the best route."""
    known = [c for c in found or [] if c.get("what") in CROSSED]
    if not known:
        return None
    did, advice = [], []
    for c in known:
        for item, seen in zip(CROSSED[c["what"]], (did, advice)):
            if item not in seen:
                seen.append(item)
    return dict(at=[c["at"] for c in known],
                text=f"Tvoje stopa {' a '.join(did)}. Nejlepší postup tudy nesmí, proto obíhá a může vyjít "
                     f"pomaleji než tvoje stopa. {' '.join(advice)}")


# type -> (short label, sentence); the numbers come from oroute.mistakes.classify
MISTAKES = {
    "overshoot": ("přeběhnutí", "Minul jsi kontrolu o {miss:.0f} m, běžel dál ještě {over:.0f} m a vracel ses "
                                "({back:.0f} s od průběhu kolem kontroly do ražení)."),
    "undershoot": ("nedoběhnutí", "Asi {dist:.0f} m před kontrolou jsi zpomalil nebo stál ({stop:.0f} s) a hledal; "
                                  "kontrola byla dál ve směru postupu."),
    "drift": ("úhyb ze směru", "Většinu úseku jsi běžel vedle spojnice (až {dev:.0f} m stranou) a ke kontrole jsi "
                               "dobíhal skoro kolmo na směr postupu."),
    "circling": ("hledání v kruhu", "V okruhu 100 m od kontroly ses {turns} a strávil tam {time:.0f} s."),
    "relocation": ("zastavení a nové určení polohy", "Stál jsi {stop:.0f} s a potom jsi změnil směr o {turn:.0f}°: "
                                                    "určoval sis znovu polohu."),
    "slow": ("pomalu, bez chyby v mapě", "Stopa vede rozumně, jen pomaleji, než odpovídá terénu: spíš fyzička nebo "
                                         "těžší podložka než mapa."),
}


# why a script could not analyse what it was given (oroute.errors.CODES) -> what to do about it
ANALYSIS_ERRORS = {
    "bad_fit": "Soubor s během se nepodařilo přečíst: není to platný záznam .fit. Nahraj ho z hodinek znovu.",
    "no_gps": "V záznamu není GPS stopa (hodinky bez signálu, aktivita v hale, nebo je k závodu přiřazený "
              "jiný záznam). U závodu vyber nebo nahraj jiný běh.",
    "no_course_print": "V souboru není vytištěná trať: v mapě s tratí nejsou fialová kolečka kontrol. Nejspíš je "
                       "na jejím místě nahraná mapa bez tratě; nahraj mapu s tratí své kategorie.",
    "no_start": "Na mapě s tratí se nepodařilo najít start (fialový trojúhelník). Zkontroluj, že je to mapa s tratí "
                "tvé kategorie a že je na ní start vidět celý.",
    "no_finish": "Na mapě s tratí se nepodařilo najít cíl (dvojité kolečko). Zkontroluj, že je to mapa s tratí tvé "
                 "kategorie a že je na ní cíl vidět celý.",
    "no_network": "Výškopis pro tuhle mapu se nepodařilo stáhnout. Stahuje se jednou pro každý závod (ČÚZK, u zahraničních "
                  "závodů AWS), takže je potřeba internet. Zkontroluj připojení a pusť analýzu znovu; mapy, běhy "
                  "a ostatní stránky fungují i bez něj.",
    "track_off_course": "Záznam z hodinek neprochází kontrolami této tratě: nejspíš je k závodu přiřazený jiný "
                        "běh, mapa jiné kategorie, nebo záznam nepokrývá čas závodu. Zkontroluj přiřazený běh a "
                        "mapu s tratí.",
}


def analysis_error(code, detail=""):
    """The sentence for an input a script could not analyse (oroute.errors), with what the script measured:
    how far the track is from the controls, or by how much the recording misses the race."""
    text = ANALYSIS_ERRORS.get(code, "Analýza selhala.")
    m = re.search(r"it is (\d+) m from the controls \(median\) and (\d+) of (\d+) legs", detail or "")
    if code == "track_off_course" and m:
        text += f" (Stopa je od kontrol nejblíž {m.group(1)} m, medián; chybí {m.group(2)} z {m.group(3)} úseků.)"
    m = re.search(r"start ([+-]\d+) s from the start of the recording, finish ([+-]\d+) s from its end", detail or "")
    if code == "track_off_course" and m:
        a, b = int(m.group(1)), int(m.group(2))
        text += (" Záznam nepokrývá čas závodu: "
                 + ", ".join(p for p in (f"začíná {mmss(-a)} po startu" if a < 0 else "",
                                         f"končí {mmss(b)} před cílem" if b > 0 else "") if p) + ".")
    return text


BY_HAND = "Fotku můžeš také usadit ručně kliknutím na pár kontrol (odkaz Usadit fotku ručně)."
PHOTO_PROBLEMS = {
    "few": "Klikni aspoň na 4 kontroly, co nejdál od sebe (rohy tratě).",
    "line": "Body leží skoro v přímce, z nich se mapa usadit nedá. Přidej kontroly stranou od té přímky.",
    "mirror": "Body vycházejí jako zrcadlově převrácená mapa. Zkontroluj, že každý bod je u správné kontroly.",
    "same": "Stejnou kontrolu jsi označil dvakrát.",
}


def photo_problem(code, name=None, metres=None):
    """A problem of the points clicked on a photo (oroute.georef.fit_points), in Czech."""
    if code == "loose":
        return (f"Body k sobě nesedí (až o {metres:.0f} m). Zkontroluj, že každý je u správné kontroly, nebo přidej "
                "další kontrolu; z víc bodů aplikace pozná, který nesedí.")
    if code == "far":
        who = "Start" if name == "S" else "Cíl" if name == "C" else f"Kontrola {name}"
        return f"{who} nesedí o {metres:.0f} m. Klikl jsi na správné kolečko?"
    return PHOTO_PROBLEMS[code]


def kolecek(n):
    """'je vidět 1 kolečko', 'jsou vidět 3 kolečka', 'je vidět 7 koleček'."""
    if n == 1:
        return "je vidět 1 kolečko"
    if 2 <= n <= 4:
        return f"jsou vidět {n} kolečka"
    return f"je vidět {n} koleček"


def photo_failed(reason, quality, by_hand=False):
    """Why a photo of the map could not be placed (oroute.georef.GeorefError and photo_quality), in Czech, with
    what to do about it."""
    if by_hand:
        codes = re.findall(r"few|line|mirror", reason)
        return "Body nestačí k usazení mapy. " + (" ".join(PHOTO_PROBLEMS[c] for c in codes) or "Zkus jiné kontroly.")
    if quality.get("sheets", 0) >= 2:
        return ("Na fotce jsou asi dvě mapy (přední a zadní strana nebo výměna mapy). Nahraj každou zvlášť; mapu "
                "na dvou listech zatím spojit neumíme.")
    if quality.get("dark"):
        return "Fotka je moc tmavá a kolečka kontrol na ní nejdou najít. Vyfoť mapu znovu za světla, bez blesku."
    if quality.get("blurry"):
        return ("Fotka je rozmazaná a kolečka kontrol na ní nejdou najít. Vyfoť mapu znovu a ostře (podrž mobil "
                "v klidu a ťukni na mapu, ať zaostří).")
    m = re.match(r"too few points: (\d+) circles in the picture, (\d+) controls", reason)
    if m and int(m.group(2)) < 4:
        return ("Tvoje stopa z hodinek v oficiálních časech ražení neběží (záznam nezačíná v čase tvého startu "
                "podle ORIS). Je to běh z tohoto závodu? Nahraj správný .fit, pak fotku znovu.")
    if m:
        return (f"Na fotce {kolecek(int(m.group(1)))} kontrol, tvoje trať jich má {m.group(2)}. Vyfoť celou mapu. "
                f"{BY_HAND}")
    m = re.match(r"the circles in the picture do not fit the track: (\d+) of (\d+) controls matched(?: \((\d+) circles\))?",
                 reason)
    if m:
        n, total, seen = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
        covered = ("kolečka zakrývá odlesk nebo prst, nebo je mapa uříznutá" if seen < 0.7 * total
                   else "kolečka zakrývá odlesk nebo prst")
        return (f"Kolečka na fotce neodpovídají tvé stopě: sedí jen {n} z {total} kontrol (na fotce {kolecek(seen)})."
                f" Buď je to mapa jiné kategorie nebo běh z jiného závodu, nebo {covered}. Vyfoť celou mapu bez "
                f"odlesku. {BY_HAND}")
    if reason.startswith("no control circles"):
        return ("Na fotce nejsou vidět fialová kolečka kontrol. Je to mapa s tratí? Mapu bez tratě nahraj jako KMZ "
                "z Livelox.")
    m = re.match(r"the fit is too loose: (\d+) m RMS on (\d+) controls", reason)
    if m:
        return f"Usazení vychází nepřesně (odchylka {m.group(1)} m na {m.group(2)} kontrolách). {BY_HAND}"
    return "Fotku se nepodařilo usadit: " + georef_reason(reason)


SAME_VIEW = "Udělej oba snímky hned po sobě ze stejného pohledu, jen vypni trať (mapou nehýbej a nepřibližuj)."
SCREEN_FAILED = {
    "size": "Snímky nemají stejnou velikost. Udělej oba ze stejného pohledu, jen vypni trať.",
    "no_course": ("Na snímcích není vidět trať (fialová kolečka kontrol). Jeden snímek má být s tratí, druhý ze "
                  "stejného pohledu s vypnutou tratí."),
    "course_in_maponly": "Na snímku bez tratě je pořád vidět trať. Vypni ji v Livelox a vyfoť znovu.",
    "routes": ("Na snímcích jsou vidět postupy běžců (barevné čáry přes mapu). Vypni v Livelox ostatní běžce (i sebe) "
               "a udělej oba snímky znovu."),
    "zoom": "Mezi snímky se změnilo přiblížení nebo natočení mapy. " + SAME_VIEW,
    "unrelated": ("Snímky k sobě nepatří: mimo trať se liší. Je snímek bez tratě ze stejného závodu a ze stejného "
                  "pohledu? " + SAME_VIEW),
}
SCREEN_CROP = ("Když aplikace vzala za mapu i kus stránky Livelox (lištu, seznam běžců), ořízni snímek ručně "
               "(odkaz Oříznout snímek).")
SCREEN_NOTES = {
    "swapped": "Snímky byly prohozené (trať byla na druhém z nich), prohodil jsem je.",
    "coarse": ("Snímek je málo přiblížený ({res} m na pixel), terén se z něj čte hůř. Přibliž mapu a udělej větší "
               "plochu."),
    "coarse_stop": ("Snímek je moc málo přiblížený ({res} m na pixel): mapu bez tratě z něj nedělám, nejlepší postupy "
                    "by z něj vyšly špatně. Přibliž mapu a udělej větší plochu."),
    "faint_course": ("Na snímku bez tratě byla trať pořád slabě vidět (průhledná); odbarvil jsem ji. Jestli jde v "
                     "Livelox trať vypnout úplně, bude mapa čistší."),
    "unsure_area": ("Kde na snímku končí mapa a začíná stránka Livelox, jsem nepoznal jistě. Podívej se na mapu, a když "
                    "je v ní kus lišty nebo pozadí, ořízni snímek ručně (odkaz Oříznout snímek)."),
}


def screen_failed(code, data=None):
    """Why a pair of Livelox screenshots could not be used (oroute.pair.PairError), in Czech, with what to do."""
    data = data or {}
    if code == "far":
        return f"Mapa se mezi snímky posunula o {data.get('px', 0):.0f} px. " + SAME_VIEW
    if code == "no_fit":
        reason = data.get("reason", "")
        if reason.startswith("no control circles"):
            return "Na snímku s tratí nejsou vidět kolečka kontrol. Je v Livelox zapnutá trať tvé kategorie?"
        m = re.match(r"the circles in the picture do not fit the track: (\d+) of (\d+) controls matched", reason)
        if m:
            return (f"Kolečka na snímku neodpovídají tvé stopě: sedí jen {m.group(1)} z {m.group(2)} kontrol. Zkontroluj "
                    "tři věci: v Livelox je zapnutá trať tvé kategorie (ne jiné), k závodu je spárovaný tvůj běh "
                    "z tohoto dne (Podklady, Běh z hodinek) a kategorie závodu sedí s tou, kterou jsi běžel (jinou "
                    "vybereš pod „Běžel jsem jinou kategorii“). Na snímku má být vidět celá trať.")
        m = re.match(r"too few points: (\d+) circles in the picture, (\d+) controls", reason)
        if m and int(m.group(2)) >= 4:
            return (f"Na snímku {kolecek(int(m.group(1)))} kontrol, tvoje trať jich má {m.group(2)}. Oddal mapu, ať je "
                    "vidět celá trať.")
        return "Snímek s tratí se nepodařilo usadit: " + georef_reason(reason)
    return SCREEN_FAILED[code]


def screen_note(code, res=None):
    """A note on a pair of screenshots that was used (oroute.pair place_pair notes), in Czech; None to say nothing."""
    if code not in SCREEN_NOTES:
        return None
    return SCREEN_NOTES[code].format(res=f"{res:.1f}".replace(".", ",") if res else "?")


def georef_reason(reason):
    """Why a picture could not be placed (oroute.georef.GeorefError), in Czech."""
    m = re.fullmatch(r"too few points: (\d+) circles in the picture, (\d+) controls with a punch time", reason)
    if m:
        c = int(m.group(2))
        return (f"v obrázku {kolecek(int(m.group(1)))} kontrol a mezičasy má {c} "
                f"{'kontrola' if c == 1 else 'kontroly' if 2 <= c <= 4 else 'kontrol'}; to je málo.")
    m = re.fullmatch(r"the circles in the picture do not fit the track: (\d+) of (\d+) controls matched"
                     r"(?: \(\d+ circles\))?", reason)
    if m:
        return (f"kolečka v obrázku neodpovídají tvé stopě (sedí jen {m.group(1)} z {m.group(2)} kontrol). "
                "Je to mapa téhle kategorie a běh z tohoto závodu?")
    m = re.fullmatch(r"the fit is too loose: (\d+) m RMS on (\d+) controls", reason)
    if m:
        return f"usazení je příliš nepřesné (odchylka {m.group(1)} m na {m.group(2)} kontrolách)."
    if reason.startswith("no control circles"):
        return "v obrázku nejsou vidět fialová kolečka kontrol (je to mapa s tratí?)."
    return reason


def official_reason(reason):
    """Why the official times were not used (oroute.official), in Czech."""
    m = re.fullmatch(r"official results have (-?\d+) controls, the course read from the map has (\d+)", reason or "")
    if m:
        return f"ORIS má {m.group(1)} kontrol, z mapy jich je přečteno {m.group(2)}"
    if reason and reason.startswith("the recording does not cover"):
        return "záznam z hodinek nepokrývá oficiální čas závodu"
    m = re.fullmatch(r"at the official times the track is (\d+) m from the controls \(median\)", reason or "")
    if m:
        return f"v oficiálních časech je stopa {m.group(1)} m od kontrol"
    if reason == "no official finish time":
        return "v ORIS chybí čas v cíli"
    return reason or ""


def gps_trim(trim):
    """What was cut off the start and the end of the GPS track (oroute.gpstrim.apply: track["trim"]), in Czech."""
    head, tail, mode = trim.get("head") or [], trim.get("tail") or [], trim.get("mode")
    auto = trim.get("auto") or {}
    out = []
    if head:
        why = auto.get("start_why") if mode == "auto" else None
        out.append(f"začátek stopy uříznutý o {mmss(trim['start_s'])}"
                   + (f" (GPS se ještě nechytila a pak skočila o {why['jump_m']} m)" if why else ""))
    if tail:
        why = auto.get("end_why") if mode == "auto" else None
        out.append(f"konec uříznutý o {mmss(trim['length_s'] - trim['end_s'])}"
                   + (f" (GPS na konci skočila o {why['jump_m']} m)" if why else ""))
    if not out:
        if mode == "off":
            return "Stopa se neořezává, je použitá celá."
        return "Stopa vypadá v pořádku, nic se neořezalo."
    lead = {"auto": "Automaticky: ", "manual": "Ručně: "}.get(mode, "")
    text = lead + " a ".join(out) + "."
    return text[0].upper() + text[1:]


# --- English: the same functions, answered by texts_en.py when the page is English ------------------------------------

def _in_language(name):
    cs = globals()[name]

    @functools.wraps(cs)
    def wrapper(*a, **kw):
        if i18n.lang() == "en":
            from . import texts_en
            return getattr(texts_en, name)(*a, **kw)
        return cs(*a, **kw)
    globals()[name] = wrapper


for _name in ("match_note", "flags", "gps_trouble", "mistake", "attack", "feature", "relocate", "beyond", "lost_advice",
              "lost_note", "lost_moment", "crossed", "analysis_error", "photo_problem", "photo_failed", "screen_failed",
              "screen_note", "georef_reason", "official_reason", "gps_trim"):
    _in_language(_name)
