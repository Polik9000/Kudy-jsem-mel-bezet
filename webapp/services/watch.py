"""Runs from a Garmin watch connected by USB (it shows up as a disk with GARMIN/Activity/*.fit) or from any folder
with .fit files (TODO 55). The app offers the runs it does not have yet and loads the ones the runner ticks.
Newer watches that connect over MTP show no disk; the help says to export from Garmin Connect then."""
import glob
import hashlib
import os
import string
import sys
import threading
import time

from oroute import garmin

from . import matching, storage

MAX_FILES = 3000            # one watch keeps a few hundred; a folder with more than this is not a watch
MAX_FIT = 50 * 1024 * 1024
WAIT_S = 2.0                # how long a page waits for the look at the watch; longer and it asks again later
KEEP_S = 60.0               # how long a finished look is good for (a watch is plugged in for minutes, not seconds)


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
    # the runs left unticked were offered and said no to: the note on the pages does not bring them up again
    set_aside(con, user["id"], [r["sha1"] for r in rows if r["new"] and r not in chosen])
    return loaded, there, len(set(names)) - len(chosen)


# The look at the connected watches when a page opens (Přehled závodů, Nahrát běhy). It runs in a thread of its own:
# a drive letter without a card or a network drive that went away can block a call to the disk for seconds, and
# the page must not wait for it. What the thread found is kept for KEEP_S, and what each file is (by name, size and
# time) for as long as the app runs, so a watch with hundreds of runs is read once.
_lock = threading.Lock()
_state = dict(at=0.0, result=None, thread=None)
_files = {}                 # (path, size, mtime) -> (sha1, is a run with a start) or None for no activity


def _look_at_file(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (path, st.st_size, st.st_mtime)
    if key not in _files:
        if st.st_size > MAX_FIT:
            _files[key] = None
        else:
            with open(path, "rb") as f:
                data = f.read()
            info = garmin.scan_fit(data)
            ok = info.get("type") == "activity" and not info.get("error") and info.get("start") is not None
            _files[key] = hashlib.sha1(data).hexdigest() if ok else None
    return _files[key]


def _look():
    """{Activity folder: [sha1 of each run in it]} of the connected watches."""
    out = {}
    for folder in watch_folders():
        try:
            base, names = _fit_files(folder)
        except OSError:
            continue
        out[base] = [s for s in (_look_at_file(os.path.join(base, n)) for n in names) if s]
    return out


def _run():
    try:
        result = _look()
    except Exception:  # noqa: BLE001 - a look that fails is the same as no watch; the page never breaks over it
        result = {}
    with _lock:
        _state.update(at=time.monotonic(), result=result, thread=None)


def look_now(wait=WAIT_S):
    """{folder: [sha1, ...]} of the watches connected now, or None when the look is still running after wait
    seconds (the page asks again later). Starts a new look when the last one is older than KEEP_S."""
    with _lock:
        fresh = _state["result"] is not None and time.monotonic() - _state["at"] < KEEP_S
        if fresh:
            return _state["result"]
        th = _state["thread"]
        if th is None:
            th = threading.Thread(target=_run, name="watch-look", daemon=True)
            _state["thread"] = th
            th.start()
    th.join(wait)
    with _lock:
        return _state["result"] if _state["thread"] is None else None


def forget():
    """Look again at the next ask (after loading, or in tests)."""
    with _lock:
        if _state["thread"] is None:
            _state.update(at=0.0, result=None)


def news(con, user_id, wait=WAIT_S):
    """What the page offers: dict(pending=True) while the look runs, else dict(n=new runs, folder=the watch with
    most of them). New = not in the app and not set aside by the runner ("Teď ne"). Reads nothing into the app."""
    found = look_now(wait)
    if found is None:
        return dict(pending=True, n=0, folder=None)
    skip = {r["sha1"] for r in con.execute("SELECT sha1 FROM activities WHERE user_id = ?", (user_id,))}
    skip |= {r["sha1"] for r in con.execute("SELECT sha1 FROM watch_seen WHERE user_id = ?", (user_id,))}
    best, n = None, 0
    for folder, sha1s in found.items():
        k = len(set(sha1s) - skip)
        if k > n:
            best, n = folder, k
    return dict(pending=False, n=n, folder=best)


def set_aside(con, user_id, sha1s):
    """The runner said no to these runs for now: the note on the pages does not offer them again (the watch page
    still lists them)."""
    con.executemany("INSERT OR IGNORE INTO watch_seen (user_id, sha1) VALUES (?, ?)",
                    [(user_id, s) for s in set(sha1s)])
    con.commit()


def set_aside_all(con, user_id):
    """"Teď ne" on the note: every run the watches have now."""
    found = look_now(0) or {}
    set_aside(con, user_id, [s for sha1s in found.values() for s in sha1s])
