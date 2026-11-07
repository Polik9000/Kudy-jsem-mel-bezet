"""Upload activities: single .fit files or a zip (a whole Garmin account export, or just some .fit files)."""
from flask import abort, flash, g, redirect, render_template, request, url_for

from .. import cfg, get_db
from ..auth import login_required
from ..i18n import _
from ..services import garmin_api, jobs, matching, storage, watch
from . import bp, go


@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    db = get_db()
    if request.method == "POST":
        n = 0
        for f in request.files.getlist("files"):
            name = (f.filename or "").lower()
            kind = "fit" if name.endswith(".fit") else "zip" if name.endswith(".zip") else None
            if kind is None:
                if name:
                    flash(_("%(filename)s: nahrát jde jen .fit nebo .zip.", filename=f.filename), "error")
                continue
            rel, path = storage.incoming(cfg(), "." + kind)
            f.save(path)  # streamed to disk; a Garmin export can have gigabytes
            jobs.enqueue(db, "import_upload", user_id=g.user["id"], payload=dict(file=rel, name=f.filename, kind=kind))
            n += 1
        if n:
            flash(_("Nahráno souborů: %(n)s. Zpracují se na pozadí a samy se spárují se závody.", n=n), "ok")
            return go(url_for("ob.jobs_page"))
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return go(url_for("ob.upload"))  # the page it loads next shows why the files were refused
    acts = db.execute(
        "SELECT a.*, (SELECT ev.name FROM entries e JOIN classes c ON c.id = e.class_id JOIN events ev"
        " ON ev.id = c.event_id WHERE e.activity_id = a.id LIMIT 1) AS race,"
        " (SELECT e.id FROM entries e WHERE e.activity_id = a.id LIMIT 1) AS race_entry FROM activities a"
        " WHERE a.user_id = ? ORDER BY a.start_utc DESC LIMIT 300", (g.user["id"],)).fetchall()
    total = db.execute("SELECT COUNT(*) FROM activities WHERE user_id = ?", (g.user["id"],)).fetchone()[0]
    return render_template("ob/upload.html", acts=acts, total=total, at_races=matching.at_races(db, g.user["id"]))


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


DAYS = (14, 60, 365, 3650)   # periods offered on the Garmin Connect page


@bp.route("/upload/garmin", methods=["GET", "POST"])
@login_required
def garmin_page():
    """Runs straight from the runner's Garmin Connect account (Garmin's Personal API, services/garmin_api.py).
    Only the app on one's own computer: on a server the key of every runner would sit on the server."""
    if not cfg().local:
        abort(404)
    db, conf, uid = get_db(), cfg(), g.user["id"]
    if request.method == "POST":
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
                return go(url_for("ob.jobs_page"))
        return redirect(url_for("ob.garmin_page"))
    days = request.args.get("dni", type=int)
    days = days if days in DAYS else 60
    rows, connected = None, garmin_api.has_key(conf, uid)
    if connected:
        try:
            rows = garmin_api.offer(db, conf, uid, days)
        except garmin_api.GarminApiError as e:
            flash(str(e), "error")
    types = sorted({r["type"] for r in rows or []})
    types = [(t, sum(1 for r in rows if r["type"] == t)) for t in types]
    return render_template("ob/garmin.html", connected=connected, rows=rows, types=types, days=days, periods=DAYS,
                           key_page=garmin_api.KEY_PAGE)


@bp.route("/upload/hodinky", methods=["GET", "POST"])
@login_required
def watch_page():
    """Runs from a watch connected by USB, or from a folder (only the app on one's own computer: the server
    would read its own disk)."""
    if not cfg().local:
        abort(404)
    db = get_db()
    folder = (request.values.get("slozka") or "").strip()
    found = watch.watch_folders()
    if request.method == "POST":
        try:
            loaded, there, refused = watch.load(db, cfg(), g.user, folder, request.form.getlist("soubor"))
        except FileNotFoundError:
            flash(_("Složka neexistuje."), "error")
            return redirect(url_for("ob.watch_page"))
        flash(_("Načteno běhů: %(n)s.", n=loaded) + (" " + _("Už v aplikaci bylo %(n)s.", n=there) if there else "")
              + (" " + _("Běhy se se závody spárovaly samy.") if loaded else ""), "ok" if loaded else "error")
        return redirect(url_for("ob.upload"))
    rows = base = None
    if not folder and len(found) == 1:
        folder = found[0]
    if folder:
        try:
            base, rows = watch.offer(db, g.user["id"], folder)
        except FileNotFoundError:
            flash(_("Složka neexistuje. Zkontroluj cestu."), "error")
    return render_template("ob/watch.html", found=found, folder=folder, base=base, rows=rows,
                           sample="D:\\GARMIN\\Activity")
