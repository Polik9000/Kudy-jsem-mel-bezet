"""What the race page shows: the stored analysis read through the runner's notes (oroute.annotations)."""
from .. import texts
from ..db import loads
from . import personal

NOTE_FIELDS = ("planned", "deliberate_stop", "lost_contact", "green", "fatigue", "text")


def note_dict(row):
    if row is None:
        return dict(planned=None, plan=None, deliberate_stop=False, lost_contact=False, green=None, fatigue=None,
                    text="", corrected=None, control_desc="")
    return dict(planned=loads(row["planned"]), plan=loads(row["plan"]), deliberate_stop=bool(row["deliberate_stop"]),
                lost_contact=bool(row["lost_contact"]), green=row["green"], fatigue=row["fatigue"],
                text=row["text"] or "", corrected=loads(row["corrected"]), control_desc=row["control_desc"] or "")


def official_splits(entry):
    """Official time of each leg (s) from the cumulative ORIS times; None where a punch is missing."""
    cum = loads(entry["splits"])
    if not cum:
        return []
    out, prev = [], 0
    for c in cum:
        out.append(None if c is None or prev is None else c - prev)
        prev = c
    return out


def legs_view(con, entry, analysis, event_id, ws=None, geometry=True):
    """Legs of the analysis with losses, Czech signals and notes, plus the totals by cause.
    ws: {leg number: loss by the class split times} (services.splits.by_leg), shown next to the GPS numbers.
    geometry=False leaves out the lines of the routes (best_route, alts, the average runner's route): a note
    changes the numbers of a leg, never its routes, and the page already has them."""
    ws = ws or {}
    summary = loads(analysis["summary"], {})
    reads, _ = personal.leg_reads(con, entry["id"], analysis["id"], event_id)
    notes = {r["leg_n"]: r for r in con.execute("SELECT * FROM leg_notes WHERE entry_id = ?", (entry["id"],))}
    official = official_splits(entry)
    legs = []
    ws_legs = ws.pop("n_legs", None) if ws else None
    totals = dict(route=0.0, mistake=0.0, fatigue=0.0, deliberate=0.0)
    for r in con.execute("SELECT * FROM legs WHERE analysis_id = ? ORDER BY n", (analysis["id"],)):
        d, rd = loads(r["data"]), reads[r["n"]]
        for k in totals:
            totals[k] += rd["parts"][k]
        legs.append(dict(
            n=r["n"], name=r["name"], a=d["a"], b=d["b"], time=d["time"],
            official=official[r["n"] - 1] if len(official) == len(reads) else None,
            straight=d["straight"], run=d["run"], climb=d["climb"], stop_time=d["stop_time"], stops=d["stops"],
            best=d.get("best"), line=d.get("line"), est_loss=rd["est_loss"],
            loss_total=rd["loss_total"], loss_route=rd["loss_route"], loss_exec=rd["loss_exec"],
            parts=rd["parts"], deliberate_s=rd["deliberate_s"], refreshment_s=rd["refreshment_s"],
            in_model=rd["in_model"], loss=rd["parts"]["route"] + rd["parts"]["mistake"] + rd["parts"]["fatigue"],
            flags=texts.flags(d, summary.get("vref") or 0.0, rd["deliberate_s"]),
            explain=r["explain_cs"], best_route=loads(r["best_route"]), note=note_dict(notes.get(r["n"])),
            ws=ws.get(r["n"]) if len(ws) and len(reads) == ws_legs else None,
            alts=d.get("alts") or [], balanced=bool(d.get("balanced")), crossed=texts.crossed(d.get("crossed")),
            # a leg drawn by hand: the shape of its GPS track says nothing, so no kind of mistake from it
            mistake=None if d.get("corrected") else texts.mistake(d.get("mistake"), rd, notes.get(r["n"])),
            corrected=bool(d.get("corrected")), gps_trouble=texts.gps_trouble(d.get("gps_trouble")),
            # the attack point of an analysis from before oroute/relocate.py was the nearest junction, whatever
            # side of the control it lay on: not shown
            attack=texts.attack(d.get("attack")) if d.get("relocate") else None,
            beyond=texts.beyond(d.get("beyond")), relocate=texts.relocate(d.get("relocate")),
            generic=d.get("generic")))
        if not geometry:
            del legs[-1]["best_route"], legs[-1]["alts"]
            if legs[-1]["generic"]:
                legs[-1]["generic"] = {k: v for k, v in legs[-1]["generic"].items() if k != "route"}
    return legs, totals
