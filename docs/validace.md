# Validace (měření z noci 6. → 7. 10. 2026)

Všechna čísla jsou ze čtyř závodů v `data/` a z jednoho běžce. Je to málo; u každého závěru je napsané, jak moc se o něj dá opřít.

## 1. Regrese: čtyři závody

| Závod | Čas dnes | Má být | Zdroj časů |
|---|---|---|---|
| Azymut Cup E5 | 77:02 | 77:02 | GPS (není v ORIS) |
| Azymut Cup Day 4 | 55:07 | 55:07 | GPS |
| Pohora | 50:22 | 50:22 | oficiální mezičasy ORIS |
| Petřvald | 80:18 (1:20:18) | 1:20:18 | oficiální mezičasy ORIS |

Časy jsou z přepočtu všech čtyř závodů konečným kódem přes webovou frontu (vývojové prostředí). Úplný běh pomalých testů (36 testů) proběhl 7. 10. odpoledne na větvi `rychlejsi-ovladani`: `legs.csv` a `course.json` čtyř závodů jsou shodné se zlatými soubory `tests/golden`, `best_legs.csv` také; u Petřvaldu je zlatý `best_legs.csv` nový (oprava čtení terénu, část 12).

## 2. Řadí model úseky podle obtížnosti stejně jako kategorie?

Čas nejlepšího postupu podle osobního modelu proti referenčnímu času kategorie (průměr nejlepší čtvrtiny) po úsecích. Nemá sedět čas, má sedět pořadí a poměry. Míra: Spearmanova pořadová korelace; „rozptyl“ je medián absolutní odchylky poměru od společného měřítka.

| Závod | Běžců | Úseků | Korelace | Rozptyl | Poznámka |
|---|---|---|---|---|---|
| Pohora H16C | 32 | 17 | **0,94** | 14 % | výškopis ČÚZK |
| Petřvald H18, původně | 5 | 20 | 0,87 | 21 % | AWS, bez železnice |
| Petřvald H18, v noci 6. → 7. 10. | 5 | 20 | 0,93 | 15 % | ČÚZK a železnice z OSM |
| Petřvald H18, po opravě čtení terénu | 5 | 20 | **0,95** | 11 % | ČÚZK a železnice z OSM; model jen z tohoto závodu (měřicí účet), viz část 12 |

Největší odchylky (kladné číslo: kategorie potřebuje víc času, než odpovídá modelu, model je optimistický):

| Závod | Úsek | Model | Reference | Odchylka | Co za tím nejspíš je |
|---|---|---|---|---|---|
| Pohora | 16–F | 0:28 | 0:07 | −78 % | doběh: reference 7 s je kratší než přesnost; nezajímavé |
| Pohora | S–1 | 0:41 | 1:18 | +63 % | první kontrola, čtení mapy po startu |
| Pohora | 8–9 | 1:40 | 2:48 | +44 % | neznámé; stojí za pohled do mapy |
| Petřvald | 13–14 | 1:28 | 2:34 | +72 % | neznámé; i ty jsi tam podle GPS zpomalil před kontrolou |
| Petřvald | 2–3 | 3:19 | 2:21 | −30 % | **chyba čtení mapy**: silnice přečtená jako budova, postup ji obcházel. Opraveno 7. 10. odpoledne (část 12), úsek už mezi odchylkami není |
| Petřvald | S–1 | 1:21 | 1:56 | +42 % | první kontrola |

Co z toho plyne: model řadí úseky jako kategorie (0,93 a 0,94; po opravě čtení terénu u Petřvaldu 0,95). Kontrola dělá, co má: úsek 2–3 na Petřvaldu označila jako pesimistický a příčina je skutečná chyba. U Petřvaldu je kategorie malá (5 běžců), čísla jsou hrubá. Pro Azymut mezičasy nemáme.

Stejná tabulka je v aplikaci na záložce „Mezičasy kategorie“ u každého závodu s nejlepšími postupy.

## 3. Výškopis: ČÚZK DMR 5G proti AWS

Měřítko je barometr hodinek (vyhlazený přes 15 s) podél stopy; po odečtení posunu.

| Závod | Zdroj | Odchylka výšek (RMS) | Stoupání po 50 m | Chyba sklonu (RMS) | Korelace sklonu s barometrem |
|---|---|---|---|---|---|
| Petřvald | AWS | 5,7 m | 231 m | 6,2 % | 0,57 |
| Petřvald | ČÚZK, vyhlazení 10 m | **2,3 m** | 298 m | **2,6 %** | **0,94** |
| Petřvald | barometr | | 279 m | | |
| Pohora | AWS | 8,0 m | 110 m | 4,2 % | 0,57 |
| Pohora | ČÚZK, vyhlazení 10 m | **3,5 m** | 96 m | **2,1 %** | **0,88** |
| Pohora | barometr | | 95 m | | |

ČÚZK je jednoznačně lepší. Průměrný sklon terénu na mapě Petřvaldu vychází 7,3 % z AWS a 11,8 % z ČÚZK (před vyhlazením): AWS terén zahlazuje.

Vyhlazení: na syrové mřížce 2 m dává sčítání po 2 m (tak se oceňují postupy) podél stopy 409 m stoupání proti 279 m z barometru, s vyhlazením 10 m 355 m, s 25 m 300 m. Zvolil jsem 10 m: nejlepší shoda výšek, a ještě zůstanou rokle.

Poučení: služba vrací pixely čtvercové ve stupních a výřez si rozšíří. První verze, která to nečekala, měla na Petřvaldu RMS 13 m a korelaci sklonu 0,14, tedy horší než AWS. Kód teď čte rozsah ze značek GeoTIFF a odmítne odpověď, která mapu nepokrývá.

## 4. Zakázané přechody: Petřvald 14–15

| | Nejlepší postup 14–15 | Délka |
|---|---|---|
| dřív, bez železnice | 8:45 | 1 280 m, rovně přes koleje |
| se železnicí z OSM (zakázáno), stejný model, výškopis ČÚZK | 10:59 | 1 521 m, přes přejezd |
| ve webu (tvůj model, ČÚZK) | 10:07 | |
| kategorie: reference / nejlepší mezičas | 11:22 / 10:43 | |

OSM má na mapě Petřvaldu 2 úseky železnice a 3 průchody. Test kontroluje, že žádný nejlepší postup ani alternativa nekříží koleje dál než 25 m od průchodu.

Ploty z OSM (46 úseků) se stahují, ale nepoužívají. Původně jsem je zapnul a pak jim mylně přičetl okliku na úseku 2–3; po vypnutí oklika zůstala (příčina je v bodě 2). Jestli ploty pomáhají, nevím.

## 5. Kontroly nejlepších postupů

Rychlé testy na umělém terénu (`tests/test_routing.py`): nejlepší postup není pomalejší než 20 náhodných čar; cesta kolem zelené; do kopce dráž než z kopce; zakázanou čáru jen přejezdem; těžko překonatelná čára stojí 60 až 130 s; alternativa vede druhou stranou jezera a její čas je skutečný; při posunu rychlosti terénu o 20 % se dva postupy proti sobě pohnou.

Na závodech (vyhodnoceno nad spočítanými analýzami, viz `co-zbyva.md`):

| Kontrola | Výsledek |
|---|---|
| nejlepší postup ≤ běžená stopa oceněná stejným modelem (× 1,05 + 15 s) | 70 ze 71 úseků; výjimka Petřvald 2–3 (silnice jako budova) |
| ztráta volbou + ztráta provedením = celková ztráta | všechny úseky |
| alternativa není zřetelně rychlejší než nejlepší postup | všechny |
| úseků s aspoň jednou alternativou | E5 8 ze 13, Day 4 17 z 21, Pohora 9 ze 17, Petřvald 16 z 20 |
| úseků označených „postupy jsou vyrovnané“ | E5 1 (8–9), Day 4 3 (10–11, 15–16, 16–17), Pohora 1 (1–2), Petřvald 0 |

## 6. Umístění mapy bez KMZ

Zapomenu georeferenci KMZ z Livelox, najdu ji znovu z obrázku, tvé stopy a oficiálních časů ražení a porovnám.

| Závod | Kontrol spárováno | Odchylka na kontrolách (RMS) | Chyba v rozích a středu mapy | Měřítko |
|---|---|---|---|---|
| Pohora | 16 ze 16 | 12,8 m | 2 až 15 m | 1,324 proti 1,330 m/px |
| Petřvald | 19 z 19 | 10,4 m | 4 až 19 m | 0,586 proti 0,590 m/px |

Odchylka kolem 10 m je chyba GPS v okamžiku ražení; mapa jako celek sedí líp, protože se chyby na 16 až 19 kontrolách průměrují. Ověřeno jen na obrázcích z Livelox; sken nebo fotka mohou dopadnout hůř.

## 7. Typ chyby u kontroly

Co pravidla našla (úseky s odhadem ztráty z GPS aspoň 40 s):

| Závod | Úsek | Ztráta | Typ | Čísla |
|---|---|---|---|---|
| E5 | 3–4 | 5:50 | přeběhnutí | minul o 38 m, dál 89 m, návrat 260 s |
| E5 | 5–6 | 11:27 | přeběhnutí | minul o 28 m, dál 164 m, návrat 456 s |
| E5 | 6–7, 7–8 | 1:04, 1:43 | nedoběhnutí | stání 16 až 17 s asi 100 až 125 m před kontrolou |
| E5 | 8–9 | 14:12 | úhyb ze směru | až 205 m od spojnice |
| E5 | 9–10 | 2:24 | hledání v kruhu | 578°, 255 s |
| Day 4 | S–1, 3–4, 14–15 | 4:25, 4:45, 1:41 | hledání v kruhu | 362 až 853° |
| Day 4 | 4–5, 6–7, 13–14 | 1:05 až 5:35 | nedoběhnutí | |
| Pohora | 1–2 | 4:52 | hledání v kruhu | 648°, 281 s |
| Pohora | 2–3, 4–5 | 0:41, 6:00 | úhyb ze směru | 174 a 236 m od spojnice |
| Petřvald | 12–13, 13–14, 14–15 | 1:54, 1:04, 2:14 | nedoběhnutí | |
| Petřvald | 15–16 | 4:23 | nové určení polohy | stání 46 s, změna směru 139° |

Shoda s mezičasy kategorie (WinSplits, nezávislá na GPS): na Pohoře označil chybu na úsecích 1–2 a 4–5, na Petřvaldu na 15–16. Všechny tři má i klasifikace ze stopy (hledání v kruhu, úhyb, nové určení polohy).

Slabiny: „úhyb ze směru“ dostane i úsek, kde ses ztratil úplně (E5 8–9), a „nedoběhnutí“ dostane každé zpomalení 40 až 160 m před kontrolou, i když jsi jen četl mapu. **Prahy nejsou laděné proti tvým poznámkám**, protože žádná „ztráta kontaktu s mapou“ v databázi nebyla.

## 8. Model rychlosti: zkouška vynecháním závodu

Model se spočítá ze tří závodů a předpoví čisté úseky čtvrtého. Všechny varianty se hodnotí na stejných oknech po 15 s. „Celek“ je průměr absolutní chyby celkového času, „úseky“ průměrná chyba času úseku.

| Varianta | Celek | Úseky | E5 | Day 4 | Pohora | Petřvald |
|---|---|---|---|---|---|---|
| **po krocích (dosavadní, používá se)** | **6,0 %** | **19,2 %** | −9,1 | +6,3 | −2,1 | −6,7 |
| společný odhad v logaritmu, okno 1 krok, třída pod bodem | 7,0 % | 18,9 % | | | | |
| společný odhad, okna 15 s | 7,0 % | 19,7 % | | | | |
| společný odhad, okna 15 s, podíly tříd v okolí | 8,1 % | 19,1 % | | | | |
| … + příčný sklon | 6,0 % | 18,0 % | | | | |
| … + únava | 8,3 % | 20,6 % | | | | |
| … + příčný sklon + únava | 6,1 % | 19,8 % | | | | |

(Sloupce závodů jsou chyba celkového času v procentech u dosavadního modelu; pro ostatní varianty je vypíše `python tools/jointfit.py`.)

Závěry:

- **Společný odhad s hřebenovou penalizací sám nepomohl**: celek se zhoršil ze 6,0 na 7,0 až 8,1 %, úseky zůstaly stejné. Nechávám dosavadní model.
- **Příčný sklon** je jediný člen, který pomáhá: uvnitř společného odhadu sníží chybu úseků z 19,1 na 18,0 % a celku z 8,1 na 6,0 %. Koeficient vychází ve všech čtyřech pokusech kladný (0,9 až 2,0 na jednotku sklonu, tedy svah 10 % napříč znamená o 9 až 19 % pomalejší běh), takže jev je skutečný. Proti dosavadnímu modelu je ale zisk jen 1,2 bodu na úsecích a nic na celku, což je na čtyřech závodech v šumu. Zapojení by znamenalo přidat příčný sklon i do ceny hran při hledání postupu; nedělal jsem to.
- **Únava** (pokles tempa s časem závodu) chybu zvýšila. Koeficient vychází kolem nuly (−0,06 až +0,13 za hodinu).
- **Obtížnost závodu z mezičasů** jde spočítat jen u dvou závodů; test z toho udělat nejde.
- **Klubový prior** s jedním běžcem ověřit nejde; je napsaný a vypnutý.
- **Výškopis** pro tuhle zkoušku byl AWS u všech čtyř závodů (aby byla opakovatelná bez sítě). S ČÚZK se vzorky českých závodů změní a zkoušku stojí za to zopakovat.

Nejistota činitelů terénu na stránce modelu (jedna směrodatná odchylka, ukázkový účet se čtyřmi závody): les 5 % (2 488 s dat), zelená, světle zelená a cesta 12 % (340 až 520 s), hrubá louka a podrost 16 % (kolem 210 s), louka, bažina a tmavě zelená 21 až 23 % (33 až 68 s), terén bez dat 25 % (nejistota výchozí hodnoty ISOM).

## 9. Celý Garmin export (soukromá data, nejsou v repozitáři)

Složku `private/Garmin` jsem zabalil do zipu mimo repozitář a nahrál ve vývojovém prostředí.

| | |
|---|---|
| souborů `.fit` v exportu | 10 074 |
| z toho uloženo jako běh nebo podobná aktivita | 257 (účet jich z dřívějška měl 261) |
| model kopců | 164 běhů, 1 383 oken do kopce, `up_k` 3,4 (stejně jako v README) |
| závodů v účtu / spárováno | 107 / 31 (20 jistých, 7 pravděpodobných, 4 nejisté) |
| rozhodla poloha | 2× „vybrána aktivita, která začíná u centra závodu“; 1× „aktivita začíná 16 km od centra“ (nejistá) |
| po zpracování | zůstalo 29 běhů spárovaných se závody, 232 smazáno, zip smazán |

## 10. Zakázané prostory ze šrafování mapy (doplněno 7. 10. 2026)

`oroute/hatch.py` na čtyřech mapách s tratí z `data/`:

| Mapa | Rozlišení | Nalezených buněk šraf | Ploch | Čas čtení |
|---|---|---|---|---|
| Azymut E5 | 1,33 m/px | 0 | 0 | 0,3 s |
| Azymut Day 4 | 1,33 m/px | 0 | 0 | 0,4 s |
| Pohora | 1,33 m/px | 1 | 0 | 0,2 s |
| Petřvald H18 | 0,59 m/px | 152 | 7 | 10 s |

Na Petřvaldu je to pět šrafovaných polí a silnice podél jižního okraje mapy (ta vyšla ve dvou kusech, které na sebe navazují), dohromady asi 5,8 ha; strana buňky 15,4 m. Zkontrolováno pohledem do mapy: nic nechybí a nic nepřebývá. Okraj plochy je asi o půl buňky (7 m) nepřesný, protože krajní buňky šrafování nejsou uzavřené.

Vliv na postupy Petřvaldu (stejný model, výškopis ČÚZK, železnice z OSM; šrafy zapnuté proti vypnutým):

| Úsek | Se zákazem | Bez zákazu |
|---|---|---|
| 1–2 | 3:06, 496 m | 3:04, 495 m |
| 4–5 | 4:46, 808 m | 4:43, 788 m |

Ostatních 18 úseků se nezměnilo: nejlepší postupy šrafovanými poli nevedly ani předtím. Pomalý test hlídá, že žádný nejlepší postup ani alternativa plochou nevede.

Co z toho plyne: na téhle mapě je přínos malý (dva úseky o 2 až 3 s). Jistota je jen z jedné mapy se šrafami; na mapě s jiným rozlišením je čtení ověřené jen na kresleném obrázku v testu (`tests/test_hatch.py`, 1,33 m/px, buňka 8,5 m).

## 11. Rychlost analýzy (měřeno 7. 10. 2026)

Petřvald přes frontu webu: nový závod nového účtu, výškopis z uložených dlaždic AWS, bez OpenStreetMap, jeden pracovní proces, nic jiného při tom nepočítalo. Jedno měření každého stavu.

| | Kód `main` | Úprava úlohy | K tomu rychlejší čtení trati |
|---|---|---|---|
| Stopa, mezičasy a typy chyb na stránce | za 4:37 | za 2:30 | za 0:34 |
| Nejlepší postupy hotové | za 6:22 (dvě úlohy: 277 s a 105 s) | za 4:48 (jedna úloha) | za 2:51 (jedna úloha) |
| Složka výstupů | 32,8 MB | 3,6 MB | 3,6 MB |

„Úprava úlohy“: výsledek `analyze.py` se ukládá hned, osobní model se přepočítá před hledáním postupů (`bestroute.py --samples-only`), takže se postupy hledají jednou, a skripty nekreslí obrázky (`--no-images`). „Rychlejší čtení trati“: `oroute/course.py` sčítá hlasy pro středy kružnic přes `np.bincount` a pořadí kontrol skládá po vrstvách v numpy.

Kde byl čas: profil `analyze.py` na Petřvaldu ukázal 157 s, z toho 76 s skládání pořadí 19 kontrol smyčkami v Pythonu a 62 s hledání kružnic (50 s v `np.add.at`). Po úpravě trvá čtení trati v úloze 33 s místo 149 s. Výsledky jsou stejné: `legs.csv` a `course.json` všech čtyř závodů bajtově shodné se zlatými soubory.

Z čeho se skládá necelých 3 minut teď: čtení trati z mapy 33 s, šrafování 13 s, čtení terénu a výškopis pro vzorky modelu 26 s, přepočet modelu a druhé čtení terénu 28 s, postupy 20 úseků 72 s.

Co z toho plyne a neplyne: Petřvald má ze čtyř závodů největší mapu (0,59 m na pixel) a 19 kontrol; Azymut E4 má kontrol 20, ale mapu menší. Ostatní tři jsem přes frontu neměřil; samotné `analyze.py` na nich teď trvá 6 až 10 s. Pomalé testy trvaly před úpravami asi 25 minut, po nich 7 minut 27 sekund.

Po opravě čtení terénu a s uloženým terénem (jedno měření, stejné podmínky): stopa na stránce za 0:35, postupy hotové za 2:59. Čtení terénu trvá na Petřvaldu 37 s místo 25 s (větší značky znamenají větší okna filtrů), ale čte se už jen jednou na závod, ne dvakrát v každé úloze; hledání postupů 84 s místo 72 s. Druhá analýza téhož závodu (jiný běžec, změna zakázané čáry) terén nečte vůbec.

## 12. Čtení terénu podle rozlišení mapy (7. 10. 2026)

`oroute/terrain.py` násobí velikosti značek v pixelech poměrem 1,33 / rozlišení mapy. Tři mapy mají 1,33 m na pixel a jejich výsledky se nezměnily (zlaté soubory shodné). Petřvald má 0,59 m na pixel:

| Petřvald | Dřív | Teď |
|---|---|---|
| Podíl plochy čtený jako budova | 3,6 % | 1,0 % |
| Podíl plochy čtený jako cesta | 3,4 % | 6,8 % |
| Úsek 2–3, nejlepší postup | 3:41, 504 m (oklikou kolem silnice) | 2:16, 351 m |
| Úsek 10–11, nejlepší postup | 8:44, 1202 m | 6:22, 984 m |
| Úsek 15–16, nejlepší postup | 3:27, 524 m | 2:39, 423 m |
| Součet nejlepších postupů | 59:01 | 53:05 |
| Shoda pořadí úseků s kategorií (Spearman) | 0,87 | 0,95 |

Čísla v tabulce jsou ze skriptů (výškopis AWS, bez železnice, model `oroute/personal_model.json`), tedy ze stejných podmínek jako zlaté soubory. Referenční časy kategorie: 2–3 2:21, 10–11 6:41, 15–16 2:42; nejlepší postupy na těch třech úsecích jsou teď 2:16, 6:22 a 2:39. V nastavení webu (ČÚZK, železnice z OSM) vyšla shoda 0,95 a rozptyl 11 % proti 0,93 a 15 % z noci; model v tom měření byl ale jen z Petřvaldu samotného, kdežto noční číslo je s modelem ze čtyř závodů, takže rozdíl nejde celý připsat opravě.

Co z toho plyne: tři úseky, které se v noci jevily jako pesimistické (2–3, 10–11, 15–16), měly stejnou příčinu a po opravě sedí na referenci kategorie do pár procent. Největší zbylá odchylka je 13–14 (model 1:26, reference 2:34), jako předtím. Jistota je z jedné mapy s vysokým rozlišením. Vedlejší účinek: železnice se čte jako cesta, ne jako řada budov (viz `co-zbyva.md`).

## 13. Pořadí kontrol z oficiálních časů a hledání pro dlouhé tratě (7. 10. 2026)

- Pohora (16 kontrol) a Petřvald (19): pořadí z poloh v oficiálních okamžicích ražení je stejné jako pořadí ve zlatých `course.json` z čar a stopy; medián vzdálenosti stopy od koleček v těch okamžicích pod 25 m, rozdíl hodin do 10 s. `course.json` z `analyze.py --official` je bajtově shodný se zlatým.
- Umělé tratě (`tests/test_course.py`): 30 náhodně rozmístěných kontrol spojených čarami, z toho několik leží na čáře cizího úseku; přibližné hledání najde správné pořadí za necelé 4 s. Na 9 kontrolách dává totéž co přesná tabulka. S šesti chybějícími čarami z 27 skončí a vrátí každou kontrolu jednou (správnost pořadí tam hlídá až stopa).
- Na skutečné mapě s víc než 20 kontrolami změřeno není nic.

## 14. Záchytné body u kontrol a bloudění (`oroute/relocate.py`, 7. 10. 2026 večer)

*Tahle část popisuje první verzi. Náběhový bod, zarážka, konce cest, oplocenky a bodové značky jsou z 8. 10. a čísla k nim jsou v části 16.*

Čtyři závody z `data/` analyzované přes web ve vývojovém prostředí (osobní model ze všech čtyř, výškopis `auto`: ČÚZK pro Pohoru a Petřvald, AWS pro Azymut). Skript ke každé kontrole kreslí výřez mapy se vším, co našel (`--debug SLOŽKA`); podle těch obrázků jsem prošel deset kontrol.

| Závod | Kontrol | Se 2 až 4 body | S jedním | Bez bodu | S náběhovým bodem | Bloudění podle stopy |
|---|---|---|---|---|---|---|
| Azymut E5 | 12 | 12 | 0 | 0 | 10 | 3–4, 5–6, 6–7, 8–9, 9–10 |
| Azymut E4 | 20 | 19 | 0 | 1 | 18 | S–1, 3–4, 13–14, 14–15 |
| Pohora | 16 | 16 | 0 | 0 | 15 | 1–2, 4–5 |
| Petřvald | 19 | 16 | 1 | 2 | 17 | žádné |

Co bylo mezi vybranými body (všechny čtyři závody): křížení cest 119×, cesta 41×, paseka 32×, vodoteč 15×, cesta přes vodoteč 8×, okraj otevřené plochy 6×, vodní plocha 2×, budova 2×, kupa 0×. Výpočet trvá 6 až 9 s na závod s mapou 1,33 m na pixel a 23 s na Petřvaldu.

Kontroly prošlé podle obrázku mapy:

| Kontrola | Co vyšlo | Sedí s mapou? |
|---|---|---|
| E5, 4 (úsek 3–4) | rybník 99 m na sever, křížení cest 71 m na JV, cesta přes potok 79 m na JZ, potok 44 m | Ano, všechny čtyři jsou na mapě tam, kde mají být. První verze měla místo potoka „okraj hustníku“ uprostřed zelené. |
| E5, 1 (S–1) | paseka 104 m na SZ, potok 55 m na SV, cesta 45 m na JZ | Ano. Potok vedený bažinou první verze nenašla (viz níže). |
| E5, 6 (5–6) | tři křížení cest, potok 48 m | Křížení jsou skutečná, ale na jihu je jich na 100 m šest; vybrané nejsou ničím zvláštní. Bloudění: přímý směr opuštěn 43 m před kontrolou, pak skoro 10 minut a 700 m navíc severně od ní; sedí se stopou. |
| E5, 11 (10–11) | křížení cest 101 m na sever, „paseka“ 80 m na západ, silnice 60 m, okraj pole 129 m | Křížení, silnice a pole ano; „paseka“ je roh pole mezi silnicí a lesem, název nesedí. V první verzi silnice chyběla, protože ležela stejným směrem jako křížení. |
| E4, 3 (2–3) | čtyři křížení cest | Všechna jsou na mapě; jedno je v pravidelné síti průseků, kde jich je vedle sebe deset stejných. |
| E4, 14 (13–14) | křížení cest 99 m na SZ (náběh), křížení 116 m na východ, paseka 98 m, křížení 50 m na JZ | První tři ano. Čtvrté je roh pole ohraničeného tenkou černou čarou, ne křížení cest: v terénu se najít dá, ale název nesedí. |
| Pohora, 2 (1–2) | paseka 88 m, křížení cest 146 m na JZ, cesta 78 m, potok 110 m | Křížení, cesta a potok ano. Paseka je malá světle žlutá ploška mezi zelenými šrafami; první verze nabízela dvě „paseky“, které byly jen kusy velké polootevřené plochy. |
| Pohora, 10 (9–10) | paseka 88 m na SV, silnice 116 m na východ, „paseka“ 147 m na JZ, potok 25 m na jih | Paseka na SV, silnice a potok ano. Druhá „paseka“ leží v mozaice polootevřeného; po zpřísnění zůstala, je sporná. Silnici a potok první verze nevybrala. |
| Petřvald, 3 (2–3) | křížení cesty se silnicí 109 m na západ, křížení 110 m na SZ, budova 137 m na SV, paseka 67 m na SZ | Ano. Budova stojí v soukromém pozemku (zakázaný prostor): je vidět, dojít k ní nejde. |
| Petřvald, 18 (17–18) | nic | Správně: do 150 m jsou jen vrstevnice, kupky a hranice porostu; nejbližší cesta je 156 m daleko. |

Co bylo špatně a jak to dopadlo:

- **Okraje hustníků** vycházely na mapách s hodně zelenou jako bod uprostřed ničeho (nejbližší pixel velké zelené plochy). Vyřazeno úplně, neukazují se.
- **Paseky v mozaice polootevřeného** (Pohora): kusy velké světle žluté plochy vycházely jako samostatné paseky. Teď je paseka jen souvislá otevřená plocha 200 až 4000 m², kompaktní a celá uvnitř výřezu; „okraj otevřené plochy“ jen u ploch od 1 ha. Sporné případy zůstávají (Pohora 10).
- **Potok vedený bažinou** se nenašel, protože se bažina z modré odečítala. Teď se berou souvislé modré čáry od 60 m délky; čárky bažiny jsou krátké a nespojité, takže vypadnou samy.
- **Dva body stejným směrem**: druhý bod stejného druhu ve stejném směru (do 45°) se nevybere, bod a čára stejným směrem zůstanou oba (silnice a křížení na ní).
- **„Křížení cest“ je křížení černých čar mapy.** Cesta, průsek, plot i hranice pole jsou na mapě černě a z barvy je rozlišit nejde; stránka to u bodů píše. Ramena křížení musí pokračovat aspoň 21 m, takže značky (skalky, kupky s čárkami) křížení nedělají.
- **Kupy z výškopisu** nevyšly na čtyřech závodech ani jednou (pravidlo: vrchol, kolem kterého je ve vzdálenosti 45 m všechno aspoň o 3 m níž, u AWS o 6 m). Pravidlo je ověřené jen na umělém terénu v testu; je přísné schválně.
- **Hustý les a husté sítě cest** (E5 kontrola 6, E4 kontrola 3): body jsou skutečné, ale je jich v okolí tolik stejných, že se podle nich poloha neurčí. Nevyřazuji je; chtělo by to měřit, jak je bod v okolí jedinečný.

Co ověřeno není: jestli by se těch bodů běžec v terénu opravdu chytil (to řekne jen Tobias nad mapou), popisy kontrol (nepoužívají se), azimuty proti buzole (počítají se k severu obrázku mapy, tedy k magnetickým poledníkům, zaokrouhlené na 5°), a bloudění proti poznámkám „ztráta kontaktu s mapou“ (žádné v datech nejsou). Bloudění se pozná u 11 z 20 úseků, kterým `oroute/mistakes.py` dal typ chyby; zbylých devět jsou hlavně „nedoběhnutí“ a „úhyb ze směru“, kde běžec stál nebo běžel vedle, ale nenaběhal u kontroly 60 m navíc.

## 15. Testy na větvi `co-chybi` (7. 10. 2026 večer)

- Rychlé testy: 159, asi minuta. Pomalé: 36 za 10:02 (čtyři závody skripty i přes web, na počítači nic dalšího neběželo). Zlaté soubory `tests/golden` se neměnily: `bestroute.py` se změnil jen tím, že čtení terénu, výškopisu a zakázaných čar převzal `oroute/mapdata.py`.
- Analýza přes web má o krok víc (záchytné body, 6 až 23 s na závod) a čtení šraf z mapy s tratí hledá i svislé čáry (Petřvald 22 s místo 12 s, jednou na nahranou mapu).
- Ocenění plánovaného postupu na skutečném závodě hlídá pomalý test (`test_notes_change_the_loss_and_the_model`: čára nakreslená k úseku 7–8 Azymutu E5 dostane čas, délku a větu).
- Svislé šrafování na čtyřech mapách s tratí z `data/`: žádný nález; křížové na Petřvaldu 7 ploch (1 173 až 20 614 m²), stejně jako před změnou.

## 16. Náběhový bod před kontrolou, zarážka za ní a značky podle ISOM 2017-2 (8. 10. 2026)

Proč: na Petřvaldu u úseku 13–14 stránka nabízela „náběhový bod: křížení cest 68 m“ za kontrolou, a byl to konec cesty; u 14–15 bylo „křížení cest“ rohem oplocenky. Příčiny byly dvě:

- Petřvald v Tobiasově instalaci byl spočítaný kódem ze 7. 10. ráno a stránka ukazovala starý návrh z `bestroute.py` (nejbližší křížení do 200 m, na směr nehledí). Že je rozbor starý, stránka nepoznala. Teď má výpočet záchytných bodů číslo verze (3) a rozbor bez něj nebo se starším dostane pruh s tlačítkem „Přepočítat záchytné body“; starý návrh se neukazuje.
- Ani nový kód neznal konec cesty, oplocenku a bod za kontrolou a směr příchodu bral jako přímku od minulé kontroly.

Čtyři závody z `data/` ve vývojovém prostředí, konečný kód:

| Závod | m na pixel | Kontrol | Se 2 až 4 body | S náběhovým bodem | Se zarážkou (z toho linie) | Bloudění | Výpočet |
|---|---|---|---|---|---|---|---|
| Azymut E5 | 1,33 | 12 | 12 | 10 | 12 (9) | 5 | 7 s |
| Azymut E4 | 1,33 | 20 | 20 | 20 | 20 (15) | 4 | 9 s |
| Pohora | 1,33 | 16 | 16 | 16 | 16 (11) | 2 | 7 s |
| Petřvald | 0,59 | 19 | 19 | 19 | 19 (9) | 0 | 35 s (úloha ve webu 34 s) |

Vybrané záchytné body dohromady: křížení cest 116×, konec cesty 54×, cesta 19×, paseka 15×, vodoteč 13×, cesta přes vodoteč 7×, kupka 7×, výrazný strom 6×, okraj otevřené plochy 5×, oplocenka 5×, vodní plocha 2×, budova 2×, prohlubeň 2×, okraj zakázaného prostoru 2×, výrazný terénní objekt 2×, jáma, jáma s vodou a posed po jednom; vrchol z výškopisu ani jednou. Náběhové body: křížení 35×, konec cesty 14×, paseka 7×, strom 3×, kupka 3×, rybník, cesta přes vodoteč a oplocenka po jednom, žádný 2×. Zarážky: cesta 37×, konec cesty 8×, vodoteč 4×, paseka 4×, křížení 3×, okraj otevřené plochy 3×, strom 2×, kupka 2×, rybník, posed, oplocenka a terénní objekt po jednom.

### Dvanáct kontrol podle obrázku mapy

Výřezy kreslí `python -m oroute.relocate … --debug SLOŽKA` (náběhový bod zelený čtverec, zarážka oranžový, konec nejlepšího postupu modře, oplocená plocha fialově).

| Kontrola | Co vyšlo | Sedí s mapou? |
|---|---|---|
| Petřvald 14 (13–14) | náběh kupka 44 m na azimut 170°, zarážka konec cesty 69 m na azimut 300°; dál křížení 110 m a druhá kupka 97 m | Ano. Kupka leží na nejlepším postupu před kontrolou. Konec přerušované pěšiny za kontrolou je to místo, kterému stará verze říkala „křížení cest 68 m“. Kontrola sama stojí na hnědém trojúhelníku (115); ten je blíž než 30 m, takže se mezi body neukazuje. |
| Petřvald 15 (14–15) | náběh konec cesty 56 m na azimut 165°, zarážka oplocenka 47 m na azimut 70°; dál křížení 88 m, vodoteč 102 m | Ano. Oplocenka je plocha s čárkami dovnitř hned za kontrolou; stará verze její roh nazvala křížením. „Křížení 88 m“ je místo, kde cesta dojde k plotu zástavby. Dvě menší oplocené zelené plošky dál od kontroly se nepoznaly. |
| Petřvald 13 (12–13) | náběh oplocenka 74 m (nejlepší postup vede podél ní), zarážka cesta 33 m; dál konec cesty 74 m, kupka 80 m, jáma s vodou 119 m | Ano, po dvou opravách: nejdřív vyšlo „křížení cest 132 m“ v nadpisu legendy vedle mapy a silnice za kontrolou jako „okraj otevřené plochy“. |
| Petřvald 9 (8–9) | náběh konec cesty 135 m, zarážka posed 76 m; dál křížení 102 m, křížení 126 m, strom 111 m, kupka 75 m | Posed, strom, kupka a první křížení ano. Druhé „křížení“ je roh plotu zakázaného prostoru. |
| Petřvald 6 (5–6) | náběh výrazný strom 93 m na nejlepším postupu, zarážka konec cesty 46 m; dál křížení 84 m, křížení 109 m, okraj zakázaného prostoru 64 m | Ano. Křížení 109 m je křížení ulic uvnitř zástavby: vidět je, dojít k němu nejde. |
| Petřvald 18 (17–18) | náběh křížení 153 m, zarážka výrazný terénní objekt 71 m; dál křížení 143 m, posed 122 m, cesta 132 m, prohlubeň 119 m | Značky ano (první verze tu nenašla nic). Náběhové „křížení“ je místo, kde se k cestě připojuje zelená čárkovaná hranice porostu: název nesedí. |
| Pohora 5 (4–5) | náběh křížení 107 m (cesta přes potok, na nejlepším postupu), zarážka okraj otevřené plochy 30 m; dál křížení 105 m, konec cesty 68 m, oplocenka 90 m | Ano. Dvě další oplocené louky na severovýchodě se nepoznaly (jednu kříží vrstevnice, druhá je u okraje mapy), jejich rohy jsou mezi kandidáty jako křížení. |
| Pohora 8 (7–8) | náběh výrazný strom 52 m, zarážka cesta 120 m; dál křížení 126 m, paseka 41 m, dva konce cest | Ano. |
| E5 8 (7–8) | náběh konec cesty 54 m, zarážka konec cesty 72 m; dvě křížení kolem 110 m | Ano, oba jsou konce krátkých pěšin. |
| E5 4 (3–4) | náběh rybník 99 m, zarážka cesta 36 m; dál křížení 50 m, cesta přes vodoteč 84 m, vodoteč 44 m | Ano, stejné body jako v první verzi a k nim cesta za kontrolou. |
| E4 14 (13–14) | náběh křížení 90 m na azimut 315°, zarážka cesta 24 m (hrana pole) | Zarážka ano. Náběhový bod leží 69° stranou od směru příchodu, tedy na hraně povoleného úhlu 70°; křížení 113 m na severovýchodě by bylo lepší. |
| E4 5 (4–5) | náběh konec cesty 51 m na nejlepším postupu, zarážka cesta 132 m | Ano. |

U všech dvanácti leží náběhový bod před kontrolou a zarážka za ní. Název nesedí nebo je sporný u čtyř bodů z asi šedesáti prohlédnutých: dvakrát plot zástavby jako rameno „křížení cest“, jednou hranice porostu, jednou hrana pole jako „cesta“.

### Bodové značky (`oroute/symbols.py`)

Pravidlo z plánu: druh značky se ukazuje, jen když na prohlédnutých výřezech sedí aspoň devět nálezů z deseti. Petřvald (0,59 m na pixel), u každého druhu až 24 nálezů rovnoměrně z celé mapy, 20 m kolem každého:

| Značka (ISOM 2017-2) | Nálezů | Prohlédnuto | Správně |
|---|---|---|---|
| 109 kupka | 91 | 24 | 24 |
| 111 prohlubeň | 66 | 24 | 24 |
| 417 výrazný strom | 42 | 12 | 12 |
| 112 jáma | 28 | 24 | 24 |
| 115 výrazný terénní objekt | 19 | 19 | 19 |
| 525 posed | 8 | 8 | 8 |
| 530, 531 umělý objekt | 6 | 6 | 6 (pět křížků, jeden kroužek) |
| 204 balvan | 2 | 2 | 2 |
| 311 studna nebo nádrž | 2 | 2 | 2 |
| 303 jáma s vodou | 2 | 2 | 2 |

Z map s 1,33 m na pixel se čte jen kupka a výrazný strom (tečka tam má pět pixelů, V šest): E5 kupka 9 z 9 a strom 1 z 1, E4 kupka 3 ze 4 (čtvrtá je větší tečka v řadě menších teček, sporná), Pohora kupka 12 z 12 a strom 12 z 12. Všech deset druhů tedy pravidlem prošlo.

Kupku, jámu, terénní objekt a strom na Petřvaldu jsem prohlížel před posledním zpřísněním pravidel; to nálezy jen ubírá a počty těchto druhů se jím nezměnily.

Co se cestou muselo opravit (všechno nalezeno na přehledových listech nálezů):

- domy a písmena legendy jako balvan nebo umělý objekt: bere se jen skutečná černá mapy (šedý tisk ne), tečka musí být kruh, značka nesmí stát v řadě s jinými stejně vysokými (písmena) ani v zakázaném prostoru (domy);
- stromy sadu jako „výrazný keř“ (418): druh zrušen, nečte se;
- čárky přerušované cesty jako křížek, šipka jiné značky jako T: křížek musí mít barvu ve všech čtyřech rozích, T příčku přes celou šířku;
- kousky vrstevnice mezi dvěma cestami jako kupka: hnědá tečka nesmí sousedit s černou;
- malé hnědé tečky (řady teček) jako kupka na hrubé mapě: kupka má aspoň 6 m.

Kolik značek mapy se nenašlo, změřeno není. Značka, která se dotýká vrstevnice, cesty nebo jiné značky, se nenajde nikdy; to je záměr (falešný bod je horší než chybějící).

### Oplocenky, konce cest, šedý tisk, silnice

- **Oplocenka** je plocha uzavřená černou čarou, která má aspoň dvě krátké čárky dovnitř. Nalezeno: E5 3, E4 4, Pohora 3, Petřvald 8; všech 18 je na listech skutečně oplocená plocha. Nenalezené jsem viděl čtyři (dvě u kontroly 15 na Petřvaldu, dvě u kontroly 5 na Pohoře). Pokus číst čárky volněji jich na Petřvaldu našel 16 místo 8, ale mezi nimi znak v rohu mapy a proužky mezi domy; vrátil jsem to.
- **Plot, který nic neuzavírá**, zůstává cestou. Obecné čtení plotu podle čárek dávalo ploty z přerušovaných cest, proto není.
- **Konec cesty**: první pokus hlásil konec u každé mezery přerušované pěšiny; čárky se teď spojují a konec je jen tam, kde do 12 m žádná černá čára nepokračuje.
- **Šedý tisk kolem mapy** (legenda, kód Livelox) terén čte jako cesty a budovy. Na Petřvaldu má 18 takových „cest“ a 71 „budov“ podíl černé mapy pod 0,05, všechny ostatní čáry a domy čtyř map 0,05 a víc (na Petřvaldu od 0,2). Hranice je 0,01; „křížení cest“ v nadpisu legendy u kontroly 13 tím zmizelo.
- **Silnice a zpevněná plocha** (světle hnědá, 501 a 502) se čte jako otevřená plocha, protože se po ní běží stejně rychle; mezi záchytnými body už jako otevřená plocha není a zarážkou je její černá krajnice („cesta“).
- **Cesta přes louku** dělila louku na kusy a vycházela jako její okraj; černá cesty teď patří k louce.

Co jsem zkusil a nevzal: vážit náběhový bod úhlem od směru příchodu a vyřadit z cest tmavě zelené čárky hranice porostu. Dohromady to změnilo 14 kontrol a na hrubých mapách ubralo skutečná křížení v hustnících; obojí vráceno, případy E4 14 a Petřvald 18 proto zůstávají.

Rychlost: Petřvald trval s novými pravidly 85 s. Rozšiřování a uzavírání masek kotoučem jde teď přes vzdálenost k nejbližšímu pixelu (stejný výsledek, ověřeno proti `scipy` na náhodných maskách, a stejné výstupy čtyř závodů): 35 s.

Co ověřeno není: jestli se těch bodů dá v terénu chytit a jestli by se běžec na zarážce opravdu zastavil; tvary značek proti kresbám v PDF (z PDF jsem přečetl jen čísla a názvy, kreslit ho nebylo čím); mapy v jiném měřítku a s jinými barvami než čtyři z `data/`; sprintové mapy.

### Testy

- Rychlé testy: 167, asi minuta a půl. Nové: `tests/test_symbols.py` (každý druh značky při 0,6 m na pixel, kupka a strom při 1,33; vrstevnice, čárky cesty, dům, tečky a písmena značky nedělají) a v `tests/test_relocate.py` konec cesty proti křížení, přerušovaná pěšina, oplocenka s čárkami a bez nich, zarážka paprskem, směr z nejlepšího postupu, šedý tisk, silnice. `tests/test_web_plans.py`: starý rozbor → pruh a žádný náběhový bod, úloha `relocate` body doplní, `beyond` v `data.json`.
- Pomalé testy (36, asi 11 minut): **na konečném kódu nedoběhly.** Pustil jsem je jednou na konci; po sedmi minutách je zastavil systém kvůli nedostatku paměti na počítači (ne kvůli testům) a znovu jsem je nepouštěl. Výsledek tedy není. Z pěti pomalých souborů se změn z 8. 10. týká jen `tests/test_web_pipeline.py` (analýza přes web pouští i `oroute.relocate`); ostatní (`test_regression.py`, `test_official_races.py`, `test_georef.py`, `test_hatch.py`) zkoušejí kód, na který jsem nesáhl, a zlaté soubory `tests/golden` jsou beze změny. Místo toho je ověřeno: `oroute.relocate` na všech čtyřech závodech z příkazové řádky a úloha `relocate` přes web na Petřvaldu a Pohoře ve vývojové instanci. Spuštění: `docker compose -p obdev -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps -T web pytest -m slow -q` (při něm nic jiného nepouštět, bere až 3 GB).
- V bezhlavém Chromu: panel úseku 13–14 Petřvaldu na 390 px bez vodorovného posuvníku, značky náběhového bodu a zarážky na mapě u úseku 14–15.

## 17. Voda s břehem, oplocenky v postupech, zarážka po výsecích, co stopa překročila (8. 10. 2026 večer)

Proč: čtyři nálezy z Petřvaldu v Tobiasově instalaci (data jsem jen četl, svazek připojený pro čtení).

| Nález | Příčina, dohledaná na datech |
|---|---|
| S–1: nejlepší postup vede rybníkem, možnost 2 oplocenkou | Rybník u jedničky má 8 m; voda se poznala jen od šířky 9 m, zbytek vyšel jako bažina a černá břehová čára jako cesta. Nejlepší postup měl 156 z 240 m „po cestě“ a ta cesta byl břeh. Plot oplocenky je černá čára, tedy také „cesta“, a hledání postupů o oplocenkách nevědělo. |
| 1–2: „běžený 3:01“, „nejlepší 3:18“ | Mezi kontrolami je železnice z OSM (výchozí „zakázáno“). Stopa ji kříží mimo přejezd, nejlepší postup musí k přejezdu u silnice. Stejný úsek bez zákazů: nejlepší postup 2:41 (418 m), přímka 2:47, stopa 3:01, naměřeno 3:35. Model rychlosti v tom není. |
| Zarážka u kontroly 2: „konec cesty 65 m“ | Bodový objekt bližší než linie měl přednost; byl to konec pěšiny, po které se ke kontrole přibíhá. |
| 2–3: náběhový bod | Záměna kontroly, beze změny. |

### Vodní plocha s břehovou čarou

Pravidlo: plná modrá plocha od 30 m², kolem které je prstenec černé. Měřeno pomocným skriptem na všech čtyřech mapách bez tratě (`data/`; modrá podle prahu barvy, ne přesně jako v `classify`), u každé plné modré plochy podíl černé v nejčernějším z prstenců širokých jeden pixel do vzdálenosti břehové čáry:

| Mapa | m na pixel | Modrých ploch od 30 m² | S prstencem od 0,8 | Nejvyšší podíl u ostatních |
|---|---|---|---|---|
| Petřvald | 0,59 | 95 | 10 (všechny 0,97 až 1,0) | 0,66 |
| Azymut E5 | 1,33 | 63 | 0 | 0,38 |
| Azymut E4 | 1,33 | 28 | 0 | 0,43 |
| Pohora | 1,33 | 14 | 0 | 0,48 |

Deset ploch Petřvaldu má černý břeh; po změně jsem na výřezu viděl dva z nich přečtené jako voda (u kontroly 1 a část sousedního), ostatní jen jako čísla. Na třech mapách z Livelox se nemění nic: rybník na E5 břehovou čáru nemá a čte se podle šířky jako dřív.

### Oplocenky a postupy

Neprůchodných oplocenek: E5 3, E4 4, Pohora 3, Petřvald 8 (stejné, které čte výpočet záchytných bodů; všech 18 skutečných, část 16).

Zlaté soubory po změně (`tests/make_golden.py`): `legs.csv` a `course.json` čtyř závodů a `best_legs.csv` tří závodů z Livelox jsou bajtově stejné. V `best_legs.csv` Petřvaldu se změnily čtyři úseky z dvaceti:

| Úsek | Nejlepší dřív | Teď | Co se stalo |
|---|---|---|---|
| S–1 | 1:24, 240 m, z toho 140 m „po cestě“ | 1:25, 233 m, 108 m | Postup už nevede po břehu rybníka. Zbylých 108 m „po cestě“ je plot s čárkami podél pole, který nic neuzavírá (známá výhrada). |
| 12–13 | 3:14, 475 m | 3:14, 478 m | Nejspíš oplocenka u kontroly 13, podél které postup vede; nedohledával jsem. |
| 15–16 | 2:39 | 2:38 | Rozdíl sekundy; příčinu jsem nedohledával. |
| 17–18 | 2:27, stopa 3:23 | 2:28, stopa 3:26 | Terén pod stopou i postupem se čte jinak; příčinu jsem nedohledával. |

Úloha analýzy Petřvaldu ve webu (jen postupy a záchytné body): 2 min 45 s s novým čtením terénu, 2 min 9 s s uloženým; ostatní tři závody 16 až 25 s. Jedno měření.

### Co stopa překročila

Na vývojové kopii (šrafy a železnice zapnuté): Petřvald 1–2 a 14–15 „kříží železnici mimo přechod“, jinde nic; ostatní tři závody zákazy nemají a jejich oplocenkami žádná stopa nevede. Na vývojové kopii je u 1–2 stopa 3:11 a nejlepší 3:23 (jiný osobní model než v Tobiasově instalaci).

### Zarážka po výsecích

Čtyři závody, vývojová kopie, konečný kód:

| Závod | Kontrol | Se třemi částmi | Se dvěma | S jednou | Bez zarážky | Nejbližší část, medián |
|---|---|---|---|---|---|---|
| Azymut E5 | 12 | 11 | 1 | 0 | 0 | 44 m |
| Azymut E4 | 20 | 18 | 2 | 0 | 0 | 34 m |
| Pohora | 16 | 13 | 2 | 1 | 0 | 44 m |
| Petřvald | 19 | 14 | 4 | 1 | 0 | 32 m |

Druhy částí dohromady: cesta 148×, vodoteč 15×, paseka 12×, okraj otevřené plochy 9×, vodní plocha 2×, oplocenka 2×. Náběhové body jako v části 16 (pravidlo se neměnilo; u několika kontrol jiný bod, protože se změnil nejlepší postup nebo dosažitelnost přes oplocenku).

Šest kontrol podle výřezu mapy (`--debug`, zásahy paprsků oranžově):

| Kontrola | Co vyšlo | Sedí s mapou? |
|---|---|---|
| Petřvald 2 (1–2) | vlevo cesta 15 m, rovně cesta 166 m, vpravo oplocenka 22 m | Oplocenka za kontrolou a pěšina vlevo ano: to je to, co Tobias nakreslil. Cesta východně od kontroly se do vějíře nevešla, protože nejlepší postup přichází od jihovýchodu (Tobias běžel od jihu). „Cesta 166 m“ je černý obrys úzké plochy, ne cesta. |
| Petřvald 15 (14–15) | vlevo cesta 56 m, rovně cesta 151 m, vpravo oplocenka 32 m | Oplocenka ano. „Cesta“ vlevo je černý obrys téže úzké plochy, rovně pěšina podél plotu zástavby. |
| Petřvald 14 (13–14) | vlevo cesta 81 m, rovně cesta 101 m, vpravo cesta 107 m | Ano: jedna pěšina napříč za kontrolou, vlevo krajnice silnice. Dřív „konec cesty 69 m“. |
| Petřvald 1 (S–1) | vlevo vodní plocha 21 m, rovně vodní plocha 84 m, vpravo cesta 177 m | Rybníky ano (kontrola stojí u prvního, druhý je dál po směru). Cesta 177 m je daleko. |
| E4 12 (11–12) | paseka napříč 15–31 m | Kontrola stojí na okraji té paseky: zarážkou je objekt kontroly sám. |
| Pohora 16 (15–16) | vlevo okraj otevřené plochy 15 m, rovně cesta 32 m, vpravo okraj 16 m | Ano, pole hned za kontrolou. |

Ostatních 61 kontrol jsem viděl jen jako čísla ve výpisu, ne na mapě.

Co jsem cestou změnil podle výřezů: směr přeběhnutí z posledních 40 m postupu místo stometrové tětivy (u dvojky Petřvaldu se postup před kontrolou láme); část platí jen při shodě druhu u poloviny paprsků (dřív stačila polovina jakýchkoli zásahů a vyšlo „okraj plochy 168 m“ ze tří různých věcí); nejbližší zásah od 15 m místo 10.

### Testy a stránka

- Rychlé testy: 173, asi minuta a půl, linter bez nálezů. Nové: `tests/test_terrain.py` (úzký rybník s břehem je voda a břeh není cesta; vodoteč, bažina a cesta podél břehu se nemění; rybník 5 pixelů široký při 1,33 m na pixel), `tests/test_routing.py` (maska je neprůchodná a průchod ji neotevře; `crossed` pozná křížení čáry mimo průchod, plochu a oplocenku, nepozná křížení na průchodu ani stopu podél čáry), `tests/test_relocate.py` (zarážka po výsecích, pěšina ve směru doběhu, bod zarážkou není, oplocenka ano, slova), `tests/test_web_plans.py` (nový tvar zarážky, věta o železnici v `data.json` i `legs.json`, pruh staré verze postupů).
- Pomalé testy (36): 36 prošlo za 11 min 21 s, na konečném kódu, puštěné jednou a samotné (se zlatým souborem Petřvaldu už novým).
- V bezhlavém Chromu na vývojové kopii, bez chyb JavaScriptu: bez výběru 20 stop a čip „Celá trať“ stisknutý; po výběru S–1 jedna stopa, jeden nejlepší postup, dvě možnosti a tři čáry zarážky; u 1–2 značka překročení a věta o železnici, řádky tabulky „nejlepší, tvoje stopa, možnost 2, možnost 3“; Esc vrátí 20 stop a prázdný panel; na 390 px bez vodorovného posuvníku (tabulka 327 px); se zapnutými záchytnými body u vybraného úseku jen čtyři číslované body jeho kontroly.
- Neověřeno: ruční proklikání v prohlížeči a na telefonu; Tobiasův svazek (jeho Petřvald má jiný model a nemá šrafy, čísla se budou lišit); zakázaná plocha v `crossed` na skutečném závodě (jen v testu).

## 18. Kontrola tras očima: nové zlaté soubory (10. 10. 2026, větev `kontrola-tras`)

Postup noci a nálezy jsou v `docs/kontrola-tras.md`. Tady je, co se změnilo ve zlatých souborech `tests/golden`, přegenerovaných jednou na konci (`tests/make_golden.py`, skripty bez `--barriers`, výškopis AWS, model `oroute/personal_model.json`).

**`course.json` a `legs.csv` se změnily u všech čtyř závodů, a jen startem:** start tratě je střed startovního trojúhelníku (dřív nejhustší fialový shluk u první polohy záznamu). Kontroly a cíl jsou bajtově stejné; v `legs.csv` se liší jediný řádek, S–1 (přímá vzdálenost, poměr, očekávaný čas, značky).

| Závod | Posun startu | S–1 přímo dřív → teď | Proč |
|---|---|---|---|
| Azymut E5 | 6 m | 252 → 257 m | shluk byl u okraje trojúhelníku |
| Azymut E4 | 4 m | 253 → 249 m | totéž |
| Pohora | 44 m | 78 → 123 m | „start“ byl v číslici 16 vytištěné přes trojúhelník; zmizela falešná značka „postup 2,3× delší než přímka“ |
| Petřvald | 93 m | 227 → 267 m | „start“ byl na čárce startu času, od které vede k trojúhelníku značený úsek |

**`best_legs.csv`: úseky, jejichž nejlepší postup se změnil o víc než 5 s**

| Úsek | Nejlepší dřív | Teď | Proč |
|---|---|---|---|
| Azymut E5 S–1 | 1:55, 283 m | 2:21, 353 m (+26 s) | Záznam začíná asi 70 m před trojúhelníkem a naměřený čas úseku ten kus obsahuje; nejlepší postup teď začíná tam, kde stopa, a vede přes trojúhelník. |
| Pohora S–1 | 0:44, 83 m | 1:10, 129 m (+26 s) | Start o 44 m jinde (viz výše). Naměřeno 1:28. |
| Petřvald S–1 | 1:25, 233 m | 2:10, 362 m (+45 s) | Start ve středu trojúhelníku a značený úsek od čárky startu času (93 m) patří k postupu. Naměřeno 2:12. |
| Azymut E4 18–19 | 1:56, 243 m po cestě | 2:02, 171 m po cestě (+6 s) | 72 m „cesty“ byla tečkovaná hranice porostu. |
| Pohora 14–15 | 1:40, 109 m po cestě | 1:48, 34 m po cestě (+8 s) | Postup vedl po tečkovaných hranicích pasek; teď jde lesem a po skutečných průsecích. |
| Petřvald 10–11 | 6:22, 552 m po cestě | 6:33, 358 m po cestě (+11 s) | Asi 190 m „cesty“ byl plot zástavby (černý obrys olivové plochy). Moje stopa, která vede ulicemi zástavby, vychází 9:30 místo 9:06: tenké černé čáry mezi pozemky uvnitř zástavby už také nejsou cesta (naměřeno 7:33; model ulice v zástavbě podceňoval už předtím). |

Součty nejlepších postupů: Azymut E5 24:35 → 25:00, Azymut E4 32:04 → 32:13, Pohora 26:42 → 27:21, Petřvald 53:06 → 54:06. Většina rozdílu je první úsek.

Ostatní úseky se změnily o 5 s nebo méně (tečky, pás bažiny kolem rybníků, obrysy). Azymut E4 S–1 se nezměnil, i když záznam začíná stovky metrů před startem: bez oficiálních časů se doběh ke startu počítá jen do 150 m.

Co z toho plyne a neplyne: změny jsou tam, kde obrázky ukázaly špatně přečtenou kresbu, a jdou směrem k pomalejším (poctivějším) časům. Jestli nové časy sedí líp s referencí kategorie (část 2 a 12), jsem neměřil.

## 19. Kontrola tras podruhé: zlaté soubory a seznam podezřelých (11. 10. 2026, větev `kontrola-tras-2`)

Postup noci je v `docs/kontrola-tras.md`, část „Druhá noc“. Zlaté soubory `tests/golden` jsou přegenerované jednou na konci (`tests/make_golden.py`, skripty bez `--barriers`, výškopis AWS, model `oroute/personal_model.json`). Přegenerování jsem pouštěl dvakrát: první běh spadl u Petřvaldu na stahování výškopisu (chyba SSL), druhý s výškopisem zkopírovaným ze zlatých souborů doběhl.

**`course.json` a `legs.csv` jsou u všech čtyř závodů bajtově stejné.**

**`best_legs.csv`: žádný nejlepší postup se nezměnil o víc než 5 s.** Sloupec `best_model` se liší v jediném řádku ze 71, o 1 s (Azymut E5 12–F, 0:35 → 0:34, 108 → 107 m: u cíle se čte kus mapy u okraje obrázku, který byl zakázaný). Součty nejlepších postupů se nemění. Pravidlo o zástavbě nezměnilo žádný postup: už po minulé noci vedly ulicemi.

Mění se sloupec `your_line_model` (ocenění mojí stopy) ve čtyřech řádcích, z toho ve třech o víc než 5 s:

| Úsek | Moje stopa dřív | Teď | Naměřeno | Proč |
|---|---|---|---|---|
| Petřvald 10–11 | 9:30 | 7:03 (−147 s) | 7:33 | Stopa vede ulicemi zástavby a chybou GPS zabíhá do zahrad, kde se oceňovala chůzí. Vzorek stopy na neprůchodné ploše teď bere třídu nejbližší průchodné plochy do 8 m. |
| Petřvald 6–7 | 2:41 | 2:17 (−24 s) | 2:52 | Totéž, ulice na jižním okraji zástavby. |
| Azymut E4 S–1 | 7:15 | 7:05 (−10 s) | 6:24 | Záznam začíná stovky metrů před startem a vede u spodního okraje obrázku, kde byl pás zakázaného prostoru (chůze); teď se tam čte mapa. |
| Petřvald 17–18 | 3:25 | 3:22 (−3 s) | 3:43 | Stopa podél rybníka: vzorky na břehové čáře berou třídu vedle. |

**Třídy terénu čtyř map** (před nocí → po ní, `kontrola/tmp/cls_dump.py` a `cls_diff.py`):

| Změna | Azymut E5 | Azymut E4 | Pohora | Petřvald |
|---|---|---|---|---|
| Zástavba (cesta → zakázaný prostor uvnitř olivové), pixelů | 1 918 | 0 | 1 010 | 73 534 |
| z toho dál než 8 m od olivové | 0 | 0 | 0 | 0 |
| Okraj obrázku (zakázaný prostor → mapa), pixelů | 92 463 | 133 556 | 21 784 | 33 494 |
| Severní čára přes vodu | 0 | 0 | 0 | 0 |

Okraj obrázku jsem na čtyřech výřezech viděl (po jednom z každé mapy): změněné pixely jsou mapa, která byla zakázaná; u šikmého okraje mapy přesahuje „les“ do bílého okraje listu o klín (viz `docs/rozhodnuti.md`).

**Seznam podezřelých (`tools/podezrele.py`), stejná pravidla pro obě kola:** 32 → 28 podezřelých úseků ze 134 posuzovaných (A 21 → 20, B 16 → 12); průměrná odchylka poměru skutečný čas / nejlepší postup od mediánu závodu 21,7 % → 21,2 %. Zmizely čtyři úseky, nepřibyl žádný. Co seznam neříká: jestli jsou nové časy blíž referenci kategorie (části 2 a 12), jsem neměřil.

**Testy:** rychlé 202 prošly (asi 2 minuty), `ruff check .` bez nálezů, po každé opravě. Pomalé: 36 prošlo za 11 min 41 s, jednou, samotné, na konečném kódu s novými zlatými soubory. (Před tím jsem je jednou zastavil po pár sekundách, protože se pustily proti neúplným zlatým souborům z prvního, spadlého přegenerování.) Po pomalých testech se měnil už jen `tools/podezrele.py` (první úsek se nevyřazuje kvůli záznamu začínajícímu před startem) a jeho rychlý test.

## 20. Sprintové mapy: šedé budovy, zpevněná plocha, průchody (19. 10. 2026, větev `pro-tebe-a-sprint`)

Pravidla (`oroute/terrain.py`, `sprint_greys`, `paved(sprint=True)`) platí jen na mapě, kde je aspoň 0,5 % obrázku plná šedá (průměr kanálů 105 až 150, rozptyl pod 14, po otevření kruhem asi 1,3 m). Podíl plné šedé po otevření:

| Mapa | m/px | Plná šedá | Sprintová pravidla |
|---|---|---|---|
| Azymut E4, E5, Pohora, Petřvald (`data/`) | 0,59 až 1,33 | 0,000 až 0,001 % | ne |
| Grand prix Silesia E1 až E4, noční OB, 10. SZL MSKS | 0,34 až 1,33 | pod 0,1 % (před otevřením) | ne |
| Sprint MSK | 0,399 | 3,56 % | ano |
| Slezská zimní liga | 0,266 | 4,32 % | ano |
| Žebříček B | 0,399 | 6,51 % | ano |
| 3. Zkouška sirén (nespárovaná) | 0,266 | 2,50 % | ano |

(Grand prix Silesia E2 je sprint 1:4 000 v paletě ISOM, černé budovy, beze změny. 10. SZL MSKS je podle názvu sprint, šedé budovy nemá.)

**Lesní mapy se nezměnily:** v kole 2 (`kontrola/noc3/kolo-2`) jsou obrázky všech úseků Azymutu E4, E5 a Pohory bajt po bajtu stejné jako v kole 1 (`tools/kontrola.py --proti`). Petřvald, Grand prix Silesia, Slezská zimní liga a Žebříček B se v kole 2 nedopočítaly (systém zastavil kolo kvůli nedostatku paměti). Pomalé testy se zlatými soubory na tomhle kódu neběžely: běží jednou na konci noci, po části 21.

**Sprint MSK (kolo 1 → kolo 2), nejlepší postup:**

| Úsek | Naměřeno | Nejlepší dřív | Nejlepší teď | Co se změnilo |
|---|---|---|---|---|
| 11–12 | 0:42 | 0:11, 37 m | 0:22, 69 m | už nevede domem (obrázky `docs/reference/sprint/msk-12_11-12-pred.jpg` a `-po.jpg`) |
| 13–14 | 1:19 | 0:29, 94 m | 1:13, 216 m | vedl skrz dva domy, teď kolem nich mezi nimi (`msk-14_13-14-*`) |
| 14–15 | 1:04 | 0:31, 96 m | 0:36, 115 m | kolem domu u kontroly 15 (`msk-15_14-15-*`); vede ale přes silnou černou čáru u dvora (zeď, ISSprOM 515), viz `co-zbyva.md` |
| 2–3 | 1:37 | 1:40, 250 m | 1:45, 264 m | |
| 3–4 | 0:19 | 0:12, 39 m | 0:18, 55 m | |

Ostatní úseky ± 3 s. Zpevněná plocha a průchody jsou teď cesta (na obrázcích tříd černě), domy budova (tmavě červeně).

**Seznam podezřelých na čtyřech přepočítaných závodech** (Azymut E4, E5, Pohora, sprint MSK): 15 → 14 (A 9 → 9, B 8 → 7). Zmizel MSK 4–5 (B), nepřibyl žádný. U sprintu MSK klesla průměrná odchylka poměru skutečný / nejlepší od mediánu závodu z 36,0 % na 19,3 %. Celý seznam (deset závodů) před opravou: 28 podezřelých ze 134 (A 20, B 12), `kontrola/noc3/podezrele-pred.md`. Po opravě na deseti závodech změřený není.

## 21. Stopa vedle cesty a nový osobní model skriptů (19. 10. 2026, větev `pro-tebe-a-sprint`)

Rozhodnuto 11. 10. (otázka 20): úsek tvé stopy, který vede do 15 m od cesty a s ní souběžně (nejbližší bod cesty se v okně ±10 m posouvá se stopou aspoň na 70 % délky a nejvýš 30° od jejího směru), na délce aspoň 30 m, se čte jako cesta (`oroute/routing.py`, `along_path`). Platí všude, kde se čte vlastní stopa: „tvoje stopa“ v rozboru, vzorky, ze kterých se učí model (terén pod každým krokem GPS i ocenění čistých úseků, podle kterého se škáluje rychlost). Zároveň je přepočítaný `oroute/personal_model.json` (audit, rozpor 7: byl ze 6. 10., před opravou čtení terénu ze 7. 10.), aby se zlaté soubory měnily jen jednou.

Postup (v kontejneru, jeden výpočet po druhém, asi 6 minut): pro každý závod z `data/` `analyze.py` a `bestroute.py --samples-only --title …` do pracovní složky (výškopis ze zlatých souborů), pak `python -m oroute.personal oroute/personal_model.json …/fit_samples.npz --check`, pak `tests/make_golden.py` (s `dem_cache.npz` ze zlatých souborů). `data/*/fit_samples.npz` jsem nepřepisoval (`data/` se necommituje).

**Model** (rychlost po rovné cestě pro hodinový závod a činitele terénu):

| | Starý (6. 10.) | Nový bez pravidla | Nový s pravidlem (commit) |
|---|---|---|---|
| cesta km/h | 12,28 | 12,06 | 11,42 |
| délka závodu `dur_exp` | (není) | 0,073 | 0,073 |
| louka | 0,987 | 0,968 | 0,957 |
| hrubá louka | 0,849 | 0,838 | 0,810 |
| les | 0,774 | 0,763 | 0,780 |
| podrost | 0,698 | 0,686 | 0,667 |
| světle zelená | 0,696 | 0,686 | 0,659 |
| bažina | 0,520 | 0,493 | 0,489 |
| zelená | 0,509 | 0,510 | 0,450 |

Stopa, která jela po cestě a GPS ji dávalo vedle, se dřív učila jako les nebo zelená: les a zelená vycházely rychlejší, než jsou. Teď se ty kroky učí jako cesta a model se celý škáluje k naměřeným časům čistých úseků, které ocení rychleji: rychlost po cestě klesla o 5 %, zelená o 12 %.

**Zkouška vynecháním závodu** (`--check`, model z ostatních tří závodů předpovídá čisté úseky vynechaného):

| Závod | Chyba celku bez pravidla | s pravidlem | Chyba po úsecích bez | s | Model z vlastního závodu, po úsecích bez | s |
|---|---|---|---|---|---|---|
| Azymut E4 | +13,6 % | +18,5 % | 26,9 % | 29,2 % | 19,8 % | 19,0 % |
| Azymut E5 | −6,0 % | −2,1 % | 11,1 % | 12,3 % | 13,2 % | 15,0 % |
| Pohora | +0,3 % | −2,0 % | 28,5 % | 26,3 % | 21,3 % | 20,9 % |
| Petřvald | −6,5 % | −9,5 % | 13,8 % | 10,9 % | 13,0 % | 7,3 % |
| průměr (abs.) | 6,6 % | 8,0 % | 20,1 % | 19,7 % | 16,8 % | 15,6 % |

Na čtyřech závodech je to v šumu: celek o něco horší, úseky o něco lepší, nejvíc Petřvald (vlastní model 13,0 → 7,3 % po úsecích; stopa vede ulicemi a cestami a GPS ji dává do zahrad a lesa).

**Zlaté soubory** (`best_legs.csv`, `legs.csv` a `course.json` beze změny):

| Závod | Úseků | „Tvoje stopa“ změněná o víc než 5 s | Nejlepší postup změněný o víc než 5 s | Součet tvé stopy dřív → teď (naměřeno) | Součet nejlepších dřív → teď |
|---|---|---|---|---|---|
| Azymut E5 | 13 | 11 | 10 | 53:19 → 59:27 (77:02) | 24:59 → 27:50 |
| Azymut E4 | 21 | 16 | 17 | 51:23 → 53:19 (55:07) | 32:13 → 34:44 |
| Pohora | 17 | 14 | 12 | 46:38 → 47:56 (51:05) | 27:21 → 29:52 |
| Petřvald | 20 | 15 | 17 | 68:13 → 70:51 (80:18) | 54:06 → 59:35 |

Nejlepší postupy jsou všude o 5 až 10 % pomalejší: je to pomalejší model (nižší rychlost po cestě, k tomu faktor délky závodu), ne jiné postupy. Ztráta volbou postupu a provedením (`loss_*`) se tím přesouvá: provedení vychází menší.

**Pět úseků z `co-zbyva.md` („Stopa vedle cesty“):**

| Úsek | Naměřeno | Tvoje stopa dřív | Teď | |
|---|---|---|---|---|
| Azymut E4 2–3 | 1:21 | 1:55 | 1:25 | blíž (stopa podél cesty se teď počítá jako cesta) |
| Azymut E4 11–12 | 1:24 | 1:40 | 1:34 | blíž |
| Petřvald 10–11 | 7:33 | 7:03 | 7:38 | blíž (dřív o 30 s rychlejší, teď o 5 s pomalejší) |
| Azymut E4 18–19 | 1:57 | 2:32 | 2:51 | **dál**: stopa vede dál než 15 m od cesty nebo napříč, pravidlo ji nebere, a model je teď pomalejší |
| Pohora 8–9 | 2:59 | 4:38 | 5:08 | **dál**: totéž |

Tři z pěti se přiblížily, dva se vzdálily, protože pravidlo na ně nedosáhne a pomalejší model je oceňuje ještě pomaleji. U nich je příčina jiná než posun GPS podél cesty (mapa usazená o víc než 15 m, nebo zkratka, kterou mapa nezná); neověřoval jsem na obrázku.

**Seznam podezřelých po všech opravách noci** (kolo 1 → kolo 3, stejných devět závodů; Žebříček B se v kole 3 nedopočítal): **26 → 26** podezřelých ze 120 posuzovaných (A 18 → 18, B 12 → 11), nepřibylo. Změny:

| Zmizely | Přibyly |
|---|---|
| Azymut E4 2–3 (B) a 11–12 (B): stopa podél cesty, cíl části 21 | Azymut E4 1–2, 7–8, 10–11, 15–16 (všechny B): tvoje stopa je teď oceněná o 16 až 33 % pomaleji, než jsi běžel. Není to čtení mapy: nový model je pomalejší (rychlost po cestě −7 %) a na E4 běžíš rychleji, než model z ostatních závodů čeká (zkouška vynecháním: E4 +18,5 %) |
| Grand prix Silesia E4 12–13 (B), sprint MSK 4–5 (B), Pohora S–1 (A) | Grand prix Silesia E4 17–F (A, doběh do cíle) |

Průměrná odchylka poměru skutečný / nejlepší od mediánu závodu u sprintu MSK 36,0 % → 19,2 %.

## 22. Dva snímky z Livelox po sloučení s pravidly sprintu (22. 10. 2026, větev `snimky-a-napoveda`)

`tools/snimek.py` (umělé dvojice snímků se známou pravdou, `--routes`) na pěti mapách: Azymut E4, Pohora (les), MSK,
Slezská zimní liga, Žebříček B (sprint), zvětšení prohlížeče 1 a 1,5, bez posunu. **Před** = kód větve
`snimky-livelox` (bez budov, zdí a stopy vedle cesty), **po** = sloučená větev s opravou rozmazání zdí (níže). Každá
strana své referenční postupy z KMZ (pravidla se liší). Skript `kontrola/noc5/snimky.sh`, výsledky
`kontrola/noc5/pred-final.csv` a `po-oprava.csv`.

Pozor na měření: polohy kontrol dostávají sprinty s 8 m šumu z jednoho generátoru (seed 7) pro všechny mapy běhu, takže
výsledek mapy závisí na tom, které mapy běžely před ní. První pokus ukázal „horší usazení“ na Žebříčku B (rohy 7,9 →
15,3 m); stejná mapa měřená samotná vyšla před i po 15,3 m. Srovnání níže je mapa po mapě se stejným pořadím.

| Zvětšení | | usazeno | rohy medián / nejvíc | terén u tratě změněn | cesty ±1 px | zelená | zakázané | úseky do 5 s | úseky přes zákaz KMZ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | před | 5 z 5 | 15 / 16 m | 1,0 % | 0,1 % | 0,2 % | 8,1 % | 97 z 102 | 0 |
| 1 | po | 5 z 5 | 15 / 16 m | 1,0 % | 0,1 % | 0,2 % | 8,1 % | 96 z 102 | 0 |
| 1,5 | před | 5 z 5 | 15 / 17 m | 10,6 % | 6,8 % | 15,8 % | 6,8 % | 90 z 102 | 8 |
| 1,5 | po bez opravy | 5 z 5 | 15 / 17 m | 11,5 % | 4,0 % | 15,9 % | 12,7 % | 84 z 102 | 2 |
| 1,5 | **po** | 5 z 5 | 15 / 17 m | 10,3 % | 4,0 % | 15,9 % | 6,8 % | 85 z 102 | 1 |

- **Usazení beze změny** (stejný kód `pair.py`, stejné rohy na všech mapách).
- **Terén**: při zvětšení 1 stejný, při 1,5 stejný nebo lepší (cesty 6,8 → 4,0 %), úseků přes zakázané místo KMZ 8 → 1.
- **Co se zhoršilo bez opravy**: při zvětšení 1,5 ze snímku mizely zdi sprintu (rozmazaná čára 1,3 m vycházela
  1,22 m, pod prahem 1,25 m), MSK: změněné zakázané plochy 5,6 → 12,7 %, chybějící pixely budov 16 061. Oprava
  (`pair.py` odhadne rozmazání a KMZ ho nese jako `ob-blur-m`, `terrain.sprint_walls` ho započte) → 5,3 %, 5 032.
- **Úseky do 5 s** jsou o pár horší (97 → 96, 90 → 85). Není to terén: na Žebříčku B se úsek 9 liší o 16,8 s i při
  zvětšení 1, kde má snímek přesně pixely KMZ. Se zdmi na sprintu je nejlepší postup citlivý na to, na kterou stranu
  zdi padne kontrola, a snímek je usazený s chybou 6 až 15 m. Bez zdí (kód před) na tom nezáleželo.

## 23. Délka závodu a únava (10. 10. 2026, větev `claude/project-thread-ao1vg1`)

Otázka: běhá se na dlouhém závodě pomaleji a počítá s tím model? Dosud měl jednu rychlost pro všechny závody.

**Během závodu tempo neklesá.** 30 závodů z Garmin exportu (sprinty 16 min až Český pohár 98 min), rychlost v pohybu po třetinách závodu, medián poslední třetina / první: do 30 min 1,00, 30–50 min 0,98, nad 50 min 1,03. Tep v poslední třetině stoupá hlavně na krátkých závodech (+13 tepů, finiš), na dlouhých skoro ne (+2). To sedí s bodem 8: člen „únava za hodinu“ vyšel kolem nuly.

**Délka závodu ano.** Čisté úseky čtyř závodů proti modelu bez délky (dvojice ve stejném terénu):

| Závod | Délka | Pomaleji než model |
|---|---|---|
| Pohora | 51 min | +1,6 % |
| Petřvald | 80 min | +1,2 % |
| Azymut Day 4 | 55 min | −6,4 % |
| Azymut E5 | 77 min | +8,9 % |

V obou dvojicích byl delší závod pomalejší. Průměrný tep z Garminu je na závodech nad 50 min o něco nižší (medián 141 proti 148–151), korelace s délkou je ale slabá (Spearman −0,15, tep ze zápěstí je hlučný).

**Úprava** (`SpeedModel.dur_exp`, `oroute/personal.py` `fit_duration`): rychlost závodu dlouhého D je `v_flat · (D / 60 min) ^ −dur_exp`, `v_flat` je rychlost hodinového závodu. Exponent se odhadne z odchylek závodů s volným posunem a je přitahovaný k Riegelovu 0,057 (σ 0,05), protože čtyři závody samy dávají 0,22 a to při vynechání závodu vychází hůř. Výsledek 0,068: 15 min ×1,10, 30 min ×1,05, 90 min ×0,97 proti hodinovému závodu. Délka je tvůj čas závodu (`race_s` ve vzorcích, u starších souborů čas posledního vzorku).

| Vynechání závodu | Celek | Úseky |
|---|---|---|
| bez délky závodu | 5,6 % | 19,8 % |
| s délkou (σ 0,05) | 4,9 % | 19,3 % |
| jen data, bez Riegela | 8,0 % | 19,0 % |

Zisk je malý a na čtyřech závodech v šumu; rozhodne až víc závodů různé délky (sprinty a zimní liga z `data-extra/`). Na tom, **který postup je nejlepší, to nic nemění** (všechny postupy úseku se zrychlí nebo zpomalí stejně); mění se časy postupů a rozdělení ztráty na volbu postupu a provedení. `oroute/personal_model.json` v repu se nepřepočítal (vzorky v `data/` nemají délku závodu), webová appka si exponent spočítá při dalším přepočtu modelu z `leg_samples.npz`.

**Stav k 24. 10. 2026.** Kód je v `main` od sloučení `ae21cbf` (19. 10.), tenhle oddíl se tehdy při konfliktu ve `docs/validace.md` ztratil (na jeho místě je oddíl 18 o kontrole tras) a vrací se sem beze změny obsahu. Model v repu (`oroute/personal_model.json`) už exponent má: `dur_exp` 0,073, tedy 15 min ×1,11, 30 min ×1,05, 90 min ×0,97. Test `tests/test_race_length.py`.

## 24. Kolečka kontrol proti ORIS (11. 11. 2026, větev `kontroly-podle-oris`)

Issue 9: appka u tátových KITL 2025 (H45B) nepoznala některé kontroly, na Macu jednou našla 6 z 19, jindy 169
„koleček“ místo 18. Nástroj `tools/kolecka.py` porovná u každé mapy na tomhle počítači kolečka z `detect_course`
(počítaná jako v `analyze.py`, 25 m a dál od cíle) s počtem kontrol podle ORIS (počet mezičasů, jinak kódy kontrol
kategorie). S během a oficiálními časy ukáže i kolečka dohledaná u míst ražení (+) a vynechaná (−). S `--rozbor` uloží
výřezy do `kontrola/kitl-kolecka/`. Tátovy KITL tu nejsou (`docs/co-zbyva.md`, otázka 51); Tobiasovy H16B z týchž dnů
sedí (13 z 13, 12 z 12).

**Počet z ORIS.** `classes.controls` („Controls“ z `getEvent`) nesedí s mezičasy u 12 z 83 přihlášek v databázi
autora: vždy říká víc (SZL 15. 2. 2025: 28, mapa i popisy kontrol mají 26; Zkouška sirén 6. 11. 2024: 20 proti 16).
Kódy kontrol z mezičasů sedí s mezičasy vždy. Porovnává se proto jen s nimi.

**30 map.** U 23 map s počtem z ORIS vycházelo před změnou:

| Mapa | ORIS | Kolečka | Proč |
|---|---|---|---|
| Bohemia 2025 E1 (H16B) | 11 | 2 | Mapa 0,43 m/px, čára kolečka 7 px. Jedno kolečko se trefí na několika poloměrech až 7 px od sebe a `_circles` bral každou skupinu s rozpětím ≥ 5 px jako cíl. Dvě kolečka (4, 6) jsou navíc rozřezaná. |
| Přebor BFM+SFM 2026 | 13 | 14 | Číslo „10“ vytištěné přes „4“: nula se čte jako kolečko (vnitřek 0,22 fialové, 105 m od všech ražení). |
| Grand Prix Silesia E1 (H16B) | 22 | 21 | Kontrola 16 je rozřezaná černou kresbou: skóre 0,33 (práh 0,35), obvod 69 %, největší mezera 55°. Mapa nemá běh, takže se nedohledá; zbývá ruční oprava. |
| ostatních 20 | = | = | |

**Rozřezaná kolečka.** Celé kolečko z Livelox má skóre `hough_circles` kolem 0,5 a skóre klesá s vytištěnou částí obvodu
(na umělé mapě 0,51 · podíl). Práh 0,35 tak nevezme kolečko, kterému chybí víc než asi třetina. Naměřené
rozřezané kontroly:

| Kontrola | Obvod | Největší mezera | Spojnice | Od hodinek |
|---|---|---|---|---|
| Bohemia E1, 4 | 69 % | 40° | 0,97 | 10,7 m |
| Bohemia E1, 6 | 65 % | 55° | 0,93 | 18,1 m |
| GPS E1, 16 | 69 % | 55° | (bez běhu) | |

**Po změně** (`oroute/course.VERSION` 1): Bohemia E1 9 koleček + 2 dohledaná = 11 a oficiální časy se použily (dřív
GPS); Přebor 14 − 1 = 13 a oficiální časy se použily. Ostatních 28 map dává stejný počet koleček a najde start i cíl
jako před změnou (porovnání `vse-pred.json` a `vse-po.json`). Změnilo se jen, kdy je skupina kruhů cíl;
kdyby se některá zařadila jinak, změnil by se počet. Zlaté soubory čtyř referenčních závodů viz níže. Hledání u míst ražení se pouští jen tam, kde počet nesedí, takže
se jejich trať nemůže změnit. Na umělé mapě (`tests/test_kolecka.py`) se dohledají kolečka s 64 % a 43 % obvodu (ve třech
obloucích), s 33 % a 28 % ne. Číslo kontroly, šrafy a křížení spojnic u místa ražení kolečko nedají.

**Referenční závody** (`tests/test_regression.py`, `tests/test_official_races.py`, 11. 11. na Windows, Python 3.14):
`legs.csv` a `course.json` Pohory a Petřvaldu jsou stejné jako zlaté soubory, i s oficiálními časy. Bajtově testy na
Windows neprojdou kvůli koncům řádků (`\r\n` proti `\n` ve zlatých souborech z Linuxu). `best_legs.csv` se od zlatých
liší o pár metrů v `best_path_m` a `best_green_m` (časy stejné). Stejně ale vyjde i `bestroute.py` z `main` na stejných
vstupech, takže to dělá prostředí, ne tahle změna. Zlaté soubory se nemění.
