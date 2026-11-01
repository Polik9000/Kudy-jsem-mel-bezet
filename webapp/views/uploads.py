"""Upload activities: single .fit files or a zip (a whole Garmin account export, or just some .fit files)."""
from flask import abort, flash, g, redirect, render_template, request, url_for

from .. import cfg, get_db
from ..auth import login_required
from ..services import jobs, matching, storage, watch
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
                    flash(f"{f.filename}: nahrát jde jen .fit nebo .zip.", "error")
                continue
            rel, path = storage.incoming(cfg(), "." + kind)
            f.save(path)  # streamed to disk; a Garmin export can have gigabytes
            jobs.enqueue(db, "import_upload", user_id=g.user["id"], payload=dict(file=rel, name=f.filename, kind=kind))
            n += 1
        if n:
            flash(f"Nahráno souborů: {n}. Zpracují se na pozadí a samy se spárují se závody.", "ok")
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
        flash("Běh je spárovaný se závodem. Nejdřív u závodu vyber jiný běh.", "error")
    else:
        storage.drop_activity(db, cfg(), activity_id)
        db.commit()
        flash("Běh je smazaný.", "ok")
    return redirect(url_for("ob.upload"))


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
            flash("Složka neexistuje.", "error")
            return redirect(url_for("ob.watch_page"))
        flash(f"Načteno běhů: {loaded}." + (f" Už v aplikaci bylo {there}." if there else "")
              + (" Běhy se se závody spárovaly samy." if loaded else ""), "ok" if loaded else "error")
        return redirect(url_for("ob.upload"))
    rows = base = None
    if not folder and len(found) == 1:
        folder = found[0]
    if folder:
        try:
            base, rows = watch.offer(db, g.user["id"], folder)
        except FileNotFoundError:
            flash("Složka neexistuje. Zkontroluj cestu.", "error")
    return render_template("ob/watch.html", found=found, folder=folder, base=base, rows=rows,
                           sample="D:\\GARMIN\\Activity")
