# CLAUDE.md: Kudy jsem měl běžet

Rozbor orientačního běhu z Garmin `.fit`, mapy (KMZ z Livelox, snímek, fotka) a oficiálních časů ORIS. Lokální
aplikace pro Windows a macOS (`desktop/`, Flask v `webapp/`) a výpočet v Pythonu (`oroute/`, `analyze.py`,
`bestroute.py`, `run_race.py`). Bez LLM a placených API, jen pravidla a geometrie. Popis v `README.md`,
dokumentace (česky) v `docs/`.

## Kde se vyvíjí (od 7. 11. 2026)

- **Jen tady**, v `Polik9000/Kudy-jsem-mel-bezet`. Nová větev z `main`, pull request do `main`.
- Soukromé repo `Polik9000/OB_tracker` je **archiv**: nic do něj nepushuj, nezakládej v něm větve ani PR
  a nezrcadli do něj změny. Starší historie a rozhodnutí tam zůstávají ke čtení.
- **Žádná data do gitu**: mapy, `.fit`, Garmin export, `tests/golden/`, `.obzavod`, databáze. Kde data leží
  a jak se s nimi testuje: [`docs/data-lokalne.md`](docs/data-lokalne.md). `git add` jen konkrétních souborů,
  nikdy `git add -A` přes složky s daty a nikdy `git add -f`.

## Testy a linter

```sh
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
python -m pytest -m "not slow" -q -p no:cacheprovider      # rychlé testy
python -m pytest -m slow -q -p no:cacheprovider tests/test_regression.py   # pomalé, jen s daty, po částech
```

- GitHub Actions (`.github/workflows/testy.yml`) pouští ruff a rychlé testy bez dat; testy se značkou
  `needs_data` nebo `slow` se tam přeskočí. S daty (v `data/` a `tests/golden/`, nebo `OB_TEST_DATA`) běží všechny.
- Nový test, který potřebuje skutečný závod, označ `@pytest.mark.needs_data`. Test, kterému stačí „nějaký závod“,
  vezme `inputs("pohora")` z `tests/races.py`: bez dat dostane umělý závod z `tests/synthetic.py` (`tests/README.md`).
- Úkol je hotový, až projde ruff a rychlé testy. Pomalé testy pusť (s daty), když se mění `oroute/`, `analyze.py`,
  `bestroute.py`, `run_race.py` nebo `webapp/services/runner.py` / `handlers.py`.
- Zlaté soubory (`tests/golden/`, mimo git): `tests/make_golden.py` jen schválně, s důvodem v `docs/validace.md`.

## Konvence

- Kód, komentáře a docstringy anglicky. Dokumentace v `docs/`, commity a texty pro uživatele česky, krátké věty
  bez žargonu.
- **Rozhraní je česky i anglicky.** Každý nový text pro uživatele obal: `_("...")` v Pythonu a šablonách,
  `{% trans %}...{% endtrans %}` v šablonách, `T("...")` ve skriptech `webapp/static/*.js`. Anglický text přidej do
  `webapp/lang_en.py` (`EN`, skripty `EN_JS`). Co chybí, vypíše `python tools/i18n_extract.py`; hlídá to
  `tests/test_i18n.py`.
- Python 3.12, `ruff` podle `ruff.toml` (řádek 125). Žádné ORM, SQL ručně (`webapp/db.py`, SQLite).
- Verze knihoven pevně v `requirements.txt`. Novou knihovnu jen když je nutná, se zápisem licence v `docs/zavislosti.md`.
- Výpočet patří do `oroute/` a skriptů, `webapp/` jen volá (`webapp/services/runner.py`). Skripty jdou pustit bez webu.
- **ORIS je hlavní zdroj** (start, cíl, mezičasy, kategorie). Jen GPS je záloha pro závody mimo ORIS.
- Když se změní výsledek pro stejný vstup, zvedni verzi (`bestroute.VERSION`, `relocate.VERSION`, `lost.VERSION`,
  `oroute/personal.SAMPLES`). Aplikace pak nabídne přepočet starších rozborů.
- Aplikace sama nikam neposílá data (`docs/soukromi.md`, hlídá `tests/test_soukromi.py`).
- `docs/rozhodnuti.md`: historie rozhodnutí, jen přidávat na konec.
- Nic placeného, žádné LLM API, žádné klíče v kódu.

## Kde co je

- `oroute/`: výpočet (mapa, trať, terén, model rychlosti, postupy, záchytné body, Ztratil jsem se, usazení fotky
  a snímků). `webapp/`: Flask, `services/` (úlohy, ORIS, Garmin, soubory), `views/`, `templates/ob/`, `static/`.
- `desktop/`: spouštěč lokální aplikace a balení (PyInstaller, MSIX). Instalátory staví
  `.github/workflows/instalatory.yml` (`docs/instalatory.md`), stránka ke stažení je `docs/index.html` (GitHub Pages).
- `tools/`: měřicí a kontrolní skripty. `tests/`: testy (`tests/README.md`).
