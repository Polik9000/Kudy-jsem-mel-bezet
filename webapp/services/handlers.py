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
from ..db import dumps
from ..i18n import _, _n
from . import garmin_api, jobs, matching, personal, plans, results, runner, storage, sync_oris


@jobs.handler("sync_oris")
def _sync_oris(ctx, job):
    message = sync_oris.sync_user(ctx.con, ctx.conf, job["user_id"])
    matching.queue_waiting_photos(ctx.con, job["user_id"])
    matching.queue_waiting_screens(ctx.con, job["user_id"])
    return message


@jobs.handler("import_upload")
def _import_upload(ctx, job):
    """A .fit, or a zip of them (a whole Garmin export): store the activities, pair them with the races."""
    p = jobs.payload(job)
    path = ctx.conf.path(p["file"])
    try:
        # a zip with a single run (one activity exported from Garmin Connect) is that run, not an account export:
        # nothing of the earlier exports may be dropped because of it ("export": runs from Garmin Connect, a zip
        # made by the garmin_api job, is an export even with one run)
        one = garmin.single_fit(path) if p["kind"] == "zip" else None
        if p["kind"] == "fit" or one:
            if one:
                name, data = one
            else:
                name = p.get("name")
                with open(path, "rb") as f:
                    data = f.read()
            aid, new = storage.save_activity(ctx.con, ctx.conf, job["user_id"], data, name, "fit")
            if aid is None:
                raise ValueError(_("Soubor není aktivita Garmin (.fit se záznamem běhu)."))
            msg = _("Aktivita uložena.") if new else _("Tahle aktivita už nahraná je.")
            # a run from a race ORIS has not been asked about yet (the race was this weekend): load the races
            # first, as the Garmin export does, or the run stays unpaired and the race missing from the list
            if new and not _race_on_day_of(ctx.con, job["user_id"], aid):
                msg += " " + _races_from_oris(ctx, job["user_id"])     # it pairs the runs it can, too
                if ctx.con.execute("SELECT 1 FROM entries WHERE activity_id = ?", (aid,)).fetchone():
                    msg += _(" Spárováno se závodem.")
        else:
            seen = added = 0
            try:
                for name, data in garmin.iter_fit(path):
                    seen += 1
                    added += storage.save_activity(ctx.con, ctx.conf, job["user_id"], data, name, "garmin-export")[1]
            except zipfile.BadZipFile as e:
                raise ValueError(_("Soubor není zip (export účtu Garmin nebo zip se soubory .fit).")) from e
            msg = _("V archivu %(seen)s souborů .fit, běhů %(added)s.", seen=seen, added=added)
            # The runs that are not paired are about to be dropped: first learn every race ORIS knows of the
            # runner (as the button on the race list does), or the run of a race loaded later would be gone.
            before = _paired(ctx.con, job["user_id"])
            msg += " " + _races_from_oris(ctx, job["user_id"])
            matching.match_user(ctx.con, job["user_id"])
            matching.queue_waiting_photos(ctx.con, job["user_id"])
            matching.queue_waiting_screens(ctx.con, job["user_id"])
            changed = _paired(ctx.con, job["user_id"]) - before
            msg += " " + fit_slope(ctx, job["user_id"], path)
            # privacy: ordinary runs show where the runner lives. Once the hill model is fitted only the runs
            # paired with races stay, and the unpaired ones recorded at a race on its day (the runner decides
            # about those); the rest of the export is dropped (the zip itself goes in `finally`)
            at_race = matching.at_races(ctx.con, job["user_id"])
            paired, spared, dropped = storage.drop_unpaired(ctx.con, ctx.conf, job["user_id"], "garmin-export",
                                                            keep=set(at_race))
            msg += (_(" Zůstalo %(v)s běhů: %(paired)s spárovaných se závody a %(spared)s nespárovaných u "
                        "závodu (v seznamu nahraných aktivit je jde přiřadit nebo smazat).",
                            v=paired + spared, paired=paired, spared=spared) if spared else
                    _(" Zůstalo %(paired)s běhů spárovaných se závody.", paired=paired))
            msg += _(" Smazáno %(dropped)s ostatních běhů; ty se vrátí jen opětovným nahráním exportu.", dropped=dropped)
            return msg + (_(" Nově spárováno: %(len)s.", len=len(changed)) if changed else "")
    finally:
        if os.path.exists(path):
            os.remove(path)
    changed = matching.match_user(ctx.con, job["user_id"])
    matching.queue_waiting_photos(ctx.con, job["user_id"])
    matching.queue_waiting_screens(ctx.con, job["user_id"])
    return msg + (_(" Spárováno se závody: %(len)s.", len=len(changed)) if changed else "")


@jobs.handler("garmin_api")
def _garmin_api(ctx, job):
    """Runs from the runner's Garmin Connect account (services/garmin_api.py, only the app on one's own computer).
    payload ids: the chosen activities, stored as if uploaded one by one (they stay) and paired with the races.
    payload model_days: every run of that many last days, handled as a whole Garmin export (import_upload):
    races from ORIS, pairing, the own hill model, and then only the runs paired with races (or recorded at one)
    stay. Both can come in one job: the chosen runs are stored first, so the export part does not drop them."""
    p = jobs.payload(job)
    uid = job["user_id"]
    ids = [int(i) for i in p.get("ids", [])]
    days = int(p["model_days"]) if p.get("model_days") else None
    if not ids and not days:
        raise jobs.Refused(_("Nevybraná žádná aktivita."))
    parts = []
    if ids:
        parts.append(_garmin_chosen(ctx, job, uid, ids))
    if days:
        try:
            all_ids = [r["id"] for r in garmin_api.offer(ctx.con, ctx.conf, uid, days) if r["run"]]
        except garmin_api.GarminApiError as e:
            raise jobs.Refused(str(e)) from None
        if not all_ids:
            raise jobs.Refused(_("V Garmin Connect za vybrané období není žádný běh."))
        rel, path, got, note = _garmin_download(ctx, job, uid, all_ids)
        msg = _import_upload(ctx, dict(job, payload=dumps(dict(file=rel, name="Garmin Connect", kind="export"))))
        parts.append(_("Model kopců: staženo z Garmin Connect %(n)s běhů.", n=got) + " " + msg + note)
    return "\n".join(parts)


def _garmin_download(ctx, job, uid, ids):
    """Download the activities into a zip in the incoming folder: (relative path, path, downloaded, note)."""
    rel, path = storage.incoming(ctx.conf, ".zip")
    try:
        got, skipped = garmin_api.download_zip(ctx.conf, uid, ids, path,
                                               progress=lambda t: jobs.progress(ctx.con, job["id"], t))
    except garmin_api.GarminApiError as e:
        if os.path.exists(path):
            os.remove(path)
        raise jobs.Refused(str(e)) from None
    note = _(" Nestaženo %(n)s: %(why)s", n=len(skipped), why=skipped[0][1]) if skipped else ""
    if not got:
        os.remove(path)
        raise jobs.Refused(_("Z Garmin Connect se nestáhla žádná aktivita.") + note)
    return rel, path, got, note


def _garmin_chosen(ctx, job, uid, ids):
    """The chosen activities: stored, the races loaded from ORIS when there is something new, paired."""
    rel, path, got, note = _garmin_download(ctx, job, uid, ids)
    new = 0
    try:
        for name, data in garmin.iter_fit(path):
            aid, added = storage.save_activity(ctx.con, ctx.conf, uid, data, name, "garmin-api")
            new += added
    finally:
        os.remove(path)
    msg = _("Staženo z Garmin Connect %(n)s aktivit, nových %(new)s.", n=got, new=new) + note
    if new:
        msg += " " + _races_from_oris(ctx, uid)
    changed = matching.match_user(ctx.con, uid)
    matching.queue_waiting_photos(ctx.con, uid)
    matching.queue_waiting_screens(ctx.con, uid)
    return msg + (_(" Spárováno se závody: %(len)s.", len=len(changed)) if changed else "")


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
        return _("Účet nemá registrační číslo, závody z ORIS se nenačítaly.")
    try:
        sync_oris.sync_user(ctx.con, ctx.conf, user_id)
    except ValueError as e:                      # the number is not in ORIS
        ctx.con.rollback()
        return _("%(e)s Závody z ORIS se nenačetly.", e=e)
    except (oris.OrisError, OSError):
        ctx.con.rollback()
        return (_("ORIS teď neodpovídá, párovalo se jen se závody, které aplikace už zná: běh ze závodu, který "
                    "se načte až později, nahraj znovu."))
    return _("Závody z ORIS načteny.")


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
        return _("Model kopců se nestihl spočítat.")
    if p.returncode != 0 or not os.path.exists(conf.path(rel)):
        return _("Na vlastní model kopců je v archivu málo běhů, zůstává výchozí.")
    con.execute("UPDATE users SET slope_file = ? WHERE id = ?", (rel, user_id))
    con.commit()
    jobs.enqueue(con, "refit_model", user_id=user_id)
    return _("Model kopců spočítán z tvých běhů.")


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
        notes.append(_("Plánované postupy se nepodařilo ocenit."))
    if not has_routes:
        src = ctx.con.execute("SELECT c.course_source FROM entries e JOIN classes c ON c.id = e.class_id"
                              " WHERE e.id = ?", (entry_id,)).fetchone()
        if src and src["course_source"] in ("image", "photo", "manual", "screen"):
            return (_("Mezičasy a chyby hotové. Nejlepší postupy z fotky nepočítáme, terén se z ní nedá "
                        "spolehlivě přečíst. Až pořadatel zveřejní mapu na Livelox, nahraj KMZ "
                        "a přepočítá se to."))
        return _("Mezičasy a chyby hotové. Na nejlepší postupy chybí mapa bez tratě.")
    return (_("Analýza hotová") + (_(", osobní model přepočítán.") if any(refitted) else ".")
            + ((" " + " ".join(notes)) if notes else ""))


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
        return _("Zatím není co přepočítat (žádný závod s nejlepšími postupy).")
    n = len(rows)
    resampled = set()
    for i, r in enumerate(rows, 1):
        say(_("vzorky %(i)s z %(n)s závodů (%(name)s)", i=i, n=n, name=r['name']))
        if runner.sample_entry(con, conf, r["id"]):
            resampled.add(r["id"])
    say(_("přepočítávám osobní model"))
    model_id, changed = personal.refit(con, conf, uid, tol=personal.KEEP_TOL)
    model = runner.current_model(con, uid)

    def stale(r):
        s = json.loads(r["summary"] or "{}")
        return (r["id"] in resampled or r["model_id"] != model_id or s.get("routes", 1) != results.ROUTES
                or s.get("relocate") != results.RELOCATE)
    todo = [r for r in rows if stale(r)]
    notes = []
    for i, r in enumerate(todo, 1):
        head = _("postupy %(i)s z %(len)s závodů (%(name)s)", i=i, len=len(todo), name=r['name'])
        say(head)
        rel, has_routes, used, more = runner.analyse_entry(
            con, conf, r["id"], routes_only=True, progress=lambda text, head=head: say(f"{head}: {text}"),
            model=model)
        results.store(con, conf, r["id"], rel, has_routes, used)
        try:
            plans.price(con, conf, r["id"], again=True)
        except (runner.AnalysisError, OSError, ValueError, KeyError):
            more.append(_("Plánované postupy se nepodařilo ocenit."))
        notes += [f"{r['name']}: {m}" for m in more]
    if not todo:
        return _n(n, "Nic nového: závod už má postupy spočítané s aktuálním modelem.",
                  "Nic nového: všechny %(n)s závody už mají postupy spočítané s aktuálním modelem.",
                  "Nic nového: všech %(n)s závodů už má postupy spočítané s aktuálním modelem.")
    return (_n(n, "Přepočítáno %(done)s z %(n)s závodu s jedním modelem",
               "Přepočítáno %(done)s z %(n)s závodů s jedním modelem",
               "Přepočítáno %(done)s z %(n)s závodů s jedním modelem", done=len(todo))
            + (_(" (model se změnil).") if changed else ".") + ((" " + " ".join(notes)) if notes else ""))


@jobs.handler("relocate")
def _relocate(ctx, job):
    """The catching features around the controls again, with a newer version of oroute/relocate.py; the routes
    of the analysis stay as they are."""
    runner.relocate_entry(ctx.con, ctx.conf, job["entry_id"])
    results.store_relocate(ctx.con, ctx.conf, job["entry_id"])
    return _("Záchytné a náběhové body u kontrol přepočítány.")


@jobs.handler("lost_scene")
def _lost_scene(ctx, job):
    """What is around every control to catch when lost there (oroute/lost.py), for the page "Ztratil jsem se". Not
    part of an analysis and of "Přepočítat všechno": the page asks for it when it finds it missing or stale."""
    jobs.progress(ctx.con, job["id"], _("čtu mapu kolem kontrol"))
    runner.run_lost(ctx.con, ctx.conf, job["entry_id"])
    return _("Nápověda „Ztratil jsem se“ je připravená.")


@jobs.handler("price_plans")
def _price_plans(ctx, job):
    """A planned route was drawn or changed: what the speed model says about it (services/plans.py)."""
    n = plans.price(ctx.con, ctx.conf, job["entry_id"])
    return _("Plánované postupy oceněny modelem: %(n)s.", n=n) if n else _("Žádný plánovaný postup k ocenění.")


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
    stored_photo = bool(p.get("stored_photo"))
    path = ctx.conf.path(p["file"]) if p.get("file") else None
    by_hand = p.get("points") is not None
    try:
        info = runner.entry_info(ctx.con, job["entry_id"])
        track, start_s, cumulative = photo_track(ctx.conf, info)
        cls = ctx.con.execute("SELECT * FROM classes WHERE id = ?", (info["cid"],)).fetchone()
        before = storage.course_source(ctx.conf, cls)
        if before == "kmz":
            return _("Pro tuhle kategorii už je mapa z KMZ, která je přesnější. Fotka se nepoužila.")
        if by_hand or stored_photo:
            row = ctx.con.execute("SELECT file FROM photos WHERE entry_id = ?", (job["entry_id"],)).fetchone()
            if row is None or not os.path.exists(ctx.conf.path(row["file"])):
                raise jobs.Refused(_("Uložená fotka mapy už tu není; nahraj ji znovu."))
            if stored_photo:
                ctx.con.execute("UPDATE photos SET waiting_for_run = 0 WHERE entry_id = ?", (job["entry_id"],))
                ctx.con.commit()
            image = georef.open_image(ctx.conf.path(row["file"]))
        else:
            try:
                image = georef.open_image(path)
            except (OSError, ValueError, Image.DecompressionBombError) as e:
                raise jobs.Refused(_("Soubor se nepodařilo otevřít jako obrázek (jpg nebo png).")) from e
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
            return (_("Pro kategorii už je mapa ze snímku Livelox s menší odchylkou (%(course_rms).0f m); fotka "
                        "(%(rms).0f m) se nepoužila.", course_rms=cls['course_rms'], rms=fit['rms']))
        if not by_hand and before in ("image", "photo", "manual") and cls["course_rms"] is not None \
                and fit["rms"] >= cls["course_rms"]:
            return (_("Pro kategorii už je mapa z fotky s menší odchylkou (%(course_rms).0f m); tahle "
                        "(%(rms).0f m) se nepoužila. Přepsat ji jde ručním usazením.",
                            course_rms=cls['course_rms'], rms=fit['rms']))
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
        how = (_("podle %(n)s bodů, které jsi označil", n=fit['n']) if by_hand
               else _("podle %(n)s z %(controls)s kontrol", n=fit['n'], controls=fit['controls']))
        replaced = (_(" Nahradila předchozí mapu z fotky.") if before in ("image", "photo", "manual") else
                    _(" Nahradila mapu ze snímku Livelox.") if before == "screen" else "")
        return (_("Mapa usazena %(how)s, odchylka %(rms).0f m, na okraji mapy asi %(edge_m).0f m.%(replaced)s "
                    "Analýza je ve frontě.", how=how, rms=fit['rms'], edge_m=fit['edge_m'], replaced=replaced))
    finally:
        if path and not stored_photo and os.path.exists(path):
            os.remove(path)


def photo_track(conf, info, trim=None):
    """(track, official start in seconds of the track's clock, official cumulative times) for placing a photo,
    or jobs.Refused with what is missing. trim: how the start and end of the track are cut (analyze.py --gps-trim);
    default the runner's setting (runner.gps_trim)."""
    import datetime as dt

    from oroute import gpstrim
    from oroute.errors import InputError
    from oroute.fitload import load_track

    from .. import texts
    official = runner.official_times(info) if info else None
    if not info or not info["fit_file"] or not official:
        raise jobs.Refused(_("Fotka mapy se usazuje podle tvé stopy v oficiálních časech ražení: k závodu chybí "
                               "běh z hodinek nebo mezičasy z ORIS. Nahraj nejdřív běh z hodinek (.fit)."))
    try:
        track = gpstrim.apply(load_track(conf.path(info["fit_file"])), trim or runner.gps_trim(info))
    except InputError as e:
        raise jobs.Refused(texts.analysis_error(e.code, e.text)) from e
    rec = track["start"] if track["start"].tzinfo else track["start"].replace(tzinfo=dt.timezone.utc)
    start_s = (dt.datetime.fromisoformat(official["start_utc"]) - rec).total_seconds()
    return track, start_s, official["cumulative"]


@jobs.handler("refit_model")
def _refit_model(ctx, job):
    mid, changed = personal.refit(ctx.con, ctx.conf, job["user_id"])
    if mid is None:
        return _("Zatím není z čeho model počítat (žádný závod s nejlepšími postupy).")
    return _("Osobní model přepočítán.") if changed else _("Osobní model se nezměnil.")
