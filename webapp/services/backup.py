"""Backups of the database and of the uploaded files that cannot be got again (flask backup, flask restore).

A backup is three things in OB_BACKUP_DIR (default: the folder backups/ in the instance folder; better a disk
or a folder outside it, see docs/provoz.md):
  ob-YYYY-MM-DD_HHMM.db           a copy of the database (SQLite's own backup: consistent while the web pages
                                  and the worker write to it), checked with PRAGMA integrity_check
  ob-YYYY-MM-DD_HHMM-soubory.txt  the list of the uploaded files it refers to that cannot be got again: the
                                  .fit files, the maps (with and without course), the photos of maps, the
                                  course placed from a photo and the own slope from a Garmin export (the
                                  export itself is deleted after the import); size and SHA-1 of each
  soubory/                        a mirror of those files: a file is copied when it is new or changed, and
                                  removed when no kept backup lists it any more
Everything else in the instance folder is computed again from these (analyses, models, elevation, OSM).
Only the last `keep` backups are kept (OB_BACKUP_KEEP, default 14).

Restore (flask restore, with the web pages and the worker stopped): the database of a backup back into the
instance folder, and the files of its list from the mirror. The analyses are then offered to be redone.
"""
import datetime as dt
import glob
import hashlib
import os
import shutil
import sqlite3

import click
from flask import current_app
from flask.cli import with_appcontext

from .. import db as dbm

KEEP = 14
FILES = "soubory"
# the columns that name an uploaded file, and what it is (for the list)
UPLOADS = [("SELECT file FROM activities", "aktivita .fit"),
           ("SELECT maponly_file FROM events WHERE maponly_file IS NOT NULL", "mapa bez tratě"),
           ("SELECT course_file FROM classes WHERE course_file IS NOT NULL", "mapa s tratí"),
           ("SELECT file FROM photos", "fotka mapy"),
           ("SELECT slope_file FROM users WHERE slope_file IS NOT NULL", "vlastní sklon z exportu Garmin")]


def backup_dir(conf):
    return os.path.abspath(os.environ.get("OB_BACKUP_DIR") or conf.path("backups"))


def keep_count():
    try:
        return max(1, int(os.environ.get("OB_BACKUP_KEEP", KEEP)))
    except ValueError:
        return KEEP


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def uploads(con, conf):
    """[(relative path, what)] of the files the database refers to that cannot be got again."""
    from .storage import course_json
    out, seen = [], set()
    for sql, what in UPLOADS:
        for (rel,) in con.execute(sql):
            if rel and rel not in seen:
                seen.add(rel)
                out.append((rel, what))
            if what == "mapa s tratí" and rel and os.path.exists(conf.path(course_json(rel))):
                out.append((course_json(rel), "trať usazená z fotky"))   # (the points clicked on the photo)
    return out


def _listed(path):
    """The relative paths of a list of files of a backup."""
    with open(path, encoding="utf-8") as f:
        return [line.split("\t")[0] for line in f if line.strip() and not line.startswith("#")]


def backup(conf, dest=None, keep=None, now=None, files=True):
    """Make a backup (see the module). Returns dict(db, list, files, copied, missing, removed)."""
    dest = os.path.abspath(dest or backup_dir(conf))
    keep = keep or keep_count()
    os.makedirs(dest, exist_ok=True)
    stamp = (now or dt.datetime.now()).strftime("%Y-%m-%d_%H%M")
    db_out = os.path.join(dest, f"ob-{stamp}.db")
    tmp = db_out + ".tmp"
    src = dbm.connect(conf.db_path)
    try:
        out_con = sqlite3.connect(tmp)
        src.backup(out_con)
        ok = out_con.execute("PRAGMA integrity_check").fetchone()[0]
        out_con.close()
        if ok != "ok":
            raise RuntimeError(f"the copy of the database is damaged: {ok}")
        os.replace(tmp, db_out)
        listed = uploads(src, conf)
    finally:
        src.close()
        if os.path.exists(tmp):
            os.remove(tmp)
    mirror = os.path.join(dest, FILES)
    copied, missing, lines = 0, [], []
    for rel, what in listed:
        path = conf.path(rel)
        if not os.path.exists(path):
            missing.append(rel)
            lines.append(f"{rel}\t-\t-\t{what}\tCHYBÍ")
            continue
        size = os.path.getsize(path)
        lines.append(f"{rel}\t{size}\t{_sha1(path)}\t{what}")
        if files:
            target = os.path.join(mirror, rel)
            if not os.path.exists(target) or os.path.getsize(target) != size \
                    or os.path.getmtime(target) < os.path.getmtime(path):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(path, target)
                copied += 1
    list_out = db_out[:-3] + "-soubory.txt"
    with open(list_out, "w", encoding="utf-8") as f:
        f.write(f"# záloha {stamp}: soubory, které nejdou znovu získat "
                "(cesta ve složce instance, velikost, SHA-1, co to je)\n")
        f.write("\n".join(lines) + ("\n" if lines else ""))
    # only the last `keep` backups stay, and the mirror keeps what one of them lists
    dbs = sorted(glob.glob(os.path.join(dest, "ob-*.db")))
    for old in dbs[:-keep]:
        os.remove(old)
        if os.path.exists(old[:-3] + "-soubory.txt"):
            os.remove(old[:-3] + "-soubory.txt")
    removed = 0
    if files and os.path.isdir(mirror):
        wanted = set()
        for lst in glob.glob(os.path.join(dest, "ob-*-soubory.txt")):
            wanted.update(os.path.normpath(r) for r in _listed(lst))
        for root, _, names in os.walk(mirror):
            for n in names:
                rel = os.path.normpath(os.path.relpath(os.path.join(root, n), mirror))
                if rel not in wanted:
                    os.remove(os.path.join(root, n))
                    removed += 1
    return dict(db=db_out, list=list_out, files=len(listed), copied=copied, missing=missing, removed=removed)


def restore(conf, db_file, files_dir=None):
    """The database of a backup into the instance folder, and the files of its list from files_dir (default:
    the mirror next to it). Returns dict(files, restored, missing). The web pages and the worker must not run."""
    db_file = os.path.abspath(db_file)
    with sqlite3.connect(db_file) as c:
        ok = c.execute("PRAGMA integrity_check").fetchone()[0]
    if ok != "ok":
        raise RuntimeError(f"the backup {db_file} is damaged: {ok}")
    for extra in ("-wal", "-shm"):            # what is left of the old database must not be mixed into it
        if os.path.exists(conf.db_path + extra):
            os.remove(conf.db_path + extra)
    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(conf.db_path)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    dbm.init(conf.db_path)                    # (a backup from an older version gets the new columns)
    files_dir = files_dir or os.path.join(os.path.dirname(db_file), FILES)
    lst = db_file[:-3] + "-soubory.txt"
    listed = _listed(lst) if os.path.exists(lst) else []
    restored, missing = 0, []
    for rel in listed:
        src_file = os.path.join(files_dir, rel)
        if not os.path.exists(src_file):
            if not os.path.exists(conf.path(rel)):
                missing.append(rel)
            continue
        os.makedirs(os.path.dirname(conf.path(rel)), exist_ok=True)
        shutil.copy2(src_file, conf.path(rel))
        restored += 1
    return dict(files=len(listed), restored=restored, missing=missing)


@click.command("backup")
@click.option("--to", "dest", help="the folder of the backups (default: OB_BACKUP_DIR, else backups/ in the instance)")
@click.option("--keep", type=int, help=f"how many backups to keep (default: OB_BACKUP_KEEP, else {KEEP})")
@click.option("--no-files", is_flag=True, help="only the database and the list, no copies of the files")
@with_appcontext
def backup_command(dest, keep, no_files):
    """Back up the database and the uploaded files that cannot be got again."""
    r = backup(current_app.config["OB"], dest, keep, files=not no_files)
    click.echo(f"database: {r['db']}")
    click.echo(f"list of {r['files']} files: {r['list']} ({r['copied']} copied, {r['removed']} no longer needed removed)")
    if r["missing"]:
        click.echo(f"missing in the instance folder ({len(r['missing'])}): {', '.join(r['missing'][:10])}")


@click.command("restore")
@click.argument("backup_db")
@click.option("--files", "files_dir", help="where the files of the backup are (default: soubory/ next to it)")
@click.option("--yes", is_flag=True, help="really overwrite the database (stop the web pages and the worker first)")
@with_appcontext
def restore_command(backup_db, files_dir, yes):
    """Put the database of a backup (ob-....db) and its files back into the instance folder."""
    conf = current_app.config["OB"]
    if not os.path.exists(backup_db):
        raise click.ClickException(f"no such backup: {backup_db}")
    if not yes:
        click.echo(f"would overwrite {conf.db_path} with {backup_db}; stop the web pages and the worker, then "
                   "run again with --yes")
        return
    r = restore(conf, backup_db, files_dir)
    click.echo(f"database restored, {r['restored']} of {r['files']} files put back")
    if r["missing"]:
        click.echo(f"not in the backup ({len(r['missing'])}): {', '.join(r['missing'][:10])}")
