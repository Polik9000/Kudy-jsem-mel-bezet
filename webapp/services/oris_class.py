"""The class a runner really ran, chosen by the runner: another class of a race from ORIS ("I ran another class"),
or a race from ORIS they are not entered in under their registration number. ORIS is asked sparingly: one
getEvent per race (all its classes are kept) and one getSplits per class (kept in class_splits), never again
for what the database already holds."""
import re
import time

from .. import oris
from ..db import dumps
from ..i18n import _
from . import matching, regnos, stages
from . import splits as class_splits
from .sync_oris import PAUSE_S, upsert_class, upsert_event


class Refused(ValueError):
    """What the runner asked for cannot be done; the message is Czech and goes to the page."""


def parse_ref(text):
    """The ORIS id of a race from what the runner typed: the id itself or a link to ORIS (…/Zavod?id=1234)."""
    t = (text or "").strip()
    m = re.search(r"[?&]id=(\d+)", t) or re.fullmatch(r"#?(\d{1,7})", t)
    return int(m.group(1)) if m else None


def event_classes(con, event_id):
    return con.execute("SELECT * FROM classes WHERE event_id = ? AND oris_id IS NOT NULL ORDER BY name",
                       (event_id,)).fetchall()


def _ask_event(client, oris_id):
    try:
        return client.event(oris_id)
    except (oris.OrisError, KeyError, TypeError, ValueError) as e:
        raise Refused(_("Závod %(oris_id)s se z ORIS načíst nepodařilo. Je číslo závodu správně?", oris_id=oris_id)) from e


def _save(con, ev):
    event_id = upsert_event(con, ev)
    for c in ev["classes"]:
        upsert_class(con, event_id, c)
    return event_id


def load_event(con, conf, oris_id, client=None, pause=PAUSE_S):
    """events.id of the race from ORIS with all its classes. getEvent is asked only when the race, or more than
    the one class a runner was entered in, is not in the database yet. The umbrella of a multi-stage event is no
    race (services/stages.py): its stages are loaded instead and None is returned (race_oris_class offers them)."""
    client = client or oris.client(conf)
    umb = stages.known(con, oris_id)
    if umb is None:
        row = con.execute("SELECT id FROM events WHERE oris_id = ?", (oris_id,)).fetchone()
        if row and len(event_classes(con, row["id"])) > 1 and not stages.suspect(con, row["id"]):
            return row["id"]
        ev = _ask_event(client, oris_id)
        if ev["cancelled"]:
            raise Refused(_("Závod %(name)s je v ORIS zrušený.", name=ev['name']))
        if not ev["stages"]:
            if row:
                stages.not_umbrella(con, row["id"])
            event_id = _save(con, ev)
            con.commit()
            return event_id
        umb = stages.remember(con, ev)
    for sid in umb["stages"]:
        row = con.execute("SELECT id FROM events WHERE oris_id = ?", (sid,)).fetchone()
        if row and len(event_classes(con, row["id"])) > 1:
            continue
        time.sleep(pause)
        try:
            sev = _ask_event(client, sid)
        except Refused:
            continue          # one stage ORIS does not give: the others can still be chosen
        if not sev["cancelled"]:
            _save(con, sev)
    stages.mark(con, oris_id, umb["stages"])
    con.commit()
    return None


def runner_times(con, conf, cls, regnos, client=None):
    """The runner's official times in a class from ORIS (dict as oris.parse_splits gives it), or None when the
    class has no split times or the runner is not in its results. getSplits is asked once per class."""
    data = class_splits.load(con, cls["id"])
    if data is None:
        try:
            raw = (client or oris.client(conf)).class_splits_raw(cls["oris_id"])
        except oris.OrisError:
            return None             # the times can come later (sync of ORIS); the class is chosen anyway
        data = class_splits.store(con, cls["id"], raw)
        if data is None:
            class_splits.store_none(con, cls["id"])
            return None
    mine = oris.numbers(regnos)
    me = next((r for r in data["runners"] if (r["regno"] or "").upper() in mine), None)
    if me is None:
        return None
    return dict(control_codes=data["control_codes"], start_local=me["start_local"], time_s=me["time_s"],
                place=me["place"], cumulative=me["cum"][:-1] + [me["time_s"]])


def _put_times(con, entry_id, cls, t):
    if t:
        con.execute("UPDATE entries SET official_time_s=?, start_local=?, result_place=?, splits=? WHERE id=?",
                    (t["time_s"], t["start_local"], t["place"],
                     dumps(t["cumulative"]) if t["time_s"] is not None else None, entry_id))
        con.execute("UPDATE classes SET control_codes = ? WHERE id = ?", (dumps(t["control_codes"]),
                                                                          cls["id"]))
    else:
        con.execute("UPDATE entries SET official_time_s=NULL, start_local=NULL, result_place=NULL, splits=NULL"
                    " WHERE id=?", (entry_id,))


def change_class(con, conf, user, entry_id, class_id, client=None):
    """Move the runner's entry of a race from ORIS to another class of the same race; its official times come
    from that class, the analysis of the old class (another course) and the notes of its legs go, and the
    entry is analysed again. Returns a Czech message."""
    e = con.execute("SELECT e.*, c.event_id, c.id AS cid FROM entries e JOIN classes c ON c.id = e.class_id"
                    " WHERE e.id = ? AND e.user_id = ?", (entry_id, user["id"])).fetchone()
    cls = con.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    if e is None or cls is None or cls["event_id"] != e["event_id"] or cls["oris_id"] is None:
        raise Refused(_("Taková kategorie u závodu není."))
    if cls["id"] == e["cid"]:
        con.execute("UPDATE entries SET class_chosen = 1 WHERE id = ?", (entry_id,))
        con.commit()
        return _("Kategorie %(name)s zůstává.", name=cls['name'])
    if con.execute("SELECT 1 FROM entries WHERE user_id = ? AND class_id = ?", (user["id"], cls["id"])).fetchone():
        raise Refused(_("Závod v kategorii %(name)s už mezi svými závody máš.", name=cls['name']))
    t = runner_times(con, conf, cls, regnos.of(con, user["id"]), client)
    con.execute("UPDATE entries SET class_id = ?, class_chosen = 1 WHERE id = ?", (cls["id"], entry_id))
    _put_times(con, entry_id, cls, t)
    con.execute("DELETE FROM analyses WHERE entry_id = ?", (entry_id,))      # the legs of another course
    con.execute("DELETE FROM leg_notes WHERE entry_id = ?", (entry_id,))
    con.commit()
    matching.queue_analysis(con, entry_id)
    return (_("Kategorie změněna na %(name)s. ", name=cls['name'])
            + (_("Oficiální čas a mezičasy jsou z jejích výsledků.") if t and t["time_s"] is not None
               else _("Ve výsledcích této kategorie v ORIS nejsi, mezičasy se vezmou z GPS.")))


def add_race(con, conf, user, class_id, client=None):
    """A race from ORIS the runner is not entered in under their number, in the class they choose. Returns
    (entry id, Czech message); a race the runner already has gives that entry."""
    cls = con.execute("SELECT * FROM classes WHERE id = ? AND oris_id IS NOT NULL", (class_id,)).fetchone()
    if cls is None:
        raise Refused(_("Taková kategorie u závodu není."))
    have = con.execute("SELECT e.id FROM entries e JOIN classes c ON c.id = e.class_id"
                       " WHERE e.user_id = ? AND c.event_id = ? ORDER BY e.id LIMIT 1",
                       (user["id"], cls["event_id"])).fetchone()
    if have:
        return have["id"], _("Tenhle závod už mezi svými závody máš; kategorii změníš na jeho stránce.")
    t = runner_times(con, conf, cls, regnos.of(con, user["id"]), client)
    entry_id = con.execute("INSERT INTO entries (user_id, class_id, class_chosen) VALUES (?, ?, 1)",
                           (user["id"], cls["id"])).lastrowid
    _put_times(con, entry_id, cls, t)
    con.commit()
    matching.match_user(con, user["id"])
    return entry_id, (_("Závod přidán v kategorii %(name)s. ", name=cls['name'])
                      + (_("Oficiální čas a mezičasy jsou z ORIS.") if t and t["time_s"] is not None
                         else _("Ve výsledcích této kategorie v ORIS nejsi, mezičasy se vezmou z GPS.")))
