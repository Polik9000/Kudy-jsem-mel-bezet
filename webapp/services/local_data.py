"""The data folder of the app on one's own computer: open it, wipe it (TODO 41)."""
import os
import shutil
import subprocess
import sys

from .. import db as dbm

KEEP = ("secret_key",)          # the session key: the open page stays valid after the wipe
CONFIRM = "SMAZAT"


class Busy(RuntimeError):
    """Something is being computed; wiping now would pull the files from under it."""


def open_folder(path):
    """Show the folder in the file manager. False when there is none (a server without a screen)."""
    try:
        if sys.platform == "win32":
            os.startfile(path)      # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def wipe(con, conf):
    """Delete every race, run, map, analysis and model, in the database and on disk. The tables stay (the app
    keeps running, the one local runner is made again on the next page). Raises Busy while a job runs."""
    if con.execute("SELECT 1 FROM jobs WHERE status IN ('queued', 'running')").fetchone():
        raise Busy("Teď se něco počítá. Počkej, až úlohy doběhnou (nebo je zastav), a zkus to znovu.")
    con.commit()
    con.execute("PRAGMA foreign_keys = OFF")
    tables = con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    for (table,) in tables:
        con.execute(f'DELETE FROM "{table}"')
    con.commit()
    con.execute("PRAGMA foreign_keys = ON")
    for name in os.listdir(conf.instance):
        if name in KEEP or name.startswith(os.path.basename(conf.db_path)):
            continue
        p = conf.path(name)
        if os.path.isdir(p) and not os.path.islink(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except OSError:
                pass
    dbm.init(conf.db_path)
