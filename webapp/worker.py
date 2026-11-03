"""Background worker: runs the queued jobs (ORIS sync, imports, analysis, model refit).

    python -m webapp.worker          keep running, look for new jobs every 2 s (Docker)
    python -m webapp.worker --once   run what is waiting and exit (cron on the club server)
"""
import argparse
import time
import traceback

from . import db as dbm
from . import i18n
from .config import Config
from .services import jobs


class Ctx:
    """What a job handler gets: settings and its own database connection."""

    def __init__(self, conf):
        self.conf = conf
        self.con = dbm.connect(conf.db_path)


def load_handlers():
    from .services import handlers  # noqa: F401  (registers itself in jobs.HANDLERS)


def run_once(conf):
    """Run every waiting job. Returns how many ran."""
    ctx = Ctx(conf)
    n = 0
    while True:
        job = jobs.claim(ctx.con)
        if job is None:
            break
        n += 1
        jobs.watch(conf.db_path, job["id"])
        try:
            fn = jobs.HANDLERS.get(job["kind"])
            if fn is None:
                raise RuntimeError(f"unknown job kind {job['kind']!r}")
            with i18n.use(job["lang"]):   # the sentences it stores are in the language of the page that started it
                jobs.finish(ctx.con, job["id"], fn(ctx, job))
        except jobs.Stopped:             # the runner stopped it: what was half done is gone (services/runner.py)
            ctx.con.rollback()
            jobs.stopped(ctx.con, job["id"])
        except jobs.Refused as e:        # what the user gave cannot be used: the sentence says why
            ctx.con.rollback()
            jobs.fail(ctx.con, job["id"], str(e))
        except Exception as e:  # a failed job must not stop the queue
            ctx.con.rollback()
            # the first line is what the page shows; the rest (cut from the front) goes under "Podrobnosti"
            first, _nl, rest = f"{e}\n\n{traceback.format_exc()}".partition("\n")
            jobs.fail(ctx.con, job["id"], first + "\n" + rest[-4000:])
            print(f"job {job['id']} ({job['kind']}) failed: {e}", flush=True)
        finally:
            jobs.unwatch()
    ctx.con.close()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run the waiting jobs and exit")
    a = ap.parse_args()
    conf = Config()
    dbm.init(conf.db_path)
    load_handlers()
    con = dbm.connect(conf.db_path)
    # from cron an earlier run may still be busy with a long job, so only take back what is clearly dead
    jobs.requeue_interrupted(con, older_than_min=30 if a.once else 0)
    con.close()
    if a.once:
        run_once(conf)
        return
    print("worker started", flush=True)
    while True:
        if not run_once(conf):
            time.sleep(2)


if __name__ == "__main__":
    main()
