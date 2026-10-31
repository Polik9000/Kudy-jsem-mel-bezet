# Oplocenky a severky místo vodotečí (noc 25. 10. 2026, větev `oplocenky-vodotece`)

Podklad: Tobiasův závod **Bělá (okr. Opava), Oblastní žebříček 18. 10. 2026, H18C** z webové appky (svazek
`ob_tracker_ob_data`, závod 372, přihláška 109; čteno jen pro čtení). Mapa bez tratě je snímek z Livelox, 3269 ×
2403 px, **0,97 m/px**, rozmazaný; trať usazená ručně. Kopie v `data-extra/bela/` (gitignored), závod je v
`tools/kola.sh` jako `bela`. Postupy, které Tobias viděl ve webu (jeho `best.json` a `relocate.json`), jsou
vykreslené v `kontrola/noc4/web-bela/useky/`.

Tobiasovy výřezy obrazovky do repa nedorazily (`docs/reference/oplocenky-vodotece/tobias/README.md`); práce je podle
popisu v zadání a podle stejných postupů z webu.

Nástroje noci:

- `tools/oplocenky.py OUT_DIR MAPONLY.kmz`: kde každá čára (nejlepší postup, možnosti, průměrný běžec, rady
  „Ztratil jsem se“) vede uzavřenou černou plochou nebo přes plot, proč ta plocha není oplocenka (`plocha`,
  `tvar`, `okraj`, `oob`, `podil_cerne`, `paleta`, `silnice`, `zoubky N`), a kontaktní archy všech uzavřených
  ploch s důvodem (`JEN_PRIJATE=1`, `JEN_ODMITNUTE=1`).
- `relocate.enclosures(..., why={})`: stejné důvody pro jednu mapu (výsledek beze změny).
- `kontrola/porovnej_oplocenky.py`, `kontrola/severky_vse.py`, `kontrola/severky_vyrez.py` (gitignored): oplocenky
  dřív a teď na všech 11 mapách, měření severek, obrázky severek.

## 1. Oplocenky

### Proč postupy v Bělé šly přes oplocenky

Diagnóza na mapě Bělé (kód ze 24. 10.): z 56 uzavřených černých ploch nad 100 m² byly oplocenky jen **9**.
Skutečných oplocenek (žlutá s pruhy výsadby nebo zelená, plot se zoubky dovnitř) se odmítlo **20** a 4 jejich rohy:

| Příčina | Kolik | Příklad | Co se stalo |
|---|---|---|---|
| Zoubky nenalezené | 11 | (2595, 583), (2591, 683), (2453, 720) | Zavírání mezer v obrysu (kruh 2,5 m = 3 px) na rozmazaném snímku slilo zoubky s čarou: „díra“ se zmenšila o délku zoubku a zoubky v ní nebyly. Zoubek 2,5 m = 2,6 px je na hranici rozlišení. |
| Černá tisku mapy | 6 | (1313, 270), (557, 598), (2378, 1980) (obrázek 5, 4-5 možnost 3) | Test „černá mapy, ne šedý tisk“ (součet RGB < 150) na rozmazané čáře neprošel: střed čáry má (30, 30, 30), okraje šedé. |
| Paleta uvnitř | 2 | (2516, 1888), (2243, 1982) | Rozmazané pruhy výsadby dávají směsi žluté a zelené, které nejsou v paletě ploch. |
| Tvar | 1 | (2036, 1812) | Protáhlá zahnutá oplocenka: filtr podle obdélníku kolem (1 : 4). |

K tomu **čára plotu kolem přijaté oplocenky zůstávala cestou**: neprůchozí maska byla plocha (zmenšená o zoubky)
+ 3,5 m, takže na rozmazané čáře 4 px vyšla hrana masky na plot. Postup i možnosti pak běžely po plotu jako po
cestě a přes úzkou špičku trojúhelníku (obrázek 1: S-1, oplocenka (1433, 690), špička (1434, 640) byla samostatná
díra s 55 % černé, odmítnutá).

| S-1 dřív (web): možnost 2 po plotu a přes špičku | S-1 teď: celý trojúhelník neprůchozí, možnost 2 obíhá po čárkované cestě |
|---|---|
| ![](reference/oplocenky-vodotece/s1-pred.jpg) | ![](reference/oplocenky-vodotece/s1-po.jpg) |

Další příčiny ze zadání: mezera v obrysu nad 5 m (v Bělé žádná), plocha nad 10 000 m² (v Bělé žádná oplocenka,
jen obec), oplocenka otevřená kontrolou (v Bělé žádná kontrola v oplocence), plot nalezený jen jako „hard“
(4 ploty, žádný není součástí oplocenky, žádný neprůchodný).

### Opravy (`oroute/relocate.py`, `oroute/mapdata.py`)

Na **hrubém obrázku** (zoubek 2,5 m je kratší než 4 px: snímky a KMZ z Livelox 1 až 1,33 m/px):

1. zoubky se hledají na ploše, kterou uzavírá samotná čára (`_drawn`, spojená přes 1 až 2 px), ne na ploše po
   zavření mezer; „zářez“ zoubku podle naměřené tloušťky čáry; krátký zoubek od 2 px (1,5 m);
2. černá tisku mapy se hledá do 1 px od čáry;
3. uvnitř se počítají i směsi barev ploch se zelenou pruhů (`_palette_dist`);
4. tvar podle vepsaného kruhu (aspoň 6 m), ne podle obdélníku kolem;
5. malá plocha s 45 % černé přes plot od nalezené oplocenky je její **roh** (špička trojúhelníku).

Na všech mapách:

6. neprůchozí maska obsahuje **i samotný plot** (tmavé pixely do tloušťky čáry od plochy); ne na sprintové mapě,
   kde jsou černé čáry kolem dvora okraje domů a ulic (preventivně: sprintové „oplocenky“ jsou sporné, otázka 44);
7. oplocenka do 60 000 m², nad 10 000 m² zoubek aspoň každých 60 m obvodu;
8. plocha z víc než 25 % zpevněná (světle hnědá, na sprintu i světlejší dlažba ISSprOM) je ulice, ne oplocenka;
   okolí do 15 m musí mít barvy mapy
   (směsi s bílou papíru jsou v pořádku), ne znak v rohu listu;
9. **mezera v plotu do 12 m**: konce dvou plotů se zoubky 5 až 12 m od sebe se pro hledání ploch spojí
   (`_bridges`, ploty z `fences()`, které `mapdata.obstacles` teď volá jako první);
10. **neprůchodný plot** (ISOM 2017-2 č. 518, v ISOM 2000 č. 524 „vysoký plot“): zoubky po dvou na jedné straně
    (krátká mezera do 4 m, mezery před a za ní aspoň dvakrát delší), aspoň 2 dvojice a 60 % zoubků, zoubky nemíří
    do zakázaného prostoru → neprůchozí čára (`blocked`), cesta podél zůstává; obyčejný plot dál 90 s. Na sprintu
    jsou zoubky každého plotu po pár metrech (bez vzoru dvojic by SZL měl 6 a Žebříček B 5 „neprůchodných“ plotů,
    teď 1 a 0); ploty kolem olivových pozemků (520) uzavírá ten pozemek sám;
11. kontrola otevře **jen oplocenku, ve které stojí nebo u jejíhož plotu je** (do 5 m jako dřív, q22), ne sousední
    oplocenku, která se s ní v masce 5 m slije. (Zkoušel jsem 2 m: na SZL pak zůstala zavřená falešná „oplocenka“
    ze smyčky čárkovaných cest se zelenými pruhy, kterou dřív otevírala kontrola: +7 100 m² masky.) Kontrola na
    neprůchodném plotu ho otevře v okolí 4,5 m.

Zvoleno a zamítnuto: **obrys bez zoubků oplocenka není.** Obdélník z obrázku 5 zoubky má (rozmazané) a teď se
najde; uzavřená plná černá čára bez zoubků je v lese i smyčka cest (ISOM 504) nebo okraj silnice.

Mezera 12 m: branka nebo cesta přes plot 3 až 5 m, k tomu přerušení čáry kvůli vrstevnici nebo průseku; 12 m je
9 px na 1,33 m/px. Smyčka cest nemá zoubky (`fences()` ji nenajde), takže se nezavře.

### Výsledek v Bělé

**29 oplocenek** (z 9) a 4 rohy. Seznam (střed v pixelech mapy): (278, 904), (557, 598), (626, 1365),
(989, 1506), (1313, 270), (1409, 1176), (1433, 690) + roh (1434, 640), (1898, 1729), (1941, 1703), (1968, 1607),
(1970, 1796), (1997, 1962), (2007, 1429), (2008, 1719), (2028, 1903), (2036, 1812), (2065, 1040), (2221, 847),
(2235, 1221), (2243, 1982), (2378, 1980), (2407, 626), (2453, 720), (2516, 1888), (2541, 981), (2591, 683),
(2595, 583), (2638, 2159), (2741, 546). Zbylé uzavřené plochy: rybníky s černým břehem (voda je neprůchozí sama),
ulice (2), obec (OOB), silniční smyčky bez zoubků (1334, 295), (315, 198), a (1112, 1553) (zahrada u obce s tenkou
čarou na jedné straně, 44 % černé; na trase žádného postupu).

`tools/oplocenky.py` na postupech kola 7 (nejlepší, 2 možnosti, průměrný běžec, rady „Ztratil jsem se“): **žádná
čára nevede oplocenkou ani přes plot**; jediný dotyk je rada u kontroly 3, která se 3 m dotkne plochy 76 m² (pod
hranicí oplocenky).

| 4-5 dřív (web): možnost 3 přes roh obdélníku (2378, 1980) | 4-5 teď |
|---|---|
| ![](reference/oplocenky-vodotece/4-5-pred.jpg) | ![](reference/oplocenky-vodotece/4-5-po.jpg) |

### Falešné nálezy na ostatních mapách

`kontrola/porovnej_oplocenky.py` (dřív | teď) na všech 11 mapách z `tools/kola.sh`:

| Závod | Oplocenek dřív → teď | Co přibylo |
|---|---|---|
| Azymut E5, Pohora | 3 → 3, 3 → 3 | nic; masky o plot větší |
| Azymut E4 | 4 → 5 | (1015, 1820): tmavě zelená oplocenka se zoubky (opravdová) |
| Petřvald (0,59 m/px, ostrá) | 8 → 8 | nic; masky o plot větší |
| GPS E2 / E3 / E4 | 0 / 20 / 20 → 0 / 20 / 20 | (2372, 1173) na E3 opravdová; masky o plot větší |
| MSK sprint, SZL Zábřeh, Žebříček B (0,27 až 0,4 m/px) | 0 / 11 / 0 → beze změny (SZL: 8 po otevření kontrolami) | nic |

Cestou zamítnuté pokusy (změřeno, vráceno): uvolnění pro všechna rozlišení udělalo na SZL Zábřeh z dvorů mezi domy
53 „oplocenek“ a na MSK sprintu z rámečků textu legendy 5; libovolné směsi barev pustily znak (orlici) v rohu
Petřvaldu; bez testu dlažby se přijaly ulice mezi zahradami Petřvaldu. Dvory na SZL (11) byly „oplocenkami“ už
dřív a zůstávají (otázka 44).

## 2. Severky místo vodotečí

### Měření (všech 11 map, `kontrola/severky_vse.py`)

| Mapa | m/px | Úhel severek | Severek | Rozestup | Šířka | Staré pravidlo (svislé sloupce) |
|---|---|---|---|---|---|---|
| Bělá (snímek) | 0,97 | **−0,70°** | 10 | 308 px = 298 m | 2 px | **0 sloupců: žádná severka** |
| Azymut E5 / E4 | 1,33 | 0,02° | 6 / 5 | 225 px = 300 m | 4 / 2 px | 7 / 5 |
| Pohora | 1,33 | 0,06° | 7 | 225 px | 4 px | 6 |
| Petřvald | 0,59 | 0° | 7 | 507 px = 299 m | 3 px | 18 |
| GPS E2 / E3 / E4 | 0,40 / 1,33 / 1,33 | 0° | 3 / 7 / 7 | 120 m / 300 m | 2 px | 5 / 10 / 10 |
| MSK sprint, SZL, Žebříček B | 0,27 až 0,40 | 0° | 6 / 13 / 6 | 120 m | 2 px | 21 / 26 / 12 |

Barva: čistá modrá (b > 200, r < 120), stejná jako vodoteče. **Přerušení:** nejdelší souvislý kus severky je jen
5 až 30 % mapy (severky jsou přerušené kvůli popisům a značkám), takže „plná, bez mezer“ se jako pravidlo použít
nedá; rozhoduje **mřížka** (rovnoběžné, stejný rozestup 300 m v lese, 120 m na sprintu).

V Bělé je snímek pootočený o 0,7°: na 2400 řádků se severka posune o 29 px, žádný sloupec pixelů ji nemá ani z 9 %
(staré pravidlo chtělo 15 %), a **všech 10 severek se četlo jako vodoteče**. Z nich vzniklo ve webu: 16 bodů „cesta
přes vodoteč“, 3 „vodoteče“ jako záchytné body, **11 zarážek „vodoteč“** u 6 kontrol (1-2: „rovně vodoteč 54 m“,
obrázek 3), 2 náběhové body „přechod cesty přes vodoteč“ a rada „Ztratil jsem se“ u 4 vedla „k vodoteči a podél
ní“.

### Nové rozpoznání (`terrain.north_lines`)

Projekce modrých pixelů pod úhly do ±30° (po 0,5°, pak po 0,02°), vybere se úhel s nejostřejšími vrcholy. Severka =
tenký vrchol (vedle něj do 8 px nejvýš čtvrtina modré) na pravidelné mřížce: rozestup je medián mezer mezi čarami
s modrou aspoň na 30 % délky, přesnost 2 px + 0,5 px na každý rozestup od kotvy; na mřížce stačí 12 %. Osamocená
čára bez mřížky jen s 80 % délky a souvislým kusem 15 %. Maska = pás šířky čáry ± 0,5 px (svislá čára 2 px → 3 px,
jako dřív sloupce).

- Vodoteč přes severku zůstane (modrá v pásu, která navazuje na kus mimo něj, patří vodoteči).
- Rybník přes severku (`NORTH_GAP_PX`) se zavírá napříč úhlu severek.
- Úhel se ukládá (`relocate.json`: `north: {by: "lines", deg}`, scéna „Ztratil jsem se“: `north`) a **azimuty jsou
  k severkám** (`relocate.north_bearings`), ne k horní hraně obrázku. V Bělé o 0,7°.
- Severka není záchytný bod, zarážka, náběhový bod, bariéra ani terén (všechno bere modrou přes `stream_mask` nebo
  `classify`, obojí bez pásu severek; bodové značky hledají malé modré tvary).

| Kontrola 7 (obrázek 6): šikmá čárkovaná modrá = vodoteč (zůstala modrá), rovná plná = severka (teď červená) |
|---|
| ![](reference/oplocenky-vodotece/kontrola-7-severky.png) |

| Kontrola 2 (úsek 1-2, obrázek 3): „vodoteč 54 m za kontrolou“ byla severka |
|---|
| ![](reference/oplocenky-vodotece/kontrola-2-severky.png) |

Po opravě v Bělé: **žádná vodoteč, přechod vodoteče ani zarážka „vodoteč“**; opravdové vodoteče zůstaly (9 kusů nad
60 m na východě mapy, žádný u kontroly).

## 3. Zarážky

Kontrola 1 (obrázek 2): zarážka byla „vlevo cesta 15 m, vpravo cesta 15 m“ (15 m je nejmenší povolená vzdálenost:
kontrola stojí u dvou cest a paprsky narazily na její vlastní cesty; „vpravo“ byla čárkovaná cesta, která leží přesně
na severce, Tobiasova červená čára k jihu). Čárkovaná cesta 55 m za kontrolou (Tobiasova žlutá) běží 26° od směru
paprsku a pravidlo „cesta, po které běžec přišel“ (`ALONG_DEG` 30°) ji přeskočilo.

Oprava (`relocate.beyond`):
- cesta nebo vodoteč do 10 m od kontroly je její vlastní: její kus do 60 m se počítá teprve, když ji paprsek opustí
  aspoň na 5 m (jako vlastní paseka, `OWN_M`). Na sprintu tak zmizely umělé zarážky „cesta 25 m“ (tatáž ulice za
  hranicí), které dala první verze pravidla s pevnými 25 m;
- souběžná cesta se přeskočí jen tehdy, když prodloužená vede do 15 m od kontroly (je to opravdu cesta příchodu).

Teď: **„rovně cesta 55 m, vpravo cesta 36 m“**.

Zarážky všech kontrol Bělé teď (kolo 9, `useky/seznam.txt`), zkontrolované proti mapě:

| Kontrola | Zarážka | Na mapě |
|---|---|---|
| 1 | rovně cesta 55 m, vpravo cesta 36 m | ano (žlutá cesta z obrázku 2) |
| 2 | vlevo cesta 18 m, rovně cesta 104 m, vpravo cesta 103 m | ano; dřív „rovně vodoteč 54 m, vpravo vodoteč 47 m“ = severky |
| 3 | vlevo cesta 68 m, rovně 86 m, vpravo 111 m | ano |
| 4 | vlevo cesta 149 m, rovně 78 m, vpravo 62 m | ano; dřív „vlevo vodoteč 34 m“ = severka |
| 5 | vlevo cesta 35 m, rovně 94 m, vpravo 92 m | ano |
| 6 | vlevo cesta 73 m, rovně cesta 111 m, vpravo paseka 33 m | ano; dřív „vlevo/rovně vodoteč 40/43 m“ = severka |
| 7 | vlevo cesta 45 m, rovně 83 m | ano |
| 8 | vlevo budova 30 m, rovně cesta 38 m, vpravo cesta 139 m | ano |
| 9 | vlevo paseka 71 m, rovně cesta 60 m, vpravo cesta 47 m | ano; dřív „vodoteč“ ve všech třech = severka |
| 10 | rovně cesta 68 m, vpravo cesta 58 m | ano; dřív „vlevo/rovně vodoteč“ = severka |
| 11 | rovně cesta 141 m, vpravo cesta 98 m | ano; dřív „vlevo vodoteč 33 m“ = severka |
| 12 | vlevo cesta 57 m, rovně 46 m, vpravo 66 m | ano |
| 13 | vlevo/rovně okraj otevřené plochy 96/104 m, vpravo cesta 17 m | ano |
| 14 | rovně cesta 76 m, vpravo cesta 126 m | ano |

Zarážky ostatních závodů (kolo 9 proti kolu 3): změnily se hlavně tam, kde byla zarážkou vlastní cesta kontroly
15 m daleko (MSK sprint 13 kontrol, Žebříček B 9, GPS E2 až E4 5 až 6, referenční závody 2 až 4). Prošel jsem
změněné: teď je to věc za vlastní cestou (další ulice, dům, plot, rybník) nebo nic do 200 m. Zarážky „vodoteč“ na
ostatních mapách zůstaly (svislé severky staré pravidlo z velké části chytalo; Azymut E5 má 15 dílů zarážek na
opravdových vodotečích).

## 4. Rada „Ztratil jsem se“ u kontroly 4 (obrázek 4)

Dřív (kolo 6, kód ze 24. 10.): „Jdi na východ k vodoteči (asi 70 m), pak podél ní na jih 85 m, kontrola je 35 m
vpravo“; ta „vodoteč“ byla severka. Po kroku 2: „drž se cesty, podél ní na sever ke křížení (65 m), odtud 120 m na
azimut 170°“: oklika 185 m ke kontrole vzdálené 75 m. Příčina v `lost._link`: linie dál než 40 m od kontroly
nevedla ke kontrole jinak než přes křížení (do 150 m) nebo azimutem z místa, kde se chytí.

Oprava: linie do 100 m vede ke kontrole i bez křížení (podél ní k místu nejblíž kontrole, odtud azimut). Bod na
linii vyhraje, jen když z něj nevede o víc než 15 m delší azimut a celá cesta je nejvýš 1,5× delší (nebo kdykoli
do 1,25×). Kdo stojí u linie, dostane azimut z místa, kde stojí, když je kratší. Věta pro „vlevo/vpravo“ dál než
40 m má i azimut.

| Kontrola | Dřív (kolo 6) | Teď |
|---|---|---|
| 4 | ![](reference/oplocenky-vodotece/ztraceny-4-pred.png) | ![](reference/oplocenky-vodotece/ztraceny-4-po.png) „Byl jsi u cesty, měl ses jí držet. Odtud kontrola 75 m na azimut 150°.“ |
| 11 | ![](reference/oplocenky-vodotece/ztraceny-11-pred.png) | ![](reference/oplocenky-vodotece/ztraceny-11-po.png) „… Odtud kontrola 70 m na azimut 0°.“ (dřív ke křížení 60 m a 95 m zpět) |
| 3 | ![](reference/oplocenky-vodotece/ztraceny-3-pred.png) | ![](reference/oplocenky-vodotece/ztraceny-3-po.png) „… měl jsi ji najít. Odtud kontrola 95 m na azimut 75°.“ (dřív 140 m po cestě a 100 m zpět) |
| 1 | ![](reference/oplocenky-vodotece/ztraceny-1-pred.png) | ![](reference/oplocenky-vodotece/ztraceny-1-po.png) |
| 6 | ![](reference/oplocenky-vodotece/ztraceny-6-pred.png) | ![](reference/oplocenky-vodotece/ztraceny-6-po.png) ke křížení 30 m, odtud 90 m (křížení vyhraje: kratší azimut) |
| 7 | ![](reference/oplocenky-vodotece/ztraceny-7-pred.png) | ![](reference/oplocenky-vodotece/ztraceny-7-po.png) |

Tobias u 4 kreslí „rovně na roh/křížení a pak po čáře na jih ke kontrole“. Kterou čáru myslí, z popisu nevím: na
jih ke kontrole vede jen zelená čárkovaná hranice porostu (appka ji jako linii nečte) a severka (po té se v terénu
jít nedá). Rada teď vede bez okliky, ale „po čáře“ to není (otázka 45).

## Kola a testy

- Kola `tools/kola.sh` (každý závod ve vlastním kontejneru): **6** (Bělá, kód ze 24. 10.), **7** (Bělá po prvních
  opravách), **8** (všech 11), **9** (všech 11, konečný kód; 10 závodů proti kolu 3, Bělá proti kolu 6). Výstupy
  `kontrola/noc4/kolo-N/`. Kolo 9 trvalo 69 min (SZL Zábřeh 30 min), nejvíc paměti 3,5 GB (SZL, scéna Ztratil jsem se).
- Nejlepší postupy kolo 9 proti kolu 3: změněné 0 až 2 úseky na závod (Azymut E5 1, E4 1, Pohora 2, Petřvald 2,
  GPS E3 2, ostatní 0). Stopa přes oplocenku: nikde nová (Bělá 7-8 a 11-12 jen olizují okraj, GPS kolem 10 m; hlásil
  to i web).
- `tools/podezrele.py`: úseků, kde jsi rychlejší než nejlepší postup (skupina A), **23 před i po**, množina stejná
  (32 podezřelých ze 146).
- **Goldeny** (`tests/golden/*/best_legs.csv`, `tests/make_golden.py` s výškopisem ze zlatých souborů), jen tam, kde
  nový postup obchází oplocenku nebo už nevede po severce:

| Závod, úsek | Dřív → teď | Proč |
|---|---|---|
| Azymut E5 6-7 | 0:55 → 0:56, zelená 18 → 20 m | severka už nedělá v zeleni proužek „lesa“ |
| Azymut E4 7-8 | 1:11 → 1:13, zelená 28 → 36 m | totéž |
| Pohora 4-5 | 2:30 → 2:29, cesta 40 → 14 m | starý kód nenašel 5 ze 7 severek, jejich modrá šla do terénu |
| Pohora 8-9, 9-10 | 1:57 → 1:57, 1:40 → 1:41 (zelená +2, +12 m) | totéž |
| Petřvald S-1 | 2:22 → 2:23, cesta 140 → 114 m | postup neběží po plotu oplocenky u startu |
| Petřvald 12-13 | 3:33 → 3:42, cesta 136 → 62 m | postup běžel z velké části po plotu dlouhé oplocenky (čára plotu byla „cesta“) |
| Petřvald 15-16 | 2:54 → 2:54, cesta 170 → 168 m | totéž, kousek |

  Úseky (`legs.csv`) a tratě (`course.json`) beze změny.
