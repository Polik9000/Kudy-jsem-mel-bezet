"""Nahrát: the runs (single .fit files or a zip, Garmin Connect, a watch or a folder) and the maps of a race on one page."""
from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for

from .. import cfg, get_db
from ..auth import login_required
from ..i18n import _
from ..services import garmin_api, jobs, matching, storage, watch
from . import bp, go, skipped
from .jobs import KINDS
from .races import get_entry, map_files


def _looks_like(f, kind):
    """True when the start of the file is what a .fit (".FIT" at bytes 8 to 11) or a zip ("PK") starts with. A
    broken file is told at once, by its name, and the others of the same upload still go through."""
    head = f.stream.read(12)
    f.stream.seek(0)
    return head[8:12] == b".FIT" if kind == "fit" else head[:2] == b"PK"


SOURCES = ("pocitac", "garmin", "hodinky")   # where the run comes from: a file, Garmin Connect, a watch or folder
ACTIVE_SQL = ("SELECT id, kind, status, message FROM jobs WHERE user_id = ? AND status IN ('queued', 'running')")


def _source():
    """The source of runs Nahrát opens on: the one asked for (?zdroj=, kept), else the last one used, kept with the
    account like the light / dark mode (the app on one's own computer starts on another port each time)."""
    asked = request.args.get("zdroj")
    if asked in SOURCES and asked != g.user["upload_source"]:
        _keep_source(asked)
    src = asked if asked in SOURCES else g.user["upload_source"]
    return src if src in SOURCES and (src == "pocitac" or cfg().local) else "pocitac"


def _keep_source(src):
    db = get_db()
    db.execute("UPDATE users SET upload_source = ? WHERE id = ?", (src, g.user["id"]))
    db.commit()


def _active(db, uid, entry_id=None):
    """The jobs of the runner that wait or run, for the line under each part of Nahrát: those of the runs (no race)
    or those of one race. Each comes as (id, name, text); the page follows them and loads itself again when they end."""
    rows = db.execute(ACTIVE_SQL + (" AND entry_id = ?" if entry_id else " AND entry_id IS NULL") + " ORDER BY id LIMIT 4",
                      (uid, entry_id) if entry_id else (uid,)).fetchall()
    return [(r["id"], _(KINDS.get(r["kind"], r["kind"])), r["message"] or (_("běží") if r["status"] == "running" else
                                                                          _("čeká ve frontě"))) for r in rows]


def _races(db, uid):
    """The races to pick for the maps: the newest first, with what each still lacks."""
    return db.execute(
        "SELECT e.id, ev.name, ev.date, c.name AS class_name, c.course_file IS NOT NULL AS has_course,"
        " ev.maponly_file IS NOT NULL AS has_maponly FROM entries e JOIN classes c ON c.id = e.class_id"
        " JOIN events ev ON ev.id = c.event_id WHERE e.user_id = ? ORDER BY ev.date DESC, e.id DESC LIMIT 400",
        (uid,)).fetchall()


@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Nahrát: the run (from a file, from Garmin Connect, from a watch or a folder: the three sources switch in place)
    and the maps of one race (picked, or the one the link came from: ?zavod=<entry id>)."""
    db = get_db()
    if request.method == "POST":
        n = 0
        skipped()
        for f in request.files.getlist("files"):
            name = (f.filename or "").lower()
            kind = "fit" if name.endswith(".fit") else "zip" if name.endswith(".zip") else None
            if kind is None:
                if name:
                    flash(_("%(filename)s: nahrát jde jen .fit nebo .zip.", filename=f.filename), "error")
                continue
            if not _looks_like(f, kind):
                flash(_("%(filename)s: není soubor z hodinek (.fit), nebo je poškozený. Nenahrál se, ostatní ano.",
                        filename=f.filename) if kind == "fit" else
                      _("%(filename)s: není zip, nebo je poškozený. Nenahrál se, ostatní ano.", filename=f.filename),
                      "error")
                continue
            rel, path = storage.incoming(cfg(), "." + kind)
            f.save(path)  # streamed to disk; a Garmin export can have gigabytes
            jobs.enqueue(db, "import_upload", user_id=g.user["id"], payload=dict(file=rel, name=f.filename, kind=kind))
            n += 1
        if n:
            flash(_("Nahráno souborů: %(n)s. Zpracují se na pozadí a samy se spárují se závody.", n=n), "ok")
            return go(url_for("ob.upload"))   # the state of the job is shown on Nahrát, under the form
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return go(url_for("ob.upload"))  # the page it loads next shows why the files were refused
    uid = g.user["id"]
    src = _source()
    panel = _garmin(request.args.get("dni", type=int)) if src == "garmin" else \
        _watch((request.args.get("slozka") or "").strip()) if src == "hodinky" else {}
    races = _races(db, uid)
    picked = request.args.get("zavod", type=int)
    if picked not in {r["id"] for r in races}:
        # no race asked for: the newest one that still lacks a map, else the newest
        picked = next((r["id"] for r in races if not (r["has_course"] and r["has_maponly"])),
                      races[0]["id"] if races else None)
    e = get_entry(picked) if picked else None
    acts = db.execute(
        "SELECT a.*, (SELECT ev.name FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
        " ON ev.id = c.event_id WHERE e.activity_id = a.id LIMIT 1) AS race,"
        " (SELECT e.id FROM entries e WHERE e.activity_id = a.id LIMIT 1) AS race_entry FROM activities a"
        " WHERE a.user_id = ? ORDER BY a.start_utc DESC LIMIT 300", (uid,)).fetchall()
    total = db.execute("SELECT COUNT(*) FROM activities WHERE user_id = ?", (uid,)).fetchone()[0]
    return render_template("ob/upload.html", acts=acts, total=total, at_races=matching.at_races(db, uid),
                           source=src, sources=SOURCES if cfg().local else ("pocitac",), races=races, e=e,
                           run_jobs=_active(db, uid), map_jobs=_active(db, uid, e["id"]) if e else [],
                           **(map_files(db, e) if e else {}), **panel)


@bp.route("/upload/zdroj", methods=["POST"])
@login_required
def upload_source():
    """The switch of the source on Nahrát (static/ob.js): {"zdroj": "pocitac" | "garmin" | "hodinky"}, kept."""
    src = (request.get_json(silent=True) or {}).get("zdroj")
    if src not in SOURCES or (src != "pocitac" and not cfg().local):
        abort(400)
    _keep_source(src)
    return "", 204


@bp.route("/upload/panel/<src>")
@login_required
def upload_panel(src):
    """The panel of one source, for Nahrát to put in place when it is switched to (and again for another period or
    folder): the panels of Garmin Connect and of the watch ask Garmin or the disk, so only the shown one is made."""
    if src not in ("garmin", "hodinky") or not cfg().local:
        abort(404)
    ctx = _garmin(request.args.get("dni", type=int)) if src == "garmin" else \
        _watch((request.args.get("slozka") or "").strip())
    return render_template(f"ob/_zdroj_{src}.html", **ctx)


@bp.route("/activities/<int:activity_id>/delete", methods=["POST"])
@login_required
def activity_delete(activity_id):
    """Delete an uploaded run that is paired with no race (one paired with a race is the race's track)."""
    db = get_db()
    row = db.execute("SELECT a.id, EXISTS (SELECT 1 FROM entries e WHERE e.activity_id = a.id) AS paired"
                     " FROM activities a WHERE a.id = ? AND a.user_id = ?", (activity_id, g.user["id"])).fetchone()
    if row is None:
        abort(404)
    if row["paired"]:
        flash(_("Běh je spárovaný se závodem. Nejdřív u závodu vyber jiný běh."), "error")
    else:
        storage.drop_activity(db, cfg(), activity_id)
        db.commit()
        flash(_("Běh je smazaný."), "ok")
    return redirect(url_for("ob.upload"))


DAYS = (14, 60, 365, 3650)   # periods offered for Garmin Connect


def _garmin(days):
    """What the panel Garmin Connect on Nahrát shows: the key form, or the runs of the period from the account."""
    conf, uid = cfg(), g.user["id"]
    days = days if days in DAYS else 60
    rows, error, connected = None, None, garmin_api.has_key(conf, uid)
    if connected:
        try:
            rows = garmin_api.offer(get_db(), conf, uid, days)
        except garmin_api.GarminApiError as e:
            error = str(e)
    types = sorted({r["type"] for r in rows or []})
    types = [(t, sum(1 for r in rows if r["type"] == t)) for t in types]
    return dict(connected=connected, rows=rows, types=types, days=days, periods=DAYS, garmin_error=error,
                key_page=garmin_api.KEY_PAGE)


def _watch(folder):
    """What the panel Hodinky / složka on Nahrát shows: the watches found, the folder and its runs."""
    found, rows, base, error = watch.watch_folders(), None, None, None
    if not folder and len(found) == 1:
        folder = found[0]
    if folder:
        try:
            base, rows = watch.offer(get_db(), g.user["id"], folder)
        except FileNotFoundError:
            error = _("Složka neexistuje. Zkontroluj cestu.")
    return dict(found=found, folder=folder, base=base, watch_rows=rows, watch_error=error, sample="D:\\GARMIN\\Activity")


@bp.route("/upload/garmin", methods=["GET", "POST"])
@login_required
def garmin_page():
    """Runs straight from the runner's Garmin Connect account (Garmin's Personal API, services/garmin_api.py).
    Only the app on one's own computer: on a server the key of every runner would sit on the server. The panel is
    on Nahrát; this address takes its forms and sends an old link there."""
    if not cfg().local:
        abort(404)
    db, conf, uid = get_db(), cfg(), g.user["id"]
    back = url_for("ob.upload", zdroj="garmin") + "#zdroj=garmin"
    if request.method == "GET":
        days = request.args.get("dni", type=int)
        return redirect(url_for("ob.upload", zdroj="garmin", **({"dni": days} if days else {})) + "#zdroj=garmin")
    act = request.form.get("akce")
    if act == "klic":
        try:
            garmin_api.save_key(conf, uid, request.form.get("klic"))
        except garmin_api.GarminApiError as e:
            flash(str(e), "error")
        else:
            flash(_("Klíč je uložený jen v tomhle počítači. Appka teď načte tvoje aktivity z Garmin Connect."), "ok")
    elif act == "odpojit":
        garmin_api.forget(conf, uid)
        flash(_("Klíč je z tohoto počítače smazaný. V Garmin Connect ho můžeš smazat i tam."), "ok")
    elif act == "nacist":
        ids = [int(i) for i in request.form.getlist("aktivita") if i.isdecimal()]
        days = request.form.get("dni_model", type=int) if request.form.get("model") else None
        days = days if days in DAYS else (365 if days else None)
        if not ids and not days:
            flash(_("Nevybral jsi žádnou aktivitu ani model kopců."), "error")
        else:
            jobs.enqueue(db, "garmin_api", user_id=uid, payload=dict(ids=ids, model_days=days))
            flash(_("Stahuji z Garmin Connect: vybrané aktivity %(n)s, model kopců: %(model)s."
                    " Samy se spárují se závody.", n=len(ids), model=_("ano") if days else _("ne")), "ok")
            return go(back)
    return redirect(back)


@bp.route("/upload/hodinky", methods=["GET", "POST"])
@login_required
def watch_page():
    """Runs from a watch connected by USB, or from a folder (only the app on one's own computer: the server
    would read its own disk). The panel is on Nahrát; this address loads the ticked runs and sends an old link there."""
    if not cfg().local:
        abort(404)
    folder = (request.values.get("slozka") or "").strip()
    back = url_for("ob.upload", zdroj="hodinky", **({"slozka": folder} if folder else {})) + "#zdroj=hodinky"
    if request.method == "GET":
        return redirect(back)
    try:
        loaded, there, refused = watch.load(get_db(), cfg(), g.user, folder, request.form.getlist("soubor"))
    except FileNotFoundError:
        flash(_("Složka neexistuje."), "error")
        return redirect(back)
    flash(_("Načteno běhů: %(n)s.", n=loaded) + (" " + _("Už v aplikaci bylo %(n)s.", n=there) if there else "")
          + (" " + _("Běhy se se závody spárovaly samy.") if loaded else ""), "ok" if loaded else "error")
    return redirect(back)


@bp.route("/upload/hodinky/nove.json")
@login_required
def watch_news():
    """The note on Přehled závodů and Nahrát běhy: how many new runs a connected watch has (asked by ob.js after the
    page is shown, so a slow disk never holds the page). Nothing is loaded here."""
    if not cfg().local:
        abort(404)
    out = watch.news(get_db(), g.user["id"])
    if out["n"]:
        out["url"] = url_for("ob.upload", zdroj="hodinky", slozka=out["folder"]) + "#zdroj=hodinky"
    out.pop("folder")
    return jsonify(out)


@bp.route("/upload/hodinky/ted-ne", methods=["POST"])
@login_required
def watch_not_now():
    """"Teď ne" on the note: the runs on the watch now are not offered on the pages again."""
    if not cfg().local:
        abort(404)
    watch.set_aside_all(get_db(), g.user["id"])
    return jsonify(ok=True)
