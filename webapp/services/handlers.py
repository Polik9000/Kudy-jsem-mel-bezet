"""What the worker does for each kind of job. The returned text is shown in the job list (Czech)."""
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import zipfile

from oroute import garmin

from .. import oris
from ..config import ROOT
from . import jobs, matching, personal, plans, results, runner, storage, sync_oris


@jobs.handler("sync_oris")
def _sync_oris(ctx, job):
    return sync_oris.sync_user(ctx.con, ctx.conf, job["user_id"])


@jobs.handler("import_upload")
def _import_upload(ctx, job):
    """A .fit, or a zip of them (a whole Garmin export): store the activities, pair them with the races."""
    p = jobs.payload(job)
    path = ctx.conf.path(p["file"])
    try:
        # a zip with a single run (one activity exported from Garmin Connect) is that run, not an account export:
        # nothing of the earlier exports may be dropped because of it
        one = garmin.single_fit(path) if p["kind"] != "fit" else None
        if p["kind"] == "fit" or one:
            if one:
                name, data = one
            else:
                name = p.get("name")
                with open(path, "rb") as f:
                    data = f.read()
            aid, new = storage.save_activity(ctx.con, ctx.conf, job["user_id"], data, name, "fit")
            if aid is None:
                raise ValueError("Soubor není aktivita Garmin (.fit se záznamem běhu).")
            msg = "Aktivita uložena." if new else "Tahle aktivita už nahraná je."
            # a run from a race ORIS has not been asked about yet (the race was this weekend): load the races
            # first, as the Garmin export does, or the run stays unpaired and the race missing from the list
            if new and not _race_on_day_of(ctx.con, job["user_id"], aid):
                msg += " " + _races_from_oris(ctx, job["user_id"])     # it pairs the runs it can, too
                if ctx.con.execute("SELECT 1 FROM entries WHERE activity_id = ?", (aid,)).fetchone():
                    msg += " Spárováno se závodem."
        else:
            seen = added = 0
            try:
                for name, data in garmin.iter_fit(path):
                    seen += 1
                    added += storage.save_activity(ctx.con, ctx.conf, job["user_id"], data, name, "garmin-export")[1]
            except zipfile.BadZipFile as e:
                raise ValueError("Soubor není zip (export účtu Garmin nebo zip se soubory .fit).") from e
            msg = f"V archivu {seen} souborů .fit, běhů {added}."
            # The runs that are not paired are about to be dropped: first learn every race ORIS knows of the
            # runner (as the button on the race list does), or the run of a race loaded later would be gone.
            before = _paired(ctx.con, job["user_id"])
            msg += " " + _races_from_oris(ctx, job["user_id"])
            matching.match_user(ctx.con, job["user_id"])
            changed = _paired(ctx.con, job["user_id"]) - before
            msg += " " + fit_slope(ctx, job["user_id"], path)
            # privacy: ordinary runs show where the runner lives. Once the hill model is fitted only the runs
            # paired with races stay, and the unpaired ones recorded at a race on its day (the runner decides
            # about those); the rest of the export is dropped (the zip itself goes in `finally`)
            at_race = matching.at_races(ctx.con, job["user_id"])
            paired, spared, dropped = storage.drop_unpaired(ctx.con, ctx.conf, job["user_id"], "garmin-export",
                                                            keep=set(at_race))
            msg += (f" Zůstalo {paired + spared} běhů: {paired} spárovaných se závody a {spared} nespárovaných u závodu"
                    " (v seznamu nahraných aktivit je jde přiřadit nebo smazat)." if spared else
                    f" Zůstalo {paired} běhů spárovaných se závody.")
            msg += f" Smazáno {dropped} ostatních běhů; ty se vrátí jen opětovným nahráním exportu."
            return msg + (f" Nově spárováno: {len(changed)}." if changed else "")
    finally:
        if os.path.exists(path):
            os.remove(path)
    changed = matching.match_user(ctx.con, job["user_id"])
    return msg + (f" Spárováno se závody: {len(changed)}." if changed else "")


def _race_on_day_of(con, user_id, activity_id):
    """Does the runner have a race the app already knows on the (local) day this activity was recorded?"""
    a = con.execute("SELECT start_utc FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if not a or not a["start_utc"]:
        return True  # no time: nothing to look up in ORIS for it
    day = garmin.local(dt.datetime.fromisoformat(a["start_utc"])).date().isoformat()
    return con.execute("SELECT 1 FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                       " WHERE e.user_id = ? AND ev.date = ?", (user_id, day)).fetchone() is not None


def _paired(con, user_id):
    """The entries of the runner that have an activity."""
    return {r[0] for r in con.execute("SELECT id FROM entries WHERE user_id = ? AND activity_id IS NOT NULL", (user_id,))}


def _races_from_oris(ctx, user_id):
    """Load the runner's races from ORIS inside another job. Returns a Czech sentence on how it went; ORIS
    being down must not lose the upload."""
    if not ctx.con.execute("SELECT oris_regno FROM users WHERE id = ?", (user_id,)).fetchone()["oris_regno"]:
        return "Účet nemá registrační číslo, závody z ORIS se nenačítaly."
    try:
        sync_oris.sync_user(ctx.con, ctx.conf, user_id)
    except ValueError as e:                      # the number is not in ORIS
        ctx.con.rollback()
        return f"{e} Závody z ORIS se nenačetly."
    except (oris.OrisError, OSError):
        ctx.con.rollback()
        return ("ORIS teď neodpovídá, párovalo se jen se závody, které aplikace už zná: běh ze závodu, který se "
                "načte až později, nahraj znovu.")
    return "Závody z ORIS načteny."


def fit_slope(ctx, user_id, export):
    """The runner's own uphill/downhill shape from all their runs (oroute.slopefit), as the scripts do it:
    uphill from every run, downhill only from the runs that are orienteering races."""
    con, conf = ctx.con, ctx.conf
    rel = os.path.join("models", f"user_{user_id}", "slope_prior.json")
    os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
    names = [r["original_name"] for r in con.execute(
        "SELECT a.original_name FROM entries e JOIN activities a ON a.id = e.activity_id WHERE e.user_id = ?"
        " AND e.match_confidence IN ('high', 'manual')", (user_id,))]
    cmd = [sys.executable, "-m", "oroute.slopefit", export, conf.path(rel)]
    races_csv = conf.path("models", f"user_{user_id}", "races.csv")
    if len(names) >= 5:
        with open(races_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fit_file"])
            w.writerows([n] for n in names)
        cmd += ["--races", races_csv]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=runner.TIMEOUT)
    except subprocess.TimeoutExpired:
        return "Model kopců se nestihl spočítat."
    if p.returncode != 0 or not os.path.exists(conf.path(rel)):
        return "Na vlastní model kopců je v archivu málo běhů, zůstává výchozí."
    con.execute("UPDATE users SET slope_file = ? WHERE id = ?", (rel, user_id))
    con.commit()
    jobs.enqueue(con, "refit_model", user_id=user_id)
    return "Model kopců spočítán z tvých běhů."


@jobs.handler("analyse")
def _analyse(ctx, job):
    p = jobs.payload(job)
    entry_id = job["entry_id"]
    refitted = []

    def after_course(rel):
        # The track, the splits and the kinds of mistakes are ready minutes before the best routes: show them
        # now. Not when the page already has routes: it would lose them until the new ones are found.
        row = ctx.con.execute("SELECT has_routes FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
        if row is None or not row["has_routes"]:
            results.store(ctx.con, ctx.conf, entry_id, rel, False, None)

    def before_routes(rel):
        # like run_race.py --refit: the race joins the personal model, then its routes are found with that model
        refitted.append(personal.refit(ctx.con, ctx.conf, job["user_id"], fresh=(entry_id, rel))[1])

    rel, has_routes, model_id, notes = runner.analyse_entry(
        ctx.con, ctx.conf, entry_id, routes_only=p.get("routes_only", False),
        progress=lambda text: jobs.progress(ctx.con, job["id"], text), after_course=after_course,
        before_routes=before_routes if p.get("refit", True) else None)
    results.store(ctx.con, ctx.conf, entry_id, rel, has_routes, model_id)
    # the planned routes were priced with the routes and the model of the analysis that is gone now
    try:
        plans.price(ctx.con, ctx.conf, entry_id, again=True)
    except (runner.AnalysisError, OSError, ValueError, KeyError):
        notes.append("Plánované postupy se nepodařilo ocenit.")
    if not has_routes:
        src = ctx.con.execute("SELECT c.course_source FROM entries e JOIN classes c ON c.id = e.class_id"
                              " WHERE e.id = ?", (entry_id,)).fetchone()
        if src and src["course_source"] in ("image", "photo", "manual", "screen"):
            return ("Mezičasy a chyby hotové. Nejlepší postupy z fotky nepočítáme, terén se z ní nedá spolehlivě "
                    "přečíst. Až pořadatel zveřejní mapu na Livelox nebo OB postupech, nahraj KMZ a přepočítá se to.")
        return "Mezičasy a chyby hotové. Na nejlepší postupy chybí mapa bez tratě."
    return ("Analýza hotová" + (", osobní model přepočítán." if any(refitted) else ".")
            + ((" " + " ".join(notes)) if notes else ""))


def _plural(n, one, few, many):
    return one if n == 1 else few if 2 <= n <= 4 else many


@jobs.handler("recompute_all")
def _recompute_all(ctx, job):
    """Every race of the user with one model, in three steps and without going round in circles: the model
    learns only from the tracks and the terrain (the samples), never from the best routes.
    1. the samples of every race, read again only where what they are read from has changed (runner.sample_entry);
    2. the personal model, once, from all of them;
    3. the best routes and the catching features of every race that does not have them with that model yet, one
       race after another. The model does not change in this step (no before_routes, no refit)."""
    con, conf, uid = ctx.con, ctx.conf, job["user_id"]

    def say(text):
        jobs.progress(con, job["id"], text)
    rows = con.execute(
        "SELECT e.id, ev.name, a.model_id, a.summary FROM entries e JOIN classes c ON c.id = e.class_id"
        " JOIN events ev ON ev.id = c.event_id JOIN analyses a ON a.entry_id = e.id"
        " WHERE e.user_id = ? AND a.has_routes = 1 ORDER BY ev.date, e.id", (uid,)).fetchall()
    if not rows:
        return "Zatím není co přepočítat (žádný závod s nejlepšími postupy)."
    n = len(rows)
    resampled = set()
    for i, r in enumerate(rows, 1):
        say(f"vzorky {i} z {n} závodů ({r['name']})")
        if runner.sample_entry(con, conf, r["id"]):
            resampled.add(r["id"])
    say("přepočítávám osobní model")
    model_id, changed = personal.refit(con, conf, uid, tol=personal.KEEP_TOL)
    model = runner.current_model(con, uid)

    def stale(r):
        s = json.loads(r["summary"] or "{}")
        return (r["id"] in resampled or r["model_id"] != model_id or s.get("routes", 1) != results.ROUTES
                or s.get("relocate") != results.RELOCATE)
    todo = [r for r in rows if stale(r)]
    notes = []
    for i, r in enumerate(todo, 1):
        head = f"postupy {i} z {len(todo)} závodů ({r['name']})"
        say(head)
        rel, has_routes, used, more = runner.analyse_entry(
            con, conf, r["id"], routes_only=True, progress=lambda text, head=head: say(f"{head}: {text}"),
            model=model)
        results.store(con, conf, r["id"], rel, has_routes, used)
        try:
            plans.price(con, conf, r["id"], again=True)
        except (runner.AnalysisError, OSError, ValueError, KeyError):
            more.append("Plánované postupy se nepodařilo ocenit.")
        notes += [f"{r['name']}: {m}" for m in more]
    if not todo:
        which = _plural(n, "závod už má", f"všechny {n} závody už mají", f"všech {n} závodů už má")
        return f"Nic nového: {which} postupy spočítané s aktuálním modelem."
    return (f"Přepočítáno {len(todo)} z {n} {_plural(n, 'závodu', 'závodů', 'závodů')} s jedním modelem"
            + (" (model se změnil)." if changed else ".") + ((" " + " ".join(notes)) if notes else ""))


@jobs.handler("relocate")
def _relocate(ctx, job):
    """The catching features around the controls again, with a newer version of oroute/relocate.py; the routes
    of the analysis stay as they are."""
    runner.relocate_entry(ctx.con, ctx.conf, job["entry_id"])
    results.store_relocate(ctx.con, ctx.conf, job["entry_id"])
    return "Záchytné a náběhové body u kontrol přepočítány."


@jobs.handler("lost_scene")
def _lost_scene(ctx, job):
    """What is around every control to catch when lost there (oroute/lost.py), for the page "Ztratil jsem se". Not
    part of an analysis and of "Přepočítat všechno": the page asks for it when it finds it missing or stale."""
    jobs.progress(ctx.con, job["id"], "čtu mapu kolem kontrol")
    runner.run_lost(ctx.con, ctx.conf, job["entry_id"])
    return "Nápověda „Ztratil jsem se“ je připravená."


@jobs.handler("price_plans")
def _price_plans(ctx, job):
    """A planned route was drawn or changed: what the speed model says about it (services/plans.py)."""
    n = plans.price(ctx.con, ctx.conf, job["entry_id"])
    return f"Plánované postupy oceněny modelem: {n}." if n else "Žádný plánovaný postup k ocenění."


@jobs.handler("georef_map")
def _georef_map(ctx, job):
    """A picture of the map with the course (scan, photo): place it by the control circles and the runner's
    track at the official punch times (oroute/georef.py), or by the points clicked on it (payload.points, the
    page views/photo.py), then keep it as the KMZ of the class with the course read from the placing."""
    import tempfile

    from PIL import Image

    from oroute import georef
    from oroute.course import save_course

    from .. import texts
    p = jobs.payload(job)
    if p.get("screens") is not None:            # two screenshots of Livelox (services/screens.py)
        from . import screens
        return screens.place(ctx, job, p)
    path = ctx.conf.path(p["file"]) if p.get("file") else None
    by_hand = p.get("points") is not None
    try:
        info = runner.entry_info(ctx.con, job["entry_id"])
        track, start_s, cumulative = photo_track(ctx.conf, info)
        cls = ctx.con.execute("SELECT * FROM classes WHERE id = ?", (info["cid"],)).fetchone()
        before = storage.course_source(ctx.conf, cls)
        if before == "kmz":
            return "Pro tuhle kategorii už je mapa z KMZ, která je přesnější. Fotka se nepoužila."
        if by_hand:
            row = ctx.con.execute("SELECT file FROM photos WHERE entry_id = ?", (job["entry_id"],)).fetchone()
            if row is None or not os.path.exists(ctx.conf.path(row["file"])):
                raise jobs.Refused("Fotka k ručnímu usazení už tu není; nahraj ji znovu.")
            image = georef.open_image(ctx.conf.path(row["file"]))
        else:
            try:
                image = georef.open_image(path)
            except (OSError, ValueError, Image.DecompressionBombError) as e:
                raise jobs.Refused("Soubor se nepodařilo otevřít jako obrázek (jpg nebo png).") from e
            storage.save_photo(ctx.con, ctx.conf, job["entry_id"], image)
        lat0, lon0 = georef.track_frame(track)
        try:
            if by_hand:
                ground = georef.ground_course(track, georef.local_frame(lat0, lon0), start_s, cumulative)
                points = {(k if k in ("S", "C") else int(k) - 1): (float(u), float(v)) for k, u, v in p["points"]}
                gm, fit = georef.place_by_points(image, points, ground, lat0, lon0)
            else:
                gm, fit = georef.georeference(image, track, start_s, cumulative, course=True)
        except georef.GeorefError as e:
            raise jobs.Refused(texts.photo_failed(str(e), georef.photo_quality(image), by_hand)) from e
        if not by_hand and fit["n"] < georef.PHOTO_RETRY * fit["controls"] \
                and georef.photo_quality(image)["sheets"] >= 2:
            # two sheets (a map exchange) and only part of the course placed: the rest would be wrong
            raise jobs.Refused(texts.photo_failed("two sheets", dict(sheets=2)))
        source = "manual" if by_hand else "photo" if fit["photo"] else "image"
        # a screenshot of Livelox is a straight picture with the exact purple: a photo replaces it, even placed by
        # hand, only when it fits the controls better
        if before == "screen" and cls["course_rms"] is not None and fit["rms"] >= cls["course_rms"]:
            return (f"Pro kategorii už je mapa ze snímku Livelox s menší odchylkou ({cls['course_rms']:.0f} m); fotka "
                    f"({fit['rms']:.0f} m) se nepoužila.")
        if not by_hand and before in ("image", "photo", "manual") and cls["course_rms"] is not None \
                and fit["rms"] >= cls["course_rms"]:
            return (f"Pro kategorii už je mapa z fotky s menší odchylkou ({cls['course_rms']:.0f} m); tahle "
                    f"({fit['rms']:.0f} m) se nepoužila. Přepsat ji jde ručním usazením.")
        fd, tmp = tempfile.mkstemp(suffix=".kmz", dir=ctx.conf.path("incoming"))
        os.close(fd)
        georef.write_kmz(tmp, gm.image, gm, name=f"{info['event_name']} ({info['class_name']})")
        rel = storage.save_map(ctx.conf, tmp, info["event_id"], info["cid"])
        if source != "image":      # a photo: its purple is not the Livelox one analyze.py reads
            save_course(ctx.conf.path(storage.course_json(rel)), gm, fit["course"])
        ctx.con.execute("UPDATE classes SET course_file = ?, course_by = ?, course_at = datetime('now'),"
                        " course_source = ?, course_rms = ?, course_n = ?, course_edge_m = ? WHERE id = ?",
                        (rel, job["user_id"], source, round(fit["rms"], 1), fit["n"], round(fit["edge_m"], 1),
                         info["cid"]))
        if by_hand:
            ctx.con.execute("UPDATE photos SET points = ? WHERE entry_id = ?",
                            (json.dumps(p["points"]), job["entry_id"]))
        ctx.con.commit()
        for r in ctx.con.execute("SELECT id FROM entries WHERE class_id = ?", (info["cid"],)).fetchall():
            matching.queue_analysis(ctx.con, r["id"])
        how = (f"podle {fit['n']} bodů, které jsi označil" if by_hand
               else f"podle {fit['n']} z {fit['controls']} kontrol")
        replaced = (" Nahradila předchozí mapu z fotky." if before in ("image", "photo", "manual") else
                    " Nahradila mapu ze snímku Livelox." if before == "screen" else "")
        return (f"Mapa usazena {how}, odchylka {fit['rms']:.0f} m, na okraji mapy asi {fit['edge_m']:.0f} m."
                f"{replaced} Analýza je ve frontě.")
    finally:
        if path and os.path.exists(path):
            os.remove(path)


def photo_track(conf, info):
    """(track, official start in seconds of the track's clock, official cumulative times) for placing a photo,
    or jobs.Refused with what is missing."""
    import datetime as dt

    from oroute.errors import InputError
    from oroute.fitload import load_track

    from .. import texts
    official = runner.official_times(info) if info else None
    if not info or not info["fit_file"] or not official:
        raise jobs.Refused("Fotka mapy se usazuje podle tvé stopy v oficiálních časech ražení: k závodu chybí "
                           "běh z hodinek nebo mezičasy z ORIS. Nahraj nejdřív běh z hodinek (.fit).")
    try:
        track = load_track(conf.path(info["fit_file"]))
    except InputError as e:
        raise jobs.Refused(texts.analysis_error(e.code, e.text)) from e
    rec = track["start"] if track["start"].tzinfo else track["start"].replace(tzinfo=dt.timezone.utc)
    start_s = (dt.datetime.fromisoformat(official["start_utc"]) - rec).total_seconds()
    return track, start_s, official["cumulative"]


@jobs.handler("refit_model")
def _refit_model(ctx, job):
    mid, changed = personal.refit(ctx.con, ctx.conf, job["user_id"])
    if mid is None:
        return "Zatím není z čeho model počítat (žádný závod s nejlepšími postupy)."
    return "Osobní model přepočítán." if changed else "Osobní model se nezměnil."
