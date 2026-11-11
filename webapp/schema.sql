-- OB tracker web app. Files (maps, .fit, analysis outputs) live in the instance folder;
-- the database keeps their paths relative to it. Times are UTC ISO strings unless named *_local.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name          TEXT,
    oris_regno    TEXT,              -- e.g. BFM0903
    oris_user_id  INTEGER,
    oris_synced_at TEXT,
    slope_file    TEXT,              -- own slope_prior.json fitted from a Garmin export, else the default
    -- a forgotten password: the one-time code the administrator printed (only its hash), until when it is
    -- good (UTC) and how many wrong tries it has seen
    reset_hash    TEXT,
    reset_until   TEXT,
    reset_tries   INTEGER NOT NULL DEFAULT 0,
    -- the settings of the interface, kept here and not in the browser: the app on one's own computer starts on another
    -- port each time and the browser keeps its storage per address with the port (docs/rozhodnuti.md, 8. 11. 2026)
    theme         TEXT,              -- light / dark: 'svetly', 'tmavy', '' = as the device, NULL = not chosen yet
    lang          TEXT,              -- 'cs' / 'en', NULL = the cookie or the default
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The registration number belongs to the account for good (an account without one may still get it).
-- Changing it would leave the races of two people in one account and block the owner of the new number.
CREATE TRIGGER IF NOT EXISTS users_regno_fixed BEFORE UPDATE OF oris_regno ON users
WHEN OLD.oris_regno IS NOT NULL AND NEW.oris_regno IS NOT OLD.oris_regno
BEGIN
    SELECT RAISE(ABORT, 'the registration number of an account cannot be changed');
END;

-- Every registration number of an account (docs/oris.md): after a move to another club the runner has a new
-- number and ORIS keeps the old races under the old one. users.oris_regno stays the first number of the account;
-- the triggers below copy it here, so whatever sets it (registration, profile, seed, tools) needs nothing more.
CREATE TABLE IF NOT EXISTS user_regnos (
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    regno        TEXT NOT NULL UNIQUE,  -- one number, one account
    oris_user_id INTEGER,
    name         TEXT,                  -- the name ORIS gives for the number
    -- ucet: the number of the account | rucne: added in the profile ("I moved to another club")
    -- | oris: seen in the runner's own entries in ORIS (the same ORIS person)
    source       TEXT NOT NULL DEFAULT 'ucet',
    added_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, regno)
);
CREATE TRIGGER IF NOT EXISTS users_regno_listed AFTER INSERT ON users WHEN NEW.oris_regno IS NOT NULL
BEGIN
    INSERT OR IGNORE INTO user_regnos (user_id, regno, oris_user_id) VALUES (NEW.id, NEW.oris_regno, NEW.oris_user_id);
END;
CREATE TRIGGER IF NOT EXISTS users_regno_listed_later AFTER UPDATE OF oris_regno ON users WHEN NEW.oris_regno IS NOT NULL
BEGIN
    INSERT OR IGNORE INTO user_regnos (user_id, regno, oris_user_id) VALUES (NEW.id, NEW.oris_regno, NEW.oris_user_id);
END;

-- a race day; from ORIS (oris_id set) or entered by hand (races outside ORIS)
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY,
    oris_id      INTEGER UNIQUE,
    name         TEXT NOT NULL,
    date         TEXT NOT NULL,      -- local date YYYY-MM-DD
    place        TEXT,
    discipline   TEXT,
    livelox_id   TEXT,
    lat          REAL,
    lon          REAL,
    links        TEXT,               -- JSON [{name, url}] from ORIS getEvent (old map, OResults, ...)
    locations    TEXT,               -- JSON [{name, lat, lon}] from ORIS getEvent (parking, centre, start ...)
    -- what the race has for runners without a setting of their own (entries.own_osm_mode, own_hatch_mode)
    osm_mode     TEXT NOT NULL DEFAULT 'forbid',  -- railways and motorways from OSM: forbid | penalty | off
    hatch_mode   TEXT NOT NULL DEFAULT 'forbid',  -- hatched out-of-bounds areas of the map with the course: forbid | off
    maponly_file TEXT,               -- map without course: one upload serves every runner of the event
    maponly_by   INTEGER REFERENCES users(id),
    maponly_at   TEXT,
    -- where the map without course came from: kmz (Livelox) | snimek (a screenshot of Livelox without the course,
    -- placed by a screenshot with it: oroute/pair.py); NULL: a KMZ from before the column
    maponly_source TEXT,
    maponly_res_m  REAL,             -- snimek: metres per pixel of the map kept
    maponly_acc_m  REAL,             -- snimek: how far off the map may be (metres)
    -- a stage of a multi-stage event: ORIS id of the umbrella event, which stage, of how many (stage_n 0: the
    -- race was checked and is no stage; NULL: not known)
    stage_parent INTEGER,
    stage_n      INTEGER,
    stage_count  INTEGER,
    created_by   INTEGER REFERENCES users(id),
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The umbrella event of a multi-stage race in ORIS: entries are made to it, the stages are the races (maps,
-- courses, split times). It is not kept as a race; this row only spares ORIS a second getEvent.
-- kept_event_id: an umbrella from before that a runner had a run or a map in and could not be moved to a stage.
CREATE TABLE IF NOT EXISTS oris_umbrellas (
    oris_id       INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    date          TEXT NOT NULL,
    stages        TEXT NOT NULL,     -- JSON [ORIS id of stage 1, stage 2, ...]
    kept_event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    fetched_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS classes (
    id            INTEGER PRIMARY KEY,
    event_id      INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    oris_id       INTEGER UNIQUE,
    name          TEXT NOT NULL,
    distance_km   REAL,
    climb_m       REAL,
    controls      INTEGER,
    control_codes TEXT,              -- JSON list, from ORIS getSplits
    course_file   TEXT,              -- map with the course printed: shared by the runners of this class
    course_by     INTEGER REFERENCES users(id),
    course_at     TEXT,
    -- where the map with the course came from: kmz (Livelox) | image (a picture placed by the
    -- circles) | photo (a photo placed by the circles) | manual (a photo placed by hand) | screen (a screenshot of
    -- Livelox, with one without the course: oroute/pair.py); NULL: from before
    course_source TEXT,
    course_rms    REAL,              -- picture and photo: how well the controls fit (metres)
    course_n      INTEGER,           -- ... on how many controls
    course_edge_m REAL,              -- ... and how far off the edges of the map may be
    UNIQUE (event_id, name)
);

CREATE TABLE IF NOT EXISTS activities (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sha1          TEXT NOT NULL,
    file          TEXT NOT NULL,
    original_name TEXT,
    source        TEXT NOT NULL,     -- 'fit' | 'garmin-export'
    start_utc     TEXT,
    sport         TEXT,
    sub_sport     TEXT,
    timer_s       REAL,
    elapsed_s     REAL,
    dist_m        REAL,
    lat           REAL,
    lon           REAL,
    has_gps       INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, sha1)
);

-- one runner in one class of one event
CREATE TABLE IF NOT EXISTS entries (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    class_id         INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    official_time_s  INTEGER,
    start_local      TEXT,           -- HH:MM:SS
    result_place     TEXT,
    splits           TEXT,           -- JSON list of official split seconds (null = missing punch)
    activity_id      INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    match_confidence TEXT,           -- high | medium | low | none | manual
    match_note       TEXT,
    own_osm_mode     TEXT,           -- the runner's own setting instead of events.osm_mode; NULL = as the race has it
    own_hatch_mode   TEXT,           -- the same for events.hatch_mode
    gps_trim         TEXT,           -- JSON: how the start and end of the run's GPS track are cut
                                     -- (services/runner.py gps_trim); NULL = automatically
    class_chosen     INTEGER NOT NULL DEFAULT 0,   -- 1: the runner chose the class (services/oris_class.py); the
                                                   -- class of their ORIS entry does not replace it
    UNIQUE (user_id, class_id)
);

CREATE TABLE IF NOT EXISTS refreshments (
    id         INTEGER PRIMARY KEY,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    lat        REAL NOT NULL,
    lon        REAL NOT NULL,
    source     TEXT NOT NULL DEFAULT 'manual',   -- 'manual' | 'detected'
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- crossings that are not allowed, drawn by hand on the map; shared by everyone at the event
CREATE TABLE IF NOT EXISTS barriers (
    id         INTEGER PRIMARY KEY,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL DEFAULT 'forbidden',  -- 'forbidden' (must not cross) | 'hard' (very slow to cross)
    line       TEXT NOT NULL,                      -- JSON [[lat, lon], ...]
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- what a runner corrected of the obstacles read from the map, for their own routes only (not shared):
-- kind: fence | enclosure (read from the picture), osm | hatch (the lines of OpenStreetMap, the hatched areas);
-- key: "lat,lon" of the centre of the obstacle, the way to find it again after a new reading of the map
CREATE TABLE IF NOT EXISTS barrier_overrides (
    entry_id   INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,
    key        TEXT NOT NULL,
    action     TEXT NOT NULL,        -- remove | hard | tall | fence | forbidden (what it is instead)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entry_id, kind, key)
);

-- official split times of every runner of a class (ORIS getSplits), kept so ORIS is asked once
CREATE TABLE IF NOT EXISTS class_splits (
    class_id   INTEGER PRIMARY KEY REFERENCES classes(id) ON DELETE CASCADE,
    data       TEXT NOT NULL,        -- JSON: control_codes, runners [{name, regno, club, place, start, time_s, cum}]
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- the current analysis of an entry (re-running replaces it)
CREATE TABLE IF NOT EXISTS analyses (
    id           INTEGER PRIMARY KEY,
    entry_id     INTEGER NOT NULL UNIQUE REFERENCES entries(id) ON DELETE CASCADE,
    has_routes   INTEGER NOT NULL DEFAULT 0,   -- 0: splits and mistake signals only, 1: best routes too
    total_time_s REAL,
    start_utc    TEXT,
    model_id     INTEGER REFERENCES speed_models(id) ON DELETE SET NULL,
    summary      TEXT,               -- JSON: reference speed, route ratio, GPS offset, notes
    course       TEXT,               -- JSON: start, controls, finish (lat/lon)
    track        TEXT,               -- JSON: lat, lon, t arrays + punch indices
    out_dir      TEXT,
    finished_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS legs (
    id          INTEGER PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    n           INTEGER NOT NULL,    -- 1 = start to first control
    name        TEXT NOT NULL,       -- S-1, 1-2, ..., 12-F
    data        TEXT NOT NULL,       -- JSON: every number analyze.py / bestroute.py computed for the leg
    best_route  TEXT,                -- JSON [[lat, lon], ...]
    explain_cs  TEXT,
    explain_en  TEXT,
    UNIQUE (analysis_id, n)
);

-- what the runner says about a leg; keyed by entry so it survives a re-analysis
CREATE TABLE IF NOT EXISTS leg_notes (
    entry_id        INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    leg_n           INTEGER NOT NULL,
    planned         TEXT,            -- JSON [[lat, lon], ...] drawn on the map
    plan            TEXT,            -- JSON: the planned route priced by the speed model (services/plans.py);
                                     -- NULL until the worker has done it, and again when the line changes
    deliberate_stop INTEGER NOT NULL DEFAULT 0,
    lost_contact    INTEGER NOT NULL DEFAULT 0,
    green           TEXT,            -- 'through' | 'around' | NULL
    fatigue         INTEGER,         -- 1..5 | NULL
    text            TEXT,
    corrected       TEXT,            -- JSON [[lat, lon], ...]: where the runner really ran, drawn where the GPS
                                     -- failed; it stands for the track of the leg (bestroute.py --corrections)
    control_desc    TEXT,            -- the description of the control at the end of the leg, typed by hand
                                     -- (shown by "Ztratil jsem se"; nothing is computed from it)
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entry_id, leg_n)
);

-- the last photo of the map a runner uploaded for an entry, kept to place it by hand (views/photo.py)
CREATE TABLE IF NOT EXISTS photos (
    entry_id    INTEGER PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
    file        TEXT NOT NULL,       -- upright, at most georef.MAX_SIDE_PX
    points      TEXT,                -- JSON [{control, u, v}] clicked so far
    waiting_for_run INTEGER NOT NULL DEFAULT 0, -- uploaded before FIT/ORIS splits; place when they arrive
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- the last pair of Livelox screenshots a runner uploaded for a class (oroute/pair.py), kept so that the one without
-- the course can come later and the map can be cut out by hand (views/photo.py)
CREATE TABLE IF NOT EXISTS screens (
    class_id     INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_file  TEXT NOT NULL,      -- the screenshot with the course, as uploaded
    maponly_file TEXT,               -- the screenshot without it, as uploaded
    width        INTEGER NOT NULL,
    height       INTEGER NOT NULL,
    crop         TEXT,               -- JSON [x0, y0, x1, y1]: the map cut out by hand (pixels of the screenshot)
    info         TEXT,               -- JSON: what the last placing said (box, reliable, notes, res)
    uploaded_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (class_id, user_id)
);

-- Livelox screenshots may arrive separately, even before the FIT or ORIS splits. Keep them here until
-- there is a screenshot with the course and the runner's track plus official punch times.
CREATE TABLE IF NOT EXISTS pending_screens (
    class_id     INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_file  TEXT,
    maponly_file TEXT,
    queued       INTEGER NOT NULL DEFAULT 0,
    uploaded_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (class_id, user_id),
    CHECK (course_file IS NOT NULL OR maponly_file IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS speed_models (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model     TEXT NOT NULL,         -- JSON as written by oroute.speedmodel.SpeedModel.save
    file      TEXT NOT NULL,
    fitted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL,       -- sync_oris | import_upload | analyse | refit_model | georef_map | price_plans | relocate | recompute_all
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    entry_id    INTEGER REFERENCES entries(id) ON DELETE CASCADE,
    payload     TEXT,                -- JSON
    status      TEXT NOT NULL DEFAULT 'queued',   -- queued | running | done | failed | stopped
    stop_requested INTEGER NOT NULL DEFAULT 0,   -- the runner asked to stop it (services/jobs.py)
    lang        TEXT,                -- language of the page that started it (cs | en): the job's sentences use it
    message     TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    started_at  TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status, id);
CREATE INDEX IF NOT EXISTS entries_user ON entries (user_id);
CREATE INDEX IF NOT EXISTS activities_user ON activities (user_id, start_utc);
