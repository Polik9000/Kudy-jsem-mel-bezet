"""Notes on a leg (planned route, check boxes, text) and the shared refreshment points of a race."""
from flask import abort, flash, g, jsonify, redirect, request, url_for

from .. import cfg, get_db
from ..auth import login_required
from ..db import dumps
from ..i18n import _
from ..services import barriers, jobs, plans, view
from . import bp
from .races import _ws, get_entry, refreshments, rerouting

MODEL_FIELDS = ("deliberate_stop", "lost_contact", "green", "fatigue")  # these change the speed model


def _latlon(p):
    lat, lon = float(p[0]), float(p[1])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError
    return [round(lat, 6), round(lon, 6)]


DESC_MAX = 200


def save_control_desc(db, entry_id, n, text):
    """The description of the control at the end of leg n, as typed (at most DESC_MAX characters; empty: none).
    It changes nothing that is computed: no model, no routes (it is not in MODEL_FIELDS)."""
    text = " ".join(str(text or "").split())[:DESC_MAX] or None
    db.execute("INSERT INTO leg_notes (entry_id, leg_n, control_desc) VALUES (?, ?, ?)"
               " ON CONFLICT (entry_id, leg_n) DO UPDATE SET control_desc = excluded.control_desc,"
               " updated_at = datetime('now')", (entry_id, n, text))


def _legs_json(db, e):
    analysis = db.execute("SELECT * FROM analyses WHERE entry_id = ?", (e["id"],)).fetchone()
    lines, _ = barriers.for_map(db, cfg(), e["event_id"], "off", g.user["id"])
    if analysis is None:  # shared settings can be changed before the runner's own analysis exists
        return jsonify(barriers=lines, refreshments=refreshments(db, e["event_id"]), rerouting=False)
    legs, totals = view.legs_view(db, e, analysis, e["event_id"], _ws(db, e), geometry=False)
    return jsonify(legs=legs, totals=totals, refreshments=refreshments(db, e["event_id"]), barriers=lines,
                   rerouting=rerouting(db, e["id"]), plans_pending=plans.pending(db, e["id"]))


@bp.route("/races/<int:entry_id>/legs.json")
@login_required
def legs_json(entry_id):
    """The numbers of the legs again (no lines): the page asks while a planned route is being priced."""
    return _legs_json(get_db(), get_entry(entry_id))


@bp.route("/races/<int:entry_id>/barriers", methods=["POST"])
@login_required
def barrier_add(entry_id):
    """A line that must not be crossed, drawn on the map; shared by everyone at the event."""
    e = get_entry(entry_id)
    db = get_db()
    d = request.get_json(silent=True) or {}
    try:
        line = [_latlon(p) for p in d["line"]]
        kind = d.get("kind") or "forbidden"
        if not 2 <= len(line) <= 200 or kind not in ("forbidden", "hard"):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError):
        abort(400)
    if db.execute("SELECT COUNT(*) FROM barriers WHERE event_id = ?", (e["event_id"],)).fetchone()[0] >= 100:
        abort(400)
    db.execute("INSERT INTO barriers (event_id, kind, line, created_by) VALUES (?,?,?,?)",
               (e["event_id"], kind, dumps(line), g.user["id"]))
    db.commit()
    barriers.requeue_event(db, e["event_id"])
    return _legs_json(db, e)


def _own(db, table, row_id, event_id):
    """Refuse (403) unless the shared thing of the event was added by the logged-in runner. One whose author's
    account is gone may be removed by anyone at the event, or nobody could. Returns False when it is not there."""
    row = db.execute(f"SELECT created_by FROM {table} WHERE id = ? AND event_id = ?", (row_id, event_id)).fetchone()
    if row is not None and row["created_by"] not in (None, g.user["id"]):
        abort(403)
    return row is not None


def _barrier_delete(e, bid):
    """A line is shared by the event on purpose, so only whoever drew it takes it away."""
    db = get_db()
    if _own(db, "barriers", bid, e["event_id"]):
        db.execute("DELETE FROM barriers WHERE id = ?", (bid,))
        db.commit()
        barriers.requeue_event(db, e["event_id"])
    return db


@bp.route("/races/<int:entry_id>/barriers/<int:bid>", methods=["DELETE"])
@login_required
def barrier_delete(entry_id, bid):
    e = get_entry(entry_id)
    return _legs_json(_barrier_delete(e, bid), e)


@bp.route("/races/<int:entry_id>/barriers/<int:bid>/delete", methods=["POST"])
@login_required
def barrier_remove(entry_id, bid):
    """The same from the settings tab (a plain form, no script needed)."""
    _barrier_delete(get_entry(entry_id), bid)
    flash(_("Čára je smazaná, postupy se přepočítají všem, kdo závod běželi."), "ok")
    return redirect(url_for("ob.race", entry_id=entry_id) + "#nastaveni")


@bp.route("/races/<int:entry_id>/legs/<int:n>/note", methods=["POST"])
@login_required
def leg_note(entry_id, n):
    e = get_entry(entry_id)
    db = get_db()
    if not e["analysis_id"] or not db.execute("SELECT 1 FROM legs WHERE analysis_id = ? AND n = ?",
                                              (e["analysis_id"], n)).fetchone():
        abort(404)
    d = request.get_json(silent=True) or {}
    try:
        green = d.get("green") or None
        fatigue = int(d["fatigue"]) if d.get("fatigue") not in (None, "") else None
        planned = [_latlon(p) for p in d["planned"]] if d.get("planned") else None
        if green not in (None, "through", "around") or fatigue not in (None, 1, 2, 3, 4, 5) \
                or (planned and not 2 <= len(planned) <= 500):
            raise ValueError
    except (ValueError, TypeError, IndexError, KeyError):
        abort(400)
    new = dict(planned=dumps(planned) if planned else None, deliberate_stop=1 if d.get("deliberate_stop") else 0,
               lost_contact=1 if d.get("lost_contact") else 0, green=green, fatigue=fatigue,
               text=str(d.get("text") or "")[:2000])
    old = db.execute("SELECT * FROM leg_notes WHERE entry_id = ? AND leg_n = ?", (entry_id, n)).fetchone()
    db.execute(
        "INSERT INTO leg_notes (entry_id, leg_n, planned, deliberate_stop, lost_contact, green, fatigue, text)"
        " VALUES (:entry_id, :leg_n, :planned, :deliberate_stop, :lost_contact, :green, :fatigue, :text)"
        " ON CONFLICT (entry_id, leg_n) DO UPDATE SET planned = excluded.planned,"
        # the numbers of the planned route belong to the line: another line (or none) and they are gone
        " plan = CASE WHEN leg_notes.planned IS excluded.planned THEN leg_notes.plan END,"
        " deliberate_stop = excluded.deliberate_stop, lost_contact = excluded.lost_contact, green = excluded.green,"
        " fatigue = excluded.fatigue, text = excluded.text, updated_at = datetime('now')",
        dict(new, entry_id=entry_id, leg_n=n))
    if "control_desc" in d:          # the description of the control: only shown, nothing is computed from it
        save_control_desc(db, entry_id, n, d.get("control_desc"))
    db.commit()
    before = {k: (old[k] if old else (0 if k in ("deliberate_stop", "lost_contact") else None)) for k in MODEL_FIELDS}
    if e["has_routes"] and any(before[k] != new[k] for k in MODEL_FIELDS):
        jobs.enqueue(db, "refit_model", user_id=g.user["id"])
    if e["has_routes"] and new["planned"] and new["planned"] != (old["planned"] if old else None):
        jobs.enqueue(db, "price_plans", user_id=g.user["id"], entry_id=entry_id)
    return _legs_json(db, e)


@bp.route("/races/<int:entry_id>/legs/<int:n>/oprava", methods=["POST"])
@login_required
def leg_correction(entry_id, n):
    """"Opravit moji stopu": the line the runner drew where the GPS failed ({line: [[lat, lon], ...]}), or back to
    the GPS track ({line: null}). The routes of the race are found again with it (the leg stays out of the model)."""
    e = get_entry(entry_id)
    db = get_db()
    if not e["analysis_id"] or not db.execute("SELECT 1 FROM legs WHERE analysis_id = ? AND n = ?",
                                              (e["analysis_id"], n)).fetchone():
        abort(404)
    d = request.get_json(silent=True) or {}
    try:
        line = [_latlon(p) for p in d["line"]] if d.get("line") else None
        if line is not None and not 2 <= len(line) <= 500:
            raise ValueError
    except (ValueError, TypeError, IndexError, KeyError):
        abort(400)
    db.execute("INSERT INTO leg_notes (entry_id, leg_n, corrected) VALUES (?, ?, ?)"
               " ON CONFLICT (entry_id, leg_n) DO UPDATE SET corrected = excluded.corrected, updated_at = datetime('now')",
               (entry_id, n, dumps(line) if line else None))
    db.commit()
    if e["has_routes"]:
        jobs.enqueue(db, "analyse", user_id=g.user["id"], entry_id=entry_id, payload=dict(routes_only=True))
    return _legs_json(db, e)


@bp.route("/races/<int:entry_id>/refreshments", methods=["POST"])
@login_required
def refreshment_add(entry_id):
    """A refreshment point is shared by everyone at the event: stops next to it are deliberate for all."""
    e = get_entry(entry_id)
    db = get_db()
    d = request.get_json(silent=True) or {}
    try:
        lat, lon = _latlon([d["lat"], d["lon"]])
    except (ValueError, TypeError, KeyError):
        abort(400)
    if db.execute("SELECT COUNT(*) FROM refreshments WHERE event_id = ?", (e["event_id"],)).fetchone()[0] >= 20:
        abort(400)
    db.execute("INSERT INTO refreshments (event_id, lat, lon, created_by) VALUES (?,?,?,?)",
               (e["event_id"], lat, lon, g.user["id"]))
    db.commit()
    if e["has_routes"]:
        jobs.enqueue(db, "refit_model", user_id=g.user["id"])
    return _legs_json(db, e)


@bp.route("/races/<int:entry_id>/refreshments/<int:rid>", methods=["DELETE"])
@login_required
def refreshment_delete(entry_id, rid):
    e = get_entry(entry_id)
    db = get_db()
    if _own(db, "refreshments", rid, e["event_id"]):
        db.execute("DELETE FROM refreshments WHERE id = ?", (rid,))
        db.commit()
        if e["has_routes"]:
            jobs.enqueue(db, "refit_model", user_id=g.user["id"])
    return _legs_json(db, e)
