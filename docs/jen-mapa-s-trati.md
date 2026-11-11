# Rozbor jen z mapy s tratí

Z testu s tátou na Macu (7. 11. 2026): stačí snímek mapy s tratí, i když je na něm trať a červená čára postupu?
Dřív appka bez mapy bez tratě nepočítala nejlepší postupy vůbec.

## Předpoklady

- „Mapa s tratí“ je jeden snímek z Livelox (kolečka, spojnice, čísla), nebo KMZ s tratí bez KMZ bez tratě. Obojí se řeší stejně.
- „Červená trasa“ je čára postupu běžce z Livelox (přehrávání), která na snímku zůstala. Fialová trať (ISOM 7xx) je druhá věc,
  která zakrývá terén. Barvu čáry jsem změřil na snímku `snimek_trat.png` (Bělá 2026): asi (216, 26, 34).
- Nepřesnost, kterou bereme: zakrytý terén se doplní z okolí. Přes kolečko a spojnici (1 až 2 čáry šířky) je to v pořádku,
  přes celou cestu pod čárou ne.

## Jak se to dělá

`oroute/occlusion.py`: maska (fialová z `course.purple_mask` a `georef.loose_purple`, červená, obě rozšířené o 2 px, aby
pokryly vyhlazený okraj čáry) a doplnění. Varianty: `nearest` (nejbližší známý pixel), `median` (postupně od okraje mediánem
okolí), `bridge` (nejbližší a přes mezeru spojí černé čáry). Měření: `tools/jen_mapa_s_trati.py`. Z `course.kmz` se udělá mapa
„jen s tratí“ (uměle se do ní nakreslí červená stopa z `.fit`), doplní se, spočítají se nejlepší postupy a porovnají se
s postupy z `maponly.kmz`.

## Výsledky (4 závody, 71 úseků)

Práh jsem určil předem: aspoň 85 % úseků se stejným postupem (délka do 3 %) a medián rozdílu času nejlepšího postupu do 5 %.
Skryto je 1,5 až 3,3 % mapy bez červené čáry, 2,7 až 4,9 % s ní.

| Varianta | stejný postup | medián rozdílu času | práh |
|---|---|---|---|
| nearest | 85,9 % | 1,1 % | ano |
| median | 85,9 % | 1,1 % | ano |
| bridge | 87,3 % | 1,1 % | ano |
| nearest + červená čára | 85,9 % | 1,7 % | ano |
| median + červená čára | 80,3 % | 1,2 % | ne |
| bridge + červená čára | 84,5 % | 1,6 % | ne |

Po závodech (nearest, bez červené): Pohora 11/17, Petřvald 19/20, Azymut E4 20/21, Azymut E5 11/13. Pohora je pod prahem
sama o sobě (65 %, s červenou čárou 76 %), ostatní jsou nad ním. Rozdíl času postupu, který běžec skutečně běžel, podle modelu
je u mediánu do 5 % (Pohora s červenou čárou 4,8 %).

## Rozhodnutí

Zapnuto, s variantou `nearest` (nejjednodušší a jediná, která projde prahem i s červenou čárou). Postupy jsou odhad:

- Terén se čte z mapy s tratí s vyjmutou tratí a čárou (`runner.terrain_map`), jen u tratě z Livelox (KMZ nebo snímek), ne
  z fotky.
- Záchytné body (`relocate`) a „Ztratil jsem se“ se z odhadnuté mapy nepočítají: potřebují přesný terén kolem kontroly.
- Na stránce závodu je upozornění. Jakmile někdo nahraje opravdovou mapu bez tratě (KMZ nebo snímek), použije se ta a rozbor se
  přepočítá.
- Nápověda radí před snímkem v Livelox vypnout čáru postupu.

## Co zůstává

- Pohora (jemné úseky, hodně cest pod tratí) vychází pod prahem; u takových map odhad víc kolísá. Poznámka u jednotlivého úseku
  s velkým podílem zakryté trasy zatím není (`occlusion.hidden_along` je připravené, ale nezapojené).
- Měřilo se na uměle nakreslené červené čáře; skutečná čára z Livelox může být širší (otázka 55).
