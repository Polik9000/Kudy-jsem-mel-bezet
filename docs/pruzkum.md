# Průzkum: co už existuje a co z toho vzít (noc 6. → 7. 10. 2026)

Průzkum na internetu k analýze postupů v orientačním běhu a k napojení na klubový web. Při průzkumu se v kódu nic neměnilo. Popis vzhledu klubového webu je zvlášť v `docs/design-klubovy-web.md`, podklady v `docs/reference/`.

**Stav k 7. 10. 2026:** podle tohoto průzkumu se stavělo. U každého doporučení je teď napsáno, co je hotové; souhrn je hned níže a na konci je část „Co zbývá teoreticky“. Původní text průzkumu jsem neměnil, jen doplnil poznámky „Stav“.

## Stav doporučení (7. 10. 2026)

| # | Vylepšení | Stav | Kde / co vyšlo |
|---|---|---|---|
| 1 | Mezičasy celé kategorie, metoda WinSplits | **hotovo** | `oroute/splits.py`, záložka „Mezičasy kategorie“; funguje bez mapy i bez `.fit` |
| 2 | `skob.css` a propojení odkazů přes ORIS ID | **hotovo** | vzhled převzat beze změny CSS; `/ob/zavod/oris-<ID>`, `/ob/clen/<ID>`, odkazy na klubový web |
| 3 | Výškopis ČÚZK DMR 5G | **hotovo** | `oroute/dem.py`; s barometrem sedí 2 až 3× líp než AWS |
| 4 | Livelox API klíč | **nedělá se** | rozhodnutí Tobiase |
| 5 | Zakázané přechody z OSM + ruční čára | **hotovo** | železnice a dálnice; ploty stažené, ale vypnuté; Petřvald 14–15 vede přes přejezd |
| 6 | Kontrolní sada pro nejlepší postupy | **hotovo** (testy 1 až 3) | `tests/test_routing.py`, pomalé testy; hned našla chybu čtení mapy na Petřvaldu (opravená 7. 10. odpoledne) |
| 7 | Umístění mapy bez KMZ | **hotovo** pro mapu s tratí | `oroute/georef.py`; Pohora a Petřvald do 20 m; mapa bez tratě z obrázku ne |
| 8 | Typ chyby u kontroly z GPS | **hotovo**, prahy neladěné | `oroute/mistakes.py`; chybí poznámky běžce, proti kterým ladit |
| 9 | Model: společný odhad, příčný sklon, klubový prior | **změřeno, nezapnuto** | společný odhad nepomohl, příčný sklon slibný, prior vypnutý (`docs/validace.md`) |
| 10 | Vektorové mapy (OCAD) | **neděláno** | čeká na soubory a souhlas oddílu |
| 11 | Strava | **nedělá se** | rozhodnutí Tobiase |
| 12 | Průchodnost z LiDARu | **nedělá se** | rozhodnutí Tobiase |

Navíc proti seznamu: alternativní postupy a hláška „postupy jsou vyrovnané“ (část 6), párování aktivit podle polohy (část 4), účet z registračního čísla (jedno číslo = jeden účet), zakázané prostory ze šrafování mapy, pořadí kontrol z oficiálních mezičasů.

Jak číst zdroje: u tvrzení je odkaz. Značka **(neověřeno)** znamená, že jsem zdroj neotevřel nebo se nedal přečíst a opírám se jen o výtah z vyhledávače nebo o cizí shrnutí. Souhrn těchto míst je na konci.

## Shrnutí

1. **Nikdo veřejně nedělá totéž co my.** Existují tři skupiny nástrojů: prohlížeče tras (Livelox, RouteGadget, QuickRoute, 2DRerun), rozbory mezičasů (WinSplits, SplitsBrowser) a výpočet nejrychlejší cesty z mapy pro stavitele tratí (OCAD Route Analyzer, pár akademických prací). Spojení „osobní model rychlosti z vlastních běhů + nejrychlejší postup + porovnání se skutečnou stopou + vysvětlení“ jsem nenašel nikde. Nejblíž je OCAD Route Analyzer, ten ale potřebuje vektorovou mapu, není osobní a se stopou neporovnává.
2. **Největší zisk za nejmíň práce jsou mezičasy celé kategorie.** ORIS je v `getSplits` vrací pro všechny běžce a my z nich dnes bereme jen svůj řádek. S nimi jde hned zavést osvědčenou metodu WinSplits (chyba = ztráta přes 30 s a zároveň přes 25 % proti vlastnímu normálu) a nezávisle zkontrolovat, jestli náš model řadí úseky podle obtížnosti stejně jako skutečné časy ostatních.
3. **Výškopis jde výrazně zpřesnit zdarma a legálně.** ČÚZK dává DMR 5G (laserové skenování, chyba 0,18 m v otevřeném terénu) jako otevřená data pod CC BY 4.0. Dnes používáme dlaždice se zdrojem kolem 30 m. Sklon je druhá polovina modelu, takže se zpřesní model i trasy.
4. **Mapy z Livelox automaticky nepůjdou a nemá smysl to zkoušet.** Dokumentace API říká výslovně, že mapy a trasy přes API nejsou, podmínky zakazují strojové vytěžování a API je určeno pro veřejné aplikace, které Livelox nekopírují. Přes API jdou jen tratě (souřadnice kontrol v IOF XML). O klíč stojí za to požádat, ale je reálné, že ho nedostaneme.
5. **Ruční export KMZ jde obejít jinak:** z oficiálních časů ražení (ORIS) a stopy GPS známe přibližnou polohu každé kontroly, takže libovolný obrázek mapy s tratí (fotka, sken) jde umístit sám, bez Livelox. Hotový nástroj, který by to dělal automaticky, jsem nenašel; všechny (QuickRoute, RouteGadget) to nechávají na ručním posouvání.
6. **Zakázané přechody jde z velké části vyřešit z OpenStreetMap:** železnice, dálnice a ploty jako překážky, přejezdy, mosty a podchody jako povolená místa. Řeší to známou chybu z Petřvaldu (úsek 14–15) bez rozpoznávání symbolů z obrázku.
7. **Strava a Garmin:** Garmin API je jen pro firmy a nové žádosti jsou podle dostupných zpráv pozastavené. Strava jde, ale nová aplikace má jednoho uživatele, bez schvalování nejvýš deset, a data smí vidět jen jejich vlastník. Pro oddíl o 75 členech zůstává základem nahrání `.fit` a celého exportu z Garminu.
8. **Klubový web je tátou psaná aplikace ve stejné technologii jako naše** (podle vnějších znaků Flask, Jinja, SQLite, cron, za Cloudflare). Adresy závodů i členů stojí na číslech z ORIS, takže propojení odkazů je přímé. Web má sdílené CSS připravené pro další aplikace. Dvě věci je potřeba domluvit: web schválně nemá přihlašování a v plánu má vlastní položku „Analýza mezičasů“.

## Co dělat první (seřazeno podle poměru přínos / práce)

| # | Vylepšení | Přínos | Práce | Proč v tomto pořadí | Stav 7. 10. 2026 |
|---|---|---|---|---|---|
| 1 | Ukládat mezičasy **všech** běžců kategorie z ORIS a spočítat z nich „normální výkon“, ztrátu a chybu po úsecích (metoda WinSplits) | velký | malá | Data už stahujeme. Funguje i bez mapy a bez `.fit`. Dá druhý, nezávislý pohled na ztráty z GPS. | **hotovo** |
| 2 | Převzít `skob.css` a propojit odkazy s klubovým webem přes ORIS ID | střední | malá | Viditelné hned, bez rizika. Podrobnosti v části „Klubový web“. | **hotovo** |
| 3 | Výškopis ČÚZK DMR 5G pro české závody (v `oroute/dem.py`), AWS nechat jako zálohu | velký | malá až střední | Jedna funkce, zbytek kódu se nemění. Nejdřív ověřit dostupnost služby ze serveru. | **hotovo** |
| 4 | Požádat Livelox o API klíč za oddíl (tratě v IOF XML) | střední | malá (e-mail) | Nestojí nic, jen se čeká. Kód až po schválení. | **nedělá se (rozhodnutí Tobiase)** |
| 5 | Zakázané přechody z OpenStreetMap + ruční zakázaná čára v aplikaci | velký u dotčených závodů | střední | Opravuje známé špatné trasy. Ruční čára je pojistka. | **hotovo (ploty vypnuté)** |
| 6 | Kontrolní sada pro „nejlepší postupy“ (čtyři testy z části 6) | střední | malá až střední | Bez ní nevíme, jestli další změny modelu pomáhají. | **hotovo** |
| 7 | Umístění mapy bez KMZ: kontroly z obrázku + polohy z oficiálních časů | velký | střední | Odstraní nejhorší ruční krok. Stavebnice už je v kódu (hledání koleček, `order_by_track`). | **hotovo pro mapu s tratí** |
| 8 | Rozpoznání typu chyby u kontroly z GPS (přeběhl, nedoběhl, úhyb, hledání) | střední | střední | Navazuje na bod 1; dává text „co se stalo“, ne jen sekundy. | **hotovo, prahy neladěné** |
| 9 | Model rychlosti: společný odhad v logaritmu rychlosti, příčný sklon, klubový prior | střední | střední až velká | Zpřesnění; dělat až s testy z bodu 6. | **změřeno, nezapnuto** |
| 10 | Vektorové mapy (OCAD) u závodů pořádaných oddílem | velký, ale jen pro pár závodů | střední | Přesné třídy terénu i zákazy. Jen kde máme soubory a práva. | **neděláno** |
| 11 | Strava (do 10 lidí) | malý až střední | střední | Až když o to někdo bude stát. | **nedělá se (rozhodnutí Tobiase)** |
| 12 | Průchodnost z LiDARu (výška porostu DMP − DMR) | nejistý | velká | Pokus, ne produkt. Data porostu jsou stará. | **nedělá se (rozhodnutí Tobiase)** |

## 1. Dělal už něco podobného někdo jiný?

### Prohlížeče tras a mezičasů

| Projekt | Co dělá a jak | Licence | Co převzít | Co jim chybí proti nám |
|---|---|---|---|---|
| [Livelox](https://www.livelox.com/Documentation/Viewer) | Přehrávání tras na mapě, pohled po úsecích (čas, délka, tempo každého běžce), barvení postupů od zelené po červenou. „Vyrovnání rychlosti“ přepočítá časy, jako by všichni měli fyzičku nejrychlejšího, aby vynikl rozdíl ve volbě postupu. Placený „duel“ dvou běžců a nástroj na vlastní výřez úseku. ([zdroj: výtah z dokumentace](https://www.livelox.com/Documentation/Viewer), **neověřeno** přímo na stránce) | uzavřený, komerční | Myšlenku vyrovnání rychlosti (přesně to potřebujeme při srovnání členů oddílu). Barevnou škálu postupů. | Žádný model terénu, žádný vypočtený nejlepší postup, žádný osobní model. |
| [RouteGadget 2](https://github.com/Maprunner/rg2) | Webové kreslení a nahrávání tras, přehrávání, statistiky z mezičasů. Mapu georeferencuje správce třemi body. | MIT podle výtahu z GitHubu (**neověřeno** v repozitáři) | Rozložení dat (závod, trať, trasa). Ukazuje, že tři body stačí na umístění mapy. | Analýza volby postupu, model. |
| [QuickRoute](https://github.com/jarkko/quickroute-gps) | Program pro Windows: obrázek mapy + GPS, ruční „natažení“ mapy na stopu, barvení podle tempa, odchylka směru od spojnice. | GPL v3 ([zdroj](https://github.com/jarkko/quickroute-gps), výtah) | Metriky (odchylka od směru, tempo po úsecích). Kód kvůli GPL nepřebírat, pokud náš repozitář nemá být GPL. | Automatika, model, nejlepší postup. |
| [DOMA](https://github.com/matstroeng/doma) | Osobní archiv map s trasami (PHP + MySQL), napojený na QuickRoute. | **neověřeno** | Nic podstatného. | Analýza. |
| [2DRerun / 3DRerun](https://news.worldofo.com/2015/02/26/introducing-the-2drerun-courseplanning-module/) (Jan Kocbach, World of O) | Webové přehrávání a „AutOanalysis“: z více stop a oficiálních mezičasů ukáže po úsecích, kdo kudy běžel a kolik kde ztratil. Má i modul pro stavbu tratí. (**neověřeno**, jen výtah) | uzavřený | Postup „seskup trasy na úseku do variant a porovnej jejich časy“. | Model terénu, osobní model. |
| [WinSplits](http://obasen.orientering.se/winsplits/help.aspx?topic=terms&lang=en) | Rozbor mezičasů. Výkonnostní index: 100 % = průměr 25 % nejlepších časů na úseku. „Superman“ = součet nejlepších mezičasů. Chyba = rozdíl proti normálnímu výkonu běžce přes práh časový i procentní zároveň, výchozí 30 s a 25 %. (výtah z nápovědy, **neověřeno** přímo) | uzavřený | Celou metodu, je jednoduchá a prověřená. Viz část 5. | GPS, mapa, příčina chyby. |
| [SplitsBrowser](https://github.com/LukeWoodward/SplitsBrowser) | Otevřený webový graf mezičasů (kde jsem ztrácel proti ostatním). | otevřený, konkrétní licence **neověřena** | Typy grafů pro stránku závodu. | Totéž co WinSplits. |
| [Control](https://control-app.net/) (Orienteers Oy) | Mobilní aplikace: mapa + stopa, synchronizace s hodinkami Garmin, Suunto, Polar a COROS, grafy, odchylka od spojnice, v placené verzi srovnání tras a rozbor „co kdyby“. | uzavřená | Ukazuje, že synchronizace hodinek je pro firmu dostupná. | Vypočtený nejlepší postup z mapy (podle webu ne; **neověřeno** v aplikaci). |
| [Vikazimut](https://gitlab.ecole.ensicaen.fr/regis/vikazimut-app/-/tree/master?ref_type=heads) (ENSICAEN) | Aplikace místo mapy a průkazky, po doběhu mezičasy a stopa, webový rozbor nahraných tras. | zdroj na školním GitLabu, licence **neověřena** | Možný zdroj dat stop (používá ho AItraceur k učení). | Model, postupy. |
| [Hobby analyzátor „hram“](https://dev.to/hram/my-ai-agent-wrote-all-the-code-for-an-orienteering-analyzer-the-hard-part-came-after-it-worked-594h) | Sken mapy + GPX + výsledky; afinní umístění mapy ručními body, řezání stopy podle blízkosti kontrol, „ideální vůdce“ z nejlepších mezičasů. | **neověřeno** | Poučení autora: diagnóza jde zautomatizovat, rozhodnutí, co změnit v tréninku, ne; a formáty výsledkovek se pořád rozbíjejí. | Model terénu. |

### Výpočet nejrychlejší cesty z orientační mapy

| Projekt / práce | Co dělá a jak | Licence | Co převzít | Co chybí |
|---|---|---|---|---|
| [OCAD Route Analyzer](https://www.ocad.com/wiki/ocad/en/index.php?title=Route_Analyzer) | Z vektorové mapy (správné symboly IOF) a výškopisu spočítá nejrychlejší postup mezi kontrolami a alternativy; každému symbolu přiřadí odpor, hodnoty jdou upravit; u sprintu se sklon váží méně. Výstup: délka, převýšení, odhad času. Neumí víc úrovní (mosty, podchody). | komerční (edice OCAD) | Je to nejbližší obdoba `bestroute.py`. Potvrzuje, že vektorové symboly jsou spolehlivější vstup než barvy. Alternativy přes průchozí body. | Osobní model, porovnání se stopou, vysvětlení ztráty. Tabulku odporů wiki neuvádí. |
| [Albert a Sárközy 2021](https://ica-proc.copernicus.org/articles/4/4/2021/) | Nejlevnější cesta (GIS) na orientační mapě z tří skupin prvků: terén, cesty, porost. Ověřeno proti postupům, které navrhli orienťáci různého věku; výpočet je uměl napodobit. Sami píšou, že ideální postup je zčásti subjektivní. | CC BY 4.0 | Způsob ověření (viz část 6). Konkrétní váhy stránka článku neuvádí (**neověřeno** v PDF). | Osobní kalibrace. |
| [Arnet 2009](https://www.yumpu.com/en/document/view/16531250/scientific-journal-of-orienteering-2009-vol17-international-) (Scientific Journal of Orienteering 17) | „Aritmetická analýza postupů“ na dlouhých tratích MS 2003 a 2005: rychlost závisí na překážkách (porost), na stoupání ve směru běhu a zvlášť na sklonu svahu, po kterém se běží. (jen výtah, **neověřeno**) | — | Třetí činitel: příčný sklon. My máme jen sklon ve směru běhu. | Software. |
| [Optimal Path Calculation in the Countryside](https://ceur-ws.org/Vol-2020/paper5.pdf) | A* mezi body a pořadí bodů jako úloha obchodního cestujícího. (**neověřeno**, jen výtah) | — | Nic nového proti našemu Dijkstrovi. | — |
| [AItraceur](https://github.com/guiguoz/AItraceur) | Návrh tratí genetickým algoritmem. Čte OCAD (zakázané oblasti z vektorových symbolů), bere dlaždice MapAnt a OSM, cenu pohybu počítá Toblerovou funkcí, hledá A*, alternativy jako k nejkratších cest s požadavkem na odlišnost, hlídá „psí nohy“. Tabulku cen terénu nezveřejňuje. | AGPL-3.0 | Nápad na alternativní postupy (k nejkratších, odlišných). Kód kvůli AGPL nepřebírat. | Osobní model, stopa. |
| [venkat8424/Optimal-Path-Orienteering](https://github.com/venkat8424/Optimal-Path-Orienteering) | Školní úloha: A* po obrázku terénu s výškami. | **neověřeno** | Nic. | — |

### Nástroje okolo map a tratí

| Projekt | K čemu | Licence |
|---|---|---|
| [ocad2geojson](https://github.com/perliedman/ocad2geojson) a [ocad2tiles](https://github.com/perliedman/ocad2tiles) | Čtení souborů OCAD (verze 10 až 2018) v JavaScriptu, export do GeoJSON, SVG a dlaždic. Knihovnu v Pythonu jsem nenašel. | **neověřeno** |
| [OpenOrienteering Mapper](https://github.com/OpenOrienteering/mapper) | Otevřený editor map; umí otevřít OCAD, vlastní formát `.omap` je XML. | GPL-3 (**neověřeno** v repozitáři) |
| [Purple Pen](https://purple-pen.org/) | Stavba tratí, export IOF XML. | BSD 3-Clause podle výtahu (**neověřeno**) |
| [MeOS](https://github.com/melinsoftware/meos) | Závodní kancelář, mezičasy. | AGPL-3.0 podle výtahu (**neověřeno**) |
| [Karttapullautin](https://github.com/karttapullautin/karttapullautin) | Z LiDARu udělá orientační mapu včetně porostu; přepsáno do Rustu. | GPL-3.0 (výtah) |
| [OmapClassifier](https://github.com/GeirSmestad/OmapClassifier), [TANVOM](https://zenodo.org/records/19437536) | Neuronové sítě, které z obrázku lesní mapy odhadují symboly ISOM 2017-2; TANVOM je datová sada k vektorizaci map. | **neověřeno** (stránka repozitáře se mi neotevřela) |

K názvům „OEvent“ a „OOCAD“ ze zadání jsem nenašel nic, co by se týkalo analýzy postupů.

### Co z toho plyne

- Nejbližší hotové věci jsou komerční a uzavřené (OCAD, Livelox). Převzít jde metody, ne kód.
- Otevřený kód, který by se hodil (QuickRoute, Karttapullautin, AItraceur, MeOS), je pod GPL nebo AGPL. Než z něj něco vezmeme, je potřeba rozhodnout licenci našeho repozitáře.
- Akademické práce potvrzují náš postup (cenový povrch z terénu a sklonu, nejlevnější cesta) a přidávají dvě věci, které nemáme: příčný sklon a ověření proti lidem.

## 2. Modely rychlosti podle terénu a sklonu

### Co se používá

| Model | Tvar | Z čeho vznikl | Slabiny pro nás | Zdroj |
|---|---|---|---|---|
| Naismith | zhruba 5 km/h a hodina navíc na 600 m stoupání, tedy asi 8 m rovinky za metr stoupání | pravidlo horala z 19. století | jen stoupání, chůze | [Wikipedia](https://en.wikipedia.org/wiki/Naismith%27s_rule) (z hlavy, **neověřeno**) |
| Tobler | v = 6 · exp(−3,5 · \|s + 0,05\|) km/h, nejrychleji při klesání 5 % | chůze po cestě | chůze, žádný terén | [Higgins 2021](https://findingspress.org/article/28107-hiking-with-tobler-tracking-movement-and-calibrating-a-cost-function-for-personalized-3d-accessibility) |
| Minetti 2002 | polynom 5. stupně: energie na metr podle sklonu. Běh po rovině 3,40 J/kg/m, minimum 1,73 při −20 %, při +45 % 18,93 | 10 běžců na pásu | je to energie, ne rychlost; v prudkém klesání slibuje víc, než lidé v terénu běží | [abstrakt](https://www.researchgate.net/publication/11202969_Energy_Cost_of_Walking_and_Running_at_Extreme_Uphill_and_Downhill_Slopes) |
| Strava GAP (2017) | empirická křivka „jaké tempo po rovině odpovídá stejnému tepu“; přínos klesání od určité strmosti už neroste | velká data uživatelů s tepem | cesty a silnice, ne les; křivka není zveřejněná jako vzorec | [Strava Engineering](https://medium.com/strava-engineering/an-improved-gap-model-8b07ae8886c3) (**neověřeno**, stránka vrátila 403, jen výtah) |
| Campbell a kol. 2019 | nesouměrná Lorentzova funkce sklonu; křivky pro různé percentily lidí | 421 247 aktivit ze Stravy | cesty | [Applied Geography](https://www.sciencedirect.com/science/article/abs/pii/S0143622818307859) (výtah) |
| Wood a kol. 2023 | v = exp(a + b·φ + c·θ + d·θ²), θ sklon ve směru chůze, φ sklon svahu; koeficienty zvlášť pro silnici, cestu a terén, překážky z LiDARu | 7 636 stop z Anglie a Walesu | chůze; průměr populace | [PLOS ONE](https://pmc.ncbi.nlm.nih.gov/articles/PMC10727444/), kód je podle článku na GitHubu |
| STRIDE (Campbell 2024) a Cutler 2026 | rychlost ze sklonu, hustoty porostu a drsnosti povrchu z LiDARu; nejvíc brzdí porost ve výšce 0,85 až 1,20 m; R² 0,81 | měřené přechody mimo cesty | chůze; potřebuje mračno bodů | [Scientific Reports](https://www.nature.com/articles/s41598-024-71359-6), [GIScience & RS 2026](https://www.tandfonline.com/doi/full/10.1080/15481603.2026.2626632) (**neověřeno**, jen výtahy) |

Chyba průměrných modelů proti skutečnosti podle Wooda: RMSE 1,10 jeho model, 1,24 Tobler, 1,27 Naismith. Rozdíl mezi modely je tedy menší než rozdíl mezi lidmi, a proto se vyplatí osobní kalibrace.

### Jak se kalibruje na jednoho člověka

- **Higgins 2021**: stejný tvar jako Tobler se třemi parametry (nejvyšší rychlost, strmost poklesu, posun optima) proložil nelineárními nejmenšími čtverci vlastními stopami ze 4 túr (14 449 bodů). Vyšlo 4,6 km/h, 1,54 a 0,033 místo Toblerových 6, 3,5 a 0,05. Sám upozorňuje, že je to vzorek jednoho člověka. ([zdroj](https://findingspress.org/article/28107-hiking-with-tobler-tracking-movement-and-calibrating-a-cost-function-for-personalized-3d-accessibility))
- **Trailový běh**: regrese rychlosti úseku ze sklonu, technické náročnosti, pořadí úseku v závodě a průměrné rychlosti běžce vysvětlila 81 % rozptylu ([Int. J. of Performance Analysis in Sport 2026](https://www.tandfonline.com/doi/abs/10.1080/24748668.2026.2651537), **neověřeno**, výtah). Jiná práce bere Minettiho křivku a na 13 závodech jednoho běžce ladí jen dva osobní parametry včetně poklesu tempa během závodu ([Sensors 2026](https://doi.org/10.3390/s26123731), **neověřeno**, výtah).
- **Mezičasy bez GPS**: log času úseku = rychlost běžce + obtížnost úseku + zbytek; ze zbytků se počítá nestabilita a závažnost chyb ([Wang 2026](https://journals.sagepub.com/doi/full/10.1177/22150218261460282), výtah).

### Je lepší přístup než náš?

Náš model (`oroute/speedmodel.py`): tempo = 1 / (v_rovina · činitel terénu) · násobitel sklonu, činitele terénu vycházejí z ISOM a posouvají se k datům podle toho, kolik sekund v terénu máme, sklon je lomená přímka naučená z běžných běhů. Stavbou je to stejná rodina jako Arnet, Wood i STRIDE (terén krát sklon). Zásadně lepší hotový model pro orientační běh jsem nenašel. Zlepšit jdou čtyři věci, seřazeno podle toho, co bych čekal od přínosu:

1. **Odhadovat všechno najednou v logaritmu rychlosti.** Dnes se postupně hledá rychlost na rovině, pak `up_k`, pak činitele terénu, pokaždé mediánem. Zelená bývá ve svazích, takže se terén a sklon pletou dohromady. Jedna regrese `log v = log v0 + terén + f(sklon) + chyba` s priorem z ISOM jako penalizací (hřebenová regrese, robustní ztráta) odhadne obojí společně a dá ke každému činiteli i nejistotu. Tu pak jde ukázat u úseku („postupy jsou v rámci nejistoty stejné“).
2. **Příčný sklon** jako další člen (Arnet, Wood). Běh po vrstevnici strmým svahem je pomalý, i když je sklon ve směru běhu nulový. V našem modelu taková traverza vychází stejně rychlá jako rovina, takže ji směrování přeceňuje.
3. **Klubový prior místo učebnicového.** Až bude víc členů, výchozí činitele terénu pro nového běžce mohou být průměr oddílu (částečné sdružení dat) a k učebnici se vracet jen tam, kde nemá data nikdo. Čtyři závody jednoho běžce dávají na tmavě zelenou 33 s dat; oddíl jich dá řádově víc.
4. **Menší šum vstupu.** Vzorky po krocích stopy mají v lese chybu polohy 5 až 10 m, takže bod občas padne do sousední třídy terénu. Pomůže brát okna 10 až 20 s a třídu terénu jako podíly tříd v okolí stopy místo jedné hodnoty. Hladší křivka sklonu (tvar Toblera nebo Lorentze se třemi parametry) by navíc odstranila zlom v lomené přímce; to je spíš kosmetika.

Dál stojí za zvážení člen pro únavu (pokles tempa s časem závodu, jak to dělají trailové modely) a činitel závodu: běžnost „bílého lesa“ se mezi terény liší a leave-one-race-out chyba −11 až +7 % tomu odpovídá. Obtížnost závodu jde odhadnout z nejlepších mezičasů kategorie (bod 1 seznamu), tedy bez GPS.

Každou z těchto změn je potřeba měřit stávajícím testem `--check` (jeden závod stranou). Bez toho nepoznáme, jestli pomohla.

**Stav 7. 10. 2026:** změřeno (`tools/jointfit.py`, `docs/validace.md` část 8). Bod 1 (společný odhad) chybu nezlepšil: celek 6,0 → 7,0 až 8,1 %. Bod 2 (příčný sklon) je jediný, který pomáhá (úseky 19,1 → 18,0 %, koeficient ve všech pokusech kladný), ale proti dosavadnímu modelu je zisk v šumu čtyř závodů. Bod 3 (klubový prior) je napsaný a vypnutý, s jedním běžcem ho nejde ověřit. Z bodu 4 jsou hotová okna a podíly tříd v okolí stopy (samy nepomohly); hladší křivka sklonu ne. Únava chybu zvýšila; obtížnost závodu z mezičasů nejde na dvou závodech otestovat. Aplikace používá dosavadní model, doplněný o nejistotu činitelů.

## 3. Čtení mapy přesněji než z barev

| Zdroj | Co dá | Právo a dostupnost | Doporučení |
|---|---|---|---|
| **Vektorová mapa OCAD / OOM od pořadatele** | Přesné symboly včetně zákazů, georeference uvnitř souboru. | Práva má vydavatel mapy. U závodů a map našeho oddílu je to věc domluvy uvnitř oddílu. | Pro vlastní mapy ano. Nejjednodušší cesta bez kódu: z OCADu vyexportovat georeferencovaný rastr bez tratě ve vysokém rozlišení a tratě jako IOF XML. Čtení `.ocd` přímo jen přes JavaScript ([ocad2geojson](https://github.com/perliedman/ocad2geojson)) nebo přes OpenOrienteering Mapper. |
| **Livelox** | Přes API jen tratě. „For copyright, attribution and privacy reasons, maps and routes are not accessible through the API.“ | [Dokumentace API](https://www.livelox.com/Documentation/Api); [uživatelská smlouva](https://www.livelox.com/UserAgreement) (znění z 7. 8. 2026) zakazuje „scrape data … or systematically extract data from the services except through authenticated and authorized API access“ a práva k mapám nechává pořadatelům. | Mapy dál ručně. Nezkoušet nic obcházet. |
| **mapy.ceskyorientak.cz** (Archiv map ČSOS) | Náhledy 96 dpi s vodoznakem „Archiv map ČSOS“, georeferencované pro Google Earth. ORIS na ně u závodu odkazuje (`Links`, typ „Stará mapa“). | [O projektu](https://mapy.ceskyorientak.cz/cs/text/about): autorská práva mají vydavatelé; náhledy neopravňují k použití pro organizované akce; plná data jen objednávkou. O API ani o strojovém přístupu stránka nemluví. | Jen jako odkaz na stránce závodu. Na analýzu je rozlišení malé a vodoznak by pletl barvy. Bez souhlasu ČSOS nestahovat hromadně. |
| **ČÚZK DMR 5G** (terén). **Stav: hotovo**, služba odpovídá na `ags.cuzk.gov.cz/arcgis2/rest/services/dmr5g/ImageServer`. | Výškopis z laserového skenování, chyba 0,18 m v otevřeném terénu a 0,3 m v lese. | [Otevřená data, CC BY 4.0, stahovací služba ATOM zdarma](https://geoportal.cuzk.cz/(S(2zqu5vtxd523dytpf1isrfve))/Default.aspx?mode=TextMeta&side=vyskopis&metadataID=CZ-CUZK-DMR5G-V&head_tab=sekce-02-gp&menu=302), [přehled otevřených dat](https://ags.cuzk.gov.cz/opendata/). Uvádět zdroj. | Ano, hned (bod 3 seznamu). Cizí projekt [orienteering-map-prep](https://github.com/severynoagent-ui/orienteering-map-prep) (MIT) bere výřezy z `https://ags.cuzk.cz/arcgis2/rest/services/dmr5g/ImageServer`; adresu jsem sám nezkoušel (**neověřeno**). README říká, že z cloudu ČÚZK dostupný nebyl, takže první krok je zkouška ze serveru, kde aplikace poběží. |
| **ČÚZK DMP 1G** (povrch) | Výšky včetně porostu a budov; rozdíl DMP − DMR dává výšku porostu. | Stejná licence ([metadata](https://geoportal.cuzk.cz/(S(0nc0sukzkzd2cptwc1vgzeua))/Default.aspx?mode=TextMeta&side=vyskopis&metadataID=CZ-CUZK-DMP1G-V&head_tab=sekce-02-gp&menu=303)). | Jen pokus. Skenováno 2009 až 2013, po kůrovci a těžbě neodpovídá. Výška porostu navíc není průchodnost; podle [STRIDE](https://www.nature.com/articles/s41598-024-71359-6) rozhoduje hustota ve výšce kolem 1 m, a tu z rozdílu dvou povrchů nepoznáme. Mapa od mapaře je lepší zdroj. |
| **OpenStreetMap**. **Stav: hotovo** pro železnice a dálnice (`oroute/osm.py`). | Železnice, silnice, ploty, zdi, budovy, vodní plochy; přejezdy, mosty a podchody jako body a úseky. | [ODbL, povinné uvedení zdroje](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines); veřejný Overpass snese podle zásad do 10 000 dotazů a 1 GB denně, dotazy po jednom. | Ano, na zakázané přechody (bod 5 seznamu). Jeden dotaz na závod, výsledek uložit. |
| **MapAnt** | Automatická mapa z LiDARu pro celé státy. | Pro Česko jsem existenci a podmínky neověřil (**neověřeno**). | Zatím ne. |
| **Neuronové sítě na obrázek mapy** | Odhad symbolů ISOM z rastru. | [OmapClassifier](https://github.com/GeirSmestad/OmapClassifier), [TANVOM](https://zenodo.org/records/19437536) (**neověřeno**). | Ne. Velká práce, nejistý výsledek, a měnilo by to zásadu „žádná AI v analýze“. |

### Zakázané a nepřekonatelné prvky

- ISOM 2017-2 rozlišuje dvě věci. „Out-of-bounds“ je zákaz: hranice 708 se nesmí překročit, oblast 709 a plocha 520 se nesmí vstoupit. „Impassable / uncrossable“ (například nepřekonatelný sráz 201) zákaz není, jen je to pro běžného elitního závodníka příliš těžké nebo nebezpečné ([ISOM 2017-2](https://omapwiki.orienteering.sport/specifications/isom/), znění podle výtahu). Pro model to znamená dvě různé hodnoty: zákaz je nekonečná cena, nepřekonatelné je velmi vysoká cena.
- Z rastru Livelox jde barvou chytit olivovou plochu 520 a fialové šrafy 709. Čárové zákazy (708, nepřekonatelný plot, železnice) jsou tenké a po kompresi JPEG nespolehlivé.
- Jestli je železnice sama o sobě zakázaná, mapový klíč neřeší jednotně; rozhodují pokyny závodu a pravidla (**neověřeno**, zeptat se). Proto doporučuji kombinaci: překážky z OSM (`railway=rail`, `highway=motorway|trunk`, `barrier=fence|wall`), průchody tam, kde OSM má `railway=level_crossing`, `railway=crossing`, most nebo tunel, a k tomu ruční zakázaná čára v aplikaci, sdílená pro všechny běžce závodu stejně jako dnes značka občerstvení.

**Stav 7. 10. 2026:** kombinace je hotová: železnice a dálnice z OSM s přepínačem „zakázáno / jen znevýhodněno / nepoužívat“ u závodu, průchody z přejezdů, mostů a tunelů, ruční zakázaná a těžko překonatelná čára sdílená pro závod. Ploty a zdi z OSM se stahují, ale nepoužívají (`OB_OSM_FENCES`). Čtení zákazů z rastru (olivová 520 se čte už dřív, fialové šrafy 709 ne) přidané není.

### Co je legální a technicky možné stáhnout

| Zdroj | Stáhnout automaticky? |
|---|---|
| ORIS API (závody, kategorie, mezičasy, odkazy, souřadnice) | ano, veřejné, bez klíče |
| ČÚZK DMR 5G, DMP 1G | ano, CC BY 4.0 |
| OpenStreetMap přes Overpass | ano, ODbL, s uvedením zdroje a šetrně |
| Livelox tratě | jen s klíčem, o který se žádá |
| Livelox mapy a trasy | ne |
| Náhledy z mapy.ceskyorientak.cz | technicky jsou veřejné, právně bez svolení nedoporučuji |
| OCAD soubory | jen od vydavatele mapy |

## 4. Automatizace vstupů

### ORIS API (ověřeno voláním 6. 10. 2026)

[Dokumentace](https://oris.ceskyorientak.cz/API) vyjmenovává metody, o limitech ani podmínkách nic neříká. Zkusil jsem `getEvent` pro závod 9827 (Petřvald) a `getSplits` pro jeho kategorii H18:

- `getEvent` vrací `LiveloxID` (182468), `GPSLat` a `GPSLon` centra, `Locations` (další pojmenované body se souřadnicemi), `Links` (mimo jiné „Stará mapa“ s adresou na mapy.ceskyorientak.cz), `Documents` (rozpis, pokyny v PDF), `StartTime` a `Classes` s délkou, převýšením, počtem kontrol a příznakem `Splits`.
- `getSplits` vrací `Splits` (řádek na každého běžce kategorie: `RegNo`, `StartTime`, `FinishTime`, mezičas a pořadí na každé kontrole), `Controls` (kód kontroly, nejlepší a druhý mezičas) a `BestTime`.
- `getUser?rgnum=BFM0903` vrací ID 45118. Stejné číslo má vizitka na klubovém webu (`/clen/45118`).

Omezení: ORIS má občas výpadky. Stránka [Stav](https://skobfm.vzdyonline.cz/stav) klubového webu měla 20. 9. u stahování z ORIS chybu („vrátilo HTML místo JSON“, HTTP 502). Proto ukládat odpovědi, opakovat s prodlevou a nespoléhat na okamžitou odpověď. A protože klubový web stahuje totéž každou hodinu, je slušné stahovat jen jednou a data si předat (viz „Klubový web“).

**Stav 7. 10. 2026:** ORIS se volá s prodlevou 0,4 s, odpovědi se ukládají (závody, kategorie, mezičasy celých kategorií, `Locations`, `Links`); na kategorii se ptá jednou. Z `Links` se bere odkaz na OResults.

### Tratě

- **Livelox API**: `GET /orienteering/courses/iofxml` (rozsah `courses.read`) dává tratě se souřadnicemi kontrol; `GET /events` a `/events/{id}` informace o závodě. Přístup e-mailem na info@livelox.com, každou žádost posuzují zvlášť. Podmínky: aplikace nemá Livelox „replicate or compete directly“, API je „intended for publicly available applications, not private or personal use“, klíč nesmí být v klientském kódu, data si ukládat a neposílat zbytečné dotazy ([dokumentace](https://www.livelox.com/Documentation/Api)). Náš rozbor postupů se Livelox částečně podobá a aplikace je za přihlášením, takže zamítnutí je možné. V žádosti napsat pravdivě, co děláme, a že mapy ani trasy z Livelox nebereme.
- **Bez klíče** zůstává čtení fialového tisku z KMZ jako dnes. Oficiální mezičasy dají počet kontrol a časy, takže pořadí jde hlídat ještě přísněji.
- **Závody pořádané oddílem**: export tratí z OCADu nebo Purple Penu do IOF XML, žádné rozpoznávání.

### Aktivity

| Možnost | Jak | Omezení | Doporučení |
|---|---|---|---|
| Nahrání `.fit` (i víc najednou) a celého exportu Garmin | jako dnes | ruční krok po každém závodě | Základ. Zlepšit jen pohodlí: přetažení víc souborů, nahrání z mobilu. |
| Strava API | OAuth, webhook o nové aktivitě, proudy poloha, čas, výška, tep | Nová aplikace má 1 sportovce, samoobslužně 10, víc po posouzení bez záruky ([limity Stravy](https://developers.strava.com/docs/rate-limits/): 100 čtecích dotazů za 15 min, 1 000 denně). Od listopadu 2024 smí aplikace ukazovat data jen jejich vlastníkovi a nesmí je dávat do AI ([DC Rainmaker](https://www.dcrainmaker.com/2024/11/stravas-changes-to-kill-off-apps.html), výtah). Podle [shrnutí třetí strany](https://tryterra.co/blog/strava-api-changes-2026) potřebuje vývojář ve vyšší úrovni od června 2026 placenou Stravu (**neověřeno** u Stravy). | Druhá fáze, pro pár zájemců. Srovnání tras mezi členy z dat Stravy dělat nesmíme. Osobní model je statistika, ne AI, ale zákaz je formulovaný široce; před nasazením si přečíst aktuální smlouvu. |
| Garmin Connect Developer Program | oficiální API, dává aktivity | Jen pro právnické osoby, ruční schvalování; podle několika zdrojů jsou nové žádosti v roce 2026 pozastavené ([Rook](https://tryrook.io/blog/garmin-connect-api-access), výtah; **neověřeno** u Garminu). | Ne. |
| Neoficiální knihovny s heslem ke Garminu | — | Proti podmínkám, web by držel cizí hesla. | Ne (beze změny proti `docs/automatizace.md`). |
| Hodinky jiných značek | Aplikace Control synchronizuje Garmin, Suunto, Polar a COROS, takže rozhraní existují. | Podmínky jednotlivých výrobců jsem nezjišťoval (**neověřeno**). | Neřešit, dokud to někdo z oddílu nepotřebuje. |

### Párování aktivit se závody

Dnes podle data a oficiálního času startu. ORIS dává navíc souřadnice centra a dalších míst (`GPSLat`, `GPSLon`, `Locations`), takže jde přidat podmínku „začátek aktivity do několika kilometrů od centra“. To pomůže ve dnech se dvěma závody nebo se závodem a rozklusáním. U štafet a závodů bez času startu rozhodne právě poloha.

**Stav 7. 10. 2026:** hotovo. Aktivita, která začíná dál než 10 km od centra a pojmenovaných míst závodu, se nevezme, když ten den existuje jiná u závodu; závod bez oficiálního času dostane aktivitu nejblíž centru. Na celém Garmin exportu (10 074 souborů) rozhodla poloha u dvou závodů.

### Umístění mapy podle GPS a mapy bez KMZ

Nápad, který se opírá o data, jež už máme:

1. Z ORIS známe čas ražení každé kontroly. Poloha stopy v těch časech je odhad souřadnic kontrol (chyba GPS 5 až 15 m, bez soustavného posunu, pokud sedí hodiny).
2. Na obrázku mapy s tratí už umíme najít kolečka a jejich pořadí (`oroute/course.py`).
3. Dvojice „pixel kolečka ↔ souřadnice“ pro 10 až 25 kontrol stačí na podobnostní nebo afinní transformaci metodou nejmenších čtverců, s vyřazením odlehlých bodů (RANSAC). Víc běžců stejného závodu chybu zprůměruje.

Tím by šla použít fotka mapy z mobilu nebo sken, ne jen KMZ z Livelox. Na terén je pořád potřeba mapa bez tratě, nebo fialový tisk z mapy s tratí odmazat (trať zakrývá jen malou část plochy). Existující nástroje to dělají ručně: [QuickRoute](https://github.com/jarkko/quickroute-gps) posouváním mapy, RouteGadget třemi body. Automatickou obdobu jsem nenašel, což neznamená, že neexistuje.

**Stav 7. 10. 2026:** hotovo přesně takhle (`oroute/georef.py`): kolečka bez znalosti měřítka, RANSAC, nejmenší čtverce, výsledek jako KMZ. Na Pohoře spárovalo 16 ze 16 kontrol, na Petřvaldu 19 z 19, rohy mapy do 20 m od původní georeference. Zatím jen pro mapu s tratí a jen s jedním běžcem; průměrování přes víc běžců a odmazání fialového tisku pro terén hotové nejsou.

### Doporučený jednoduchý postup pro běžce

1. Přihlásí se, registračku už má vyplněnou (z klubového webu).
2. Nahraje `.fit` nebo jednou celý export. Spárování je automatické.
3. U závodu, kde chybí mapa, vidí jedno tlačítko: „nahrát mapu“ (KMZ z Livelox, později i fotka). Mapa bez tratě platí pro celý závod.
4. Zbytek (ORIS, mezičasy, tratě, výškopis, OSM) se stáhne sám.

## 5. Chyby u kontrol a „ztratil jsem se u kontroly“

### Co existuje

- **Z mezičasů.** WinSplits: normální výkon běžce = jeho obvyklý poměr k referenčnímu času úseku (průměr 25 % nejlepších); chyba, když ztráta na úseku překročí 30 s a zároveň 25 % ([nápověda WinSplits](http://obasen.orientering.se/winsplits/help.aspx?topic=terms&lang=en), výtah). Wang 2026 totéž formálně: zbytky z modelu „běžec + úsek“ a z nich nestabilita a závažnost chyb ([článek](https://journals.sagepub.com/doi/full/10.1177/22150218261460282)).
- **Z GPS.** Hotový otevřený algoritmus na rozpoznání chyby u kontroly ze stopy jsem nenašel. Nástroje (QuickRoute, Control, Livelox) dávají podklady, tedy odchylku od spojnice, tempo a přehrání, a hodnocení nechávají na člověku.
- **Typologie chyb** je popsaná dobře: nedoběhnutí (zastavím dřív, myslím, že jsem jinde), přeběhnutí, chybějící náběhový bod, paralelní chyba ([O'Brien 2006](https://oobrien.com/2006/12/gps-tracks-and-orienteering-mistakes/), výtah; [O-training.net](https://o-training.net/blog/2011/04/13/gps-analysis-for-orienteering-the-basics/)).
- **Od ztráty k příčině.** Orienteering USA (srpen 2026): ztráta času je příznak, ne příčina. Příčiny dělí na nejasný cíl náběhu, slabé čtení mapy, nedodržený azimut, pomalé rozhodování o postupu a rozptýlenou pozornost. Platí i poznámka, že velikost ztráty po ztrátě kontaktu s mapou je hlavně věc štěstí, ne závažnosti chyby ([článek](https://orienteeringusa.org/2026/08/from-time-loss-to-root-causea-practical-approach-to-route-analysis/)).

### Jak to dělat u nás

Dnes máme signály „čas v posledních 100 m“, „stání“ a „o kolik delší než spojnice“. Návrh ve dvou krocích:

**Krok A, mezičasy (bod 1 seznamu).** Pro každý úsek spočítat referenční čas kategorie, normál běžce a ztrátu. Úsek je podezřelý, když ztráta projde oběma prahy. Tohle říká „kde“, a to i u běžce bez `.fit`.

**Krok B, tvar stopy u kontroly.** Jen na podezřelých úsecích spočítat pár čísel a z nich pravidly určit typ:

| Znak ve stopě | Jak změřit | Typ chyby |
|---|---|---|
| Stopa mine kontrolu do 30 až 40 m, pokračuje dál a vrátí se | nejmenší vzdálenost před ražením výrazně dřív než ražení; největší „přeběh“ za kontrolu ve směru úseku | přeběhnutí |
| Zastavení nebo bloudění před kontrolou, pak dojití | stání nebo prudký pokles tempa ve vzdálenosti 50 až 150 m před kontrolou, bez přeběhu | nedoběhnutí, nejistota |
| Stopa jde dlouho rovně vedle spojnice a u kontroly zahne skoro kolmo | boční odchylka v 80 % délky úseku nad prahem, poslední část kolmo na směr úseku | úhyb ze směru (azimut) |
| Smyčky kolem kontroly | součet změn směru v kruhu 100 m přes 360° | hledání v kruhu |
| Stání a po něm změna směru o víc než 60° | z funkce `stops` a směru před a po | zastavení a nové určení polohy |
| Nic z toho, jen pomalu | tempo proti modelu pro daný terén | fyzika nebo terén, ne mapa |

Prahy je potřeba nastavit na našich čtyřech závodech a poznámkách běžce („ztráta kontaktu s mapou“ je označená ručně, takže máme, proti čemu ladit).

**Pomoc „ztratil jsem se u kontroly“.** Stránka úseku by měla ukázat tři věci: (1) místo posledního jistého bodu, tedy kde stopa naposledy šla po čárovém prvku nebo přes výrazný bod, (2) výřez stopy s časovými značkami po 10 s, aby bylo vidět, kde se čas ztratil, a (3) návrh náběhového bodu: nejbližší křížení cest, roh louky nebo okraj vody do 150 až 200 m od kontroly, ze kterého je to ke kontrole nejkratší. Křížení cest jdou najít z třídy „cesta“ v `terrain.py` ztenčením čar na kostru a hledáním uzlů. Je to odhad z rastru, takže ho uvádět jako návrh.

**Stav 7. 10. 2026:** krok A i B jsou hotové (`oroute/splits.py`, `oroute/mistakes.py`), typ chyby je v tabulce úseků i v mapě. Z „pomoci“ je hotový jen bod 3 (návrh náběhového bodu z křížení cest, označený jako odhad); poslední jistý bod a časové značky po 10 s ne. Prahy nejsou laděné proti poznámkám běžce, žádné „ztráty kontaktu s mapou“ zatím neoznačil.

## 6. Jak ověřit, že „nejlepší postupy“ dávají smysl

Albert a Sárközy ověřovali proti postupům, které navrhli lidé. My máme lepší data: skutečné časy. Čtyři testy od nejlevnějšího:

1. **Vnitřní soudržnost (hned, bez dalších dat).** Čas nejlepšího postupu podle modelu nesmí být delší než čas skutečné stopy oceněné stejným modelem; jinak je chyba ve směrování. A „ztráta volbou + ztráta provedením“ má dát celkovou ztrátu úseku. Patří do rychlých testů.
2. **Model proti mezičasům kategorie (s bodem 1 seznamu).** Pro každý úsek čas nejlepšího postupu podle modelu proti referenčnímu času kategorie. Nemá sedět absolutně (ostatní jsou jinak rychlí), má sedět pořadí a poměry: úsek, který model považuje za dvakrát delší, má být dvakrát delší i pro ostatní. Míra: pořadová korelace přes úseky závodu a největší odchylky vypsat. Úsek, kde je model výrazně optimističtější než všichni, znamená skoro jistě chybně přečtenou mapu nebo zakázaný průchod.
3. **Zpětný test na vlastních čistých úsecích (už máme, rozšířit).** Jeden závod stranou a chyba předpovědi po úsecích, navíc rozdělená podle terénu, sklonu a délky úseku, aby bylo vidět, kde model lže soustavně.
4. **Srovnání variant mezi členy oddílu (až bude víc stop na stejné trati).** Stopy na úseku seskupit do variant (například podle toho, kterou stranou obcházejí překážku, nebo podle překryvu koridorů 25 m). Časy přepočítat na stejnou fyzičku, jak to dělá Livelox („vyrovnání rychlosti“). Pak se ptát: je varianta, kterou model označil za nejlepší, opravdu ta nejrychlejší? Míra: podíl úseků, kde se shodnou, a průměrný rozdíl v sekundách tam, kde ne.

K tomu dvě pojistky do výstupu:

- **Citlivost.** Přepočítat úsek s činiteli terénu posunutými o ±20 %. Když se nejlepší postup překlopí na jinou variantu, napsat u úseku „postupy jsou vyrovnané“ místo ztráty v sekundách.
- **Alternativy.** Ukazovat dva až tři odlišné postupy s rozdílem času (k nejkratších s podmínkou odlišnosti, jako AItraceur), ne jednu čáru. Běžec lépe pozná, kdy model přehání.

**Stav 7. 10. 2026:** testy 1 až 3 jsou hotové. Test 1 je v rychlých i pomalých testech a našel skutečnou chybu (silnice přečtená jako budova na Petřvaldu; opravená týž den odpoledne). Test 2 je v aplikaci u každého závodu: pořadová korelace 0,94 (Pohora) a 0,93 (Petřvald; po opravě 0,95). Test 3 je na stránce modelu (předpověď z ostatních závodů), bez rozdělení podle terénu a sklonu. Test 4 (varianty mezi členy) se dělat nebude ze stop členů (soukromí); šel by jen z oficiálních mezičasů. Obě pojistky (citlivost ±20 % a alternativy) jsou hotové.

Při srovnání s ostatními počítat s vyšlapanými stopami: rozbor 4,25 milionu úseků z O-Ringenu vyšel tak, že stý běžec na úseku je asi o 3,6 % rychlejší než první a dvoustý o 7,3 % ([Leif Blake 2025](https://leifblake.ca/2025/01/01/orienteering-split-analysis.html)). Pozdní startovní čas tedy sám o sobě dělá rozdíl velikosti malé chyby.

## Klubový web (https://skobfm.vzdyonline.cz/)

Prošel jsem všechny stránky z menu a od každého typu podstránky vzorek (stránka závodu z ORIS a z WinSplits, budoucí závod, vizitka člena, detail žebříčku, exporty). Celkem zhruba 40 načtení stránek s pauzami, bez přihlášení a bez odeslání formuláře. `robots.txt` web nemá (vrací stránku 404).

### 1. Jaká data a odkazy web má

| Stránka | Adresa | Co obsahuje |
|---|---|---|
| LIVE | `/` | „Dnes závodíme“: v den závodu startovka a průběžné výsledky z OResults, obnova po 3 minutách; box novinek |
| Budoucí závody | `/nadchazejici`, `?okno=7\|14\|30` | přihlášky oddílu (datum, závod, disciplína, oblast, úroveň, počet přihlášených, odkaz na ORIS), kalendář po měsících s filtrem oblastí |
| Minulé závody | `/archiv`, `?season=2026`, `?clen=<id>`, `?misto=`, `?od=&do=` | řádek na závod: datum, název, místo, pořadatel, disciplína, úroveň, oblast, počet našich, nejlepší umístění, zdroj |
| Stránka závodu | `/zavod/oris-<ORIS ID>`, `/zavod/winsplits-<id>`, `/zavod/oresults-<id>`, `/zavod/dokumenty-<n>`; budoucí `/nadchazejici/zavod/<ORIS ID>` | místo, start 00, pořadatel, disciplína, ražení, termíny, souřadnice (u budoucích), odkazy Detaily / Startovka / Výsledky na ORIS a OResults; záložky Výsledky (člen, kategorie, umístění z počtu, čas, ztráta, pořadí v oddíle, zdroj) a Přihlášky (u budoucích i registračka, čip a čas startu) |
| Žebříčky | `/zebricky`, `/zebricky/<ORIS ID žebříčku>` | pořadí a body členů v dlouhodobých žebříčcích od 2013 |
| Členové | `/clenove`, `/clen/<ORIS ID osoby>` | jméno, registrační číslo, SI čip, kategorie, počet výsledků; vizitka: členství, licence, graf výkonnosti, žebříčky, všechny závody |
| Statistiky | `/statistiky`, `?od=&do=` | závody, dokončené, vítězství, 2.–3. místa, průměrné umístění |
| Porovnání v letech | `/porovnani?clen=&serie=` | vývoj v sérii závodů |
| Chyby a náměty | `/napady` | veřejný formulář a hlasování (nepoužil jsem) |
| Plán vývoje, Novinky, Stav | `/funkce`, `/novinky`, `/stav` | co je hotové a co se chystá; zdraví stahování |

Strojově čitelné výstupy:

| Adresa | Formát | Obsah |
|---|---|---|
| `/export/vysledky.csv?season=<rok>` nebo `?clen=<ORIS ID osoby>` | CSV, středník, UTF-8 s BOM | sloupce: datum; závod; etapa; místo; pořadatel; disciplína; úroveň; region; člen; kategorie; umístění; startujících; čas; ztráta; stav; bez výsledku; jen podle jména; v oddíle; na prvního z oddílu; do finále A; ztráta na postup; země; zdroj; odkaz. Sezóna 2026 má 867 řádků. |
| `/export/vysledky.html?…` | samostatná stránka HTML | totéž k tisku |
| `/export/vysledky.rss` | RSS 2.0 | poslední závody s výsledky, odkaz na `/zavod/…` |
| `/export/kalendar.ics` | iCalendar | závody s přihláškami oddílu, UID `oris-<ID>@skob-results-bfm` |
| `/static/skob.css`, `/logo` | CSS, SVG | vzhled a logo |

Odkazy ven: ORIS (`Zavod?id=`, `Startovka?id=`, `Vysledky?id=`, zatím na starou doménu `oris.orientacnisporty.cz`), OResults (`oresults.eu/events/<id>`), OpenStreetMap a Mapy.cz u polohy závodu. WinSplits je zdroj dat, ale odkaz na něj stránka nemá („WinSplits: bez odkazu na výsledky“). **Odkaz na Livelox web nemá nikde** a mezičasy zatím neukazuje.

Co z toho jde napojit:

- **Seznam závodů a kategorie člena** bez volání ORIS: CSV s `?clen=<id>`, nebo lépe přímo tátova databáze.
- **Závody mimo ORIS.** Azymut Cup, který my vedeme jako ruční závod bez ORIS, klubový web má z WinSplits a OResults (Day 5 = `/zavod/winsplits-114458`, OResults 3633). Pro tyhle závody tedy oficiální časy existují a nemusíme jet jen z GPS. Jestli má táta v databázi i mezičasy, nebo jen výsledné časy, je potřeba se zeptat.
- **Registračka, čip, ORIS ID člena** pro předvyplnění profilu.
- **RSS** jako spouštěč: nový závod s výsledky znamená „dotáhni mezičasy a nabídni nahrání běhu“.
- V [plánu vývoje](https://skobfm.vzdyonline.cz/funkce) je položka „Výsledky na oddílovém webu“: hotový vkládací box a „stejná data ve strojové podobě“, zatím vypnuté. Až to táta zapne, je to čistší cesta než čtení CSV.

### 2. Jak by to pomohlo uživateli

- Nemusí zadávat registračku ani hledat závody: seznam a kategorie se vezmou z klubových dat.
- Z klubové stránky závodu se jedním klikem dostane na svůj rozbor a zpět na výsledky oddílu.
- Zahraniční závody, které v ORIS nejsou, se spárují s klubovým archivem místo ručního zadávání názvu a data.
- Mapa nahraná jedním členem poslouží všem, kdo závod běželi; klubová stránka závodu může ukázat „rozbor postupů je k dispozici“.
- Stejný vzhled, takže to působí jako jedna služba.

### 3. Mapování odkazů

| U nás | Na klubovém webu | Jak se spojí |
|---|---|---|
| stránka závodu `/races/<entry_id>` (tabulka `events`, sloupec `oris_id`) | `/zavod/oris-<oris_id>` | ORIS ID závodu, přímo |
| závod, který teprve bude | `/nadchazejici/zavod/<oris_id>` (podle novinek vede na stejnou stránku závodu) | ORIS ID závodu |
| ruční závod mimo ORIS | `/zavod/winsplits-<id>`, `/zavod/oresults-<id>` nebo `/zavod/dokumenty-<n>` | datum + podobnost názvu proti řádkům CSV (`datum`, `závod`, `zdroj`); první shodu potvrdit ručně a uložit k závodu |
| seznam mých závodů `/` | `/archiv?clen=<oris_user_id>&season=` | ORIS ID osoby (`users.oris_user_id`) |
| osobní model `/model`, profil `/profile` | `/clen/<oris_user_id>` | ORIS ID osoby; ověřeno, `getUser?rgnum=BFM0903` vrací 45118 a vizitka je `/clen/45118` |
| odkaz na ORIS a Livelox u závodu | stejné odkazy na ORIS má i klubová stránka | ORIS ID; Livelox jen u nás (`LiveloxID` z `getEvent`) |
| **zpět:** klubová stránka závodu → náš rozbor | nová stálá adresa u nás, například `/ob/zavod/oris-<oris_id>`, která přihlášeného pošle na jeho `/races/<entry_id>` a ostatním řekne, co je potřeba nahrát | ORIS ID závodu; táta přidá tlačítko vedle „Startovka“ a „Výsledky“ |
| **zpět:** vizitka člena → jeho rozbory | například `/ob/clen/<oris_user_id>` | ORIS ID osoby; vidí jen vlastník, nebo podle nastavení soukromí |

Naše adresy dnes stojí na interním `entry_id`. Pro odkazy z klubového webu je potřeba přidat adresu podle ORIS ID, protože klubový web naše interní čísla nezná.

**Stav 7. 10. 2026:** hotovo. Aplikace běží pod `/ob`; `/ob/zavod/oris-<oris_id>` přesměruje přihlášeného na jeho rozbor a `/ob/clen/<oris_user_id>` na jeho závody (cizímu členovi 403). Od nás vedou odkazy na `/zavod/oris-<id>`, `/clen/<id>` a `/archiv?clen=`. Spojení ručních závodů mimo ORIS s klubovým archivem (řádek „datum + podobnost názvu“) hotové není, stejně jako předvyplnění profilu z klubových dat a spouštěč z RSS. Tlačítka na klubovém webu musí přidat táta.

### 4. Jak aplikaci začlenit do webu

Co jde poznat zvenčí:

| Znak | Co z něj plyne |
|---|---|
| ETag statických souborů ve tvaru `"<čas>-<velikost>-<kontrolní součet>"` (`"1789753228.2730677-116273-1226252239"`) | takhle je tvoří Werkzeug, tedy **Flask** |
| Uvozovky v textu jako `&#34;`, názvy šablon `_table.html` a `clen.html` v komentářích | **Jinja2** |
| Stránka Stav: „Integrita databáze: quick_check: ok“, „databáze 10.9 MB“, „Migrace databáze: 39 použito“ | **SQLite** s vlastními migracemi |
| „Tep cronu live“, hodinové a denní úlohy, soubory `live-plan.toml`, `watch.toml`, `dokumenty.toml`, příkaz `skob-results conflicts` | **cron + příkazová řádka**, nastavení v TOML, balík se jmenuje `skob-results` |
| Hlavičky `Server: cloudflare`, `x-skob-kod: 44caaceea7a6` | za Cloudflare; hlavička nese verzi nasazeného kódu |
| CSP a `X-Frame-Options: DENY` | nic cizího se nenačte a web nejde vložit do rámu |
| CSS: „sdílený soubor, používá ho skob-results i oris2sidroid“ | táta už provozuje dvě aplikace se společným vzhledem |
| Plán vývoje: „Přihlašování uživatelů — zamítnuto. Web zůstává bez účtů a hesel.“ | veřejný web účty nemá a mít nemá; správa je na tajné adrese |
| Stav: „volno 1,6 GB“ | na serveru je málo místa na mapy a `.fit` |

Naše aplikace je Flask blueprint se SQLite a frontou úloh přes cron, takže technicky sedí. Dvě cesty:

- **A. Vedle klubového webu** (vlastní proces, cesta `/ob` nebo vlastní poddoména za stejným Cloudflare, vlastní databáze a přihlášení). Klubový web zůstane bez účtů, propojení je jen odkazy a společným CSS. Nejmenší zásah do tátova kódu a nejmenší riziko, že naše těžká analýza (Petřvald trvá 3 minuty CPU) zpomalí živé výsledky.
- **B. Blueprint uvnitř jeho aplikace** (`app.register_blueprint(ob_bp, url_prefix="/ob")`, jak popisuje `docs/web-aplikace.md`). Společné šablony a menu, ale do webu bez účtů by přibylo přihlašování a nahrávání souborů.

Doporučuji A a ze začátku číst klubová data přes CSV a ORIS ID. Přímé čtení jeho databáze až po domluvě.

**Stav 7. 10. 2026:** jde se cestou A, zatím jen lokálně; návod na nasazení je v `docs/web-aplikace.md`. Klubové CSV aplikace nečte, všechno bere z ORIS. Otázky na tátu níže zůstávají otevřené (s doplněním jsou v `docs/co-zbyva.md`).

Co potvrdit s tátou:

1. Je to opravdu Flask a SQLite a kde to běží (vlastní server, VPS, kolik CPU, RAM a disku)? Smí tam běžet druhý proces a pracovní úloha, která občas počítá minuty?
2. Účty: smí vedle veřejného webu existovat část s přihlášením? Kdo zakládá účty (jen členové podle registračky)?
3. Chce „Analýzu mezičasů“ z jeho plánu dělat sám, nebo ji máme dodat my (bod 1 našeho seznamu je přesně to)?
4. Má v databázi mezičasy, nebo jen výsledky? Z kterých zdrojů (ORIS, OResults, WinSplits)? Dá nám je, abychom nestahovali dvakrát?
5. Jak chce sdílet `skob.css` (kopie při nasazení, společný balíček, odkaz na jeho `/static/skob.css`)?
6. Přidá na stránku závodu a na vizitku tlačítko na náš rozbor? V jakém tvaru chce adresu?
7. Odkazy na ORIS vedou na starou doménu `oris.orientacnisporty.cz`, která podle našich poznámek jen přesměrovává; ví o tom?
8. Jak se staví k mapám na serveru (místo na disku, práva pořadatelů, viz otázky níže)?

## Otevřené otázky pro Tobiase

Na otázky 1, 2, 4, 6, 7 a 8 platí výchozí odpovědi ze zadání noční práce (Tobias je může změnit); stav je u každé otázky.

1. **Kde to poběží a pro koho?** Jen pro tebe a pár lidí, nebo pro celý oddíl? Podle toho se rozhodne Strava (limit 10 lidí), nároky na server i to, jestli stojí za to žádat Livelox o klíč. → **Stav 7. 10. 2026:** pro celý oddíl, zatím jen lokálně; účet se zakládá registračním číslem ORIS (jedno číslo = jeden účet).
2. **Mapy sdílené v oddíle.** Práva k mapám mají pořadatelé. Je v pořádku, aby mapu, kterou si jeden člen vyexportoval z Livelox, viděl v aplikaci celý oddíl? Navrhuji: jen za přihlášením, bez možnosti stažení, a zeptat se na to v oddíle (případně mapové rady oblasti). Chceš to řešit takhle, nebo mapy držet jen u toho, kdo je nahrál? → **Stav 7. 10. 2026:** mapy nahrává uživatel, vidí je jen přihlášení, kteří závod běželi, bez stažení, s poznámkou o autorských právech; mapa bez tratě je sdílená pro závod.
3. **Livelox klíč.** Má o něj požádat táta jménem oddílu? Počítej s tím, že ho nemusíme dostat. → **Stav 7. 10. 2026:** o klíč se nežádá.
4. **Licence repozitáře.** Bude kód veřejný a pod jakou licencí? Od toho závisí, jestli smíme převzít kód pod GPL nebo AGPL (QuickRoute, Karttapullautin, AItraceur). → **Stav 7. 10. 2026:** repozitář je soukromý, licence se neřeší; kód z GPL a AGPL projektů se nepřebírá.
5. **Vlastní mapy oddílu.** Má oddíl soubory OCAD svých map a tratí (například závod 3. 10. 2026 ve Vratimovských Zadkách, který SKOB pořádal)? Smíme je použít pro přesnější rozbor? → **Stav 7. 10. 2026:** nezodpovězeno, vektorové mapy se nepoužívají.
6. **Soukromí.** V oddíle je hodně dětí. Kdo smí vidět čí stopu? Chceš srovnání tras mezi členy (test 4 v části 6), nebo má každý vidět jen své? Stopy z běžných běhů ukazují, kde kdo bydlí; export z Garminu by se měl po spočítání sklonu mazat. → **Stav 7. 10. 2026:** každý vidí jen svoje stopy; srovnání mezi členy jen z oficiálních mezičasů; z Garmin exportu zůstanou jen běhy spárované se závody.
7. **Zakázané přechody.** Je podle tebe železnice v Petřvaldu zakázaná pravidly, pokyny, nebo jen nebezpečná? Podle toho ji model buď zakáže, nebo jen silně znevýhodní. → **Stav 7. 10. 2026:** výchozí „zakázáno“ kromě přejezdů, mostů a podchodů, s přepínačem u závodu.
8. **Zahraničí.** Jak důležité jsou polské závody? Pro ně by bylo potřeba dohledat polský výškopis; pro Česko stačí ČÚZK. → **Stav 7. 10. 2026:** v Polsku výškopis AWS jako dosud, ČÚZK pro české závody.
9. **Co má přednost ráno:** vzhled a propojení s klubovým webem, nebo mezičasy kategorie a rozpoznání chyb? → **Stav 7. 10. 2026:** udělalo se obojí.
10. **Poznámky běžce jako pravda pro ladění.** Smím tvoje ruční poznámky („ztráta kontaktu s mapou“, „obíhal zelenou“) použít jako vzor, proti kterému nastavím prahy pro rozpoznání chyb? → **Stav 7. 10. 2026:** nezodpovězeno; v databázi žádná taková poznámka nebyla, prahy jsou neladěné.

## Co jsem nemohl ověřit

- **Stránky, které se neotevřely:** blog Stravy o GAP (403), srovnání metod plánování tras v International Journal of Cartography 2025 (403, do textu jsem ho proto nezařadil), článek o STRIDE v Scientific Reports (přesměrování na přihlášení), PDF Campbell 2022 (nečitelné), repozitář OmapClassifier (404 při čtení, i když ho vyhledávač zná).
- **Licence uvedené jen podle výtahu z vyhledávače:** RouteGadget 2 (MIT), QuickRoute (GPL v3), Karttapullautin (GPL-3.0), Purple Pen (BSD 3-Clause), MeOS (AGPL-3.0). Licence DOMA, SplitsBrowser, ocad2geojson, Vikazimut a OpenOrienteering Mapper jsem nezjišťoval. Před převzetím čehokoli otevřít soubor LICENSE.
- **Stav API Garminu a nové úrovně Stravy v roce 2026** znám jen z blogů třetích stran, ne z oficiálních stránek. Limity dotazů Stravy jsou z její dokumentace.
- **Adresu služby ČÚZK pro výřezy DMR 5G** mám z cizího repozitáře; nezkoušel jsem ji. Licenci CC BY 4.0 uvádí ČÚZK sám. **Ověřeno 7. 10. 2026:** služba odpovídá (na doméně `ags.cuzk.gov.cz`), vrací výšky jako TIFF a mimo Česko prázdný obrázek.
- **Podmínky Livelox pro soubor KMZ, který si uživatel vyexportuje,** jsem v dokumentaci nenašel. Smlouva řeší práva pořadatelů a zákaz strojového vytěžování, ne další sdílení exportu.
- **MapAnt pro Česko, polský výškopis, rozhraní hodinek Suunto, Polar a COROS, WinSplits a OResults jako zdroj mezičasů:** nezjišťoval jsem.
- **Arnet 2009, 2DRerun AutOanalysis, WinSplits prahy, Minetti, Campbell 2019:** čísla a popisy jsou z abstraktů a výtahů, plné texty jsem nečetl.
- **Technologie klubového webu** je odhad z vnějších znaků; potvrdí ji jen táta.
- **Pravidla pro přebíhání železnice** jsem nedohledal.
- V prostředí není Playwright; screenshoty jsou z bezhlavého Chromu.

## Co zbývá teoreticky (stav 7. 10. 2026)

Věci z průzkumu, které hotové nejsou, seřazené podle toho, co bych dělal dřív. Praktické nedodělky a nejistoty toho, co hotové je, jsou v `docs/co-zbyva.md`.

**Opravit a doladit to, co už běží**

| Věc | Odkud | Co by to chtělo |
|---|---|---|
| ~~Prahy čtení mapy podle rozlišení mapy~~ | nález kontrolní sady (část 6, test 1) | **hotovo 7. 10. odpoledne**: `oroute/terrain.py` násobí velikosti značek rozlišením mapy (`docs/validace.md`, část 12) |
| Prahy typů chyb proti poznámkám běžce | část 5 | pár označených „ztrát kontaktu s mapou“ |
| Poslední jistý bod a časové značky po 10 s u ztracené kontroly | část 5, „pomoc“ | čárové prvky z `terrain.py`, výřez stopy na stránce úseku |
| Náběhový bod i z rohů luk a okrajů vody, ne jen z křížení cest | část 5 | hrany tříd v `terrain.py` |
| Zpětný test modelu rozdělený podle terénu, sklonu a délky úseku | část 6, test 3 | rozšířit `oroute/personal.py --check` |
| Čas plánovaného postupu podle modelu | `web-aplikace.md` | ocenit nakreslenou čáru funkcí `route_metrics` |

**Model rychlosti (část 2)**

| Věc | Stav | Co by to chtělo |
|---|---|---|
| Příčný sklon | změřen, slibný | víc závodů; pak doplnit do ceny hran v `routing.py` |
| Klubový prior | napsaný, vypnutý | aspoň tři další běžce s daty |
| Únava, obtížnost závodu z mezičasů | změřeno, nepomáhá / málo dat | aspoň pět závodů s mezičasy |
| Hladší křivka sklonu (tvar Toblera nebo Lorentze) | neděláno | kosmetika, odstraní zlom |
| Model „běžec + úsek“ v logaritmu času (Wang 2026) místo WinSplits | neděláno | dal by nestabilitu a závažnost chyb; WinSplits zatím stačí |

**Vstupy a propojení (části 3 a 4, Klubový web)**

| Věc | Stav | Co by to chtělo |
|---|---|---|
| Mapa bez tratě z obrázku (odmazání fialového tisku) | neděláno | čtení terénu ze skenu, jiná paleta než Livelox |
| Usazení mapy z více běžců najednou | neděláno | průměrovat polohy kontrol přes běžce kategorie |
| Zakázané oblasti z rastru (fialové šrafy 709) | **hotovo 7. 10.** pro křížové šrafy (`oroute/hatch.py`) | svislé šrafy a zakázaná hranice jednou čarou (708) chybí |
| Polský výškopis (GUGiK) | neděláno | dohledat službu a licenci |
| Vektorové mapy OCAD u závodů oddílu | neděláno | soubory a souhlas oddílu; export rastru a IOF XML z OCADu |
| Závody mimo ORIS z klubového archivu (WinSplits, OResults) | neděláno | číst klubové CSV nebo databázi; dalo by oficiální časy i pro Azymut |
| Předvyplnění profilu a spouštěč z RSS klubového webu | neděláno | domluva s tátou |
| Tlačítka na klubovém webu k našim adresám | čeká na tátu | adresy jsou hotové |
| Nasazení na klubový server | neděláno | odpovědi na „Co potvrdit s tátou“ |

**Srovnání mezi členy (část 6, test 4)**

| Věc | Stav | Co by to chtělo |
|---|---|---|
| Varianty postupu na úseku z více stop a „vyrovnání rychlosti“ | nedělá se ze stop členů (soukromí) | šlo by jen se souhlasem, nebo z oficiálních mezičasů: kdo byl na úseku rychlý proti svému normálu |

**Záměrně se nedělá:** Livelox API klíč a import tratí z IOF XML, Strava, Garmin API, průchodnost z LiDARu (výška porostu), neuronové sítě na obrázek mapy, stahování map z Livelox nebo z Archivu map ČSOS.
