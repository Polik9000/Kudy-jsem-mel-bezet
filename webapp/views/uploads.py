"""Upload activities: single .fit files or a zip (a whole Garmin account export, or just some .fit files)."""
from flask import abort, flash, g, redirect, render_template, request, url_for

from .. import cfg, get_db
from ..auth import login_required
from ..i18n import _
from ..services import jobs, matching, storage
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
