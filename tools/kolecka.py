#!/usr/bin/env python3
"""Kolečka kontrol proti ORIS: how many control circles the map gives against the number of controls in ORIS.

usage: python3 tools/kolecka.py [--rozbor] [--out kontrola/kitl-kolecka] [--db PATH] [RACE_FOLDER ...]

A folder may also hold races saved by the app (*.obzavod, "Uložit závod do souboru" with the run).

Without folders it goes through every race it can find on this computer, read only:
  data/*/, data-extra/*/, data-extra/dodano/*/   course.kmz with official.json (and run.fit) or race.json
  data-extra/*.kmz                               "NAME, CLASS.kmz", the count from the app's database
  the app's database                             classes with a map with the course (course_file)

For each map: the controls in ORIS (official.json: number of split times; else the control codes of the class), the circles
oroute.course.detect_course reads (those 25 m or more from the finish, as analyze.py counts them) and, with a run
and official times, the circles course.find_missing adds where the watch was at the punch times and those
course.drop_extra leaves out (columns + and -), as analyze.py does.
--rozbor: for every control with no circle near where the watch was at its punch, how much of the best circle
there is printed (share of the outline, the largest gap, a leg line at it), and a crop of the map into --out.
"""
import argparse
import glob
import json
import os
import sqlite3
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from oroute import course as C  # noqa: E402
from oroute.fitload import load_track  # noqa: E402
from oroute.kmzmap import GeoMap  # noqa: E402
from oroute.official import punch_places  # noqa: E402

FINISH_M = 25.0


def app_db():
    for base in (os.environ.get("LOCALAPPDATA"), os.path.expanduser("~/Library/Application Support")):
        if base:
            p = os.path.join(base, "KudyJsemMelBezet", "app.db")
            if os.path.exists(p):
                return p
    return None


def oris_count(con, event_name=None, class_name=None, oris_id=None):
    if con is None or not class_name:
        return None
    if oris_id:
        row = con.execute("SELECT c.control_codes FROM classes c JOIN events e ON e.id = c.event_id "
                          "WHERE e.oris_id = ? AND c.name = ?", (oris_id, class_name)).fetchone()
    else:
        # the file names of Livelox write "/" as "_"; a name several events have (a league) says nothing
        rows = {r[0] for r in con.execute("SELECT c.control_codes FROM classes c JOIN events e ON e.id = c.event_id "
                                          "WHERE replace(e.name, '/', '_') = ? AND c.name = ?",
                                          (event_name, class_name))}
        return codes(rows.pop()) if len(rows) == 1 else None
    return codes(row[0]) if row else None


def codes(text):
    """The number of controls in the split times of ORIS (not classes.controls: it is often more)."""
    n = len(json.loads(text)) if text else 0
    return n or None


def from_obzavod(path):
    """A race saved by the app (Uložit závod do souboru, with the run): unpacked next to the crops."""
    import zipfile

    from webapp.oris import start_utc
    dest = os.path.join(HERE, "kontrola", "kitl-kolecka", "_obzavod", os.path.basename(path)[:-8])
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        doc = json.loads(z.read("obzavod.json"))
        for name in ("course.kmz", "run.fit"):
            if name in z.namelist():
                with open(os.path.join(dest, name), "wb") as f:
                    f.write(z.read(name))
    res = (doc.get("mine") or {}).get("result") or {}
    cum, start = res.get("splits"), res.get("start_local")
    official = (dict(start_utc=start_utc(doc["event"]["date"], start).isoformat(), cumulative=cum)
                if cum and start and cum[-1] is not None else None)
    fit = os.path.join(dest, "run.fit")
    return dict(name=os.path.relpath(path, HERE).replace("\\", "/"), kmz=os.path.join(dest, "course.kmz"),
                fit=fit if os.path.exists(fit) else None, official=official,
                oris=len(cum) - 1 if cum else codes(json.dumps(doc["class"].get("control_codes") or [])))


def races(con, folders):
    """[dict(name, kmz, fit, official, oris)]"""
    out = []
    given = bool(folders)
    if not given:
        folders = sorted(glob.glob(os.path.join(HERE, "data", "*", ""))
                         + glob.glob(os.path.join(HERE, "data-extra", "*", ""))
                         + glob.glob(os.path.join(HERE, "data-extra", "dodano", "*", "")))
    for d in folders:
        for z in sorted(glob.glob(os.path.join(d, "*.obzavod"))):
            out.append(from_obzavod(z))
        kmz = os.path.join(d, "course.kmz")
        if not os.path.exists(kmz):
            continue
        r = dict(name=os.path.relpath(d, HERE).replace("\\", "/").rstrip("/"), kmz=kmz, fit=None, official=None,
                 oris=None)
        if os.path.exists(os.path.join(d, "run.fit")):
            r["fit"] = os.path.join(d, "run.fit")
        if os.path.exists(os.path.join(d, "official.json")):
            with open(os.path.join(d, "official.json"), encoding="utf-8") as f:
                r["official"] = json.load(f)
            r["oris"] = len(r["official"]["cumulative"]) - 1
        if os.path.exists(os.path.join(d, "race.json")):
            with open(os.path.join(d, "race.json"), encoding="utf-8") as f:
                meta = json.load(f)
            r["oris"] = r["oris"] or oris_count(con, class_name=meta.get("class"), oris_id=meta.get("oris_id"))
        out.append(r)
    if given:
        return out
    extra = os.path.join(HERE, "data-extra")
    pairing = {}
    if os.path.exists(os.path.join(extra, "parovani.json")):
        with open(os.path.join(extra, "parovani.json"), encoding="utf-8") as f:
            pairing = json.load(f)
    for kmz in sorted(glob.glob(os.path.join(extra, "*, *.kmz"))):
        stem = os.path.basename(kmz)[:-4]
        event, cls = stem.rsplit(", ", 1)
        fit = (pairing.get(stem) or {}).get("fit")
        out.append(dict(name="data-extra/" + stem, kmz=kmz, fit=fit and os.path.join(HERE, fit), official=None,
                        oris=oris_count(con, event, cls)))
    if con is not None:
        base = os.path.dirname(app_db() or "")
        for name, cls, n, path in con.execute(
                "SELECT e.name, c.name, c.control_codes, c.course_file FROM classes c JOIN events e ON e.id = c.event_id "
                "WHERE c.course_file IS NOT NULL"):
            p = os.path.join(base, path.replace("\\", "/"))
            if os.path.exists(p):
                out.append(dict(name=f"app: {name}, {cls}", kmz=p, fit=None, official=None, oris=codes(n)))
    return out


def crop(gm, det, added, hint, note, path, half=110):
    from PIL import Image, ImageDraw
    im = Image.fromarray(np.asarray(gm.image)).convert("RGB")
    d = ImageDraw.Draw(im)
    for c in det["controls"]:
        d.ellipse([c[0] - c[2], c[1] - c[2], c[0] + c[2], c[1] + c[2]], outline=(0, 160, 0), width=2)
    for c in added:
        d.ellipse([c[0] - c[2], c[1] - c[2], c[0] + c[2], c[1] + c[2]], outline=(255, 120, 0), width=3)
    if note.get("px") and not note.get("found"):
        x, y = note["px"]
        r = float(np.median([c[2] for c in det["controls"]]))
        d.ellipse([x - r, y - r, x + r, y + r], outline=(200, 0, 0), width=1)
    u, v = hint
    d.line([u - 8, v, u + 8, v], fill=(0, 0, 255), width=2)
    d.line([u, v - 8, u, v + 8], fill=(0, 0, 255), width=2)
    box = (int(u - half), int(v - half), int(u + half), int(v + half))
    im.crop(box).resize((3 * 2 * half, 3 * 2 * half), Image.NEAREST).save(path)


def one(r, rozbor, out):
    gm = GeoMap.from_kmz(r["kmz"])
    tr = load_track(r["fit"]) if r["fit"] and os.path.exists(r["fit"]) else None
    hint0 = None
    if tr is not None:
        u0, v0 = gm.latlon_to_px(tr["lat"][:1], tr["lon"][:1])
        hint0 = (float(u0[0]), float(v0[0]))
    det = C.detect_course(gm, start_hint_px=hint0)
    mpp = (gm.m_per_px_x + gm.m_per_px_y) / 2
    fin = det["finish"]
    circles = [c for c in det["controls"]
               if fin is None or np.hypot(c[0] - fin[0], c[1] - fin[1]) * mpp >= FINISH_M]
    res = dict(name=r["name"], oris=r["oris"], found=len(circles), added=0, removed=0, notes=[], finish=fin is not None,
               start=det["start"] is not None)
    if tr is None or r["official"] is None or r["oris"] is None or not circles:
        return res
    places = punch_places(tr, r["official"])
    hints = []
    for p in places:
        if p is None:
            hints.append(None)
        else:
            u, v = gm.latlon_to_px(np.array([p[0]]), np.array([p[1]]))
            hints.append((float(u[0]), float(v[0])))
    added, notes = C.find_missing(det["mask"], mpp, det["start"], circles, fin, hints, r["oris"])
    removed = C.drop_extra(circles, hints, r["oris"], mpp)
    res.update(added=len(added), removed=len(removed), notes=notes, hints=len([h for h in hints if h is not None]),
               removed_px=[[round(c[0]), round(c[1])] for c in removed])
    if rozbor:
        # every control with no circle read near its punch, before find_missing, with or without a circle added
        r_px = float(np.median([c[2] for c in circles]))
        near = r_px + 40.0 / mpp
        missing = [k for k, h in enumerate(hints)
                   if h is not None and not any(np.hypot(h[0] - c[0], h[1] - c[1]) <= near for c in circles)]
        res["missing"] = [k + 1 for k in missing]
        folder = os.path.join(out, r["name"].replace("/", "_").replace(":", "").replace(" ", "_"))
        os.makedirs(folder, exist_ok=True)
        by_k = {n["k"]: n for n in notes}
        for k in missing:
            crop(gm, det | {"controls": circles}, added, hints[k], by_k.get(k + 1, {}),
                 os.path.join(folder, f"{k + 1}.png"))
    return res


def main():
    ap = argparse.ArgumentParser(description="Kolečka kontrol proti ORIS")
    ap.add_argument("folders", nargs="*")
    ap.add_argument("--rozbor", action="store_true", help="u chybějících kontrol změřit kolečko a uložit výřez")
    ap.add_argument("--out", default=os.path.join(HERE, "kontrola", "kitl-kolecka"))
    ap.add_argument("--db", default=app_db())
    ap.add_argument("--json", help="zapsat výsledky i do tohoto souboru")
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True) if a.db and os.path.exists(a.db) else None
    rows = []
    print(f"{'závod':70s} {'ORIS':>4s} {'mapa':>4s} {'+':>3s} {'-':>3s}  rozdíl")
    for r in races(con, [os.path.abspath(f) + os.sep for f in a.folders]):
        try:
            res = one(r, a.rozbor, a.out)
        except Exception as e:  # noqa: BLE001 - one bad map must not stop the list
            print(f"{r['name'][:70]:70s} chyba: {e}")
            continue
        rows.append(res)
        diff = "" if res["oris"] is None else res["found"] + res["added"] - res["removed"] - res["oris"]
        flag = "" if diff in ("", 0) else "  <-- nesedí"
        print(f"{res['name'][:70]:70s} {res['oris'] if res['oris'] is not None else '?':>4} {res['found']:>4} "
              f"{res['added']:>3} {res['removed']:>3}  {diff}{flag}")
        for n in res["notes"]:
            if "cover" in n:
                print(f"{'':10s}kontrola {n['k']:>2}: {'PŘIDÁNA' if n['found'] else 'nepřidána'}, obvod "
                      f"{100 * n['cover']:.0f} %, největší mezera {n['gap']}°, spojnice {n['line']:.2f}, "
                      f"{n['off_m']} m od hodinek")
            else:
                print(f"{'':10s}kontrola {n['k']:>2}: v okolí žádné kolečko")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
