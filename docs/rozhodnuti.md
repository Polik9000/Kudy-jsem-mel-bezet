# Rozhodnutí z noci 6. → 7. 10. 2026

Co jsem zvolil tam, kde zadání nechávalo volbu nebo kde jsem narazil na něco nečekaného, a proč. Výchozí odpovědi na otevřené otázky z `docs/pruzkum.md` jsou ty ze zadání; tady jsou jen věci navíc.

## Prostředí a větev

| Rozhodnutí | Proč |
|---|---|
| Větev `web-aplikace` jsem založil z `main`. | Zadání říká „aktuální větev `web-aplikace`“, ta ale neexistovala; `main` už obsahoval `webapp/` i průzkum. |
| Vývoj běží v projektu Compose `obdev` s vlastním svazkem (`docker-compose.dev.yml`). | Výchozí svazek `ob_tracker_ob_data` obsahuje tvoje data (2 účty, 111 závodů). Nechtěl jsem do nich zapisovat nevyzkoušeným kódem. Do `obdev` jsem si je jen zkopíroval, abych ověřil migraci databáze. |
| Screenshoty dělá `tools/shot.mjs` s vynuceným `forced-colors: none`. | Bezhlavý Chrome na tomhle počítači hlásil `forced-colors: active` (kontrastní motiv Windows) a stránky vycházely černé se žlutými okraji. Vynucení dává stejné obrázky na každém stroji. |

## Vzhled a začlenění

| Rozhodnutí | Proč |
|---|---|
| `webapp/static/skob.css` je bajtově stejná kopie `docs/reference/skob-klubovy-web.css`; hlídá to test. | Hlavička souboru říká, že kopie se nesmí upravovat ručně. |
| `ob.css` nepředefinovává žádnou klubovou proměnnou. Jediná barva mimo proměnné je `--ob-trat-mapa: #7A2F86`. | Obrázek mapy je světlý i v tmavém režimu, kdežto `--vtisk` se v tmavém režimu zesvětluje pro tmavý podklad. Trať kreslená na mapě proto potřebuje světlou hodnotu natvrdo. |
| Barvy čar v mapě jsou třídy CSS (`path.ob-best` …), ne barvy předané Leafletu. | SVG atribut `stroke` neumí `var()`. Třída ho přebije a barva jde z proměnné. |
| Stránka závodu s mapou je přes celou šířku, levé menu je na ní schované pod třemi čárkami. | Mapa potřebuje místo; doporučuje to i `docs/design-klubovy-web.md`. Ostatní stránky mají levé menu. |
| Aplikace běží pod `/ob` přes obal ve `webapp/wsgi.py` (`OB_URL_PREFIX`), ne přes `url_prefix` u blueprintu. | Cesty uvnitř aplikace i v testech zůstávají stejné (`/races/5`), ven jdou jako `/ob/races/5`. Proxy klubového webu jen přepošle `/ob/...` beze změny. |
| Vlastní cookie `ob_session` s cestou `/ob`. | Na stejné doméně se nesmí srazit s ničím z klubového webu. |
| Hlavičky CSP stejné jako klubový web, navíc `img-src blob:`. | Leaflet si pro otočený překryv nic cizího nenačítá; `blob:` je pojistka pro budoucí export obrázku. |
| V menu je hodinový údaj jako na klubovém webu a pod ním jméno přihlášeného místo verze. | Verzi nese patička. |

## Účty a soukromí

| Rozhodnutí | Proč |
|---|---|
| Účet = registrační číslo ORIS + heslo. Přihlašovací jméno je registračka. | Výchozí odpověď 1. Heslo jsem nechal: bez něj by se za kohokoli přihlásil každý, kdo zná jeho registračku (jsou veřejné). |
| Když ORIS při registraci neodpovídá, účet se založí a jméno se doplní později. | ORIS má výpadky (průzkum). |
| **Na jednu registračku jen jeden účet** (doplněno 7. 10. na tvé přání). Hlídá to unikátní index v databázi a registrace. | Dva účty se stejným číslem se pletly při přihlášení registračkou. |
| **Registračka účtu se nedá změnit** (7. 10. večer, na tvé přání). Profil ji jen ukazuje a přepsání odmítne i databáze (trigger `users_regno_fixed`). | Po změně čísla v profilu zůstaly v účtu závody obou lidí, přihlásit se šlo oběma čísly a majitel druhého čísla si účet založit nemohl. |
| **K registraci je potřeba kód od správce**, jiný pro každou registračku (`flask --app webapp.wsgi invite REGISTRACKA`). Kód se počítá z tajného klíče aplikace (HMAC, 8 znaků), nikam se neukládá. | Registračky jsou veřejné, takže si kdokoli mohl založit účet na cizí číslo dřív než majitel. ORIS přihlášení pro cizí aplikace nemá a e-maily členů nedává; e-mailové ověření by chtělo seznam adres a poštovní server. Kód správce předá člověku, kterého zná. |
| Kód se kontroluje dřív, než aplikace řekne „účet už existuje“. | Bez kódu se nedá zjišťovat, kdo už účet má. |
| Databáze, která už dva účty se stejným číslem má, naběhne dál a napíše, jak nadbytečné smazat (`flask --app webapp.wsgi delete-account JMENO --yes`). Index se doplní, jakmile duplicity zmizí. | Aplikace nesmí při startu sama mazat účty. |
| Smazání účtu odstraní jeho závody, aktivity, analýzy, poznámky, modely a ručně přidané závody, které nemá nikdo jiný. Závody z ORIS, jejich mapy, mezičasy kategorií, občerstvovačky a zakázané čáry zůstávají. | Jsou sdílené pro všechny, kdo závod běželi. |
| Účty založené dřív (jméno + heslo) fungují dál; přihlásit se dá jménem i registračkou. | Starší účty bez registračky. |
| Z celého Garmin exportu zůstanou po zpracování jen běhy spárované se závody. Zip i ostatní běhy se smažou, zůstane odvozený model kopců. | Výchozí odpověď 4. Běžné běhy ukazují, kde kdo bydlí. Jednotlivě nahrané `.fit` se nemažou nikdy. |
| V testovacích datech `tests/fixtures/oris/getSplits_*.json` jsou jména a registračky cizích běžců nahrazené („Závodník 07“, `TST0007`). | Mezičasy jsou veřejné, ale do repozitáře jsem nechtěl ukládat osobní údaje cizích lidí (v H16C jsou děti). Tvůj řádek zůstal. |
| Stránka `/ob/clen/<ID>` cizího člena vrací 403 s odkazem na jeho vizitku na klubovém webu. | Každý vidí jen svoje. |
| Tabulka „Běžci kategorie“ ukazuje jména a časy z ORIS. | Jsou to veřejné výsledky; stopy z hodinek ostatních se neukazují nikde. |

## Mezičasy (WinSplits)

| Rozhodnutí | Proč |
|---|---|
| Normál běžce = medián jeho výkonnostních indexů přes úseky. | Nápověda WinSplits vzorec neuvádí (v průzkumu je označená jako neověřená). Medián je odolný vůči chybám, což je smysl „normálního výkonu“. |
| „25 %“ se počítá z očekávaného času úseku (reference / normál). | Totéž: zvolil jsem čtení, které dává smysl pro pomalejšího běžce. |
| Reference se počítá ze všech běžců, kteří mají na úseku čas, i z diskvalifikovaných. | Jejich mezičasy jsou platné časy na úseku. |
| ORIS se na mezičasy kategorie ptá jednou; odpověď je v tabulce `class_splits`. Starý závod bez mezičasů dostane prázdný záznam, aby se neptal znovu. | Šetrnost k ORIS. Prodlevu mezi dotazy jsem zvedl z 0,15 s na 0,4 s. |

## Výškopis

| Rozhodnutí | Proč |
|---|---|
| Web používá `OB_DEM=auto`: ČÚZK DMR 5G pro mapy v Česku, AWS jinde a jako zálohu. Skripty mají výchozí `--dem aws`. | Výchozí odpověď 6. Skripty musí dál dávat zlaté soubory `tests/golden` bajt po bajtu. |
| **Tím se u českých závodů ve webu změní osobní model** (sklony i stoupání postupů vycházejí jinak). Časy závodů se nemění. | ČÚZK sedí s barometrem hodinek výrazně líp než AWS: Petřvald 2,3 m proti 5,7 m, Pohora 3,5 m proti 8,0 m (`docs/validace.md`). Je to záměrná změna modelu. |
| Mřížku ČÚZK vyhlazuji Gaussem 10 m. | Model sklonu se učil z barometru vyhlazeného přes 15 s a postupy se oceňují po 2 m. Na syrové mřížce 2 m by se každý příkop počítal jako stoupání (Petřvald 409 m podél stopy proti 279 m z barometru). |
| Službu volám `exportImage` na `ags.cuzk.gov.cz`, jeden dotaz na mapu, výsledek do cache. Rozsah obrázku čtu ze značek GeoTIFF. | Služba vrací pixely čtvercové ve stupních a výřez si sama rozšíří; kdo věří svému požadavku, má výšky posunuté (stalo se mi to, viz validace). |

## Zakázané přechody

| Rozhodnutí | Proč |
|---|---|
| Železnice a dálnice z OSM: „zakázáno“ = buňky neprůchodné, „jen znevýhodněno“ = přechod stojí 90 s. | Výchozí odpověď 5 a ISOM (zákaz proti „nepřekonatelnému“). 90 s je odhad: přelézt plot nebo obejít sráz. |
| Ploty a zdi z OSM se stahují, ale **nepoužívají** (`OB_OSM_FENCES=0`). Kdyby se zapnuly, berou se jen jako „těžko překonatelné“. | Zadání mluví o železnici a dálnici. Ploty jsou v OSM zmapované nerovnoměrně (hodně u zahrad, málo v lese) a nemám nic, co by ukázalo, že pomáhají; plot, který v terénu není, by dělal okliky. |
| Železnice nebo dálnice na mostě či v tunelu se vynechá celá. Průchod je tam, kde OSM má přejezd, nebo kde cesta na mostě či v tunelu kříží překážku. | Pod mostem a nad tunelem se projít dá. |
| Čáry kreslím 4 buňky silné (asi 11 m). | Směrování má 16 sousedů včetně „koňských“ skoků; tenčí čáru by přeskočilo. |
| Ruční čára i přepínač jsou sdílené pro závod a smí je měnit každý, kdo závod běžel. | Stejně jako dosud značka občerstvovačky. |
| Když Overpass neodpovídá, analýza doběhne bez překážek a zkusí to při příští. | Veřejný Overpass bývá přetížený. `OB_OSM=0` stahování vypne úplně. |

## Zakázané prostory ze šrafování mapy (doplněno 7. 10.)

| Rozhodnutí | Proč |
|---|---|
| Čte se z **mapy s tratí**, ne z mapy bez tratě. | Fialový přetisk (šrafy) je jen na ní; na mapě bez tratě není ani jeden fialový pixel. |
| Hledají se malé uzavřené buňky mezi šrafami, ne šrafy samotné. Buňka musí mít okraj hlavně fialový a šikmý (45°); plocha je tam, kde je aspoň 6 buněk u sebe. | Křížové šrafování rozdělí mapu na spoustu stejných kosočtverců. Trať sama uzavřených tvarů skoro nedělá (kolečko, vnitřek osmičky), a ty jsou kulaté nebo po jednom. Na třech mapách bez šrafování tak nevyjde nic. |
| Černé čáry mapy se počítají jako stěna buňky. | Fialová pod černou čarou zmizí. Bez toho se pruh šraf podél silnice (Petřvald, jižní okraj) nenašel, protože krajnice každou buňku otevřela. |
| Plocha je pro postup **neprůchodná**; přejezd z OpenStreetMap ji neotvírá. Volba „jen znevýhodněno“ u ní není. | ISOM 709 je zákaz vstupu, ne obtížný terén. |
| Kontrola, která leží v zakázané ploše, se dosáhne z nejbližšího místa mimo ni. | Tak se chová směrování u každé neprůchodné buňky; trať do zákazu kontrolu nedává, jde jen o přesah o pár metrů. |
| Přečtené plochy se ukládají **na kategorii** (`hatch/class_<id>.json`), přepínač „zakázáno / nepoužívat“ je **na závod**. | Mapa s tratí je na kategorii a výřez se může lišit. Jestli se šrafám věří, je vlastnost závodu, stejně jako u železnice. |
| Čtení běží jako skript (`python -m oroute.hatch`), jednou na nahranou mapu; po novém nahrání mapy se čte znovu. | Výpočty zůstávají v `oroute`, web je jen spouští. Na Petřvaldu trvá asi 10 s. |
| Skripty bez `--barriers` plochy nepoužívají. | `tests/golden` musí vycházet bajt po bajtu. |
| Svislé šrafy (starší mapy, sprint) se od 7. 10. večer čtou: aspoň 6 tenkých fialových čar rovně vzhůru, každá aspoň 12 m, vedle sebe ve stejných rozestupech (2,5 až 13 m). | Ověřeno jen na nakreslené mapě v testu (i s „11“, úsekem běžícím na sever a písmeny, které se najít nesmí). Na čtyřech mapách z `data/` nenajde nic a Petřvald má stejných 7 křížově šrafovaných ploch jako předtím. Čtení šraf na Petřvaldu trvá 22 s místo 12 s. |
| Zakázaná hranice jednou čarou (708) se nečte. | Jedna fialová čára se podle vzhledu nedá odlišit od spojnice kontrol a nemám mapu, na které bych to ověřil; test na vlastní kresbě by ověřil jen můj předpoklad, jak se kreslí. Falešný zákaz je horší než chybějící. Jde nakreslit ručně. |

## Nejlepší postupy

| Rozhodnutí | Proč |
|---|---|
| Alternativy hledám metodou penalizace: koridor 30 m kolem už nalezených postupů zdražím 1,6× a hledám znovu. Alternativa musí vést aspoň 35 % délky mimo koridor a být nejvýš o 35 % + 30 s pomalejší. | „k odlišných nejkratších cest“ bez cizího kódu (AItraceur je AGPL). Čísla jsou odhad, jdou změnit v `oroute/routing.py`. |
| „Postupy jsou vyrovnané“ = některá alternativa vyjde rychlejší než nejlepší postup, když se terén mimo cesty zrychlí nebo zpomalí o 20 %. | Levné (jen přeceněné tři čáry, žádné nové hledání). Nezachytí variantu, kterou hledání alternativ nenašlo. |
| Web počítá 2 alternativy na úsek. | Dohromady až tři postupy, jak chce zadání. |

## Umístění obrázku mapy

| Rozhodnutí | Proč |
|---|---|
| Výsledkem je KMZ (obrázek + `LatLonBox` + natočení) se značkou `ob-header-px: 0`. | Zbytek analýzy ho čte jako export z Livelox, nic dalšího se nemuselo měnit. Výška hlavičky Livelox (145 px) už není natvrdo, mapa si ji nese sama. |
| Transformace je podobnostní, s měřítkem zvlášť v ose x a y. Plná afinní se počítá jen pro informaci (zkosení). | Víc `LatLonBox` neumí. |
| Obrázek jde nahrát jen jako mapa s tratí a jen k závodu s během a mezičasy z ORIS. | Bez koleček a časů ražení není podle čeho usadit. |
| Mapu bez tratě z obrázku nedělám (odmazání fialového tisku). *(Pro snímek z Livelox nahrazeno 19. 10., viz část „Dva snímky z Livelox“.)* | Barvy skenu neodpovídají paletě Livelox, čtení terénu by bylo špatné. Viz `co-zbyva.md`. |

## Typ chyby u kontroly

| Rozhodnutí | Proč |
|---|---|
| Pořadí pravidel: přeběhnutí, hledání v kruhu, nedoběhnutí, úhyb ze směru, nové určení polohy, jinak „pomalu“. | První pravidlo, které sedí, vyhrává; silnější důkaz dřív. |
| Klasifikuje se jen úsek s odhadem ztráty z GPS aspoň 40 s. | Tabulka v průzkumu říká „jen na podezřelých úsecích“. |
| Náběhový bod = nejbližší křížení cest 30 až 200 m od kontroly, na stránce označený jako odhad. | Křížení hledám bez kostry: na kružnici kolem bodu cesty počítám větve (tři a víc = křížení). `scipy` kostru neumí a novou knihovnu jsem kvůli tomu nepřidával. |

## Model rychlosti

| Rozhodnutí | Proč |
|---|---|
| Aplikace dál používá dosavadní model (odhad po krocích). | Zkouška vynecháním závodu: společný odhad v logaritmu rychlosti chybu nezlepšil. Čísla v `docs/validace.md`. |
| `oroute/jointfit.py` zůstává jako modul s příkazem na zkoušku, aplikace ho nevolá (19. 10. přesunutý do `tools/jointfit.py`, ať v jádře není kód, který appka nevolá). | Zadání: nechat v kódu jen to, co chybu nezvyšuje, jinak vypnout a zapsat. Příčný sklon vychází slibně, ale na čtyřech závodech je rozdíl v šumu. |
| Únava a obtížnost závodu z mezičasů nejsou zapojené. | Únava chybu zvýšila. Obtížnost závodu jde spočítat jen u dvou závodů se mezičasy, na test to nestačí. |
| Klubový prior je napsaný a otestovaný, ale vypnutý (`OB_CLUB_PRIOR=0`). | S daty jednoho běžce se nedá ověřit. |
| Nejistota činitele terénu na stránce modelu je odhad jedné směrodatné odchylky z rozptylu rychlostí a počtu nezávislých měření (15 s běhu = jedno). | Jen se ukazuje, model nemění. |

## Ovládání a rychlost (doplněno 7. 10.)

| Rozhodnutí | Proč |
|---|---|
| Stránka se sama načte znovu jen tam, kde ukazuje stav úloh (`<body data-obnovit>`: seznam závodů, úlohy, závod s čekající úlohou), a nikdy přes vybraný soubor, rozepsaný formulář, kreslenou čáru nebo psanou poznámku. | Dřív se načetla každá stránka, jakmile doběhla jakákoli úloha, a zahodila rozdělanou práci. |
| Vybraný úsek je v adrese (`#usek-N`). | Přežije načtení stránky a jde poslat odkazem. |
| Přihlášení trvá 90 dní od poslední návštěvy; cookie se posílá znovu jednou denně, ne s každou odpovědí. | Na telefonu se jinak přihlašovalo po každém zavření prohlížeče. Styly a skripty musí chodit bez cookie, aby je směla držet i proxy. |
| Styly a skripty mají v adrese otisk obsahu a platnost rok. | Bez toho se prohlížeč při každé stránce ptal serveru na každý soubor zvlášť. |
| Obrázek mapy zůstává v KMZ a vybaluje se na dotaz; vedle KMZ je jen malý soubor s rohy mapy. Adresa obrázku nese razítko nahrání a platnost rok, jen pro prohlížeč běžce (`private`). | Vybalená kopie by zdvojnásobila místo pro mapy (5 až 30 MB každá) a na serveru je ho málo. Prohlížeč si obrázek stáhne jednou, takže vybalování nevadí. |
| Úloha analýzy uloží stopu a mezičasy hned po `analyze.py`, jen když závod ještě nemá postupy. | U nového závodu je za půl minuty na co se dívat. U přepočtu by hotový rozbor na dvě minuty přišel o postupy. |
| Osobní model se přepočítá před hledáním postupů (`bestroute.py --samples-only`, pak model, pak postupy). | Dřív se postupy hledaly dvakrát: jednou starým modelem, podruhé novým. Co se model ze závodu naučí, na postupech nezávisí (`oroute/annotations.py`). |
| `oroute/course.py`: hlasy pro středy kružnic sčítá `np.bincount`, pořadí kontrol se skládá po vrstvách v numpy. | Stejné výsledky (`legs.csv` a `course.json` všech čtyř závodů bajtově shodné se zlatými soubory), `analyze.py` na Petřvaldu 33 s místo 149 s (v úloze webu, bez obrázků). |
| Úseky se procházejí pásem nad mapou, šipkami v něm a klávesami ← →; výběr úseku mapu nepřekresluje, jen mění tloušťky čar a vrstvu alternativ. | Tabulka úseků je pod mapou; po každém kliknutí se muselo zpátky dolů. |
| Alternativy mají v mapě čísla 2 a 3 jako v panelu a řádek v panelu čáru zvýrazní (najetím i klepnutím). | Byly stejně barevné a rozlišila je jen bublina po najetí myší, která na telefonu není. |
| Text poznámky se ukládá vteřinu po posledním úhozu, při výběru jiného úseku a při zavření stránky; odpovědi se berou v pořadí odeslání. | Dřív se ukládal až po opuštění pole. Kdo dopsal a klikl do mapy na jiný úsek, o text přišel. |
| Odpověď na poznámku, čáru nebo občerstvovačku nenese čáry postupů. | Mění se jen čísla; stránka si čáry drží. |
| Běh i obě mapy se u závodu nahrávají jedním formulářem (`/races/<id>/files`); běh se spáruje ručně s tím závodem a analýza se zařadí jednou. Staré adresy `/map` a `/upload` zůstávají. | Dřív tři formuláře a tři zařazení analýzy; běh se nahrával jinde a zpět k závodu se muselo dojít. |
| Formuláře se soubory posílá skript a ukazuje procenta; server mu místo přesměrování vrátí adresu (`views.go`). Bez skriptu fungují jako obyčejné formuláře. | Celý export z Garminu se nahrává minuty a stránka při tom vypadala mrtvě. |
| Zvolená sezóna v seznamu závodů se pamatuje v relaci. Na úzké obrazovce se schovají sloupce Aktivita a obě Mapy; stav „chybí …“ je odkaz do Podkladů. | Devět sloupců se na telefon nevešlo a tři z nich říkají totéž co Stav. |
| Oba přepínače nastavení závodu jsou jeden formulář. | Každý zvlášť přepočítával postupy všem, kdo závod běželi. |
| Na stav úloh se ptá jen karta, která je vidět. | Otevřené karty na pozadí se ptaly každých 20 s napořád. |
| Přečtený terén z mapy bez tratě se ukládá pro závod (`terrain/event_<id>.npz`, klíč: otisk `terrain.py`, velikost a čas mapy). | V jedné úloze se četl dvakrát a každý další běžec závodu ho četl znovu; na Petřvaldu je to 37 s. Po změně mapy nebo kódu se přečte znovu sám. |

## Pořadí kontrol a čtení terénu (doplněno 7. 10.)

| Rozhodnutí | Proč |
|---|---|
| S oficiálními mezičasy se pořadí kontrol bere z nich: poloha z hodinek v okamžiku ražení určí kolečko (`official.order_controls`, přiřazení s nejmenším součtem vzdáleností). Čáry a stopa pořadí potom jen kontrolují. | Tobiasův návrh. ORIS má přednost a hledání přes všechny podmnožiny kontrol nestačilo paměťově od zhruba 24 kontrol. |
| Pořadí z mezičasů se použije jen při stejném počtu koleček a kontrol, nejvýš jednom chybějícím ražení a mediánu vzdálenosti do 60 m. Jinak cesta z čar a důvod ve výpisu. | Stejné prahy jako u oficiálních časů samotných (`MAX_MISS_M`); pořadí, kterému se nedá věřit, je horší než žádné. |
| Bez mezičasů: do 20 kontrol přesná tabulka jako dřív, nad 20 hladová cesta vylepšovaná přehazováním úseků. | Do 20 kontrol se nesmí nic změnit (zlaté soubory; Azymut E4 má 20). Hledání s odhadem shora se na trati, kde kontrola leží na čáře jiného úseku, nedopočítalo; přehazování úseků tuhle past řeší jedním tahem a stopa pořadí stejně kontroluje. |
| Velikosti značek v `terrain.py` se násobí poměrem 1,33 / rozlišení mapy. Rozšíření o jeden pixel kolem čar (vyhlazené okraje) se nenásobí. | Na mapě s 0,59 m na pixel se silnice četla jako budova. Okraj vyhlazení má jeden pixel při každém rozlišení. |
| Osobní model skriptů a `data/petrvald/fit_samples.npz` jsem po opravě terénu nepřepočítal. | Změnilo by to zlaté soubory všech čtyř závodů; web si modely běžců přepočítá sám. Viz `co-zbyva.md`. |

## Větev `co-chybi` (7. 10. večer)

| Rozhodnutí | Proč |
|---|---|
| Večerní práci z pracovního stromu `main` (registrace s kódem od správce, neměnná registračka) jsem beze změny commitnul jako první commit větve `co-chybi`. `main` zůstal na `2158d9f`. | Zadání říká „všechno aktuální je v `main`“, ale tahle práce v něm ležela jen necommitnutá. Na větvi se neztratí a další kroky (příklad `BFM0000`, zapomenuté heslo) na ni navazují. Smazaný `docs/co_chci_pridat.txt` a nový `docs/New Text Document.txt` jsem nechal, jak jsem je našel, mimo commity. (Oba jsou 19. 10. pryč: přání je splněné.) |
| Plánovaný postup oceňuje skript `oroute/planned.py` v krátké úloze fronty (`price_plans`), ne přímo při uložení poznámky. | Načtení mapy, terénu a výškopisu trvá asi sekundu až několik sekund a bere paměť; ve webovém procesu by to běželo souběžně s analýzou. Úloha jde ve frontě před analýzami, ale na právě běžící analýzu počká (pracovní proces je jeden). Stránka si o výsledek řekne sama po 2 s. |
| Plán se oceňuje tím, co použila poslední analýza závodu: `best/speed_model.json`, uložený terén závodu a výškopis ze složky analýzy (i když tehdy ČÚZK neodpověděl a použil se AWS). | Jinak by se plán, nejlepší a běžený postup nedaly srovnat. Po každé nové analýze se plány ocení znovu v téže úloze. |
| Věta k plánu: rozdíl do 15 s proti nejlepšímu postupu je „plán byl dobrý“, ztráta nad 30 s proti času plánu je „při provedení“, plánu ses „držel“, když devět desetin stopy leží do 40 m od čáry. Jako důvod pomalejšího plánu se uvede jen ten, který podle hrubého odhadu stojí nejvíc sekund (stoupání, zelená, méně cest, délka). | Stejné prahy jako `explain()` v `bestroute.py` (15 s, 30 s); 40 m je odhad podle přesnosti GPS a kreslení prstem. |
| Plán rychlejší než nejlepší postup modelu se neschovává; věta řekne, že nejspíš vede zakázaným místem nebo jde o šum. | Ruční čára se oceňuje na plné mapě, hledání běží po buňkách 2 px a respektuje zákazy; `route_metrics` zákazy nezná (stejně jako u běženého postupu). |
| Tabulka v panelu úseku je jedna: nejlepší, plán, běžený, další možnosti. | Tři tabulky pod sebou by se na telefon nevešly; pět sloupců se na 390 px vejde (ověřeno v bezhlavém Chromu, tabulka 327 px bez posuvníku). |

### Pomocník „ztratil jsem se u kontroly“ (`oroute/relocate.py`)

| Rozhodnutí | Proč |
|---|---|
| Počítá se v úloze analýzy hned po nejlepších postupech, pro každého běžce zvlášť; když selže, analýza doběhne bez něj. | Potřebuje totéž co postupy (terén, výškopis, model, zakázané čáry) a stopu běžce. Trvá 6 až 23 s. |
| Azimuty jsou k severu obrázku mapy (magnetické poledníky), zaokrouhlené na 5°. | To ukazuje buzola položená na mapu; zeměpisný sever by se lišil o deklinaci a natočení mapy (u čtyř závodů 1 až 7°). |
| Záchytné body do 150 m (čára může být blíž než 30 m, bod ne), náběhový bod do 200 m a jen ve směru příchodu (do 70° od spojnice s předchozí kontrolou); když tam nic není, náběhový bod se nenavrhne. | Zadání: 150 m, náběh jako dosud 30 až 200 m, raději nic než bod za kontrolou. |
| „Dá se dojít“ = cesta z bodu ke kontrole po mřížce stojí nejvýš 2,5× tolik co přímý běh lesem plus 30 s; počítá se stejným hledáním jako postupy včetně zakázaných čar a prostorů. | Bod za řekou, plotem nebo železnicí nepomůže. Čísla jsou odhad. |
| Pořadí bodů: křížení cest a cesta přes vodoteč 1,0; budova a vodní plocha 0,9; paseka 0,75; kupa 0,7; cesta a vodoteč 0,65; okraj otevřené plochy 0,5. Nejlíp 45 až 110 m od kontroly, o čtvrtinu víc ve směru příchodu, bod stejného druhu ve stejném směru se nebere. Pod 0,38 se bod neukáže. | Bodový prvek určí polohu, čára jen jednu souřadnici. Váhy jsou odhad podle oka na čtyřech závodech (`docs/validace.md`, část 14). |
| Okraje hustníků a kusy polootevřené mozaiky se neukazují vůbec. | Na obrázcích vycházely jako místa, která se v terénu nedají pojmenovat. |
| Bloudění u kontroly: od chvíle, kdy je stopa poprvé do 200 m od kontroly, se sleduje „kolik ještě naběhám minus přímá vzdálenost“. Dokud běžec míří ke kontrole, to číslo se nemění; kde začne klesat, opustil přímý směr. Bloudění = aspoň 60 m a 30 s navíc na úseku se ztrátou od 40 s. | Jedno pravidlo pro přeběhnutí, kroužení i odbočení; `mistakes.py` dál říká, jaký typ chyby to byl. Prahy neladěné (žádné poznámky „ztráta kontaktu“ v datech). |
| Nejbližší záchytný bod při bloudění se hledá jen mezi bodovými prvky a jen do 120 m od stopy. | „Byl jsi 60 m od křížení“ dává smysl; „byl jsi 60 m od cesty“ ne, když nevím kde na ní. |
| Vrstva „záchytné body“ je na mapě vypnutá, zapne ji volba pod mapou nebo rozbalení části „Kdyby ses ztratil“. | Zadání chce vrstvu, která jde zapnout a vypnout; zapnutá u všech kontrol mapu zahltí. |

### Nastavení závodu po běžcích

| Rozhodnutí | Proč |
|---|---|
| Přepínače „železnice a dálnice“ a „zakázané prostory z mapy“ má každý běžec vlastní (`entries.own_osm_mode`, `own_hatch_mode`; NULL = jako závod). Změna přepočítá jen jeho postupy. | Výchozí řešení ze zadání. Dřív změna jednoho běžce přepočítala analýzu všem. |
| Výchozí hodnotu závodu mění jen ten, kdo nahrál mapu bez tratě; přepočítají se běžci, kteří v měněném přepínači nemají vlastní volbu. Když účet toho člověka zanikne, výchozí hodnotu nezmění nikdo (každý má dál vlastní volbu). | Zadání. Jiného „vlastníka závodu“ aplikace nemá a nechtěl jsem ho vymýšlet. |
| Vlastní volba stejná jako výchozí hodnota závodu se uloží, ale nic nepřepočítá. | Pro běžce se nic nezměnilo; volba ale drží, i když se výchozí hodnota později změní. |
| Ruční čáry a občerstvovačky zůstávají sdílené. U každé je vidět, kdo ji přidal (v nastavení i v bublině na mapě), a smazat ji smí jen on. Věc, jejíž autor už účet nemá, smí smazat kdokoli ze závodu. | Zadání; druhá věta proto, že by jinak po zrušení účtu zůstala čára navždy. |
| Přidání nebo smazání ruční čáry dál přepočítá postupy všem na závodě. | Čára je sdílená záměrně; jinak by každý viděl jiné postupy podle toho, kdy analýzu pustil. |

### Běhy z Garmin exportu

| Rozhodnutí | Proč |
|---|---|
| Úloha exportu (každý nahraný zip) nejdřív načte závody běžce z ORIS, teprve potom páruje a maže. | Zadání: běh ze závodu, který aplikace ještě neznala, se dřív smazal s ostatními. |
| Když ORIS neodpovídá, úloha doběhne, spáruje se závody, které aplikace zná, nespárované běhy smaže a napíše to do zprávy. | Soukromí má přednost (běžné běhy ukazují, kde kdo bydlí) a nahraný zip se po zpracování maže vždy. Druhá možnost, nechat při výpadku ORIS všechno, je otázka v `co-zbyva.md`. |
| „U závodu“ = stejný místní den jako závod běžce a start běhu do 15 km od centra nebo pojmenovaných míst závodu z ORIS. Když poloha závodu nebo běhu není známá, bere se běh jako „u závodu“. | Zadání (15 km; párování samo má 10 km). Bez polohy se to nedá rozhodnout a jde o den závodu. |
| Takový běh zůstane a v seznamu nahraných aktivit má „nespárované u závodu“ s tlačítky Přiřadit (ruční spárování, existující adresa `/races/<id>/activity`) a Smazat (`/activities/<id>/delete`, jen pro běhy bez závodu). | Zadání. |

### Účet: příklad registračky, zrušení účtu, zapomenuté heslo

| Rozhodnutí | Proč |
|---|---|
| Příklad `BFM0000` je šedý zástupný text pole a věta pod ním, v přihlášení, registraci i na stránce zapomenutého hesla; stejně chybová hláška registrace. | Tvoje přání. V přihlášení pole bere i staré uživatelské jméno, proto popisek zůstal „Registrační číslo nebo uživatelské jméno“. |
| Zrušení účtu z profilu potvrzuje heslo a dělá přesně to, co příkaz `delete-account` (`accounts.delete_user`); stránka předem vypíše, kolik závodů, běhů, rozborů, poznámek a modelů zmizí. | Zadání. Jedna funkce pro obě cesty, aby se nerozešly. |
| Zapomenuté heslo: `flask --app webapp.wsgi reset-code REGISTRAČKA` vypíše jednorázový kód (8 znaků, 40 bitů) platný 24 hodin; v databázi je jen jeho hash (`users.reset_hash`, stejné hashování jako hesla). Na `/ob/forgot` se s registračkou a kódem nastaví nové heslo. | Zadání; e-mail v aplikaci není. |
| Kód přestane platit po použití, po 24 hodinách, po vydání nového kódu a po pěti špatných pokusech. Špatný kód, prošlý kód i registračka bez účtu dostanou stejnou odpověď. | Osm znaků by se jinak dalo zkoušet; stejná odpověď neprozradí, kdo účet má. |
| Nové heslo neodhlásí jiná přihlášená zařízení. | Relace nese jen číslo účtu; odhlášení všude by chtělo verzi hesla v relaci. Zapsáno v `co-zbyva.md`. |

### Náběhový bod, zarážka a názvy podle ISOM 2017-2 (8. 10.)

| Rozhodnutí | Proč |
|---|---|
| Výpočet záchytných bodů má číslo verze (`oroute.relocate.VERSION`, teď 3), uložené v `relocate.json` a v `analyses.summary`. Rozbor bez něj nebo se starším dostane pruh „Přepočítat záchytné body“. | Petřvald v tvé instalaci byl spočítaný starším kódem a stránka to nepoznala. |
| Přepočet je krátká úloha `relocate` (jen `python -m oroute.relocate`), ne celá analýza. | Postupy se nemění; celá analýza Petřvaldu trvá minuty, tohle půl minuty. |
| Starý návrh náběhového bodu z `bestroute.py` (nejbližší křížení do 200 m) se už neukazuje vůbec. | Na směr nehleděl, proto ležel i za kontrolou. |
| Směr příchodu je směr od kontroly k bodu nejlepšího postupu 100 m (po trase) před ní. Bez nejlepšího postupu přímka od minulé kontroly. | Tvoje volba. Sto metrů proto, aby směr neotočil poslední ohyb kolem hustníku. |
| Náběhový bod je bodový objekt 30 až 200 m od kontroly. Přednost má ten, který leží do 30 m od nejlepšího postupu (a do 110° od směru příchodu), jinak objekt do 70° od směru příchodu. | Zadání: před kontrolou ze směru přibíhání. |
| *(Nahrazeno 8. 10. večer, viz další část.)* Zarážka: tři paprsky od kontroly ve směru postupu (0° a ±25°), 20 až 250 m. Bere se první linie, kterou protnou aspoň dva: cesta, vodoteč, břeh, okraj otevřené plochy od 1 ha, okraj zakázaného prostoru. Když je bodový objekt do 35° od směru blíž, bere se ten. | „Co jde poznat, že už jsi za tím.“ Dva paprsky ze tří proto, aby zarážkou nebyla cesta vedoucí podél směru. |
| Dvě linie do 5 m za sebou jsou jedna věc a pojmenuje se ta dřívější v pořadí cesta, vodoteč, břeh, okraj plochy, okraj zástavby. | Silnice má černou krajnici i plochu; louka za cestou začíná cestou. |
| Na stránce se tomu říká „zarážka“. | Tak se tomu v OB říká; „bod za kontrolou“ by nebyl vždy bod. |
| Názvy podle českého vydání ISOM 2017-2 (ČSOS): konec cesty, oplocenka, kupka (109), prohlubeň (111), jáma (112), výrazný terénní objekt (115), balvan (204), jáma s vodou (303), studna nebo nádrž (311), výrazný strom (417), posed (525), výrazný umělý objekt (530, 531), okraj zakázaného prostoru (520). | Zadání. „Oplocenka“ v klíči není (516 a 518 jsou plot); je to slovo, které jsi použil a které běžci používají pro oplocenou plochu. |
| Vrchol z výškopisu se jmenuje „vrchol“, ne „kupa“. | Aby se nepletl s kupkou 109 z mapy. |
| Oplocenka je jen uzavřená plocha 100 až 10 000 m² s aspoň dvěma čárkami dovnitř. Plot, který nic neuzavírá, se čte dál jako cesta. | Čtení plotu podle čárek dávalo ploty z přerušovaných cest; uzavřená plocha se poznat dá. Radši oplocenku minout než ji vymyslet (pokus číst čárky volněji: `docs/validace.md`, část 16). |
| Bodová značka se bere, jen když stojí samostatně (jedna skvrna své barvy správné velikosti). Z map hrubších než 0,9 m na pixel jen kupka a výrazný strom. | Na 1,33 m na pixel má V šest pixelů a tečka pět; falešný bod je horší než chybějící. |
| Velikosti značek jsou v metrech v terénu (značka 1 : 15 000 zvětšená na měřítko mapy pokrývá vždy stejně metrů). | Jedna sada pravidel pro každé rozlišení; měřítko mapy aplikace nezná. |
| Nečte se: výrazný keř (418), krmelec (527), mohyla (526), pramen (312), skupina balvanů (207), protáhlá kupka (110). | Keř: všechny zelené tečky na Petřvaldu byly stromy sadu. Ostatní nejsou na čtyřech mapách v počtu, na kterém by šlo pravidlo ověřit. |
| Bodové značky mají nižší váhu než křížení a budova (0,55 až 0,7) a tři stejné do 60 m ještě o 40 % menší. | Kupka v poli kupek polohu neurčí. |
| Čára nebo dům bez černé mapy (jen šedý tisk) se nepočítá; světle hnědá silnice není otevřená plocha. | Legenda a kód Livelox na Petřvaldu dávaly „křížení cest“ a „budovy“ vedle mapy. |
| Kde je nejbližší bod cesty její konec, ukáže se jen „konec cesty“. | Dvakrát totéž stejným směrem. |
| Tvary značek beru z normy, jak ji znám, a z výřezů čtyř map; z nahraného PDF jen čísla a české názvy. | PDF se v prostředí nedalo vykreslit (chybí `pdftoppm`), text přečíst šel. |
| `docs/csos-isom2017-2cz.pdf` a snímek obrazovky nejsou v commitech. | Tvoje volba. |
| Vážení náběhového bodu úhlem a vyřazení zelené hranice porostu z cest jsem zkusil a vrátil. | Změnilo 14 kontrol a ubralo skutečná křížení; na prohlédnutí všech nebyl čas. |

### Voda s břehem, oplocenky v postupech, zarážka po výsecích (8. 10. večer)

| Rozhodnutí | Proč |
|---|---|
| Plná modrá plocha od 30 m², kolem které je černý prstenec (aspoň 80 % nejčernějšího z prstenců širokých jeden pixel do vzdálenosti břehové čáry), je vodní plocha celá i s tou čarou, ať je jakkoli úzká. Pravidlo „modrá široká aspoň 9 m“ zůstává vedle něj. | Rybník u jedničky na Petřvaldu má 8 m: vyšel jako bažina a jeho břeh jako cesta, po které vedl nejlepší postup. Práh je změřený: deset rybníků Petřvaldu má 0,97 a víc, žádná jiná modrá skvrna čtyř map přes 0,66. |
| Uzavřená oplocenka je pro hledání postupů neprůchodná (plocha a 3,5 m kolem, tedy plot; `Grid(barriers=dict(mask=...))`). Průchod z OSM ji neotevírá. Vypínač nemá. | Tvoje zadání („prochází oplocenkou, opravit“). ISOM 518 se překonávat nesmí a nižší plot stojí čas. Širší pás by uřízl cestu vedoucí podél plotu. |
| Kontrola nebo bod uvnitř oplocenky se bere z jejího okraje. | Jinak by oplocenky vypadly ze záchytných bodů jako nedosažitelné. |
| Nejlepší postupy mají číslo verze (`bestroute.VERSION`, teď 2) v `best.json` a v `analyses.summary`. Rozbor se starší verzí ukáže pruh „Přepočítat postupy“ (celá analýza; spočítá znovu i záchytné body, takže druhý pruh se neukazuje). | Stejný důvod jako u záchytných bodů: starý rozbor by dál vedl postup rybníkem a stránka by to nepoznala. |
| Co stopa překročila (`routing.crossed`): zakázanou čáru, když ji protne dál než 14 m od průchodu a dostane se aspoň 8 m na obě strany; plochu nebo oplocenku, když v ní leží aspoň 10 m stopy 5 m od okraje. | Ocenění stopy zákazy nezná, takže stopa přes železnici vyjde rychlejší než nejlepší postup, který musí k přejezdu. Bez věty „kříží železnici“ to vypadá jako rozbitý model. Prahy jsou kvůli GPS: stopa podél trati přes ni kmitá. |
| Na Petřvaldu jsem železnici nepřepínal. Věta v panelu řekne, kde to přepnout. | Jestli se přebíhat smělo, víš ty; volba „Železnice a dálnice“ je v Nastavení závodu pro každého běžce zvlášť. |
| Řádek tabulky postupů se jmenuje „tvoje stopa“, ne „běžený“, a pod tabulkou je, že všechny časy v ní počítá model. | „Běžený 3:01“ jsi četl jako naměřený čas; naměřený byl 3:35. |
| Zarážka je to, na co narazí běžec, který kontrolu přeběhl: vějíř paprsků po 10° do ±60° kolem směru, 15 až 200 m za kontrolou, první zásah cesty, vodoteče, břehu, plotu oplocenky, okraje paseky nebo velké otevřené plochy, okraje zástavby nebo budovy. Bodové značky a konce cest zarážkou nejsou. | Tvoje zadání: „něco uvidíš, tak se zastavíš, nebo cesta, kterou budeš jistě křížit“. Konec cesty mineš o 20 m a nevíš o něm. |
| Výsledek má tři části: vlevo (paprsky −60° až −30°), rovně (−20° až +20°), vpravo. Část se počítá, když aspoň polovina jejích paprsků zasáhne stejný druh; vzdálenost je prostřední z těch zásahů. Na mapě je to čárkovaná čára přes zásahy. | Tvůj obrázek u dvojky: cesta vlevo, oplocenka za kontrolou, cesta vpravo. Jedna linie na třech paprscích to nepopíše. |
| Rovně se přeskočí cesta nebo vodoteč, která vede podél paprsku (odchylka pod 30°). | To je pěšina, po které se přibíhá a která pokračuje za kontrolu: nekříží se, takže nezastaví. |
| Směr přeběhnutí je směr posledních 40 m nejlepšího postupu, ne stometrová tětiva jako u náběhového bodu. | Kdo kontrolu mine, běží dál tak, jak k ní dobíhal. U dvojky Petřvaldu se postup 50 m před kontrolou láme a stometrový směr mířil o 30° vedle. |
| Dvě věci do 5 m za sebou jsou jedna a pojmenuje se ta dřívější v pořadí oplocenka, vodní plocha, budova, okraj zástavby, cesta, vodoteč, paseka, okraj otevřené plochy. | Louka za cestou začíná cestou (jako dřív); plot s cestou podél je plot. |
| Nejbližší zásah se bere od 15 m. | Co leží blíž, je objekt kontroly sám. Deset metrů dávalo „vodní plocha 10 m“ u kontroly na břehu. |
| Při vybraném úseku jsou na mapě jen jeho čáry (stopa, nejlepší postup, možnosti, plán, stání, místo chyby, záchytné body jeho kontroly). Čáry ostatních se z mapy odeberou, ne zprůhlední. Zpět čipem „Celá trať“ nebo klávesou Esc. | Tvoje zadání. Neviditelná stopa by dál chytala kliknutí. Kolečka kontrol a zakázané čáry zůstávají, aby bylo vidět, kde úsek na trati leží. |
| Náběhový bod se neměnil. | U 2–3 sis spletl kontrolu. |

### Kontrola tras očima (noc 9. → 10. 10., větev `kontrola-tras`)

| Rozhodnutí | Proč |
|---|---|
| Všechno pouštím přes `docker compose -p obdev -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps -T web …`, ne přes `docker compose run --rm web …` ze zadání. | Výchozí příkaz pouští obraz s kódem z doby sestavení (testy by zkoušely starý kód) a připojuje svazek `ob_tracker_ob_data`, na který nemám sahat. |
| Start tratě je střed startovního trojúhelníku nalezeného podle tvaru, ne nejhustší fialový shluk u první polohy záznamu. Zlaté `course.json` (jen `start`) a řádek S–1 v `legs.csv` se tím mění u všech čtyř závodů. | Na Pohoře byl „start“ v číslici 16 vytištěné přes trojúhelník (44 m vedle), na Petřvaldu na čárce startu času (93 m vedle). Zadání chtělo start i bez první polohy GPS; se stejným pravidlem vyšlo najevo, že dosavadní start byl špatně. |
| Kde čas začíná aspoň 60 m před trojúhelníkem (značený úsek), začíná nejlepší postup prvního úseku tam, kde stopa; bez oficiálních časů jen do 150 m. | Čas úseku S–1 ten kus obsahuje. Bez oficiálních časů začíná záznam často cestou na start, proto strop. |
| Velikost koleček se čte z mapy: aspoň tři stejně velká uzavřená kolečka určí poloměr; původní rozsah 30 až 45 m se zkusí, když to nevyjde. | Sprintová mapa 1:4 000 má kolečka 12 m. Čtyři původní mapy mají 35 m a čtou se beze změny. |
| Kolečko, které má uvnitř víc než čtvrtinu fialové, není kontrola. | Na mapě Žebříčku B-Morava se pět „koleček“ našlo ve šrafování; skutečná kolečka mají uvnitř nejvýš 15 %, šrafy od 33 %. |
| Neúplný záznam s oficiálními časy se použije, když ukazuje aspoň polovinu kontrol; úseky mimo něj mají oficiální čas a značku „nedostatek dat“. Když jich chybí víc než polovina, nebo je stopa od kontrol v mediánu dál než 30 m, analýza skončí větou „Záznam z hodinek neprochází kontrolami této tratě…“. | Zadání nechávalo volbu mezi označením úseků a čistou chybou; použil jsem obojí podle toho, kolik závodu záznam ukazuje. 30 m: běh po trati je do 10 m od většiny kontrol, cizí běh přes stejnou mapu 59 m (3. Zkouška sirén). |
| Aktivita bez GPS se s závodem nespáruje vůbec (dřív jistota „nízká“). | Nedá se analyzovat; závod má radši zůstat „chybí aktivita“ s poznámkou, proč. |
| Přednost záznamu, který pokrývá čas závodu, jsem do párování nepřidal. | Chyba s NaN nebyla v párování: běh byl správný, jen spuštěný 8 minut po startu. |
| Chyba vstupu je řádek `OB-ERROR <kód>: …` a návratový kód 2; české věty jsou ve `webapp/texts.py`. | Skripty zůstávají anglické a bez webu; web nepáruje text výjimek. |
| Řada teček není cesta: černá značka do 4 m napříč (3 px při 1,33 m na pixel) se z cest vyřadí. | Tečkovaná hranice porostu a tečky polí se četly jako cesta a postupy po nich „běžely“. Čárka nejkratší pěšiny má 10 m. |
| Plot, který nic neuzavírá: aspoň tři čárky v řadě na téže straně souvislé čáry. Dvě nestačí. | Dvě krátké odbočky má i cesta; falešný plot by postupy posílal oklikou a mazal skutečné cesty. Cena: plot se třemi čárkami, z nichž jedna splývá s jinou kresbou, se nepozná (Petřvald S–1). |
| Plot je „těžko překonatelný“ (90 s), i neprůchodný 518; zakázaný není žádný. | Dvojitou čárku od jednoduché na mapě 1,33 m na pixel nerozeznám, a zákaz by bez vypínače škodil víc než cena. |
| Plot jako maska je na mřížce tenký (dotčené buňky a jedna vedle), ne 4 buňky jako čáry z OSM. | Širší pás by zdražil cestu vedoucí podél plotu. Dvě buňky stačí, aby žádný tah mřížky plot nepřeskočil. |
| Překážky mapy čte jedno místo, `mapdata.obstacles`; rozpoznávání je v `oroute/relocate.py` vedle `enclosures()`. | Zadání: postupy, záchytné body i zarážka mají číst totéž. Plán ho volá jen pro výřez kolem čáry (sekundy místo minuty na velké mapě). |
| Bažina se počítá z modré bez vodních ploch. | Kolem každého rybníka a široké vody byl pás bažiny široký jako okno filtru. Šrafy bažiny jsou tenké čáry a zůstávají. |
| Směr zarážky je posledních 40 m vlastní stopy, když stopa končí do 30 m od kontroly a úsek nemá bloudění; jinak nejlepší postup. | Tvoje poznámka u dvojky Petřvaldu. Při bloudění je poslední kus stopy náhodný směr. |
| Okraj paseky nebo pole, u kterého kontrola stojí (do 15 m), není zarážkou do 45 m; vzdálenější okraj téže plochy ano. | „Paseka napříč 15–31 m“ byla paseka kontroly; ale les 100 m za kontrolou na louce zarážka je. |
| Srázy a skály (201, 202) se nečtou. | Na čtyřech mapách na trasách nejsou; na mapě, kde jsou (Grand prix Silesia E3), mají zoubky dva až tři pixely a pravidlo by bralo i okraje silnic. |
| Sprintové mapy (ISSprOM) se čtou pravidly pro ISOM. | Analýza na nich doběhne; čtení terénu (průchodné a neprůchodné zdi, šedé budovy, dlažba) na ně laděné není a neladil jsem ho. |

### Kontrola tras, druhá noc (10. → 11. 10., větev `kontrola-tras-2`)

| Rozhodnutí | Proč |
|---|---|
| Větev `kontrola-tras-2` je z `kontrola-tras`, ne z `main`. | `kontrola-tras` v `main` na začátku noci nebyla (`origin/main` = `40313fd`). |
| Výchozí stav (kolo 0) jsem spočítal znovu pro všech deset závodů, staré výstupy z minulé noci jsem nepoužil. | Byly z různých verzí kódu (tři extra závody jen z kola 1), seznam podezřelých by míchal různá čtení mapy. |
| Seznam podezřelých (`tools/podezrele.py`) nepočítá úsek bez dat, se stáním nebo blouděním (`mistake`, značky `stop`, `zone`, `entries`, `ratio`, bloudění u kontroly), bez nalezeného postupu a úsek, jehož stopa je při ražení dál než 40 m od kontroly (start se do toho nepočítá: záznam často začíná před trojúhelníkem). Značka `slow` sama nevyřazuje. | Na takovém úseku poměr času k modelu nic neříká. Poslední pravidlo přibylo po prohlídce: Grand prix Silesia E2 má v jednom obrázku dvě mapy a prvních 13 kontrol leží 30 až 150 m od stopy. |
| Skupina B (model přeceňuje moji stopu o víc než 15 %) má stejný práh 10 s jako skupina A. | Bez něj vyskakovaly úseky po 20 s. V zadání u skupiny B práh není. |
| Závod s méně než třemi počítanými úseky se neposuzuje. Test má vedle tří úseků ze zadání pár obyčejných. | Ze tří úseků, z nichž dva vypadnou, medián závodu spočítat nejde. |
| Různé osobní modely v jednom seznamu jsou chyba (`OB-ERROR mixed_models`), ne varování. | Zadání: nemíchat dva modely. Větev s Riegelem se během noci nesloučila, model byl celou dobu jeden (`7b503c49`). |
| Olivová plocha: „uvnitř“ je černá, která má olivovou barvu obrázku po obou stranách do 4 px (5 m), ne černá do pár metrů od olivové. Obrys celé zástavby dál řeší `mapdata.obstacles`. | Rozšíření olivové o pár metrů (jak navrhovalo zadání) by bralo i cestu vedoucí těsně podél zástavby a dělalo z ní zakázaný prostor. Pravidlo „olivová z obou stran“ mimo zástavbu nezmění nic: na čtyřech mapách je do 8 m od olivové 100 % změněných pixelů. |
| Olivová se pro tohle pravidlo bere z barvy obrázku, ne z přečtených tříd. | Třídy mají pod každou čarou barvu nejbližší plochy, takže černá čára podél zástavby „má olivovou po obou stranách“, i když na obrázku je z jedné strany les. První verze tak změnila 800 pixelů mimo zástavbu. |
| Které čárky tvoří dost dlouhou cestu, se posuzuje před vyřazením čar zástavby, ne po něm. | Jinak cesta, která končí u zástavby, přišla o kus a mohla vypadnout celá; na Pohoře a Azymutu E5 se tak měnily cesty mimo zástavbu. |
| Okraj obrázku: mapa se bere jako pokračující za okraj tam, kde je pás 32 px podél okraje aspoň z 30 % v barvách mapy. Jinde zůstává pás 85 m podél okraje zakázaný jako dřív. | Uzávěr, kterým se hledá obrys mapy, bere prostor za obrázkem jako prázdný. U listu s bílým okrajem je to správně (rámeček a tisk nesmějí bílou uzavřít), u mapy až k okraji obrázku ne: cíl sprintu MSK a kontrola 24 Slezské zimní ligy ležely v zákazu. Petřvald a Pohora jsou bajtově stejné; u Azymutu E4 a E5 se u okraje obrázku čte mapa, kde byl zákaz (na obrázku zkontrolováno, je to mapa). |
| Kontrola v uzavřené kapse průchodné plochy do 5000 m² se bere z nejbližšího místa mimo kapsu. Dva velké kusy bez přechodu zůstávají bez postupu a úsek nese `no_route`. | Když hledání cestu nenašlo, byl „nejlepší postup“ beze slova přímka přes domy (Slezská zimní liga 4–5). Železnice bez přejezdu má dál znamenat „postup není“, ne postup k trati; proto práh na velikost. 5000 m² je odhad (dvůr, ostrov). |
| Náběhový bod: aspoň 25 m od předchozí kontroly, nejvýš 70 % přímé délky úseku před svou kontrolou, úsek pod 80 m žádný. | Tvoje zadání. Pravidlo 25 m váže jen u úseků 80 až 83 m (jinak je přísnější těch 70 %). |
| Záchytný bod za překážkou: překážka je oplocenka, zakázaná čára nebo plocha, voda a zakázaný prostor; budova ne. Spojnice je „přes překážku“, když v ní leží aspoň 4 m. Bod se neukáže při obchůzce nad 1,3× přímé vzdálenosti; pod 1,05× je to přímka (jen lízne roh). | Tvoje zadání (1,3×). Budovu jsi nejmenoval a dům se obejde bez přemýšlení. 4 m a 1,05× jsou proto, aby „obchůzkou 80 m“ nestálo u bodu 80 m daleko. |
| Délka obchůzky je nejkratší průchodná cesta v metrech, ne nejrychlejší postup modelu. | Nejrychlejší postup si rád zajde po cestě; otázka tady je, jak daleko se musí obejít překážka. |
| Oplocenka a rybník jako záchytný bod leží tam, kde je přímka od kontroly potká, ne ve svém středu, a píše se „oplocenka, nejblíž 38 m“. | Střed oplocenky je „za plotem“ sám sobě; azimut na střed protáhlé oplocenky mířil jinam než na její nejbližší místo (Petřvald 13: 74 m na střed, 38 m k plotu). |
| Vzorek vlastní stopy na neprůchodné ploše bere třídu nejbližší průchodné plochy do 8 m; dál zůstává chůze. Jen pro ocenění stopy. | Stopa po ulici mezi zahradami zabíhá chybou GPS do olivové a oceňovala se tam chůzí. 8 m je odhad chyby GPS v zástavbě. Nejlepší postup a plán se oceňují přesně tam, kudy vedou. |
| Širší oprava „stopa pár metrů vedle cesty se ocení jako cesta“ není. | Pět úseků skupiny B (Azymut E4 2–3, 11–12, 18–19, Pohora 8–9) má tuhle příčinu, ale oprava by zrychlila ocenění každé stopy v síti cest a změnila všechny zlaté soubory; je to změna modelu, ne čtení mapy. Otázka v `co-zbyva.md`. |
| Srázy a skály (část 3) se dál nečtou. Zkusil jsem jediné, co je na mapě 1,33 m na pixel vidět (černá širší než čára silnice, která není budova), a nepoužil to. | Čísla: černá širší než 6,6 m dává na Azymutu E4 138 kusů, E5 68, Pohoře 78, Petřvaldu 352 (silnice) a na Bludišti 202; nad 9,2 m pořád 13, 3, 11 a 178 proti 25 na Bludišti, a devět největších z těch 25 (jeden přehledový list; ostatní jsem neviděl) je sedm domů a dvě křižovatky, sráz žádný. Zoubky srázu mají dva pixely. Podmínka „na čtyřech původních mapách nula“ nejde splnit. |
| Hustá kamenitá půda (část 4) a ploty se dvěma čárkami (část 5): nedělal jsem. | Seznam podezřelých jim nepřipsal jediný úsek ze 34 (sráz nebo skála: dva úseky, okraj obrázku tři, postup přímkou jeden, posun stopy pět, doběhy do cíle šest). Čas šel na to, co seznam ukázal. Tečky kamenité půdy na sprintu E2 se po loňské opravě teček jako cesta nečtou (viděno na 13 úsecích). |
| Stejný pás bere i mapu, která končí do 85 m od okraje obrázku za bílým okrajem. V pásu se uzávěr dělá znovu bez ztráty u okraje a platí jen mezi nejzazšími barvami mapy v každém řádku a sloupci. | Druhá polovina téže chyby, nalezená v kole 2 na Slezské zimní lize (kontrola 24). Týká se i čtyř původních map: roh Pohory (asi 40 m mapy), rohy obou Azymutů a kus Petřvaldu byly zakázaný prostor. Bílý okraj s rámečkem a tiskem dál od mapy zůstává zakázaný (zkontrolováno na čtyřech výřezech). **Cena:** bílý les u kraje mapy se od bílého okraje listu barvou nepozná, takže v tom pásu se bílá do asi 40 m za poslední barvou mapy čte jako les. U šikmého okraje mapy tak vznikne klín „lesa“ mimo mapu (viděno na Azymutu E5 a na sprintu MSK). Žádný postup deseti závodů jím nevede; dřív byla chyba opačná a větší (mapa u okraje zakázaná). |
| Severní čára, která má vodu z obou stran, je voda. | Modré čáry severu se z modré vyřazují; přes rybník tak zůstal pruh „lesa“, v mřížce cesta přes vodu (viděno na Grand prix Silesia E4 u kontroly 11). Žádný postup deseti závodů jím nevedl; nejdřív jsem si myslel, že postup 10–11 ano, ale ten vede po hrázi mezi dvěma rybníky a opravou se nezměnil. Je to oprava stávajícího čtení vody, ne nová značka; čtyři původní mapy jsou bajtově stejné. |
| Oplocenka, ve které stojí kontrola tratě, je průchozí (pro postupy, plán i záchytné body) a mezi oplocenkami se neuvádí. | Kontrolu nikdo nepostaví tam, kam se nesmí. Na sprintové mapě se dvory mezi domy čtou jako oplocenky (mezery do 5 m v čáře se zavírají) a postup pak vedl jen k „plotu“ (Slezská zimní liga 5–6, 14–15). Je to povolení, ne nové rozpoznávání; na čtyřech původních závodech žádná kontrola v oplocence nestojí. |
| Šedé budovy sprintových map (ISSprOM 521, barva 128/129/132) jsem číst nezačal, i když kvůli nim postup na všech třech sprintech místy vede skrz dům. | Našel jsem to při prohlídce kola 2 a oprava by byla nové rozpoznávání v posledním kole, které se podle zadání dělat nemá. Je první v `co-zbyva.md`. |
| Kola: 0 výchozí, 1 a 2 s opravami, 3 poslední (všech deset závodů konečným kódem). Čtvrté nebylo. | Po kole 3 nezbylo nic, co by šlo opravit bez nového rozpoznávání. Kolo 3 jsem dvakrát zastavil a pustil znovu, protože jsem při prohlídce kola 2 našel ještě dvě chyby (oplocenka s kontrolou, okraj za bílým okrajem). |

### Fotka papírové mapy (noc 17. → 18. 10., větev `foto-mapy`)

| Rozhodnutí | Proč |
|---|---|
| Větev `foto-mapy` je z `kontrola-tras-2`. | `pruchod-appkou` neexistuje (ani na `origin`), `kontrola-tras-2` v `main` není. |
| Průchod webem přes `tools/shot.mjs` (Chrome přes DevTools), rozšířený o nahrání souboru, klepnutí myší a čekání na úlohu; ne Playwright. | Playwright v repozitáři ani v kontejneru není a nová knihovna se přidávat nemá. `tools/pruchod.py` neexistuje. |
| Umělé fotky dělá `tools/fotka.py` jako přesná zobrazení (prohnutí, kamera, posun), pravda se neodhaduje. Kontroly „z GPS“: u Pohory a Petřvaldu skutečná stopa v časech ORIS, u ostatních map pravé polohy + šum 8 m. | U map bez běhu jinou pravdu o ražení nemám; 8 m je střed udávaných 5 až 15 m. |
| Generátor dělá fotku jako mobil: optická osa ve středu snímku, ohnisko asi 0,7 úhlopříčky, zapsané v EXIF (`FocalLengthIn35mmFilm`). Uříznutý okraj je posun mapy z rámu, ne ořez obrázku. Výchozí měření jsem kvůli tomu pustil znovu se stejným generátorem na kódu před větví. | První verze generátoru měla optickou osu mimo střed a ohnisko se měnilo s náklonem; skutečná fotka takhle nevypadá a poměr stran listu by se z ní počítal špatně. |
| Fotka se rozpozná tak, že přesná fialová Livelox nespáruje skoro všechny kontroly (pod 90 %), nebo že na fotce je list na stole. Čistý obrázek z Livelox jde starou cestou beze změny. | Pomalý `test_real_map_lands_where_its_kmz_says` dává po každém kole stejná čísla (Pohora rohy 2,1 až 15,3 m, Petřvald 4,0 až 19,2 m). |
| Světlo: každý kanál se dělí barvou papíru v okolí (nejsvětlejší barva v okně 1/12 kratší strany, rozmazaná). | Vyvážení bílé a vyrovnání stínu jedním krokem; okno je větší než kolečko (asi 1/30 mapy), takže v něm vždy je kus papíru. |
| Perspektiva primárně z okraje listu: čtyřúhelník listu na stole, z něj obdélník se skutečným poměrem stran (Zhang a He, ohnisko z EXIF, jinak 0,65 úhlopříčky), kolečka se hledají na narovnaném listu a za ním je jen dnešní plochý model (podobnost se zvlášť škálovanými osami). | Homografie jen z kontrol extrapoluje: kontroly jsou uprostřed mapy a GPS má 5 až 15 m, rohy pak ujížděly o stovky metrů. Okraj listu je přes celou fotku. Afinní zobrazení za listem přenášelo zkosení do rohů (rovná fotka E5: rohy 26 m místo 9 m). |
| Homografie z kontrol (když okraj listu vidět není) jen při aspoň 5 kontrolách, o čtvrtinu menší RMS než plochý model na stejných kontrolách, rozumná (bez zrcadla, zkrácení nejvýš 0,7) a když se rohy obrázku bez kterékoli jedné kontroly nepohnou o víc než 50 m (nebo dvojnásobek plochého modelu). | Zadání (čtvrtina, 40°). Poslední podmínka přibyla po oříznuté šikmé fotce, kde homografie dala rohy 870 m vedle. |
| Kolečka sprintových map: RANSAC zkouší průměr kolečka 75, 50 a 30 m, další jen když 75 m nespáruje skoro všechno. | Tři sprintové mapy z `data-extra` se neusadily ani jako čistý obrázek; měřítko z velikosti kolečka bylo třikrát mimo. Týká se i obrázků z Livelox, nejen fotek. |
| Prohnutí: kvadratický člen v jedné ose listu, jen s aspoň 8 kontrolami a jen když RMS klesne aspoň o 10 %. Narovnává se sítí buněk (`Image.MESH`). | Zadání. Pomáhá jen částečně (níže a v `docs/foto-mapy.md`); lepší by bylo zakřivení měřit na okraji listu, to je v `co-zbyva.md`. |
| Trať (start, kontroly, cíl) u fotky nebere `analyze.py` z fialové, ale úloha ji zapíše z usazení do `course_class_N.kmz.course.json` a analýza dostane `--course`. Kontrola = spárované kolečko; bez kolečka místo ražení; start = trojúhelník nejblíž místu, kde byl běžec v čase startu (do 200 m), cíl = místo v čase cíle. | `analyze.py` čte přesnou Livelox fialovou, na fotce ji nenajde. Které kolečko je která kontrola, víme z usazení přesněji než z čar tratě. Ověřeno proti KMZ (níže). |
| Šrafy zakázaných prostorů se z fotky nečtou. | Šrafa se na fotce plete se stínem a kresbou; zakázanou čáru jde nakreslit ručně. |
| Záchytné a náběhové body se z fotky neskrývají, jen se u mapy napíše, že je brát s rezervou. | Terén pro ně je z mapy bez tratě (KMZ), z fotky je jen poloha kontroly s chybou asi ±15 m; schovat je by vzalo víc, než chyba kazí. |
| Ruční usazení: 4 a 5 bodů afinní zobrazení, od 6 homografie (jen o čtvrtinu lepší), s okrajem listu jako automatika. Odchylka bodu se měří s vynechaným bodem; špatný bod je ten, bez kterého ostatní sedí nejlíp (od 5 bodů), u 4 bodů jen „body k sobě nesedí“. | Homografie ze 4 bodů projde jimi přesně a odchylka 0 by nic neřekla. Při jednom špatném bodu se nafouknou odchylky všech, proto se viník hledá zvlášť. |
| Náhled ručního usazení kreslí stopu do původní fotky, ne do narovnané. | Ukazuje totéž (sedí, nebo nesedí), a nemusí se po každém kliknutí přepočítávat obrázek. Narovnaná fotka je po uložení na stránce závodu. |
| Ruční usazení přepíše automatické vždy; automatické (i další fotka) přepíše předchozí, ruční i automatické, jen s menší odchylkou. Fotka KMZ nikdy nepřepíše, ani ručně; když KMZ už je, fotka se ani neuloží. | Ruční usazení je oprava, kterou běžec chce; fotka od jiného běžce ji nemá zahodit, pokud nesedí líp. |
| Fotka se po nahrání ukládá (`photos/entry_N.jpg`, zmenšená, s ohniskem v EXIF), aby šla usadit ručně; smaže se, až KMZ nahradí mapu kategorie. | Bez ní ruční usazení nejde. |
| Chyba úlohy „pro uživatele“ (`jobs.Refused`) se ukládá bez výpisu; ostatní chyby dál s výpisem pod „Podrobnosti“. | Zadání: česká věta, žádný výpis. Neočekávaná chyba výpis potřebuje k opravě. |
| Dvě mapy na jedné fotce se odmítnou, jen když se usadí méně než 90 % kontrol. | List s popisy kontrol vedle mapy je taky „druhý list“ a fotka s ním je v pořádku. |
| Odhad chyby na okraji: RMS × (vzdálenost nejvzdálenějšího rohu od středu kontrol / dosah kontrol), aspoň RMS. Štítek „přesnost asi ±N m“ bere větší z RMS a tohoto odhadu, nejméně 15 m. | Jednoduché a na straně opatrnosti; porovnání s pravdou je v `docs/foto-mapy.md`. |

### Dva snímky z Livelox (noc 18. → 19. 10., větev `snimky-livelox`)

| Rozhodnutí | Proč |
|---|---|
| Větev `snimky-livelox` je z `main`. | PR #2 (`claude/project-thread-s0dshb`) v `main` je (`ae21cbf`). |
| **Nahrazuje rozhodnutí „Mapu bez tratě z obrázku nedělám“** (část Umístění obrázku mapy) pro snímek z Livelox. Sken a fotka zůstávají jen mapou s tratí. | Snímek z Livelox má paletu Livelox (stejné barvy jako KMZ), barvy skenu ne. Na zvětšení 1 vychází terén ze snímku na 99 % pixelů stejně jako z KMZ. |
| Výpočet je v `oroute/pair.py`, web jen volá `place_pair` (úloha `georef_map` s `payload.screens`, `webapp/services/screens.py`). Měřicí nástroj `tools/snimek.py` volá tutéž funkci. | Měří se přesně kód appky. Nová úloha by se jinak lišila od fotky jen v detailech; stránka úloh a „Zkusit znovu“ ji berou stejně. |
| Snímek s tratí se usazuje jen podobností (`georef.place(screen=True)`): žádný list na stole, žádná homografie. | Snímek je rovný. Perspektiva z kontrol by jen sledovala chybu GPS (5 až 15 m). |
| Usazuje se na kopii 4000 px, mapy se vyřezávají z plného snímku. | 10 000 × 8 000 px (DPR 2) by `open_image` zmenšil na 4000 px a mapa by přišla o ostrost. |
| Co není mapa: barvy mapy (hnědá, žlutá, zelená, modrá, olivová) uzavřené, největší kus, konvexní obal; pruh přes okraj mapy (posuvník, lišta) se usekne podél rovné hrany přes celou šířku. Všechno mimo se přebarví na bílou. | Terén bere bílou za kresbou mapy jako „mimo mapu“ (stejně jako bílý okraj KMZ, kontrola-tras-2), takže `terrain.py` se nemění a zlaté soubory zůstávají. První verze ořezávala okraje podle palety Livelox a na Petřvaldu (export v jemném rozlišení, jiné barvy) uřízla 15 % mapy. |
| „Oblast nalezena jistě“ = obal zabírá aspoň šestinu snímku a mimo něj je nejvýš 1 % barev mapy. Jinak se snímek použije a úloha řekne, ať se oblast zkontroluje a případně ořízne ručně. | Lepší použitelná mapa s varováním než odmítnutí. Ruční ořez je na `/races/N/fotka?snimek=1` (obdélník s přetahovanými rohy). |
| Kontrola dvojice: fázová korelace (numpy FFT) v mřížce 4 × 4 dlaždic; stejný posun ve všech = posun (vyrovná se, s přesností pod pixel), posuny rostoucí s polohou = přiblížení nebo otočení, žádná shoda = jiný závod. Po vyrovnání se nesmí lišit víc než 8 % mapy mimo trať (okolí 3 × 3 jako tolerance). | Rozdělení na dlaždice odliší posun od změny měřítka bez hledání měřítka. Lišta a tlačítka Livelox se s mapou nehýbou; při posunu se proto z porovnání vynechá, co zůstalo na místě. |
| Posun mezi snímky se vyrovná, i když je větší než 20 px (do 10 % snímku). | U Tobiase byl posun 249 px a dvojice byla jinak v pořádku. |
| Trať na snímku bez tratě: **zapnutá** (stejně pixelů přesné fialové Livelox jako na snímku s tratí a kolečka) se odmítne; **průhledná** se odbarví a úloha to napíše. | Na šesti ze sedmi skutečných dvojic Tobiase zůstala trať na snímku bez tratě průhledná na 12 až 15 %. Průhlednost se změří na pixelech pod tratí, jejichž barva leží na přímce bílá–fialová; kde trať pokrývá pixel jen zčásti (okraj čáry), se pokrytí spočte ze snímku s tratí. |
| Postupy běžců: jen sytě červené a tmavě modré tenké čáry (po odebrání 2 px z okraje zbude nejvýš čtvrtina), dohromady delší než 1,5× delší strana mapy. Oranžové a zelené postupy se nepoznají. | Barvy mimo paletu Livelox nestačily: sprintové mapy (ISSprOM) a loga sponzorů v listu mapy se braly jako postupy. Červená a tmavě modrá v mapách ISOM ani ISSprOM nejsou. |
| Mapa bez tratě se ukládá jako KMZ s PNG. | JPEG by rozmazal přesné barvy, podle kterých se čte terén. |
| Rozlišení uložené mapy: jak ostrá je mapa sama, ne snímek. Přiblížení prohlížeče se odhadne z šířky nejostřejších hran (1,05 + 0,95 × přiblížení px), mapa se převzorkuje na 0,85 odhadu, nejvýš na 1,33 m/px, nejvýš 20 Mpx. | Zvětšený snímek nemá jemnější kresbu, jen víc pixelů, a `bestroute.py` by na něm hledal v jemnější mřížce než na KMZ téže mapy (postupy pak vychází soustavně o 2 až 9 s rychlejší). Převzorkování na původní rozlišení terén nezlepšilo ani nezhoršilo. Odhad: 1,0 / 1,5 / 2,0 / 3,1 při skutečném 1 / 1,5 / 2 / 3; u oddáleného snímku (0,75) vychází 1,4, proto strop. |
| Vyhlazení prohlížečem se v terénu neopravuje (`terrain.py` beze změny). | Zkoušel jsem vracet smíšené barvy okrajů k převažující barvě palety: na zvětšení 2 až 3 ubralo změněných pixelů z 7,5 na 5,2 %, na zvětšení 1 přidalo z 1,1 na 4,7 % a nejlepší postupy se tím nezlepšily. |
| Málo přiblížený snímek: nad 2 m/px varování, nad 3 m/px se mapa bez tratě neuloží (snímek s tratí ano). | Zadání. |
| Přesnost na štítku: větší z 10 m, RMS a odhadu chyby na okraji (z rohů vyřezané mapy, ne celého snímku). | Na umělé sadě je štítek aspoň tak velký jako skutečná chyba rohů. Rohy celého snímku s lištou a seznamem běžců dávaly ±54 m. |
| Mapa s tratí ze snímku má zdroj `screen`; trať čte `analyze.py` z fialové (bez `course.json`), šrafy se čtou. | Fialová snímku je fialová Livelox. Ověřeno: Pohora, zvětšení 2, všech 16 kontrol. |
| Snímek s tratí nahradí mapu z obrázku, fotky i ručně usazené fotky; fotka (i ručně usazená) nahradí snímek jen s menší odchylkou; KMZ nahradí vždy. Snímek bez tratě se nepoužije, když závod má KMZ bez tratě; KMZ bez tratě nahradí snímek a uložené snímky závodu smaže. | U Tobiase přepsalo ruční usazení staré fotky (18 m) snímek (8 m). |
| Oba snímky se ukládají v plné velikosti (`screens/class_C_user_U_trat.png`, `_bez.png`) pro kategorii a běžce. | Snímek bez tratě může přijít později a ořez ručně potřebuje oba. Cena: u Tobiase 25 až 44 MB na snímek. |

### Malé opravy, „proč právě pro tebe“, sprinty, stopa vedle cesty, kategorie (noc 19. → 20. 10., větev `pro-tebe-a-sprint`)

| Rozhodnutí | Proč |
|---|---|
| Klíč režimu světlý/tmavý je `ob-rezim`. Dokud ho prohlížeč nemá, platí hodnota `skob-rezim` klubového webu, kterou rozbor postupů nechá být (nemaže ji). | Zadání chtělo neutrální klíč se zachováním staré hodnoty. `skob-rezim` patří klubovému webu na stejné doméně, kdyby ho rozbor smazal, klubový web by volbu ztratil. |
| Logo klubu (`OB_CLUB_LOGO`) je název souboru ve `webapp/static`, ne cesta kamkoli. | Statické soubory se servírují jen odtud (a s verzí v adrese); jiný klub logo do složky přidá. |
| CSRF (`webapp/security.py`) se registruje na aplikaci (`app.before_request`), ne na blueprint. Kontrola teď běží před načtením uživatele, ne po něm. | Výsledek je stejný: neplatný formulář končí 400 dřív, než by na uživateli záleželo. Testy prošly beze změny. |
| **Průměrný běžec** je učebnicový model `SpeedModel()`: činitele terénu ISOM (`PRIOR_FACTORS`), učebnicový sklon (up_k 9, down_gain 2,5, steep_down 3) a **rychlost po rovné cestě daného běžce** (`v_flat`). Rozhodl Tobias (19. 10.). | `slope_prior.json`, který navrhovalo zadání, je Tobiasův vlastní Garmin (164 běhů, up_k 3,4) a dostává ho jako výchozí sklon každý běžec bez exportu: Tobiasův sklon by se pak rovnal „průměrnému“ a věta o kopci by nikdy nevyšla. Stejná rychlost po rovině: porovnává se tvar modelu, ne kondice (stejně jako `personal.check` a vyrovnání rychlosti v Livelox). Klubový průměr (`club_prior`) je vypnutý, dokud nejsou data tří běžců. |
| Učebnicový sklon je přísný: při 10 % do kopce je 1,9× pomalejší než po rovině, Tobiasův 1,34×. Věta „do kopce běžíš o 42 % rychleji než průměr“ je tedy proti učebnicovému pravidlu (blízko Naismithovi pro chůzi), ne proti průměrnému orientačnímu běžci. | Lepší „průměr“ v repozitáři není. Až budou v klubu data aspoň tří běžců s vlastním exportem, dá se průměr spočítat z nich (otázka v `co-zbyva.md`). |
| Bez vlastního exportu z Garminu (web bez `--slope`) dostane průměrný běžec sklon běžce: porovnávají se jen terény (`bestroute.py --generic terrain`). Skripty (`personal_model.json` je Tobiasův) porovnávají i sklon (`--generic` = podle `slope_own` v poznámkách modelu, bez ní ano). | Jinak by appka tvrdila „do kopce jsi rychlejší než průměr“ podle Tobiasových dat i u běžce, který žádná data o kopcích nedal. |
| Postup průměrného běžce se hledá na té samé mřížce: po všech osobních postupech se graf přestaví s jeho modelem (`Grid.with_model`, starý graf se zahodí předem), jedno hledání na úsek, žádné alternativy. Petřvald: 151 s → 189 s, paměť 2,96 GB → 2,97 GB. | Zadání: hlídat dobu a paměť. Druhá mřížka vedle první by paměť zdvojila. |
| Postupy se **liší**, když kterýkoli z nich vede dál než 30 m od druhého na víc než 20 % své délky (`generic.APART_M`, `APART_SHARE`). Když se liší, ale tobě by postup průměrného běžce trval nejvýš o 3 s déle, věta řekne „skoro stejně“, ne „pro tebe je rychlejší“. | Práh ze zadání. Mřížka a ocenění čáry se o pár sekund liší, rozdíl 1–2 s by nic neříkal. |
| Čas postupu průměrného běžce ve větě i v tabulce je **tvým** modelem („tobě by ten postup trval 2:41“), vedle tvého nejlepšího (2:29, stejné číslo jako jinde na stránce). | Jinak by věta srovnávala dva různé modely a čísla by neseděla s tabulkou postupů. |
| Důvod: každá část modelu (stoupání, klesání, každý terén, kterého má některý z postupů aspoň 10 m a jehož činitel se liší o 3 % a víc) se vymění z průměrného za tvůj a naopak; vyhraje ta, která rozdíl časů obou postupů posune nejvíc k tvému. Procento: u kopce poměr násobků sklonu při typickém sklonu stoupání (klesání) postupu, který stoupá (klesá) víc; u terénu poměr činitelů. | Jednoduché, vysvětlitelné a čísla jdou dohledat na stránce modelu. Výměna oběma směry zmírní to, že se části navzájem ovlivňují. |
| „Vlevo“ / „vpravo“ jen tehdy, když aspoň 75 % odsazené části obecného postupu leží na jedné straně tvého (při pohledu od kontroly ke kontrole). | Postup, který tvůj kříží, nemá jednu stranu. |
| Kategorie: synchronizace s ORIS ukládá všechny kategorie závodu (z `getEvent`, který se volá stejně); u starších závodů se kategorie načtou tlačítkem „Načíst kategorie závodu z ORIS“ (jedno `getEvent`). | Šetrné k ORIS: žádný dotaz navíc při synchronizaci, jeden na závod, když běžec kategorii mění. |
| Změna kategorie smaže rozbor a poznámky k úsekům dosavadní kategorie a pustí nový rozbor. Kategorie vybraná ručně (`entries.class_chosen`) se synchronizací s ORIS nepřepíše a za přihlášku do jiné kategorie téhož závodu nevznikne druhý závod. | Jiná kategorie má jinou trať: úseky ani poznámky k nim nesedí. Bez značky by další synchronizace závod v přihlášené kategorii založila znovu. |
| Mezičasy jiné kategorie se berou z uložených výsledků celé kategorie (`class_splits`, i se jménem a registračkou), ORIS se ptá jen na kategorii, která v DB ještě není. Když v ní běžec ve výsledcích není, oficiální čas zůstane prázdný a mezičasy jsou z GPS. | Jedny mezičasy na kategorii, jak chce zadání. |

### Zdi na sprintu, věty průměrného běžce, provoz pro klub (noc 20. → 21. 10., větev `zdi-sbehy-provoz`)

| Rozhodnutí | Proč |
|---|---|
| Kola noční kontroly pouští každý závod ve vlastním kontejneru, jeden po druhém (`tools/kola.sh`, `kontrola/noc4/kolo4.py`), a měří špičku paměti každého kroku spolu s posledním řádkem logu v tu chvíli. Dockeru paměť nepřidávám. | Odpověď na otázku 31. Jeden spadlý závod zastaví jen sám sebe; poslední řádek logu řekne, jestli šlo o mřížku, výškopis nebo obrázky. |
| Zeď se hledá jen na mapě se šedými budovami (stejné pravidlo jako u budov z 19. 10.). Lesní mapy a Grand prix Silesia E2 (sprint kreslený v paletě ISOM, bez šedých budov) se nemění. Žebříček B je mapa sídliště se šedými domy (6,9 % mapy), takže se podle pravidla čte jako sprint (od 19. 10. budovy, teď i zdi). | Zadání. Na lesní mapě je silná černá čára silnice. Žebříček B má domy, dvory a olivové plochy jako sprint; pravidlo jsem pro něj neměnil. |
| **Neprůchodná zeď** = souvislá černá čára aspoň 8 m dlouhá, která má na hřebeni aspoň 1,25 m. Patří k ní i neprůchodný plot (518) a zábradlí mostu. V třídách terénu je to budova, mřížka ji navíc dostane jako masku (`wall_mask`): neprůchodná je každá buňka, které se zeď dotkne, a tah úhlopříčně nebo koněm mezi dvěma buňkami zdi nebo přes buňku zdi je zakázaný. | Změřeno na MSK a Slezské zimní lize: zdi 1,30–1,55 m, zídky s tečkami a pěšiny 0,75–1,1 m, křížení dvou čárkovaných pěšin 1,22 m. Tloušťka se počítá z inkoustu čáry (rozmazání 0,5 m a šířka přes erf), ne z pixelů: na 0,4 m/px dělí zaokrouhlení na pixely čáru 1 m a 1,5 m špatně. Bez masky by zeď 1,5 m na mřížce s buňkou 1,06 m (SZL) nebo 2,7 m (záchytné body) zmizela nebo by ji tah koněm přeskočil. Zeď jsem nejdřív zesílil o buňku; to ale zavřelo branku 3,6 m na MSK 11–12 (postup 1:27 oklikou), proto zákaz tahů místo zesílení. |
| Kolem kontroly je zeď otevřená na 4 m (`mapdata.WALL_OPEN_M`). | Kontrola u rohu nebo konce zdi se razí z kterékoli strany; nejbližší průchozí buňka by jinak mohla ležet za zdí. Na deseti závodech jsem případ, kde by na tom záleželo, nenašel, je to pojistka. |
| **Průchodná zeď** = čára mezi 0,7 a 1,25 m, aspoň 8 m dlouhá, s aspoň dvěma tečkami (kulaté černé skvrny do 3 m) do 1 m od ní. Přelezení stojí 6 s (`routing.CLIMB_CROSS_S`) a není to cesta. Bez teček zůstane čára, jak byla. | Hrana silnice nebo dlažby je stejně tlustá jako zídka; tečky ji odliší (na SZL kolem záhonů). Zadání psalo „průchodná zeď (516)“; podle ISSprOM 2019 je zeď 513 a 516 je plot (tenký, s háčky): ten se čte jako dřív (`relocate.fences`, 90 s). 6 s je odhad (přelézt zídku po pás), ne měření. |
| Na zídce s tečkami neplatí cena plotu (90 s), i když ji `relocate.fences` vzal za plot. | Tečky zídky vypadají pro hledání háčků jako háčky plotu. |
| Zeď není budova pro záchytné body (`relocate.layers(walls=...)`). | Zeď kolem dvora má přes 300 m² a těžiště uprostřed dvora: hlásila by se „budova“ na místě, kde žádná není. |
| `bestroute.VERSION` 8, `relocate.VERSION` 7: starší rozbory se nabídnou přepočítat, i na lesních mapách, kde se nic nezmění. | Verze je jedna pro všechny mapy; jemnější rozlišení by stálo víc, než ušetří. |
| Věta u postupů, které se liší jen strmostí: najde se úsek postupu průměrného běžce s největším klesáním (stoupáním) na 60 m, po čem vede (cesta od poloviny délky, jinak převládající terén) a jestli je to údolí, hřbet nebo svah (výška 25 m po obou stranách vyšší / nižší aspoň o 1,5 m). Je-li ten úsek prudší než nejprudší úsek tvého postupu, věta řekne „seběhl“ („vyběhl prudce“), je-li mírnější, „klesal pozvolna“ („stoupal pozvolna“). Tvůj postup je „kratší“ / „delší“, když se délky liší aspoň o 5 %, jinak „s mírnějším“ / „s prudším klesáním“ (o 15 % a víc). | Zadání (příklad „seběhl by údolím po cestě vlevo“). 25 m a 1,5 m: menší údolí výškopis AWS po 30 m nezachytí, větší práh by vynechal údolí na ČÚZK. Na Grand prix Silesia E4 6–7 je to naopak, než čekala minulá noc: učebnicový běžec je z mírného kopce o čtvrtinu rychlejší, a tak bere delší postup s pozvolným klesáním; tobě klesání nepřidává, tvůj je kratší a klesá prudčeji. Délka to řekne srozumitelněji než sklon. Procento důvodu zůstává při typickém sklonu klesání (jako dosud). |
| Stejný popis dostanou i věty „skoro stejně“ (dřív „by běžel jinudy“). Les se jako důvod „obíhání“ neuvádí (les je všude kolem); místo „jinudy“ věta řekne „oklikou“ nebo „zkratkou“, když se délky liší aspoň o 5 %. | Řekne kudy i tam, kde rozdíl času nic neznamená. „By les obíhal“ by na lesní mapě nic neříkalo. |
| Na sprintové mapě: „otevřená plocha“, „hrubá otevřená plocha“ místo louky a „zpevněné plochy“ místo cest. Ostatní třídy (les, zelené, podrost, bažina) mají na sprintu stejná slova. Příznak `sprint` je v `best.json` u každého úseku a stránka modelu podle něj píše důvody. | Zadání. Cesta je na sprintu hlavně dlažba a průchody (`PATH` z 19. 10.). |
| `flask sync-oris-all` načítá synchronně v jednom procesu (ne jako úlohy workeru), účet po účtu s 0,4 s mezi dotazy, a přeskočí účet načtený v posledních 20 h. `getUser` jen u účtu bez ORIS ID. Opakované dotazy na mezičasy čerstvého závodu bez oficiálního času (do 30 dnů) zůstávají jako dosud. | Šetrné k ORIS a jednoduché pro cron (výpis do logu). Úlohy workeru by v seznamu úloh každého účtu přidaly řádek denně. Výsledky bývají v ORIS až pár dní po závodě: bez opakování by oficiální čas nikdy nepřišel. |
| Záloha = kopie databáze (`sqlite3` backup API, ne `.backup` z příkazové řádky: v obrazu `sqlite3` není) + seznam nenahraditelných souborů + jejich zrcadlo. Zrcadlo kopíruje jen nové a změněné a maže, co žádná ponechaná záloha neuvádí. Výchozí složka je `backups/` v instanci, služba `cron` zálohuje do `zalohy/` vedle compose. | Mapy mají 5–30 MB: denní tar všeho by byl desítky GB. Smazaný účet zmizí ze zrcadla nejpozději po `OB_BACKUP_KEEP` zálohách (výchozí 14 dní). |
| Denní úlohy umí obojí: cron na hostiteli (doporučeno) i služba `cron` v `docker-compose.yml`, vypnutá profilem. | Nevím, jestli tátův server cron má (otázka na tátu 1). |
| Nápověda „Jak na to“ je otevřená bez přihlášení, odkaz je v nabídce (obě nabídky stránky) a v prázdném seznamu závodů. Popis exportu z Livelox drží slova, která appka používá u nahrávání (Sdílet → Exportovat → Google Earth). | Kdo zakládá účet, má vědět, co bude potřebovat. Postup v cizích webech jsem neověřoval proti jejich současnému vzhledu (viz `co-zbyva.md`). |

### Snímky z Livelox v appce, přepočítat všechno, zastavení úloh, mezičasy, oprava stopy (noc 21. → 22. 10., větev `snimky-a-napoveda`)

| Rozhodnutí | Proč |
|---|---|
| Větev `snimky-livelox` je sloučená (merge, ne rebase) a `bestroute.VERSION` (8) ani `relocate.VERSION` (7) se nezvedají. | Snímky pravidla postupů nemění: `oroute/terrain.py` ani verze větev nemění a změny v `oroute/georef.py` jsou jen nové volby s výchozími hodnotami, KMZ se počítá stejně. Zvýšení by nabídlo přepočet všem rozborům zbytečně. Zadání („vyšší + 1“) počítalo s tím, že verze změnily obě větve. |
| **Přepočítat všechno** je jedna úloha ve třech krocích: 1. vzorky stop každého závodu (jen kde se změnilo, z čeho se čtou), 2. jednou osobní model, 3. postupy a záchytné body všech závodů, které je s tím modelem ještě nemají, jeden po druhém. Ve třetím kroku se model nemění (`analyse_entry` bez `before_routes`, test to hlídá). | Model se učí jen ze stopy a terénu (`leg_samples.npz`), ne z nejlepších postupů, takže kolo dokola nevznikne. Jedna úloha = jeden těžký výpočet najednou a jedno místo, kde ji zastavit. |
| Vzorky se čtou znovu, když se změní **klíč** v `best/samples.json`: verze vzorků (`oroute.personal.SAMPLES`, ručně), obsah `oroute/terrain.py`, `mapdata.py`, `fitload.py`, `official.py`, mapa bez tratě a běh (velikost a čas souboru), `course.json` a `official.json`. Rozbory starší než tahle noc klíč nemají: první „Přepočítat všechno“ jim vzorky přečte znovu. | Zadání: „jen když se změnila verze čtení terénu nebo stopy“. Změna `bestroute.py` nebo `routing.py` kvůli postupům vzorky neruší; když se změní, co se do vzorků zapisuje, musí se zvednout `SAMPLES` (poznámka je u zápisu v `bestroute.py`). |
| Přepočítat všechno nechá dosavadní model, když se nový liší o méně než 0,5 % (rychlost po rovině i každý činitel terénu, `personal.KEEP_TOL`). | Váha závodu závisí na dni (poločas 365 dní), takže stejná data zítra dají model o pár desetin promile jiný. Bez tolerance by každé další stisknutí přepočítalo všechno znovu. Běžný přepočet po závodě nebo poznámce toleranci nemá (jako dosud). |
| Přepočítat všechno i velké analýzy bere worker až po rychlých úlohách (`jobs.HEAVY_SQL`). | Načtení z ORIS nebo nahrání běhu nemá čekat desítky minut. |
| `leg_samples.npz` a soubory, které zapisuje appka (`official.json`, `barriers.json`), se zapisují do dočasného souboru a pak přejmenují. | Zastavená úloha nesmí nechat půl souboru (bod 7). |
| **Zastavení úlohy** je značka v databázi (`jobs.stop_requested`), ne zabití procesu z webu. Čekající úloha se zastaví hned; běžící se podívá na značku při každém hlášení postupu a každou sekundu, kdy běží skript výpočtu (`runner._run` skript zabije). Stav „zastaveno“. Worker po restartu zastavenou úlohu nevrací do fronty. | Web a worker jsou v Dockeru různé kontejnery: web na proces workeru nedosáhne. Sekunda je dost rychlá na to, aby uživatel viděl výsledek po obnovení stránky, a dotaz do SQLite za sekundu nic nestojí. Krátká úloha bez skriptu (usazení fotky, přepočet modelu) doběhne, má jen pár sekund. |
| Rozbor závodu, který už má hotové postupy, se počítá v kopii složky (`races/entry_N.new`) a vymění se za starou, až je celý. Zastavený nebo spadlý výpočet kopii smaže a platí předchozí rozbor. Nový závod (bez postupů) se počítá ve své složce jako dosud; při zastavení se smaže jen rozpracovaná část `best/`. | Zadání: po zastavení musí zůstat platný poslední hotový rozbor. Kopie stojí pár desítek MB a sekundu; nový závod nemá co chránit a mezičasy z `analyze.py` jsou celé dřív, než se začnou hledat postupy. |
| Zastavit smí jen vlastní úlohy (cizí vrací 404, „Zastavit všechny moje“ se cizích nedotkne). | Zadání. |
| Graf mezičasů: čísla kontrol nad kreslicí plochou (blízká čísla ve dvou řadách), nad nejrychlejším běžcem 6 % rezervy (aspoň 3,6 s). Spodek osy zůstává podle nejpomalejšího. Jméno a ztráta na referenci u nejbližší kontroly se ukážou po najetí myší nebo ťuknutí; každá čára má neviditelnou širší kopii, na kterou se trefuje prst. Na telefonu má graf šířku aspoň 640 px a posouvá se do strany. | Zadání. Oříznout pomalé běžce dole by schovalo, kde ztratili; jejich čáry jsou šedé a nepřekáží. Čára 1 px se prstem netrefí. Graf zmenšený na 390 px nešel přečíst. |
| Mapa bez tratě ze snímku nese v KMZ, o kolik je rozmazanější než export z Livelox (`<!-- ob-blur-m: … -->`, odhad z přiblížení prohlížeče a ze zmenšení v `pair.py`: bilineární převzorkování ≈ gauss 0,41 pixelu). Šířka zdi se pak čte s oběma rozmazáními (`terrain.sprint_walls(blur_m=…)`). KMZ z Livelox ani snímek při zvětšení 1 poznámku nemají a počítají se jako dřív. | Měření tools/snimek.py po sloučení: při zvětšení 1,5 se na sprintech ztrácely zdi (1,3 m vycházela 1,22 m pod prahem 1,25 m) a trasy vedly domy (MSK: změněné zakázané plochy 5,6 % → 12,7 %). S opravou 5,3 %. Oprava je jen částečná: slabé okraje rozmazané čáry padnou pod práh inku a na hnědé dlažbě se okraj čáry nebere jako šedý, takže zeď těsně nad 1,25 m se může ztratit dál (`docs/co-zbyva.md`). |
| Nápověda „Jak na to“ je přepsaná podle Tobiase (21. 10.): Garmin „Exportovat soubor“ (zip s jedním .fit), celý export přes Export Your Data, Livelox tři čárky → Stáhnout mapu dvakrát (Mapa s tratí, Pouze mapa, KMZ), a když Livelox stažení nedovolí, nejdřív fotka, pak šest kroků ke dvěma snímkům. Věta „Mapu neposouvej ani nepřibližuj“ zůstala přísná. | `oroute/pair.py` usadí jen snímek s tratí a snímku bez tratě dá stejné místo: snese posun do 10 % obrazovky, ale jiné přiblížení (`PairError("zoom")`) ani jinou velikost obrázku (`"size"`) ne. |
| Zip s jediným .fit a bez složky `DI_CONNECT` je jedna aktivita, ne export účtu: uloží se jako .fit a z dřívějších exportů se nic nemaže. Jde nahrát i v Podkladech závodu. | Dosud se každý zip bral jako celý export a nespárované běhy předchozích exportů se mazaly (`storage.drop_unpaired`): nová rada „nahraj zip“ by je mazala. Export s jediným během (ve složce `DI_CONNECT`) zůstává exportem. |
| Podklady závodu ukazují tři cesty k mapě v pořadí: 1. KMZ z Livelox (s tratí, bez tratě), 2. dva snímky z Livelox, 3. fotka papírové mapy (vlastní pole). Postup ke snímkům je jen v nápovědě, Podklady na něj odkazují. | Zadání. Jeden postup na jednom místě: dva by se rozešly. |
| **Opravit moji stopu**: nakreslená čára (od kontroly ke kontrole, konce jsou kontroly jako u plánovaného postupu) zastoupí GPS stopu úseku v rozkladu ztráty: „tvoje stopa“ se ocení modelem po čáře (s tolerancí stopy jako GPS, 8 m od nepřístupného a 15 m od cesty) a provedení = oficiální čas úseku z ORIS − tahle cena. Oficiální čas se po čáře nerozkládá: patří celé čáře. Úsek se z učení modelu **vyřadí** (jako ztráta kontaktu), druh chyby se u něj z GPS neurčuje. Posun celé mapy se nedělá. | Zadání nechalo na mně, jestli čas rozložit podle modelu, nebo rovnoměrně, a jestli úsek do modelu brát. Nakreslená čára není měření: rozložený čas by si vymýšlel, kde byl běžec pomalý, a model by se z toho učil vlastní odhad. Bezpečnější je úsek z učení vynechat; ztráta volbou × provedením rozložený čas nepotřebuje. Tobias: na Žebříčku B je to rušená GPS ve městě, ne posunutá mapa. |
| **Usadit mapu ručně** i pro KMZ a snímky (dosud jen fotka): běžec klikne aspoň na 3 kontroly na mapě s tratí; z toho, kde kontroly na mapě leží teď a kde byla stopa v oficiálních časech ražení, vyjde posun, otočení a měřítko (podobnost, ne afinita). Změní se jen LatLonBox v KMZ (`georef.shift_kmz`), obrázek ani titulní pruh ne. Livelox KMZ je mapa celého závodu: posune se KMZ s tratí všech kategorií závodu (z Livelox) i KMZ bez tratě. Snímky: jen mapa s tratí té kategorie a mapa bez tratě z těch snímků. Originály zůstávají (`*_puvodni.kmz`), „Vrátit původní usazení“ je vrátí; nové nahrání mapy původní kopii zahodí. | Zadání („pro případ, že je opravdu posunutá mapa“). Posunout jen jednu kategorii by rozešlo její trať se sdílenou mapou bez tratě a s ostatními kategoriemi. Afinita nebo perspektiva by u mapy z Livelox jen sledovala chybu GPS. Na stránce je napsané, že na pár zlobivých úseků je správně Opravit moji stopu, ne posun mapy (Tobias: Žebříček B je rušená GPS). |
| „GPS tu asi zlobí“ u úseku, kde je stopa při ražení dál než 30 m od kontroly, nebo kde se pohne rychleji než 30 km/h, měřeno přes 5 s. | Bod po bodu (1 s) dá obyčejný šum 3 m až 46 km/h: hlásilo by se skoro všude. Za 5 s se šum vyrovná a skok o 60 m na sekundu se pořád ukáže (test na umělé stopě se šumem). Starší rozbory to ukážou až po přepočtu. |
| OpenStreetMap: když `overpass-api.de` neodpoví (3 pokusy po 8 s), zeptá se appka stejně (POST, User-Agent, 3 pokusy) záložního `overpass.private.coffee`. Výsledek se neukládá nově: appka ho už ukládá k závodu (`osm/event_N.json`, `runner.fetch_osm` se pak už neptá) a teď se zapisuje celý nebo vůbec. Uživatel uvidí jen „OpenStreetMap teď neodpovídá (přetížený server). Zakázané přechody se doplní při příštím přepočtu.“, kód chyby jde do logu workeru. | Zadání. 502 je přetížený server, ne chyba dotazu. Druhé uložení by se jen rozcházelo s prvním. |
| „Sedí model s kategorií?“ je na stránce modelu jako „Jak dobře model sedí“ pro posledních 10 závodů s postupy a mezičasy kategorie; na Mezičasech zůstal jeden řádek s odkazem. | Je to kontrola modelu, ne rada pro běžce (zadání). Na stránce modelu jde vidět víc závodů vedle sebe. |

## Noc 24. → 25. 10.: Ztratil jsem se u kontroly (větev `ztraceny-u-kontroly`)

| Rozhodnutí | Proč |
|---|---|
| Nový modul `oroute/lost.py` staví na `oroute/relocate.py` (`prepare`, `cut`, `candidates`, `describe`, `bearing`) a nic v něm nemění. Z `relocate.main` jsem jen vytáhl přípravu mapy a výřez do funkcí; `relocate.json` je na Pohoře i MSK sprintu bajtově stejný jako na `main`. | Zadání: modul záchytných bodů rozšířit, nepřepisovat. |
| **Verze se nezvedají** (`bestroute.VERSION` 8, `relocate.VERSION` 7) a nesahám na `terrain.py`, `mapdata.py`, `fitload.py`, `official.py`. Scéna má vlastní verzi (`lost.VERSION` 1) a vlastní soubor (`lost/entry_N/lost.json` + `lost.npz`). | Zadání: nic se nepřepočítává. Zvednutí `relocate.VERSION` by „Přepočítat všechno“ přimělo přepočítat postupy všem závodům (`handlers._recompute_all` porovnává `summary.relocate`); změna těch čtyř souborů by znovu načetla vzorky všech závodů (`runner.SAMPLE_CODE`). |
| Dvě části: **scéna** (těžká, jednou na závod, krátká úloha `lost_scene`, asi minuta) a **rada** (pár desítek ms ve webovém procesu, z masek 2 m kolem kontroly bez obrázku mapy). Scéna má afinní převod lat/lon → buňka (přesný: GeoMap je plochá Země otočená o rotaci mapy). | V terénu se nesmí čekat minutu na každé ťuknutí. Obrázek mapy má desítky MB, masky jednoho závodu jednotky MB. |
| Úloha se pustí, **když stránka zjistí, že scéna chybí nebo je stará** (otisk: verze, obě mapy, čas analýzy). Není součástí analýzy ani „Přepočítat všechno“. Po neúspěchu se sama znovu nepouští (tlačítko Zkusit znovu). | Nic se nepočítá navíc tomu, kdo stránku nepoužije. Nový test by jinak měnil pořadí úloh po analýze, na kterém stojí starší testy. Znovu usazená mapa nebo nová analýza scénu zneplatní. |
| Stránka jde použít **i bez běhu** (jen mapa s tratí a bez tratě): kontroly se pak čtou z KMZ s tratí stejně jako v `analyze.py` bez stopy (`detect_course` + `order_by_lines`), nebo z usazené fotky. S analýzou se berou kontroly z ní (pořadí podle ORIS), zakázané přechody, náběhové body a model. | Pro závod bez .fit nebo místo, které stopa nechytla. (Původně „na trénink v terénu“; od 25. 10. je stránka jen rozbor po závodě, otázka 42.) |
| **„Nedá se minout“** = z 9 rovnoběžných paprsků napříč celým kruhem nejistoty v daném směru (po 10°) narazí na tu věc aspoň 80 % dřív než na něco neprůchodného. Bodový objekt je kotouč 8 m, z velkého kruhu ho proto paprsky skoro nikdy netrefí. Skóre: spolehlivost druhu × podíl paprsků × vzdálenost (plná do 150 m, 0,5 od 250 m) × navázání na kontrolu × poměr celé cesty k přímé (od 1,5× klesá). | Zadání: nejjistější, ne nejbližší. Paprsky z celého kruhu, ne jen ze středu, protože běžec neví, kde v kruhu je. Bez poměru celé cesty vedla rada na Petřvaldu u kontroly 6 k cestě a zpátky, i když byla kontrola blíž než cesta. |
| Navázání na kontrolu: linie do 40 m od kontroly → „podél ní na sever asi 100 m, kontrola je 30 m vpravo“ (strana podle směru chůze); jinak křížení, konec cesty nebo přechod vodoteče na linii do 150 m od kontroly → „podél ní ke křížení, odtud kontrola 95 m na azimut 200°“; jinak azimut z místa, kde se linie chytí. | Vzor ze zadání. Dlouhý azimut z linie se snadno ztratí: vzdálenější navázání má nižší skóre (od 60 m do 180 m o 35 %). |
| **Relokace:** když je nejbližší jistá věc dál od běžce, než je kruh nejistoty (a kontrola také), první věta zní „Nehádej směr ke kontrole. Nejdřív dojdi / se vrať…“. „Vrať se“, když je ta věc do 70° od směru, odkud běžec přišel (k minulé kontrole, po závodě zpět po stopě). Když jistého není nic, rada pošle zpět na náběhový bod (z `relocate.json`). | Zadání bod 5. Směr příchodu je jediné, co appka o „posledním jistém místě“ v terénu ví. |
| Neprůchodné pro radu: voda, OOB, budovy, oplocenky, zdi sprintu, zakázané čáry a plochy, **a ploty mapy** (rada nevyzve plot přelézt). Linie za překážkou dostane obchůzku (nejvýš 1,5× přímka), jinak vypadne. Ťuknutí do oplocenky se posune na nejbližší místo venku a stránka to řekne. | Zadání: nevyzývat jít do oploceného místa. Plot stojí v postupech 90 s, ale radit „přelez plot“ ztracenému běžci je špatně. |
| Paprsek počítá jen věc, která leží aspoň o poloměr kruhu dál (za celým kruhem). **Dlouhá linie, která vede kruhem** (nejbližší bod do poloměru, kus linie aspoň 2× poloměr a aspoň 60 m, cesta k ní volná), je jistá zvlášť: „Do 50 m od tebe vede cesta (nejblíž na sever, asi 15 m): najdi ji.“, do 8 m „Jsi u cesty, drž se jí.“ | Paprsky vycházejí z průměru kruhu kolmého na směr: linie uvnitř kruhu souběžná s tím průměrem vycházela „trefená všemi“, i když běžec z druhé půlky kruhu by ji minul (test). A naopak linie, která kruh protíná, nevycházela jistá nikdy, i když ji běžec na 30 m v lese uvidí (Petřvald 10 po závodě, noční 10). |
| Místo po závodě, které splyne s jiným (do 30 m nebo 20 s), si nechá začátek, ale jméno dostane podle toho, co našla analýza (druh chyby, bloudění, zastavení), když tam něco našla. | Zadání: chyby u kontrol appka už detekuje, použít to. Na Petřvaldu se tak nedoběhnutí u 14 a 15 ukáže jako nedoběhnutí, ne jako zpomalení. |
| Rybník je pro radu každá voda, i úzká (relocate bere jako rybník až vodu širší než 12 m). | Petřvald S–1: kontrola na konci úzkého rybníka (8 m), který byl nejlepší záchytný bod a rada ho neviděla. |
| Po závodě: kotvy z toho, co appka už našla (druh chyby `mistakes.classify`, zastavení, místo bloudění z `relocate.wandering`), k nim zpomalení pod 50 % vlastní rychlosti aspoň na 10 s, otočka o 135° (10 s před a po) a smyčka (za 45 s aspoň 30 m, konec blíž než 40 % z toho). Jen 20 až 100 m od kontroly, dvě místa do 30 m nebo 20 s jsou jedno, nejvýš 4. U každého: co bylo do 30 m, co stopa přešla v posledních 100 m, a rada z místa s kruhem 30 m. | Zadání bod 6. Bez smyčky se plynulé kroužení nenašlo (test). 20 m je samo ražení. |
| Popis kontroly: `leg_notes.control_desc` (ručně, nejvýš 200 znaků), ukládá se ze stránky i s poznámkou úseku, **jen se ukáže** jako poslední věta rady. Není v `MODEL_FIELDS`, nic nepřepočítá. Patří běžci (jako poznámka), ne celé kategorii (otázka 41). | Zadání: volitelné pole, funkce musí jít i bez něj. |
| Věty jsou šablony v `webapp/texts.py` (`lost_advice`, `lost_moment`), vzdálenosti zaokrouhlené na 5 m (nad 100 m na 10 m), azimuty na 5° k severu mapy jako všude. Nejvýš tři věty. | Zadání: bez LLM, jedna až tři věty. |
| Ladicí obrázky (`--debug`) mají věty bez diakritiky: v kontejneru není písmo s českými znaky. Plné věty jsou v `rady.json` a v dokumentaci. | Přidat písmo do obrazu = nová závislost kvůli ladicím obrázkům. |
| ~~Poloha z telefonu (`navigator.geolocation`) je na stránce s poznámkou „jen na trénink“.~~ **25. 10.: pryč**, viz další oddíl. | Tobias: na závodě se mobil s polohou ani podobné pomůcky používat nesmějí (otázka 42). |

## Noc 25. 10.: oplocenky, severky místo vodotečí, Ztratil jsem se jen po závodě (větev `oplocenky-vodotece`)

Podklad: Tobiasův závod Bělá (okr. Opava, 18. 10. 2026) z webové appky, snímek z Livelox 0,97 m/px. Podrobně
`docs/oplocenky-vodotece.md`.

| Rozhodnutí | Proč |
|---|---|
| **Oplocenky na hrubém obrázku** (zoubek 2,5 m je kratší než 4 px: snímky a KMZ z Livelox 1 až 1,33 m/px) se čtou jinak: zoubky se hledají na ploše uzavřené samotnou čarou (bez zavírání mezer), „zářez“ zoubku podle naměřené tloušťky čáry, krátký zoubek od 2 px (1,5 m), černá tisku mapy do 1 px od čáry, uvnitř i směs pruhů se zelenou, tvar podle vepsaného kruhu (6 m), ne podle obdélníku kolem. Na ostrých mapách (Petřvald 0,59, sprinty 0,27 až 0,4 m/px) zůstává čtení jako dřív. | V Bělé se z 33 oplocenek našlo 9: rozmazané čáry tloušťky 4 px slily zoubky s čarou a test černé (součet RGB < 150) na rozmazané čáře selhal. Stejná uvolnění na SZL Zábřeh (0,27 m/px) udělala z dvorů mezi domy 50 nových „oplocenek“ (změřeno), proto jen na hrubých obrázcích. |
| Neprůchozí maska oplocenky obsahuje **i samotný plot** (čáru kolem plochy; ne na sprintové mapě, kde jsou to okraje domů a ulic), a **úzký roh** odříznutý zavíráním mezer (malá plocha přes plot od nalezené oplocenky) k ní patří. | Bělá S–1: maska byla o délku zoubků uvnitř plotu, čára plotu zůstala „cestou“ a možnost postupu běžela po plotu a přes špičku trojúhelníku. |
| Oplocenka do 60 000 m² (dřív 10 000); nad 10 000 m² potřebuje zoubek aspoň každých 60 m obvodu. Plocha z víc než 25 % zpevněná (světle hnědá) není oplocenka; okolí do 15 m musí mít barvy mapy (ne znak v rohu listu). | Velké oplocenky jsou běžné. Ulice mezi zahradami vesnice (Petřvald) a orlice ve znaku (Petřvald) se jinak přijaly (změřeno). |
| **Mezera v plotu** do 12 m (dřív 5 m) neotevře oplocenku, když jsou po obou stranách ploty se zoubky (`fences()`): konce dvou plotů 5 až 12 m od sebe se spojí. | Branka nebo cesta přes plot má 3 až 5 m, k tomu přerušení čáry kvůli vrstevnici nebo průseku; 12 m je 9 px na 1,33 m/px. Smyčka cest nemá zoubky, takže se nezavře. V Bělé žádná taková mezera nebyla. |
| **Obrys bez zoubků oplocenka není.** | Tobiasův obrázek 5 (obdélník na 4-5) zoubky má, jen rozmazané (najde se teď). Uzavřená plná černá čára bez zoubků je v lese i smyčka cest (504) nebo okraj silnice; riziko falešných zákazů je větší než užitek. |
| **Neprůchodný plot** (ISOM 2017-2 č. 518, v ISOM 2000 č. 524 „vysoký plot“): zoubky po dvou na jedné straně (mezera do 4 m, kolem ní aspoň dvakrát delší), aspoň 2 dvojice a 60 % zoubků v dvojicích, zoubky ne do zakázaného prostoru → neprůchozí jako oplocenka (jen čára plotu, cesta vedle zůstává). Obyčejný plot, který nic neuzavírá, dál stojí 90 s. | Pravidlo ISOM ze zadání. Bez vzoru dvojic dávaly sprinty (zoubky po 3 m) 5 až 6 „neprůchodných“ plotů. |
| Kontrola **otevře jen oplocenku, ve které stojí nebo u jejíhož plotu je** (do 5 m, jako dřív), ne sousední slitou; kontrola na neprůchodném plotu ho otevře v okolí 4,5 m. | Rozhodnutí q22 platí. 2 m by na SZL nechala zavřenou falešnou „oplocenku“, kterou dřív otevírala kontrola. |
| **Severky** (`terrain.north_lines`): projekce modrých pixelů pod úhly do ±30°, nejostřejší vrcholy; severka je vrchol na pravidelné mřížce (rozestup = medián mezer, přesnost 2 px + 0,5 px na každý rozestup od kotvy), modrá aspoň na 12 % délky (30 % u čar, které mřížku tvoří), tenká (vedle ní do 8 px nejvýš čtvrtina modré). Osamocená čára bez mřížky jen s 80 % délky a souvislým kusem 15 %. Úhel se ukládá a azimuty v `relocate.json` a radě „Ztratil jsem se“ jsou k severkám. | Změřeno na 11 mapách: severky jsou přerušené kvůli popisům a značkám (nejdelší kus jen 5 až 30 % mapy), takže „plná bez mezer“ je nepoužitelné; mřížka (300 m v lese, 120 m na sprintu) je spolehlivá. Bělá: 10 severek pod úhlem 0,70°, staré pravidlo (svislé sloupce) nenašlo žádnou. |
| Vodoteč přes severku zůstane: modrá v pásu severky, která navazuje na kus modré mimo něj (do šířky čáry + 2 px), patří vodoteči. Rybník přes severku (`NORTH_GAP_PX`) se zavírá napříč úhlu severek. | Zadání krok 2.3 a 2.4. |
| **Zarážka:** cesta nebo vodoteč do 10 m od kontroly je její vlastní a do 60 m se počítá, až když ji paprsek opustí aspoň na 5 m; „cesta, po které běžec přišel“ (souběžná s paprskem) se přeskočí, jen když prodloužená vede do 15 m od kontroly. | Bělá 1: kontrola u dvou cest, zarážka „vlevo 15 m, vpravo 15 m“ (vpravo cesta na severce, Tobiasova červená čára k jihu); čárkovaná cesta 55 m dál (Tobiasova žlutá) se přeskočila jako „cesta příchodu“. Teď „rovně cesta 55 m“. |
| **Rada bez okliky:** linie do 100 m od kontroly vede ke kontrole i bez křížení; bod na linii vyhraje, jen když z něj nevede o víc než 15 m delší azimut a celá cesta je nejvýš 1,5× (nebo kdykoli do 1,25×) delší. Kdo stojí u linie, dostane azimut z místa, kde stojí, když je kratší. | Tobias (Bělá 4): radši krátký přímý úsek na jistou čáru a po ní, než dlouhá oklika. Bělá 11 a 3 vedly ke křížení a 95 až 100 m zpět. |
| **Ztratil jsem se jen po závodě:** pryč „Teď v lese“, „Moje poloha z telefonu“ a `navigator.geolocation`; hlavní je „Po závodě: kde jsem se ztratil“, ťuknutí jako „Kde jsem asi byl“; věty v minulém čase. Závod dnes nebo v budoucnu bez stopy: místo odkazu věta, stránka jen vysvětlí. | Tobias 25. 10. (otázka 42). |
| Kruh nejistoty: výchozí 50 m v lese, 25 m na sprintu (`lost.CIRCLE_SPRINT_M`, podle `mapdata.obstacles` `sprint`, uloženo ve scéně). | Tobias 25. 10. (otázka 40). |
| Verze: `bestroute.VERSION` 9, `results.ROUTES` 9, `relocate.VERSION` 8, `results.RELOCATE` 8, `lost.VERSION` 2. | Mění se postupy (oplocenky, severky v terénu), záchytné body a zarážky (severky, azimuty) i scéna (sprint, úhel severek). |

## Co jsem nedělal záměrně

Livelox API klíč ani import IOF XML, Strava, výška porostu z LiDARu (zadání). Žádné volání AI. Nic jsem neposílal na produkční server ani na klubový web; z něj jsem nečetl nic nového (podklady už byly v `docs/reference/`).

## 8. 11. 2026: stránka závodu neposkakuje, Garmin nahoře, režim barev, „záměrná“ (issues 5, 8, 10, 12)

| Rozhodnutí | Proč |
|---|---|
| Průběh výpočtu je **lišta pevně dole v okně** (`position: fixed`, na telefonu nad spodní nabídkou), ne odstavec nad mapou. Lišta je ve stránce závodu vždy, schovaná, když se nic nepočítá. | Odstavec nad mapou se objevoval, měnil délku a mizel a obsah pod ním skákal; navíc byl daleko nad místem, kde člověk čte. Lišta mimo tok stránky nic neposune. |
| Konec úlohy pozná `ob.js` jen podle **viditelné** lišty. | Lišta je teď v každé stránce závodu; bez toho se stránka načítala pořád dokola (našel test v Playwright). |
| Po vlastním načtení se stránka vrátí na **prvek, který byl nahoře v okně** (a na otevřenou záložku), uložené v `sessionStorage` jen pro záložku prohlížeče; znovu ještě po vykreslení mapy (`ob-vykresleno`) a po `load`, dokud člověk sám neposune. | Pozice v pixelech nestačí: nad mapou se po přepočtu mění hlášky a rozbalení „Jak je rozbor spočítaný“. Na `main` se tabulka úseků po dopočítání posunula o 36 až 54 px, teď do 0,4 px (Playwright, 1280×900 i 390×844, úloha hotová i selhaná). |
| Hlášky, které se objevit musí (selhaná analýza), zůstávají nahoře; lišta na 12 s řekne, že tam jsou. Místo pro souhrn ztrát a pás úseků se drží od začátku (`min-height`, `visibility`). | Hláška je důležitá a patří k závodu, ale čtenář je jinde; přeskočit ho k ní by bylo horší. |
| Garmin Connect: tlačítko, počet zaškrtnutých a volba modelu kopců v **liště nad tabulkou** (`position: sticky`); na telefonu se drží jen její spodní řádek. Dolní tlačítko zůstává. Tlačítko říká „Načíst vybrané“, když model kopců není zaškrtnutý. | Rok běhů je dlouhá tabulka. Celá lišta by na telefonu zabrala třetinu výšky (289 px), spodní řádek 169 px. |
| Odkaz Načíst z Garmin Connect je i na Přehledu závodů (jen lokální appka) a na Nahrát běhy **nad** formulářem. | Je to nejjednodušší cesta (nápověda #garmin). |
| Světlý / tmavý režim se ukládá **k účtu v databázi** (`users.theme`: `svetly`, `tmavy`, `''` = podle zařízení, `NULL` = ještě nevybráno), server ho píše do `<html data-theme>`; `localStorage` je jen kopie. Jazyk se ukládá taky (`users.lang`) jako záloha za cookie. | Ověřeno: lokální appka startuje na náhodném portu a `localStorage` patří k adrese s portem, takže režim se po restartu ztratil; cookie jazyka port nerozlišuje a zůstala. Cookie by stačila v appce, ale na webu by režim neplatil na jiném zařízení a nová relace by ho neměla; databáze funguje v obou a bez bliknutí. `NULL` proti `''` dovolí převzít režim, který už někdo měl v prohlížeči. |
| „Schválná zastávka“ → **„záměrná zastávka“** ve všech textech (mapa, panel úseku, nastavení, nápověda, dokumentace). „Schválně“ ve smyslu „úmyslně“ v ostatních dokumentech zůstává. | Tobias (issue 10). |

## 9. 11. 2026: průběh načítání z ORIS, víc registračních čísel, etapové závody (issues 1, 2, 11)

| Rozhodnutí | Proč |
|---|---|
| PR stojí na `origin/main`. | PR #47 i #48 už jsou sloučené. |
| Načítání z ORIS je na Přehledu závodů vidět jako řádek nad přehledem i nad „Jak začít“, se stavem úlohy („zatím 12 z 85 závodů“). Stránka se obnoví, jakmile úloha z `jobs.json` zmizí (`data-ceka-na`), i když doběhne dřív než první dotaz. Výsledek (zpráva úlohy) se ukazuje 10 minut po doběhnutí. | Prázdný přehled vypadal jako chyba. Obnovení jen podle „bylo aktivní, teď není“ nestačí: krátká úloha doběhne před prvním dotazem stránky. |
| Během načítání je tlačítko zakázané a `/sync` nezaloží druhou úlohu ani vedle běžící (dřív jen vedle čekající). | Zadání; dvě souběžná načtení by se ptala ORIS dvakrát. |
| Víc registračních čísel v tabulce `user_regnos`; `users.oris_regno` zůstává první číslo účtu a trigger `users_regno_fixed` dál platí. Do seznamu ho kopírují triggery, ne kód. | Registrace, Profil, `seed.py` a nástroje v `tools/` zakládají účty po svém; trigger je pokryje všechny bez změny. |
| Čísla z vlastních přihlášek v ORIS (stejné ORIS ID) se do účtu připíšou sama, i na serveru. Ručně přidat jde jen v lokální appce. | Ověřeno v ORIS: ID osoby se přestupem nemění a přihlášky nesou staré číslo. Je to tentýž člověk podle ORIS, ne změna čísla účtu; bez toho by účet s novým číslem nenašel mezičasy starých závodů. |
| Staré číslo, na které `getUser` už neodpoví, nevadí, když je ID známé. | Ověřeno v ORIS (AOV7900, LBM0909): jinak by účet založený se starým číslem po přestupu přestal načítat. |
| Nové číslo musí mít stejné ORIS ID nebo stejné jméno (bez diakritiky, velikosti písmen a pořadí slov); staré číslo musí být v přihláškách běžce. | Zadání: číslo s jiným jménem odmítnout. Jméno v účtu si běžec může přepsat, proto rozhoduje i ORIS ID a jméno podle ORIS. |
| Smazat jde jen ručně přidané číslo, pod kterým není v uložených výsledcích žádný závod účtu. | Zadání: jen číslo přidané omylem. |
| Přihlásit se jde kterýmkoli číslem účtu. | Po přestupu člověk zadá to nové. |
| `oroute/splits.py` se nemění; `splits.my_regno` vybere z čísel účtu to, které je ve výsledcích kategorie. | Výpočet zůstává stejný (žádná nová verze), mění se jen vstup. |
| Zastřešující etapový závod se nezakládá, jen se zapamatuje (`oris_umbrellas`). Přihláška na něj se rozloží na etapy podle názvu kategorie, jen kde ORIS etapu nevypisuje zvlášť. | Ověřeno: ORIS u Tobiase vypisuje zastřešující závod i každou etapu, takže etapy už v databázi byly a navíc tři prázdné zastřešující závody. Rozložení je pojistka pro závod, kde by ORIS etapy nevypsal. |
| Zastřešující závod ze starší verze se pozná podle disciplíny „Etapový závod“ a jednou se ověří `getEvent`; co zastřešující není, dostane `stage_n = 0` a už se na něj appka neptá. | Starší databáze nemá `Stages`; ptát se ORIS u každého závodu by bylo zbytečné (na Tobiasově databázi 3 dotazy). |
| Přihláška zastřešujícího závodu s během jde na etapu ze dne běhu (místní čas): celá, když tam běžec etapu nemá; jinak jen běh, když etapa běh nemá a přihláška nemá poznámky. Mapy jdou s ní, jen když se přihlášky přesunuly na jedinou etapu. Jinak závod zůstane. | Den běhu je jediné spolehlivé spojení s etapou. Mapa bez jednoznačné etapy by mohla skončit u jiné trati. |
| Disciplína je vidět v přehledu i na stránce závodu u všech závodů z ORIS, u etapy navíc „E1 / 5“. | Disciplína se dřív nikde neukazovala; u etap ji chce zadání, u ostatních závodů pomůže taky. |
| KITL 2025 se nemění. | V ORIS to není etapový závod, ale dva závody spojené `MultiEvent1` (8228 6. 9., 8229 7. 9.), viz `docs/oris.md`. |

## 11. 11. 2026: kontroly podle ORIS a nahrání víc souborů (issues 9 a 6, větev `kontroly-podle-oris`)

| Rozhodnutí | Proč |
|---|---|
| Počet kontrol podle ORIS je **počet mezičasů** (`entries.splits`), jinak počet kódů kontrol kategorie (`classes.control_codes`). `classes.controls` („Controls“ z `getEvent`) se k porovnání nepoužívá. | Ověřeno v databázi autora: u 12 z 83 závodů říká `controls` víc, než mají mezičasy (SZL 15. 2. 2025: 28, na mapě i v popisech 26). Varování by pak bylo falešné u každého sedmého závodu. |
| Kroužek, který se sám najde na několika poloměrech (tlustá čára), už není cíl: cíl musí mít dva kruhy, které se liší aspoň o 12 % poloměru (dřív pevně 5 px). Na mapách s poloměrem do 41 px (všechny dosavadní) se nic nemění. | Bohemia 2025 E1 (0,43 m/px, čára 7 px): všechna kolečka se brala jako cíl a našla se 2 z 11 kontrol. Ostatních 29 map v `tools/kolecka.py` vychází stejně. |
| Chybějící kolečko se hledá **jen** s oficiálními časy, jen kolem místa, kde byly hodinky v čase ražení (80 m), jen s poloměrem ostatních koleček a jen dokud počet nesedí s ORIS (`course.find_missing`). Bere se, když je vytištěno aspoň 40 % obvodu, žádná mezera není větší než 150°, uvnitř není fialová (šrafy) a na okraj dosedá spojnice, nebo je vytištěno aspoň 60 %. | Rozřezaná kolečka (ISOM) mají měřeně 65 až 70 % obvodu a mezery 25 až 55° (Bohemia E1, GPS E1). Na mapách, kde počet sedí, se nic nehledá, takže se jejich trať nemůže zhoršit. Čísla kontrol, křížení spojnic a šrafy u místa ražení kolečko nedají (test). |
| Kolečko navíc se vynechá jen tehdy, když je přes 80 m od všech míst ražení, hodinky ukazují všechna ražení a po vynechání vyjde přesně počet ORIS (`course.drop_extra`). Mapa se stovkami „koleček“ se nechá, jak je, a jen se hlásí. | Přebor BFM+SFM 2026: „10“ přes „4“ se četlo jako kolečko. Mapa se 169 kolečky má fialovou přečtenou špatně; vybírat z nich podle stopy by mohlo potichu dát špatnou trať. |
| Rozbor zapisuje `course_check` (nalezeno, dohledáno, vynecháno, ORIS, zdroj) a stránka závodu ukáže varování „Kontrol na mapě: 13, v ORIS: 18“ s odkazem **Doplnit kontroly**. Když se dohledávalo, je tam jen poznámka s odkazem „Zkontrolovat kontroly“. Bez ORIS a u ruční tratě se nic neukazuje. | Zadání (Tobias). |
| **Doplnit kontroly** (`/races/<id>/kontroly`) je stránka ručního usazení (`photo.html`, `photo.js`) v dalším režimu: body S, 1 až N, C, kde N je počet z ORIS. Kolečka z rozboru dostanou číslo podle ražení (přiřazení do 120 m), kolečka navíc jsou šedá. U každého bodu ukáže vzdálenost od místa ražení (nad 40 m červeně). | Zadání: ručně jako u usazení, počet bodů podle ORIS i při 13 nalezených. Stejné ovládání, které už lidé znají. |
| Ruční trať se ukládá **pro kategorii** do `…kmz.course.json` (stejné místo jako trať z usazené fotky) s `by_hand: true`; smaže ji jen nová mapa s tratí (`storage.save_map`), nebo tlačítko na stránce. Uložení pustí rozbor všech přihlášek kategorie. | Trať je stejná pro všechny v kategorii. Runner tenhle soubor už předával `analyze.py --course`, takže přepočet novou verzí ruční trať zachová. |
| `analyze.py --course` přepíše `course.json` souřadnicemi spočtenými z pixelů aktuální mapy. | Po ručním posunutí mapy (`mapfix`) byla zeměpisná šířka a délka v souboru stará; `bestroute.py` čte právě je. |
| Nová `oroute/course.VERSION` (1) v `analysis.json`; přepočet jen postupů (`routes_only`, „Přepočítat vše“) přečte trať z mapy znovu, když byla přečtená starší verzí. `bestroute.VERSION` a `results.ROUTES` 9 → 10, aby appka přepočet nabídla. | Samotná nová verze postupů trať znovu nečetla (`out/course.json` existoval), takže by se oprava Bohemie E1 do starých rozborů nedostala. Model se v kroku 1 učí ze vzorků se starou tratí; až příští přepočet vzorky přečte znovu. |
| Ruční usazení fotky, mapy i snímků bere body z mezičasů běžce už dřív (ověřeno testem). Bez mezičasů dál odmítne, protože nemá s čím polohu porovnat. Doplnit kontroly mezičasy nepotřebuje: bez nich jen nečísluje podle ražení a u závodu mimo ORIS se počet kontrol zadá. | Zadání (krok 4.1). |
| Dva snímky z Livelox: každý se kontroluje zvlášť. Ten, který neprojde (přípona, pod 400 px, nad 120 Mpx, HEIC), dostane vlastní hlášku se jménem souboru, druhý se uloží, jako by byl nahraný sám. | Issue 6: jeden příliš velký snímek zahodil oba. |
| Prohlížeč před odesláním vynechá soubor větší než limit svého pole (`data-max`, běh 50 MB) a pak největší soubory, dokud celek nesedí s `OB_MAX_UPLOAD_MB` (`OBAPP.maxUpload`). Jména vynechaných pošle v poli `vynechano` a server je vypíše. Když se nevejde nic, neodešle se nic a hláška je hned. | Jinak server odmítne celé tělo (413) a nenahraje se nic. |
| Server vrátí 413 jako přesměrování zpět s hláškou (u skriptu JSON s adresou). | Formulář bez skriptu dřív skončil holou chybovou stránkou Werkzeugu. |
| `/upload` pozná rozbitý soubor hned podle začátku (`.FIT` na bajtech 8 až 11, zip `PK`): nahlásí ho jménem a ostatní zpracuje. Soubor, který začíná dobře a je poškozený dál, selže ve své úloze jako dřív. | Dřív se rozbitý soubor ukázal až v seznamu úloh. |
| `.venv/` v `.gitignore`. | Na Windows bez Dockeru se testy pouštějí z místního prostředí v repu. |

## 11. 11. 2026: rozbor jen z mapy s tratí (issue 13, větev `jen-mapa-s-trati`)

| Rozhodnutí | Proč |
|---|---|
| Závod jen s mapou s tratí z Livelox (KMZ nebo snímek) dostane nejlepší postupy: terén se čte z mapy s vyjmutou tratí a čárou postupu (`oroute/occlusion.py`, varianta `nearest`; `runner.terrain_map`). | Měření na 4 závodech (71 úseků): 85,9 % stejný postup a medián rozdílu času 1,1 % (1,7 % s červenou čárou), tedy nad předem daným prahem 85 % / 5 %. Čísla v `docs/jen-mapa-s-trati.md`. |
| Záchytné body a „Ztratil jsem se“ se z odhadnuté mapy nepočítají. | Potřebují přesný terén těsně kolem kontroly, kde je právě kolečko. |
| Bez nového sloupce v databázi: odhad se pozná podle toho, že závod nemá `maponly_file`. Opravdová mapa bez tratě odhad nahradí sama (rozbor se přepočítá jako dnes). | Menší zásah do schématu a do nahrávání. |
| Doplněná mapa je v `terrain/class_<kategorie>_<otisk>.kmz` a má vlastní cache terénu. | Mapa s tratí je pro každou kategorii jiná. |
| `bestroute.VERSION` a `results.ROUTES` 10 → 11. | Appka nabídne přepočet starších rozborů. |
| Nápověda radí vypnout čáru postupu v Livelox před snímkem s tratí. | Zakrývá mapu; snímek bez tratě je pořád lepší. |


## 11. 11. 2026: nápověda ke snímkům z Livelox na Macu (issue 4, větev `napoveda-snimky-mac`)

| Rozhodnutí | Proč |
|---|---|
| Nápověda `#snimky` ukáže zkratky podle systému (Windows F12 / Ctrl+Shift+M, Mac ⌥⌘I / ⇧⌘M), jde přepnout ručně. | Test na Macu: nápověda znala jen Windows. |
| Doporučený je Chrome i na Macu, Safari je druhá možnost a nápověda rovně říká, že snímek bude menší. | Safari nemá snímek celé stránky ani rozměr 5000 × 4000 (dokumentace Apple). |
| Obrázek mapy z canvasu v Safari zatím jen zápis v `docs/snimky-livelox.md`, bez pole v Podkladech. | Chybí vzorová data a napasování na snímek s tratí nejde změřit. |

## 11. 11. 2026: překážky v mapě: vedení a oprava rozpoznaných (issues 37 a 38, větev `prekazky-oprava`)

| Rozhodnutí | Proč |
|---|---|
| Elektrické vedení, lanovky, potrubí a hranice se z OpenStreetMap nestahují a test (`tests/test_osm_dem.py`) hlídá, že by se nečetly, ani kdyby je server poslal. | Pod vedením se běží; do dotazu se dostávají jen železnice, dálnice a ploty/zdi. |
| Pravidlo pro vedení čtené z obrázku mapy jsem **nezměnil**. Testy hlídají, že příčky přes čáru, střídavé příčky a čtverce pylonů plot nedají. | Na třech mapách, které mám, žádné vedení není (jediný „plot“ na Žebříčku je skutečný plot u silnice). Jednostranná řada krátkých příček je geometricky totéž co plot; pravidlo bez skutečného vzorku by zhoršilo ploty. Otázka 59 v `co-zbyva.md`. |
| Oprava rozpoznané překážky je **osobní**: tabulka `barrier_overrides (entry_id, kind, key, action)`, k záznamu, nikdo jiný ji nevidí a jeho postupy se kvůli ní nepřepočítají. Ruční čáry zůstávají sdílené. | Stejně jako vlastní nastavení OSM a šrafů: oprava je můj názor na mapu. |
| Klíč prvku je typ a střed v lat/lon (zaokrouhlený na 1e-5 °). Při použití se prvek hledá nejblíž středu do 15 m. | Pořadí prvků se po novém čtení mapy mění, střed ne. |
| Opravit jde plot (není překážka, jen těžký průchod, neprůchozí), oplocenka (není překážka, je plot), čára z OSM (není překážka, jen těžký průchod) a šrafy (není překážka). Zdi sprintových map ne. | Zdi jsou v mapě jinak (`terrain.sprint_walls`), otázka 61. |
| „Není překážka“ u plotu nechá černou čáru jako mapu bez cesty: terén pod ní je to, co leží vedle. | Vrátit ji jako cestu by dalo rychlost cesty vedení, které cesta není. |
| Opravy jdou do `best/barriers.json` (klíč `overrides`), takže je čtou `bestroute.py`, `oroute/planned.py` i `oroute/relocate.py` bez nových přepínačů a plány s nejlepšími postupy se shodnou. | Všechny tři volají `mapdata.obstacles` samostatně. |
| Po uložení opravy se přepočítají jen postupy toho záznamu (`barriers.requeue_entry`), ne celý rozbor (`matching.queue_analysis`). | Trasa, mezičasy a model se nemění, jen postupy; stejně jako u změny nastavení OSM. |
| `best.json` nese seznam rozpoznaných překážek (`obstacles`), `bestroute.VERSION` a `results.ROUTES` 11 → 12. | Starší rozbory ho nemají, appka je nabídne přepočítat; vrstva se jinak u nich nezobrazí. |
| Opravy jedou v `.obzavod` (`mine.obstacles`), na mapě se vrstva pamatuje po dobu okna prohlížeče (`sessionStorage`) a po přepočtu zůstane zapnutá. | Přepočet stránku načte znovu. |

