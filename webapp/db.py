"""SQLite access shared by the web process and the worker (plain sqlite3, no ORM)."""
import json
import os
import sqlite3

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def connect(path):
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")  # the worker writes while the web process reads
    return con


# columns added after the first version: (table, column, definition). schema.sql creates new databases with
# them; an older database gets them here (CREATE TABLE IF NOT EXISTS does not touch an existing table).
ADDED_COLUMNS = [
    ("events", "links", "TEXT"),
    ("events", "locations", "TEXT"),
    ("events", "osm_mode", "TEXT NOT NULL DEFAULT 'forbid'"),
    ("events", "hatch_mode", "TEXT NOT NULL DEFAULT 'forbid'"),
    ("leg_notes", "plan", "TEXT"),
    ("users", "reset_hash", "TEXT"),
    ("users", "reset_until", "TEXT"),
    ("users", "reset_tries", "INTEGER NOT NULL DEFAULT 0"),
    ("entries", "own_osm_mode", "TEXT"),
    ("entries", "own_hatch_mode", "TEXT"),
    ("entries", "class_chosen", "INTEGER NOT NULL DEFAULT 0"),
    ("classes", "course_source", "TEXT"),
    ("classes", "course_rms", "REAL"),
    ("classes", "course_n", "INTEGER"),
    ("classes", "course_edge_m", "REAL"),
    ("events", "maponly_source", "TEXT"),
    ("events", "maponly_res_m", "REAL"),
    ("events", "maponly_acc_m", "REAL"),
    ("jobs", "stop_requested", "INTEGER NOT NULL DEFAULT 0"),
    ("jobs", "lang", "TEXT"),
    ("leg_notes", "corrected", "TEXT"),
    ("leg_notes", "control_desc", "TEXT"),
]


def migrate(con):
    for table, column, ddl in ADDED_COLUMNS:
        have = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
        if have and column not in have:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    # One account per registration number. A database from before this rule may hold several accounts with
    # the same number: then the index cannot be made, the app still starts (new duplicates are refused by
    # the registration and profile forms) and says how to clean up.
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone():
        try:
            con.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_regno ON users (oris_regno)"
                        " WHERE oris_regno IS NOT NULL")
        except sqlite3.IntegrityError:
            dup = [r[0] for r in con.execute("SELECT oris_regno FROM users WHERE oris_regno IS NOT NULL"
                                             " GROUP BY oris_regno HAVING COUNT(*) > 1")]
            print(f"warning: several accounts share a registration number ({', '.join(dup)}); remove the extra "
                  "ones with: flask --app webapp.wsgi delete-account NAME --yes", flush=True)


def init(path):
    """Create missing tables and columns (safe to call on every start)."""
    con = connect(path)
    # an older database: add the new columns first, schema.sql may index or use them
    migrate(con)
    with open(SCHEMA, encoding="utf-8") as f:
        con.executescript(f.read())
    migrate(con)
    con.commit()
    con.close()


def loads(text, default=None):
    return json.loads(text) if text else default


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
