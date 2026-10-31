# Kontrola tras očima (noc 9. → 10. 10. 2026, větev `kontrola-tras`)

## Shrnutí

**Co se opravilo**

- Analýza na dalších mapách už nekončí výpisem chyby: tři chyby z webu jsou zreprodukované a opravené, špatný vstup končí českou větou (kolo 0).
- Start tratě je střed startovního trojúhelníku (Pohora byla 44 m vedle, Petřvald 93 m).
- Čte se i trať vytištěná pro sprint (kolečka 12 m).
- Řada teček, plot se třemi čárkami v řadě a obrys zakázaného prostoru už nejsou cesta; plot stojí 90 s.
- Kolem rybníků není pás bažiny.
- Plánovaný postup zná stejné překážky jako nejlepší a řekne, co kříží.
- Zarážka bere směr z vlastní stopy; paseka kontroly zarážkou není.
- Čtení terénu bere třetinu paměti.

**Co zůstává**

- Skály a srázy se nečtou (na mapě Bludiště po nich postupy místy vedou).
- Hustá kamenitá půda se čte jako cesta.
- Ploty bez tří čárek v řadě zůstávají cestou (Petřvald S–1 u pole).
- Čtyři nenalezené oplocenky (Pohora u 5, Petřvald u 15) se dál nepoznají.
- Sprintové mapy se čtou pravidly pro lesní mapy.

**Co jsem neudělal, i když to bylo v zadání**

- **Každý úsek v každém kole jsem neprohlédl.** Všech 71 obrázků čtyř původních závodů (67 kontrol a 4 doběhy) jsem prošel v kole 1; v dalších kolech jen úseky, kde se změnil nejlepší postup, a u zarážek jeden výřez. Z 113 úseků šesti extra závodů jsem na obrázku viděl asi dvanáct.
- **Web jsem zkontroloval jen zčásti** (bod 9 seznamu). Čtyři ukázkové závody jsem po všech změnách nechal spočítat úlohou webu ve vlastní složce vývojové instance (`/data/kontrola-tras` ve svazku `obdev_ob_data`, účet `kontrola`, heslo `kontrola-heslo`): všechny čtyři úlohy doběhly, verze postupů 3 a záchytných bodů 5, Petřvald s železnicí z OSM (2 čáry, 3 přechody), 7 šrafovanými plochami a 8 oplocenkami. Pět snímků přes `tools/shot.mjs` bez chyb JavaScriptu (Petřvald 1–2 a 10–11 na 1440 px, 1–2 na 390 px, Pohora 14–15 na 1440 a 390 px); **prohlédl jsem dva** (Petřvald 1–2 na 1440 px, Pohora 14–15 na 390 px); snímek `web-petrvald-1-2.jpg`. Postup, stopa, možnosti, zakázané plochy a zarážka na Petřvaldu 1–2 sedí s obrázky ze skriptu. Větu u selhané úlohy a značku u plánu jsem na stránce neviděl, jen v testech.
- **Čtení srázů** jsem nenapsal ani jako pokus s testem na nakreslené mapě.
- **Kol bylo pět, ale kola 4 a 5 byla jen Petřvald** (doladění obrysu zástavby), ne všechny závody.

Počty: čtyři původní závody = 67 kontrol (71 úseků s doběhy). Extra: 10 map, 6 spárovaných s během a spočítaných (113 úseků), 4 přeskočené (tabulka níže).

Obrázky před a po (`docs/reference/kontrola-tras/`):

- `pohora-14-15-pred.jpg` / `pohora-14-15-po.jpg`: tečkované hranice pasek už nejsou cesty.
- `petrvald-10-11-pred.jpg` / `petrvald-10-11-po.jpg`: plot zástavby (žlutě) už není cesta, ulice ano.
- `gps-e2-9-10-pred.jpg` / `gps-e2-9-10-po.jpg`: tečkované pole na sprintové mapě už není černá plocha „cest“ (zbylé černé jsou srázy).
- `petrvald-ploty.jpg`: přehledový list všech osmi nalezených plotů na Petřvaldu.


## Jak se to pouštělo

Všechno v kontejneru se zdrojákem připojeným z disku a s vývojovým svazkem, vždy jen jeden výpočet najednou:

```
docker compose -p obdev -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps -T web <příkaz>
```

`docker compose run --rm web …` ze zadání jsem nepoužil: pouští obraz s kódem z doby sestavení a připojuje svazek `ob_tracker_ob_data`.

Jeden závod jednoho kola (obrázky jsou v `kontrola/kolo-N/<závod>/`, složka není v gitu):

```
python run_race.py COURSE.kmz MAPONLY.kmz RUN.fit kontrola/kolo-N/zavod --title "…" --alternatives 2
python -m oroute.relocate MAPONLY.kmz kontrola/kolo-N/zavod kontrola/kolo-N/zavod/best/relocate.json --debug kontrola/kolo-N/zavod/zarazky
python tools/kontrola.py kontrola/kolo-N/zavod MAPONLY.kmz COURSE.kmz --proti kontrola/kolo-(N-1)/zavod
```

`tools/kontrola.py` udělá ke každému úseku `useky/NN_A-B.jpg`: mapa s nejlepším postupem (modře), stopou (červeně) a možnostmi (světle modře); totéž přes přečtené třídy terénu; totéž s překážkami (neprůchodné fialově, těžko překonatelné oranžově, zakázané olivově, budovy tmavě červeně, voda modře, cesty tak, jak se přečetly, černě). Dlouhý úsek má navíc kusy `_dK.jpg` v plné velikosti. `prehled.jpg` je mapa s tratí, přečtená trať a stopa. S `--proti` vypíše, které obrázky jsou bajtově stejné jako minule; ty jsem znovu neprohlížel.

## Kolo 0: proč analýza dalších map padala

### Párování map z `data-extra/` s běhy z exportu (`tools/parovani.py`)

V `data-extra/` je deset párů (mapa bez tratě `NÁZEV.kmz`, mapa s tratí `NÁZEV, KATEGORIE.kmz`; každá mapa má jednu kategorii, takže není co volit). Export z Garminu (`private/Garmin/…/UploadedFiles_0-_Part1.zip`) má 299 aktivit, z toho 292 s GPS. Běh se hledá podle polohy: aktivity, které začínají do 3 km od okraje mapy, a z nich ta, jejíž stopa prošla do 25 m nejvíc koleček přečtených z mapy s tratí. Výsledek je v `data-extra/parovani.json` (mimo git, stejně jako rozbalené `.fit` v `kontrola/fits/`).

| Mapa | Běh z exportu | Jistota | Důvod |
|---|---|---|---|
| Grand prix Silesia - E2, H16B | …326843095804.fit | jistá | jediný běh na mapě, 93 % z 27 koleček |
| Grand prix Silesia - E3, H16B | …327087135593.fit | jistá | 81 % z 16 koleček, další běh na mapě 31 % |
| Grand prix Silesia - E4, H16B | …327278184065.fit | jistá | 90 % z 19, další 5 % |
| Mistrovství oblasti MSK ve sprintu, H16 | …328730680304.fit | jistá | 100 % z 21 |
| Slezská zimní liga, HA | …312051319035.fit | jistá | 100 % z 28, další 7 % |
| Žebříček B-Morava, oblastní žebříček, H16B | …341473143517.fit | jistá | jediný běh na mapě, 100 % z 18 |
| Grand prix Silesia - E1, H16B | žádný | – | na mapě leží jen stopy E3 a E4, které přes ni vedou (48 % a 13 %); běh z 17. 4. 2025 v exportu polohu nemá |
| 3. Zkouška sirén 2024_2025, HA | žádný | nejistá | nejlepší stopa prošla 43 % koleček a patří Slezské zimní lize; běh z 8. 1. 2025 jen 21 % |
| 10. SZL MSKS, HA | žádný | – | žádná aktivita z exportu na mapě neleží (nejbližší začíná 2,6 km od ní) |
| Mistrovství oblasti v nočním OB, H14C | žádný | – | závod je z 20. 10. 2023, nejbližší aktivita exportu začíná 4,7 km od mapy |

Počítá se tedy šest extra závodů, čtyři jsou přeskočené.

### Reprodukce tří chyb

Pro každou mapu jsem z ORIS (veřejné API, odpovědi jen v `kontrola/oris/`) vzal datum, čas startu a mezičasy, nechal `garmin.match_race` vybrat aktivitu z celého exportu, jako to dělá web, a pustil `analyze.py` přesně jako úloha webu (`--no-images --official …`), nejdřív s kódem z `main`:

| Závod (datum) | Co web spáruje | `main` | Příčina | Po opravě |
|---|---|---|---|---|
| Grand prix Silesia E3 (19. 4. 2025) | správný běh, jistota nízká („aktivita −8 min proti času závodu“) | **chyba 1**: `ValueError: cannot convert float NaN to integer` | Opravdu neúplný záznam, ne párování: hodinky spuštěné 8 min 38 s po startu. Oficiální časy se nepoužily, stopa se rozsekala podle nejbližších přiblížení, úseky bez bodů měly rychlost NaN. | doběhne: 53:08, úseky S–1, 1–2 a 2–3 „nedostatek dat“ s oficiálními časy, ostatní podle oficiálních časů |
| Grand prix Silesia E2 (18. 4. 2025) | správný běh, jistý | **chyba 2**: `could not find start triangle / finish` | Sprintová mapa 1:4 000: kolečka mají 12 m, čtečka hledala 30 až 45 m. | doběhne, pořadí z oficiálních časů |
| Mistrovství oblasti ve sprintu (26. 4. 2025) | správný běh | chyba 2 | totéž | doběhne |
| Slezská zimní liga (15. 2. 2025) | správný běh | chyba 2 | totéž | doběhne |
| Žebříček B-Morava (15. 6. 2025) | správný běh | chyba 2 | totéž; navíc se pět „koleček“ našlo ve šrafování zakázaného prostoru | doběhne se 16 kontrolami jako v ORIS |
| 3. Zkouška sirén (8. 1. 2025) | běh z toho dne (bez oficiálního času, jen podle data) | chyba 2 | totéž; stopa navíc tratí neprochází (do 25 m jen 6 koleček z 26, záznam končí před časem startu z ORIS) | čistá chyba „Záznam z hodinek neprochází kontrolami této tratě…“ |
| Grand prix Silesia E1 (17. 4. 2025) | jediná aktivita toho dne, **bez GPS** | **chyba 3**: `IndexError` ve `fitload.py` | Špatné párování: aktivita bez polohy se párovala s jistotou „nízká“. | čistá chyba „V záznamu není GPS stopa…“; nové párování ji už nevybere („ten den je jen aktivita bez GPS“) |
| Grand prix Silesia E4 (20. 4. 2025) | správný běh | doběhl (ten jediný z deseti) | – | doběhne |
| 10. SZL MSKS (8. 3. 2025), noční OB (20. 10. 2023) | žádná aktivita toho dne | nebylo co počítat | – | – |

Žádná z map nebyla „mapa bez tratě na místě mapy s tratí“, štafeta ani trať v jiné barvě; ty případy jsou ošetřené (věta níže) a zkoušené jen na nakreslené mapě.

### Co se opravilo

| Commit | Co |
|---|---|
| `b83eec1` | Čtení terénu po pásech řádků: stejné třídy (čtyři mapy bajtově), špička paměti na Petřvaldu 4,7 GB → 1,5 GB. Bez toho by mapy z `data-extra/` (až 29 milionů pixelů) spadly na paměť. |
| `cbad3b2` | `load_track`: záznam bez polohy = chyba `no_gps`, nečitelný soubor = `bad_fit`. `match_race` aktivitu bez GPS nebere; když je ten den jediná, závod zůstane bez aktivity s poznámkou. |
| `a4ec04a` | Neúplný záznam. S oficiálními časy: když záznam ukazuje aspoň polovinu kontrol, úseky uvnitř něj se počítají podle oficiálních časů a úseky mimo dostanou značku `no_data` („nedostatek dat“), oficiální čas si nechají a do referenční rychlosti nevstupují. Bez oficiálních časů: úsek, který končí tam, kde začal, a úseky ke kontrole, ke které se stopa nepřiblížila na 150 m, jsou `no_data`. Stopa, která je od kontrol v mediánu dál než 30 m nebo jí chybí víc než polovina úseků, končí chybou `track_off_course`. NaN do výstupu nejde. |
| `ebab67c` | Čtení tratě z mapy: poloměr koleček se bere z uzavřených koleček mapy (aspoň tři stejně velká), takže se čte i sprint; když to nevyjde, zkusí se původní rozsah. Start je střed trojúhelníku nalezeného podle tvaru: toho u první polohy záznamu, a když tam žádný není (hodinky spuštěné jinde), toho, ze kterého vede spojnice. Kolečko s fialovou uvnitř (šrafování) se zahodí. Kontroly mimo záznam se zařadí podle spojnic. |
| `680a78c` | Skripty končí u špatného vstupu řádkem `OB-ERROR <kód>: …` a kódem 2 (`oroute/errors.py`); `runner._run` z něj udělá českou větu, co s tím, a výpis nechá pod rozbalovátkem „Podrobnosti“ (stránka závodu i seznam úloh). Neznámá chyba: „Výpočet selhal (analyze.py); podrobnosti jsou níže.“ |
| `6fd7dfa` | `tools/parovani.py`. |

České věty (`webapp/texts.py`, `ANALYSIS_ERRORS`): `no_gps` „V záznamu není GPS stopa…“, `no_course_print` „V souboru není vytištěná trať…“, `no_start`, `no_finish`, `track_off_course` „Záznam z hodinek neprochází kontrolami této tratě…“ (s tím, jak daleko stopa od kontrol je a o kolik záznam čas závodu nepokrývá), `bad_fit`.

Rychlé testy na umělých vstupech: `tests/test_fitload.py` (záznam bez polohy, nečitelný soubor, mapa bez fialového tisku, jiný běh než závod, záznam kratší než závod, věta a „Podrobnosti“ u selhané úlohy), `tests/test_course.py` (trať vytištěná pro 1:10 000 i 1:4 000 při třech rozlišeních, nula v čísle kontroly, start s nápovědou u startovní čáry, daleko od startu i bez ní, šrafování, mapa bez tratě, kontroly mimo záznam), `tests/test_official.py` (neúplný záznam s oficiálními časy i bez nich, sprint bez úseku nad 60 m).

### Co se při tom našlo na čtyřech původních závodech (bod 7 kontrolního seznamu)

Start nebyl na svém místě. Dosud to byl „nejhustší fialový shluk u první polohy záznamu“:

| Závod | Start dřív | Start teď | Posun | Co tam bylo |
|---|---|---|---|---|
| Pohora | v číslici „16“ vytištěné přes trojúhelník | střed trojúhelníku | 44 m | S–1 měl přímou vzdálenost 78 m místo 123 m a falešnou značku „postup 2,3× delší než přímka“ |
| Petřvald | fialová čárka startu času | střed trojúhelníku | 93 m | od čárky vede k trojúhelníku značený úsek |
| Azymut E5 | u trojúhelníku | střed trojúhelníku | 6 m | |
| Azymut E4 | u trojúhelníku | střed trojúhelníku | 4 m | |

Proto se ve zlatých souborech změní `course.json` (jen `start`) a v `legs.csv` řádek S–1 (přímá vzdálenost, poměr, očekávaný čas); kontroly, cíl a všechny ostatní řádky jsou stejné. Kde čas začíná aspoň 60 m před trojúhelníkem (Petřvald), začíná nejlepší postup prvního úseku tam, kde začíná stopa, a vede přes trojúhelník: značený úsek musí běžec běžet taky.

### Co jsem se rozhodl nedělat

- **Přednost záznamu, který pokrývá čas závodu, v `match_race`.** Reprodukce ukázala, že chyba 1 nebyla v párování (běh byl správný, jen neúplný).
- **Sprintové mapy (ISSprOM)** se teď přečtou a analýza doběhne, ale čtení terénu je laděné na ISOM (lesní mapy). Jak dopadly, je v zápisech kol.

## Kolo 1

Spočítáno: čtyři závody z `data/` (71 obrázků úseků = 67 kontrol + 4 doběhy do cíle) a šest extra závodů (113 úseků). Čtyři původní jsem prošel celé, obrázek po obrázku, a podezřelá místa ještě ve zvětšení 2 až 8×. Z extra závodů jsem v tomhle kole viděl přehledy a vybrané úseky Grand prix Silesia E2 (sprint) a E3 (les); ostatní až v kole 2.

Úplný seznam je v `kontrola/kolo-1/nalezy.md` (mimo git). Co mělo společnou příčinu:

| Nález | Kde | Příčina | Oprava |
|---|---|---|---|
| Nejlepší postup běží „po cestě“, která je řada teček | Azymut E4 15–16, 18–19 (72 m), 19–20; Pohora 12–13, 13–14, 14–15 (109 m), 15–16, 16–F; Grand prix Silesia E2 (tečkované pole přečtené jako souvislá černá plocha), E3 (kamenitá půda) | `terrain.classify` bral každou černou jako cestu; tečky hranice porostu (416), kultivované plochy a kamenité půdy se dilatací spojily v čáru | `3c5dd0c`: černá značka do 4 m napříč je tečka, ne čárka cesty |
| Plot je „cesta“ | Petřvald S–1 (možnost 2 podél plotu u pole), 10–11 (552 m „po cestě“, velká část je plot zástavby), 6–7 | plot je černá čára jako cesta; poznala se jen uzavřená oplocenka | `3d212d9`: `relocate.fences`, viz níže |
| Pás „bažiny“ kolem úzkých rybníků | Petřvald S–1, 1–2, 16–17, 17–18 | hustota modré se počítala i z modré rybníka | `a9b6b52`: hustota modré pro bažinu bez pixelů vody |
| Start mimo trojúhelník | Pohora (44 m), Petřvald (93 m) | viz kolo 0 | `ebab67c` |
| Ocenění plánu nezná zákazy | všude | `oroute/planned.py` bral jen terén | `02e64e6`: plán čte stejné překážky a `routing.crossed` řekne, co kříží |
| Zarážka: směr z nejlepšího postupu, i když jsem doběhl odjinud; paseka kontroly jako zarážka | Petřvald 2, Azymut E4 12 | pravidlo | `577f794`: směr z vlastní stopy, když ke kontrole doběhla a není na ní bloudění; okraj vlastní paseky do 45 m se nepočítá; část dál než 150 m jen při dvou třetinách paprsků |

Co jsem neviděl na žádném ze 71 obrázků: postup přes budovu, přes vodní plochu, skrz uzavřenou oplocenku, mimo mapu nebo legendou. Petřvald 1–2, 4–5, 14–15 a 16–17 kříží železnici mimo přejezd: skript běží bez `--barriers` (zlaté soubory), web železnici z OSM zná.

### Ploty (`relocate.fences`)

Pravidlo: aspoň tři krátké čárky (2,5 až 10 m) v řadě na téže straně jedné souvislé černé čáry, nejvýš 45 m od sebe. Čárka se pozná od konce: na malé kružnici kolem konce je jeden úzký oblouk černé, na větších pořád jeden, a za délkou čárky kružnice protne čáru dvakrát, obojí před čárkou. Konec cesty druhý oblouk nevidí; konec čárky přerušované cesty vidí další čárku, ale přímo proti sobě; pražec železnice pokračuje i za čáru; vrstevnice a spádnice jsou hnědé.

Kontrola na přehledových listech (`tools/prekazky.py`, každý nález vedle výřezu mapy):

| Mapa | Nalezených plotů | Skutečných | Co to je |
|---|---|---|---|
| Petřvald | 8 | 8 | kusy plotů zástavby a pozemků, jeden plot u pole |
| Azymut E5 | 1 | 1 | plot soukromého pozemku |
| Azymut E4, Pohora | 0 | – | |
| Grand prix Silesia E3/E4 | 2 | 2 | plot zakázaného prostoru, plot zástavby |

Falešný nález žádný. **Úplné to není:** plot u pole na Petřvaldu S–1 má tři čárky, třetí leží u konce přerušované cesty a nepozná se, takže plot zůstal „cestou“; ploty se dvěma čárkami se neberou vůbec. Raději minout než vymyslet: dvě čárky v řadě má i cesta se dvěma krátkými odbočkami.

Neprůchodný plot (518, dvojité čárky) od průchodného (516) nerozlišuji: obojí je „těžko překonatelné“ (`HARD_CROSS_S`, 90 s), ne zakázané. Na mapě 1,33 m na pixel se dvojitá čárka od jednoduché rozeznat nedá.

### Co se neopravilo

- **Skály a srázy (201, 202).** Na čtyřech původních mapách na trasách nejsou. Na Grand prix Silesia E3 (mapa „Bludiště“) jsou: silná černá čára se zoubky se čte jako cesta a nejlepší postup 2–3 vede 42 m „po cestě“, která je sráz. Čtení srázů jsem nenapsal: zoubky mají na mapě 1,33 m na pixel dva až tři pixely a pravidlo, které by je poznalo, by bralo i okraje silných čar silnic. Je to v `docs/co-zbyva.md`.
- **Dvě oplocenky u kontroly 5 na Pohoře** (obdélníky s čárkami dovnitř, přes ně zelené šrafy) se dál nepoznají; postup jimi nevede.

**Oprava nálezu z kola 1:** Azymut E4 11–12 jsem zapsal jako „122 m po hranici porostu“. Ve zvětšení kola 2 je to tenká přerušovaná pěšina, tedy skutečná cesta, a postup se právem nezměnil. Tečkované hranice byly na jiných úsecích téže mapy.

## Kola 2 až 5

**Kolo 2** (všechny čtyři původní závody a tři extra: Grand prix Silesia E2, E3, E4; zbylé tři extra jsem zastavil kvůli času). Co se změnilo proti kolu 1 (`kontrola/tmp/cmp.py`, porovnání výpisů úseků):

| Závod | Změněných postupů | Co |
|---|---|---|
| Azymut E5 | 1 z 13 | 3–4 o 2 s |
| Azymut E4 | 4 z 21 | S–1 2:31 → 1:37 (doběh ke startu se bez oficiálních časů počítá jen do 150 m; záznam začíná dál), 18–19 +6 s (tečky), 8–9 a 10–11 do 3 s |
| Pohora | 2 z 17 | 14–15 +8 s (109 → 34 m po „cestě“), 13–14 +3 s |
| Petřvald | 0 z 20 | ploty nalezené na mapě na žádném postupu neleží; pás bažiny postupy neměnil |
| Grand prix Silesia E2 (sprint) | 11 z 26 | tečkované pole už není „cesta“, časy o 1 až 5 s delší |
| Grand prix Silesia E3, E4 | 0 a 1 | |

Zarážky se změnily u většiny kontrol (směr z vlastní stopy). Viděl jsem jeden výřez (Azymut E5 kontrola 2: vějíř míří tam, kam jsem dobíhal, a končí na potoce a na cestě za kontrolou); ostatní jen ve výpisu.

Nález kola 2: Petřvald 10–11 má pořád 552 m „po cestě“. Na výřezu vede postup po silné černé čáře kolem zástavby, která má čárky dovnitř olivové plochy jen řídce a s rohy mezi nimi, takže ji pravidlo o plotech nenajde. Oprava (`dfcf745` a commit po něm): černá čára do 2,5 m od zakázaného prostoru je jeho obrys, v celé své šířce; okraj zpevněné ulice se nechává.

**Kolo 3** (čtyři původní a Grand prix Silesia E3, E4): obrys v první verzi změnil jen Petřvald 10–11 o 10 m; bral jen vnitřní půlku silné čáry.

**Kolo 4** (jen Petřvald): obrys v celé šířce čáry. Petřvald 10–11 542 → 342 m po cestě, ale 6–7 se zhoršil o 15 s a moje stopa na 10–11 o 1:44: pravidlo vzalo i černé okraje ulic uvnitř zástavby. To je falešný nález, pravidlo jsem zpřísnil.

**Kolo 5** (jen Petřvald): černá do 2,5 m od zpevněné plochy (světle hnědá) se nebere. Petřvald 6–7 je zpět (2:07 proti 2:05), 10–11 má 358 m po cestě a na výřezu je žlutě jen plot zástavby (`petrvald-10-11-po.jpg`). Moje stopa na 10–11 vychází o 24 s pomaleji než dřív (tenké černé čáry mezi pozemky uvnitř zástavby); nechal jsem to tak a zapsal do `docs/validace.md`, část 18.

Co jsem na extra mapách viděl a neopravil: srázy jako cesty (E2, E3, E4), hustá kamenitá půda jako cesta (E4 9–10). Oplocenek je na mapě Bludiště 21; prvních devět na přehledovém listu je skutečných, zbylých dvanáct jsem neviděl.

Kde skončit: po kole 5 nezbylo nic jistého, co by šlo opravit pravidlem bez nového rozpoznávání (srázy, kamenitá půda), a to se od čtvrtého kola dělat nemělo.

# Druhá noc (10. → 11. 10. 2026, větev `kontrola-tras-2`)

Větev je z `kontrola-tras` (ta v `main` na začátku noci nebyla), nic se neslučovalo. Model byl celou noc jeden (`oroute/personal_model.json`, otisk `7b503c49`); větev s Riegelem (`claude/project-thread-ao1vg1`) se nesloučila.

## Shrnutí

**Co se opravilo**

- **`tools/podezrele.py`**: seznam úseků, kde je nejspíš špatně přečtená mapa (část 0). Na začátku 34 podezřelých úseků ze 144 posuzovaných, na konci 28 ze 134 (podle stejných, konečných pravidel nástroje jich na začátku bylo 32 ze 134).
- **Uvnitř zástavby se smí jen po zpevněné ulici**: černá s olivovou po obou stranách je zakázaný prostor, ne cesta; okraj světle hnědé ulice cestou zůstává.
- **Náběhový bod leží uvnitř svého úseku** (Petřvald 8–9 už ho nemá u osmičky).
- **Záchytný bod za oplocenkou** se neukáže, nebo dostane obchůzku místo přímého azimutu; mapa kreslí obchůzku. Oplocenka a rybník se berou od okraje.
- **Mapa nakreslená až k okraji obrázku** už nemá podél okraje pás zakázaného prostoru (našel to seznam podezřelých: cíl sprintu MSK ležel „v zákazu“).
- **Kontrola v uzavřeném místě**: postup vede co nejblíž, ne beze slova přímkou přes domy (našel to seznam: Slezská zimní liga 4–5).
- **Moje stopa pár metrů v zahradě** se oceňuje jako ulice vedle (Petřvald 10–11: 9:30 → 7:03 při naměřených 7:33).

**Co zůstává**

- Srázy a skály se nečtou (pokus s čísly níže), hustá kamenitá půda a ploty se dvěma čárkami také ne.
- Grand prix Silesia E2 má v jednom obrázku dvě mapy; prvních 13 kontrol leží 30 až 150 m od stopy a úseky mezi nimi se nedají hodnotit.
- **Sprintové mapy: šedá budova užší než asi 9 m se čte jako „cesta“ a postup jí místy vede** (sprint MSK 11–12, 13–14, 14–15). Nalezeno při prohlídce kola 2, neopraveno.
- Sprintové mapy: zpevněná plocha (světle hnědá výplň ISSprOM) se čte jako polootevřený prostor, ne jako cesta; tenké pěšiny parku jen zčásti.
- Moje stopa vedená 10 až 20 m vedle cesty se oceňuje terénem vedle cesty (pět úseků skupiny B).

**Co jsem neudělal, i když to bylo v zadání**

- **Části 3, 4 a 5** (srázy, kamenitá půda, ploty se dvěma čárkami) nejsou. U srázů jsem udělal jen měření, které ukázalo, že jediný znak čitelný na mapě 1,33 m na pixel nestačí (níže); rozpoznávání s testem na nakreslené mapě jsem nenapsal. Části 4 a 5 jsem nezkoušel vůbec.
- **Kola s opravami byla tři (1, 2 a 3), ne čtyři.** Kolo 3 je poslední a počítalo všech deset závodů konečným kódem; od kola 0 do kola 3 se u čtyř původních závodů nezměnil žádný nejlepší postup. Kolo 3 jsem dvakrát zastavil a pustil znovu, protože jsem při prohlídce kola 2 našel ještě dvě chyby.
- **Každý úsek dvakrát jsem neotevřel** a u extra závodů jsem viděl 69 obrázků ze 123 (podrobně na konci).
- **Přehledové listy** plotů a oplocenek všech map jsem znovu nedělal.
- **Web** jsem zkontroloval jen na Petřvaldu a čáru obchůzky na mapě jsem na snímku nerozeznal.

Obrázky (`docs/reference/kontrola-tras-2/`): `petrvald-6-7.jpg` a `petrvald-10-11.jpg` (postup po ulici, zástavba bez „cest“), `petrvald-13-zachytne-pred.jpg` / `-po.jpg` (záchytné body kontroly 13), `msk-sprint-19-F-pred.jpg` / `-po.jpg` (cíl v pásu u okraje obrázku), `szl-4-5-pred.jpg` / `-po.jpg` (postup přímkou přes domy a po opravě), `msk-sprint-11-12-budova.jpg` (neopraveno: postup skrz šedou budovu), `bludiste-cerna-sirsi-nez-9m.jpg` (pokus se srázy), `web-petrvald-5-6-obchuzka.jpg` a `web-petrvald-12-13.jpg` (stránka).

Počty: čtyři původní závody = 67 kontrol, 71 úseků. Extra: šest závodů, **123 úseků** (ne 113, jak stálo v minulém zápisu: 26 + 15 + 18 + 20 + 27 + 17).

## Jak se to pouštělo

Stejně jako minulou noc (`kontrola/dc.sh`, vždy jeden výpočet). Kolo = `python kontrola/kolo2.py N` (všech deset závodů po sobě, asi 55 minut, z toho Slezská zimní liga 19), výstupy v `kontrola/noc2/kolo-N/<závod>/` (mimo git). Porovnání dvou kol: `node kontrola/tmp/cmp2.js A B`. Seznam podezřelých:

```
python tools/podezrele.py kontrola/noc2/kolo-N/* --out kontrola/noc2 --name podezrele-zacatek
```

## Část 0: seznam podezřelých úseků

`tools/podezrele.py` čte `best/best.json`, `analysis.json` a `best/relocate.json` každého závodu. Skupina **A**: poměr skutečný čas / čas nejlepšího postupu je aspoň o 15 % pod mediánem závodu a jde aspoň o 10 s. Skupina **B**: model oceňuje moji stopu o víc než 15 % a 10 s nad skutečný čas. Nepočítá se úsek bez dat, se stáním nebo blouděním, bez nalezeného postupu a úsek, jehož stopa je při ražení dál než 40 m od kontroly. Výstup má u každého úseku metry nejlepšího postupu po cestě, na plotu a do 5 m od zakázané plochy a výřez; příčiny se píšou do `…-priciny.csv` a nástroj je vloží do seznamu.

**Výchozí stav (kolo 0, kód z `kontrola-tras`): 34 podezřelých úseků (23 A, 16 B) ze 144 posuzovaných.** Všech 34 výřezů jsem prohlédl. Příčiny:

| Příčina | Úseků | Které | Co s tím |
|---|---|---|---|
| Doběh do cíle (sprint na 30 až 100 m po rovné ploše nebo cestě) | 6 | Žebříček B 16–F, Grand prix Silesia E3 14–F, Petřvald 19–F, Azymut E4 20–F, Azymut E5 12–F, Slezská zimní liga 26–F | Není chyba mapy; model na krátkém doběhu podceňuje. |
| Moje stopa leží 10 až 20 m vedle cesty nebo v hustníku, kterým jsem proběhl | 5 | Azymut E4 2–3, 11–12, 18–19, Pohora 8–9 (60 m přes tmavě zelenou), Petřvald 10–11 (ulice zástavby) | Petřvald opraven (stopa v zahradě = ulice vedle). Ostatní ne: otázka v `co-zbyva.md`. |
| Běh po cestě nebo silnici, na které je model pomalejší než já | 5 | Pohora 15–16, Grand prix Silesia E3 12–13, E4 1–2, Petřvald S–1, 2–3 | Není chyba mapy. |
| Terén rychlejší, než ho model cení (les, zelená s průseky) | 5 | Pohora 9–10, 14–15, Azymut E5 10–11, Azymut E4 19–20, Grand prix Silesia E2 17–18 | Není chyba čtení; cena terénu je věc modelu. |
| **Pás zakázaného prostoru podél okraje obrázku** | 3 | Sprint MSK 19–F a S–1, Slezská zimní liga 23–24 | **Opraveno** (okraj obrázku). |
| Sprintová mapa: dlažba, průchody, pěšiny parku | 4 | Sprint MSK 2–3, 4–5, Žebříček B 3–4, 1–2 | Neopraveno (ISSprOM). |
| Sráz nebo skála čtená jako cesta | 2 | Grand prix Silesia E3 7–8 (36 m po skalní stěně), E4 12–13 | Neopraveno. |
| **Postup přímkou přes domy** (hledání cestu nenašlo) | 1 | Slezská zimní liga 4–5 | **Opraveno.** |
| Stopa u kontrol neleží (dvě mapy v jednom obrázku) | 1 | Grand prix Silesia E2 5–6 | Úsek se teď nepočítá. |
| Start: čas běží před trojúhelníkem, krátký první úsek | 2 | Pohora S–1, Grand prix Silesia E4 S–1 | Není chyba mapy. |

Z 34 podezřelých úseků tedy **5 ukázalo na skutečnou chybu čtení nebo výpočtu** (okraj obrázku 3×, postup přímkou, dvě mapy v obrázku), 2 na srázy a 4 na sprintové mapy. Zástavbu (část 1) seznam jako chybu nejlepšího postupu neukázal: postup na Petřvaldu 6–7 i 10–11 vedl už po minulé noci po ulicích a po opravě se nezměnil.

**Konec (kolo 3):** nástroj se během noci zpřísnil (úsek bez nalezeného postupu a úsek, jehož stopa je při ražení dál než 40 m od kontroly, se nepočítají), proto srovnávám obě kola stejnými, konečnými pravidly (`kontrola/tmp/pod_quick.py 0 3`):

| | Kolo 0 | Kolo 3 |
|---|---|---|
| Posuzovaných úseků | 134 ze 194 | 134 ze 194 |
| Podezřelých | **32** (21 A, 16 B) | **28** (20 A, 12 B) |
| z toho původní závody | 11 A, 7 B | 11 A, 6 B |
| z toho extra závody | 10 A, 9 B | 9 A, 6 B |
| Průměrná odchylka poměru od mediánu závodu | 21,7 % (původní 18,1 %, extra 23,7 %) | 21,2 % (původní 18,0 %, extra 23,0 %) |

Ze seznamu zmizely čtyři úseky: sprint MSK 19–F (okraj obrázku), Slezská zimní liga 4–5 (postup přímkou), Petřvald 10–11 a Žebříček B 1–2 (ocenění stopy v zahradě). Nový nepřibyl žádný, žádný se nezhoršil. **Poměry se k mediánu přiblížily jen nepatrně** (o půl procentního bodu): opravené chyby se týkaly jednotlivých úseků, ne ceny terénu. Zbylých 28 úseků jsou doběhy do cíle, běh po cestě, cena terénu, posun stopy vedle cesty, sprinty a dva úseky se srázy; chyba čtení, kterou bych uměl opravit, mezi nimi podle výřezů není. Původní výstup nástroje ze začátku noci (34 ze 144, starší pravidla) je v `kontrola/noc2/podezrele-zacatek.md`, konečný v `kontrola/podezrele.md` (obojí mimo git).

## Část 1: olivová plocha

Diagnóza ze zadání (92 m postupu 6–7 „u zástavby“, z toho 94 % po třídě `PATH`) seděla, ale ty pixely jsou okraje světle hnědých ulic: postup 6–7 vede od kontroly 6 ulicí na západ, pak ulicí na jih a lesem k sedmičce (`petrvald-6-7.jpg`). Chodby přes pozemky v něm po minulé noci nebyly. Co zbývalo, byly černé čáry uvnitř olivové (obrysy domů, ploty mezi pozemky), které byly dál `PATH` a mřížka je nechávala průchozí; postup jimi mohl vést, jen zrovna nevedl.

Pravidlo (`terrain.classify`): černá, která má olivovou barvu obrázku po obou stranách do 4 px (5 m), je uvnitř zástavby; je `PATH` jen do 2 px od světle hnědé (`terrain.paved`), jinak `OOB`. Obrys celé zástavby dál řeší `mapdata.obstacles`.

Ověření:

- Třídy čtyř map před a po (`kontrola/tmp/cls_dump.py`, `cls_diff.py`): Petřvald 73 534 změněných pixelů (95 % cesta → zakázaný prostor), Azymut E5 1 918, Pohora 1 010, **Azymut E4 0 (bajtově stejný)**; **mimo olivovou (dál než 8 m od ní) 0 na všech čtyřech**. První dvě verze pravidla tuhle zkoušku neprošly (89 až 816 pixelů mimo zástavbu: braly čáru podél zástavby a rušily kusy cest, které u zástavby končí) a jsou opravené.
- Obrázky Petřvaldu 6–7, 10–11, 4–5, 1–2, 14–15: postup vede po ulici nebo mimo zástavbu, přes pozemek nikde. **Nejlepší postupy se nezměnily** (0 z 71 u čtyř původních závodů, kolo 0 → 1).
- **Moje stopa na Petřvaldu 10–11:** po opravě olivové pořád 9:30. Příčina nebyla v čarách, ale v ocenění stopy: stopa vede ulicemi a chybou GPS zabíhá do olivové, kde se oceňovala chůzí. Po opravě „stopa v zahradě = ulice vedle“ vychází **7:03** (naměřeno 7:33; před minulou nocí 9:06). Stejně 6–7: 2:41 → 2:17 (naměřeno 2:52).
- **Sprint (ISSprOM):** olivová (zahrady, dvory, soukromé plochy) se čte stejně jako na lesní mapě, tedy zakázaný prostor, a po opravě okraje obrázku sedí i u kraje mapy. Úzké olivové pásy pod 7 m, které by chyběly, jsem na prohlédnutých úsecích tří sprintů neviděl; hledal jsem je jen očima na výřezech, ne měřením.

## Část 2: náběhový bod

`relocate.choose`: bod aspoň 25 m od předchozí kontroly, nejvýš 70 % přímé délky úseku před svou kontrolou, úsek pod 80 m žádný. **Změnilo se 17 z 67 náběhových bodů**, z toho 13 pravidlem o úseku a 4 tím, že oplocenka a rybník leží nově na okraji, ne ve středu. Bez náběhového bodu je 10 kontrol (dřív 2).

| Úsek | Délka úseku | Dřív | Teď |
|---|---|---|---|
| Azymut E5 3–4 | 175 m | vodní plocha 99 m před (střed) | vodní plocha 91 m před (břeh) |
| Azymut E5 4–5 | 114 m | konec cesty 122 m před, 18 m od čtyřky | žádný |
| Azymut E5 6–7 | 106 m | křížení 122 m před | konec cesty 64 m před |
| Azymut E5 11–12 | 100 m | křížení 48 m před | křížení 49 m před (jiný bod téhož křížení) |
| Azymut E4 5–6 | 116 m | konec cesty 110 m před | žádný |
| Azymut E4 7–8 | 156 m | paseka 126 m před, 35 m od sedmičky | žádný |
| Azymut E4 16–17 | 184 m | konec cesty 131 m před | kupka 52 m před |
| Azymut E4 19–20 | 125 m | paseka 119 m před, 14 m od devatenáctky | žádný |
| Pohora S–1 | 123 m | paseka 134 m před, 12 m od startu | žádný |
| Pohora 8–9 | 232 m | paseka 165 m před | konec cesty 126 m před |
| Pohora 12–13 | 94 m | křížení 184 m před (dvakrát dál, než je úsek dlouhý) | žádný |
| Pohora 13–14 | 70 m | konec cesty 31 m před | žádný (úsek pod 80 m) |
| Pohora 15–16 | 110 m | křížení 88 m před | konec cesty 73 m před |
| Petřvald S–1 | 267 m | oplocenka 80 m před (střed) | oplocenka 58 m před (plot) |
| Petřvald 8–9 | 120 m | konec cesty 135 m před, 20 m od osmičky | žádný |
| Petřvald 12–13 | 449 m | oplocenka 74 m před (střed) | oplocenka 38 m před (plot) |
| Petřvald 18–19 | 140 m | výrazný strom 138 m před, 2 m od osmnáctky | kupka 89 m před |

Petřvald 8–9 (tvoje hlášení): konec cesty 135 m před devítkou, 20 m od osmičky → žádný. Na obrázku jsem viděl pět ze sedmnácti změněných (Petřvald S–1, 8–9, 12–13, 18–19 a Azymut E5 11–12): sedí. Zbylých dvanáct jen jako čísla v tabulce.

## Část 2b: záchytné body za překážkou

Jak to bylo: dosažitelnost se počítala přes mřížku se všemi překážkami, ale práh byl 2,5× přímého běhu + 30 s, takže bod za oplocenkou prošel a panel i mapa ukazovaly přímý azimut a přímou čáru. Navíc oplocenka jako záchytný bod ležela ve svém středu, tedy „za plotem“ sama sobě: u kontroly 13 Petřvaldu 74 m na střed protáhlé oplocenky, když plot je 38 m od kontroly.

Teď (`relocate.describe`): přímá spojnice se zkouší proti oplocenkám, zakázaným čarám a plochám, vodě a zakázanému prostoru. Kříží-li je aspoň 4 m, spočítá se nejkratší průchodná obchůzka; nad 1,3× přímé vzdálenosti se bod neukáže, pod 1,05× zůstane přímý azimut, mezi tím panel píše „obchůzkou N m, nejdřív na azimut X° (přímo je překážka)“ a mapa kreslí obchůzku. Oplocenka a rybník leží tam, kde je přímka od kontroly potká.

Co se změnilo (kolo 0 → kolo 3):

| | Čtyři původní závody | Šest extra závodů |
|---|---|---|
| Záchytných bodů celkem | 258 | 462 |
| Nahrazených jiným bodem (i posunem oplocenky na okraj a jiným pořadím) | 6 | 40 |
| Ukázaných s obchůzkou | 2 (Petřvald 5–6: křížení 110 m, obchůzka 125 m; Azymut E5 11–12: křížení 99 m, obchůzka 117 m) | 15 |
| Oplocenek a rybníků udaných od okraje | 12 | 20 |

**Petřvald, kontrola 13** (tvoje hlášení; `petrvald-13-zachytne-pred.jpg` a `-po.jpg`): dřív oplocenka 74 m (střed, za plotem), křížení 53 m, kupka 80 m a jáma s vodou 119 m, která leží za oplocenkou. Teď oplocenka, nejblíž 38 m na azimut 60° (plot), křížení 53 m, kupka 80 m a cesta 32 m; jáma s vodou za oplocenkou vypadla. Na obrázcích všech 19 kontrol Petřvaldu jsem neviděl bod, ke kterému by přímá čára vedla přes oplocenku, rybník nebo zástavbu. Na Petřvaldu 5–6 je bod s obchůzkou křížení ulic uvnitř zástavby: přímo ke kontrole je plot, obchází se ulicí.

Na sprintových mapách je obchůzek víc (15), protože budovy a zakázané plochy jsou tam všude; jak vypadají, jsem na obrázcích neviděl.

## Co ještě našly obrázky a je opravené

| Nález | Kde | Příčina | Oprava |
|---|---|---|---|
| Cíl, start nebo kontrola „v zakázaném prostoru“, postup oklikou | Sprint MSK 19–F a S–1, Slezská zimní liga 23–24 (ze seznamu podezřelých) | Obrys mapy se hledá uzávěrem, který bere prostor za obrázkem jako prázdný: pás 85 m podél okraje obrázku byl zakázaný. Na listu s bílým okrajem to nevadilo, dokud mapa nekončila blíž než 85 m od okraje. | `675f4c3`, `21ba350`, `9831c46`: kde je pás u okraje v barvách mapy, mapa pokračuje za okraj; v pásu se uzávěr dělá bez ztráty a platí mezi nejzazšími barvami mapy. Týká se i čtyř původních map (roh Pohory, rohy Azymutů, kus Petřvaldu byly zakázané). |
| „Nejlepší postup“ je přímka přes domy | Slezská zimní liga 4–5 (784 m) | Kontrola 5 stojí ve dvoře čteném jako uzavřený; hledání cestu nenašlo a přímka se ukázala beze slova. | `5edcdc1`: kontrola v uzavřené kapse do 5000 m² se bere z nejbližšího místa mimo; jinak `no_route`. `27aad05`: oplocenka, ve které stojí kontrola, je průchozí (kontroly 5 a 15 téhož závodu). |
| Pruh „lesa“ přes rybník | Grand prix Silesia E4 u kontroly 11 | Severní čára se vyřazuje z modré. | `5ba3dc1`. Žádný postup tím pruhem nevedl. |
| „Obchůzkou 80 m“ u bodu 80 m daleko | Grand prix Silesia E4 1–2 a další v kole 1 | Přímka jen lízla roh překážky. | `cbbd7df`: obchůzka pod 1,05× je přímka. |

## Co se neopravilo

**Srázy a skály (část 3).** Na mapě Bludiště (1,33 m na pixel) vypadají skalní stěny jako silné černé pruhy a hrudky široké 4 až 6 px; zoubky nejsou vidět. Zkusil jsem jediný znak, který vidět je: černá širší než čára silnice, která není budova (`kontrola/tmp/lumps.py`, přehledové listy `kontrola/noc2/lumps/`).

| Mapa | Kusů černé širší než 6,6 m | Širší než 9,2 m |
|---|---|---|
| Azymut E4 | 138 | 13 |
| Azymut E5 | 68 | 3 |
| Pohora | 78 | 11 |
| Petřvald | 352 | 178 |
| Bludiště (Grand prix Silesia E3/E4) | 202 | 25 |
| tři sprinty | 0 až 5 | 0 až 3 |

Na čtyřech původních mapách sráz není a nálezů jsou stovky (silnice, křižovatky, domy natočené šikmo); na Bludišti je devět největších nálezů při 9,2 m sedm domů a dvě křižovatky, sráz žádný. Podmínku „na původních mapách nula“ tenhle znak nesplní a jiný na téhle mapě není čitelný. Do kódu nešlo nic.

**Kamenitá půda (část 4) a ploty se dvěma čárkami (část 5):** nezkoušel jsem. Seznam podezřelých jim nepřipsal žádný úsek. Tečky kamenité půdy a polí na sprintu E2 se jako cesta nečtou (13 prohlédnutých úseků).

**Co ukázaly obrázky extra závodů a neopravil jsem:**

- **Sprinty: šedá budova užší než asi 9 m se čte jako „cesta“ a postup jí vede.** Viděno na sprintu MSK 11–12, 13–14 a 14–15 (`msk-sprint-11-12-budova.jpg`); na Slezské zimní lize a Žebříčku B se úzké šedé budovy čtou stejně (na obrázcích přečtených tříd černě), jestli jimi některý postup vede, jsem tam nedohledával. Širší šedé budovy se čtou správně jako budova. Našel jsem to při prohlídce kola 2 a nezačal opravovat: je to nové rozpoznávání.

- **Grand prix Silesia E2**: dvě mapy v jednom obrázku (výměna mapy), usazená je jen jedna. Stopa je při ražení 30 až 150 m od kontrol 1 až 13 a do 11 m od kontrol 14 až 25. Úseky první části jsou k ničemu; analýza to nepozná a nehlásí.
- **Bludiště**: skalní stěny jako cesty (E3 2–3, 4–5, 5–6, 7–8).
- **Sprinty**: zpevněná plocha (světle hnědá výplň) je „polootevřený prostor“, takže model po ní běží pomaleji než po cestě.

## Co jsem prohlédl a co ne

- **Čtyři původní závody (71 úseků):** všech 71 obrázků úseků jsem otevřel jednou po opravách částí 1, 2 a 2b (v kolech 1 a 2; u pěti dlouhých úseků Petřvaldu jen celkový obrázek, ne všechny kusy ve velikosti 1:1). V posledním kole jsem znovu otevřel jen čtyři obrázky, které se změnily (Azymut E4 S–1, Petřvald 6–7, 10–11, 17–18); zbylých 67 je bajtově stejných jako ty, které jsem viděl (`tools/kontrola.py --proti`). Zadání chtělo všech 71 otevřít dvakrát.
- **Šest extra závodů (123 úseků):** otevřel jsem 69 obrázků úseků, u každého závodu aspoň polovinu: Grand prix Silesia E2 14 z 26, E3 9 z 15, E4 11 z 18, sprint MSK 11 z 20, Slezská zimní liga 14 z 27, Žebříček B 10 ze 17. Většinu v kole 1 nebo 2; z kola 3 jen změněné.
- **Seznam podezřelých:** všech 34 výřezů výchozího seznamu.
- **Záchytné body:** obrázky všech 19 kontrol Petřvaldu v posledním kole a po jedné kontrole s oplocenkou na Pohoře (5), Azymutu E5 (12) a E4 (2). U ostatních kontrol a u extra závodů jen čísla z porovnání kol.
- **Přehledové listy:** jen list „černá širší než 9 m“ z Bludiště (pokus se srázy). Listy plotů a oplocenek jsem znovu nedělal; jejich čtení se neměnilo, kromě toho, že oplocenka s kontrolou uvnitř se nepočítá.
- **Web:** Petřvald přepočítaný úlohou webu na vývojové instanci (`/data/kontrola-tras` ve svazku `obdev_ob_data`, účet `kontrola`), úloha doběhla za 4 min 41 s, verze postupů 4 a záchytných bodů 6. Tři snímky přes `tools/shot.mjs` bez chyb JavaScriptu, dva jsem viděl: u 5–6 je v panelu „křížení cest 110 m od kontroly na azimut 330°, ke kontrole z křížení cest obchůzkou 125 m, nejdřív na azimut 105° (přímo je překážka)“, u 12–13 „náběhový bod: oplocenka 38 m před kontrolou“. **Čáru obchůzky na mapě jsem na zmenšeném snímku s jistotou nerozeznal**; že ji `map.js` kreslí z `via`, je jen v kódu. Ostatní tři závody jsem úlohou webu nepouštěl. Kontejnery jsem zastavil.
