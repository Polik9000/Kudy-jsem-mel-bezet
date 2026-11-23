# Mapy přes OResults a ČSOS: koho oslovit

Průzkum a názor z 23. 11. 2026. Kód se podle něj zatím nemění. Navazuje na [mapa-bez-kmz.md](mapa-bez-kmz.md).

## Krátce

**Nejdřív OResults, s podporou ČSOS. Kluby až potom a přes ČSOS. Livelox ne.**

ČSOS sám přechází od Livelox k OResults. Livelox zdražil o 80 % a od roku 2027 se mají změnit podmínky. Svaz proto
vyzývá pořadatele, aby mapy nahrávali na OResults. Mapy s tratí se tedy v Česku budou čím dál víc sbírat tam.

## OResults (oresults.eu)

- **Kdo**: česká firma O&J Labs s.r.o. (Praha). Dělají ji Jan Jurica (OK Lokomotiva Pardubice) a Otakar Hirš
  (SK Brno Žabovřesky). Zdroj: [prezentace pro metodiku ČSOS](https://metodika.orientacnisporty.cz/upload/2024/01/OResults-Systemy-pro-prenos-mezicasu.pdf).
- **Co umí**:
  - živé výsledky a online mezičasy;
  - **Aftershow**: přehrávání GPS nad mapou s tratí, srovnání běžců, mezičasy. Od podzimu 2026 ve veřejném
    náhledu, naplno od sezóny 2027 ([dokumentace](https://docs.oresults.eu/start/how-oresults-works/)).
- **Mapy a tratě od pořadatele**:
  - mapa jako OCAD, OOM, GeoTIFF nebo KMZ, **musí být georeferencovaná**;
  - trať jako OCAD, Purple Pen nebo IOF XML se souřadnicemi
    ([nahrání map a tratí](https://docs.oresults.eu/organizers/upload-maps-and-courses/)).
- **Cena**: pro pořadatele zdarma, platí se jen online kontroly.
- **ORIS**: akce se zakládá z ORIS a startovky i výsledky se berou odtud.
- **Hodinky**: Garmin a Polar napřímo, ostatní přes intervals.icu, nebo ručně GPX a FIT.
- **Mapy stáhnout nejdou.** Podmínky §3.3: originální soubory nikdy nezveřejní, uživatel vidí jen vykreslený
  obrázek. Mapy patří pořadateli (§3.2).
- **API je jen pro nahrávání** (`POST /courses`, `/results` a další, [API](https://docs.oresults.eu/developers/public-api/)).
  Čtení map, tratí a tras nejde. V jejich veřejném plánu je:
  - „API access – personal access tokens“ jako **zvažované**;
  - „Georeference a map“ (pořadatel usadí obyčejný obrázek) jako **rozpracované**.
- **Kontakt**: tech@oresults.eu, organize@oresults.eu, Discord (odkaz v dokumentaci), tlačítko Feedback.
- **Rozšíření**: v ORIS je OResults u 83 z 229 akcí od 15. 8. do 22. 11. 2026, Livelox u 33.

## ČSOS

- Livelox platí ČSOS za všechny členy
  ([online nástroje](https://www.ceskyorientak.cz/organizace/benefity/online-nastroje/)).
  - Valná hromada v prosinci 2025: podmínky se „rapidně zhoršují“ a od roku 2027 „proběhnou určité změny“
    ([zpráva](https://www.ceskyorientak.cz/valna-hromada-schvalila-nove-stanovy-csos-i-rozpocet-na-rok-2026/)).
  - Článek z 2. 10. 2026 ([Analyzuj postupy přímo v OResults](https://www.ceskyorientak.cz/analyzuj-postupy-primo-v-oresults/)):
    Livelox zdražil o 80 %. Svaz žádá pořadatele, aby mapové podklady nahráli na OResults.
- OResults je partner ČSOS.
- [Směrnice pro mapy 2026](https://www.ceskyorientak.cz/wp-content/uploads/2026/03/Smernice_mapy_2026.pdf):
  majetková práva má vydavatel mapy. Pravidlo, že se má mapa po závodě zveřejnit, není.
- Kontakt k mapám: Mapová rada ČSOS (předseda podle webu ČSOS).

## ORIS

- Typy odkazů jsou veřejné: `https://oris.ceskyorientak.cz/API/?format=json&method=getList&list=sourcetype`.
  Pro mapy jsou to hlavně:
  - 9 Ukázky mapy;
  - 10 Stará mapa (vede do archivu map ČSOS);
  - 11 OB Postupy / Routechoices;
  - 20 Embargo mapový portál.
- Livelox i OResults bývají jen volné odkazy bez typu. Některé akce mají mapu přímo v ORIS jako soubor (typ 9 nebo 10).
- Stará doména `oris.orientacnisporty.cz` přesměrovává na `oris.ceskyorientak.cz`. Aplikace už používá novou doménu.
  Odkaz na OResults bere z `Links` (`webapp/oris.py`).

## Livelox

Podmínky [API](https://www.livelox.com/Documentation/Api):
- mapy ani trasy přes API nejsou;
- „Do not compete with Livelox“;
- „No personal-use access“;
- přístup schvalují jednotlivě.

Aplikace pro rozbor postupů by neprošla. Smlouva navíc zakazuje stahování mimo API. Livelox je pro mapy slepá ulička.

## Pořadí kroků (názor)

1. **OResults.** Je to česká a malá firma, svaz je podporuje a osobní API mají v plánu. Nekonkurujeme si: oni
   ukazují, kudy kdo běžel, my počítáme, kudy se mělo běžet. O co požádat, od nejmenšího:
   1. přepínač pro pořadatele „povolit stažení mapy s tratí“ (georeferencovaný obrázek nebo KMZ), jako má Livelox;
   2. čtecí API s osobním tokenem: tratě se souřadnicemi kontrol a mapa tam, kde to pořadatel povolí. Už samotné
      souřadnice kontrol pomohou: fotka nebo snímek se usadí bez hledání kroužků (i s červenou tratí);
   3. rozbor přímo v Aftershow (viz níže).
2. **ČSOS**, až odpoví OResults. Svaz mapy nevlastní, ale může pořadatelům doporučit, aby stažení mapy po závodě
   povolovali. Nejlíp přijít s hotovou věcí: „OResults to umí, doporučíte to?“
3. **Kluby jen přes ČSOS.** Přesvědčovat je po jednom je moc práce a místo už existuje: OResults, nebo soubor
   „Ukázky mapy“ v ORIS. Vlastní web na mapy nedoporučuji. Kluby by musely obsluhovat další službu, řešila by se
   práva a [soukromi.md](soukromi.md) slibuje, že aplikace nic nikam neposílá. Vlastní klub se ale zeptat dá, ať
   v Livelox nechává stažení povolené.
4. **Livelox ne.**

## Rozbor přímo v Aftershow

**Nápad**: v Aftershow OResults by šlo zobrazit i „kudy jsi měl běžet“.

**Proč ano**:
- OResults má originální vektorovou mapu a souřadnice kontrol. Je to lepší vstup než KMZ nebo fotka: terén se
  nehádá z barev a kroužky se nehledají.
- Uživatel nic nestahuje ani nefotí, GPS z hodinek už tam je.
- Mapa nikam neodchází.

**Nejlepší postup není jeden pro celou trať.** Každý závodník ho má jiný podle svého modelu rychlosti
(`oroute/personal.py`: rychlost v terénu, ve stoupání, po cestách). Stejný pro všechny je jen postup
**průměrného běžce**. Pro server to znamená:

- **Společné pro mapu** (jednou na mapu): terén, překážky, výškopis, graf buněk.
- **Společné pro trať** (jednou na trať): postup průměrného běžce.
- **Osobní** (pro každého běžce zvlášť): jeho nejlepší postup, ztráty, Ztratil jsem se.

Postup průměrného běžce může být první vrstva v Aftershow. Osobní postupy přijdou, až bude výpočet dost rychlý.

**Co vyřešit**:
- **Licence**: repo je PolyForm Noncommercial a OResults je firma. Potřebovali by samostatnou dohodu s autorem.
- **Vstup**: aplikace čte mapu jako obrázek (`oroute/mapdata.py`, `terrain.classify`), ne OCAD. Na začátek
  stačí vykreslený obrázek s tratí a bez ní. Čtení vektorové mapy by bylo přesnější, ale je to velká práce.
- **Provoz**: výpočet je v Pythonu (`oroute/`) a jde pustit bez webu, takže může běžet jako samostatná služba.
- **Rychlost**: viz další oddíl.

### Úkol: zjistit, jestli jde výpočet zrychlit

Dnes trvá jedna mapa 30 s až 7 min a potřebuje 0,5 až 3 GB paměti ([vykon.md](vykon.md)). Pro osobní postup
každého běžce na serveru je to moc.

Co už je v [vykon.md](vykon.md):
- překážky se počítají třikrát, asi 125 s ze 442 s na Petřvaldu;
- kružnice kontrol se hledají přes celý obrázek;
- `float32` a `uint8` místo `float64` (špička 3 GB je v postupech);
- sdílet terén a výškopis mezi kroky.

Nové otázky:
- Jde graf buněk jedné mapy uložit a osobní model jen přepočítat jako jiné ceny hran, bez nového `routing._build`?
- Stačí hledat osobní postup jen v pruhu kolem přímky a postupu průměrného běžce?
- Jak dlouho trvá jen osobní část, když je společná část v mezipaměti? Hledání cest je dnes asi 79 s ze 442 s.

Změřit přes `tools/profil.py`. Až bude odpověď, zapsat ji sem a do [vykon.md](vykon.md).

## Návrh zprávy pro OResults

> Dobrý den,
>
> dělám zdarma aplikaci „Kudy jsem měl běžet“. Je to lokální aplikace pro Windows a Mac, která z běhu z hodinek
> a mezičasů z ORIS počítá nejlepší postupy, kde se běžec ztratil a jak by to šlo líp. Nic nikam neposílá, data
> zůstávají u uživatele.
>
> Potřebuje mapu s tratí. Když ji pořadatel nedovolí stáhnout z Livelox, musí uživatelé fotit papírovou mapu.
> ČSOS vyzývá pořadatele nahrávat mapy k vám, proto se chci zeptat:
>
> 1. Uvažujete o přepínači pro pořadatele „povolit stažení mapy s tratí“ (georeferencovaný obrázek nebo KMZ)?
> 2. Ve vašem plánu je osobní API. Šlo by přes něj číst tratě se souřadnicemi kontrol, případně mapu tam, kde
>    to pořadatel povolí?
> 3. Šlo by rozbor nabídnout přímo v Aftershow? Na začátek postup průměrného běžce pro každou trať jako čáry
>    (GeoJSON), později i osobní postup podle modelu rychlosti každého běžce.
>
> Vaše Aftershow ukazuje, kudy kdo běžel. Moje aplikace počítá, kudy se mělo běžet, takže by se to doplňovalo.
> Rád pošlu ukázku.
>
> Děkuji, [jméno]
