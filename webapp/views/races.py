"""Race list, one race (maps, activity, analysis), profile."""
import datetime as dt
import io
import os
import re
import zipfile

from flask import abort, current_app, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for

from oroute import garmin

from .. import cfg, club, get_db, i18n, oris, texts
from ..auth import login_required
from ..db import loads
from ..i18n import N_, _
from ..services import accounts, barriers, jobs, mapfix, matching, oris_class, plans, results, screens, storage, view
from ..services import splits as class_splits
from . import bp, go
from .jobs import analysis_stamp, entry_progress

ENTRY_SQL = (
    "SELECT e.*, c.name AS class_name, c.course_file, c.distance_km, c.climb_m, c.controls, c.event_id,"
    " c.course_source, c.course_rms, c.course_n, c.course_edge_m,"
    " ev.name AS event_name, ev.date, ev.place, ev.oris_id AS event_oris_id, ev.livelox_id, ev.maponly_file,"
    " ev.links, ev.locations, ev.lat AS event_lat, ev.lon AS event_lon, ev.maponly_by,"
    " ev.maponly_source, ev.maponly_res_m, ev.maponly_acc_m,"
    # osm_mode, hatch_mode: what holds for this runner (their own setting, else the one of the race)
    " ev.osm_mode AS event_osm_mode, ev.hatch_mode AS event_hatch_mode,"
    " COALESCE(e.own_osm_mode, ev.osm_mode) AS osm_mode, COALESCE(e.own_hatch_mode, ev.hatch_mode) AS hatch_mode,"
    " (SELECT COALESCE(u.name, u.username) FROM users u WHERE u.id = ev.maponly_by) AS maponly_who,"
    " an.id AS analysis_id, an.has_routes, an.total_time_s, an.model_id, an.finished_at,"
    " act.start_utc AS act_start, act.timer_s AS act_timer, act.dist_m AS act_dist"
    " FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
    " LEFT JOIN analyses an ON an.entry_id = e.id LEFT JOIN activities act ON act.id = e.activity_id")


def get_entry(entry_id):
    """The entry, only for its owner."""
    row = get_db().execute(ENTRY_SQL + " WHERE e.id = ? AND e.user_id = ?", (entry_id, g.user["id"])).fetchone()
    if row is None:
        abort(404)
    return row


def status(e, job):
    """(text, css class, key) of where the analysis of an entry stands. key: hotovo | mapa | aktivita | jine."""
    if job and job["status"] in ("queued", "running"):
        return (_("počítá se") if job["status"] == "running" else _("čeká ve frontě")), "ob-warn", "jine"
    if job and job["status"] == "failed" and not (e["analysis_id"] and e["has_routes"]):
        return _("analýza selhala"), "ob-bad", "jine"
    if job and job["status"] == "stopped" and not (e["analysis_id"] and e["has_routes"]):
        return _("zastaveno"), "", "jine"
    if e["analysis_id"] and e["has_routes"]:
        return _("hotovo"), "ob-ok", "hotovo"
    if not e["activity_id"]:
        return _("chybí aktivita"), "", "aktivita"
    if e["analysis_id"]:
        return _("chybí mapa bez tratě"), "ob-warn", "mapa"
    if not e["course_file"]:
        return _("chybí mapa"), "ob-warn", "mapa"
    return _("připraveno"), "", "jine"


def last_jobs(db, user_id):
    """Latest analysis job per entry."""
    out = {}
    for j in db.execute("SELECT * FROM jobs WHERE user_id = ? AND kind = 'analyse' ORDER BY id", (user_id,)):
        out[j["entry_id"]] = j
    return out


@bp.app_template_filter("mmss")
def _mmss(s):
    return texts.mmss(s)


@bp.app_template_filter("mmss_sign")
def _mmss_sign(s):
    return texts.mmss(s, sign=True)


@bp.app_template_filter("localtime")
def _localtime(iso, fmt="%H:%M"):
    return garmin.local(dt.datetime.fromisoformat(iso)).strftime(fmt) if iso else ""


@bp.app_template_filter("datum")
def _datum(iso):
    """'2026-10-03' -> '3. 10. 2026' (as the club site writes dates), in English '3 Oct 2026'."""
    try:
        d = dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return i18n.date_text(d)


@bp.app_template_filter("kdy")
def _kdy(iso):
    """A time of the database (UTC, '2026-10-07 08:02:11') as local date and time: '7. 10. 2026 10:02'."""
    try:
        d = garmin.local(dt.datetime.fromisoformat(iso))
    except (TypeError, ValueError):
        return iso or ""
    return f"{i18n.date_text(d)} {d:%H:%M}"


def _first_start():
    """True once: the first time the races page opens in the app on one's own computer. A marker file in the
    data folder remembers it, so a runner who skips the number is not asked again at every start."""
    marker = os.path.join(cfg().instance, ".uvod-profil")
    if os.path.exists(marker):
        return False
    try:
        with open(marker, "w", encoding="utf-8") as f:
            f.write("1")
    except OSError:
        return False  # cannot remember it: do not ask at all rather than at every start
    return True


@bp.route("/")
@login_required
def races():
    db = get_db()
    if cfg().local and not g.user["oris_regno"] and _first_start():
        # the app on one's own computer, the very first start: ask for the registration number right away
        flash(_("Vítej! Zadej svoje registrační číslo ORIS, načtou se z něj tvoje závody. Jde to i později, "
                "nebo to přeskoč a přidávej závody ručně."), "ok")
        return redirect(url_for("ob.profile"))
    rows = db.execute(ENTRY_SQL + " WHERE e.user_id = ? ORDER BY ev.date DESC, e.id DESC", (g.user["id"],)).fetchall()
    lj = last_jobs(db, g.user["id"])
    sync = db.execute("SELECT * FROM jobs WHERE user_id = ? AND kind = 'sync_oris' ORDER BY id DESC LIMIT 1",
                      (g.user["id"],)).fetchone()
    seasons = sorted({e["date"][:4] for e in rows}, reverse=True)
    if "sezona" in request.args:
        session["sezona"] = request.args["sezona"]  # the chosen season stays for the next visit
    season = session.get("sezona") if session.get("sezona") in seasons else ""
    only = request.args.get("jen") if request.args.get("jen") in ("hotovo", "mapa", "aktivita", "beh") else ""
    listed = [(e, status(e, lj.get(e["id"]))) for e in rows if not season or e["date"].startswith(season)]
    # beh = races with a run from the watch: the ones there is something to look at or to finish
    counts = dict(total=len(listed), hotovo=0, mapa=0, aktivita=0, jine=0,
                  beh=sum(bool(e["activity_id"]) for e, _st in listed))
    for _e, st in listed:
        counts[st[2]] += 1
    shown = [x for x in listed if not only or (bool(x[0]["activity_id"]) if only == "beh" else x[1][2] == only)]
    # the last analysed race of the runner: a quick way back to it from the list
    analysed = [e for e, _st in listed if e["analysis_id"] and e["finished_at"]]
    last = max(analysed, key=lambda e: e["finished_at"]) if analysed else None
    return render_template("ob/races.html", entries=shown, sync=sync, last=last,
                           conf=texts.confidence(), livelox=oris.livelox_url, oris_url=oris.event_url,
                           seasons=seasons, season=season, only=only, counts=counts)


@bp.route("/zavod/oris-<int:oris_id>")
@login_required
def race_by_oris(oris_id):
    """Stable address for links from the club site (it knows ORIS ids, not our entry ids)."""
    db = get_db()
    row = db.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
                     " WHERE ev.oris_id = ? AND e.user_id = ? ORDER BY e.id LIMIT 1", (oris_id, g.user["id"])).fetchone()
    if row:
        return redirect(url_for("ob.race", entry_id=row["id"]))
    ev = db.execute("SELECT * FROM events WHERE oris_id = ?", (oris_id,)).fetchone()
    return render_template("ob/race_missing.html", oris_id=oris_id, ev=ev, oris_url=oris.event_url(oris_id)), 404


@bp.route("/clen/<int:oris_user_id>")
@login_required
def member(oris_user_id):
    """Stable address for links from a member's card on the club site. Everyone sees only their own races."""
    if g.user["oris_user_id"] == oris_user_id:
        return redirect(url_for("ob.races"))
    return render_template("ob/member_other.html", oris_user_id=oris_user_id), 403


@bp.route("/sync", methods=["POST"])
@login_required
def sync():
    if not g.user["oris_regno"]:
        flash(_("Tenhle účet nemá registrační číslo ORIS, závody z něj načíst nejde. Přidej závod ručně."), "error")
        return redirect(url_for("ob.races"))
    jobs.enqueue(get_db(), "sync_oris", user_id=g.user["id"])
    flash(_("Načítám závody z ORIS, za chvíli se objeví."), "ok")
    return redirect(url_for("ob.races"))


@bp.route("/races/new", methods=["GET", "POST"])
@login_required
def race_new():
    """A race that is not in ORIS (abroad, training)."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        cls = request.form.get("class_name", "").strip() or "-"
        try:
            date = dt.date.fromisoformat(request.form.get("date", ""))
            time_s = texts.parse_time(request.form.get("time"))
        except ValueError:
            date = None
        if not name or date is None:
            flash(_("Vyplň název, datum (RRRR-MM-DD) a čas jako 55:07 nebo 1:20:18 (čas může zůstat prázdný)."), "error")
        else:
            db = get_db()
            ev = db.execute("INSERT INTO events (name, date, place, created_by) VALUES (?,?,?,?)",
                            (name[:200], date.isoformat(), request.form.get("place", "").strip()[:200] or None,
                             g.user["id"])).lastrowid
            cid = db.execute("INSERT INTO classes (event_id, name) VALUES (?, ?)", (ev, cls[:40])).lastrowid
            eid = db.execute("INSERT INTO entries (user_id, class_id, official_time_s) VALUES (?,?,?)",
                             (g.user["id"], cid, time_s)).lastrowid
            db.commit()
            matching.match_user(db, g.user["id"])
            return redirect(url_for("ob.race", entry_id=eid))
    return render_template("ob/race_new.html")


@bp.route("/races/oris", methods=["GET", "POST"])
@login_required
def race_oris():
    """A race from ORIS by its id or a link to it, for a runner not entered in it under their number."""
    if request.method == "POST":
        oris_id = oris_class.parse_ref(request.form.get("zavod"))
        if oris_id is None:
            flash(_("Zadej číslo závodu v ORIS (např. 9827) nebo odkaz na něj (…/Zavod?id=9827)."), "error")
        else:
            try:
                oris_class.load_event(get_db(), cfg(), oris_id)
                return redirect(url_for("ob.race_oris_class", oris_id=oris_id))
            except oris_class.Refused as err:
                flash(str(err), "error")
    return render_template("ob/race_oris.html", ev=None, classes=[], have=None, aktivni="races")


@bp.route("/races/oris/<int:oris_id>", methods=["GET", "POST"])
@login_required
def race_oris_class(oris_id):
    """The classes of a race from ORIS (loaded by race_oris): the runner picks the one they ran."""
    db = get_db()
    ev = db.execute("SELECT * FROM events WHERE oris_id = ?", (oris_id,)).fetchone()
    if ev is None:
        return redirect(url_for("ob.race_oris"))
    if request.method == "POST":
        try:
            entry_id, msg = oris_class.add_race(db, cfg(), g.user, int(request.form.get("class_id") or 0))
            flash(msg, "ok")
            return redirect(url_for("ob.race", entry_id=entry_id))
        except (oris_class.Refused, ValueError) as err:
            flash(str(err), "error")
    have = db.execute("SELECT e.id, c.name FROM entries e JOIN classes c ON c.id = e.class_id"
                      " WHERE e.user_id = ? AND c.event_id = ? ORDER BY e.id LIMIT 1", (g.user["id"], ev["id"])).fetchone()
    return render_template("ob/race_oris.html", ev=ev, classes=oris_class.event_classes(db, ev["id"]), have=have,
                           oris_url=oris.event_url(oris_id), aktivni="races")


@bp.route("/races/<int:entry_id>/class", methods=["POST"])
@login_required
def race_class(entry_id):
    """"I ran another class": the entry of a race from ORIS moves to another of its classes (without class_id:
    the classes of the race are loaded from ORIS first)."""
    e = get_entry(entry_id)
    if not e["event_oris_id"]:
        abort(404)
    db = get_db()
    try:
        if request.form.get("class_id"):
            flash(oris_class.change_class(db, cfg(), g.user, entry_id, int(request.form["class_id"])), "ok")
        else:
            oris_class.load_event(db, cfg(), e["event_oris_id"])
            flash(_("Kategorie závodu jsou načtené z ORIS."), "ok")
    except (oris_class.Refused, ValueError) as err:
        flash(str(err), "error")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#kategorie")


def too_early(e, today=None):
    """Whether the race is today or still to come and the entry has no track yet: the look back "Ztratil jsem se
    u kontroly" is after the race (a phone and other aids are not allowed during it), so there is nothing yet."""
    today = today or dt.date.today().isoformat()
    return not e["activity_id"] and bool(e["date"]) and str(e["date"]) >= today


@bp.route("/races/<int:entry_id>")
@login_required
def race(entry_id):
    e = get_entry(entry_id)
    db = get_db()
    near = matching.places(dict(lat=e["event_lat"], lon=e["event_lon"], locations=e["locations"]))
    day = [dict(a, km_from_event=garmin.km_from(dict(lat=a["lat"], lon=a["lon"]), near))
           for a in db.execute("SELECT * FROM activities WHERE user_id = ? ORDER BY start_utc", (g.user["id"],))
           if a["start_utc"] and garmin.local(dt.datetime.fromisoformat(a["start_utc"])).date().isoformat() == e["date"]]
    job = last_jobs(db, g.user["id"]).get(entry_id)
    analysis = db.execute("SELECT * FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
    summary = loads(analysis["summary"], {}) if analysis else {}
    official = summary.get("official")
    model = db.execute("SELECT id FROM speed_models WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                       (g.user["id"],)).fetchone()
    src = storage.course_source(cfg(), e)
    return render_template(
        "ob/race.html", e=e, day=day, job=job, course_src=src, course_acc=course_accuracy(e, src),
        moved=mapfix.shifted(cfg(), e["event_id"]),
        classes=oris_class.event_classes(db, e["event_id"]) if e["event_oris_id"] else [],
        screen=screens.row(db, cfg(), e["class_id"], g.user["id"]),
        maponly_acc=int(e["maponly_acc_m"] + 0.5) if e["maponly_source"] == "snimek" and e["maponly_acc_m"] else None,
        has_photo=bool(db.execute("SELECT 1 FROM photos WHERE entry_id = ?", (entry_id,)).fetchone()),
        status=status(e, job), analysis=analysis, summary=summary, lost_early=too_early(e),
        official=official, official_reason=texts.official_reason((official or {}).get("reason")), aktivni="races",
        conf=texts.confidence(), match_note=texts.match_note(e["match_note"]), livelox=oris.livelox_url(e["livelox_id"]),
        oris_url=oris.event_url(e["event_oris_id"]), oris_results=oris.results_url(e["event_oris_id"]),
        oresults=oris.oresults_url(loads(e["links"], [])), club_url=club.event(e["event_oris_id"]),
        barriers=barriers.manual(db, e["event_id"], g.user["id"]), osm_info=_osm_info(e["event_id"]),
        osm_enabled=cfg().osm, mode_names={k: _(v) for k, v in MODE_NAMES.items()},
        hatch_info=barriers.hatch_data(cfg(), e["class_id"]),
        refreshes=refreshments(db, e["event_id"]), wide=bool(analysis),
        progress=entry_progress(db, entry_id), stamp=analysis_stamp(db, entry_id),
        sp=class_splits.view(db, e, g.user["oris_regno"], _model_times(db, analysis)),
        model_stale=bool(analysis and analysis["has_routes"] and model and analysis["model_id"] != model["id"]),
        # the catching features around the controls come from an older oroute/relocate.py, or from none at all
        relocate_stale=bool(analysis and analysis["has_routes"] and summary.get("relocate") != results.RELOCATE),
        # ... and the best routes from an older bestroute.py (a new analysis finds both again)
        routes_stale=bool(analysis and analysis["has_routes"] and summary.get("routes", 1) != results.ROUTES))


PHOTO_SOURCES = ("image", "photo", "manual", "screen")


def course_accuracy(e, src):
    """How far off the map with the course placed from a picture may be, in whole metres (at least 15 for a photo:
    the GPS at the punches is good to 5 to 15 m; at least 10 for a screenshot of Livelox, which is a straight picture
    of the map: oroute/pair.py), or None for a KMZ."""
    if src not in PHOTO_SOURCES:
        return None
    least = 10.0 if src == "screen" else 15.0
    return int(max(least, e["course_rms"] or 0, e["course_edge_m"] or 0) + 0.5)


def _model_times(db, analysis):
    """Model time of the best route of every leg of an analysis with routes, else None."""
    if analysis is None or not analysis["has_routes"]:
        return None
    return [(loads(r["data"]).get("best") or {}).get("time")
            for r in db.execute("SELECT data FROM legs WHERE analysis_id = ? ORDER BY n", (analysis["id"],))]


def _ws(db, e):
    """Loss per leg by the split times of the class, for the leg table of the map."""
    t = class_splits.table(db, e["class_id"], g.user["oris_regno"])
    return dict(class_splits.by_leg(t), n_legs=t["n_legs"]) if t and t["me"] is not None else None


def _osm_info(event_id):
    d = barriers.osm_data(cfg(), event_id)
    if not d:
        return None
    used = [l for l in d.get("lines", []) if cfg().osm_fences or l.get("what") != "fence"]
    return dict(fetched=d.get("fetched"), lines=len(used), crossings=len(d.get("crossings", [])))


MODE_NAMES = {"forbid": N_("zakázáno"), "penalty": N_("jen znevýhodněno"), "off": N_("nepoužívat")}


@bp.route("/races/<int:entry_id>/settings", methods=["POST"])
@login_required
def race_settings(entry_id):
    """How railways and motorways from OpenStreetMap are treated (osm_mode) and whether the hatched
    out-of-bounds areas of the map with the course are kept out of (hatch_mode).

    Every runner sets it for their own analysis (an empty value = as the race has it): only their routes are
    found again. With scope=event the value of the race is set, for the runners without a setting of their own:
    only whoever uploaded the map without course may, and only those runners' routes are found again."""
    e = get_entry(entry_id)
    allowed = dict(osm_mode=barriers.MODES, hatch_mode=barriers.HATCH_MODES)
    whole = request.form.get("scope") == "event"
    sent = {k: request.form[k] for k in allowed if k in request.form}
    if not sent or any(v not in allowed[k] and (whole or v != "") for k, v in sent.items()):
        abort(400)
    db = get_db()
    if whole:
        if e["maponly_by"] != g.user["id"]:
            abort(403)
        changed = [k for k, v in sent.items() if v != e["event_" + k]]
        for k in changed:
            db.execute(f"UPDATE events SET {k} = ? WHERE id = ?", (sent[k], e["event_id"]))
        db.commit()
        n = barriers.requeue_event(db, e["event_id"], following=changed) if changed else 0
    else:
        changed = [k for k, v in sent.items() if (v or None) != e["own_" + k]]
        for k in changed:
            db.execute(f"UPDATE entries SET own_{k} = ? WHERE id = ?", (sent[k] or None, entry_id))
        db.commit()
        # what holds for the runner may be the same as before (their own "forbid" where the race forbids too)
        moved = any((sent[k] or e["event_" + k]) != e[k] for k in changed)
        n = barriers.requeue_entry(db, entry_id, g.user["id"]) if moved and e["has_routes"] else 0
    if changed:
        flash(_("Uloženo.") + (_(" Postupy se přepočítají na pozadí.") if n else ""), "ok")
    else:
        flash(_("Nastavení se nezměnilo."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#nastaveni")


def _take_map(db, e, kind, f):
    """Store an uploaded map of the race (kind: course | maponly). Returns the ids of the entries to analyse
    again, or None when the file was refused (the reason is flashed). A picture instead of a KMZ is handed to
    the worker, which places it and queues the analysis itself."""
    ext = os.path.splitext(f.filename)[1].lower()
    if ext in storage.IMAGE_EXT:
        # A photo can be uploaded before the FIT: keep it in the user's data folder and place it once the
        # activity and official ORIS splits are available. It is only a map with the course.
        if kind != "course":
            flash(_("Obrázek jde nahrát jen jako mapu s tratí. Mapu bez tratě nahraj jako KMZ z Livelox."), "error")
            return None
        if storage.course_source(cfg(), e) == "kmz":
            flash(_("Pro tuhle kategorii už je mapa z KMZ, která je přesnější. Fotka se nepoužila."), "error")
            return None
        rel, tmp = storage.incoming(cfg(), ext)
        f.save(tmp)
        try:
            storage.check_image(tmp)
            from oroute import georef
            image = georef.open_image(tmp)
            storage.save_photo(db, cfg(), e["id"], image)
        except (ValueError, OSError) as err:
            if os.path.exists(tmp):
                os.remove(tmp)
            flash(str(err), "error")
            return None
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if not e["activity_id"] or not loads(e["splits"]):
            flash(_("Fotka je uložená. Až doplníš běh z hodinek a mezičasy z ORIS, usadí se automaticky."), "ok")
            return []
        jobs.enqueue(db, "georef_map", user_id=g.user["id"], entry_id=e["id"], payload=dict(stored_photo=True))
        flash(_("Fotka je uložená a usazuje se na pozadí; výsledek uvidíš v úlohách."), "ok")
        return []
    rel, tmp = storage.incoming(cfg(), ".kmz")
    f.save(tmp)
    try:
        storage.check_kmz(tmp)
    except ValueError as err:
        os.remove(tmp)
        flash(str(err), "error")
        return None
    if kind == "maponly":
        path = storage.save_map(cfg(), tmp, e["event_id"])
        db.execute("UPDATE events SET maponly_file = ?, maponly_by = ?, maponly_at = datetime('now'),"
                   " maponly_source = 'kmz', maponly_res_m = NULL, maponly_acc_m = NULL WHERE id = ?",
                   (path, g.user["id"], e["event_id"]))
        # the screenshots kept for the race are of no more use: a KMZ is sharper and placed exactly
        screens.drop_event(db, cfg(), e["event_id"])
        who = db.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id WHERE c.event_id = ?",
                         (e["event_id"],)).fetchall()
        flash(_("Mapa bez tratě je uložená pro všechny, kdo tenhle závod běželi.")
              + (_(" Nahradila mapu ze snímku Livelox; nejlepší postupy se přepočítají.")
                 if e["maponly_source"] == "snimek" else ""), "ok")
    else:
        was = storage.course_source(cfg(), e)
        path = storage.save_map(cfg(), tmp, e["event_id"], e["class_id"])
        # a KMZ replaces a photo: the photos kept for placing by hand and the course read from them go too
        storage.drop_photos(db, cfg(), e["class_id"])
        db.execute("UPDATE classes SET course_file = ?, course_by = ?, course_at = datetime('now'),"
                   " course_source = 'kmz', course_rms = NULL, course_n = NULL, course_edge_m = NULL WHERE id = ?",
                   (path, g.user["id"], e["class_id"]))
        who = db.execute("SELECT id FROM entries WHERE class_id = ?", (e["class_id"],)).fetchall()
        flash(_("Mapa s tratí je uložená pro kategorii %(class_name)s.", class_name=e['class_name'])
              + (_(" Nahradila mapu z fotky; analýza všech běžců kategorie se spustí znovu.")
                 if was in ("image", "photo", "manual") else
                 _(" Nahradila mapu ze snímku Livelox; analýza všech běžců kategorie se spustí znovu.")
                 if was == "screen" else ""), "ok")
    db.commit()
    return [r["id"] for r in who]


def _take_screens(db, e, course, maponly):
    """Two screenshots of Livelox (course: with the course, maponly: the same view without it; either may be
    missing): checked here as far as it goes without opening them, then handed to the worker (job georef_map with
    payload.screens, services/screens.py). Returns [] when a job was queued, None when refused (flashed)."""
    for f in (course, maponly):
        if f is not None and os.path.splitext(f.filename)[1].lower() not in storage.IMAGE_EXT:
            flash(_("%(filename)s: snímek obrazovky má být obrázek (png nebo jpg).", filename=f.filename), "error")
            return None
    if not e["activity_id"] or not loads(e["splits"]):
        flash(_("Snímek z Livelox se usazuje podle tvé stopy v oficiálních časech ražení: k závodu chybí běh z "
                  "hodinek nebo mezičasy z ORIS. Nahraj nejdřív běh z hodinek (.fit), nebo použij KMZ z Livelox."), "error")
        return None
    if maponly is not None and course is None and screens.row(db, cfg(), e["class_id"], g.user["id"]) is None:
        flash(_("Snímek bez tratě se usazuje podle snímku s tratí ze stejného pohledu. Nahraj nejdřív oba "
                  "snímky najednou (nebo mapu bez tratě jako KMZ z Livelox)."), "error")
        return None
    if maponly is not None and e["maponly_file"] and (e["maponly_source"] or "kmz") == "kmz":
        flash(_("Pro závod už je mapa bez tratě z KMZ, která je přesnější. Snímek bez tratě se nepoužil."), "error")
        maponly = None
        if course is None:
            return None
    sent = {}
    for key, f in (("course", course), ("maponly", maponly)):
        if f is None:
            continue
        rel, tmp = storage.incoming(cfg(), os.path.splitext(f.filename)[1].lower())
        f.save(tmp)
        try:
            storage.check_image(tmp)
        except ValueError as err:
            os.remove(tmp)
            for other in sent.values():
                os.remove(cfg().path(other))
            flash(f"{f.filename}: {err}", "error")
            return None
        sent[key] = rel
    jobs.enqueue(db, "georef_map", user_id=g.user["id"], entry_id=e["id"],
                 payload=dict(screens=dict(course=sent.get("course"), maponly=sent.get("maponly"))))
    flash(_("Snímky jsou nahrané. Usazují se na pozadí podle kontrol a tvé stopy; výsledek uvidíš v úlohách."), "ok")
    return []


@bp.route("/races/<int:entry_id>/map", methods=["POST"])
@login_required
def race_map_upload(entry_id):
    e = get_entry(entry_id)
    kind = request.form.get("kind")
    f = request.files.get("kmz")
    if kind not in ("course", "maponly") or not f or not f.filename:
        abort(400)
    db = get_db()
    who = _take_map(db, e, kind, f)
    for i in who or []:
        matching.queue_analysis(db, i)
    return redirect(url_for("ob.race", entry_id=entry_id) + ("" if who else "#podklady"))


MAX_FIT = 50 * 1024 * 1024  # a .fit of one run has a few hundred kB


@bp.route("/races/<int:entry_id>/files", methods=["POST"])
@login_required
def race_files(entry_id):
    """Everything the race needs in one form: the run from the watch (fit) and the two maps (course, maponly),
    any of them. The run is paired with this race by hand. The analysis is queued once, after all the files
    are in, not once per file."""
    e = get_entry(entry_id)
    db = get_db()
    sent = {k: f for k, f in ((k, request.files.get(k))
                              for k in ("fit", "course", "course_photo", "maponly", "screen_course", "screen_maponly"))
            if f and f.filename}
    # the photo of the paper map has its own field (the third way to the map), but it is the map with the course
    if "course_photo" in sent:
        photo = sent.pop("course_photo")
        sent.setdefault("course", photo)
    again = set()
    if not sent:
        flash(_("Vyber aspoň jeden soubor."), "error")
    if "fit" in sent:
        data = sent["fit"].read(MAX_FIT + 1)
        aid, name = None, sent["fit"].filename
        if name.lower().endswith(".zip") and len(data) <= MAX_FIT:
            # one activity exported from Garmin Connect: a zip with its .fit
            name, data = garmin.single_fit(io.BytesIO(data)) or (name, b"")
        if name.lower().endswith(".fit") and data and len(data) <= MAX_FIT:
            aid = storage.save_activity(db, cfg(), g.user["id"], data, name, "fit")[0]
        if aid is None:
            flash(_("%(filename)s: není aktivita Garmin (.fit se záznamem běhu, nebo zip s jedním .fit). Celý "
                      "export z Garminu nahraj v Nahrát běhy.", filename=sent['fit'].filename), "error")
        else:
            db.execute("UPDATE entries SET activity_id = ?, match_confidence = 'manual', match_note = NULL WHERE id = ?",
                       (aid, entry_id))
            db.commit()
            flash(_("Běh je nahraný a spárovaný s tímhle závodem."), "ok")
            again.add(entry_id)
            e = get_entry(entry_id)
    for kind in ("course", "maponly"):
        if kind in sent:
            again.update(_take_map(db, e, kind, sent[kind]) or [])
            e = get_entry(entry_id)
    if "screen_course" in sent or "screen_maponly" in sent:
        _take_screens(db, e, sent.get("screen_course"), sent.get("screen_maponly"))
    matching.queue_waiting_photos(db, g.user["id"])
    for i in sorted(again):
        matching.queue_analysis(db, i)
    return go(url_for("ob.race", entry_id=entry_id) + ("" if again else "#podklady"))


@bp.route("/races/<int:entry_id>/activity", methods=["POST"])
@login_required
def race_activity(entry_id):
    """Pair the race with an activity by hand, or go back to automatic matching."""
    get_entry(entry_id)
    db = get_db()
    aid = request.form.get("activity_id", "")
    if aid == "auto":
        db.execute("UPDATE entries SET match_confidence = NULL, activity_id = NULL WHERE id = ?", (entry_id,))
        db.commit()
        matching.match_user(db, g.user["id"])
    else:
        if not aid.isdigit() or not db.execute("SELECT 1 FROM activities WHERE id = ? AND user_id = ?",
                                               (aid, g.user["id"])).fetchone():
            abort(400)
        db.execute("UPDATE entries SET activity_id = ?, match_confidence = 'manual', match_note = NULL WHERE id = ?",
                   (int(aid), entry_id))
        db.commit()
        matching.queue_analysis(db, entry_id)
    return redirect(url_for("ob.race", entry_id=entry_id))


@bp.route("/races/<int:entry_id>/relocate", methods=["POST"])
@login_required
def race_relocate(entry_id):
    """Find the catching features around the controls again (a short job); the routes of the analysis stay."""
    e = get_entry(entry_id)
    if not e["has_routes"]:
        flash(_("Záchytné body se počítají až s nejlepšími postupy (chybí mapa bez tratě nebo analýza)."), "error")
    else:
        jobs.enqueue(get_db(), "relocate", user_id=g.user["id"], entry_id=entry_id)
        flash(_("Záchytné body se přepočítávají, za chvíli se objeví."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id))


@bp.route("/races/<int:entry_id>/reanalyse", methods=["POST"])
@login_required
def race_reanalyse(entry_id):
    get_entry(entry_id)
    if matching.queue_analysis(get_db(), entry_id) is None:
        flash(_("K analýze chybí běh (.fit) nebo mapa s tratí."), "error")
    else:
        flash(_("Analýza je zařazená do fronty."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id))


def _kmz_file(e, kind):
    rel = e["maponly_file"] if kind == "maponly" else e["course_file"] if kind == "course" else None
    if not rel or not os.path.exists(cfg().path(rel)):
        abort(404)
    return cfg().path(rel)


@bp.route("/races/<int:entry_id>/map/<kind>.img")
@login_required
def race_map_image(entry_id, kind):
    """The map picture out of the KMZ (the page lays it over the Leaflet map)."""
    path = _kmz_file(get_entry(entry_id), kind)
    with zipfile.ZipFile(path) as z:
        kml = z.read(next(n for n in z.namelist() if n.lower().endswith(".kml"))).decode("utf-8")
        href = re.search(r"<href>([^<]+)</href>", kml).group(1).strip()
        data = z.read(href)
    mime = "image/png" if href.lower().endswith(".png") else "image/jpeg"
    resp = send_file(io.BytesIO(data), mimetype=mime, max_age=3600, last_modified=os.path.getmtime(path))
    # the page asks with the stamp of the upload in the address (race_data): that picture never changes, so
    # the browser keeps it. Only the runner's own browser may: the map is for logged-in members.
    resp.headers["Cache-Control"] = "private, max-age=31536000, immutable" if request.args.get("v") \
        else "private, max-age=3600"
    return resp


def map_layers(e):
    """The two map pictures of an entry as the pages lay them over Leaflet: {kind: dict(url, corners, header_px)}."""
    maps = {}
    for kind in ("maponly", "course"):
        rel = e["maponly_file"] if kind == "maponly" else e["course_file"]
        if rel and os.path.exists(cfg().path(rel)):
            meta = storage.map_meta(cfg(), rel)
            maps[kind] = dict(url=url_for("ob.race_map_image", entry_id=e["id"], kind=kind, v=meta["stamp"][1]),
                              corners=meta["corners"], header_px=meta["header_px"])
    return maps


@bp.route("/races/<int:entry_id>/data.json")
@login_required
def race_data(entry_id):
    """Everything the map page draws."""
    e = get_entry(entry_id)
    db = get_db()
    analysis = db.execute("SELECT * FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
    if analysis is None:
        abort(404)
    maps = map_layers(e)
    legs, totals = view.legs_view(db, e, analysis, e["event_id"], _ws(db, e))
    lines, osm = barriers.for_map(db, cfg(), e["event_id"], e["osm_mode"], g.user["id"])
    return jsonify(maps=maps, course=loads(analysis["course"]), track=loads(analysis["track"]), legs=legs,
                   totals=totals, total_time=analysis["total_time_s"], has_routes=bool(analysis["has_routes"]),
                   refreshments=refreshments(db, e["event_id"]), barriers=lines, osm=osm,
                   areas=barriers.hatch_areas(cfg(), e["class_id"], e["hatch_mode"]),
                   rerouting=rerouting(db, entry_id), plans_pending=plans.pending(db, entry_id))


def rerouting(db, entry_id):
    """True while a new analysis of the entry is waiting or running (the routes on the page are about to change)."""
    return bool(db.execute("SELECT 1 FROM jobs WHERE entry_id = ? AND kind = 'analyse' AND status IN"
                           " ('queued', 'running')", (entry_id,)).fetchone())


def refreshments(db, event_id):
    """The refreshment points of the event for the logged-in runner. by: who added it; mine: they may delete it
    (their own point, or one whose author's account is gone)."""
    return [dict(id=r["id"], lat=r["lat"], lon=r["lon"], source=r["source"], by=r["who"],
                 mine=r["created_by"] in (None, g.user["id"]))
            for r in db.execute("SELECT r.*, COALESCE(u.name, u.username) AS who FROM refreshments r LEFT JOIN users u"
                                " ON u.id = r.created_by WHERE r.event_id = ? ORDER BY r.id", (event_id,))]


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Only the name can be changed here. The registration number belongs to the account for good: with
    another number the account would hold the races of two people and block the owner of that number."""
    if request.method == "POST":
        db = get_db()
        db.execute("UPDATE users SET name = ? WHERE id = ?",
                   (request.form.get("name", "").strip() or None, g.user["id"]))
        regno = accounts.clean_regno(request.form.get("oris_regno"))
        if cfg().local and regno and not g.user["oris_regno"]:
            # on one's own computer the number is given once here (there is no registration form)
            if not re.fullmatch(accounts.REGNO, regno):
                db.commit()
                flash(_("Registrační číslo má tvar tří písmen oddílu a čtyř číslic, např. BFM0000."), "error")
                return redirect(url_for("ob.profile"))
            try:
                person = oris.client(cfg()).user(regno)
            except oris.OrisError:
                db.commit()
                flash(_("ORIS teď neodpovídá, zkus registrační číslo uložit později."), "error")
                return redirect(url_for("ob.profile"))
            if person is None:
                db.commit()
                flash(_("Registrační číslo %(regno)s v ORIS není.", regno=regno), "error")
                return redirect(url_for("ob.profile"))
            db.execute("UPDATE users SET oris_regno = ?, oris_user_id = ?, name = COALESCE(name, ?) WHERE id = ?",
                       (regno, person["oris_user_id"], person["name"], g.user["id"]))
            db.commit()
            jobs.enqueue(db, "sync_oris", user_id=g.user["id"])
            flash(_("Uloženo. Závody z ORIS se načítají (%(name)s).", name=person['name']), "ok")
            return redirect(url_for("ob.races"))
        db.commit()
        flash(_("Uloženo."), "ok")
        return redirect(url_for("ob.profile"))
    return render_template("ob/profile.html", has=accounts.summary(get_db(), g.user["id"]))


@bp.route("/konec", methods=["POST"])
@login_required
def quit_app():
    """The app on one's own computer: "Ukončit aplikaci" in the menu (desktop.py sets OB_QUIT)."""
    stop = current_app.config.get("OB_QUIT")
    if not cfg().local or stop is None:
        abort(404)
    stop()
    return render_template("ob/quit.html")
