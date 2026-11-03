"""The runner's personal speed model as tables: terrain and hills."""
import json
from collections import Counter

from flask import flash, g, redirect, render_template, request, url_for

from oroute import generic
from oroute import terrain as T
from oroute.speedmodel import PRIOR_SIGMA, SpeedModel

from .. import cfg, get_db, i18n
from ..auth import login_required
from ..db import loads
from ..i18n import N_, _
from ..services import charts, jobs, personal
from ..services import splits as class_splits
from . import bp

TERRAIN_CS = {
    "path/road": N_("cesta, silnice"), "open land": N_("louka"), "rough open": N_("hrubá louka"),
    "forest (runnable)": N_("les (dobře průběžný)"), "undergrowth (stripes)": N_("podrost (zelené šrafy)"),
    "light green (slow run)": N_("světle zelená (pomalý běh)"), "marsh": N_("bažina"),
    "green (walk)": N_("zelená (chůze)"), "dark green (fight)": N_("tmavě zelená (prodírání)")}
GRADES = [-30, -20, -15, -10, -5, 0, 5, 10, 15, 20, 30]
TOP_LEGS = 3   # legs shown under the summary of the average runner


def reason_label(kind, cls, pct, sprint=False):
    """The reason of oroute.generic.compare in a few words ("do kopce jsi rychlejší než průměr"; on a
    sprint map in its words: "na otevřené ploše", not "na louce")."""
    better = _("rychlejší") if pct > 0 else _("pomalejší")
    if kind == "up":
        return _("do kopce jsi %(better)s než průměr", better=better)
    if kind == "down":
        return _("z kopce jsi %(better)s než průměr", better=better)
    c = T.NAMES.index(cls) if cls in T.NAMES else None
    where = generic.words(i18n.lang(), bool(sprint))[2].get(c, _("v terénu"))
    return _("%(where)s jsi %(better)s než průměr", where=where, better=better)


def average_summary(db, user_id):
    """How often the runner's best route differs from an average runner's, over all their analysed legs with
    that comparison (bestroute.py --generic), and the most common reasons. None before any such analysis."""
    rows = db.execute(
        "SELECT l.n, l.name, e.id AS entry_id, ev.name AS event_name,"
        " json_extract(l.data, '$.generic.differs') AS differs, json_extract(l.data, '$.generic.gain') AS gain,"
        " json_extract(l.data, '$.generic.reason.kind') AS kind, json_extract(l.data, '$.generic.reason.cls') AS cls,"
        " json_extract(l.data, '$.generic.reason.pct') AS pct, json_extract(l.data, '$.generic.text_cs') AS text_cs,"
        " json_extract(l.data, '$.generic.text_en') AS text_en,"
        " json_extract(l.data, '$.generic.sprint') AS sprint"
        " FROM legs l JOIN analyses a ON a.id = l.analysis_id JOIN entries e ON e.id = a.entry_id"
        " JOIN classes c ON c.id = e.class_id JOIN events ev ON ev.id = c.event_id"
        " WHERE e.user_id = ? AND a.has_routes = 1 AND json_extract(l.data, '$.generic') IS NOT NULL",
        (user_id,)).fetchall()
    if not rows:
        return None
    differ = [r for r in rows if r["differs"]]
    yours = [r for r in differ if r["kind"] and (r["gain"] or 0) >= generic.LEVEL_S]
    reasons = Counter(reason_label(r["kind"], r["cls"], r["pct"] or 0, r["sprint"]) for r in yours)
    top = sorted(yours, key=lambda r: -(r["gain"] or 0))[:TOP_LEGS]
    return dict(legs=len(rows), races=len({r["entry_id"] for r in rows}), differ=len(differ), yours=len(yours),
                level=len(differ) - len(yours), reasons=reasons.most_common(3),
                top=[dict(entry_id=r["entry_id"], n=r["n"], name=r["name"], event=r["event_name"], gain=r["gain"],
                          text=(r["text_en"] or r["text_cs"]) if i18n.lang() == "en" else r["text_cs"]) for r in top])


def tables(model):
    """(terrain rows, hill rows) for a SpeedModel."""
    obs = model.notes.get("terrain", {})
    terrain = []
    for name, cs in TERRAIN_CS.items():
        f = model.factors.get(T.NAMES.index(name), 0.0)
        if f <= 0:
            continue
        o = obs.get(name, {})
        v = model.v_flat * f
        # without own data the factor is the ISOM value, known only as well as that prior
        se = o.get("rel_se", PRIOR_SIGMA)
        terrain.append(dict(name=_(cs), kmh=v * 3.6, pace=1000 / v, factor=f, seconds=o.get("seconds", 0),
                            implied=o.get("implied"), prior=o.get("prior"), se=se, kmh_pm=v * 3.6 * se,
                            trust="good" if se < 0.08 else "medium" if se < 0.16 else "low"))
    terrain.sort(key=lambda r: -r["kmh"])
    forest = model.factors.get(T.FOREST, 0.75)
    hills = []
    for gr in GRADES:
        m = float(model.slope_mult(gr / 100))
        hills.append(dict(grade=gr, mult=m, path_kmh=model.v_flat / m * 3.6, forest_kmh=model.v_flat * forest / m * 3.6,
                          path_pace=1000 * m / model.v_flat))
    return terrain, hills


FIT_RACES = 10   # "Jak dobře model sedí": the latest races with best routes and the split times of the class


def class_fit(db, user):
    """How well the speed model orders the legs as the class does (services/splits.agreement), for the latest
    analysed races with the split times of the whole class: [{entry_id, name, date, agreement}]."""
    out = []
    rows = db.execute(
        "SELECT e.id, e.class_id, ev.name, ev.date, a.id AS analysis_id FROM entries e JOIN classes c ON c.id = e.class_id"
        " JOIN events ev ON ev.id = c.event_id JOIN analyses a ON a.entry_id = e.id"
        " WHERE e.user_id = ? AND a.has_routes = 1 AND EXISTS (SELECT 1 FROM class_splits s WHERE s.class_id = c.id)"
        " ORDER BY ev.date DESC LIMIT ?", (user["id"], FIT_RACES)).fetchall()
    for r in rows:
        times = [(loads(x["data"]).get("best") or {}).get("time")
                 for x in db.execute("SELECT data FROM legs WHERE analysis_id = ? ORDER BY n", (r["analysis_id"],))]
        a = class_splits.agreement(class_splits.table(db, r["class_id"], user["oris_regno"]), times)
        if a is not None:
            out.append(dict(entry_id=r["id"], name=r["name"], date=r["date"], agreement=a))
    return out


@bp.route("/model")
@login_required
def model():
    db = get_db()
    rows = db.execute("SELECT * FROM speed_models WHERE user_id = ? ORDER BY id DESC LIMIT 20", (g.user["id"],)).fetchall()
    if not rows:
        return render_template("ob/model.html", model=None)
    m = SpeedModel.load(cfg().path(rows[0]["file"]))
    terrain, hills = tables(m)
    history = [dict(fitted_at=r["fitted_at"], v_flat=loads(r["model"])["v_flat"] * 3.6,
                    races=len((loads(r["model"]).get("notes", {}).get("personal") or {}).get("races", [])))
               for r in rows]
    slope_file = cfg().path(g.user["slope_file"]) if g.user["slope_file"] else personal.DEFAULT_SLOPE
    try:
        with open(slope_file, encoding="utf-8") as f:
            curve = json.load(f).get("curve") or []
    except (OSError, ValueError):
        curve = []
    return render_template("ob/model.html", model=m, terrain=terrain, hills=hills, history=history,
                           personal=m.notes.get("personal") or {}, slope=m.slope_from or {},
                           slope_own=bool(m.notes.get("slope_own")), fitted_at=rows[0]["fitted_at"],
                           slope_chart=charts.slope_chart(m, curve), check=m.notes.get("check"),
                           average=average_summary(db, g.user["id"]), fit=class_fit(db, g.user))


@bp.route("/model/prepocitat-vse", methods=["POST"])
@login_required
def recompute_all():
    """Samples of every race, one model, then the routes of every race with it (handlers._recompute_all)."""
    jobs.enqueue(get_db(), "recompute_all", user_id=g.user["id"])
    flash(_("Přepočítat všechno je ve frontě: postup uvidíš v seznamu úloh."), "ok")
    back = request.form.get("zpet")
    return redirect(back if back and back.startswith("/") and not back.startswith("//") else url_for("ob.model"))


@bp.route("/model/refit", methods=["POST"])
@login_required
def model_refit():
    jobs.enqueue(get_db(), "refit_model", user_id=g.user["id"])
    flash(_("Přepočet osobního modelu je ve frontě."), "ok")
    return redirect(url_for("ob.model"))
