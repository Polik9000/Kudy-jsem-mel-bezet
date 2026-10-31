# Běží celá analýza jen ve skriptech? (kontrola 2026-10-06)

Krátce: **ano, kód nikde nevolá Clauda ani žádné AI API** (prohledáno, žádný `anthropic`/`openai`). Vysvětlení „proč je postup lepší“ píše skript podle pravidel (`explain()` v `bestroute.py`). Dvě věci ale dosud dělal Claude ručně: opravu pořadí kontrol a vytažení .fit ze zipu. Obě jsou teď ve skriptech. Zbytek ručních kroků je seznam níže.

## Krok po kroku

| Krok | Stav | Kde / návrh |
|---|---|---|
| Čtení mapy a georeferencování z KMZ | skript | `oroute/kmzmap.py` |
| Nalezení kontrol, startu a cíle na mapě | skript | `oroute/course.py` |
| **Pořadí kontrol** (Pohora bylo zčásti obrácené, Petřvald celé obrácené a cíl se počítal jako kontrola) | **nově skript** | Dřív Claude ručně psal `course_fixed.json`. Nově `order_by_track` porovná fialové čáry se stopou GPS a opraví to sám. Ověřeno: Pohora i Petřvald vyjdou přesně jako ruční opravy, E4 a E5 se nezmění. |
| **Vytažení .fit z Garmin exportu** | **nově skript** | `garmin-matching/extract_fit.py EXPORT.zip OUT číslo_aktivity` |
| Mezičasy, chyby, obrázky | skript | `analyze.py` |
| Nejlepší postup, ztráta trasa/provedení | skript | `bestroute.py` |
| Text „proč je postup lepší“ | skript (pravidla) | `explain()` v `bestroute.py`. Je anglicky; pro web stačí přeložit šablony vět do češtiny, AI netřeba. |
| Model sklonu z běžných běhů | skript | `oroute/slopefit.py` |
| Sloučení osobního modelu ze všech závodů | skript | `oroute/personal.py`; seznam souborů se zatím píše ručně, nově to dělá `run_race.py --refit` |
| Celý závod jedním příkazem | **nově skript** | `run_race.py` (analýza, nejlepší postupy, volitelně přepočet modelu). Pohora z čistých vstupů vyšla identicky. |
| Párování závodů s aktivitami | skript | `garmin-matching/match.py` (vstup `my_runs.html`; na webu místo toho taťkova databáze) |

## Stav k 7. 10. 2026

Odpověď na otázku v nadpisu platí dál: žádné volání AI v kódu ani při běhu aplikace. Z osmi bodů seznamu níže:

| Bod | Stav |
|---|---|
| 1. Dohledání v ORIS | hotovo, `webapp/oris.py` |
| 2. Oficiální mezičasy místo odhadu z GPS | hotovo, `oroute/official.py`; navíc mezičasy celé kategorie, `oroute/splits.py`, a od 7. 10. z nich jde i pořadí kontrol |
| 3. Zakázané přechody | hotovo návrhem A (ruční čára v aplikaci) a železnice s dálnicí z OpenStreetMap; návrh B (rozpoznání symbolů z mapy) ne |
| 4. Výběr závodu k analýze | odpadl, analyzuje se vše, k čemu je mapa a běh |
| 5. Shrnutí v README | nahrazeno stránkou závodu |
| 6. Stažení KMZ z Livelox | ručně, záměrně |
| 7. Mapy bez KMZ | hotovo pro mapu s tratí (`oroute/georef.py`); mapa bez tratě z obrázku ne |
| 8. Nehotové funkce | hotové: webová aplikace, plánovaný postup, komentář u úseku, typ chyby u kontroly a návrh náběhového bodu |

Poznámka „Drobnost, která sedí“ na konci už neplatí doslova: výška hlavičky Livelox (145 px) není natvrdo, mapa si ji nese sama (`GeoMap.header_px`), aby šly použít i obrázky bez hlavičky.

Nově ruční krok žádný nepřibyl. Co zbývá, je v `docs/co-zbyva.md`.

## Co pořád není ve skriptu, s návrhy (seznam z 6. 10.)

1. **Dohledání v ORIS** (Livelox ID závodu, kategorie, oficiální mezičasy, název závodu pro `--title`). Dělal to Claude přes web. Návrh: malý `oris.py`, který volá veřejné ORIS API (`getEvent`, `getSplits`, `getUserEventEntries`) obyčejným HTTP. Z cloudu je ORIS pro skripty blokovaný, takže ho napíšu a otestuju až u tebe lokálně (Claude Code).
2. **Oficiální mezičasy místo odhadu z GPS.** Dnes se čas na kontrole odhaduje z nejbližšího průběhu GPS. Návrh: když jsou mezičasy z ORIS, brát je jako pravdu a GPS jen přiřadit. Také by to hlídalo počet kontrol.
3. **Zakázané přechody** (železnice v Petřvaldu 14–15). Model o nich neví. Návrh A: v aplikaci uživatel jedním tahem nakreslí zakázanou čáru a přepočítá se. Návrh B: rozpoznat symbol železnice a fialové šrafování zakázaných prostor z mapy podle barev ISOM (jako zbytek terénu).
4. **Výběr, který závod analyzovat** (shortlist dělal Claude). Na webu odpadá: seznam závodů je v taťkově databázi a analyzuje se vše, k čemu je mapa a běh.
5. **Shrnutí v README** (tabulky „ztráta ~24 min“ apod.) psal Claude. Na webu je nahradí stránka generovaná z `best_legs.csv` a `legs.csv`.
6. **Stažení KMZ z Livelox** zůstává ručně, záměrně (Livelox mapy přes API nedává). Na webu stačí jedno nahrání mapy na závod pro celý oddíl.
7. **Mapy bez KMZ** (JPG z mapy.ceskyorientak.cz) zatím nejdou. Návrh: napasovat obrázek na mapu podle GPS stop (bez AI, jen geometrie).
8. **Ještě nehotové funkce**: krok 4 (pomoc „ztracen u kontroly“), samotná webová aplikace, kreslení plánovaného postupu a komentář u úseku.

## Drobnost, která sedí
Horních 145 px obrázku je hlavička Livelox a kód je přeskakuje natvrdo. Zkontrolováno na všech 4 mapách: hlavička je u všech stejně vysoká, takže to je v pořádku.
