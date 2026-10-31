"""Run the analysis of one entry with the scripts in the repo root, as run_race.py does: analyze.py (splits,
mistake signals) and, when the map without course is there, bestroute.py (best routes). The pictures the
scripts draw for a reader of their reports are left out (--no-images): the pages draw from the JSON."""
import collections
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager

from oroute import errors, osm
from oroute import personal as fitter
from oroute.kmzmap import GeoMap

from .. import oris, texts
from ..config import ROOT
from ..db import loads
from . import barriers, jobs, storage

TIMEOUT = 45 * 60
ALTERNATIVES = 2  # besides the best route: up to three different routes per leg on the page


class AnalysisError(Exception):
    """The first line says in Czech what went wrong (and what to do about it); what the script printed
    follows after an empty line, for the "Podrobnosti" of the job."""


STOP_LOOK_S = 1.0   # how often a running script looks whether the runner asked to stop its job


def _run(*cmd, on_line=None):
    """Run a script of the repo root. on_line gets every line it prints, as it prints it (python -u).
    Raises jobs.Stopped (the script killed) when the runner asks to stop the job meanwhile."""
    p = subprocess.Popen([sys.executable, "-u", *cmd], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    late, halt, done = threading.Event(), threading.Event(), threading.Event()

    def stop():
        late.set()
        p.kill()

    def look():
        while not done.wait(STOP_LOOK_S):
            if jobs.stop_wanted():
                halt.set()
                p.kill()
                return
    timer = threading.Timer(TIMEOUT, stop)
    timer.start()
    watcher = threading.Thread(target=look, daemon=True)
    watcher.start()
    tail = collections.deque(maxlen=12)
    try:
        for line in p.stdout:
            tail.append(line.rstrip())
            if on_line:
                on_line(tail[-1])
        p.wait()
    finally:
        timer.cancel()
        done.set()
        if p.poll() is None:  # on_line failed: do not leave the script running on its own
            p.kill()
            p.wait()
        p.stdout.close()
    name = cmd[1] if cmd[0] == "-m" else cmd[0]
    if halt.is_set():
        raise jobs.Stopped()
    if late.is_set():
        raise AnalysisError(f"Výpočet ({name}) neskončil do {TIMEOUT // 60} minut.")
    if p.returncode != 0:
        # an input the script could not analyse says so itself (oroute.errors); anything else is a bug
        known = errors.parse(tail)
        first = texts.analysis_error(*known) if known else f"Výpočet selhal ({name}); podrobnosti jsou níže."
        raise AnalysisError(first + "\n\n" + "\n".join(tail))


_LEG_DONE = re.compile(r"^(S|\d+)-(\d+|F): actual ")


def _stages(say, n_legs, from_grid=False):
    """What bestroute.py prints, as Czech notes on how far it is (for jobs.progress).
    from_grid: say nothing until the routes are being found (the map was already read once in this job)."""
    done = 0

    def on_line(line):
        nonlocal done
        if line.startswith("reading terrain") and not from_grid:
            say("čtu terén z mapy")
        elif line.startswith("elevation ...") and not from_grid:
            say("načítám výškopis")
        elif line.startswith("building grid"):
            say("připravuji hledání postupů")
        elif _LEG_DONE.match(line):
            done += 1
            say(f"hledám nejlepší postupy: {done} z {n_legs} úseků")
    return on_line


def entry_info(con, entry_id):
    return con.execute(
        "SELECT e.*, c.name AS class_name, c.course_file, c.course_source, c.id AS cid, ev.id AS event_id,"
        " ev.name AS event_name,"
        " ev.date, ev.oris_id AS event_oris_id, ev.maponly_file, a.file AS fit_file,"
        # the runner's own setting of the race, else what the race has
        " COALESCE(e.own_osm_mode, ev.osm_mode) AS osm_mode, COALESCE(e.own_hatch_mode, ev.hatch_mode) AS hatch_mode,"
        " u.slope_file"
        " FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
        " JOIN users u ON u.id = e.user_id LEFT JOIN activities a ON a.id = e.activity_id WHERE e.id = ?",
        (entry_id,)).fetchone()


def official_times(info):
    """The dict oroute/official.py takes, when ORIS gave a start time and split times; else None."""
    cum = loads(info["splits"])
    if not cum or not info["start_local"] or cum[-1] is None:
        return None
    return dict(start_utc=oris.start_utc(info["date"], info["start_local"]).isoformat(), cumulative=cum)


def current_model(con, user_id):
    return con.execute("SELECT * FROM speed_models WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()


def fetch_osm(conf, event_id, maponly):
    """Railways, motorways and fences around the map from OpenStreetMap, once per event (kept in the instance
    folder). Returns a Czech note when it could not be done, else None."""
    if not conf.osm or barriers.osm_data(conf, event_id) is not None:
        return None
    gm = GeoMap.from_kmz(maponly)
    la, lo = gm.px_to_latlon([0, gm.W, 0, gm.W], [0, 0, gm.H, gm.H])
    try:
        data = (conf.osm_fetch or osm.for_box)(float(min(la)), float(min(lo)), float(max(la)), float(max(lo)))
    except OSError as e:
        print(f"event {event_id}: {e}", flush=True)             # the code of the error is for the log only
        return "OpenStreetMap teď neodpovídá (přetížený server). Zakázané přechody se doplní při příštím přepočtu."
    barriers.save_osm(conf, event_id, data)
    return None


def read_hatching(conf, class_id, course):
    """Out-of-bounds areas from the purple hatching of the class's map with the course (oroute/hatch.py), read
    once per uploaded map. Returns (areas, Czech note when it could not be done or None)."""
    if barriers.hatch_data(conf, class_id, course) is None:
        tmp = barriers.hatch_path(conf, class_id) + ".tmp"
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        try:
            _run("-m", "oroute.hatch", course, tmp)
            with open(tmp, encoding="utf-8") as f:
                areas = json.load(f)["areas"]
        except (AnalysisError, OSError, ValueError, KeyError):
            return [], "Šrafování zakázaných prostorů se z mapy s tratí nepodařilo přečíst; postupy s ním nepočítají."
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        barriers.save_hatch(conf, class_id, course, areas, dt.date.today().isoformat())
    return barriers.hatch_data(conf, class_id, course)["areas"], None


def _terrain_cache(conf, event_id):
    """The terrain read from the map without course is the same for everyone at the event: kept next to the
    elevation, so it is read once per uploaded map (the scripts read it again when the map changes)."""
    return conf.path("terrain", f"event_{event_id}.npz")


def run_planned(conf, info, out, plans, result):
    """Price planned routes (oroute/planned.py) with what the analysis in folder `out` used.
    info: entry_info of the entry; plans, result: the JSON files the script reads and writes."""
    crossings = os.path.join(out, "best", "barriers.json")     # what the routes of this analysis kept out of
    _run("-m", "oroute.planned", conf.path(info["maponly_file"]), out, plans, result, "--dem", conf.dem,
         "--terrain-cache", _terrain_cache(conf, info["event_id"]),
         *(["--barriers", crossings] if os.path.exists(crossings) else []))


def _share(src, dst):
    if os.path.exists(src) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, f"{dst}.{os.getpid()}.tmp")
        os.replace(f"{dst}.{os.getpid()}.tmp", dst)


WORK, OLD = ".new", ".old"   # the folder of an analysis being written, and the one it replaces


@contextmanager
def _staged(conf, rel, keep):
    """The folder to write an analysis into (relative to the instance). keep=True (the entry has finished best
    routes that must stay valid until the new ones are whole): a copy next to it (entry_N.new), put in its place
    only when everything in it is done; when the run fails or is stopped the copy goes and the old folder stays.
    keep=False: the folder itself (a new entry: what analyze.py writes is whole, shown at once); when the run
    fails or is stopped, only its best/ goes (a route half found)."""
    final, work, old = conf.path(rel), conf.path(rel + WORK), conf.path(rel + OLD)
    if not os.path.isdir(final) and os.path.isdir(old):    # a swap cut short between its two renames
        os.replace(old, final)
    keep = keep and os.path.isdir(final)
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(old, ignore_errors=True)
    if not keep:
        os.makedirs(final, exist_ok=True)
        try:
            yield rel
        except BaseException:
            shutil.rmtree(os.path.join(final, "best"), ignore_errors=True)
            raise
        return
    shutil.copytree(final, work)
    try:
        yield rel + WORK
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    os.replace(final, old)
    os.replace(work, final)
    shutil.rmtree(old, ignore_errors=True)


def _has_routes(con, entry_id):
    return con.execute("SELECT 1 FROM analyses WHERE entry_id = ? AND has_routes = 1", (entry_id,)).fetchone() is not None


def _write_json(path, data):
    """Whole or not at all: a stopped job must not leave half a file."""
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


# the code that reads what the samples of a race are made of: the terrain of the map and the track of the run
SAMPLE_CODE = ("oroute/terrain.py", "oroute/mapdata.py", "oroute/fitload.py", "oroute/official.py")


def samples_key(conf, info, out):
    """What the samples in folder `out` are read from: their version (oroute.personal.SAMPLES), the code reading the
    terrain and the track, the map without course and the run, the course and the official times. Another key: the
    samples have to be read again (best/samples.json keeps the key they were read with)."""
    h = hashlib.sha1(f"samples {fitter.SAMPLES}".encode())
    for name in SAMPLE_CODE:
        with open(os.path.join(ROOT, name), "rb") as f:
            h.update(f.read())
    for path in (conf.path(info["maponly_file"]), conf.path(info["fit_file"])):
        st = os.stat(path)
        h.update(f"{os.path.basename(path)}/{st.st_size}/{st.st_mtime_ns}".encode())
    for name in ("course.json", "official.json"):
        path = os.path.join(out, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                h.update(name.encode() + f.read())
    return h.hexdigest()


def samples_fresh(conf, info, out):
    """True when best/leg_samples.npz of folder `out` was read with what the entry has now."""
    try:
        with open(os.path.join(out, "best", "samples.json"), encoding="utf-8") as f:
            stamp = json.load(f)
    except (OSError, ValueError):
        return False
    return os.path.exists(os.path.join(out, "best", "leg_samples.npz")) and stamp.get("key") == samples_key(conf, info, out)


def _stamp_samples(conf, info, out):
    _write_json(os.path.join(out, "best", "samples.json"), dict(key=samples_key(conf, info, out)))


def _official(info, out):
    """official.json in the folder when ORIS gave the times; the arguments of the scripts for it."""
    official = official_times(info)
    if not official:
        return []
    _write_json(os.path.join(out, "official.json"), official)
    return ["--official", os.path.join(out, "official.json")]


def _routing_inputs(con, conf, info, out, extra, notes):
    """Everything bestroute.py needs next to the course and the track (elevation, forbidden crossings and areas).
    Returns (the command of bestroute.py, number of legs, {file in best/: shared file of the event})."""
    best = os.path.join(out, "best")
    os.makedirs(best, exist_ok=True)
    course = conf.path(info["course_file"])
    # elevation is the same for everyone at the event: download once (AWS tiles and ČÚZK DMR 5G each have a file)
    shared = {"dem_cache.npz": conf.path("dem", f"event_{info['event_id']}.npz"),
              "dem_cuzk.npz": conf.path("dem", f"event_{info['event_id']}_cuzk.npz")}
    for name, path in shared.items():
        _share(path, os.path.join(best, name))
    # crossings that are not allowed: OpenStreetMap (once per event) and the lines drawn by hand
    if info["osm_mode"] != "off":
        note = fetch_osm(conf, info["event_id"], conf.path(info["maponly_file"]))
        if note:
            notes.append(note)
    # areas that must not be entered: the purple hatching of the runner's own map with the course
    areas = []
    # not from a photo: its purple hatching cannot be told from shadows and the drawing as reliably
    # (a screenshot of Livelox has the exact purple too; a photo does not)
    if info["hatch_mode"] != "off" and info["course_source"] in (None, "kmz", "image", "screen"):
        areas, note = read_hatching(conf, info["cid"], course)
        if note:
            notes.append(note)
    # lines the runner drew where the GPS failed ("Opravit moji stopu"): they stand for the track of their legs
    fixed = {r["leg_n"]: json.loads(r["corrected"]) for r in con.execute(
        "SELECT leg_n, corrected FROM leg_notes WHERE entry_id = ? AND corrected IS NOT NULL", (info["id"],))}
    if fixed:
        _write_json(os.path.join(best, "corrections.json"), fixed)
        extra = [*extra, "--corrections", os.path.join(best, "corrections.json")]
    elif os.path.exists(os.path.join(best, "corrections.json")):
        os.remove(os.path.join(best, "corrections.json"))
    b = barriers.for_routing(con, conf, info["event_id"], info["osm_mode"], areas)
    if b:
        _write_json(os.path.join(best, "barriers.json"), b)
        extra = [*extra, "--barriers", os.path.join(best, "barriers.json")]
    elif os.path.exists(os.path.join(best, "barriers.json")):
        os.remove(os.path.join(best, "barriers.json"))   # of an earlier analysis: the folder says what was used
    slope = ["--slope", conf.path(info["slope_file"])] if info["slope_file"] else []
    script = ["bestroute.py", conf.path(info["maponly_file"]), os.path.join(out, "course.json"),
              conf.path(info["fit_file"]), best,
              "--title", f"{info['event_name']} ({info['class_name']})", *slope, *extra, "--dem", conf.dem,
              "--no-images", "--terrain-cache", _terrain_cache(conf, info["event_id"])]
    with open(os.path.join(out, "course.json"), encoding="utf-8") as f:
        n_legs = len(json.load(f)["controls"]) + 1
    return script, n_legs, shared


def analyse_entry(con, conf, entry_id, routes_only=False, progress=None, after_course=None, before_routes=None,
                  model=None):
    """Returns (output folder relative to the instance, True if best routes were computed, model id used,
    Czech notes for the job list).

    progress(text): what is being done right now, in Czech.
    after_course(folder): called when analyze.py has written the track, the splits and the kinds of mistakes
      (analysis.json), minutes before the best routes are found.
    before_routes(folder): called when the folder holds what the personal speed model learns from this race
      (best/leg_samples.npz), before any route is found. The caller refits the model there, so the routes are
      found once, with the model that already knows this race. Without it the model is used as it is.
    model: the row of speed_models to find the routes with (default: the user's latest). The model is never
      fitted here: only before_routes may do that.
    """
    say = progress or (lambda text: None)
    info = entry_info(con, entry_id)
    if info is None or not info["fit_file"] or not info["course_file"]:
        raise AnalysisError("K závodu chybí aktivita (.fit) nebo mapa s tratí.")
    rel = os.path.join("races", f"entry_{entry_id}")
    # the analysis shown until now stays valid until the new one is whole (a stopped or failed run leaves it)
    with _staged(conf, rel, _has_routes(con, entry_id)) as work:
        has_routes, model_id, notes = _analyse_in(con, conf, info, work, routes_only, say, after_course,
                                                  before_routes, model)
    return rel, has_routes, model_id, notes


def _analyse_in(con, conf, info, rel, routes_only, say, after_course, before_routes, model):
    """analyse_entry in folder rel: (has routes, model id, notes)."""
    out, best = conf.path(rel), conf.path(rel, "best")
    fit, course = conf.path(info["fit_file"]), conf.path(info["course_file"])
    os.makedirs(out, exist_ok=True)

    extra = _official(info, out)
    if not (routes_only and os.path.exists(os.path.join(out, "course.json"))):
        say("čtu trať z mapy a stopu z hodinek")
        # a photo of the map: the course comes from its placing (the controls matched to the circles), not
        # from the purple of the photo, which is not the Livelox purple analyze.py reads
        given = []
        if os.path.exists(conf.path(storage.course_json(info["course_file"]))):
            shutil.copyfile(conf.path(storage.course_json(info["course_file"])), os.path.join(out, "course.json"))
            given = ["--course", os.path.join(out, "course.json")]
        _run("analyze.py", course, fit, out, "--no-images", *given, *extra)
        if after_course:
            after_course(rel)
    if not info["maponly_file"]:
        shutil.rmtree(best, ignore_errors=True)
        return False, None, []

    notes = []
    script, n_legs, shared = _routing_inputs(con, conf, info, out, extra, notes)
    if before_routes:
        _run(*script, "--samples-only", on_line=_stages(say, n_legs))
        _stamp_samples(conf, info, out)
        say("přepočítávám osobní model")
        before_routes(rel)
    if model is None:
        model = current_model(con, info["user_id"])
    # the route of an average runner next to the runner's own: the slope is compared only when it was measured
    # on the runner (their Garmin export), otherwise it is the default prior for both (oroute/generic.py)
    _run(*script, "--model", conf.path(model["file"]) if model else "race", "--alternatives", str(ALTERNATIVES),
         "--generic", "all" if info["slope_file"] else "terrain",
         on_line=_stages(say, n_legs, from_grid=bool(before_routes)))
    _stamp_samples(conf, info, out)
    for name, path in shared.items():
        _share(os.path.join(best, name), path)
    # what is around every control to catch when contact with the map is lost, and where the track shows it
    # was (oroute/relocate.py). The routes are there already: without this the page only lacks that part.
    say("hledám záchytné body u kontrol")
    try:
        run_relocate(conf, info, out)
    except (AnalysisError, OSError):
        notes.append("Záchytné body u kontrol se nepodařilo spočítat.")
    return True, model["id"] if model else None, notes


def sample_entry(con, conf, entry_id, progress=None):
    """Step 1 of "Přepočítat všechno": the samples the personal model learns from (best/leg_samples.npz) of an
    analysed entry, read again only when samples_key has changed (another map, run, course, official times, or
    code that reads the terrain or the track). No route is found. Returns True when they were read again."""
    info = entry_info(con, entry_id)
    a = con.execute("SELECT out_dir FROM analyses WHERE entry_id = ? AND has_routes = 1", (entry_id,)).fetchone()
    if info is None or a is None or not info["maponly_file"] or not info["fit_file"]:
        return False
    _official(info, conf.path(a["out_dir"]))     # the official times ORIS gives now (whole file or none)
    if samples_fresh(conf, info, conf.path(a["out_dir"])):
        return False
    with _staged(conf, a["out_dir"], True) as work:       # the routes of the entry stay valid if it is stopped
        out = conf.path(work)
        extra = _official(info, out)
        script, n_legs, _ = _routing_inputs(con, conf, info, out, extra, [])
        _run(*script, "--samples-only", on_line=_stages(progress or (lambda text: None), n_legs))
        _stamp_samples(conf, info, out)
    return True


def run_relocate(conf, info, out):
    """Find the catching features around the controls (oroute/relocate.py) with what the analysis in folder
    `out` used: its routes, model, elevation and forbidden crossings. Leaves best/relocate.json, or none at
    all when it fails."""
    best = os.path.join(out, "best")
    found, crossings = os.path.join(best, "relocate.json"), os.path.join(best, "barriers.json")
    try:
        _run("-m", "oroute.relocate", conf.path(info["maponly_file"]), out, found + ".tmp", "--dem", conf.dem,
             "--terrain-cache", _terrain_cache(conf, info["event_id"]),
             *(["--barriers", crossings] if os.path.exists(crossings) else []))
        os.replace(found + ".tmp", found)
    except (AnalysisError, OSError):
        for path in (found, found + ".tmp"):
            if os.path.exists(path):
                os.remove(path)
        raise


def relocate_entry(con, conf, entry_id):
    """The catching features of an analysed entry again, without finding its routes again (after a newer
    version of oroute/relocate.py). Raises AnalysisError when the entry has no best routes."""
    info = entry_info(con, entry_id)
    a = con.execute("SELECT out_dir FROM analyses WHERE entry_id = ? AND has_routes = 1", (entry_id,)).fetchone()
    if info is None or a is None or not info["maponly_file"]:
        raise AnalysisError("Závod nemá nejlepší postupy; záchytné body se počítají s nimi.")
    run_relocate(conf, info, conf.path(a["out_dir"]))


def lost_dir(conf, entry_id):
    """Where the scenes of "Ztratil jsem se" of an entry are kept (oroute/lost.py): next to the analysis, not in
    its folder, which a new analysis replaces whole."""
    return conf.path("lost", f"entry_{entry_id}")


def lost_stamp(con, conf, info):
    """What the scenes of an entry are made from: the version of oroute/lost.py, the two maps and the analysis.
    Another stamp: the scenes have to be prepared again (the map placed again by hand, a new analysis)."""
    def st(rel):
        if not rel or not os.path.exists(conf.path(rel)):
            return None
        s = os.stat(conf.path(rel))
        return [s.st_size, s.st_mtime_ns]
    a = con.execute("SELECT finished_at FROM analyses WHERE entry_id = ?", (info["id"],)).fetchone()
    from oroute import lost
    return dict(v=lost.VERSION, maponly=st(info["maponly_file"]), course=st(info["course_file"]),
                analysis=a["finished_at"] if a else None)


def lost_fresh(con, conf, info):
    """True when the scenes of the entry were prepared from what it has now."""
    try:
        with open(os.path.join(lost_dir(conf, info["id"]), "lost.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return False
    return os.path.exists(os.path.join(lost_dir(conf, info["id"]), "lost.npz")) and \
        meta.get("stamp") == lost_stamp(con, conf, info)


def run_lost(con, conf, entry_id):
    """Prepare the scenes of "Ztratil jsem se" (oroute/lost.py) for an entry: with its analysis when there is one
    (the controls in the order of the official times, the forbidden crossings, the attack points, the model), else
    from the two maps alone (a race not run yet: training in the terrain). Raises AnalysisError."""
    info = entry_info(con, entry_id)
    if info is None or not info["maponly_file"] or not info["course_file"]:
        raise AnalysisError("Nápověda „Ztratil jsem se“ potřebuje mapu bez tratě i mapu s tratí.")
    out = lost_dir(conf, entry_id)
    os.makedirs(out, exist_ok=True)
    args = [conf.path(info["maponly_file"]), out, "--dem", conf.dem,
            "--terrain-cache", _terrain_cache(conf, info["event_id"]),
            "--stamp", json.dumps(lost_stamp(con, conf, info))]
    a = con.execute("SELECT out_dir FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
    if a and os.path.exists(conf.path(a["out_dir"], "analysis.json")):
        args += ["--analysis", conf.path(a["out_dir"])]
    else:
        placed = conf.path(storage.course_json(info["course_file"]))
        args += ["--course", placed if os.path.exists(placed) else conf.path(info["course_file"])]
        model = current_model(con, info["user_id"])
        if model and os.path.exists(conf.path(model["file"])):
            args += ["--model", conf.path(model["file"])]
        # the elevation is shared by the event (as for the analyses)
        for name, path in (("dem_cache.npz", conf.path("dem", f"event_{info['event_id']}.npz")),
                           ("dem_cuzk.npz", conf.path("dem", f"event_{info['event_id']}_cuzk.npz"))):
            _share(path, os.path.join(out, name))
    _run("-m", "oroute.lost", *args)
