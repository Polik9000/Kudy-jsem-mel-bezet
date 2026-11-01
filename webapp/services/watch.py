"""Runs from a Garmin watch connected by USB (it shows up as a disk with GARMIN/Activity/*.fit) or from any folder
with .fit files (TODO 55). The app offers the runs it does not have yet and loads the ones the runner ticks.
Newer watches that connect over MTP show no disk; the help says to export from Garmin Connect then."""
import glob
import hashlib
import os
import string
import sys

from oroute import garmin

from . import matching, storage

MAX_FILES = 3000            # one watch keeps a few hundred; a folder with more than this is not a watch
MAX_FIT = 50 * 1024 * 1024


def watch_folders():
    """The Activity folders of connected Garmin watches: GARMIN/Activity on a disk (or ACTIVITY on some models)."""
    if sys.platform == "win32":
        roots = [f"{d}:\\" for d in string.ascii_uppercase if d not in "AB"]
    elif sys.platform == "darwin":
        roots = glob.glob("/Volumes/*")
    else:
        roots = glob.glob("/media/*/*") + glob.glob("/run/media/*/*") + glob.glob("/mnt/*") + glob.glob("/media/*")
    out = []
    for root in roots:
        for sub in (("GARMIN", "Activity"), ("Garmin", "Activity"), ("GARMIN", "ACTIVITY")):
            p = os.path.join(root, *sub)
            if os.path.isdir(p) and p not in out:
                out.append(p)
    return out


def _fit_files(folder):
    """The .fit files of a folder, newest first: the folder itself, or its Activity folder for a watch disk."""
    for base in (folder, os.path.join(folder, "GARMIN", "Activity"), os.path.join(folder, "Activity")):
        if os.path.isdir(base):
            names = [n for n in os.listdir(base) if n.lower().endswith(".fit") and os.path.isfile(os.path.join(base, n))]
            if names:
                names.sort(key=lambda n: os.path.getmtime(os.path.join(base, n)), reverse=True)
                return base, names[:MAX_FILES]
    return folder, []


def offer(con, user_id, folder):
    """(the folder the files are in, [dict(name, start, sport, timer_s, dist_m, sha1, new)]) for a folder; new is
    False for a run the app has already. Files that are no activity (settings, monitoring) are left out.
    Raises FileNotFoundError when the folder is not there."""
    folder = os.path.abspath(os.path.expanduser(folder.strip()))
    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)
    base, names = _fit_files(folder)
    have = {r["sha1"] for r in con.execute("SELECT sha1 FROM activities WHERE user_id = ?", (user_id,))}
    rows = []
    for name in names:
        path = os.path.join(base, name)
        if os.path.getsize(path) > MAX_FIT:
            continue
        with open(path, "rb") as f:
            data = f.read()
        info = garmin.scan_fit(data)
        if info.get("type") != "activity" or info.get("error") or info.get("start") is None:
            continue
        sha1 = hashlib.sha1(data).hexdigest()
        rows.append(dict(name=name, start=garmin.local(info["start"]), sport=info.get("sport"),
                         timer_s=info.get("timer"), dist_m=info.get("dist"), has_gps=bool(info.get("first_gps")),
                         sha1=sha1, new=sha1 not in have))
    return base, rows


def load(con, conf, user, folder, names):
    """Load the chosen files (names as offer() gave them; anything else is ignored) and pair them with the
    races. Returns (loaded, already there, refused)."""
    base, rows = offer(con, user["id"], folder)
    chosen = [r for r in rows if r["name"] in set(names)]
    loaded = there = 0
    for r in chosen:
        with open(os.path.join(base, r["name"]), "rb") as f:
            data = f.read()
        aid, new = storage.save_activity(con, conf, user["id"], data, r["name"], "fit")
        if aid is None:
            continue
        loaded += new
        there += not new
    if loaded:
        matching.match_user(con, user["id"])
    return loaded, there, len(set(names)) - len(chosen)
