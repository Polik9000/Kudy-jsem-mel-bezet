"""The daily jobs of a club server, for a server without cron (the service "cron" of docker-compose.yml, off
unless started with --profile cron): python -m webapp.cron [--once]

Every day at OB_CRON_AT (default 04:30, time of OB_CRON_TZ, default Europe/Prague):
  OB_CRON_ORIS=1    the new races of every account from ORIS (flask sync-oris-all; default 1)
  OB_CRON_BACKUP=1  a backup of the database and the uploaded files (flask backup; default 1)
--once runs the jobs now, once, and ends. A host with cron does not need this: see docs/provoz.md.
"""
import argparse
import datetime as dt
import os
import sys
import time
import traceback
from zoneinfo import ZoneInfo

from . import db as dbm
from .config import Config


def next_run(now, at="04:30"):
    """The next time of day `at` (HH:MM) after `now` (aware datetime)."""
    h, m = (int(x) for x in at.split(":"))
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return t if t > now else t + dt.timedelta(days=1)


def run_jobs(conf, log=print):
    """The jobs that are switched on, each on its own: one failing does not stop the other."""
    from .services import backup, sync_oris
    if os.environ.get("OB_CRON_ORIS", "1") != "0":
        try:
            con = dbm.connect(conf.db_path)
            try:
                r = sync_oris.sync_all(con, conf, log=log)
            finally:
                con.close()
            log(f"ORIS: {r['done']} accounts loaded, {r['skipped']} loaded recently, {r['failed']} failed")
        except Exception:
            log("ORIS: " + traceback.format_exc())
    if os.environ.get("OB_CRON_BACKUP", "1") != "0":
        try:
            r = backup.backup(conf)
            log(f"backup: {r['db']}, {r['files']} files ({r['copied']} copied)")
        except Exception:
            log("backup: " + traceback.format_exc())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--once", action="store_true", help="run the jobs now and end")
    a = ap.parse_args(argv)
    conf = Config()
    dbm.init(conf.db_path)
    log = lambda s: print(f"{dt.datetime.now():%Y-%m-%d %H:%M} {s}", flush=True)
    if a.once:
        run_jobs(conf, log)
        return 0
    tz = ZoneInfo(os.environ.get("OB_CRON_TZ", "Europe/Prague"))
    at = os.environ.get("OB_CRON_AT", "04:30")
    while True:
        t = next_run(dt.datetime.now(tz), at)
        log(f"next run {t:%Y-%m-%d %H:%M %Z}")
        while dt.datetime.now(tz) < t:          # in steps, so that a clock change or a sleeping host is caught up
            time.sleep(min(600.0, max(1.0, (t - dt.datetime.now(tz)).total_seconds())))
        run_jobs(conf, log)


if __name__ == "__main__":
    sys.exit(main())
