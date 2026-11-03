"""Job queue in the `jobs` table: the web process adds rows, webapp.worker takes them one by one.

Stopping: the web process cannot reach the worker (another process, in Docker another container), so it only
marks the job (jobs.stop_requested). A waiting job is stopped at once; a running one stops at the worker's next
look at the mark: every progress() of the job and every second while a script of the analysis runs
(services/runner._run kills the script)."""
import sqlite3

from .. import i18n
from ..db import dumps, loads
from ..i18n import _

HANDLERS = {}  # job kind -> function(ctx, job) returning an optional message for the job list
# the jobs that take minutes: the worker takes every other waiting job before them
HEAVY_SQL = "(kind IN ('analyse', 'recompute_all'))"


class Refused(Exception):
    """A job that cannot be done because of what the user gave it (a photo that cannot be placed...): the message
    is a sentence for the job list, and nothing else is kept (no traceback under "Podrobnosti")."""


class Stopped(Exception):
    """The runner asked to stop the job: whatever it was doing is left out, nothing half done is kept."""


def handler(kind):
    """Register the function that runs jobs of this kind (see services/handlers.py)."""
    def reg(fn):
        HANDLERS[kind] = fn
        return fn
    return reg


def enqueue(con, kind, user_id=None, entry_id=None, payload=None):
    """Add a job unless the same one is already waiting. Returns the job id."""
    body = dumps(payload) if payload is not None else None
    row = con.execute(
        "SELECT id FROM jobs WHERE status = 'queued' AND kind = ? AND user_id IS ? AND entry_id IS ? AND payload IS ?",
        (kind, user_id, entry_id, body)).fetchone()
    if row:
        return row["id"]
    cur = con.execute("INSERT INTO jobs (kind, user_id, entry_id, payload, lang) VALUES (?, ?, ?, ?, ?)",
                      (kind, user_id, entry_id, body, i18n.lang()))
    con.commit()
    return cur.lastrowid


def claim(con):
    """Take the oldest waiting job and mark it running (BEGIN IMMEDIATE: safe with several workers).
    Quick jobs (ORIS, imports, model refit) go before analyses, which take minutes each."""
    con.execute("BEGIN IMMEDIATE")
    row = con.execute(f"SELECT * FROM jobs WHERE status = 'queued' ORDER BY {HEAVY_SQL}, id LIMIT 1").fetchone()
    if row:
        con.execute("UPDATE jobs SET status = 'running', started_at = datetime('now') WHERE id = ?", (row["id"],))
    con.commit()
    return row


def progress(con, job_id, text):
    """What a running job is doing right now (the job list and the race page show it). Raises Stopped when the
    runner asked to stop the job."""
    con.execute("UPDATE jobs SET message = ? WHERE id = ? AND status = 'running'", (text, job_id))
    con.commit()
    row = con.execute("SELECT stop_requested FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is not None and row["stop_requested"]:
        raise Stopped()


def stop(con, job_id, user_id):
    """Stop one of the user's jobs: a waiting one at once, a running one by the mark the worker looks at.
    Returns 'stopped', 'stopping', or None when the user has no such waiting or running job."""
    row = con.execute("SELECT status FROM jobs WHERE id = ? AND user_id = ? AND status IN ('queued', 'running')",
                      (job_id, user_id)).fetchone()
    if row is None:
        return None
    if row["status"] == "queued":
        con.execute("UPDATE jobs SET status = 'stopped', message = ?, finished_at = datetime('now')"
                    " WHERE id = ? AND status = 'queued'", (_("Zastaveno, než začala."), job_id))
    con.execute("UPDATE jobs SET stop_requested = 1 WHERE id = ?", (job_id,))
    con.commit()
    return "stopped" if row["status"] == "queued" else "stopping"


def stop_all(con, user_id):
    """Stop every waiting and running job of the user. Returns how many."""
    ids = [r["id"] for r in con.execute("SELECT id FROM jobs WHERE user_id = ? AND status IN ('queued', 'running')",
                                        (user_id,))]
    return sum(stop(con, i, user_id) is not None for i in ids)


def stopped(con, job_id):
    con.execute("UPDATE jobs SET status = 'stopped', message = ?, finished_at = datetime('now') WHERE id = ?",
                (_("Zastaveno. Hotové části zůstaly, rozpracované se zahodily."), job_id))
    con.commit()


# the job the worker of this process runs now, for stop_wanted (any thread: it opens its own connection)
_current = {}


def watch(db_path, job_id):
    _current.update(db=db_path, id=job_id)


def unwatch():
    _current.clear()


def stop_wanted():
    """True when the runner asked to stop the job the worker runs now (False outside a job)."""
    if not _current:
        return False
    try:
        con = sqlite3.connect(_current["db"], timeout=5)
        try:
            row = con.execute("SELECT stop_requested FROM jobs WHERE id = ?", (_current["id"],)).fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        return False
    return bool(row and row[0])


def finish(con, job_id, message=None):
    con.execute("UPDATE jobs SET status = 'done', message = ?, finished_at = datetime('now') WHERE id = ?",
                (message, job_id))
    con.commit()


def fail(con, job_id, error):
    con.execute("UPDATE jobs SET status = 'failed', error = ?, finished_at = datetime('now') WHERE id = ?",
                (error, job_id))
    con.commit()


def requeue_interrupted(con, older_than_min=0):
    """Jobs left 'running' by a worker that was stopped go back to the queue.
    older_than_min: leave younger ones alone (another cron run may still be working on them)."""
    since = (f"-{int(older_than_min)} minutes",)
    # ... unless the runner asked to stop them: those are stopped (nothing stays "running")
    con.execute("UPDATE jobs SET status = 'stopped', message = ?, finished_at = datetime('now')"
                " WHERE status = 'running' AND stop_requested = 1 AND started_at <= datetime('now', ?)",
                (_("Zastaveno."), *since))
    con.execute("UPDATE jobs SET status = 'queued', started_at = NULL WHERE status = 'running' "
                "AND started_at <= datetime('now', ?)", since)
    con.commit()


def payload(job):
    return loads(job["payload"], {})
