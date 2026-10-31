# Závislosti a licence (stav 7. 10. 2026)

Repozitář je soukromý. Žádný kód z projektů pod GPL nebo AGPL (QuickRoute, Karttapullautin, AItraceur, MeOS, OpenOrienteering Mapper) v něm není; z nich a z článků jsou převzaté jen metody, kód je vlastní. Při přidání knihovny sem zapiš verzi a licenci.

## Knihovny Pythonu (`requirements.txt`)

| Knihovna | Verze | K čemu | Licence |
|---|---|---|---|
| numpy | 2.5.3 | výpočty | BSD 3-Clause |
| scipy | 1.18.1 | Dijkstra, filtry obrazu, interpolace | BSD 3-Clause |
| pillow | 12.3.0 | čtení map (PNG, JPG, TIFF z ČÚZK), kreslení | MIT-CMU (HPND) |
| fitdecode | 0.11.0 | čtení `.fit` z hodinek | MIT |
| Flask | 3.1.3 | webová vrstva (s ní Werkzeug, Jinja2, MarkupSafe, itsdangerous, click, blinker) | BSD 3-Clause |
| gunicorn | 26.2.0 | server | MIT |
| tzdata | 2026.5 | časová pásma v kontejneru | Apache 2.0 |

## Jen pro vývoj (`requirements-dev.txt`)

| Knihovna | Verze | K čemu | Licence |
|---|---|---|---|
| pytest | 9.1.1 | testy | MIT |
| ruff | 0.16.10 | linter (**přidáno tuto noc**) | MIT |

Tuto noc nepřibyla žádná knihovna, kterou by aplikace potřebovala k běhu. Věci, které by se nabízely jako knihovna, jsou napsané přímo: grafy (SVG ve `webapp/services/charts.py`), pořadová korelace a metoda WinSplits (`oroute/splits.py`), hledání křížení cest (`oroute/mistakes.py`), podobnostní transformace a RANSAC (`oroute/georef.py`), čtení Overpass a ČÚZK (`urllib` ze standardní knihovny).

Noc s fotkami map (větev `foto-mapy`) nepřidala nic: homografie (normalizovaný DLT), poměr stran listu z perspektivy,
okraj listu, vyrovnání světla a narovnání fotky jsou v `oroute/georef.py` nad numpy, scipy a Pillow (OpenCV ne);
průchod webem dělá `tools/shot.mjs` přes Chrome DevTools, ne Playwright. HEIC (fotky z iPhonu) by chtěl
`pillow-heif`; místo něj aplikace řekne, jak fotku uložit jako JPEG.

## JavaScript (přibalený v `webapp/static/vendor/`, nic se nenačítá z cizí domény)

| Knihovna | Verze | Licence |
|---|---|---|
| Leaflet | 1.9.4 | BSD 2-Clause |
| Leaflet.ImageOverlay.Rotated | 0.2.1 | Beerware podle repozitáře autora (Iván Sánchez Ortega). **Neověřeno tuto noc**: přibalený soubor licenci neobsahuje, knihovnu přidala už předchozí verze aplikace. Před nasazením otevřít `LICENSE` v jeho repozitáři. |

Nástroj `tools/shot.mjs` (screenshoty) potřebuje Node 22+ a Chrome; do aplikace nepatří.

## Vzhled

| Soubor | Původ | Poznámka |
|---|---|---|
| `webapp/static/skob.css` | kopie `/static/skob.css` klubového webu (repozitář `skob-results`, píše táta) | nesmí se upravovat ručně; test hlídá shodu s `docs/reference/skob-klubovy-web.css` |
| `webapp/static/skob-logo.svg`, `skob-ikony-sprite.svg` | logo a ikony klubového webu | totéž |

Jak se kopie udržuje při změně klubového webu, je otázka na tátu (`docs/co-zbyva.md`).

## Data z cizích služeb

| Zdroj | Co bereme | Podmínky | Kde se to uvádí |
|---|---|---|---|
| ORIS API (`oris.ceskyorientak.cz/API`) | závody, kategorie, mezičasy, místa, odkazy | veřejné, bez klíče; dokumentace o limitech mlčí. Ptáme se po jednom s prodlevou 0,4 s a odpovědi ukládáme. | patička stránek |
| ČÚZK DMR 5G (`ags.cuzk.gov.cz`, ImageServer `dmr5g`) | výšky terénu pro české mapy | otevřená data, CC BY 4.0, uvádět „© ČÚZK“. Jeden dotaz na mapu, výsledek v cache. | patička stránek |
| AWS Terrain Tiles (Mapzen terrarium) | výšky terénu jinde a jako záloha | otevřená data; zdroje a jejich uvedení viz `github.com/tilezen/joerd/blob/master/docs/attribution.md` | patička stránek |
| OpenStreetMap přes Overpass (`overpass-api.de`) | železnice, dálnice, ploty, přejezdy, mosty, podchody | ODbL, povinné „© přispěvatelé OpenStreetMap“. Jeden dotaz na závod, výsledek v cache; veřejný Overpass snese do 10 000 dotazů denně. | patička stránek, mapa, záložka Nastavení závodu |
| Livelox | nic strojově; uživatel si sám exportuje KMZ a nahraje ho | API klíč ani stahování map nepoužíváme (zadání) | upozornění u mapy |

Uložená testovací data: `tests/fixtures/oris/` (odpovědi ORIS, cizí jména nahrazená), `tests/fixtures/osm/petrvald_overpass.json` (© přispěvatelé OpenStreetMap, ODbL), `tests/fixtures/cuzk/dmr5g_petrvald.tif` (výřez 350 × 230 m, © ČÚZK, CC BY 4.0).

## Mapy závodů

Mapy jsou díla pořadatelů a mapařů. Aplikace je ukazuje jen přihlášeným, kteří závod běželi, nenabízí stažení a u mapy na to upozorňuje. V repozitáři jsou čtyři mapy v `data/` (soukromý repozitář, tvoje závody).
