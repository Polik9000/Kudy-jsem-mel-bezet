# Adresy, cizí služby a data (stav 7. 10. 2026)

## Adresy aplikace

Aplikace běží pod předponou `OB_URL_PREFIX` (výchozí `/ob`); všechny adresy níže jsou za ní. Kromě přihlášení a registrace chce každá přihlášeného uživatele a každý POST token CSRF (pole `csrf_token` nebo hlavička `X-CSRF-Token`, `webapp/security.py`, mimo přihlášení v `webapp/auth.py`).

| Adresa | Metoda | Co dělá |
|---|---|---|
| `/` | GET | moje závody; `?sezona=2026` (pamatuje se v relaci, `?sezona=` = všechny), `?jen=beh\|hotovo\|mapa\|aktivita` |
| `/zavod/oris-<ORIS ID závodu>` | GET | **stálá adresa pro klubový web**: přesměruje na můj rozbor závodu; kdo závod nemá, dostane vysvětlení (404) |
| `/clen/<ORIS ID osoby>` | GET | **stálá adresa pro klubový web**: vlastníka přesměruje na jeho závody, ostatním 403 s odkazem na vizitku |
| `/races/<id>` | GET | stránka závodu: záložky Mapa a úseky, Mezičasy kategorie, Podklady, Nastavení závodu |
| `/races/<id>/data.json` | GET | vše, co kreslí mapa (viz níže) |
| `/races/<id>/map/<course\|maponly>.img` | GET | obrázek mapy z KMZ, jen pro vlastníka závodu, bez nabídky stažení. Stránka se ptá s `?v=<razítko nahrání>`; taková odpověď smí zůstat v prohlížeči rok (`private, immutable`) |
| `/races/<id>/files` | POST | vše k závodu jedním formulářem: soubory `fit` (běh, spáruje se ručně s tímto závodem), `course` (KMZ nebo jpg/png), `maponly` (KMZ), kterékoli z nich; analýza se zařadí jednou. S hlavičkou `X-Requested-With: XMLHttpRequest` vrací `{redirect}` místo přesměrování |
| `/races/<id>/map` | POST | nahrání jedné mapy: `kind=course\|maponly`, soubor `kmz` (KMZ, u `course` i jpg/png) |
| `/races/<id>/activity` | POST | ruční volba aktivity (`activity_id` nebo `auto`) |
| `/races/<id>/reanalyse` | POST | analýza znovu |
| `/races/<id>/relocate` | POST | jen záchytné body, náběhový bod a zarážka znovu (krátká úloha `relocate`; nabízí se, když je rozbor má ze starší verze výpočtu nebo žádné) |
| `/races/<id>/settings` | POST | `osm_mode=forbid\|penalty\|off` a `hatch_mode=forbid\|off`, jen pro tohoto běžce; prázdná hodnota = jako závod. S `scope=event` se mění výchozí hodnota závodu (jen kdo nahrál mapu bez tratě, jinak 403) |
| `/races/<id>/legs/<n>/note` | POST JSON | poznámka k úseku: `planned`, `deliberate_stop`, `lost_contact`, `green`, `fatigue`, `text`. Odpověď (i u čar a občerstvovaček) nese úseky bez `best_route` a `alts` a `plans_pending`. Nová čára `planned` zařadí úlohu `price_plans` |
| `/races/<id>/legs.json` | GET | čísla úseků znovu (bez čar); stránka se ptá, dokud se plánovaný postup oceňuje |
| `/races/<id>/refreshments`, `/…/<rid>` | POST JSON, DELETE | občerstvovačka (sdílená pro závod); smazat ji smí jen ten, kdo ji přidal (jinak 403) |
| `/races/<id>/barriers`, `/…/<bid>` | POST JSON, DELETE | zakázaná čára: `{kind: forbidden\|hard, line: [[lat, lon], …]}` (sdílená pro závod); smazat ji smí jen ten, kdo ji nakreslil |
| `/races/<id>/barriers/<bid>/delete` | POST | totéž z formuláře |
| `/races/new` | GET, POST | závod mimo ORIS |
| `/races/oris` | GET, POST | závod z ORIS podle čísla nebo odkazu (`zavod`): jedno `getEvent`, uloží všechny kategorie; u etapového závodu načte etapy (`getEvent` každé) |
| `/races/oris/<ORIS ID>` | GET, POST | výběr kategorie (`class_id`): jedno `getSplits` (jen když mezičasy kategorie nejsou v DB), nový závod s `entries.class_chosen = 1`; pro zastřešující etapový závod výběr etapy |
| `/races/<id>/class` | POST | „běžel jsem jinou kategorii“: `class_id` = jiná kategorie téhož závodu (mezičasy z ní, rozbor a poznámky dosavadní kategorie se smažou, nový rozbor); bez `class_id` načte kategorie závodu z ORIS |
| `/sync` | POST | načíst závody z ORIS (když už načítání čeká nebo běží, druhé se nezakládá) |
| `/profile/cisla` | POST | jen lokální appka: další registrační číslo po přestupu (`regno`), ověří se v ORIS ([`oris.md`](oris.md)) |
| `/profile/cisla/<číslo>/smazat` | POST | jen lokální appka: smazat ručně přidané číslo, pod kterým není žádný závod |
| `/upload` | GET, POST | `.fit` (víc najednou) nebo zip (celý export Garmin); seznam nahraných běhů, u nespárovaných běhů ze dne a místa závodu tlačítka Přiřadit a Smazat |
| `/activities/<id>/delete` | POST | smazat nahraný běh, který není spárovaný se závodem |
| `/model`, `/model/refit` | GET, POST | osobní model rychlosti |
| `/jobs`, `/jobs.json` | GET | úlohy na pozadí. `jobs.json`: `active` (kolik čeká nebo běží), `running` `[{id, message}]` (co běžící úloha právě dělá); s `?entry=<id závodu>` navíc `progress` (stav úlohy toho závodu česky, prázdné = žádná) a `analysis` (razítko uložené analýzy; změní se, stránka se načte znovu) |
| `/jobs/<id>/retry` | POST | zařadit znovu úlohu, která selhala (analýza, načtení z ORIS, přepočet modelu) |
| `/profile` | GET, POST | jméno; registrační číslo se jen ukazuje, změnit nejde |
| `/password` | POST | změna hesla: `current`, `password`, `password2` |
| `/account/delete` | POST | zrušení vlastního účtu, potvrzené polem `password`; smaže totéž co příkaz `delete-account` |
| `/forgot` | GET, POST | zapomenuté heslo: `oris_regno`, `code` (jednorázový kód z příkazu `reset-code`), `password`, `password2`; bez přihlášení |
| `/login`, `/register`, `/logout` | GET, POST | účet: registrace registračním číslem ORIS a kódem od správce (`oris_regno`, `code`, `password`, `password2`; jedno číslo = jeden účet; `/register?regno=…&kod=…` formulář předvyplní), přihlášení registračkou nebo původním jménem |
| `/ob-static/…` | GET | `base.css`, `ob.css`, `les.css`, `app-icons.svg`, `ob-logo.svg`, `ob.js`, `map.js`, Leaflet. Stránky je odkazují s otiskem obsahu (`?v=…`) a prohlížeč si je pak smí nechat rok; bez otisku se ptá pokaždé |

### Odkazy na klubový web (`webapp/club.py`, `OB_CLUB_URL`)

| Odkud | Kam |
|---|---|
| závod z ORIS (seznam i stránka závodu) | `/zavod/oris-<ORIS ID závodu>` |
| menu „Moje výsledky“ | `/archiv?clen=<ORIS ID osoby>` |
| menu „Moje vizitka“, profil | `/clen/<ORIS ID osoby>` |
| menu „Závodní centrum“ | `/` |

Ven dál vedou odkazy na ORIS (`Zavod?id=`, `Vysledky?id=` na `oris.ceskyorientak.cz`), OResults (když ho ORIS u závodu uvádí v `Links`) a Livelox (`LiveloxID`).

### `data.json`

```
maps        {maponly, course}: url obrázku, corners [levý horní, pravý horní, levý dolní] jako [lat, lon], header_px
course      [{lat, lon}] start, kontroly, cíl
track       {t, lat, lon, speed, punch}
legs        [{n, name, a, b, time, official, straight, run, climb, stops, best, line, best_route,
              loss_total, loss_route, loss_exec, parts, in_model, flags, explain, note,
              alts [{time, dist, climb, delta, route}], balanced, mistake {type, label, text, at}, attack {lat, lon, label} | null, beyond {label, text, parts [{lat, lon, label, line}]} | null, crossed {text, at} | null,
              ws {loss, mistake, index, ref},
              generic {differs, apart, time, time_avg, gain, dist, climb, side, reason {kind, cls, pct, weight} | null, text_cs, text_en, route} | null,
                 (postup průměrného běžce, oroute/generic.py: time = tvým modelem, gain = time − tvůj nejlepší; route jen když se liší)
              relocate {features [{kind, label, lat, lon, point, where, back}], lost {i, at, text, near {lat, lon, i}} | null} | null}]
              note.plan = {time, dist, climb, path_m, slow_m, delta, off_m, text} | null   (plánovaný postup oceněný modelem)
              attack = náběhový bod před kontrolou, beyond = zarážka za ní; oba jen s relocate. kind: junction, path_end, path,
              stream_path, stream, pond, building, enclosure, settlement, clearing, open_edge, hilltop, knoll, depression, pit,
              landform, boulder, water_pit, well, tree, stand, object (české názvy: webapp/texts.py, FEATURES)
totals      {route, mistake, fatigue, deliberate}
refreshments [{id, lat, lon, source, by, mine}], barriers [{id, kind, line, by, mine}]
osm {lines [{kind, what, line}], crossings [[lat, lon]]}, rerouting, plans_pending
areas       [[[lat, lon], …], …]   zakázané prostory přečtené ze šrafování mapy s tratí
```

## Cizí služby

Vše jsou veřejná data. Uživatelská data (stopy, poznámky, mapy) se nikam neposílají.

| Služba | Volání | Kdy | Cache | Vypnutí |
|---|---|---|---|---|
| ORIS | `getUser?rgnum=`, `getUserEventEntries?userid=`, `getEvent?id=`, `getSplits?classid=` | registrace (jen `getUser`), „Načíst závody z ORIS“ | závody, kategorie a mezičasy v databázi; na třídu se ptá jednou, na zastřešující etapový závod jednou | `OB_ORIS_URL` |
| ČÚZK DMR 5G | `…/dmr5g/ImageServer/exportImage` (TIFF, `F32`, WGS 84) | první analýza s mapou bez tratě u českého závodu | `dem/event_<id>_cuzk.npz` | `OB_DEM=aws` |
| AWS Terrain Tiles | `elevation-tiles-prod/terrarium/15/x/y.png` | závody mimo Česko, nebo když ČÚZK neodpoví | `dem/event_<id>.npz` | (není, je to záloha) |
| Overpass (OSM) | jeden dotaz na obdélník mapy, viz `oroute/osm.py` | první analýza s mapou bez tratě | `osm/event_<id>.json` | `OB_OSM=0`, nebo u závodu „nepoužívat“ |

Z `getEvent` se čte `Name`, `Date`, `Place`, `Discipline`, `LiveloxID`, `GPSLat`, `GPSLon`, `Locations` (místa závodu, pro párování aktivit), `Links` (OResults), `Classes`, `Stages`, `Stage1…7`, `ParentID` (etapové závody). Z `getUserEventEntries` i `RegNo` (číslo, pod kterým přihláška byla). Podrobnosti, přestup a etapové závody: [`oris.md`](oris.md). Z `getSplits` řádek každého běžce: `ResName`, `RegNo`, `ResClub`, `ResPlace`, `ResTime`, `StartTime`, `FinishTime`, `TotalTime1…n`.

## Databáze (SQLite, `webapp/schema.sql`)

| Tabulka | Obsah | Čí |
|---|---|---|
| `users` | účet, registrační číslo (jedno číslo = jeden účet, unikátní index; číslo účtu nejde přepsat, trigger `users_regno_fixed`), ORIS ID, vlastní model kopců; `reset_hash`, `reset_until`, `reset_tries` (jednorázový kód k novému heslu, jen hash) | uživatel |
| `user_regnos` | všechna registrační čísla účtu (po přestupu i staré), ORIS ID a jméno podle ORIS, odkud číslo je (`ucet`, `rucne`, `oris`); jedno číslo = jeden účet | uživatel |
| `events` | závod; `links`, `locations`, mapa bez tratě; `osm_mode`, `hatch_mode` = výchozí nastavení závodu pro běžce bez vlastního; `stage_parent`, `stage_n`, `stage_count` u etapy etapového závodu | **sdílené** |
| `oris_umbrellas` | zastřešující etapové závody z ORIS (jen seznam etap, závodem nejsou) | **sdílené** |
| `classes` | kategorie, mapa s tratí | **sdílené** v kategorii |
| `class_splits` | mezičasy všech běžců kategorie z ORIS | **sdílené** (veřejná data) |
| `refreshments`, `barriers` | občerstvovačky, ruční zakázané čáry | **sdílené** pro závod |
| `activities` | `.fit` soubory | uživatel |
| `entries` | já v kategorii závodu: oficiální čas, mezičasy, spárovaná aktivita; `own_osm_mode`, `own_hatch_mode` = moje nastavení závodu (NULL = jako závod) | uživatel |
| `analyses`, `legs` | výsledek analýzy (v `legs.data` i záchytné body kontroly a bloudění) | uživatel |
| `leg_notes` | poznámky k úseku; `planned` = nakreslený plán, `plan` = jeho ocenění modelem (NULL, dokud ho pracovní proces nespočítá) | uživatel |
| `speed_models` | osobní model (historie) | uživatel |
| `jobs` | fronta úloh; u běžící úlohy je v `message`, co právě dělá, u hotové výsledek | uživatel |
| `photos` | poslední nahraná fotka mapy k závodu (zmenšená, s ohniskem v EXIF) a body kliknuté při ručním usazení (`points`, JSON `[[kontrola, u, v]]`); smaže se, když KMZ nahradí mapu kategorie | uživatel |

Sloupce přidané po první verzi (`events.links`, `locations`, `osm_mode`, `hatch_mode`, `leg_notes.plan`, `entries.own_osm_mode`, `own_hatch_mode`, `users.reset_hash`, `reset_until`, `reset_tries`, `classes.course_source` (`kmz` | `image` | `photo` | `manual`), `course_rms`, `course_n`, `course_edge_m` (přesnost mapy z obrázku nebo fotky)) doplní starší databázi `webapp/db.py` při startu. Druhy úloh ve frontě: `sync_oris`, `import_upload`, `analyse`, `refit_model`, `georef_map` (usazení obrázku nebo fotky; s `payload.points` ručně podle bodů), `price_plans` (ocenění plánovaných postupů závodu), `relocate` (záchytné body, náběhový bod a zarážka znovu, bez hledání postupů). V `analyses.summary.relocate` je verze výpočtu záchytných bodů (`oroute.relocate.VERSION`).

Soubory ve složce `OB_INSTANCE`: `fit/user_<id>/`, `maps/event_<id>/` (KMZ a vedle každého malý `.json` s rohy mapy pro stránku; u mapy z fotky ještě `.course.json`, trať z usazení pro `analyze.py --course`), `photos/` (fotky k ručnímu usazení), `races/entry_<id>/` (výstupy skriptů bez obrázků), `models/user_<id>/`, `dem/`, `osm/`, `terrain/` (přečtený terén mapy bez tratě, soubor na závod), `hatch/` (zakázané prostory přečtené z mapy s tratí, soubor na kategorii), `incoming/` (nahrané soubory čekající na zpracování; po zpracování se mažou).

## Nastavení (proměnné prostředí)

| Proměnná | Výchozí | Význam |
|---|---|---|
| `OB_INSTANCE` | `./instance` (v Dockeru `/data`) | databáze a soubory |
| `OB_URL_PREFIX` | `/ob` | cesta, pod kterou aplikace běží (prázdné = kořen) |
| `OB_CLUB_URL` | nenastaveno | kam vedou odkazy na klubový web |
| `OB_PROXY` | `0` | `1` = věřit hlavičkám `X-Forwarded-*` jedné proxy před aplikací; přihlašovací cookie se pak posílá jen přes https (`Secure`) |
| `OB_SECRET_KEY` | náhodný, uložený v instanci | klíč relací; počítají se z něj i kódy k registraci |
| `OB_REGISTRATION` | `1` | `0` zavře registraci; jinak je otevřená těm, kdo mají kód své registračky |
| `OB_MAX_UPLOAD_MB` | `4096` | největší nahrávaný soubor |
| `OB_ORIS_URL` | `https://oris.ceskyorientak.cz/API/` | ORIS |
| `OB_DEM` | `auto` | `auto`, `aws`, `cuzk` |
| `OB_OSM` | `1` | `0` = nestahovat překážky z OSM |
| `OB_CLUB_PRIOR` | `0` | `1` = činitele terénu vycházejí z průměru oddílu |
| `OB_DEV` | (není) | vývoj: šablony se načítají znovu |

## Skripty (bez webu)

```
python analyze.py COURSE.kmz RUN.fit OUT [--official official.json] [--no-images]
python bestroute.py MAPONLY.kmz OUT/course.json RUN.fit OUT/best [--dem aws|cuzk|auto] [--barriers b.json] [--alternatives 2]
                    [--no-images] [--samples-only] [--terrain-cache FILE] [--generic [auto|all|terrain]]
python -m oroute.hatch COURSE.kmz areas.json             # zakázané prostory ze šrafování; areas.json jde dát do --barriers
python -m oroute.planned MAPONLY.kmz OUT PLANS.json RESULT.json [--dem …] [--terrain-cache FILE]   # čas nakreslených postupů podle modelu
python -m oroute.relocate MAPONLY.kmz OUT RESULT.json [--dem …] [--terrain-cache FILE] [--barriers b.json] [--debug SLOŽKA]
                                                          # záchytné body u kontrol, náběhový bod, zarážka a bloudění;
                                                          # --debug kreslí výřezy mapy. Bodové značky čte oroute/symbols.py
python -m oroute.personal MODEL.json */fit_samples.npz --check
python tools/jointfit.py */best/leg_samples.npz           # zkouška společného modelu vynecháním závodu
```

Správa účtů z příkazové řádky (v kontejneru `web`):

```
flask --app webapp.wsgi seed-demo JMENO --password HESLO     # ukázkové čtyři závody pro účet
flask --app webapp.wsgi invite REGISTRACKA [DALSI ...] [--site https://web]   # kód k registraci a odkaz s vyplněným formulářem
flask --app webapp.wsgi reset-code REGISTRACKA [--site https://web]           # jednorázový kód k novému heslu (24 hodin)
flask --app webapp.wsgi delete-account JMENO_NEBO_REGISTRACKA          # vypíše, co by se smazalo
flask --app webapp.wsgi delete-account JMENO_NEBO_REGISTRACKA --yes    # smaže účet a vše, co patří jen jemu
```

`--no-images` vynechá obrázky pro čtenáře zpráv (`overlay_*.jpg`, `best_*.jpg`, `terrain.png`); web je nepotřebuje a vždy ho používá. `--samples-only` skončí po zápisu vzorků pro osobní model (`fit_samples.npz`, `leg_samples.npz`), žádné postupy nehledá. `--terrain-cache FILE` uloží přečtený terén a příště ho vezme ze souboru, dokud se nezmění mapa nebo `oroute/terrain.py`.

S `--official` bere `analyze.py` pořadí kontrol z oficiálních časů (poloha z hodinek v okamžiku ražení); bez něj z fialových čar jako dřív, nad 20 kontrol přibližným hledáním.

Bez nových voleb dávají skripty na mapách s 1,33 m na pixel stejné výstupy jako dřív (`tests/golden`). U Petřvaldu (0,59 m na pixel) je od 7. 10. zlatý `best_legs.csv` nový: čtení terénu se řídí rozlišením mapy.
