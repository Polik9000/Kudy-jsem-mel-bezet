# Jak zautomatizovat analýzu pro web (návrh, 2026-10-06)

**Stav k 7. 10. 2026.** Tohle byl návrh před stavbou aplikace; nechávám ho, jak byl, a tady je, co z něj platí:

| Část návrhu | Stav |
|---|---|
| 1. Seznam závodů z ORIS | hotovo (`getUser`, `getUserEventEntries`, `getEvent`, `getSplits`); napojení na tátovu databázi ne, aplikace běží vedle jeho webu a ptá se ORIS sama |
| 2. Aktivity: ruční `.fit` a celý Garmin export | hotovo, párování i podle vzdálenosti od centra závodu; z exportu zůstanou jen běhy spárované se závody |
| 2. Strava, Garmin API, knihovny s heslem | nedělá se (Strava na přání Tobiase, ostatní z důvodů v tabulce) |
| 3. Mapy ručně, ale sdíleně | hotovo: mapa bez tratě je sdílená pro závod, odkaz do Livelox u závodu |
| 3. JPG nebo fotka mapy | hotovo jinak, než je tu psáno: obrázek se usadí podle koleček kontrol a stopy v oficiálních časech ražení (`oroute/georef.py`), jen jako mapa s tratí |
| 4. Tratě z Livelox API | nedělá se (přání Tobiase); kontroly se dál čtou z fialového tisku. Pořadí se od 7. 10. bere z oficiálních mezičasů ORIS a polohy z hodinek, čáry a stopa ho kontrolují; bez mezičasů z čar a stopy |
| Tok pro uživatele | platí, jen se přihlašuje do naší aplikace pod `/ob`, ne do klubového webu, a analýza běží hned ve frontě, ne v noci |
| „Co by bylo potřeba udělat“ | hotovo vše kromě tabulek v tátově databázi (máme vlastní) a Stravy s Livelox klíčem |

Aktuální popis je v `docs/web-aplikace.md`.

Krátce: seznam závodů, kategorie, mezičasy a odkaz na Livelox jdou plně automaticky (ORIS a taťkova databáze). Aktivity jdou poloautomaticky. Mapy zůstanou ruční, ale stačí jedno nahrání na závod pro celý oddíl.

## 1. Seznam závodů (plně automaticky)
- Taťkův web už má v SQLite výsledky všech členů (datum, kategorie, čas, odkaz na ORIS). Analýza se napojí přímo na jeho databázi, nic se nenahrává.
- Doplní se z ORIS API (z cloudu funguje):
  - `getUser?rgnum=BFM0903` → ORIS id běžce, `getUserEventEntries?userid=…` → jeho závody. (API je na `https://oris.ceskyorientak.cz/API/`, stará adresa `oris.orientacnisporty.cz` jen přesměrovává.)
  - `getEvent?id=…` → `LiveloxID`, kategorie (`Classes` s délkou, převýšením a počtem kontrol), GPS místa, dokumenty.
  - `getSplits?classid=…` → oficiální mezičasy. Ty jsou přesnější než časy na kontrolách, které dnes odhadujeme z GPS.

## 2. Aktivity (.fit)
| Způsob | Automatické? | Poznámka |
|---|---|---|
| Ruční nahrání .fit | ne | Funguje vždy, pro každé hodinky. Zůstane jako záloha. |
| Nahrání celého Garmin exportu (zip) | jednorázově | Na historii. Párování se závody už máme (`garmin-matching/match.py`). |
| **Strava API (OAuth)** | **ano** | Většina lidí má Garmin propojený se Stravou. Webhook dá vědět o novém běhu, stáhnou se proudy (GPS, čas, výška, tep). Nová aplikace má limit na pár uživatelů, víc až po schválení Stravou. Podmínky Stravy od 2024 dovolují ukázat data jen tomu uživateli, kterému patří, takže porovnání tras mezi běžci by šlo jen z nahraných .fit. |
| Garmin Connect Developer Program | ano | Oficiální, dává přímo .fit, ale je pro firmy a chce schválení. Pro oddílový web nepravděpodobné. |
| Neoficiální knihovna `garminconnect` | ano | Potřebuje heslo uživatele k Garminu. Nedoporučuji: porušuje podmínky a web by držel cizí hesla. |

Doporučení: ruční .fit plus jednorázový zip na start, Strava jako druhá fáze, až to bude používat víc lidí. Aktivita se ke závodu přiřadí sama podle data a oficiálního času z databáze (stejná logika jako `match.py`).

## 3. Mapy (zůstane ručně, ale sdíleně)
- Livelox mapy automaticky stahovat nejde a nebudeme to obcházet (API je záměrně nedává, robots.txt zakazuje prohlížeč).
- Úleva: mapa bez tratě je pro všechny kategorie závodu stejná. Stačí, když ji nahraje **jeden člověk z oddílu**, a analýza poběží všem, kdo ten závod běželi.
- Web z `LiveloxID` vygeneruje přímý odkaz do Livelox, takže běžec jen klikne, exportuje KMZ a nahraje.
- JPG z mapy.ceskyorientak.cz nebo fotka mapy: napasuje se podle GPS stop. Funguje hůř (bez přesného georeferencování) a čím víc stop od různých běžců, tím přesnější.

## 4. Tratě (kontroly)
- Dnes je čteme z fialového tisku v KMZ s tratí, takže každá kategorie potřebuje svoje KMZ a pořadí se někdy plete.
- **Livelox API klíč** (žádost na info@livelox.com): dává tratě jako IOF XML se souřadnicemi kontrol. Pak stačí jen mapa bez tratě a nahrávání per kategorie odpadne. Doporučuji o klíč požádat za oddíl.
- Bez klíče: KMZ s tratí jako dnes, pořadí kontrol opravit podle mezičasů z ORIS (počet kontrol) a GPS.

## Navržený tok pro uživatele webu
1. Přihlásí se na oddílový web (taťka už zná členy a jejich registračky).
2. Jednou nahraje Garmin export nebo jednotlivé .fit (později propojí Stravu).
3. Web sám spáruje běhy se závody a ukáže seznam: „analýza hotová“, „chybí mapa (nahrát)“, „chybí běh“.
4. U závodu bez mapy klikne na odkaz do Livelox, stáhne KMZ a nahraje. Mapa se uloží pro celý oddíl.
5. Cron v noci spustí analýzu (stejný kód jako teď: `analyze.py` + `bestroute.py`) a výsledek se objeví na stránce závodu.

## Co by bylo potřeba udělat
- Zabalit `oroute` jako Python balík s jednou funkcí „analyzuj závod (mapa, trať, stopa) → výsledek“ místo skriptů.
- Tabulky v taťkově DB: aktivity, mapy (podle ORIS id závodu), výsledky analýz.
- Napojení na ORIS (`getEvent`, `getSplits`) a párování aktivit.
- Později: Strava OAuth a Livelox API klíč.
