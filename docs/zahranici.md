# Zahraničí: výsledky, mezičasy a mapy

Průzkum z 23. 11. 2026. Kód se podle něj zatím nemění. Většina tvrzení je ověřená skutečnými dotazy na API.
Co ověřit nešlo, je označené [neověřeno].

## Hlavní zjištění

1. **Mapy jsou všude stejné jako u nás**: KMZ z Livelox, fotka papírové mapy, výjimečně RouteGadget.
2. **Chybí náhrada za ORIS** (start, mezičasy, kategorie). Aplikace jiný zdroj výsledků nezná a v kódu není
   import IOF XML. Mimo ORIS spadne na zálohu „jen GPS“.
3. **Univerzální formát je IOF XML 3.0** (ResultList se `StartTime` a `SplitTime`). Veřejně a bez klíče ho dávají
   WinSplits a Navisport. Vyexportuje ho každá časomíra (OE, MeOS, OLA, Pirilä). Jeden import pokryje Švédsko,
   Finsko, Dánsko i další.
4. **Eventor** (Švédsko, Norsko, IOF, Austrálie) bez klíče nejde. API vrací 403 a klíč patří organizaci (klubu),
   ne člověku. Webové stránky Eventoru chrání Cloudflare.

## Ověřené zdroje výsledků

| Stát | Zdroj | Bez klíče? | Co dá | Mapa |
|---|---|---|---|---|
| Švédsko (a kdo tam nahraje) | **WinSplits**: `https://obasen.orientering.se/winsplits/api/events/<id>/resultlist/xml` | ano | IOF XML 3.0 se `StartTime` a `SplitTime` | ne |
| Švédsko, Norsko, IOF, Austrálie | Eventor API `/api/results/event/iofxml?includeSplitTimes=true` | ne (403, klíč klubu) | IOF XML 3.0 | ne |
| Rakousko | **ANNE**: `https://anne-api.oefol.at/v1/event/<id>/results` | ano (dokumentace píše token, čtení jde bez něj) | JSON: `starttime`, `splittimes` (kód kontroly, čas). U některých akcí `splittimes: null` | ne |
| Finsko | **Navisport**: `https://www.navisport.com/api/events/<id>/results?format=iof-xml-3.0` | ano, dokončené akce | IOF XML 3.0 se `StartTime` a `SplitTime` | ne |
| Dánsko | O-Result API (`api.o-result.com`, bez mezičasů) → pole `winSplitsId` → WinSplits XML | ano | IOF XML 3.0 | ne |
| Británie | **RouteGadget 2** u klubů: `…/rg2/rg2api.php?type=events`, `?type=maps`, `?type=event&id=` | ano | JSON: start, mezičasy, kontroly v pixelech mapy, postupy | **ano**: obrázek + world file (WGS84), u novějších map |
| Švýcarsko | o-l.ch, stránka s mezičasy | ano, ale ochrana proti robotům, export nenalezen | pevný text | ne |
| Slovensko | is.orienteering.sk | nezjištěno, firewall | asi PDF | ? |
| všude (živé výsledky) | LiveResults API | ano | jen rádiové kontroly | ne |

## Švédsko

- **Výsledky**: nejlehčí je WinSplits. Funguje, když pořadatel mezičasy nahrál, ve Švédsku je to běžné. Eventor
  jen s klíčem klubu, který si uživatel zadá sám.
- **Mapa**: KMZ z Livelox, když je stažení povolené, jinak fotka nebo snímek.
  - Omaps (databáze svazu) mapu jen ukazuje, bez tratě a bez stažení.
  - Klubové archivy DOMA mají často mapy s tratí, ale jsou roztroušené.
- **Pozor**:
  - hodně map je v měřítku 1:7 500 (mládež, veteráni) a 1:15 000 (H/D21 klasika);
  - fialová podle tisku tíhne k čisté magentě, hledání tratě má brát rozsah magenta až fialová.

## Norsko, Finsko, Dánsko

- **Norsko**: Eventor jako ve Švédsku (klíč klubu). Norské XML ne vždy odpovídá normě.
- **Finsko**: výsledky z Navisport (veřejné API) nebo z Pirilä (export IOF XML). Mapy v Reittihärveli (finský
  RouteGadget) s tratí, kalibrace [neověřeno].
- **Dánsko**: O-Result bez mezičasů, ty jsou přes WinSplits. O-Track bez veřejného API.

## Doporučené pořadí (návrh)

1. **Import výsledků v IOF XML 3.0** ze souboru i z odkazu (WinSplits, Navisport). Největší přínos za nejméně práce.
2. **ANNE** pro Rakousko.
3. **RouteGadget 2** (Británie, Finsko): mapa s kalibrací i mezičasy v jednom.
4. **Eventor** s klíčem klubu, který si uživatel zadá sám. Klíč nikdy v kódu.

Každá nová služba znamená řádek v [soukromi.md](soukromi.md) a v `tests/test_soukromi.py`. Mapy se nestahují
automaticky: patří klubům a uživatel si přinese vlastní.

## Co zbývá ověřit

Zadání pro další relaci:

```
Pokračuj v průzkumu rozšíření aplikace do zahraničí. Nic neměň v kódu.
Přečti docs/zahranici.md a docs/mapa-bez-kmz.md. Ověř přímo na webu:
1. Slovensko: is.orienteering.sk – API nebo XML s mezičasy, nebo jen PDF?
2. Švýcarsko: o-l.ch – jde stáhnout CSV nebo XML s mezičasy?
3. Finsko: Reittihärveli (finský RouteGadget 2) – mají mapy world file a funguje rg2api.php?
4. Dánsko: o-track.dk – jdou mapy stáhnout?
5. Švédsko: rozlišení obrázku Omaps /se/Home/MapImage/{id}.
6. Najdi švédskou akci, která je na WinSplits i na Livelox, a zkontroluj, že XML z WinSplits má start
   a všechny kontroly jedné kategorie.
Výsledek doplň do docs/zahranici.md a shrň ho česky.
```
