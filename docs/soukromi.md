# Soukromí: co appka stahuje a co odchází ven

Appka na vlastním počítači (`OB_LOCAL=1`, instalátor) nemá žádnou telemetrii, hlášení chyb ani kontrolu
aktualizací. Tvoje stopy z hodinek, mapy, výsledky, poznámky a modely jsou jen ve složce s daty (Windows
`%LOCALAPPDATA%\KudyJsemMelBezet`, macOS `~/Library/Application Support/KudyJsemMelBezet`) a odtud se nikam neposílají.

Appka z internetu jen stahuje veřejná data. Co přesně a co při tom odchází:

| Služba | Adresa | Kdy | Co odchází | Co se nikdy neposílá |
|---|---|---|---|---|
| ORIS (Český svaz orientačních sportů) | `oris.ceskyorientak.cz/API/` | po zadání registračního čísla, načtení závodů, přidání závodu podle čísla | metoda (`getUser`, `getUserEventEntries`, `getEvent`, `getSplits`) a registrační číslo, ORIS ID uživatele, číslo závodu nebo kategorie | stopa, soubory, mapy, poznámky |
| ČÚZK, výškopis DMR 5G | `ags.cuzk.gov.cz/arcgis2/rest/services/dmr5g/ImageServer/exportImage` | jednou pro každý závod v Česku při analýze | obdélník kolem mapy (souřadnice rohů) | stopa, jméno |
| AWS Terrain Tiles, výškopis mimo Česko | `s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png` | jednou pro každý závod mimo Česko (nebo když ČÚZK neodpoví) | čísla dlaždic mapy (z toho jde poznat jen oblast, kterou mapa pokrývá) | stopa, jméno |
| OpenStreetMap přes Overpass | `overpass-api.de/api/interpreter`, záložní `overpass.private.coffee/api/interpreter` | jednou pro každý závod, pokud je zapnuté `OB_OSM` (výchozí) | obdélník kolem mapy | stopa, jméno |
| Garmin Connect, Personal API (jen když ho zapneš) | `personal.connectapi.garmin.com` | jen když v Nahrát běhy vložíš svůj klíč Personal API a stahuješ běhy z Garmin Connect | tvůj klíč (výměna za dočasný token), dotaz na seznam aktivit za zvolené období a stažení vybraných aktivit | mapy, poznámky, výsledky; klíč a token zůstávají jen ve složce s daty |

Požadavky na ORIS a výškopis jsou uložené v databázi a ve složce s daty a podruhé se nestahují. Odkazy na ORIS,
Livelox, Garmin Connect (stránka s klíčem Personal API) a OpenStreetMap (autorství v patičce) i „Zkontrolovat nové vydání“ v Profilu jsou obyčejné odkazy, které
otevře tvůj prohlížeč, až na ně klikneš. Appka sama na ně nevolá.

Kam registrační číslo jde: do ORIS, protože jinak nejde najít tvoje závody. Je to veřejné číslo, pod kterým jsi
ve výsledcích. Chceš-li appku bez něj, nech pole prázdné a přidávej závody podle jejich čísla v ORIS nebo ručně.

## Bez internetu

Fungují mapy, nahrávání běhů, uložené závody, modely a všechny stránky. Nejde načíst ORIS a analýza nových závodů,
kterým chybí uložený výškopis (appka řekne česky, že výškopis nešel stáhnout, a analýzu jde pustit znovu). Jednou
spočítané závody jsou vidět dál.

## Jak je to hlídané

`tests/test_soukromi.py` prochází zdrojové kódy a kontroluje, že v nich nejsou jiné webové adresy, než jaké jsou
v tabulce, a že dotazy na výškopis, OpenStreetMap a ORIS obsahují jen to, co tabulka říká. Přidat novou službu tedy
znamená přidat ji do tabulky i do testu.
