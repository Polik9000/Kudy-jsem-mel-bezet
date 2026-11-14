# Data jen na vlastním počítači

Od 7. 11. 2026 se vyvíjí jen v tomhle veřejném repozitáři. Soukromé repo `Polik9000/OB_tracker` je **archiv**:
nic dalšího se do něj nepushuje a nové pull requesty míří jen sem.

Do veřejného repa nepatří žádná data:

- mapy (KMZ z Livelox, snímky, fotky papírových map): jsou dílem pořadatelů a mapařů;
- běhy z hodinek (`.fit`, Garmin export) a nic, co z nich vzniklo;
- zlaté výsledky skutečných závodů (`tests/golden/`), soubory `.obzavod`, databáze aplikace.

Hlídají to tři věci: `.gitignore` (složky a přípony níž), test `Žádná data v repu` v GitHub Actions
(`.github/workflows/testy.yml`), a zvyk: `git add` jen konkrétních souborů, nikdy `git add -f` u dat.

## Kam data dát

Nejjednodušší je nechat je **uvnitř vlastní kopie repa, ve složkách, které git ignoruje**. Všechny skripty, nástroje
v `tools/` i testy je tam najdou bez nastavování:

```
Kudy-jsem-mel-bezet/            klon veřejného repa (git)
  data/                         čtyři referenční závody: azymut-e5, azymut-e4, pohora, petrvald
    pohora/course.kmz           (každý závod: course.kmz, maponly.kmz, run.fit)
  tests/golden/                 zlaté výsledky těch čtyř závodů a jejich výškopis (dem_cache.npz)
  private/                      Garmin export (private/Garmin/...), zálohy databáze
  data-extra/                   další mapy z Livelox na ověřování pravidel
  kontrola/                     výstupy nočních kontrol a měření
  races/, out/                  výstupy skriptů
```

Všechno kromě `data/README.md` je v `.gitignore`, takže `git status` tyhle soubory vůbec neukáže.

**Přesun z archivu OB_tracker** (jednou, na Windows v PowerShellu; cesty uprav podle sebe):

```powershell
$old = "$HOME\Documents\GitHub\OB_tracker"
$new = "$HOME\Documents\GitHub\Kudy-jsem-mel-bezet"
robocopy "$old\data"         "$new\data"         /E /XF README.md
robocopy "$old\tests\golden" "$new\tests\golden" /E
robocopy "$old\private"      "$new\private"      /E
robocopy "$old\data-extra"   "$new\data-extra"   /E
robocopy "$old\kontrola"     "$new\kontrola"     /E
```

`robocopy` jen kopíruje, v archivu nic nemaže. Pak v novém klonu `git status`: nesmí ukázat žádný z těch souborů.

### Jiná složka mimo repo (volitelně)

Testy umí data číst i z libovolné složky, kterou řekne proměnná `OB_TEST_DATA` (`tests/races.py`,
`tests/README.md`). Uvnitř jsou závody jako složky a zlaté soubory v `golden/`:

```
kudy-data/
  azymut-e5/ azymut-e4/ pohora/ petrvald/     course.kmz, maponly.kmz, run.fit
  golden/                                     obsah tests/golden
```

```
OB_TEST_DATA=C:/cesta/k/kudy-data python -m pytest
```

Nástroje v `tools/` a `data-extra/` ale počítají se složkami uvnitř repa, proto je výchozí doporučení první varianta.

### Záloha dat

Data nejsou v žádném gitu na GitHubu, takže záloha je na tobě. Stačí kopie složky (disk, OneDrive).
Kdybys chtěl historii a zálohu na GitHubu, založ si **malé soukromé repo jen na data** (např. `kudy-data`,
soukromé, bez kódu) se strukturou z varianty `OB_TEST_DATA` výše. Velké soubory (Garmin export, mapy) by do něj
patřily přes Git LFS nebo vůbec ne; `private/Garmin` stačí mít jen na disku.

## Testy

| kde | co běží |
|---|---|
| GitHub Actions (každý PR a push do `main`) | ruff a rychlé testy bez dat; testy se značkou `needs_data` nebo `slow` (např. `test_best_routes_unchanged`) se samy přeskočí |
| u tebe, s daty v `data/` a `tests/golden/` | všechno: `python -m pytest -m "not slow"` a po částech `python -m pytest -m slow …` |

Přeskakování řídí `tests/conftest.py` (`have_data()` v `tests/races.py`). Nový test, který potřebuje skutečný
závod, označ `@pytest.mark.needs_data`; test, kterému stačí „nějaký závod“, použije umělé závody
z `tests/synthetic.py` a poběží i v CI (`tests/README.md`).
