# Proč je to nejlepší právě pro tebe (noc 19. → 20. 10. 2026, větev `pro-tebe-a-sprint`)

Původní myšlenka appky: „jsem silný do kopce, takže pro mě je lepší kopec přeběhnout než ho obíhat“. Appka teď na
každém úseku najde vedle tvého nejlepšího postupu i nejlepší postup **průměrného běžce**. Kde se liší, ukáže ho na
mapě a řekne proč.

## Jak to funguje

- **Průměrný běžec** je učebnicový model `SpeedModel()`: terény podle ISOM (`PRIOR_FACTORS`), sklon podle
  učebnicového pravidla (up_k 9, zhruba Naismith) a **tvoje rychlost po rovné cestě**. Porovnává se tvar modelu, ne
  kondice. Kdo nemá vlastní export z Garminu, má sklon výchozí (Tobiasův), a tak se u něj porovnávají jen terény.
  Proč ne `slope_prior.json`, je v `docs/rozhodnuti.md`.
- `bestroute.py --generic` po všech tvých postupech přestaví mřížku s modelem průměrného běžce a na každém úseku
  hledá jednou (bez alternativ). Petřvald: 151 s → 189 s, paměť stejná (2,97 GB).
- Postupy se **liší**, když kterýkoli z nich vede dál než 30 m od druhého na víc než 20 % své délky.
- **Čas** postupu průměrného běžce je **tvým** modelem („tobě by ten postup trval 5:14“). Vedle něj stojí tvůj nejlepší
  (stejné číslo jako jinde na stránce). Když je rozdíl do 3 s, věta řekne „skoro stejně“.
- **Důvod** je ta část modelu (stoupání, klesání nebo jeden terén), která po výměně z průměrného za tvůj (a naopak)
  nejvíc posune rozdíl časů obou postupů k tvému. Procento je poměr tvého a průměrného činitele (u kopce poměr násobků
  sklonu při typickém sklonu úseku).
- **Web:** tečkovaná šedá čára (zaškrtávátko „průměrný běžec“ pod mapou), věta pod vysvětlením úseku, řádek
  „průměrný běžec“ v tabulce postupů. Na stránce modelu je souhrn: na kolika úsecích, nejčastější důvody a tři úseky
  s největším rozdílem.

## Kolik úseků se liší

Konečný kód (po opravě sprintů a stopy vedle cesty), model `oroute/personal_model.json` z 19. 10. (Tobias), kolo 3
(`kontrola/noc3/kolo-3`). Devět z deseti spárovaných závodů: Žebříček B se nedopočítal (kolo zastavil systém kvůli
nedostatku paměti).

| Závod | Úseků | Liší se a pro tebe rychlejší | Liší se, ale skoro stejně | Důvod |
|---|---|---|---|---|
| Azymut Cup 2026 E4 | 21 | 0 | 1 | |
| Azymut Cup 2026 E5 | 13 | 1 | 0 | stoupání |
| Grand prix Silesia E2 (sprint v paletě ISOM) | 26 | 0 | 0 | |
| Grand prix Silesia E3 | 15 | 2 | 0 | klesání, světle zelená |
| Grand prix Silesia E4 | 18 | 1 | 1 | klesání |
| MSK sprint | 20 | 1 | 0 | louka |
| Petřvald | 20 | 0 | 0 | |
| Pohora | 17 | 1 | 1 | podrost |
| Slezská zimní liga (sprint) | 27 | 0 | 1 | |
| **celkem** | **177** | **6 (3,4 %)** | **4** | klesání 2×, stoupání, světle zelená, podrost, louka |

Pro srovnání kolo 1 (před opravou sprintů a stopy, starý model, deset závodů): 7 ze 194 a 3 „skoro stejně“.
Mezi koly vypadla Slezská zimní liga 6–7 (tvůj postup tam vedl domem) a Pohora 11–12 (v zelené, teď „skoro stejně“);
přibyl sprint MSK 9–10; Azymut E5 8–9 má teď za důvod stoupání místo zelené.

**Stoupání je důvodem jen jednou.** Tvůj sklon (up_k 3,4) je proti učebnicovému (9) mnohem mírnější: při 10 % do
kopce běžíš podle modelu o 42 % rychleji než učebnicový běžec. Postupy přes kopec a kolem kopce ale na těchto mapách
skoro všude vycházejí pro oba stejně. Neověřené vysvětlení: kopce na úsecích jsou malé nebo se obejít nedají (obejít
stojí víc, než ušetří), a u Azymutu a Grand prix Silesia je výška jen z dlaždic AWS po 30 m. Rozdíly dělají hlavně
terény, kde se tvůj model nejvíc liší od normy (světle zelená +20 %, podrost +11 %, louka +13 %), a klesání: z mírného
kopce jsi podle modelu pomalejší, než učebnice čeká (tvůj down_gain je 0, učebnicový 2,5).

## Pět nejzajímavějších úseků

Na obrázcích je modře tvůj nejlepší postup, šedě tečkovaně postup průměrného běžce, červeně tvoje stopa a fialově
kontroly. Obrázky jsou v `docs/reference/pro-tebe/`.

1. **Grand prix Silesia E3, 6–7** (`1_gps-e3_6-7.jpg`): „Běžec s průměrným modelem by běžel víc po cestách; tobě by
   ten postup trval 5:14. Pro tebe je rychlejší mimo cesty (4:02), protože ve světle zelené běžíš o 20 % rychleji než
   průměr.“ Dává smysl. Je to největší rozdíl (72 s). Zajímavé je, že jsi běžel skoro přesně postup průměrného běžce
   (po cestách na jih).
2. **Pohora, 5–6** (`2_pohora_5-6.jpg`): „… by podrost obíhal vpravo; tobě by ten postup trval 4:46. Pro tebe je
   rychlejší přes podrost (4:20), protože v podrostu běžíš o 11 % rychleji než průměr.“ Dává smysl: průměrný běžec
   jde po cestě kolem pruhů zelené (podrostu), tvůj postup jde přímo. Ty jsi běžel jako průměrný.
3. **Grand prix Silesia E4, 6–7** (`3_gps-e4_6-7.jpg`): „… by běžel jinudy vlevo; tobě by ten postup trval 3:21. Pro
   tebe je rychlejší tvůj nejlepší postup (3:05), protože z kopce jsi o 21 % pomalejší než průměr.“ **Dává smysl jen
   napůl.** Postup průměrného běžce seběhne údolím po cestách, tvůj jde přímo po vrstevnici. „Z kopce jsi pomalejší“ je
   pravda modelu (down_gain 0), ale věta nepojmenuje, co se na mapě liší: oba postupy nastoupají stejně a liší se jen
   strmostí klesání.
4. **Sprint MSK, 9–10** (`4_msk-sprint_9-10.jpg`): „… by louku obíhal vlevo; tobě by ten postup trval 0:52. Pro tebe
   je rychlejší přes louku (0:45), protože na louce běžíš o 13 % rychleji než průměr.“ Dává smysl: průměrný běžec jde
   po dlažbě kolem domů (ulicí na západ), tvůj postup jde rovně přes otevřené plochy mezi domy, jako jsi běžel.
   Na sprintu je „louka“ otevřená plocha (ISSprOM 401), slovo je trochu lesní.
5. **Azymut Cup E5, 8–9** (`5_azymut-e5_8-9.jpg`): „… by běžel víc po cestách; tobě by ten postup trval 5:56. Pro
   tebe je rychlejší mimo cesty (5:50), protože do kopce běžíš o 35 % rychleji než průměr.“ Dává smysl: postup
   průměrného běžce obíhá po cestě, tvůj jde rovnou do svahu. Rozdíl je jen 6 s a jen na začátku úseku.

## Věty: dávají smysl?

- Ve čtyřech z pěti případů ano: tvar „by obíhal / šel přes X“ a „protože v X běžíš o N % rychleji“ odpovídá obrázku.
  „Vlevo“ a „vpravo“ sedí (ověřeno na MSK 9–10 podle směru úseku).
- Slabé místo jsou úseky, kde se postupy liší jen strmostí (klesání), ne délkou v terénu ani stoupáním. Věta pak řekne
  „by běžel jinudy“ a důvod, ale ne kudy. Lepší by bylo „průměrný běžec by seběhl údolím po cestě“ (podle toho, kde je
  na jeho postupu nejvíc klesání). Zatím nedělané.
- Na sprintu by se místo „louka“ hodilo „otevřená plocha“.
- Procenta v zelené jsou po opravě stopy menší: kolo 1 mělo zelenou o 70 % rychlejší než průměr, nový model o 50 %
  (činitel 0,51 → 0,45: kroky GPS pár metrů vedle cesty se už neučí jako zelená).

## Noc 20. → 21. 10.: věty znovu (větev `zdi-sbehy-provoz`)

Kolo 2 (`kontrola/noc4/kolo-2`, konečný kód, každý závod ve vlastním kontejneru) má i **Žebříček B**, který minulou
noc nedoběhl: 17 úseků, jeden se liší a je pro tebe rychlejší (12–13, otevřená plocha +13 %; mapa sídliště, čte se
jako sprint). Celkem 194 úseků deseti závodů: **7 se liší a jsou pro tebe rychlejší** (3,6 %), 4 „skoro stejně“.
Zdi na sprintech nezměnily, které úseky se liší.

Co se změnilo ve větách:

- **Liší se jen strmostí:** věta najde úsek postupu průměrného běžce s největším klesáním (stoupáním), řekne, po čem
  vede a jestli je v údolí, na hřbetu nebo na svahu, a podle sklonu „seběhl“ nebo „klesal pozvolna“. U tvého postupu
  „kratší“ / „delší“, jinak „s mírnějším“ / „s prudším klesáním“.
- **Skoro stejně:** místo „by běžel jinudy“ stejný popis jako u ostatních (víc po cestách, obíhal zelenou…);
  „jinudy“ zůstává, jen když se postupy neliší ani terénem, ani délkou o 5 %.
- **Sprint:** „otevřená plocha“ místo louky, „zpevněné plochy“ místo cest (i ve výčtu důvodů na stránce modelu).

Všech deset úseků z tabulek výše (6 + 4 „skoro stejně“), obrázky v `docs/reference/pro-tebe/noc4/` (modře tvůj
nejlepší postup, šedě tečkovaně průměrný běžec, červeně stopa):

| # | Úsek | Nová věta | Sedí s obrázkem? |
|---|---|---|---|
| 1 | Grand prix Silesia E3, 6–7 | Běžec s průměrným modelem by běžel víc po cestách; tobě by ten postup trval 5:14. Pro tebe je rychlejší mimo cesty (4:02), protože ve světle zelené běžíš o 20 % rychleji než průměr. | ano (beze změny) |
| 2 | Pohora, 5–6 | … by podrost obíhal vpravo; tobě by ten postup trval 4:46. Pro tebe je rychlejší přes podrost (4:20), protože v podrostu běžíš o 11 % rychleji než průměr. | ano (beze změny) |
| 3 | Grand prix Silesia E4, 6–7 | … by **klesal pozvolna po svahu vlevo**; tobě by ten postup trval 3:21. Pro tebe je rychlejší **tvůj kratší nejlepší postup** (3:05), protože z kopce jsi o 21 % pomalejší než průměr. | ano. Minulá noc čekala „seběhl by údolím po cestách“; profil výšek říká opak: průměrný běžec klesá 8,9 m na 60 m (15 %), tvůj nejlepší 13,6 m (23 %) a je o 42 m kratší. Učebnicový běžec je z mírného kopce o čtvrtinu rychlejší, tak si klesání rozloží; tobě klesání nic nepřidá, proto kratší. Údolí na 25 m po stranách výškopis AWS (30 m) nenašel, je to svah. |
| 4 | Sprint MSK, 9–10 | … by **otevřenou plochu** obíhal vlevo; tobě by ten postup trval 0:52. Pro tebe je rychlejší přes otevřenou plochu (0:45), protože na otevřené ploše běžíš o 13 % rychleji než průměr. | ano |
| 5 | Azymut Cup E5, 8–9 | … by běžel víc po cestách; tobě by ten postup trval 5:56. Pro tebe je rychlejší mimo cesty (5:50), protože do kopce běžíš o 35 % rychleji než průměr. | ano (beze změny) |
| 6 | Grand prix Silesia E3, 4–5 | … by běžel víc po cestách vlevo; tobě by ten postup trval 1:17. Pro tebe je rychlejší mimo cesty (1:13), protože z kopce běžíš o 8 % rychleji než průměr. | ano (beze změny) |
| 7 | Grand prix Silesia E4, 13–14 | … by **běžel víc po cestách vlevo**; tobě by ten postup trval skoro stejně (1:02 proti 1:00). | ano: průměrný jde po cestě podél olivové plochy |
| 8 | Slezská zimní liga, 5–6 | … by běžel jinudy vlevo; tobě by ten postup trval skoro stejně (0:58 proti 0:57). | ano, ale nic neříká: průměrný obíhá dům ze severu; postupy jsou stejně dlouhé a liší se o pár metrů otevřené plochy |
| 9 | Pohora, 11–12 | … by **zelenou obíhal vpravo**; tobě by ten postup trval skoro stejně (3:17 proti 3:16). | ano: průměrný jde po cestách severně od zelené |
| 10 | Azymut Cup E4, 8–9 | … by běžel jinudy vpravo; tobě by ten postup trval skoro stejně (3:35 proti 3:34). | ano, nic víc říct nejde: oba vedou lesem, stejně dlouhé |

Žebříček B 12–13: „… by otevřenou plochu obíhal vlevo; tobě by ten postup trval 2:41. Pro tebe je rychlejší přes
otevřenou plochu (2:36), protože na otevřené ploše běžíš o 13 % rychleji než průměr.“
