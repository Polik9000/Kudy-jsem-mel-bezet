# Plán a průběh noci 6. → 7. 10. 2026

Pracovní větev `web-aplikace` (založená z `main`, protože při startu neexistovala). Výchozí stav: 41 rychlých a 22 pomalých testů prošlo.

## Co už ve `webapp/` fungovalo (zjištěno čtením kódu a průchodem v prohlížeči)

- Účty (jméno + heslo, CSRF), profil s registračním číslem ORIS.
- ORIS: `getUser`, `getUserEventEntries`, `getEvent`, `getSplits` (z mezičasů se bral jen řádek běžce).
- Seznam závodů se stavem, ruční závod mimo ORIS.
- Nahrání `.fit` a zipu (i celý Garmin export), párování podle data, času a oficiálního startu, ruční volba aktivity.
- Nahrání KMZ s tratí (na kategorii) a bez tratě (na závod, sdílené).
- Fronta úloh a `worker`, který volá `analyze.py` a `bestroute.py`.
- Stránka závodu: Leaflet, překryv mapy, stopa podle ztráty, jeden nejlepší postup, tabulka úseků, vysvětlení česky.
- Poznámky k úseku a jejich vliv na ztrátu i model; sdílená značka občerstvovačky.
- Osobní model: tabulka terénů a kopců, přepočet po analýze, vlastní sklon z Garmin exportu.

## Co chybělo

Vzhled klubového webu, tmavý režim, CSP; cesta `/ob` a stálé adresy podle ORIS ID; účet z registračky; párování podle polohy; mezičasy celé kategorie a jejich stránka; alternativy postupů a citlivost; typ chyby; zakázané přechody a nastavení závodu; obrázek mapy bez KMZ; nejistota modelu a graf sklonu; migrace starší databáze.

## Stav kroků

| Krok | Stav | Poznámka |
|---|---|---|
| 0. Příprava | hotovo | plán, vývojové prostředí `obdev`, nástroj na screenshoty |
| 1. Vzhled klubového webu | hotovo | `skob.css` beze změny, `ob.css` přes proměnné, hlavička, menu, patička, tmavý režim, CSP, mapa přes celou šířku; screenshoty v `docs/reference/nase-aplikace/` |
| 2. Seznam závodů se stavem | hotovo | „chybí aktivita / chybí mapa / hotovo“, sezóna, hledání |
| 2. Nahrání `.fit`, zipu, párování | hotovo | navíc vzdálenost od centra závodu (`GPSLat`, `GPSLon`, `Locations`); ověřeno na soukromém exportu (10 074 souborů) |
| 2. KMZ a jpg/png | hotovo | obrázek jen jako mapa s tratí (viz 3.6) |
| 2. Stránka závodu | hotovo | alternativy, typ chyby, mezičasy, odkazy na ORIS, OResults a klubový web |
| 2. Poznámky k úseku | hotovo (bylo) | |
| 2. Osobní model | hotovo | nejistota, graf křivky sklonu, zkouška vynecháním závodu |
| 2. Nastavení závodu | hotovo | přepínač OSM, ruční zakázané a těžko překonatelné čáry, občerstvovačka |
| 2. `/ob/zavod/oris-<ID>`, `/ob/clen/<ID>`, odkazy | hotovo | |
| 3.1 Mezičasy kategorie, WinSplits | hotovo | `oroute/splits.py`, tabulka `class_splits`, grafy ve vlastním SVG |
| 3.2 Model proti kategorii | hotovo | pořadová korelace a odchylky v aplikaci i ve `validace.md` |
| 3.3 Výškopis ČÚZK | hotovo | služba odpovídá; web `auto`, skripty výchozí `aws` |
| 3.4 Zakázané přechody z OSM | hotovo | železnice a dálnice; ploty stažené, ale vypnuté (neověřený přínos) |
| 3.5 Kontrolní sada postupů | hotovo | rychlé testy na umělém terénu, pomalé na závodech |
| 3.6 Umístění mapy bez KMZ | hotovo | Pohora 16/16 kontrol, Petřvald 19/19, rohy mapy do 20 m |
| 3.7 Typ chyby, náběhový bod | hotovo s výhradou | prahy neladěné proti poznámkám (žádné nebyly) |
| 3.8 Model rychlosti | změřeno, nezapnuto | společný odhad chybu nezlepšil; modul zůstává jako pokus |
| 3.9 Únava, obtížnost závodu | změřeno, nezapnuto | únava chybu zvýšila; na obtížnost je málo dat |
| 4. Testy, linter, dokumentace | hotovo s výhradou | 103 rychlých testů, ruff bez nálezů; **úplný běh pomalých testů nedoběhl** (viz níže) |

## Průběžné kontroly

- Po každém kroku rychlé testy (41 → 56 → 64 → 88 → 95 → 102 → 103) a commit.
- Pomalé testy: výchozí stav 22 prošlo za 16 minut. Po krocích 3.1 až 3.7 jsem pustil všech 31; **systém běh ukončil kvůli nedostatku paměti** (souběžně počítalo vývojové prostředí). Znovu jsem ho nepouštěl. Náhradní ověření je v `docs/co-zbyva.md` a `docs/validace.md`.
- Kontroly z nových pomalých testů vyhodnocené nad už spočítanými analýzami odhalily okliku na Petřvaldu 2–3. Nejdřív jsem ji mylně přičetl plotům z OSM (commit `697d734`); po jejich vypnutí zůstala. Příčina je starší: silnice se na mapě s vysokým rozlišením čte jako budova (`docs/co-zbyva.md`).

## Závěrečný scénář na čisté kopii (7. 10. 2026, 1:30)

Větev naklonovaná do prázdné složky, `docker compose up --build` s novým svazkem dat, pak přes HTTP:

| Krok | Výsledek |
|---|---|
| Účet registračním číslem `BFM0903` | založen, jméno „Tobiáš Otta“ vzato z ORIS |
| Načtení z ORIS | 107 závodů za 166 s, mezičasy kategorií uložené |
| Adresa z klubového webu `/ob/zavod/oris-8989` | přesměruje na můj závod |
| Nahrání `run.fit` (Pohora) | spárováno, shoda jistá; záložka Mezičasy kategorie funguje ještě bez mapy |
| Nahrání KMZ s tratí a bez tratě | uložené, analýza se zařadila sama |
| Stránka závodu | stav hotovo, čas 50:22, 17 úseků, nejlepší postupy, alternativy u 9 úseků, typ chyby u 4, výškopis ČÚZK, hlavička CSP |
| Poznámka k úseku 1–2 (ztráta kontaktu s mapou) | uložená, ztráta volbou 6:06 se přesunula do chyb, přežije nové načtení |
| Stránka modelu, stránka úloh | fungují |

Zkušební svazek jsem po scénáři smazal. Tvůj výchozí svazek `ob_tracker_ob_data` zůstal nedotčený a zastavený, jak jsem ho našel.

## Po noci (7. 10. 2026 dopoledne)

| Změna | Proč |
|---|---|
| Přihlášení registračkou zkouší všechny účty s tím číslem a vezme ten, ke kterému patří heslo. | Dva starší účty měly stejnou registračku a číslo znamenalo jen ten starší. |
| Na jednu registračku jen jeden účet (unikátní index, kontrola v registraci a profilu); příkaz `delete-account`. | Přání Tobiase. |
| Oba účty s `BFM0903` ve svazku `ob_tracker_ob_data` smazány, záloha v `private/`. | Aby si Tobias založil jeden nový. |
| Dokumentace srovnaná se stavem; v `docs/pruzkum.md` je u každého doporučení, co je hotové a co zbývá. | |

Rychlých testů je 109. Úplný běh pomalých testů na konečném kódu stále neproběhl.
