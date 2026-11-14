"""What the background worker is doing for the logged-in runner."""
from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for

from .. import get_db
from ..auth import login_required
from ..db import loads
from ..i18n import N_, _
from ..services import jobs
from . import bp

KINDS = {"sync_oris": N_("Načtení závodů z ORIS"), "import_upload": N_("Zpracování nahraných aktivit"),
         "analyse": N_("Analýza závodu"), "refit_model": N_("Přepočet osobního modelu"),
         "georef_map": N_("Usazení obrázku nebo fotky mapy"), "price_plans": N_("Ocenění plánovaného postupu"),
         "relocate": N_("Záchytné body u kontrol"), "recompute_all": N_("Přepočítat všechno"),
         "lost_scene": N_("Nápověda „Ztratil jsem se“")}
STATES = {"queued": (N_("čeká"), ""), "running": (N_("běží"), "ob-warn"), "done": (N_("hotovo"), "ob-ok"),
          "failed": (N_("chyba"), "ob-bad"), "stopped": (N_("zastaveno"), "")}
# kinds that can simply be queued again (an upload is gone by then)
RETRY = ("analyse", "sync_oris", "refit_model", "relocate", "recompute_all", "lost_scene")


def _rows():
    return get_db().execute(
        "SELECT j.*, ev.name AS event_name FROM jobs j LEFT JOIN entries e ON e.id = j.entry_id"
        " LEFT JOIN classes c ON c.id = e.class_id LEFT JOIN events ev ON ev.id = c.event_id"
        " WHERE j.user_id = ? ORDER BY j.id DESC LIMIT 60", (g.user["id"],)).fetchall()


def analysis_stamp(db, entry_id):
    """Text that changes whenever the analysis of the entry is replaced ('' without one). The race page
    carries the stamp of what it shows and loads itself again when jobs.json reports another one."""
    a = db.execute("SELECT id, has_routes, finished_at FROM analyses WHERE entry_id = ?", (entry_id,)).fetchone()
    return f"{a['id']}/{a['has_routes']}/{a['finished_at']}" if a else ""


def entry_progress(db, entry_id):
    """What is happening with the entry right now, in Czech ('' when none of its jobs waits or runs)."""
    job = db.execute("SELECT * FROM jobs WHERE entry_id = ? AND status IN ('queued', 'running')"
                     " ORDER BY status = 'queued', id LIMIT 1", (entry_id,)).fetchone()
    if job is None:
        return ""
    name = _(KINDS.get(job["kind"], job["kind"]))
    if job["status"] == "running":
        return f"{name}: {job['message'] or _('běží')}."
    # the worker takes the quick jobs first and analyses after them, each kind in the order they came
    late = int(job["kind"] in ("analyse", "recompute_all"))
    heavy = jobs.HEAVY_SQL
    ahead = db.execute("SELECT COUNT(*) FROM jobs WHERE status = 'running' OR (status = 'queued' AND"
                       f" ({heavy} < ? OR ({heavy} = ? AND id < ?)))",
                       (late, late, job["id"])).fetchone()[0]
    return _("%(name)s: čeká ve frontě", name=name) + (_(", úloh před ní: %(ahead)s.", ahead=ahead) if ahead else ".")


@bp.route("/jobs")
@login_required
def jobs_page():
    rows = _rows()
    # "try again" only next to the last job of its kind for the race, and only when that one failed
    last, retry = set(), set()
    for j in rows:
        key = (j["kind"], j["entry_id"])
        if key not in last and j["status"] == "failed" and j["kind"] in RETRY:
            retry.add(j["id"])
        last.add(key)
    # a photo that did not land: it is kept, and it can be placed by hand
    kept = {r["entry_id"] for r in get_db().execute(
        "SELECT p.entry_id FROM photos p JOIN entries e ON e.id = p.entry_id WHERE e.user_id = ?", (g.user["id"],))}
    by_hand = {j["id"] for j in rows if j["kind"] == "georef_map" and j["status"] == "failed" and j["entry_id"] in kept}
    # screenshots of Livelox kept for the class: the map can be cut out of them by hand (when the job says so)
    shots = {r["id"] for r in get_db().execute(
        "SELECT e.id FROM entries e JOIN screens s ON s.class_id = e.class_id AND s.user_id = e.user_id"
        " WHERE e.user_id = ?", (g.user["id"],))}
    by_crop = {j["id"] for j in rows if j["kind"] == "georef_map" and j["entry_id"] in shots
               and "ořízni snímek ručně" in ((j["error"] or "") + (j["message"] or ""))}
    return render_template("ob/jobs.html", jobs=rows, kinds=KINDS, states=STATES, retry=retry, by_hand=by_hand,
                           by_crop=by_crop)


@bp.route("/jobs/<int:job_id>/retry", methods=["POST"])
@login_required
def job_retry(job_id):
    db = get_db()
    j = db.execute("SELECT * FROM jobs WHERE id = ? AND user_id = ? AND status = 'failed'",
                   (job_id, g.user["id"])).fetchone()
    if j is None or j["kind"] not in RETRY:
        abort(404)
    jobs.enqueue(db, j["kind"], user_id=j["user_id"], entry_id=j["entry_id"], payload=loads(j["payload"]))
    flash(_("Úloha je znovu ve frontě."), "ok")
    return redirect(url_for("ob.jobs_page"))


@bp.route("/jobs/<int:job_id>/stop", methods=["POST"])
@login_required
def job_stop(job_id):
    """Stop one of the runner's own jobs (services/jobs.stop); anybody else's is not found."""
    got = jobs.stop(get_db(), job_id, g.user["id"])
    if got is None:
        abort(404)
    flash(_("Úloha je zastavená.") if got == "stopped" else
          _("Úloha se zastavuje: počítaný závod se zahodí, hotové zůstanou."), "ok")
    return redirect(url_for("ob.jobs_page"))


@bp.route("/jobs/stop", methods=["POST"])
@login_required
def jobs_stop_all():
    n = jobs.stop_all(get_db(), g.user["id"])
    flash(_("Zastaveno úloh: %(n)s.", n=n) if n else _("Žádná úloha nečeká ani neběží."), "ok")
    return redirect(url_for("ob.jobs_page"))


@bp.route("/jobs.json")
@login_required
def jobs_json():
    """How many jobs are still waiting or running and what the running ones are doing (pages poll this to
    show it and to load themselves again). With ?entry=N also the state of that race of the runner."""
    db = get_db()
    rows = db.execute("SELECT id, status, message FROM jobs WHERE user_id = ? AND status IN ('queued', 'running')",
                      (g.user["id"],)).fetchall()
    # ids: every waiting and running job; a page that shows one of them loads itself again once it is gone
    out = dict(active=len(rows), ids=[r["id"] for r in rows],
               running=[dict(id=r["id"], message=r["message"] or "") for r in rows if r["status"] == "running"])
    entry_id = request.args.get("entry", type=int)
    if entry_id and db.execute("SELECT 1 FROM entries WHERE id = ? AND user_id = ?",
                               (entry_id, g.user["id"])).fetchone():
        out.update(analysis=analysis_stamp(db, entry_id), progress=entry_progress(db, entry_id))
    return jsonify(out)
