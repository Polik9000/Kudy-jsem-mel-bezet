"""The routes a runner planned for the legs of a race (leg_notes.planned, drawn on the map), priced by the
speed model with oroute/planned.py: the same terrain, elevation and model the analysis of the race used.

The numbers are kept next to the line (leg_notes.plan). They are worked out by the worker right after a line
is saved (job price_plans: the map and the elevation take a few seconds to load) and again after every
analysis of the race; a line that changes or goes loses them at once."""
import json
import os

from ..db import dumps, loads
from . import results, runner


def pending(con, entry_id):
    """True while the planned routes of the entry are about to be priced (or priced again by an analysis)."""
    return bool(con.execute("SELECT 1 FROM jobs WHERE entry_id = ? AND kind IN ('price_plans', 'analyse')"
                            " AND status IN ('queued', 'running')", (entry_id,)).fetchone())


def price(con, conf, entry_id, again=False):
    """Price the planned routes of the entry that have no numbers yet (again=True: all of them, after a new
    analysis). Returns how many were priced. Without best routes there is nothing to price them with."""
    if again:
        con.execute("UPDATE leg_notes SET plan = NULL WHERE entry_id = ?", (entry_id,))
        con.commit()
    rows = con.execute("SELECT leg_n, planned FROM leg_notes WHERE entry_id = ? AND planned IS NOT NULL"
                       " AND plan IS NULL ORDER BY leg_n", (entry_id,)).fetchall()
    info = runner.entry_info(con, entry_id)
    a = con.execute("SELECT out_dir FROM analyses WHERE entry_id = ? AND has_routes = 1", (entry_id,)).fetchone()
    if not rows or a is None or info is None or not runner.has_terrain_map(info):
        return 0
    out = conf.path(a["out_dir"])
    asked, got = os.path.join(out, "best", "plans.json"), os.path.join(out, "best", "plans_priced.json")
    with open(asked, "w", encoding="utf-8") as f:
        json.dump(dict(legs=[dict(leg=r["leg_n"], planned=loads(r["planned"])) for r in rows]), f)
    runner.run_planned(conf, info, out, asked, got)
    with open(got, encoding="utf-8") as f:
        priced = {l["leg"]: l for l in json.load(f)["legs"]}
    n = 0
    for r in rows:
        p = priced.get(r["leg_n"])
        if p is None:
            continue
        plan = dict(results.route(p["plan"]), delta=p["delta"], off_m=p["off_m"], text=p["text_cs"],
                    text_en=p.get("text_en"), crossed=[c["at"] for c in p.get("crossed") or []])
        # only when the line is still the one that was priced (it may have been drawn again meanwhile)
        n += con.execute("UPDATE leg_notes SET plan = ? WHERE entry_id = ? AND leg_n = ? AND planned = ?",
                         (dumps(plan), entry_id, r["leg_n"], r["planned"])).rowcount
    con.commit()
    return n
