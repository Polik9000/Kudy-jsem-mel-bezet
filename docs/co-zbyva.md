# Co zbývá, co je nejisté, na co se zeptat (stav 25. 10. 2026 večer, větev `oplocenky-vodotece`)

## Noc 25. 10.: oplocenky, severky místo vodotečí, Ztratil jsem se jen po závodě (větev `oplocenky-vodotece`, nesloučená)

Větev je z `origin/ztraceny-u-kontroly` (ta v `main` není sloučená), takže PR obsahuje obě. Popis PR:
`docs/pr-popis.md`; podrobně `docs/oplocenky-vodotece.md`; rozhodnutí: `docs/rozhodnuti.md`, poslední oddíl.
Bělá je zkopírovaná z webové appky do `data-extra/bela/` (gitignored) a je v `tools/kola.sh` jako `bela`.

| Bod zadání | Stav |
|---|---|
| 0. Větev, data | hotovo: Bělá ze svazku `ob_tracker_ob_data` (jen pro čtení), postupy webu vykreslené v `kontrola/noc4/web-bela`. Tobiasovy výřezy obrazovky na počítači nebyly (otázka 43). |
| 1. Oplocenky | hotovo: v Bělé 29 oplocenek (dřív 9) a 4 rohy; žádný postup, možnost, průměrný běžec ani rada nejde oplocenkou ani přes plot (`tools/oplocenky.py`). Branky do 12 m, neprůchodný plot (dvojité zoubky), kontrola otevře jen svou oplocenku, plán platí 90 s za plot. Na ostatních mapách jen opravdové nové oplocenky. |
| 2. Severky | hotovo: `terrain.north_lines` (projekce pod úhly ±30°, mřížka), na všech 11 mapách 300 m / 120 m; Bělá 10 severek pod 0,70° (dřív žádná). Azimuty k severkám. V Bělé žádná falešná vodoteč. |
| 3. Zarážka u S-1 | hotovo: „rovně cesta 55 m“ (Tobiasova žlutá). Vlastní cesta kontroly do 25 m a souběžná cesta mimo kontrolu se nepřeskakuje. |
| 4. Jen po závodě | hotovo: bez polohy z telefonu a „Teď v lese“, věty v minulém čase, kruh 25 m na sprintu, před závodem bez odkazu. Fotky `docs/reference/oplocenky-vodotece/stranka-*.jpg`. |
| 5. Ztracený u 4 | hotovo: bez okliky („byl jsi u cesty, kontrola 75 m na azimut 150°“); „po čáře“ jako na Tobiasově žluté ne (otázka 45). |

**Testy:** rychlé **354 prošly**, `ruff` čistý; pomalé **38 prošly** (regrese 12, web 17, ostatní 9). Goldeny
přegenerované u čtyř referenčních závodů (8 řádků `best_legs.csv`, důvody v `docs/oplocenky-vodotece.md`). Kola 6 až
9 (`kontrola/noc4/kolo-9`: všech 11 závodů s konečným kódem); `tools/podezrele.py` 23 úseků „rychlejší než nejlepší“
před i po.

Co zbývá:

| Co | Stav |
|---|---|
| Po sloučení | Kliknout **Přepočítat postupy** (verze 9 / 8 / 2) a projít Bělou: S-1, 4-5 (možnost 3), kontrola 7, 1-2, zarážka u 1, ztracený u 4. |
| Obrys bez zoubků | Záměrně není oplocenka (smyčky cest). Kdyby na jiné mapě byla oplocenka opravdu bez zoubků, zůstane průchozí. |
| Ostré mapy | Uvolnění pro rozmazané čáry platí jen na hrubých obrázcích; na Petřvaldu (0,59 m/px) zůstaly 2 oplocená pole nenalezená (zoubky, které čára přerušuje). |
| Dvory na sprintu | SZL Zábřeh: 8 dvorů a ploch mezi domy se čte jako oplocenky už od dřívějška (otázka 44). |
| Skutečný telefon | Neověřeno, ale stránka už nic za běhu nenabízí. |


## Noc 24. → 25. 10.: Ztratil jsem se u kontroly (větev `ztraceny-u-kontroly` z `main`, nesloučená)

**PR #6 je v `main` sloučený, PR #7 ne** (v `main` není jeho merge; nesloučená je větev `claude/project-thread-qr6fix`
s jedním commitem „validace: vrácen oddíl o délce závodu (Riegel)“). Větev je proto z `main` (`b2bc8a0`), bez PR #7
(otázka 38). Popis PR: `docs/pr-popis.md`; obrázky a texty rad: `docs/ztraceny-u-kontroly.md`; rozhodnutí:
`docs/rozhodnuti.md` (poslední oddíl).

| Bod zadání | Stav |
|---|---|
| 1. Vstup: kontrola a poloha | hotovo: čipy kontrol, ťuknutí do mapy, „Moje poloha z telefonu“, „Jen kontrola a okolí“, kruh 25/50/100/150 m. Po závodě výchozí poloha z .fit (místa ze stopy). |
| 2. Výstup na mapě | hotovo: kruh nejistoty, kontrola, 2 až 4 záchytné body (cesty, vodoteče, ploty, okraje zástavby, velkých ploch a vody, budovy, zdi sprintu, křížení, konce cest, bodové značky ze záchytných bodů), čára rady. |
| 3. Azimut a vzdálenost, co uvidí cestou | hotovo: u každého bodu od tebe i od kontroly (seznam „Záchytné body kolem“), „po 80 m přejdeš cestu“. |
| 4. Doporučení 1–3 věty | hotovo, šablony v `webapp/texts.py`; vybírá nejjistější věc (rovnoběžné paprsky z celého kruhu, 80 %), ne nejbližší. |
| 5. Relokace | hotovo: „Nehádej směr ke kontrole. Nejdřív dojdi / se vrať k …“, když je jistá věc dál než kruh; bez jisté věci zpět na náběhový bod. |
| 6. Zpětná analýza | hotovo: místa 20–100 m od kontroly ze stopy (druh chyby z analýzy, zastavení, bloudění, k tomu zpomalení, otočka, smyčka), co bylo do 30 m, co stopa přešla a kudy zpět. Na Petřvaldu 5 míst, na MSK sprintu 2. |
| Popis kontroly | hotovo: `leg_notes.control_desc`, ručně, jen se ukáže; nic nepřepočítá. |
| Telefon | hotovo: velká tlačítka, bez hoveru, snímky 390 px v `docs/reference/ztraceny/`. Na skutečném telefonu nezkoušeno. |
| Bez nových verzí | hotovo: `bestroute.VERSION` 8, `relocate.VERSION` 7, nic se nepřepočítává; `relocate.json` bajtově stejný jako na `main` (Pohora, MSK sprint). |
| Tři závody, aspoň 5 kontrol | hotovo: les Petřvald (6 + 5 míst po závodě), sprint MSK (5 + 2), noční Borovec (6, bez běhu). |

**Testy:** rychlé **345 prošly** (nové `test_lost.py` 22 a `test_web_lost.py` 8, upravený `test_napoveda.py` a jeden
řádek `test_web_plans.py`), `ruff` čistý. Pomalé **38 prošly** (po částech v popředí: web 17, regrese 12, ostatní 9).

**Kolo `tools/kola.sh 5 petrvald msk-sprint` nedoběhlo:** Claude Code ho zastavil kvůli nedostatku paměti na
počítači (bez chyby výpočtu); zbylý kontejner jsem zastavil. Znovu jsem ho podle pokynu nepouštěl. Místo něj jsem
pustil jen nový krok (`python -m oroute.lost`) v popředí na výstupech kola 3 (`kontrola/noc4/kolo-3`, kód rozboru
stejný jako `main`) a na nočním závodě z KMZ: výsledky v `kontrola/noc5/`. Krok `oroute.lost` je přidaný do
`kontrola/noc4/kolo4.py`, takže příští kolo ho udělá samo.

Co zbývá:

| Co | Stav |
|---|---|
| Kolo po závodech | Pusť `tools/kola.sh 5 petrvald` a `tools/kola.sh 5 msk-sprint` (každé zvlášť, ideálně bez jiných programů); nový krok zapíše `kolo-5/<závod>/ztraceny/`. |
| Rada od kontroly pryč | Když kolem kontroly není nic jistého z kruhu (kupky, prohlubně), rada vede k jisté linii a zpátky (Petřvald 1, 10). Lepší by byla rada „azimutem a hledej kupku“ s malým kruhem. |
| Široká silnice | Uprostřed silnice (hnědá plocha s černými okraji) běžec „u cesty“ není (noční 10). Chtělo by to brát plochu silnice jako cestu. |
| Sprint | Ulice do 50 m je skoro vždycky: „Jsi u cesty“ nepozná, o kterou jde. Doporučit na sprintu kruh 25 m, nebo počítat jedinečnost. |
| Noc | Viditelnost bodu 8 m i v noci; okraje porostů za tmy. Noční závod s během chybí (otázka 39). |
| Scéna po změně | Stará scéna (nová analýza, mapa usazená ručně) se připraví znovu, až když někdo stránku otevře (asi minuta). Do terénu je potřeba stránku otevřít předem. |
| Skutečný telefon | Neověřeno: ťukání prstem, poloha z telefonu přes https (prohlížeč ji bez https mimo localhost nedá). |


## Noc 21. → 22. 10.: snímky z Livelox v appce, nápověda, přepočítat všechno, zastavení úloh, mezičasy, oprava stopy (větev `snimky-a-napoveda` z `zdi-sbehy-provoz`, nesloučená)

PR #5 (`zdi-sbehy-provoz`) v `main` sloučený nebyl, takže větev stojí na něm. Popis PR: `docs/pr-popis.md`;
rozhodnutí: `docs/rozhodnuti.md` (poslední část); měření snímků: `docs/validace.md` (oddíl 22); snímky Mezičasů před
a po: `docs/reference/mezicasy/`; nápověda a Podklady: `docs/reference/provoz/`.

| Bod zadání | Stav |
|---|---|
| 1. Snímky z Livelox | hotovo: `snimky-livelox` sloučená (merge), konflikty jen dva (`webapp/views/races.py`: import a parametry stránky; `docs/rozhodnuti.md`). Verze postupů se nezvedají (snímky pravidla nemění). V Podkladech pořadí **1. KMZ, 2. dva snímky, 3. fotka**. Měření: usazení beze změny, terén stejný nebo lepší; při zvětšení 1,5 ze snímku mizely zdi sprintu, **opraveno** (rozmazání snímku se započte do šířky zdi). Pomalé testy obou větví prošly. |
| 2. Nápověda | hotovo podle tebe (Garmin „Exportovat soubor“, celý export, Livelox tři čárky → Stáhnout mapu, když stažení nejde fotka a šest kroků ke snímkům). Bod 4 (neposouvat, nepřibližovat) zůstal přísný: appka snese posun o pár pixelů, ne jiné přiblížení. **Cestou opravená chyba:** nahraný zip s jedním během se bral jako celý export a mazal nespárované běhy dřívějších exportů. |
| 3. Otázka 32 | uzavřená: posunutá GPS, plot zůstává zavřený. |
| 4. Přepočítat všechno | hotovo: tři kroky (vzorky jen kde se změnilo, jednou model, postupy po jednom). Test: všechny závody mají jeden model, druhé stisknutí nic nepočítá, model se ve třetím kroku nemění. Tlačítko na stránce modelu, v seznamu závodů a v pruhu „Postupy jsou spočítané se starším modelem rychlosti“. |
| 5. Když GPS zlobí | hotovo: „Opravit moji stopu“ na panelu úseku (a Vrátit GPS stopu), „GPS tu asi zlobí“ u úseků, kde stopa u ražení končí dál než 30 m nebo skáče přes 30 km/h (měřeno přes 5 s). **Usadit mapu ručně** i pro KMZ a snímky (posun celé mapy podle kontrol, jde vrátit). |
| 6. Mezičasy | hotovo: čísla kontrol nad grafem, jméno a ztráta po najetí myší / ťuknutí, legenda, reference v nadpisu sloupce, nadpis ztráty, chyba u ostatních a u tebe, vysvětlení sloupců. „Sedí model s kategorií?“ je na stránce modelu („Jak dobře model sedí“). Snímky před a po v `docs/reference/mezicasy/`. |
| 7. Zastavit úlohy | hotovo: Zastavit u úlohy a Zastavit všechny moje; běžící skript se zabije do sekundy; rozbor se počítá v kopii složky, takže po zastavení platí poslední hotový. Jen vlastní úlohy. |
| 8. OpenStreetMap | hotovo: záložní server `overpass.private.coffee`, hláška bez kódu chyby, ukládání k závodu už bylo (teď se zapisuje celé). |

**Testy:** rychlé 315 prošly, `ruff` čistý; pomalé **38 prošly** (po částech: regrese 12, web 17, fotka/usazení/šrafy 5,
ostatní 4); jeden pomalý test čekal starý text pruhu o modelu, opravený.

**Kolo `tools/kola.sh 3`** (každý závod ve vlastním kontejneru, po jednom): všech deset doběhlo, nejvíc paměti SZL
3,2 GB (22 min). **Podezřelé úseky 30 → 30** (A 22, B 11), stejné úseky se stejnými časy nejlepších postupů.

**Co se v noci nepovedlo nebo je potřeba vědět:**

- Claude Code dvakrát zastavil úlohy na pozadí kvůli málo paměti hostitele (měření snímků a rychlé testy jednoho
  commitu). Nic jsem po nich znovu nepouštěl na pozadí; zbytek (měření, pomalé testy, kolo) běžel v popředí po
  kouscích. Výsledek rychlých testů toho commitu se ztratil, rychlé testy konečného kódu prošly.
- Jednou běžela dvě měření snímků najednou asi 5 minut (SZL se přesunulo na pozadí a já pustil Žebříček B). Výsledky
  to nezměnilo (každé měření má vlastní kopii kódu a soubor), pravidlo „jeden těžký výpočet“ jsem ale porušil.

Co zbývá:

| Co | Stav |
|---|---|
| Zdi na snímcích sprintu | Oprava rozmazání je jen částečná: slabé okraje rozmazané čáry padnou pod práh inku a na hnědé dlažbě se okraj čáry nebere jako šedý. Zeď těsně nad 1,25 m se při větším přiblížení může ztratit dál. Při zvětšení 1 (snímek má pixely mapy) žádná ztráta. |
| Úseky do 5 s ze snímků | O pár horší než před sloučením (97 → 96, 90 → 85 ze 102). Není to terén, ale citlivost postupů na to, na kterou stranu zdi padne kontrola: snímek je usazený s chybou 6 až 15 m. |
| Snímky v opravdovém Livelox | Měřeno na umělých snímcích (barvy stránky Livelox jsou odhad). Otázka 34. |
| Opravená stopa a záchytné body | Bloudění u kontroly (`relocate.wandering`) se u opraveného úseku počítá dál z GPS stopy. |
| Opravená stopa ve starších rozborech | „GPS tu asi zlobí“ se ukáže až po přepočtu (Přepočítat všechno). |
| Usazení mapy ručně | Posune mapu celého závodu pro všechny běžce, kteří ji mají (otázka 36). Klikání se ukládá do `manual/` v instanci; smazání účtu tyhle soubory nemaže. |
| Vzorky a verze | Když se změní, co `bestroute.py --samples-only` zapisuje, je třeba ručně zvednout `oroute/personal.SAMPLES`. Rozbory starší než tahle noc nemají klíč vzorků: první Přepočítat všechno jim vzorky přečte znovu (minuta na závod). |

## Noc 20. → 21. 10.: zdi na sprintu, věty průměrného běžce, provoz pro klub (větev `zdi-sbehy-provoz` z `pro-tebe-a-sprint`, nesloučená)

PR #4 (`pro-tebe-a-sprint`) v `main` sloučený nebyl, takže větev stojí na něm. Popis PR: `docs/pr-popis.md`;
rozhodnutí: `docs/rozhodnuti.md` (poslední část); věty: `docs/pro-tebe.md` (poslední část); provoz:
`docs/provoz.md`.

| Bod zadání | Stav |
|---|---|
| 0. Paměť a Žebříček B | hotovo: `tools/kola.sh` pouští každý závod ve vlastním kontejneru a měří špičku paměti každého kroku. **Žebříček B doběhl** (samotný 4,6 min, špička 1,3 GB) a je ve všech číslech. Nic se nezmenšovalo. |
| 1. Zdi na sprintu | hotovo: neprůchodná zeď (silná čára, i neprůchodný plot 518) je budova, zídka s tečkami (513) se přelézá 6 s, branky zůstávají otevřené. Lesní mapy a Grand prix Silesia E2: obrázky úseků bajtově stejné (Azymut E4, E5, Pohora, Petřvald, E3, E4, E2). Snímky před a po v `docs/reference/sprint/zdi-*`. Podezřelých úseků **29 → 30** (viz níže). |
| 2. Věty u průměrného běžce | hotovo: místo a povrch klesání / stoupání, „kratší“ / „delší“, sprintová slova, všech 10 úseků prošlých s obrázky (`docs/pro-tebe.md`) |
| 3. Provoz pro klub | hotovo: `flask sync-oris-all`, `flask backup` / `restore` s testem obnovy, služba `cron` v compose (vypnutá), nápověda „Jak na to“ (`/ob/jak-na-to`, snímky v `docs/reference/provoz/`) |

**Paměť (kolo 2, každý závod sám, nejvyšší krok):**

| Závod | Mapa | Špička | Kde |
|---|---|---|---|
| Slezská zimní liga | 6300 × 4599 px (29,0 Mpx), 0,266 m/px | 3,2 GB | čtení terénu (`terrain.classify`, 3,1 GB i bez zdí; zdi přidají 31 MB a 8 s) a záchytné body (3,2 GB) |
| Petřvald | 0,59 m/px | 3,1 GB | hledání postupů (mřížka, průměrný běžec) |
| Grand prix Silesia E2 | 6436 × 2512 px, 0,40 m/px | 1,7 GB | mřížka po výškopisu |
| Žebříček B | 2040 × 3054 px, 0,40 m/px | 1,2 GB | záchytné body |
| ostatní | | do 1,2 GB | |

Minulou noc kola padala na paměť hostitele (Docker 7,6 GB, ve Windows volné asi 3 GB), ne jednoho závodu: samotný
nejtěžší závod (SZL) se vejde. Zmenšovat rozlišení nebylo potřeba.

**Podezřelé úseky** (`tools/podezrele.py`, před = kolo 3 minulé noci + Žebříček B z kola 0 této noci, po = kolo 2,
stejný model): **29 → 30**. Přibyl jediný úsek, **Žebříček B 7–8** (skupina A: běžel jsi 1:57, nejlepší postup
modelem 2:04). Dřív vedl nejlepší postup (1:44) šikmo přes sportovní areál skrz jeho plot; teď ho obchází severní
brankou. Tvoje GPS stopa vede podél západního plotu, pár metrů uvnitř areálu, a jihozápadní roh plotu je na mapě
zavřený (`docs/reference/sprint/zdi-zb-*`). Buď jsi běžel venku podél plotu a GPS je o pár metrů vedle, nebo jsi
plot přelezl; podle mapy je správně obcházet. Zadání chtělo, aby počet nevzrostl: nechal jsem to tak, protože
„oprava“ by znamenala pustit postupy plotem (otázka 32). Ostatní podezřelé jsou stejné úseky jako dřív.

**Co jsem cestou opravil:** zesílení zdi o buňku v mřížce zavřelo branku 3,6 m na MSK 11–12 (postup 1:27 oklikou);
teď mřížka zeď nezesiluje a jen zakáže tahy úhlopříčně a koněm přes buňky zdi. Anglická věta na sprintu spadla na
chybě (`dict(EN, **SPRINT_EN)` s číselnými klíči), test ji teď hlídá.

Co zbývá:

| Co | Stav |
|---|---|
| Slezská zimní liga 3–4 | Nejlepší postup obíhá ke kontrole 4 jižně (+12 s). Severní mezera do úzkého pásu u kontroly má asi 2,4 m a zavře ji pás ceny plotu olivové plochy (90 s, platí od kontroly tras 2), ne zeď. Ty jsi vešel ze severu. |
| Plot s háčky na sprintu | Silná čára s háčky je teď neprůchodná (zeď), tenká s háčky dál 90 s. Otázka 32 uzavřená 21. 10.: plot zůstává zavřený, na Žebříčku B 7–8 je posunutá GPS. |
| Zídka bez teček | Čára 0,7–1,25 m bez teček zůstává cestou nebo hranou (hrana silnice je stejně tlustá). Zídku bez teček appka nepozná. |
| Mapy sprintů v jiném rozlišení | Prahy (1,25 m, 0,7 m, tečky do 3 m) jsou změřené na mapách 0,27 a 0,40 m/px. Na hrubší mapě (Livelox 1,33 m/px) se tloušťka zdi už změřit nedá; pravidlo by tam chtělo znovu ověřit. |
| Nápověda | Postup v Garmin Connect a Livelox je napsaný podle slov, která appka už používala; proti současnému vzhledu těch webů jsem ho neověřoval (otázka 33). |
| Zálohy na serveru | Kam (jiný disk nebo stroj) a jestli server má cron: otázka na tátu 10. |
| Pomalé testy | Prošly všechny (38) na konečném kódu, jednou po částech (regrese 3:31, web 7:05, ostatní 10:36); během regrese běželo asi 20 s kreslení obrázků zdí, jinak nic. |

## Noc 19. → 20. 10.: proč právě pro tebe, sprinty, kategorie (větev `pro-tebe-a-sprint` z `main`, nesloučená)

Popis PR: `docs/pr-popis.md`; rozhodnutí: `docs/rozhodnuti.md` (poslední část); čísla: `docs/pro-tebe.md` a
`docs/validace.md` (část 20). `main` obsahoval `foto-mapy`, `kontrola-tras-2` i faktor délky závodu; větev
`snimky-livelox` (13 commitů) v `main` není a do téhle větve jsem ji nebral.

| Bod zadání | Stav |
|---|---|
| 0.1 Únava 1–3 | hotovo: pod výběrem i v poznámce panelu |
| 0.2 README, verze | hotovo: README podle skutečnosti, `docs/New Text Document.txt` smazaný, `VERSION = "2026.10.19"` |
| 0.3 Mrtvý kód | hotovo: `attack_point` pryč, `jointfit.py` v `tools/`; zlaté soubory beze změny |
| 0.4 Klub z nastavení | hotovo: `OB_CLUB_NAME`, `OB_CLUB_LOGO`, klíč `ob-rezim` (bez něj platí `skob-rezim` klubového webu) |
| 0.5 CSRF mimo `auth.py` | hotovo: `webapp/security.py`, testy beze změny |
| 1. Proč právě pro tebe | hotovo: postup průměrného běžce, věta, čára, souhrn na stránce modelu; `docs/pro-tebe.md` (na 6 ze 177 úseků devíti závodů je tvůj postup jiný a rychlejší, na 4 jiný, ale skoro stejně) |
| 2. Sprintové mapy | hotovo: šedá budova = budova, dlažba a průchod = cesta, jen na mapách s plnou šedou; ověřeno na sprintu MSK (obrázky před a po) a třech lesních mapách (obrázky bajtově stejné); seznam podezřelých na devíti závodech nevzrostl (26 → 26). **Neověřeno:** Žebříček B po opravě (nedopočítal se), Slezská zimní liga jen čísly |
| 3. Stopa vedle cesty | hotovo jedním commitem se zlatými soubory a novým `personal_model.json`; tři z pěti úseků z tabulky níže se přiblížily, dva vzdálily (`docs/validace.md` část 21) |
| 4. Kategorie z ORIS | hotovo: „Běžel jsem jinou kategorii“ a „Přidat závod z ORIS“ podle čísla nebo odkazu |

**Co se stalo s pamětí:** dvakrát zastavil Claude Code kolo všech závodů, protože počítači docházela paměť. Kolo 2
(po sprintové opravě) při volných 2,3 GB z 15,7 GB, doběhly Azymut E4, E5, Pohora a sprint MSK. Kolo 3 (konečný kód)
i se zavřeným Chromem a Discordem, doběhlo devět závodů, chybí Žebříček B. Kontejnery, které ještě běžely, jsem
zastavil a kola znovu nepouštěl. Přepočet zlatých souborů a modelu (6 min) doběhl.

Co zbývá:

| Co | Stav |
|---|---|
| Žebříček B | V kole 3 se nedopočítal (paměť). `kontrola/dc.sh sh /app/kontrola/noc3/run.sh 3 zebricek-b` (asi 4 min), pak `tools/pro_tebe.py` a `tools/podezrele.py` na `kontrola/noc3/kolo-3/*`. |
| `data/*/fit_samples.npz` | Jsou ze 6. 10.; nový `personal_model.json` je ze vzorků přepočítaných mimo `data/` (`data/` se necommituje). README to říká. |
| Nové podezřelé úseky Azymut E4 | Čtyři úseky skupiny B (tvoje stopa oceněná pomaleji, než jsi běžel) přibyly, protože nový model je pomalejší a E4 jsi běžel rychleji, než čekají ostatní závody. Rozhodne až víc závodů v modelu. |
| Zdi na sprintu | Silná černá čára (zeď, ISSprOM 515) se čte jako cesta; postup MSK 14–15 přes ni vede u dvora. Je to další krok sprintového čtení. |
| Věta u úseků lišících se jen strmostí | „Průměrný běžec by běžel jinudy“ nepojmenuje kudy (Grand prix Silesia E4 6–7). Lepší: podle místa s nejvíc klesáním („seběhl by údolím po cestě“). |
| Průměrný běžec do kopce | Učebnicový sklon (Naismith) je přísnější než u běžců: proti němu jsi do kopce o 42 % rychlejší. Lepší průměr by byl z klubu (aspoň tři běžci s vlastním exportem). |
| Pomalé testy | Prošly všechny (38) na konečném kódu se zlatými soubory, ve třech bězích po sobě (regrese 3:36, web 6:53, fotky a ostatní 10:59), nic jiného nepočítalo. |


## Noc 17. → 18. 10.: fotka papírové mapy (větev `foto-mapy`, z `kontrola-tras-2`, nesloučená)

Celý zápis s čísly je v `docs/foto-mapy.md`, rozhodnutí v `docs/rozhodnuti.md` (část „Fotka papírové mapy“), popis
PR v `docs/pr-popis.md`. **Po sloučení** se databáze doplní sama (nové sloupce `classes.course_*`, tabulka
`photos`); nic se nepřepočítává.

Co se změnilo pro tebe:

- **Fotku mapy s tratí nahraješ jako dřív obrázek** (Podklady → Mapa s tratí). Aplikace ji otočí podle EXIF, vyrovná
  světlo, najde okraj listu na stole, narovná ji, najde kolečka a usadí podle tvé stopy v časech ražení. Uloží ji
  narovnanou, severem nahoru a bez stolu. U mapy je štítek „Mapa z fotky, přesnost asi ±N m“.
- **Když se neusadí**, úloha řekne česky proč a co s tím, a vedle je **Usadit fotku ručně**: klikneš na fotce aspoň
  na 4 kontroly, aplikace ukáže u každé odchylku v metrech a tvoji stopu přes fotku; Uložit. Jde to i na mobilu.
- **Trať, mezičasy, ztráty a chyby u kontrol** jsou s fotkou stejné jako s KMZ (ověřeno na umělých fotkách Pohory
  a Petřvaldu, 37 úseků). **Nejlepší postupy z fotky nejsou** (terén jen z KMZ bez tratě), stránka to napíše.
- **KMZ fotku nahradí** (a pustí analýzu kategorie znovu, plány zůstanou); fotka KMZ nepřepíše.
- Sprintové mapy (kolečko 24 m) se teď usadí i jako obrázek z Livelox; dřív ne.

Co zbývá:

| Co | Stav |
|---|---|
| Skutečná fotka | `data-extra/foto/` nebyla, všechno je z umělých fotek. První skutečná fotka je nejlepší test; když nesedí, pošli mi ji. |
| Závod mimo ORIS (bez oficiálních mezičasů) | Fotka se usadit nedá ani ručně (polohy kontrol jsou z časů ražení). Další krok: ruční usazení dvojicemi „bod na fotce + bod na mé stopě“. |
| Prohnutý papír | Korekce z kontrol pomáhá jen tam, kde je prohnutí větší než šum GPS (2 % šířky: rohy 30 až 55 m místo 15 až 20 m). Lepší by bylo měřit zakřivení na okraji listu (je ostrý a přes celou fotku). |
| Oříznutá šikmá fotka (okraj listu není celý vidět) | Kontroly sedí, rohy mapy mohou ujet o stovky metrů; štítek přesnosti to řekne jen hrubě. Pomohl by okraj listu, i když je vidět jen ze tří stran. |
| Bílý nebo šedý stůl | Okraj listu se od něj nepozná (barevností), perspektiva je pak jen z kontrol. Neměřeno, generátor dělá jen dřevěný stůl. |
| Ohnisko mobilu | Bere se z EXIF; bez něj 0,65 úhlopříčky. Fotka bez EXIF (poslaná přes WhatsApp, snímek obrazovky) má u šikmých fotek o pár procent horší poměr stran listu. |
| Mapa na dvou listech (výměna mapy) | Odmítne se s větou; spojit dvě fotky do jedné tratě neumím. |

Otázky z téhle noci jsou na konci (25 až 28).

## Noc 10. → 11. 10.: kontrola tras podruhé (větev `kontrola-tras-2`, nesloučená)

Celý zápis je v `docs/kontrola-tras.md` (část „Druhá noc“), popis PR v `docs/pr-popis.md`. Větev je z `kontrola-tras`, PR míří do ní. **Po sloučení:** `docker compose up --build` a u každého závodu **Přepočítat postupy** (pruh se ukáže sám: verze postupů 4, záchytných bodů 6).

Co se změnilo pro tebe:

- **Seznam podezřelých úseků** (`tools/podezrele.py`): bez koukání na obrázky řekne, kde jsi byl zřetelně rychlejší, než model dovolí nejlepšímu postupu. Na deseti závodech ukázal 34 úseků; pět z nich byla skutečná chyba čtení nebo výpočtu, o které jsme nevěděli (níže).
- **Uvnitř zástavby se smí jen po ulici.** Obrysy domů, ploty mezi pozemky a okraje pozemků uvnitř olivové plochy jsou zakázaný prostor, ne cesta. Nejlepší postupy na Petřvaldu se tím nezměnily (už vedly po ulicích), ale přes pozemek teď vést nemůžou.
- **Tvoje stopa na Petřvaldu 10–11** vychází 7:03 (naměřeno 7:33); po minulé noci 9:30. Stopa ulicí zabíhala chybou GPS do zahrad a oceňovala se tam chůzí.
- **Náběhový bod** je uvnitř svého úseku: aspoň 25 m od předchozí kontroly, nejvýš 70 % délky úseku před kontrolou, úsek pod 80 m žádný. Petřvald 8–9 ho teď nemá. Změnilo se 17 z 67 kontrol; deset kontrol je bez náběhového bodu (dřív dvě).
- **Záchytný bod za oplocenkou** se neukáže, nebo má v panelu „obchůzkou N m, nejdřív na azimut X° (přímo je překážka)“ a na mapě čáru po obchůzce. Oplocenka a rybník se udávají od nejbližšího místa plotu nebo břehu („oplocenka, nejblíž 38 m“), ne od středu.
- **Mapa až k okraji obrázku** (sprint, výřez) už nemá podél okraje 85 m zakázaného pásu. Cíl sprintu MSK v něm ležel.
- **Když postup neexistuje** (kontrola v uzavřeném dvoře), vede se co nejblíž; dřív byl „nejlepší postup“ beze slova přímka přes domy.

Co se nerozpozná nebo nesedí (stav po téhle noci):

| Co | Stav | Proč |
|---|---|---|
| Skály a srázy (201, 202) | Nečtou se. | Změřeno: jediný znak čitelný na mapě 1,33 m na pixel (černá širší než čára silnice) dává na čtyřech mapách bez srázů 68 až 352 nálezů a na Bludišti mezi největšími nálezy samé domy. Chce to mapu ostřejší než 1,33 m na pixel. |
| Hustá kamenitá půda, ploty se dvěma čárkami | Nezkoušel jsem. | Seznam podezřelých jim nepřipsal žádný úsek. |
| **Sprintové mapy: šedé budovy** (opraveno 19. 10., `docs/validace.md` část 20) | **Postup vede skrz dům.** Šedá budova (ISSprOM 521) užší než asi 9 m se čte jako „cesta“. Viděno: sprint MSK 11–12, 13–14 a 14–15 (na Slezské zimní lize a Žebříčku B se úzké šedé budovy čtou stejně). | Čtení je laděné na černé budovy lesních map. Oprava je nové rozpoznávání (šedá plocha = budova) a našel jsem ji až v posledním kole, kde se nové rozpoznávání dělat nemělo. Barva je přesná (128, 129, 132), šlo by to. |
| Sprintové mapy: zpevněná plocha (opraveno 19. 10.) | Světle hnědá výplň se čte jako polootevřený prostor (činitel 0,85), ne jako cesta. | Totéž. |
| Dvě mapy v jednom obrázku (výměna mapy) | Grand prix Silesia E2: usazená je jedna, kontroly 1 až 13 leží 30 až 150 m od stopy. Analýza to nepozná a nehlásí; seznam podezřelých takové úseky vynechá. | Chce to poznat druhou mapu a usadit ji zvlášť. |
| Severní čára přes rybník | Opraveno: severní čára, která má vodu z obou stran, je voda. Žádný postup deseti závodů tím pruhem nevedl. | |
| Stopa vedle cesty (hotovo 19. 10., `docs/validace.md` část 21) | Stopa vedená 10 až 20 m vedle cesty (posun GPS, špatné usazení mapy) se oceňuje terénem vedle cesty; pět úseků má proto „tvoji stopu“ o 15 až 55 % pomalejší než skutečnost (Azymut E4 2–3, 11–12, 18–19, Pohora 8–9). | Oprava by změnila ocenění každé stopy a všechny zlaté soubory; je to změna modelu. Otázka 20. |
| Krátký doběh do cíle | Model je na 30 až 100 m doběhu o 15 až 45 % pomalejší než ty (šest závodů z deseti). | Není chyba mapy; sprint do cíle model nezná. |
| Čtyři nenalezené oplocenky, neprůchodný plot (518), železnice ve skriptech | Beze změny (viz minulá noc níže). | |

Co jsem prohlédl a co ne (poctivě):

- **Čtyři původní závody (71 úseků):** všech 71 obrázků úseků jsem otevřel jednou po opravách částí 1, 2 a 2b (v kolech 1 a 2; u pěti dlouhých úseků Petřvaldu jen celkový obrázek, ne všechny kusy ve velikosti 1:1). V posledním kole jsem znovu otevřel jen čtyři obrázky, které se změnily (Azymut E4 S–1, Petřvald 6–7, 10–11, 17–18); zbylých 67 je bajtově stejných jako ty, které jsem viděl (`tools/kontrola.py --proti`). Zadání chtělo všech 71 otevřít dvakrát.
- **Šest extra závodů (123 úseků):** otevřel jsem 69 obrázků úseků, u každého závodu aspoň polovinu: Grand prix Silesia E2 14 z 26, E3 9 z 15, E4 11 z 18, sprint MSK 11 z 20, Slezská zimní liga 14 z 27, Žebříček B 10 ze 17. Většinu v kole 1 nebo 2; z kola 3 jen změněné.
- **Seznam podezřelých:** všech 34 výřezů výchozího seznamu.
- **Záchytné body:** obrázky všech 19 kontrol Petřvaldu v posledním kole a po jedné kontrole s oplocenkou na Pohoře (5), Azymutu E5 (12) a E4 (2). U ostatních kontrol a u extra závodů jen čísla z porovnání kol.
- **Přehledové listy:** jen list „černá širší než 9 m“ z Bludiště (pokus se srázy). Listy plotů a oplocenek jsem znovu nedělal; jejich čtení se neměnilo, kromě toho, že oplocenka s kontrolou uvnitř se nepočítá.
- **Web:** Petřvald přepočítaný úlohou webu na vývojové instanci (`/data/kontrola-tras` ve svazku `obdev_ob_data`, účet `kontrola`), úloha doběhla za 4 min 41 s, verze postupů 4 a záchytných bodů 6. Tři snímky přes `tools/shot.mjs` bez chyb JavaScriptu, dva jsem viděl: u 5–6 je v panelu „křížení cest 110 m od kontroly na azimut 330°, ke kontrole z křížení cest obchůzkou 125 m, nejdřív na azimut 105° (přímo je překážka)“, u 12–13 „náběhový bod: oplocenka 38 m před kontrolou“. **Čáru obchůzky na mapě jsem na zmenšeném snímku s jistotou nerozeznal**; že ji `map.js` kreslí z `via`, je jen v kódu. Ostatní tři závody jsem úlohou webu nepouštěl. Kontejnery jsem zastavil.

Otázky z téhle noci jsou na konci souboru (20 až 24). Seznam podezřelých: na začátku 32, na konci 28 ze 134 posuzovaných úseků (stejná pravidla; `docs/kontrola-tras.md`).

*(Níže je stav z 10. 10.; co z něj už neplatí: uvnitř zástavby už černé čáry cestou nejsou; „z 113 úseků šesti extra závodů“ je správně 123.)*

## Noc 9. → 10. 10.: kontrola tras očima (větev `kontrola-tras`, nesloučená)

Celý zápis je v `docs/kontrola-tras.md`, popis PR v `docs/pr-popis.md`. **Po sloučení:** `docker compose up --build` a u každého závodu stisknout **Přepočítat postupy** (pruh se ukáže sám: verze postupů je 3, záchytných bodů 5).

Co se změnilo pro tebe:

- **Analýza už nekončí výpisem chyby.** Tři chyby z webu jsou zreprodukované na mapách z `data-extra/` a opravené: záznam spuštěný pozdě (Grand prix Silesia E3) se spočítá, úseky bez stopy mají „nedostatek dat“; sprintové mapy 1:4 000 se čtou (kolečka 12 m); aktivita bez GPS se nespáruje a u ručního spárování řekne „V záznamu není GPS stopa…“. Věty jsou ve `webapp/texts.py` (`ANALYSIS_ERRORS`), výpis je pod „Podrobnosti“.
- **Start je střed trojúhelníku.** Na Pohoře byl 44 m vedle (v číslici 16), na Petřvaldu 93 m (na čárce startu času). První úsek se tím mění u všech čtyř závodů.
- **Řada teček, plot s čárkami a obrys zakázaného prostoru už nejsou cesta.** Plot je „těžko překonatelný“ (90 s).
- **Plán** se oceňuje se stejnými překážkami jako nejlepší postup a řekne, co kříží.
- **Zarážka** bere směr z tvé stopy, když jsi ke kontrole doběhl bez bloudění.

Co se nerozpozná nebo nesedí (stav po téhle noci):

| Co | Stav | Proč |
|---|---|---|
| Skály a srázy (201, 202) | Nečtou se. Silná černá čára srázu je „cesta“. | Na čtyřech mapách z `data/` na trasách nejsou. Na Grand prix Silesia E2, E3 a E4 jsou a postupy po nich místy „běží“ (E3 úsek 2–3: 42 m). Zoubky mají na mapě 1,33 m na pixel dva až tři pixely; pravidlo, které by je bralo, by bralo i okraje silných čar silnic. |
| Hustá kamenitá půda (tečky těsně u sebe) | Tečky, které se v obrázku dotýkají, splynou a čtou se jako cesta. | Viděno na Grand prix Silesia E4 (úsek 9–10). Osamělé tečky a řady teček už cestou nejsou. |
| Plot, který nic neuzavírá | Pozná se jen se třemi čárkami v řadě na jedné straně. Na čtyřech + jedné mapě nalezeno 11 kusů, všechny skutečné; mnoho plotů se nepozná. | Plot u pole na Petřvaldu S–1 má tři čárky a třetí splývá s koncem cesty: zůstal „cestou“. Dvě čárky nestačí schválně. |
| Neprůchodný plot (518) | Nerozlišuje se od průchodného, obojí stojí 90 s. | Dvojitá čárka se na hrubé mapě nepozná. |
| Oplocenky | Beze změny: 18 na čtyřech mapách, všechny skutečné; dvě u kontroly 5 na Pohoře a dvě u kontroly 15 na Petřvaldu se nepoznají. Na mapě Bludiště (Grand prix Silesia E3/E4) nalezeno 21, prvních devět na listu jsem viděl, všechny skutečné. | Nesahal jsem na pravidlo, aby nepřibyly falešné. |
| Sprintové mapy (ISSprOM) | Analýza doběhne, trať a mezičasy sedí. Terén se čte pravidly pro lesní mapy: zdi, šedé budovy a dlažba nejsou ověřené. | Tři sprinty z `data-extra/` jsem viděl jen na přehledech a pár úsecích. |
| Železnice ve skriptech | `run_race.py` ji bez `--barriers` nezná (zlaté soubory); web ano. Petřvald 1–2, 4–5, 14–15 a 16–17 ji ve skriptu kříží mimo přejezd. | Podle zadání; `run_race.py` má nově `--barriers` a `--alternatives`. |
| Web po téhle noci | Čtyři ukázkové závody jsem po všech změnách nechal spočítat úlohou webu ve vlastní složce vývojové instance (`/data/kontrola-tras` ve svazku `obdev_ob_data`, účet `kontrola`, heslo `kontrola-heslo`): všechny čtyři úlohy doběhly, verze postupů 3 a záchytných bodů 5, Petřvald s železnicí z OSM (2 čáry, 3 přechody), 7 šrafovanými plochami a 8 oplocenkami. Pět snímků přes `tools/shot.mjs` bez chyb JavaScriptu (Petřvald 1–2 a 10–11 na 1440 px, 1–2 na 390 px, Pohora 14–15 na 1440 a 390 px); **prohlédl jsem dva** (Petřvald 1–2 na 1440 px, Pohora 14–15 na 390 px). Na Petřvaldu 1–2 nejlepší postup obíhá k přejezdu, panel říká „Tvoje stopa kříží železnici mimo přechod“ a zarážka je „vlevo cesta 17 m, rovně oplocenka 24 m, vpravo oplocenka 21 m“ (směr z tvé stopy: oplocenka je za kontrolou, jak jsi kreslil). | Větu u selhané úlohy a značku u plánu jsem na stránce neviděl (jen v testech); snímek 390 px jsem viděl zmenšený, čitelnost textu a šířku tabulky úseků z něj neposoudím. Kontejnery jsem zastavil. |

Co jsem prohlédl a co ne (poctivě):

- Kolo 1: všech 71 obrázků úseků čtyř původních závodů (67 kontrol + 4 doběhy), podezřelá místa ve zvětšení.
- Kola 2 a 3: jen úseky, u kterých se změnil nejlepší postup nebo zarážka (`tools/kontrola.py --proti` a porovnání výpisů), ne všech 71 znovu.
- Extra závody: šest spárovaných (113 úseků) je spočítaných; na obrázcích jsem viděl přehledy a asi 12 úseků (Grand prix Silesia E2, E3, E4). Sprint, Slezskou zimní ligu a Žebříček B jen jako čísla.
- Zarážky: nové pravidlo jsem viděl na jednom výřezu (Azymut E5 kontrola 2), ostatní jako čísla ve výpisu.

Čtyři mapy z `data-extra/` se nespárovaly s žádným během z exportu a nepočítaly se: **10. SZL MSKS** (žádná aktivita na mapě), **Mistrovství oblasti v nočním OB** (závod z října 2023, v exportu není), **Grand prix Silesia E1** (běh z toho dne nemá GPS), **3. Zkouška sirén 2024/2025** (běh z toho dne prošel jen 6 koleček z 26). Jestli k nim záznam máš jinde, nahraj ho.

Otázky z téhle noci jsou na konci souboru (15 až 19).

*(Níže je stav z 8. 10.; co z něj už neplatí: „Cesta je pořád i plot“ platí jen pro ploty bez tří čárek v řadě; „Kolem úzkého rybníka je pás bažiny“ je opravené; „Ocenění plánovaného postupu zákazy dál nezná“ je opravené; „Směr zarážky je směr posledních 40 m nejlepšího postupu“ platí jen tam, kde stopa ke kontrole nedoběhla nebo je na úseku bloudění.)*


## 8. 10. večer: postupy přes rybník a oplocenku, zarážka, „rychlejší než nejlepší“, jen vybraný úsek

**Co po sloučení nebo sestavení udělat:** `docker compose up --build`, otevřít Petřvald a v pruhu nad mapou stisknout **Přepočítat postupy** (celá analýza, asi 3 minuty; spočítá i nové zarážky). Stejný pruh se ukáže u každého závodu s postupy ze starší verze. Na tvůj svazek jsem nesahal.

Co jsi hlásil a co s tím je:

- **S–1 vedl rybníkem a oplocenkou.** Rybník je úzký (8 m): četl se jako bažina a jeho černý břeh jako cesta. Teď je modrá plocha s černým břehem voda celá i s břehem, a uzavřená oplocenka je pro postupy neprůchodná. Na vývojové kopii vede S–1 těsně nad rybníkem, obě možnosti kolem oplocenky.
- **1–2: „běžený 3:01“ rychlejší než „nejlepší 3:18“.** Model rychlosti to není. Přeběhl jsi železnici mimo přejezd; nejlepší postup ji smí přejít jen na přejezdu u silnice, proto obíhá. Ocenění tvé stopy zákazy nezná. Bez železnice by nejlepší postup vyšel 2:41 (418 m). Panel to teď řekne („Tvoje stopa kříží železnici mimo přechod…“) a místo označí. Totéž u 14–15. **Jestli se přebíhat smělo, přepni v Nastavení závodu „Železnice a dálnice“ na „nepoužívat“**; já to nepřepínal. Řádek se jmenuje „tvoje stopa“, protože „běžený“ vypadal jako naměřený čas.
- **Zarážka u dvojky byla „konec cesty 65 m“.** Zarážka je teď to, na co při přeběhnutí narazíš, zvlášť vlevo, rovně a vpravo: cesta, vodoteč, břeh, plot oplocenky, okraj paseky, pole nebo zástavby. Body (konec cesty, kupka) ne. U dvojky vychází na vývojové kopii „vlevo cesta 15 m, rovně cesta 166 m, vpravo oplocenka 22 m“; na mapě je to čárkovaná čára.
- **2–3 náběhový bod:** spletl sis kontrolu, neměnil jsem nic.
- **Při vybraném úseku jsou vidět jen jeho čáry.** Zpět čipem „Celá trať“ na začátku pruhu úseků nebo klávesou Esc.

Co nesedí nebo není hotové:

- **Směr zarážky je směr posledních 40 m nejlepšího postupu.** Když doběhneš odjinud, „vlevo“ a „vpravo“ nesedí s tím, jak jsi běžel. U dvojky přichází nejlepší postup od jihovýchodu, ty od jihu: oplocenka proto vyšla „vpravo“, ne „rovně“, a cesta východně od kontroly se do vějíře nevešla.
- **Vzdálená část zarážky je slabá.** „Rovně cesta 166 m“ u dvojky je černý obrys úzké plochy 166 m daleko, první věc tím směrem. Je to pravda, ale zastaví až po minutě běhu.
- **„Cesta“ je pořád i plot, který nic neuzavírá.** Nejlepší postup S–1 teď vede 118 m „po cestě“, a je to plot s čárkami podél pole. Rychlost po něm model přeceňuje.
- **U kontroly na pasece nebo u pole je zarážkou ta paseka sama** (Azymut E4 kontrola 12: „paseka napříč 15–31 m“).
- **Oplocenka nemá vypínač.** Špatně přečtená by postupy posílala oklikou; dosud bylo všech 18 nalezených na čtyřech mapách skutečných. Stopa přes oplocenku (branka, spadlý plot) dostane větu v panelu.
- **Kolem úzkého rybníka je pás „bažiny“** široký asi 5 m (hustota modré v okolí); bylo to tak i dřív.
- **Prohlédl jsem šest výřezů ze 67 kontrol** (Petřvald S–1, 1–2, 13–14, 14–15; E4 11–12; Pohora 15–16; `docs/validace.md`, část 17), ostatní jen jako čísla ve výpisu. V plánu jsem sliboval všech 67.
- **Zlatý soubor Petřvaldu je nový** (`tests/golden/petrvald/best_legs.csv`, čtyři úseky z dvaceti, rozdíly do 3 s a 7 m); ostatní zlaté soubory jsou bajtově stejné.
- Ocenění plánovaného postupu zákazy dál nezná.

## 8. 10.: náběhový bod před kontrolou, zarážka za ní, názvy podle ISOM

*(Zarážka z téhle části je nahrazená, viz výše; pruh „Přepočítat záchytné body“ teď u starých rozborů nahrazuje „Přepočítat postupy“.)*

**Co po sloučení nebo sestavení udělat:** `docker compose up --build`, otevřít Petřvald a v pruhu nad mapou stisknout **Přepočítat záchytné body** (asi půl minuty, postupy se nemění). Stejný pruh se ukáže u každého závodu, který má postupy a záchytné body ze starší verze nebo žádné. Na tvůj svazek jsem nesahal, takže tam teď pořád vidíš starý stav. **Pomalé testy na konečném kódu nedoběhly** (zastavil je systém kvůli paměti); před sloučením je pusť, příkaz je v `docs/pr-popis.md`.

Proč jsi u 13–14 viděl „křížení cest“ za kontrolou: Petřvald byl ve tvé instalaci spočítaný kódem ze 7. 10. ráno a stránka ukazovala starý návrh (nejbližší křížení do 200 m, na směr nehledí). Nový výpočet ho neměl čím nahradit, protože u toho závodu ještě neběžel. Teď se starý návrh neukazuje nikdy.

Co vychází na vývojové kopii:

- **13–14:** náběhový bod kupka 44 m před kontrolou (na nejlepším postupu), zarážka konec cesty 69 m za kontrolou, zpět na azimut 120°.
- **14–15:** náběhový bod konec cesty 56 m před kontrolou, zarážka oplocenka 47 m za kontrolou.

Co je hotové: směr příchodu podle nejlepšího postupu; zarážka (první linie napříč směrem do 250 m za kontrolou, nebo bližší bodový objekt) v panelu úseku i na mapě; konec cesty, oplocenka a okraj zakázaného prostoru jako vlastní druhy; deset bodových značek ISOM čtených z obrázku mapy; názvy podle českého ISOM 2017-2. Čísla a dvanáct kontrol prošlých podle mapy: `docs/validace.md`, část 16. Rozhodnutí: `docs/rozhodnuti.md`, část „Náběhový bod, zarážka a názvy podle ISOM 2017-2“.

Co hotové není nebo nesedí:

- **Plot, který nic neuzavírá, je pořád „cesta“** a jeho roh nebo místo, kde k němu dojde cesta, „křížení cest“ (viděno u plotů zástavby: Petřvald kontroly 9 a 15). Poznám jen uzavřenou oplocenku s čárkami dovnitř.
- **Některé oplocenky se nepoznají**: když plochu kříží vrstevnice, když jsou čárky u sebe nebo když leží u okraje mapy (čtyři viděné: dvě u kontroly 15 na Petřvaldu, dvě u kontroly 5 na Pohoře). Jejich rohy pak můžou vyjít jako křížení.
- **Zelená čárkovaná hranice porostu** se místy čte jako cesta (Petřvald 17–18: „křížení“ cesty s hranicí porostu jako náběhový bod).
- **Náběhový bod na hraně úhlu**: bod 69° stranou od směru příchodu ještě projde (Azymut E4 13–14), i když je jiný víc ve směru. Zkusil jsem vážit úhlem; změnilo to 14 kontrol a neměl jsem čas je všechny prohlédnout, tak je to vrácené.
- **Bodové značky z hrubých map** (Livelox, 1,33 m na pixel): jen kupka a výrazný strom. Ostatní potřebují obrázek ostrý aspoň 0,9 m na pixel (Petřvald má 0,59).
- **Nečte se:** výrazný keř (418), krmelec (527), mohyla (526), pramen (312), skupina balvanů (207), protáhlá kupka (110), skály a srázy, kamenná pole. Značka, která se dotýká vrstevnice nebo cesty, se nenajde.
- **Tvary značek jsem neporovnal s kresbami v PDF**: přečíst z něj šel jen text (čísla a názvy), vykreslit ho nebylo čím. Tvary beru z normy, jak ji znám, a z výřezů čtyř map.
- Výpočet na Petřvaldu trvá 35 s (první verze 23 s), na mapách z Livelox 7 až 9 s.

## Kde to je

- **Větev `co-chybi`** (z `main`, pushnutá, nesloučená). Co přináší, je v `docs/pr-popis.md`. `main` zůstal na `2158d9f`.
- **Pozor, první commit větve není můj:** v pracovním stromu na `main` ležela necommitnutá práce ze 7. 10. večer (registrace s kódem od správce, neměnná registračka, testy a dokumentace k tomu). Commitnul jsem ji beze změny jako první commit větve (`6516e2b`), aby se neztratila; další kroky na ni navazují. Smazaný `docs/co_chci_pridat.txt` a nový `docs/New Text Document.txt` (stejný text) jsem nechal v pracovním stromu, jak jsem je našel, mimo commity.
- Tvůj svazek `ob_tracker_ob_data` a kontejnery na `http://localhost:8000/ob/` jsem nechal být (běží dál na obrazu z rána; nový stav uvidíš po sloučení a `docker compose up --build`). Účet v něm není; založíš ho s kódem: `docker compose exec web flask --app webapp.wsgi invite BFM0903 --site http://localhost:8000`.
- **Vývojové prostředí `obdev`**: zkoušel jsem v něm ve vlastní složce `/data/co-chybi` uvnitř svazku `obdev_ob_data` (kopie tvých dat z rána v kořeni svazku zůstala nedotčená). Jsou tam čtyři ukázkové závody analyzované kódem větve, účet `cochybi` s heslem `co-chybi-heslo`. Kontejnery jsou zastavené. Podívat se: `docker compose -p obdev -f docker-compose.yml -f docker-compose.dev.yml run --rm -e OB_INSTANCE=/data/co-chybi -p 8010:8000 web` a `http://localhost:8010/ob/`. Uklidit celé: `docker compose -p obdev down -v`.

## Tvoje přání (bývalý `docs/co_chci_pridat.txt`, později `docs/New Text Document.txt`; splněné, soubor smazaný 19. 10.)

- **Příklad formátu registračního čísla (`BFM0000`)**: hotovo v přihlášení, registraci i na stránce zapomenutého hesla (šedý text v poli a věta pod ním), chybová hláška také.

## Co je a není ověřeno

- 8. 10. večer: rychlé testy (173) a linter procházejí, **pomalé (36) prošly** na konečném kódu (11 min 21 s, jednou, samotné). Čtyři závody přepočítané na vývojové kopii, stránka v bezhlavém Chromu (`docs/validace.md`, část 17). Neověřeno: tvůj svazek a ruční proklikání.
- 8. 10.: rychlé testy (167) a linter procházejí; **pomalé (36) na konečném kódu nedoběhly**: pustil jsem je jednou na konci a po sedmi minutách je zastavil systém kvůli nedostatku paměti na počítači; znovu jsem je nepouštěl (příkaz a co je ověřeno místo nich: `docs/validace.md`, část 16, Testy). Zlaté soubory se neměnily a kód, který je vytváří, také ne. Stav ze 7. 10.: pomalé testy běžely dvakrát, první běh shodil jeden test, který čekal, že poslední úlohou po uložení poznámky je přepočet modelu (teď za ním jde ještě ocenění plánu); test jsem opravil.
- Na čtyřech závodech ve vývojovém prostředí: ocenění plánu (Azymut E5, úsek 2–3), záchytné body a bloudění u všech 67 kontrol, z toho deset prošlých podle obrázku mapy (`docs/validace.md`, část 14), čtení šraf (nic falešného, Petřvald stejných 7 ploch).
- V bezhlavém Chromu bez chyb JavaScriptu: panel úseku s tabulkou postupů na 390 px (tabulka 327 px, bez posuvníku) a na 1440 px, část „Kdyby ses ztratil“ a vrstva záchytných bodů, záložka Nastavení závodu na 390 px, přihlášení a registrace (nové snímky v `docs/reference/nase-aplikace/`).
- **Neověřeno:** ruční proklikání v prohlížeči a na skutečném telefonu; kreslení plánu prstem; jestli se záchytných bodů v terénu opravdu dá chytit; svislé šrafování na skutečné mapě; zrušení účtu a zapomenuté heslo jinde než v testech; migrace tvého svazku (testy migrují starou databázi, tvůj svazek jsem nespouštěl); přihlášení za proxy přes https; trať s víc než 20 kontrolami na skutečné mapě.
- 8. 10. v bezhlavém Chromu: panel úseku 13–14 Petřvaldu na 390 px (bez vodorovného posuvníku), značky náběhového bodu a zarážky na mapě, tlačítko „Přepočítat záchytné body“ od stisku po hotovou úlohu (34 s).

## Co větev udělala a co po ní zbývá

### 1. Čas plánovaného postupu podle modelu (hotovo)

- Čára se ocení krátkou úlohou hned po uložení (výpočet asi 1 s na mapě 1,33 m na pixel) a po každé analýze znovu; změněný nebo smazaný plán čísla ztrácí.
- **Úloha počká na právě běžící analýzu** (pracovní proces je jeden). Na prázdné frontě je výsledek za 2 až 4 s, při běžící analýze Petřvaldu až za 3 minuty. Stránka mezitím píše „počítá se…“.
- `route_metrics` nezná zakázané čáry a prostory. Plán vedený přes zákaz proto může vyjít rychlejší než nejlepší postup; věta na to upozorní, ale neřekne, kterým zákazem plán vede.
- Když ocenění selže, stránka napíše, že se plán nepodařilo ocenit; znovu se zkusí při novém nakreslení nebo nové analýze, ne samo.

### 2. Pomocník „ztratil jsem se u kontroly“ (hotovo, s výhradami)

- Co funguje a co ne na čtyřech závodech, je v `docs/validace.md`, části 14 (první verze) a 16 (náběhový bod, zarážka, značky). Stručně: křížení a konce cest, cesty, potoky, rybníky, budovy, oplocenky a bodové značky sedí; paseky většinou; okraje hustníků se neukazují; vrchol z výškopisu nevyšel ani jednou.
- „Křížení cest“ je křížení černých čar mapy (cesta, průsek, plot, který nic neuzavírá, hranice pole). Uzavřená oplocenka, šedý tisk legendy a silnice se už od cest odliší, ostatní z barvy ne.
- V husté síti cest (Azymut E4 kontrola 3, E5 kontrola 6) jsou body skutečné, ale je jich vedle sebe mnoho stejných.
- Prahy bloudění (60 m a 30 s navíc) a váhy bodů jsou odhad; poznámky „ztráta kontaktu s mapou“ v datech pořád nejsou.
- Závody analyzované dřív mají nad mapou pruh s tlačítkem „Přepočítat záchytné body“ (krátká úloha, postupy nemění).

### 4. Nastavení závodu po běžcích (hotovo)

- Když účet toho, kdo nahrál mapu bez tratě, zanikne, výchozí hodnotu závodu už nezmění nikdo (každý má vlastní volbu).
- Ruční čára dál přepočítá postupy všem; je to záměr, ale jeden běžec tak pořád může spustit přepočet ostatním.

### 5. Běhy z Garmin exportu (hotovo)

- Při výpadku ORIS úloha doběhne, nespárované běhy smaže a napíše to (otázka níže).
- Na tvém skutečném exportu (10 074 souborů) jsem novou úlohu nepouštěl; načtení z ORIS ji prodlouží o dobu běžné synchronizace (první asi 3 minuty, další desítky sekund).

### 6 a 7. Účet, šrafy

- Zrušení účtu z profilu a zapomenuté heslo (`reset-code`, `/ob/forgot`): hotovo. Nové heslo neodhlásí jiná přihlášená zařízení.
- Svislé šrafování: čte se, ověřené jen na kreslené mapě. **Zakázaná hranice jednou čarou (ISOM 708) se nečte**: jedna fialová čára se nedá odlišit od spojnice kontrol a není na čem to ověřit. Čtení šraf na Petřvaldu trvá 22 s místo 12 s (jednou na nahranou mapu).

## Nálezy ve výpočtu ze 7. 10.: oba opravené, co po nich zbývá

### 1. Silnice čtená jako budova (opraveno)

- **Osobní model skriptů je ze starého čtení.** `oroute/personal_model.json` a `data/petrvald/fit_samples.npz` vznikly před opravou a nepřepočítával jsem je: změnily by zlaté soubory všech čtyř závodů a čísla v README. Web má model pro každého běžce zvlášť a přepočítá si ho sám při příští analýze.
- **Železnice se z mapy čte jako cesta.** Přejít ji nejlepší postup nesmí díky čáře z OpenStreetMap, ale běžet po ní model považuje za rychlé. Pomocník „ztratil jsem se“ ji také bere jako cestu.
- Měřítko mapy se nebere v úvahu, jen rozlišení obrázku. Sprintová mapa 1:4 000 ověřená není.

### 2. Trať s mnoha kontrolami (opraveno jinak, než bylo navrženo)

- Na skutečné mapě s víc než 20 kontrolami to vyzkoušené není.
- Pořadí z mezičasů se nepoužije, když se počet koleček na mapě liší od počtu kontrol ve výsledcích, když chybí víc než jedno ražení, nebo když je stopa v oficiálních okamžicích daleko od koleček (medián přes 60 m).
- Kontrola ražená dvakrát (motýlek) se nečte.

## Ovládání: co zbývá

| Co | Jak to je | Co by to chtělo |
|---|---|---|
| Překreslení mapy po uložení poznámky | Po uložení (i po ocenění plánu) se vrstvy mapy a tabulka postaví znovu. | Měnit jen barvu stopy a řádek tabulky. Dělat, až se ukáže, že je to na telefonu znát. |
| Přetažení souborů | Soubor jde pustit na konkrétní pole. Samo se nepozná, které KMZ je které. | Rozpoznat mapu s tratí podle fialového tisku; pomalé a neověřené, proto ne. |
| Opakování úlohy | „Zkusit znovu“ je u analýzy, načtení z ORIS a přepočtu modelu. Ocenění plánu a zpracování nahrávky opakovat nejde. | Plán nakreslit znovu, soubor nahrát znovu. |

## Co není hotové jinde

| Věc | Stav | Co by to chtělo |
|---|---|---|
| Model: společný odhad, příčný sklon | Napsaný a změřený (`tools/jointfit.py`), aplikace ho nepoužívá. Záměrně neděláno (zadání). | Víc závodů. |
| Únava, obtížnost závodu | Nezapojeno, záměrně neděláno (zadání). | Aspoň pět závodů s mezičasy. |
| Klubový prior | Napsaný, otestovaný, vypnutý (`OB_CLUB_PRIOR`). Záměrně neděláno. | Aspoň tři další běžce s daty. |
| Prahy typů chyb a bloudění | Nastavené podle oka na čtyřech závodech. | Poznámky „ztráta kontaktu s mapou“ u pár úseků; pak jdou doladit (`oroute/mistakes.py`, `oroute/relocate.py`). |
| Zakázaná hranice jednou čarou (708) | Nečte se. | Mapu, na které by šla ověřit; do té doby ruční čára. |
| Jedinečnost záchytného bodu | Neměří se: křížení v síti průseků je stejně dobré jako osamělé. | Počítat, kolik stejných bodů je v okolí, a podle toho řadit. |
| Vrcholy a jiné tvary z výškopisu | Jen vrchol s převýšením 3 m (ČÚZK) nebo 6 m (AWS) na 45 m; na čtyřech závodech žádný. Kupky, prohlubně a jámy se čtou z kresby mapy, ne z výšek. | Sedla, údolí a hřbety nejsou vůbec. |
| Plot jako linie (516, 518) | Čte se jen plot kolem uzavřené plochy (oplocenka). Ostatní ploty jsou „cesta“. | Odlišit čárky plotu od čárek přerušované cesty; chce to mapy s ploty, na kterých by šlo pravidlo ověřit. |
| Další bodové značky | Krmelec, mohyla, pramen, skupina balvanů, výrazný keř, skály se nečtou. | Mapy, kde jich je aspoň deset, aby šlo ověřit pravidlo „devět z deseti“. |
| Bodové značky z hrubých map | Z obrázků 1,33 m na pixel jen kupka a strom. | Mapy bez tratě v lepším rozlišení (Petřvald má 0,59). |
| Ploty z OSM | Stažené, ale nepoužité (`OB_OSM_FENCES=0`). | Ověřit, že pomáhají. |
| Mapa bez tratě z obrázku, polský výškopis | Záměrně neděláno (zadání). | |
| Usazení obrázku na skutečném skenu nebo fotce | Ověřeno jen na obrázcích z Livelox a na umělém obrázku. | Vyzkoušet na fotce mapy z mobilu. |
| Místo na disku | Nová analýza má asi 4 MB na běžce a závod. Složky starších analýz obrázky dál mají. | Staré `*.jpg` a `terrain.png` ve složkách `races/entry_*` smazat ručně, nebo závody přepočítat. |

## Co je nejisté

- **WinSplits.** Vzorec „normálu“ jsem neviděl v originále. Používám medián výkonnostních indexů a 25 % z očekávaného času.
- **Malé kategorie.** Petřvald H18 má 5 běžců; reference i korelace jsou tam hrubé.
- **Osobní model ve webu se u českých závodů liší od skriptů** kvůli výškopisu ČÚZK (záměrně).
- **Cena „těžko překonatelné“ čáry je 90 s**, koridor alternativ 30 m, penalizace 1,6×, „dá se dojít“ u záchytného bodu 2,5× přímého běhu: odhady, ne měření.
- **Párování podle polohy** bere za „u závodu“ 10 km od centra; ponechání nespárovaného běhu 15 km. U vícedenních závodů s jedním centrem může být etapa dál (v tvém exportu jednou: Bohemia 2025, 16 km); takový běh by se nespároval s jistotou a při 16 km by se ani neponechal.
- **Cookie jen přes https za proxy.** S `OB_PROXY=1` má přihlašovací cookie příznak `Secure`.

## Otázky na Tobiase

1. Večerní práci (kód k registraci, neměnná registračka) jsem commitnul na větev `co-chybi`. Je to tak v pořádku, nebo měla jít zvlášť do `main`? A co se dvěma textovými soubory v `docs/` (smazaný `co_chci_pridat.txt`, nový `New Text Document.txt`): přání je splněné, smím je oba odstranit? **19. 10.: smazané.**
2. Export z Garminu, když ORIS neodpovídá: teď se nespárované běhy smažou a zpráva řekne, že běh ze závodu načteného později je potřeba nahrát znovu. Chceš radši při výpadku ORIS nemazat nic (běžné běhy by pak v aplikaci zůstaly do dalšího nahrání)?
3. Ocenění plánu čeká na běžící analýzu (až 3 minuty). Stačí to, nebo ho mám počítat rovnou ve webovém procesu (asi 1 až 3 s a paměť navíc souběžně s analýzou)?
4. Záchytné body: po přepočtu se podívej na Petřvald 13–14 a 14–15 a na pár dalších kontrol. Sedí náběhový bod a zarážka s tím, čeho by ses chytil? Sedí názvy („zarážka“, „oplocenka“, „konec cesty“, „vrchol“ pro kopec z výšek)? Který druh bodu vyhodit, který chybí?
5. Kdo má měnit výchozí nastavení závodu, když ten, kdo nahrál mapu bez tratě, účet zruší?
6. Má nové heslo ze stránky „Zapomenuté heslo“ odhlásit ostatní zařízení?
7. Ploty z OSM nechat vypnuté? (Doporučuji ano.)
8. Jména ostatních běžců v tabulce „Běžci kategorie“ a u sdílených čar a občerstvovaček: jsou to členové oddílu a veřejné výsledky ORIS. Chceš je tam, nebo jen „jiný běžec“?
9. Obrázky, které skripty generují (`best_legs.jpg` apod.), web už u nových analýz nedělá. Smím smazat i ty u starších analýz?
10. Je železnice v Petřvaldu zakázaná pokyny, nebo jen nebezpečná? Výchozí je „zakázáno“.
11. Přepočítat i osobní model skriptů (`oroute/personal_model.json`) po opravě čtení terénu? Změní zlaté soubory všech čtyř závodů a čísla v README.
12. Máš mapu závodu s víc než 20 kontrolami, se svislým šrafováním nebo se zakázanou hranicí (708), na které by šlo vyzkoušet to, co je ověřené jen na kreslených mapách?
13. Původní otázky z `docs/pruzkum.md` (kde to poběží, mapy v oddíle, soukromí dětí, polské závody) jsem vyřešil výchozími odpověďmi ze zadání; platí?
14. Máš mapy bez tratě v lepším rozlišení než z Livelox (jako Petřvald) a mapu s ploty, krmelci nebo skalami? Na nich by šlo ověřit čtení dalších značek; ze čtyř map to nejde.
15. Start tratě je teď střed trojúhelníku a první úsek na Petřvaldu začíná u čárky startu času a vede přes trojúhelník (značený úsek, 93 m). Sedí to s tím, jak se tam startovalo? Na Pohoře je start o 44 m jinde než dřív: podívej se na S–1.
16. Sprintové mapy: mají se číst pořádně (zdi, průchody, šedé budovy podle ISSprOM)? Je to samostatná práce; teď se na nich jen nic nerozbije. **19. 10.: šedé budovy, dlažba a průchody hotové; zdi zbývají.**
17. Skály a srázy: mapa Bludiště (Grand prix Silesia) by na ověření stačila. Chceš to jako další krok? Pomohla by mapa bez tratě v lepším rozlišení než 1,33 m na pixel.
18. Plot stojí 90 s jako každá „těžko překonatelná“ čára. Je to na obyčejný plot u pole moc? (Nižší cena by chtěla rozlišit 516 a 518.)
19. Čtyři mapy z `data-extra/` nemají v exportu běh (viz výše). Máš k nim záznam jinde, nebo je mám nechat být?
20. Tvoje stopa vedená 10 až 20 m vedle cesty (posun GPS nebo usazení mapy) se oceňuje terénem vedle cesty, takže „tvoje stopa“ vychází u pěti úseků o 15 až 55 % pomaleji, než jsi běžel. Mám stopu do nějaké vzdálenosti od cesty ocenit jako cestu? Změní to „tvoji stopu“ u většiny úseků a všechny zlaté soubory. **Rozhodnuto 11. 10.: ano (do 15 m a souběžně). Hotovo 19. 10.**
21. Sprintové mapy: šedé budovy užší než asi 9 m se čtou jako cesta a postup jimi místy vede; zpevněná plocha je „polootevřený prostor“. Je to první věc, kterou bych opravil (odpověď na otázku 16). Chceš to? **19. 10.: hotovo.**
22. Oplocenka, ve které stojí kontrola, je teď průchozí (branka, nebo špatně přečtený dvůr). Sedí to, nebo má postup končit u plotu?
23. Náběhový bod teď nemá 10 kontrol ze 67 (krátké úseky, nebo nic vhodného blíž než 70 % úseku). Je to tak lepší, nebo má smět být blíž než 30 m od kontroly?
24. Srázy na mapě 1,33 m na pixel číst nejdou (změřeno). Máš mapu se skalami bez tratě v lepším rozlišení, jako je Petřvald (0,59)? Nahrazuje otázku 17.
25. Fotka mapy: můžeš dát do `data-extra/foto/` skutečnou fotku z víkendového závodu a k ní `.fit`? Všechno je zatím ověřené jen na umělých fotkách.
26. Štítek „přesnost asi ±N m“ bere nejméně 15 m a odhad chyby na okraji mapy. Je to srozumitelné, nebo radši jen „mapa z fotky, méně přesná“?
27. Závody mimo ORIS (Azymut): mám udělat ruční usazení fotky dvojicemi bodů (fotka + tvoje stopa)? Bez oficiálních časů se fotka teď usadit nedá vůbec.
28. Když fotku nahraje jiný běžec téže kategorie a sedí líp (menší odchylka), přepíše tvoje ruční usazení. Je to tak dobře, nebo má ruční usazení zůstat vždycky?
29. Průměrný běžec má učebnicový sklon (Naismith, up_k 9). Proti němu jsi do kopce o 42 % rychlejší, ale stoupání
    zatím nebylo důvodem ani na jednom úseku. Je pro tebe „průměrný běžec“ ten z učebnice, nebo radši průměr klubu
    (až budou data aspoň tří běžců s vlastním exportem)?
    **20. 10.: zůstává učebnicový; „průměr klubu“ jako volba, až budou data tří běžců. Teď nic.**
30. Postupy se „liší“ od 30 m od sebe na 20 % délky. Je to tak dobře, nebo chceš rozdíly vidět i u menších odchylek?
    **20. 10.: zůstává.**
31. Kola všech deseti závodů dvakrát zastavil nedostatek paměti (Docker má 7,6 GB, Slezská zimní liga 0,27 m/px je
    nejtěžší). Mám v `kontrola/noc3/run.sh` pouštět každý závod ve vlastním kontejneru, nebo radši Dockeru dát víc
    paměti?
    **20. 10.: každý závod ve vlastním kontejneru, paměť se nepřidává. Hotovo 20. 10. (`tools/kola.sh`).**
32. Silná černá čára s háčky (neprůchodný plot, ISSprOM 518) je na sprintu teď neprůchodná jako zeď; tenký plot
    dál stojí 90 s (otázka 18). Je to tak dobře? Na Žebříčku B 7–8 vede tvoje stopa uvnitř sportovního areálu podél
    západního plotu, jehož jihozápadní roh je na mapě zavřený: běžel jsi venku podél plotu, nebo jsi ho přelezl?
    **21. 10.: uzavřená. Tobias si myslí, že je posunutá GPS (spíš rušená GPS ve městě než posunutá mapa). Plot
    zůstává zavřený podle mapy.**
33. Nápověda „Jak na to“ (`/ob/jak-na-to`): proklikej jednou postup v Garmin Connect („Exportovat originál“,
    Správa dat → Export dat) a v Livelox (Sdílet → Exportovat → Google Earth), jestli názvy sedí se současnými weby.
    **21. 10.: Tobias popsal, jak to opravdu je; nápověda je přepsaná podle něj (noc 21. → 22. 10.).**

34. Zkusíš jednou opravdové dva snímky z Livelox podle nápovědy (5000 × 4000, Capture full size screenshot) a nahraješ
    je k závodu, kde KMZ máme (třeba MSK sprint)? Snímky jsem měřil na umělých obrázcích; s opravdovými porovnám mapu
    i postupy proti KMZ.
35. Opravená stopa: úsek se teď z učení modelu vyřadí (čára není měření). Chceš radši, aby se z nakreslené čáry model
    učil (oficiální čas rozložený po čáře rovnoměrně)?
36. Usadit mapu ručně posune KMZ celého závodu (s tratí všech kategorií i bez tratě) pro všechny, kdo ho mají. Smí to
    každý běžec závodu (jako dnes nahrání mapy), nebo jen ten, kdo mapu nahrál?
37. Přepočítat všechno nechá dosavadní model, když se nový liší o méně než 0,5 %. Je ti ta hranice dobrá?

38. PR #7 (větev `claude/project-thread-qr6fix`, vrácený oddíl o délce závodu v `docs/validace.md`) v `main`
    sloučený není, tahle větev je bez něj. Sloučíš ho, nebo ho mám zahodit?
    **25. 10.: je to jen dokumentace, nechat být, neřešit.**
39. Máš `.fit` z nočního závodu (třeba Mistrovství oblasti v nočním OB 20. 10. 2023, nebo jiný noční s mapou
    z Livelox)? Zpětnou analýzu „kde jsem se ztratil“ jsem v noci vyzkoušel jen na lese a sprintu.
40. Výchozí kruh nejistoty je 50 m. Sedí ti, nebo radši 25 m (na sprintu je 50 m moc: vždycky je v něm nějaká
    ulice)?
    **25. 10.: 50 m v lese, 25 m na sprintu (podle `sprint` z `mapdata.obstacles`). Hotovo 25. 10.**
41. Popis kontroly je teď tvůj (jako poznámka k úseku). Má být společný pro celou kategorii, aby ho stačilo zadat
    jednou (a ostatní ho viděli)?
    **25. 10.: zůstává osobní.**
42. Tlačítko „Moje poloha z telefonu“ je na stránce s poznámkou „jen na trénink“. Nechat, nebo schovat (na závodě se
    mobil s polohou používat nesmí)? Poloha funguje jen přes https.
    **25. 10.: na závodě se mobil s polohou ani podobné pomůcky používat nesmějí: poloha z telefonu i „Teď v lese“
    jsou pryč, stránka je jen rozbor po závodě. Hotovo 25. 10.**

43. Tvoje výřezy obrazovky z Bělé (`noc-2026-10-25-obrazky/`, šest obrázků) na počítači nebyly; pracoval jsem podle
    popisu a podle postupů, které viděl web. Dáš je do `docs/reference/oplocenky-vodotece/tobias/`? Podívám se, jestli
    sedí to, co jsem opravil (hlavně obrázek 1 a 4).
44. Na SZL Zábřeh (sprint ve městě) se 8 dvorů a zpevněných ploch mezi domy čte jako oplocenky (od dřívějška, ne od této noci): postup
    je obejde, i když se tam běžet dá. Mám je na sprintových mapách vypnout (ISSprOM oplocenky kreslí jinak)?
45. Kontrola 4, „rovně na roh/křížení a pak po čáře na jih ke kontrole“: po které čáře? Na jih ke kontrole vede jen
    zelená čárkovaná hranice porostu (tu appka jako linii nečte) a severka. Rada teď vede bez okliky azimutem z
    cesty (75 m), ne po čáře.
46. Oplocenku bez zoubků (jen uzavřená černá čára) appka za oplocenku nebere, aby nezavřela smyčku cest. Potkáš
    takovou někde, kde je opravdu neprůchozí?
47. Na Macu (okno appky, WKWebView): přepni tmavý režim a angličtinu, appku zavři a spusť znovu. Zůstane obojí? Na
    Windows a v Chromu jsem to ověřil (8. 11.), Mac jsem neměl.
48. Garmin Connect na telefonu nebo iPadu: lišta s tlačítkem Načíst vybrané zůstává při posunu tabulky nahoře (na
    telefonu jen spodní řádek lišty, asi pětina výšky). Nepřekáží? Je z ní jasné, co tlačítko udělá?
49. KITL 2025: v ORIS to není etapový závod, ale dva samostatné závody, střední trať 6. 9. (8228) a dlouhá 7. 9.
    (8229); v appce jsou oba se svou disciplínou. V zadání byly etapy 5. a 6. 9. Běželi jste ještě něco 5. 9. (třeba
    sprint v pátek)? Jiný KITL jsem v ORIS kolem těch dnů nenašel (`docs/oris.md`).
50. Přestoupil někdy Tobias nebo táta do jiného oddílu (jiné registrační číslo)? Ověřoval jsem na cizích běžcích z
    výsledků (Jiří Vlach AOV7900 → SFM7900, Matěj Toman LBM0909 → ZBM0919): ORIS ID zůstává, staré závody nesou staré
    číslo. Kdyby to u vás vypadalo jinak, napiš.
51. Tátovy KITL 2025 (H45B, issue 9: nepoznané kontroly 2, 3, 8, 9 a 4, 9): v tátově appce u obou závodů dej
    **Uložit závod do souboru** se zaškrtnutým „přidat i můj běh z hodinek a můj výsledek“ a soubory `.obzavod` dej
    do `data-extra/kitl-2025-09-06/` a `data-extra/kitl-2025-09-07/` (KITL byl 6. a 7. 9., viz 49). Na tomhle počítači
    jsou jen tvoje H16B, a ty sedí: 13 z 13 a 12 z 12 kontrol. `tools/kolecka.py` soubory `.obzavod` čte sám:
    `python tools/kolecka.py --rozbor data-extra/kitl-2025-09-06 data-extra/kitl-2025-09-07`.
52. Mapa, kde appka našla 169 „koleček“ místo 18 (a tátův případ 6 z 19 na Macu): dej ji (KMZ s tratí, případně
    `.fit`, nebo celý `.obzavod`) do `data-extra/kolecka-problem/`. Na všech 30 mapách tady je největší rozdíl 9 kontrol
    (Bohemia 2025 E1, opraveno). Tipuju mapu s jemným rozlišením a tlustou čarou, jako Bohemia E1; nová verze ji
    možná přečte sama.
53. Na Macu: otevři u závodu **Doplnit kontroly** (Podklady, pod mapou s tratí), doplň chybějící kontrolu, ulož
    a počkej na nový rozbor. Funguje klikání a přetahování v okně appky (WKWebView)? Stránka je stejná jako Usadit
    mapu ručně; ověřil jsem ji testy serveru, v okně appky ne.
54. Nahraj u závodu najednou běh a dva snímky, z nichž jeden je moc velký (nebo menší než 400 px). Uloží se ten
    dobrý a hláška řekne jménem, který se nenahrál? Na Macu jsem to nezkoušel.
55. Rozbor jen z mapy s tratí (`docs/jen-mapa-s-trati.md`): nahraj u závodu jen snímek s tratí z Livelox, **se zapnutou
    čárou postupu** a pak bez ní. Odpovídají postupy zhruba tomu, co dává mapa bez tratě? Měřilo se na uměle nakreslené
    červené čáře (asi 4 m); potřebuju od tebe nebo od táty snímky s opravdovou čárou i bez ní z jednoho závodu.
56. Poznámka u úseku, kde postup vede přes hodně zakrytého místa, zatím není. Chceš ji? Stačí jedna věta u úseku.
57. Na Macu v Safari: Web Inspector → Elements → pravým na prvek mapy → Capture Screenshot, nebo uložení obrázku z
    `<canvas>` (`docs/snimky-livelox.md`). Pošli obrázek mapy z canvasu a snímek s tratí ze stejného závodu do
    `data-extra/`; bez nich pole „Obrázek mapy z Livelox“ nepřidávám (napasování nejde změřit).
58. Na Macu v Chromu i v Safari projdi nápovědu Dva snímky z Livelox krok po kroku a napiš, kde to nesedí (zkratky,
    české názvy menu, jestli Safari dá dost velký snímek).
59. Elektrické vedení nebo vlek čtené jako plot (Oblastní žebříček Bílá, 17. 10., postup 11–12, issue 37): na mapách, co
    mám (`data-extra/real-zebricek-2026-10-17`, `bela`, `real-bela-2026-10-18`), žádné vedení není, jen skutečné
    ploty, oplocenky a okraj silnice. Pošli prosím soubor `maponly.kmz` z Bílé 17. 10. nebo napiš číslo kontroly a
    ukaž výřez mapy s tím místem. Pravidlo zatím neměním naslepo: příčky přes čáru, střídavé příčky a čtverce
    pylonů se plotem nečtou (testy), čte se jen jednostranná řada krátkých příček, což je geometricky skutečný
    plot. Mezitím si takové místo opravíš ručně (vrstva Rozpoznané překážky, tlačítko Není překážka).
60. Vrstva Rozpoznané překážky (klávesa 4, kliknutí na plot, oplocenku, čáru z OSM nebo šrafy): v prohlížeči jsem ji
    nezkoušel (jen kontrola skriptu a testy serveru). Zkus na závodě s plotem: zapnout vrstvu, kliknout, Není
    překážka, počkat na přepočet. Drží se vrstva zapnutá a prvek šedý přerušovaný?
61. Zdi sprintové mapy (neprůchozí a přelezitelné) zatím opravit nejde, jen plot, oplocenka, čára z OSM a šrafy.
    Chceš i zdi?

## Otázky na tátu (ze seznamu „Co potvrdit s tátou“)

1. Je klubový web opravdu Flask + SQLite a kde běží (CPU, RAM, disk)? Smí tam běžet druhý proces a úloha z cronu, která občas počítá kolem 3 minut a vezme asi 1,5 GB paměti?
2. Smí vedle veřejného webu bez účtů existovat část s přihlášením pod `/ob`? Kdo zakládá účty a vydává kódy (`invite`, `reset-code`)?
3. „Analýza mezičasů“ z jeho plánu: chce ji dělat sám, nebo vezme naši (`oroute/splits.py`, záložka Mezičasy kategorie)?
4. Má v databázi mezičasy, nebo jen výsledky? Z kterých zdrojů (ORIS, OResults, WinSplits)? Dal by nám je, abychom ORIS nezatěžovali dvakrát a měli mezičasy i pro Azymut?
5. Jak chce sdílet `skob.css`: kopie při nasazení (jako teď), společný balíček, nebo odkaz na jeho `/static/skob.css`? Kdo hlídá, že se kopie nerozejde?
6. ~~Tlačítko z klubového webu na náš rozbor.~~ Tobias 7. 10.: odkaz z klubového webu k nám se nepřidává. Adresy `/ob/zavod/oris-<ID>` a `/ob/clen/<ID>` v aplikaci zůstávají, jen na ně zatím nic nevede.
7. Ví, že odkazy na ORIS vedou na starou doménu `oris.orientacnisporty.cz`?
8. Mapy na serveru: je volných jen 1,6 GB. Kam s nimi, a jak se staví k právům pořadatelů?
9. Proxy: přepošle `/ob/` beze změny cesty a s hlavičkami `X-Forwarded-Proto` a `Host`? Jde všechno přes https (kvůli cookie)? Projde přes Cloudflare nahrání celého Garmin exportu? Tvůj má 47 MB; bezplatný tarif má, pokud vím, limit 100 MB na požadavek (neověřeno).
10. Zálohy: má server cron (pak `docs/provoz.md`, cron na hostiteli), nebo zapnout službu `cron` v compose? Kam
    zálohy (jiný disk nebo stroj)? Jedna záloha je kopie databáze a zrcadlo nahraných souborů (mapy, `.fit`, fotky).
