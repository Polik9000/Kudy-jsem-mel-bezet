# Popis PR: větev `oplocenky-vodotece` → `main`

**Oplocenky, severky místo vodotečí, zarážky, rada bez okliky a stránka „Ztratil jsem se u kontroly“ jen po
závodě. PR obsahuje i větev `ztraceny-u-kontroly` (stránka Ztratil jsem se u kontroly, noc 24. → 25. 10.).**

Větev je z `origin/ztraceny-u-kontroly`, protože ta v `main` sloučená není. **Sloučením tohoto PR se do `main`
dostanou obě.** Do `main` jsem nic neslučoval. PR #7 (jen dokumentace) neřeším (otázka 38). Žádné LLM, placené API
ani nová knihovna.

Kde co je:
- `docs/oplocenky-vodotece.md`: podrobný rozbor Bělé s obrázky před a po;
- `docs/ztraceny-u-kontroly.md`: stránka Ztratil jsem se, režimy;
- `docs/rozhodnuti.md`: poslední dva oddíly;
- `docs/co-zbyva.md`: co zbývá, odpovědi 38 a 40 až 42, nové otázky 43 až 46.

Podklad noci: tvůj závod **Bělá 18. 10. 2026 (H18C)** z webové appky (svazek jsem jen četl), zkopírovaný do
`data-extra/bela/` a přidaný do `tools/kola.sh`. Tvoje výřezy obrazovky na počítači nebyly, pracoval jsem podle
popisu v zadání a podle postupů, které ukazoval web (otázka 43).

---

## Co sloučením dostaneš

### Ztratil jsem se u kontroly (z větve `ztraceny-u-kontroly`, upravené)

- Stránka `/ob/races/<id>/ztraceny`: **rozbor po závodě**. Hlavní režim „Po závodě: kde jsem se ztratil“ ukáže
  místa do 100 m od kontroly, kde jsi podle stopy zpomalil, kroužil nebo se otočil, co tam bylo vidět a kudy ses měl
  vrátit. Druhý režim „Kde jsem asi byl“: ťukneš do mapy, kde jsi asi byl (pro závod bez .fit nebo místo, které
  stopa nechytla).
- **Nic za běhu:** pryč „Teď v lese“, „Moje poloha z telefonu“ i `navigator.geolocation`. Rada je v minulém čase
  („Měl jsi jít…“). U závodu, který je dnes nebo v budoucnu a nemá stopu, odkaz není (jen věta „bude po závodě“).
- Kruh nejistoty: výchozí 50 m v lese, 25 m na sprintu. Popis kontroly zůstává osobní.

### Oplocenky (`oroute/relocate.py`, `oroute/mapdata.py`)

- V Bělé (snímek z Livelox 0,97 m/px) se z 29 oplocenek našlo jen 9: zavírání mezer slilo zoubky s rozmazanou
  čarou a test černé na rozmazané čáře neprošel. Teď všech **29** (a 4 jejich rohy).
- **Plot je v neprůchozí masce taky**: dřív zůstávala čára plotu kolem oplocenky „cestou“ a postupy po ní běhaly
  (Bělá S-1, Petřvald 12-13).
- Branka do 12 m oplocenku neotevře, **neprůchodný plot** (dvojité zoubky, ISOM 518 / 524) je neprůchozí, kontrola
  otevře jen svou oplocenku, plán počítá 90 s za přelezení plotu.
- Nic nového falešného na ostatních 10 mapách (kontaktní archy dřív/teď; sprinty a ostré mapy beze změny pravidel).

### Severky (`oroute/terrain.py`)

- Dřív se severka hledala jen jako svislý sloupec pixelů. Snímek Bělé je pootočený o 0,7°, takže **všech 10 severek
  bylo vodotečemi**: 11 zarážek „vodoteč“ (1-2: „rovně vodoteč 54 m“), 16 „přechodů cesty přes vodoteč“, rada u
  kontroly 4 „podél vodoteče“.
- Teď se hledají pod libovolným úhlem do ±30° jako rovnoběžné čáry ve stejném rozestupu (na všech 11 mapách 300 m,
  resp. 120 m na sprintu). Vodoteč, která severku kříží, zůstane. **Azimuty jsou k severkám** (v Bělé o 0,7°).

### Zarážky a rada

- Zarážka za kontrolou nebere vlastní cestu kontroly (do 10 m) a souběžnou cestu přeskočí, jen když vede přes
  kontrolu. Bělá 1: „rovně cesta 55 m“ (tvoje žlutá) místo „vlevo/vpravo cesta 15 m“.
- Rada „Ztratil jsem se“ nevede oklikou: linie do 100 m od kontroly vede ke kontrole i bez křížení, křížení vyhraje
  jen bez delšího azimutu. Bělá 4: „Byl jsi u cesty, měl ses jí držet. Odtud kontrola 75 m na azimut 150°.“

## Než to sloučíš

- **Verze:** `bestroute.VERSION` 9, `relocate.VERSION` 8 (`results.ROUTES` 9, `results.RELOCATE` 8), `lost.VERSION`
  2. Web pak u starších rozborů nabídne přepočet. **Po sloučení klikni „Přepočítat postupy“** (nebo „Přepočítat
  všechno“).
- **Databáze:** sloupec `leg_notes.control_desc` (z `ztraceny-u-kontroly`) se přidá sám.
- **Goldeny** referenčních závodů jsou přegenerované (viz Testy).

## Co zkontrolovat po sloučení (Bělá)

1. **S-1**: nejlepší postup ani možnosti nejdou přes trojúhelníkovou oplocenku ani po jejím plotu.
2. **4-5**, možnost 3: nejde přes roh obdélníkové oplocenky.
3. **Kontrola 7** (a 1-2): severka není vodoteč; zarážka 1-2 bez „vodoteče“.
4. **Zarážka u 1**: „rovně cesta 55 m“.
5. **Ztratil jsem se u kontroly 4**: bez okliky. Kdyby sis představoval jinou čáru (tvoje žlutá „po čáře na jih“),
   napiš kterou (otázka 45).
6. Stránka Ztratil jsem se: nic tam nevypadá jako pomůcka za běhu (fotky v `docs/reference/oplocenky-vodotece/`).

## Co nefunguje nebo je sporné

- Oplocenka **bez zoubků** (jen uzavřená černá čára) se za oplocenku nebere, aby se nezavřela smyčka cest (otázka 46).
- Sprint SZL Zábřeh: 8 dvorů / zpevněných ploch se čte jako oplocenky od dřívějška (otázka 44).
- „Po čáře“ u kontroly 4 (hranice porostu) appka neumí: hranice porostu není linie rady.

## Testy a měření

- Rychlé testy: **354 prošly**, `ruff` čistý. Nové `tests/test_oplocenky_severky.py` (6, umělé obrázky):
  pootočené plné rovnoběžné severky se poznají a šikmá čárkovaná vodoteč přes ně zůstane; modrá plocha ani jeden
  příkop severky nejsou; oplocenka s brankou 10 m, trojúhelník až do špičky a oplocenka 20 800 m² jsou neprůchozí,
  smyčka cest bez zoubků ne, cesta 6 m od plotu zůstává; kontrola otevře jen svou oplocenku; neprůchodný plot se
  dvojitými zoubky je neprůchozí, obyčejný stojí 90 s; nejlepší postup i možnosti Gridem oplocenku obejdou. Dál
  `test_planned.py` (přelezení plotu v plánu), `test_web_lost.py` (stránka bez `geolocation`, „Teď v lese“, „Moje
  poloha“, ťuknutí dál radí, před závodem bez odkazu) a texty v minulém čase (`test_lost.py`, `test_napoveda.py`).
- Pomalé testy: **38 prošly** (po modulech: regrese 12, web 17, ostatní 9).
- **Goldeny** přegenerované u Azymutu E5, E4, Pohory a Petřvaldu (jen `best_legs.csv`, 8 řádků): úsek po úseku
  s důvodem v `docs/oplocenky-vodotece.md`, oddíl Kola a testy. Úseky a tratě beze změny.
- Kola `tools/kola.sh` 6 až 9 (kolo 9 všech 11 závodů s konečným kódem, 69 min, nejvíc 3,5 GB na SZL): nejlepší
  postupy proti kolu 3 změněné u 0 až 2 úseků na závod; `tools/podezrele.py` (rychlejší než nejlepší postup) 23 před
  i po, stejné úseky.
- Snímky stránky Ztratil jsem se na Bělé (telefon i počítač, oba režimy, závod zítra) v samostatné instanci
  s vlastním svazkem, bez chyb JavaScriptu.
- Neověřeno: tvoje opravdové výřezy obrazovky (nedorazily), skutečný telefon.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
