# OB tracker: orienteering route analysis from Garmin .fit + map

A web app for the runners of SKOB Frýdek-Místek and the Python scripts behind it. From a Garmin track, the race
map and the official ORIS times it shows where time was lost on every leg, what the fastest route would have been
for this runner, and what kind of mistake was made at a control. Rules and geometry only, no AI/LLM calls.

**Česky v kostce:** Program porovná tvůj postup z hodinek Garmin (.fit) s nejrychlejším postupem podle mapy a
tvého osobního modelu rychlosti a ukáže, kde jsi ztratil čas. Spouští se na vlastním počítači; tvoje mapy a .fit
zůstávají u tebe. Mapy ani záznamy běhů v tomto repozitáři nejsou, nahraješ si vlastní. Licence: PolyForm
Noncommercial 1.0.0, tedy zdarma pro jakékoli nekomerční použití (sám, oddíl, škola); komerční jen se svolením autora.

## Download (Windows, macOS)

Installers without Docker or Python: the GitHub Releases of this repository (Windows 10/11, macOS on Apple
Silicon). One runner, no login; the data is in your own user folder. How they are built and what still needs a
test on a clean computer: `docs/instalatory.md` (in Czech).

## Your data stays on your computer

Run the app on your own machine (`docker compose up --build`, then http://localhost:8000/ob/; no account, no login). The maps and `.fit`
files you upload are kept in a local Docker volume and are never sent to anyone. The app itself only asks public
services for what it cannot know: race details and split times from ORIS, elevation from ČÚZK or AWS Terrain Tiles,
railways and roads from OpenStreetMap (Overpass). For elevation and OpenStreetMap it sends the area of the map, not
your track. The full list of what is requested and what goes out is in [`docs/soukromi.md`](docs/soukromi.md)
(Czech); `tests/test_soukromi.py` keeps it complete.

## What is not in this repository

This is a public copy of a private project. Left out on purpose:
- **maps**: course and map-only KMZ from Livelox, ORIS or OB postupy belong to the race organisers and map authors;
  export your own from Livelox (KMZ, "map only" and "with course");
- **runs**: no `.fit` files, no Garmin export, nothing derived from them, no demo races;
- **screenshots** of the app and of maps from the development notes in `docs/`, so some notes link to pictures that
  are not here.

Because of that, the tests that need the four reference races (`data/`, `tests/golden`) and all slow tests are
skipped here (`needs the race maps and runs ... (not public)`); the rest run as usual. `oroute/personal_model.json`
and `oroute/slope_prior.json` are the author's own speed model, used as the default until you add your races.
The docs in `docs/` are the development notes of the project, in Czech.

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE): free to use, change and share for any noncommercial purpose (personal use,
clubs, schools, research). Commercial use needs the author's permission.

# Web app

```
docker compose up --build                # http://localhost:8000/ob/
docker compose run --rm web pytest -m "not slow"                                     # fast tests (about 4 min)
docker compose run --rm web pytest -m slow                                           # the four races (about 11 min, alone: needs memory)
docker compose run --rm web ruff check .                                             # linter
```

Flask + SQLite in `webapp/`, in the look of the club site (its `skob.css` unchanged, own styles in `ob.css`, light
and dark mode), served under `/ob` so it can run next to the club site as a separate process. A second container,
`python -m webapp.worker`, runs the analysis in the background with the scripts below; no calculation lives in
`webapp/`. Uploaded maps and .fit files stay in a Docker volume, never in the repo.

One job analyses a race: the track, the splits and the kinds of mistakes are on the page as soon as `analyze.py` is
done, the race then joins the runner's speed model and the best routes are found once, with that model. The page
says what is being computed. The hardest of the four reference races (Petřvald) takes just under 3 minutes, the
track is there after half a minute (`docs/validace.md`, part 11).

What a runner does:
1. **Account.** By default (`OB_LOCAL=1`, also in `docker-compose.yml`) the app is for one runner on their own
   computer: no account, no login, the ORIS registration number is optional and set in Profile. A club server for
   many runners runs with `OB_LOCAL=0`: an account from an ORIS registration number, the code of that number and a
   password at `/ob/register`. The
   code comes from the administrator (`invite` below), so nobody makes an account on somebody else's number. The
   name and the ORIS id come from ORIS, the races load by themselves. One registration number has exactly one
   account and the number of an account cannot be changed. A login lasts 90 days.
2. **My races**: every race from ORIS with its state (activity missing / map missing / done), filter by season.
3. **Upload runs**: single `.fit` files or a whole Garmin export (zip). They are paired with the races by date,
   start time and distance from the race centre. The export job loads the runner's races from ORIS first; then
   only the runs paired with races are kept, plus unpaired runs recorded at a race on its day (to pair by hand
   or delete).
4. **Maps** per race: the Livelox KMZ with the course (per class) and without it (shared by the whole race), or a
   picture of the map (jpg, png), which is placed by the control circles and the track.
5. **Race page**: Leaflet map with the track coloured by loss, the best route with up to two alternatives, the route
   an average runner would take where it differs, with why the runner's own is faster for them, the kind
   of mistake at a control, the table of legs with explanations in Czech, the split times of the whole class
   (WinSplits method, works without a .fit), notes per leg, forbidden crossings (railways and motorways from
   OpenStreetMap, lines drawn by hand), links to ORIS, OResults and the club site. A route planned for a leg
   (drawn on the map) is priced by the model and shown next to the best route and the one that was run; "if you
   got lost" lists two to four catching features around the control with bearings, and where the track shows
   wandering, where contact was lost and what was close by. The selected leg is in the
   address (`#usek-7`), the arrow keys go from leg to leg, notes are saved as they are typed; the page reloads
   itself only when it shows the state of a job, never over unsaved work. The run and both maps can be uploaded
   in one form on the race page.
6. **Personal speed model**: speed per terrain with its uncertainty, the slope curve, a leave-one-race-out check.

Administration (inside the `web` container):

```
flask --app webapp.wsgi seed-demo NAME --password PASSWORD       # the four races of data/ (not public) for an account
flask --app webapp.wsgi invite REGNO [REGNO ...] [--site URL]    # the registration code and link of each number
flask --app webapp.wsgi reset-code REGNO [--site URL]            # a one-time code for a new password (24 hours)
flask --app webapp.wsgi delete-account NAME_OR_REGNO             # lists what would go; add --yes to delete
flask --app webapp.wsgi sync-oris-all [--hours 20]              # new races from ORIS for every account (daily)
flask --app webapp.wsgi backup [--to DIR] [--keep 14]           # database + the uploads that cannot be got again
flask --app webapp.wsgi restore BACKUP.db --yes                 # back from a backup (web and worker stopped)
```

Daily from cron on the host, or the service `cron` of `docker-compose.yml` (off unless `--profile cron`):
`docs/provoz.md`. The help page for the runners is `/ob/jak-na-to`.

Docs (Czech), all in `docs/`:

| File | What |
|---|---|
| `provoz.md` | running it for a club: the daily load from ORIS, backups and restoring them, cron |
| `web-aplikace.md` | how to use the app and how to put it next to the club site (separate process, `/ob`, shared CSS) |
| `api-a-data.md` | addresses, outside services (ORIS, ČÚZK, Overpass), database, settings, scripts |
| `rozhodnuti.md` | the choices made and why |
| `validace.md` | measurements: model against the class, ČÚZK against AWS, map placement, mistake types, model variants, speed of the analysis |
| `co-zbyva.md` | where things stand, what is not done (handling of the pages included), what is uncertain, questions for Tobias and for the club site's author |
| `pr-popis.md` | the description of the pull request of the last work branch |
| `zavislosti.md` | libraries, data sources and their licences |
| `pruzkum.md` | the research the work follows, with the state of every recommendation |
| `design-klubovy-web.md`, `reference/` | the look of the club site (its stylesheet and icons; the screenshots are not public) |
| `plan-noc.md` | log of the night of 6 to 7 Oct 2026 |
| `automatizace.md`, `audit-skripty.md` | the earlier plan and audit, with their state today |

# The `oroute` package

Everything the web app shows is computed here; the scripts `analyze.py`, `bestroute.py` and `run_race.py` can be run
without the web. Besides the modules described in the sections below:
- `official.py` official ORIS times first: with `--official` the punches are put at the organiser's times and the
  GPS track is only cut there, and the order of the controls comes from them too (where the watch was at each
  punch time says which circle is which control); without it everything works from GPS and the purple lines;
- `splits.py` split-time analysis of a class (reference time, runner's normal, mistakes over 30 s and 25 %, rank
  agreement between the model and the class);
- `dem.py` Czech DMR 5G elevation (ČÚZK, CC BY 4.0) next to the AWS tiles: `bestroute.py --dem aws|cuzk|auto`;
- `osm.py` + `routing.py` railways and motorways from OpenStreetMap as forbidden lines with level crossings, bridges
  and underpasses as the places to cross, lines drawn by hand, "forbidden" (infinite cost) against "hard to cross"
  (90 s): `bestroute.py --barriers FILE`;
- `hatch.py` out-of-bounds areas read from the purple hatching of the map with the course (ISOM 709, crossed or
  vertical lines); the routes keep out of them: `python -m oroute.hatch COURSE.kmz areas.json`, then
  `bestroute.py --barriers areas.json`;
- `planned.py` the model time of a route drawn by hand, priced like the best route and the line that was run,
  with a sentence on why it is slower or where the time was lost;
- `relocate.py` catching features around every control (path junctions and ends, paths, streams, buildings, ponds,
  fenced enclosures, clearings, the point symbols of the map) with bearings to the north of the map, the attack
  point before the control on the way the best route comes in, the backstop beyond it, and wandering near a
  control read from the track;
- `symbols.py` point symbols of ISOM 2017-2 read from the picture of the map by colour, size and shape (knoll,
  depression, pit, landform, boulder, waterhole, well, tree, stand, man-made object);
- `mapdata.py` the terrain, the elevation and the barriers of a map, read the same way by these scripts;
- `generic.py` the best route of an average runner (textbook model at your speed) next to yours: where it differs
  and why (`bestroute.py --generic`);
- `routing.py` alternatives (k dissimilar routes by the penalty method) and the check whether the best route flips
  when terrain speeds shift by 20 %: `bestroute.py --alternatives 2`;
- `mistakes.py` the kind of mistake at a control from the shape of the track (overshoot, undershoot, drift, circling,
  relocation);
- `georef.py` placing a picture of a map without a KMZ from the control circles and the track at the official punch
  times (RANSAC + least squares);
- `garmin.py`, `annotations.py` pairing activities with races, and how the runner's notes change losses and the model.

`tools/jointfit.py` is an experimental joint fit of the speed model in the log of speed with a leave-one-race-out
check (not used by the app, see `docs/validace.md`).

`tests/golden` (not public) holds the reference outputs of the four races in `data/` (see `data/README.md`); totals 77:02, 55:07,
50:22 (official; 51:05 from GPS alone), 80:18. Without the new options the scripts reproduce them byte for byte. The
best routes of Petřvald were renewed on 7 Oct 2026, when the terrain reader began to follow the map resolution.

Known limits (details in `docs/co-zbyva.md`): the order of more than 20 controls without official split times is
found by an approximate search and was only tried on made-up courses; a control punched twice (butterfly) is not
read; a railway is read from the map as a path (crossing it is forbidden by the line from OpenStreetMap, running
along it is not); the thresholds of the mistake types are not tuned against a runner's notes; the web uses ČÚZK elevation for Czech races while the scripts default to AWS, so
the personal model of the web differs from `oroute/personal_model.json`.

```
pip install -r requirements.txt          # or: docker build -t ob-tracker .
```

# oroute: step 1 (track, splits, mistake signals)

```
python3 -m pip install fitdecode pillow numpy
python3 analyze.py input/azymut_e5_o3.kmz input/23973749498_ACTIVITY.fit out
```

Works for any Livelox KMZ that has the course printed on it (and for a KMZ written by `oroute/georef.py` from a
picture of the map):
- `oroute/kmzmap.py` reads the KML GroundOverlay (corners + rotation) and converts GPS <-> map pixels.
- `oroute/course.py` finds control circles (Hough transform on the purple overprint), the start triangle
  and finish double circle, and recovers the control order from the purple leg lines (about half a minute on the
  largest reference map since 2026-10-07, two and a half before; same results).
  The result is saved to `out/course.json`; if detection gets something wrong, fix the file and rerun with `--course out/course.json`.
  Since 2026-10-06 the order is then checked against the GPS track (`order_by_track`: reverses or moves stretches of
  controls until the lines and the track agree, and drops a circle lying on the finish). This reproduces the hand-fixed
  `course_fixed.json` of Pohora and Petřvald exactly, so no manual editing is needed. `--no-gps-order` turns it off.
- `oroute/analysis.py` finds when you reached each control, then per leg: split, distance run vs straight line,
  climb, time in the last 100 m, stops, and a rough time-loss estimate against your own median speed on the course.
- `oroute/render.py` draws the overlays.

Time loss is a first approximation: it does not know terrain or route choice yet (step 3 adds that).

# oroute: step 3 (fastest route per leg)

```
python3 -m pip install fitdecode pillow numpy scipy
python3 bestroute.py input/azymut_e5_maponly.kmz out/course.json input/23973749498_ACTIVITY.fit out/best
#   optional: --legs 8-9,5-6   --model some/speed_model.json|race   --step 2
```

Needs the **map-only** Livelox KMZ (no course drawn) for terrain, plus `course.json` from step 1 for the controls.
- `oroute/terrain.py` reads ISOM colours into terrain classes (forest, light/mid/dark green, stripes, open, rough open,
  marsh, water, paths, out of bounds, buildings). Contours are ignored; slope comes from the DEM. The sizes of map
  symbols in pixels follow the resolution of the picture (tuned at 1.33 m per pixel).
- `oroute/dem.py` downloads AWS Terrain Tiles (z15, ~30 m source data) and caches them in the output folder;
  with `--dem cuzk` or `--dem auto` it takes the Czech DMR 5G of ČÚZK instead (2 m laser scanning; it agrees with the
  watch barometer two to three times better, `docs/validace.md`). The Polish GUGiK LiDAR is not wired in.
- `oroute/speedmodel.py` is the replaceable speed model: pace = 1 / (v_flat * terrain factor) * slope multiplier.
  Saved as `speed_model.json`. By default the personal model `oroute/personal_model.json` is used (see below);
  `--model race` fits on this race alone (legs without mistakes, scaled to reproduce those times).
  Every run also writes `fit_samples.npz` (GPS samples of the clean legs), the input for the personal model.
- `oroute/routing.py` builds a 16-neighbour directed grid (2 map px ≈ 2.7 m cells, uphill and downhill cost
  differently) and runs Dijkstra per leg; `route_metrics` measures distance, climb, terrain mix and model time.
- Outputs in `out/best/`: `best_routes.md` (table + explanation per leg + reliability notes), `best_legs.jpg`,
  `best_routes.jpg`, `terrain.png`, `best_legs.csv`, `speed_model.json`.
- `--no-images` (both scripts) leaves the pictures out; `bestroute.py --samples-only` stops after the sample
  files, before any route is found; `--terrain-cache FILE` keeps the terrain read from the map for the next run.
  The web app uses all three (`webapp/services/runner.py`).

# Slope from ordinary Garmin activities (`oroute/slopefit.py`)

```
python3 -m oroute.slopefit GARMIN_EXPORT.zip oroute/slope_prior.json \
    --races garmin-matching/matches.csv
```

Cuts every running activity in the Garmin export into 30 s windows (barometric altitude, smoothed), divides
each window's speed by that activity's own flat speed and fits the slope part of the speed model
(`up_k`, `down_gain`, `steep_down`). Uphill comes from all runs (training + races), downhill only from
orienteering races (`--races`), because training downhills are mostly on paths. Recency weighted, half-life 365 days.
`bestroute.py` picks up `oroute/slope_prior.json` automatically (`--slope none` = textbook values).

Fit of 2026-10-06 (164 runs, 1383 uphill windows): up_k 3.4 (textbook 9), downhill no faster than flat, steep
downhill > 10 % slightly slower. Checked out of sample (fitted on training runs only, tested on 27 orienteering
races): error on slopes dropped from 0.38 to 0.30 (median abs log speed ratio); uphill bias from +40 % to +13 %.
Walking/hiking has a different shape and is left out by default (`--sports`).

# Personal speed model from all races (`oroute/personal.py`)

```
python3 -m oroute.personal oroute/personal_model.json out/best/fit_samples.npz \
    races/e4/out/best/fit_samples.npz races/pohora/out/best/fit_samples.npz \
    races/petrvald/out/best/fit_samples.npz --check
```

Pools the clean legs of every analysed race into one model, newer races weighted more (half-life 365 days).
Slope shape stays from `slope_prior.json`; terrain factors move from the ISOM priors toward your data by how many
weighted seconds you have in each terrain across all races; flat speed is scaled to reproduce your total clean-leg
time. `bestroute.py` uses `oroute/personal_model.json` automatically when it exists.
After analysing a new race: run bestroute once (it writes that race's `fit_samples.npz`), add the file to the
command above, refit, and re-run bestroute so the race is drawn with the updated model.
On the club website this is one `personal_model.json` per runner, refitted whenever a race is added.

Fit of 2026-10-19 (E5, E4, Pohora, Petřvald; the track along a path within 15 m of it counts as on the path),
speeds on flat ground in a one-hour race: path 11.4 km/h, open 10.9, rough open 9.3, forest 8.9, stripes 7.6, light
green 7.5, marsh 5.6, green 5.1, dark green 1.4 (almost all prior); a longer race is slower everywhere
(`dur_exp` 0.073). Leave-one-race-out check (`--check`): the other races predict a race's clean-leg total within
-9.5 % to +18.5 % (textbook terrain factors: -5.8 % to +25.3 %). The samples it was fitted on are made anew
(`bestroute.py --samples-only`, commands in `docs/validace.md` part 21); `data/*/fit_samples.npz` are still those of
6 Oct 2026.

# Everything in one command (`run_race.py`)

```
python3 garmin-matching/extract_fit.py GARMIN_EXPORT.zip fits 421896337251   # .fit out of the Garmin export
python3 run_race.py COURSE.kmz MAPONLY.kmz fits/RUN.fit races/new/out --title "Race name" \
    --refit out/best/fit_samples.npz races/e4/out/best/fit_samples.npz ...       # optional: refit personal model
```

Runs analyze.py, bestroute.py and (with `--refit`) the personal model refit plus a second bestroute. No manual steps:
tested 2026-10-06 on Pohora from the raw KMZs and .fit, identical to the hand-made results.
