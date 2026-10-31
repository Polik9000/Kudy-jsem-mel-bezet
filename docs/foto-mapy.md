# Fotka papírové mapy místo KMZ (noc 17. → 18. 10. 2026, větev `foto-mapy`)

**Souhrn.** Fotka papírové mapy s tratí z mobilu se teď usadí sama: aplikace ji otočí podle EXIF, vyrovná světlo,
najde okraj listu na stole, podle něj ji narovná (perspektiva), najde kolečka a usadí je na tvou stopu v časech
ražení; uloží ji narovnanou jako KMZ. Když se neusadí, řekne česky proč, a dá se **usadit ručně** kliknutím na pár
kontrol. Trasa, mezičasy, ztráty a chyby u kontrol jsou pak stejné jako s KMZ; nejlepší postupy z fotky ne.

Na 248 umělých fotkách z osmi map (stejný generátor, kód na začátku a na konci noci):

| | Před | Po |
|---|---|---|
| usazeno automaticky | 119 (48 %) | **236 (95 %)** |
| usazeno dobře (všechny 4 rohy mapy do 50 m) | 94 (38 %) | **221 (89 %)** |
| chyba v rozích: medián / 90 % fotek do | 19 m / 196 m | **16 m / 36 m** |
| chyba na kontrolách: medián / 90 % do | 5,8 m / 12,6 m | **4,7 m / 6,7 m** |
| usazeno špatně (kontroly víc než 30 m vedle) | 1 | **0** |
| náklon 10 / 20 / 30°: dobře | 0 / 0 / 0 z 8 | **7 / 8 / 8 z 8** |
| stín 40 %: usazeno | 1 z 8 | **8 z 8** |
| sprintové mapy (3 z 8) rovně | 0 z 3 | **3 z 3** |
| ruční usazení pěti kliky: usazeno / dobře | – | **244 / 209 z 248** (všech 12 automaticky neusazených, 9 z nich dobře) |
| dobře automaticky nebo ručně | 94 | **232 z 248** |

Co se automaticky neusadí nebo usadí hůř (všechno jsou kombinace více zkreslení):

- **šikmá fotka s uříznutým okrajem** (kombinace 5: náklon 15°, prohnutí, ořez, stín): okraj listu není celý vidět,
  perspektiva jen z kontrol nejde, zůstane plochý model. Kontroly sedí (medián 9 m), rohy mapy 75 až 500 m vedle.
  Odhad chyby na okraji to ukáže (285 až 1000 m) a štítek přesnosti s ním.
- **prohnutí 2 %**: rohy 42 m medián (1 %: 32 m); korekce z kontrol pomáhá jen u map s mnoha kontrolami.
- **rozmazaná fotka 3 Mpx se stínem 40 % nebo odleskem** (kombinace 4 a 6): na sprintových mapách a na Petřvaldu se
  kolečka nenajdou (12 fotek ze 48 kombinací). Úloha řekne, ať se vyfotí znovu, nebo nabídne ruční usazení.
- **odhad chyby na okraji** je u 186 z 236 usazených fotek aspoň tak velký jako skutečná chyba, u 224 aspoň
  poloviční; u prohnutí a sprintu s menším počtem usazených kontrol podhodnocuje (např. Zkouška sirén 10°: odhad 39 m,
  skutečně 98 m).

Celá tabulka po případech (vlevo před, vpravo po; „usazeno / dobře / medián chyby v rozích / medián na kontrolách“):

| Fotka | před: usazeno / dobře / roh / kontroly | po: usazeno / dobře / roh / kontroly |
|---|---|---|
| základní | 5/8 / 5 / 16 m / 5 m | 8/8 / 8 / 15 m / 4 m |
| náklon 10° | 5/8 / 0 / 150 m / 11 m | 8/8 / 7 / 18 m / 5 m |
| náklon 20° | 4/8 / 0 / 366 m / 16 m | 8/8 / 8 / 15 m / 4 m |
| náklon 30° | 1/8 / 0 / 317 m / 30 m | 8/8 / 8 / 15 m / 4 m |
| otočení 37° | 4/8 / 4 / 15 m / 4 m | 8/8 / 8 / 17 m / 4 m |
| otočení 90° | 5/8 / 5 / 17 m / 4 m | 8/8 / 8 / 16 m / 4 m |
| otočení 180° | 5/8 / 5 / 18 m / 4 m | 8/8 / 8 / 16 m / 4 m |
| otočení 250° | 5/8 / 5 / 15 m / 5 m | 8/8 / 8 / 17 m / 4 m |
| EXIF 6 | 5/8 / 5 / 16 m / 4 m | 8/8 / 8 / 15 m / 4 m |
| EXIF 3 | 5/8 / 5 / 18 m / 4 m | 8/8 / 8 / 15 m / 4 m |
| prohnutí 1 % | 5/8 / 4 / 33 m / 5 m | 8/8 / 7 / 32 m / 5 m |
| prohnutí 2 % | 5/8 / 2 / 56 m / 7 m | 8/8 / 6 / 42 m / 6 m |
| stín 40 % | 1/8 / 1 / 25 m / 9 m | 8/8 / 8 / 19 m / 5 m |
| stín 60 % | 3/8 / 3 / 21 m / 5 m | 8/8 / 8 / 15 m / 4 m |
| stín 80 % | 4/8 / 4 / 18 m / 5 m | 8/8 / 8 / 15 m / 4 m |
| 5000 K | 3/8 / 3 / 19 m / 5 m | 8/8 / 8 / 17 m / 4 m |
| 8000 K | 5/8 / 5 / 16 m / 5 m | 8/8 / 8 / 15 m / 4 m |
| odlesk | 5/8 / 5 / 15 m / 4 m | 8/8 / 8 / 14 m / 4 m |
| rozmazání + JPEG 60 | 4/8 / 4 / 16 m / 5 m | 8/8 / 8 / 16 m / 4 m |
| stůl 10 % | 5/8 / 5 / 16 m / 5 m | 8/8 / 8 / 15 m / 4 m |
| stůl 20 % | 5/8 / 5 / 16 m / 5 m | 8/8 / 8 / 15 m / 4 m |
| stůl 30 % | 5/8 / 5 / 16 m / 5 m | 8/8 / 8 / 16 m / 4 m |
| ořez, chybí 1 kontrola | 5/8 / 5 / 14 m / 6 m | 8/8 / 8 / 14 m / 5 m |
| ořez, chybí 2 | 5/8 / 5 / 15 m / 5 m | 8/8 / 8 / 15 m / 5 m |
| 3 Mpx | 4/8 / 4 / 15 m / 5 m | 8/8 / 8 / 16 m / 4 m |
| kombinace1 | 1/8 / 0 / 278 m / 13 m | 8/8 / 8 / 16 m / 4 m |
| kombinace2 | 1/8 / 0 / 289 m / 17 m | 7/8 / 5 / 43 m / 7 m |
| kombinace3 | 5/8 / 0 / 151 m / 14 m | 8/8 / 7 / 18 m / 4 m |
| kombinace4 | 0/8 / 0 / – / – | 3/8 / 3 / 13 m / 4 m |
| kombinace5 | 4/8 / 0 / 229 m / 12 m | 7/8 / 0 / 140 m / 9 m |
| kombinace6 | 0/8 / 0 / – / – | 3/8 / 2 / 18 m / 5 m |
| **celkem** | 119/248 / 94 / 19 m / 6 m | 236/248 / 221 / 16 m / 5 m |

## Jak se to měří: `tools/fotka.py`

Umělé „fotky z mobilu“ z map s tratí, u kterých je pravda známá. Z obrázku KMZ (bez lišty Livelox) se udělá papír
a ten se přesným zobrazením (dopředu i zpátky, nic se neodhaduje) prohne, otočí, vyfotí nakloněným mobilem
(optická osa ve středu snímku, ohnisko jako u mobilu, zapsané v EXIF), položí na dřevěný stůl, nasvítí, zabarví,
rozmaže a uloží jako JPEG s EXIF orientací. Ví se tak, kam na fotce padl každý roh mapy a každá kontrola.

- Mapy: čtyři původní závody (`data/*/course.kmz`) a čtyři z `data-extra/` (dvě sprintové 1:4 000, jedna
  sprintová 1:5 000, Grand prix Silesia E3).
- Polohy kontrol „z GPS“: u Pohory a Petřvaldu skutečná stopa v oficiálních časech ORIS (jako v aplikaci), u
  ostatních map pravé polohy + šum 8 m (jiný běh k nim nemám).
- 31 fotek na mapu: základní (rovně, 15 % stolu, 12 Mpx), každé zkreslení zvlášť a šest kombinací. Celkem 248.

| Zkreslení | Úrovně |
|---|---|
| náklon mobilu | 10, 20, 30° |
| otočení | 37, 90, 180, 250° |
| EXIF orientace (uložená naležato) | 6, 3 |
| prohnutý papír | 1 a 2 % šířky |
| stín přes půl mapy | jas 40, 60, 80 % |
| barevný nádech | 5000 K a 8000 K (±1500 K) |
| odlesk přes jednu kontrolu | ano |
| rozmazání + šum + JPEG 60 | ano |
| stůl kolem | 10, 20, 30 % plochy |
| uříznutý okraj | chybí 1 a 2 kontroly |
| velikost | 12 Mpx (ostatní) a 3 Mpx |
| kombinace 1 až 6 | 20° + 37° + stín 60 % + 5000 K + stůl 20 %; 30° + prohnutí 2 % + rozmazání + stůl 25 %; 10° + 180° + EXIF 6 + odlesk + 8000 K; 20° + stín 40 % + rozmazání + 3 Mpx; 15° + prohnutí 1 % + ořez + stín 70 % + stůl 30 %; 25° + 250° + 5000 K + odlesk + rozmazání + 3 Mpx |

Pro každou fotku: usadila se?, kolik kontrol sedí, RMS, chyba ve čtyřech rozích mapy a na kontrolách, které jsou na
fotce vidět (metry proti pravdě). „Dobře“ v tabulkách = všechny čtyři rohy mapy do 50 m. Spuštění (samotné, asi
1,5 h): `kontrola/dc.sh sh /app/kontrola/foto/sada.sh kontrola/foto/konec.csv`; souhrn
`python tools/fotka.py --souhrn A.csv B.csv`. Rychlé testy mají tři malé fotky (`tests/test_foto.py`), webové
testy další (`tests/test_web_photo.py`).

Výchozí stav je změřený se stejným generátorem na kódu před touto větví (`998af6a`, git worktree a malá
kompatibilní vrstva v nástroji). První verze generátoru měla optickou osu mimo střed snímku; výsledky obou verzí na
starém kódu se liší jen u náklonu (`kontrola/foto/vychozi-gen1.csv`).

## Výchozí stav: co selhávalo

Na kódu před větví (`kontrola/foto/vychozi.csv`) se z 248 fotek usadilo 119 a dobře (všechny rohy do 50 m) 94.
Celá tabulka po případech je v souhrnu nahoře (sloupec „před“). Co selhávalo:

- **Náklon mobilu**: podobnost se zvlášť škálovanými osami šikmou fotku neudrží. 10° usazeno 5 z 8 map, ale rohy
  o 150 m vedle; 20° o 370 m; 30° se usadila jedna mapa.
- **Stín a barevný nádech**: přesná fialová Livelox našla kolečka jen ve světlé části, volnější fialová se nepouštěla
  (podmínka „málo fialových pixelů“). Stín 40 %: usazena 1 mapa z 8.
- **Sprintové mapy** (tři z osmi) se neusadily ani rovně: měřítko z velikosti kolečka počítalo s 75 m, sprint má
  24 m. To platí i pro obrázek z Livelox, nejen pro fotku.
- Kombinace: z 48 fotek 12 usazených, žádná dobře.
- Co fungovalo: otočení, EXIF (podobnost je vůči otočení lhostejná), stůl kolem, uříznutý okraj, 3 Mpx, jeden odlesk.

## Co se změnilo

Pořadí podle výchozího stavu: nejvíc selhával náklon (část 3) a světlo (část 2), pak sprintové mapy; vstup fotky
(část 1) byl rychlý a šel první.

**Kolo 1** (`5a30512` až `c1a45d1`):

- vstup: otočení podle EXIF, velký JPEG se dekóduje rovnou zmenšený, HEIC s větou, rada jak fotit;
- světlo: každý kanál se dělí barvou papíru v okolí (vyvážení bílé a stín jedním krokem), jen u fotky;
- perspektiva: okraj listu na stole → narovnání listu → kolečka se hledají na narovnaném listu → za listem jen
  dnešní plochý model; poměr stran listu z perspektivy s ohniskem z EXIF; homografie z kontrol jen když je
  o čtvrtinu lepší a kontroly ji drží (rohy se bez jedné kontroly nepohnou o víc než 50 m);
- sprint: kolečko 75, 50 a 30 m (`e686dcf`, týká se i obrázků z Livelox);
- prohnutí: kvadratický člen v jedné ose listu;
- fotka se ukládá narovnaná (severem nahoru, bez stolu) a trať se zapíše z usazení.

Výsledek: usazeno 230 z 248 (dřív 119), dobře 178 (94). Nová chyba: „prohnutí“ se našlo i na rovných fotkách map
s 12 až 14 kontrolami (učilo se šum GPS) a rohy těch map vyšly 60 až 90 m místo 15 m.

**Kolo 2** (`e6f2e52`): víc kandidátních poloměrů koleček (na rozmazané 3Mpx fotce mají smyčky číslic silnější
odezvu než tenké kroužky), bledší fialová na fotce, list na stole od 12 % fotky, prohnutí jen s aspoň 15 kontrolami
a o 15 % menší odchylkou, odhad chyby na okraji podle toho, jak se rohy hýbou bez jedné kontroly. Výsledek: 235
usazeno, 213 dobře. Nová chyba: bledší fialová schovala poloměr koleček na sprintu Zkouška sirén (náklon 20°
neusazen, v kole 1 ano).

**Kolo 3** (`32e3d1d`, `d43920c`, `f49e041`): okraj listu z konvexního obalu masky (barvy mapy u okraje listu podobné
stolu dělaly zářez, který táhl stranu o 50 až 150 px), fotka se čte nejdřív fialovou jako sken a bledší až potom,
a poměr stran listu se známým ohniskem i u přesného lichoběžníku (při předním náklonu bez otočení jsou dvě strany
listu rovnoběžné a výpočet vracel „nelze“; to se ukázalo až v prvním konečném měření, rohy Azymutu E5 a Grand prix
E3 při 20 a 30° vyšly 60 až 285 m). Konečné měření je po této opravě.

Po každém kole: pomalý `test_real_map_lands_where_its_kmz_says` se stejnými čísly, rychlé testy zelené.

## Analýza z fotky proti KMZ (část 5)

`python tools/fotka.py --analyza kontrola/foto/analyza`: `analyze.py` s KMZ z Livelox a s KMZ, které aplikace udělá
z umělé fotky téže mapy (náklon 15°, otočení 20°, stín 60 %, 5000 K, stůl 20 %), obojí s oficiálními časy ORIS.
Pohora a Petřvald, 37 úseků:

| Co | Rozdíl fotka proti KMZ |
|---|---|
| mezičasy | žádný (37 z 37 stejně) |
| uběhnutá vzdálenost úseku | žádná (37 z 37 stejně) |
| typ chyby u kontroly | žádný (37 z 37 stejně) |
| přímá délka úseku | medián 1 m, nejvíc 49 m (viz níže) |
| odhad ztráty | medián 0 s, nejvíc 5 s |
| poloha kontroly | medián 6 m, nejvíc 55 m (cíl Pohory) |

Jediný větší rozdíl je cíl Pohory: z KMZ ho `analyze.py` čte 92 m vzdušnou čarou od 16, z fotky 43 m. Běžec ale
z 16 do cíle uběhl 52 m, takže 92 m vzdušnou čarou být nemůže; podezřelé je spíš čtení cíle z KMZ (cíl z fotky je
místo, kde byl běžec v čase cíle). První verze měla na Petřvaldu start na kontrole 1 (záznam hodinek začíná až po
startu); opraveno (start u začátku záznamu, trojúhelník do 200 m od něj).

Trať z fotky nečte `analyze.py` z fialové (na fotce není přesná fialová Livelox), ale úloha ji zapíše z usazení
(`course.json` vedle KMZ, `analyze.py --course`); viz `docs/rozhodnuti.md`.

## Ruční usazení (část 4)

Stránka **Usadit fotku ručně** (`/races/N/fotka`): fotka v Leafletu (`L.CRS.Simple`), vedle seznam S, 1, 2, …, C;
vybereš kontrolu a klepneš na střed kolečka (body jde přetáhnout, × maže). Od 4. bodu server přepočítá usazení
(`georef.fit_points`, stejné jako u automatiky: s okrajem listu perspektiva z něj, jinak afinní zobrazení, od 6 bodů
homografie) a ukáže u každého bodu odchylku v metrech, varování a tvoji stopu přes fotku. Uložit pošle body úloze
`georef_map`, která fotku narovná a uloží jako mapu kategorie. Body si stránka pamatuje.

Kontroly v terénu bere aplikace ze stopy v časech ražení, žádná podkladová mapa není potřeba. Závod bez
oficiálních mezičasů ručně usadit nejde (zapsáno v `co-zbyva.md`).

Změřeno na celé sadě (`python tools/fotka.py --rucne kontrola/foto/rucne.csv`): pět kliků na kontroly
rozložené po trati (nejzápadnější, nejvýchodnější, nejjižnější, nejsevernější a nejdál od středu), každý klik o ±3 px
vedle středu kolečka, bez hledání koleček.

| | Výsledek |
|---|---|
| usazeno | 244 z 248 |
| dobře (rohy do 50 m) | 209 |
| s okrajem listu (168 fotek): rohy medián / 90 % do | 16 m / 36 m |
| bez okraje listu, afinní (76 fotek): rohy medián / 90 % do | 29 m / 230 m (šikmá fotka bez okraje listu) |
| kontroly medián / 90 % do | 6,3 m / 10,9 m |
| 12 fotek, které se automaticky neusadily | všech 12 usazeno, 9 dobře |
| neusazeno | 4 (Azymut E5: vybrané kontroly skoro v přímce, aplikace řekne „Body leží skoro v přímce…“) |

„Ručně se usadí vždy“ tedy platí, když jsou body rozumně rozložené; perspektivu ruční cesta bez okraje listu
nezachytí (afinní zobrazení), stejně jako automatika.

## Špatné vstupy (část 7)

Každý je vyrobený (`tools/fotka.py`, funkce `bad_photo`, nebo upravený soubor), zkoušený přes web v testu
(`tests/test_web_photo.py`) a ještě jednou přes `kontrola/foto/spatne.py`. „Před“ je kód na začátku větve; tehdy
každá chyba úlohy měla navíc pod „Podrobnosti“ výpis z Pythonu.

| Vstup | Před | Teď | Commit |
|---|---|---|---|
| úplně rozmazaná fotka | „v obrázku nejsou vidět fialová kolečka kontrol (je to mapa s tratí?)“ | „Fotka je rozmazaná a kolečka kontrol na ní nejdou najít. Vyfoť mapu znovu a ostře (podrž mobil v klidu a ťukni na mapu, ať zaostří).“ | `c48bfda` |
| tmavá fotka (10 % jasu) | totéž | „Fotka je moc tmavá a kolečka kontrol na ní nejdou najít. Vyfoť mapu znovu za světla, bez blesku.“ | `c48bfda` |
| fotka mapy bez tratě | totéž | „Na fotce nejsou vidět fialová kolečka kontrol. Je to mapa s tratí? Mapu bez tratě nahraj jako KMZ z Livelox.“ | `3a7a5aa` |
| mapa jiné kategorie (Azymut E5 k běhu na Pohoře) | „kolečka v obrázku neodpovídají tvé stopě (sedí jen 3 z 16 kontrol). Je to mapa téhle kategorie a běh z tohoto závodu?“ | „Kolečka na fotce neodpovídají tvé stopě: sedí jen 4 z 16 kontrol (na fotce je vidět 6 koleček). Buď je to mapa jiné kategorie nebo běh z jiného závodu, nebo kolečka zakrývá odlesk nebo prst, nebo je mapa uříznutá. Vyfoť celou mapu bez odlesku. Fotku můžeš také usadit ručně…“ | `c48bfda` |
| `.fit` z jiného závodu | „v obrázku je vidět 16 koleček kontrol a mezičas má 0 kontrol; to je málo.“ | „Tvoje stopa z hodinek v oficiálních časech ražení neběží (záznam nezačíná v čase tvého startu podle ORIS). Je to běh z tohoto závodu? Nahraj správný .fit, pak fotku znovu.“ | `43042d6` |
| půlka mapy, vidět jen 2 kontroly | „nejsou vidět fialová kolečka kontrol (je to mapa s tratí?)“ | „Na fotce jsou vidět 3 kolečka kontrol, tvoje trať jich má 16. Vyfoť celou mapu. Fotku můžeš také usadit ručně kliknutím na pár kontrol (odkaz Usadit fotku ručně).“ (třetí kolečko je cíl) | `c48bfda` |
| odlesk přes 5 kontrol | „neodpovídají tvé stopě (sedí jen 3 z 16)“ | usadí se ze zbylých (11 z 16, RMS 13 m) | `6ad78db` |
| odlesk přes 8 a víc kontrol | „neodpovídají tvé stopě“ | věta „neodpovídají tvé stopě … nebo kolečka zakrývá odlesk nebo prst … usadit ručně“; na stránce úloh tlačítko Usadit fotku ručně | `c48bfda`, `26bf78c` |
| dvě mapy na jedné fotce (mapa rozdělená na dva listy) | „neodpovídají tvé stopě (sedí jen 4 z 16)“ | „Na fotce jsou asi dvě mapy (přední a zadní strana nebo výměna mapy). Nahraj každou zvlášť; mapu na dvou listech zatím spojit neumíme.“ Odmítne se i taková, ze které se usadí méně než 90 % kontrol. | `c48bfda` |
| snímek obrazovky z Livelox v mobilu (1170 × 2532, lišta, tlačítka) | usadí se (16 z 16) | usadí se (16 z 16), beze změny | – |
| HEIC (`.heic`) | „Soubor není KMZ s mapou (export z Livelox: Share → Export → Google Earth KMZ).“ | „Fotka je ve formátu HEIC. Ulož ji jako JPEG (v iPhonu Nastavení → Fotoaparát → Formáty → Nejkompatibilnější), nebo ji nahraj přes prohlížeč, který ji převede.“ | `5a30512` |
| HEIC přejmenovaný na `.jpg` | „Soubor není obrázek (jpg nebo png).“ | věta o HEIC (pozná se podle obsahu) | `5a30512` |
| fotka 60 MB | projde (limit nahrávání 4096 MB, obrázek nejvýš 120 Mpx) | projde; JPEG nad 8000 px se dekóduje rovnou zmenšený | `5a30512` |
| soubor, který není obrázek | „Soubor není obrázek (jpg nebo png).“ | beze změny | – |
| ruční usazení: 3 body | (nebylo) | „Klikni aspoň na 4 kontroly, co nejdál od sebe (rohy tratě).“, Uložit nejde | `3a7a5aa` |
| ruční usazení: body v přímce | (nebylo) | „Body leží skoro v přímce, z nich se mapa usadit nedá. Přidej kontroly stranou od té přímky.“ | `3a7a5aa` |
| ruční usazení: stejná kontrola dvakrát | (nebylo) | „Stejnou kontrolu jsi označil dvakrát.“ | `3a7a5aa` |
| ruční usazení: jeden bod úplně vedle (5 bodů) | (nebylo) | „Kontrola N nesedí o X m. Klikl jsi na správné kolečko?“ (pozná, který bod to je); u 4 bodů „Body k sobě nesedí (až o N m)…“ | `3a7a5aa` |
| fotka nahraná dřív než `.fit` | „…chybí běh z hodinek nebo mezičasy z ORIS. Nahraj nejdřív .fit, nebo použij KMZ z Livelox.“ | „…Nahraj nejdřív běh z hodinek (.fit), nebo použij KMZ z Livelox.“ (fotka se nenahraje) | `3a7a5aa` |

Ve všech případech: úloha skončí jako „chyba“ s jednou větou (bez výpisu, `jobs.Refused`), žádná nezůstane
„běží“, fotka zůstane uložená a na stránce úloh i v Podkladech závodu je odkaz Usadit fotku ručně.

## Skutečná fotka (část 8)

Složka `data-extra/foto/` na začátku noci nebyla (ani na konci, viz níže), skutečnou fotku jsem tedy nezkoušel;
všechno výše je z umělých fotek. Jakmile tam bude fotka a `.fit`, stačí ji nahrát přes web (pole Mapa s tratí).

## Průchod webem

`tools/pruchod_foto.py` připraví samostatnou instanci (`/data/foto-mapy` ve svazku vývojového compose, port 8010;
uživatelská data ani kontejnery na 8000 nedotčené): demo závody, u Pohory smazaná mapa s tratí, dvě umělé fotky
(12 Mpx) a 18 kroků pro `tools/shot.mjs` (Chrome přes DevTools; nahrává soubory do formuláře, klepe myší a čeká na
pracovní proces). Všech 18 kroků prošlo bez chyb JavaScriptu; snímky jsem prohlédl. Všechny jsou v
`kontrola/foto/pruchod/`, důležité v `docs/reference/foto-mapy/`.

| Krok | Co se stalo | Snímek |
|---|---|---|
| nahrání fotky (náklon 15°, stín 60 %, 5000 K) | „Mapa usazena podle 16 z 16 kontrol, odchylka 13 m, na okraji mapy asi 33 m. Analýza je ve frontě.“ | `04-ulohy-usazeno-1440.jpg` |
| Podklady | „nahraná“, štítek „z fotky, přesnost asi ±33 m“, tlačítko Usadit fotku ručně, rada jak fotit | `05-podklady-z-fotky-1440.jpg` |
| analýza | doběhla celá i s nejlepšími postupy (mapa bez tratě je KMZ); nad mapou štítek „Mapa z fotky, přesnost asi ±33 m“ a věta o záchytných bodech | `06-zavod-analyza-z-fotky-1440.jpg` |
| fotka s odlesky přes 11 kontrol | úloha „chyba“ s větou bez výpisu a tlačítkem Usadit fotku ručně | `10-ulohy-neusazeno-1440.jpg` |
| ruční usazení, 1440 px | 4 body skriptem, pátý skutečným klepnutím myší; odchylky 8 až 21 m, stopa přes fotku sedí, Uložit povolené | `12-rucne-body-1440.jpg` |
| ruční usazení, 390 px | fotka přes šířku, kontroly jako tlačítka pod ní, body i stopa vidět | `13-rucne-body-390.jpg` |
| uložení | „Mapa usazena podle 5 bodů, které jsi označil, odchylka 10 m, na okraji mapy asi 23 m. Nahradila předchozí mapu z fotky.“ | `15-ulohy-rucne-1440.jpg` |
| KMZ místo fotky | „Mapa s tratí je uložená pro kategorii H16C. Nahradila mapu z fotky; analýza všech běžců kategorie se spustí znovu.“; štítek zmizel | `18-odeslano-kmz-1440.jpg` |

Co jsem neviděl: ruční usazení prstem na skutečném telefonu (jen Chrome v rozměru 390 px; přiblížení dvěma prsty
je Leaflet, nezkoušel jsem), a stránku v tmavém režimu.
