"""Official split times of a whole class: kept in `class_splits` (ORIS is asked once) and read for the race
page with oroute.splits (the WinSplits method). Works without a .fit and without a map."""
from oroute import splits as S

from .. import oris
from ..db import dumps, loads
from ..i18n import _
from . import charts


def store(con, class_id, raw):
    """Save the getSplits answer of a class (as ORIS sent it). Returns the parsed dict or None (no splits)."""
    data = oris.parse_class_splits(raw)
    if data is None:
        return None
    con.execute("INSERT INTO class_splits (class_id, data) VALUES (?, ?) ON CONFLICT (class_id) DO UPDATE SET"
                " data = excluded.data, fetched_at = datetime('now')", (class_id, dumps(data)))
    return data


def store_none(con, class_id):
    """Remember that ORIS has no split times for the class, so it is not asked again."""
    con.execute("INSERT OR IGNORE INTO class_splits (class_id, data) VALUES (?, ?)",
                (class_id, dumps(dict(control_codes=[], runners=[]))))


def load(con, class_id):
    row = con.execute("SELECT data FROM class_splits WHERE class_id = ?", (class_id,)).fetchone()
    return loads(row["data"]) if row else None


def leg_names(n):
    return [f"{'S' if k == 1 else k - 1}-{'F' if k == n else k}" for k in range(1, n + 1)]


def table(con, class_id, regno):
    """oroute.splits.class_table of the class, or None when it has no stored splits."""
    data = load(con, class_id)
    if not data or not data["runners"]:
        return None
    t = S.class_table(data["runners"], regno)
    t["control_codes"] = data["control_codes"]
    return t if t["n_legs"] else None


def by_leg(t):
    """{leg number: what the leg table of the map page shows} for the runner `me` of a class table."""
    if t is None or t["me"] is None:
        return {}
    return {k + 1: dict(loss=l["loss"], mistake=l["mistake"], index=l["index"], ref=l["ref"])
            for k, l in enumerate(t["runners"][t["me"]]["analysis"]["legs"]) if l["loss"] is not None}


def agreement(t, model_times):
    """Does the speed model order the legs as the class does (oroute.splits.rank_agreement), with Czech wording.
    model_times: model time of the best route per leg, or None."""
    if t is None or not model_times or len(model_times) != t["n_legs"]:
        return None
    a = S.rank_agreement(model_times, t["ref"], leg_names(t["n_legs"]))
    if a is None or a["rho"] is None:
        return None
    a["verdict"] = (_("model řadí úseky stejně jako kategorie") if a["rho"] >= 0.9 else
                    _("model řadí úseky podobně jako kategorie") if a["rho"] >= 0.75 else
                    _("model řadí úseky jinak než kategorie, ber nejlepší postupy s rezervou"))
    for l in a["legs"]:
        pct = (l["dev"] - 1) * 100
        l["pct"] = pct
        l["text"] = (_("kategorie tu potřebuje o %.0f %% víc času, než odpovídá modelu: model je optimistický "
                         "(špatně přečtená mapa, zakázaný průchod, nebo těžká dohledávka)") % pct if pct >= 25 else
                     _("kategorie je tu o %.0f %% rychlejší, než odpovídá modelu: model je pesimistický (terén "
                         "je průběžnější, než říká mapa, nebo vede lepší postup)") % -pct if pct <= -20 else "")
    a["outliers"] = [l for l in a["legs"] if l["text"]][:5]
    return a


def view(con, entry, regno, model_times=None):
    """Everything the tab "Mezičasy kategorie" shows, or None when the class has no stored splits."""
    t = table(con, entry["class_id"], regno)
    if t is None:
        return None
    n, names, me = t["n_legs"], leg_names(t["n_legs"]), t["me"]
    codes = t["control_codes"] + [""] * n
    runners = sorted(t["runners"], key=lambda r: (r["time_s"] is None, r["time_s"] or 0, r["cum"][-1] or 0))
    winner = next((r["time_s"] for r in runners if r["time_s"] is not None), None)
    out = dict(n_legs=n, n_runners=len(t["runners"]), n_ok=sum(r["time_s"] is not None for r in t["runners"]),
               superman=t["superman"], winner=winner, me=None, legs=[], chart=None, bars=None,
               agreement=agreement(t, model_times),
               runners=[dict(place=r["place"], name=r["name"], club=r["club"], time_s=r["time_s"], status=r["status"],
                             behind=(r["time_s"] - winner) if r["time_s"] is not None and winner else None,
                             normal=r["analysis"]["normal"], mistakes=r["analysis"]["mistakes"],
                             n_mistakes=sum(l["mistake"] for l in r["analysis"]["legs"]),
                             me=me is not None and r is t["runners"][me]) for r in runners])
    mistakes = []
    if me is not None:
        mine = t["runners"][me]
        a = mine["analysis"]
        mistakes = [k + 1 for k, l in enumerate(a["legs"]) if l["mistake"]]
        out["me"] = dict(name=mine["name"], normal=a["normal"], mistakes=a["mistakes"], n_mistakes=len(mistakes),
                         clean=a["clean"], time_s=mine["time_s"], place=mine["place"])
        for k, l in enumerate(a["legs"]):
            out["legs"].append(dict(n=k + 1, name=names[k], code=codes[k], time=l["time"], ref=l["ref"],
                                    best=t["best"][k], rank=t["ranks"][k], index=l["index"],
                                    expected=l["expected"], loss=l["loss"], mistake=l["mistake"]))
        out["bars"] = charts.bars_chart([l["loss"] for l in a["legs"]], names, set(m - 1 for m in mistakes),
                                        ylabel=_("ztráta proti tvému normálu"),
                                        title=_("Ztráta na úsecích proti tvému normálnímu výkonu"))
    else:
        for k in range(n):
            out["legs"].append(dict(n=k + 1, name=names[k], code=codes[k], time=None, ref=t["ref"][k],
                                    best=t["best"][k], rank=None, index=None, expected=None, loss=None, mistake=False))
    out["chart"] = charts.splits_chart(t["runners"], t["ref_cum"], me, mistakes)
    return out
