# Ztratil jsem se u kontroly (noc 24. → 25. 10. 2026, větev `ztraceny-u-kontroly`; od noci 25. 10. jen po závodě)

**Rozbor po závodě** pro chvíli „byl jsem u kontroly, neviděl jsem ji a nevěděl jsem přesně, kde jsem“. Na závodě se
mobil s polohou ani jiné pomůcky používat nesmějí (Tobias 25. 10., otázka 42), proto stránka nic za běhu nenabízí:
žádná poloha z telefonu, žádné „Teď v lese“, věty rady jsou v minulém čase („Měl jsi jít…“).

Dva režimy:

1. **Po závodě: kde jsem se ztratil** (hlavní, výchozí, když je analýza s .fit): místa do 100 m od kontroly, kde
   podle stopy zpomalil, kroužil nebo se otočil, a ke každému, co tam měl vidět a kudy se měl vrátit.
2. **Kde jsem asi byl** (pro závod bez .fit, nebo místo, které stopa nechytla): běžec vybere kontrolu, ťukne do mapy,
   kde asi byl, když se ztratil, a vybere, o kolik si není jistý (kruh 25, 50, 100 nebo 150 m; výchozí 50 m v lese,
   25 m na sprintu, otázka 40). Appka napíše jednu až tři věty, kam měl jít, a na mapě ukáže kruh, záchytné body a
   čáru cesty. „Jen kontrola a okolí“ dá totéž bez polohy.

Popis kontroly (osobní, otázka 41) a kruh nejistoty zůstávají. Na stránce závodu, který je dnes nebo v budoucnu a nemá
stopu, odkaz není; místo něj věta „Rozbor ‚Ztratil jsem se u kontroly‘ bude po závodě“ (`races.too_early`). Žádné
LLM ani placená služba: pravidla nad kresbou mapy (`oroute/lost.py`) a šablony vět (`webapp/texts.py`,
`lost_advice`, `lost_moment`).

Kde to je: tlačítko **Ztratil jsem se u kontroly** nahoře na stránce závodu a odkaz „Ztratil jsem se tady: co dělat“
u každého úseku (část Kdyby ses ztratil). Nápověda: `/ob/jak-na-to#ztraceny`. Rozhodnutí: `docs/rozhodnuti.md`.

> Věty v tabulkách níže jsou ze 24. 10. (přítomný čas, „Jdi na…“). Od 25. 10. zní stejně, jen v minulém čase
> („Měl jsi jít na…“, „Neměl jsi hádat směr ke kontrole…“). Nové rady z Bělé jsou v oddílu „Bělá“ na konci.

![Telefon: kontrola 3 nočního závodu, ťuknuto 110 px pod kontrolu](reference/ztraceny/ztraceny-mobil.jpg)

## Jak rada vzniká (stručně)

1. **Scéna** (jednou na závod, krátká úloha asi minutu): kolem každé kontroly do 320 m masky na buňkách asi 2 m,
   co se dá chytit (cesty, vodoteče, ploty, okraje zástavby, velkých otevřených ploch a vody, budovy, zdi sprintu) a
   co je neprůchodné (voda, OOB, budovy, oplocenky, zdi, zakázané čáry a plochy, ploty mapy), plus bodové záchytné
   body ze záchytných bodů (`relocate.candidates`). Petřvald 75 s, MSK sprint 2 min, noční závod 80 s; soubory
   0,1 až 0,5 MB na závod.
2. **Rada** (asi 40 ms na ťuknutí):
   - Z celého kruhu nejistoty vedou rovnoběžné paprsky po 10°. Linie, kterou za kruhem trefí aspoň 80 % paprsků
     dřív než něco neprůchodného, se **nedá minout**.
   - Dlouhá linie, která vede přímo kruhem, je také jistá: v lese ji na tu vzdálenost uvidíš.
   - Vybere se nejjistější věc, ne nejbližší. Pak se hledá, jak z ní ke kontrole: podél linie tam, kde je kontrola
     vedle ní, nebo ke křížení na ní, nebo azimut.
3. **Relokace:** když je nejbližší jistá věc dál než kruh, první věta zní „Neměl jsi hádat směr ke kontrole. Nejdřív
   jsi měl dojít (ses měl vrátit) …“.
4. **Bez okliky** (od 25. 10.): bod na linii (křížení) vyhraje, jen když z něj nevede delší azimut a celá cesta není
   o moc delší než podél linie k místu, kde je kontrole nejblíž, a azimut odtud (do 100 m). Kdo stojí přímo u linie,
   dostane azimut z místa, kde stojí, když je kratší. Azimuty jsou k severkám mapy (na pootočeném snímku se liší od
   horní hrany obrázku).

## Jak vznikly obrázky níže

- **Kde jsem asi byl** (dříve „Teď v lese“): umělá poloha běžce 70 m od kontroly směrem k minulé kontrole (jako by
  k ní dobíhal a nenašel ji), kruh 50 m. Oranžový kruh a tečka = běžec, fialový kruh = kontrola (37,5 m), modrá čára = rada, čísla = záchytné
  body (silně modrý = vybraný, šedý = není jistý).
- **Po závodě:** místo ze stopy .fit (kotva), kruh 30 m, červeně stopa úseku.
- Obrázky jsou z ladicího výstupu `python -m oroute.lost … --debug`. Věty v obrázku jsou bez háčků (v kontejneru
  není písmo s českými znaky); plné znění je pod obrázkem.
- Les a sprint mají analýzu z minulého kola (`kontrola/noc4/kolo-3`, kód stejný jako `main`). Noční závod nemá běh:
  kontroly jsou přečtené z KMZ s tratí (jako na tréninku bez .fit), zpětnou analýzu tam ukázat nejde.

## Les: Petřvald (MO dlouhá trať 2026, H18, mapa 0,59 m/px)

| Kontrola | Rada |
|---|---|
| 2 ![](reference/ztraceny/les-petrvald-2.jpg) | Do 50 m od tebe vede cesta (nejblíž na jihovýchod, asi 10 m): najdi ji. Pak podél ní na severozápad asi 110 m, kontrola je 10 m vpravo. |
| 4 ![](reference/ztraceny/les-petrvald-4.jpg) | Nehádej směr ke kontrole. Nejdřív dojdi na jih k cestě (asi 100 m, azimut 170°), ta se nedá minout. Pak podél ní na severovýchod asi 35 m, kontrola je 15 m vlevo. |
| 6 ![](reference/ztraceny/les-petrvald-6.jpg) | Do 50 m od tebe vede cesta (nejblíž na severozápad, asi 15 m): najdi ji. Pak podél ní na západ ke křížení cest (asi 65 m), odtud kontrola 75 m na azimut 35°. |
| 10 ![](reference/ztraceny/les-petrvald-10.jpg) | Nehádej směr ke kontrole. Nejdřív dojdi na západ k vodoteči (asi 160 m, azimut 250°, po 80 m mineš konec cesty, po 90 m přejdeš cestu), ta se nedá minout. Pak podél ní na jih k přechodu cesty přes vodoteč (asi 100 m), odtud kontrola 120 m na azimut 40°. |
| 13 ![](reference/ztraceny/les-petrvald-13.jpg) | Jdi na jih k cestě (asi 100 m, azimut 200°). Kontrola je od ní 30 m na azimut 15°. |
| 1 ![](reference/ztraceny/les-petrvald-1.jpg) | Do 50 m od tebe vede cesta (nejblíž na jihovýchod, asi 35 m): najdi ji. Odtud kontrola 100 m na azimut 270°. *(nedává smysl, viz níže)* |

Po závodě (tvoje stopa .fit):

| Místo | Co appka napíše |
|---|---|
| 10, zpomalení 75 m od kontroly ![](reference/ztraceny/les-petrvald-10_zpet_617.jpg) | 75 m od kontroly zpomalil jsi. Měl jsi vidět: kupka 10 m na jihozápad, prohlubeň 20 m na jih. Kudy zpět: Nehádej směr ke kontrole. Nejdřív dojdi na jihozápad k vodoteči (asi 150 m, azimut 240°, po 85 m mineš konec cesty, po 85 m přejdeš cestu), ta se nedá minout. Pak podél ní na jih k přechodu cesty přes vodoteč (asi 85 m), odtud kontrola 120 m na azimut 40°. |
| 14, nedoběhnutí 90 m od kontroly ![](reference/ztraceny/les-petrvald-14_zpet_1130.jpg) | 90 m od kontroly zastavil ses před kontrolou. Měl jsi vidět: kupka 15 m na východ, kupka 25 m na jih, kupka 25 m na severozápad, kupka 30 m na jihozápad. Kudy zpět: Nehádej směr ke kontrole. Nejdřív dojdi na severozápad k okraji zakázaného prostoru (asi 130 m, azimut 300°, po 120 m přejdeš cestu), ten se nedá minout. Odtud kontrola 85 m na azimut 75°. |
| 15, nedoběhnutí 60 m od kontroly ![](reference/ztraceny/les-petrvald-15_zpet_1485.jpg) | 60 m od kontroly zastavil ses před kontrolou. Do 30 m kolem nebylo nic jistého. Kudy zpět: Nehádej směr ke kontrole. Nejdřív dojdi na severovýchod k plotu (asi 85 m, azimut 40°), ten se nedá minout. Kontrola je od něj 25 m na azimut 240°. |
| 5, zpomalení 65 m od kontroly | 65 m od kontroly zpomalil jsi. Měl jsi vidět: cesta 5 m na západ, křížení cest 15 m na západ, vodoteč 30 m na jihozápad. Přešel jsi cestu 70 m předtím. Kudy zpět: Jsi u cesty, drž se jí. Pak podél ní na západ asi 65 m, kontrola je 10 m vpravo. |
| 17, zpomalení 20 m od kontroly | 20 m od kontroly zpomalil jsi. Měl jsi vidět: cesta 5 m na severozápad, vodní plocha 10 m na jihozápad, křížení cest 10 m na západ, kupka 15 m na severozápad. Přešel jsi cestu 30 m předtím. Kudy zpět: Jsi u cesty, drž se jí. Kontrola je od ní 25 m na azimut 110°. |

Na Petřvaldu našla stopa 5 míst u 19 kontrol. U úseků 14 a 15 je místo pojmenované druhem chyby z analýzy
(nedoběhnutí, `mistakes.classify`), ostatní jsou zpomalení, která appka našla sama. Chyby úseků 13 a 16 leží dál
než 100 m od kontroly, proto tu nejsou.

## Sprint: MSK sprint (Třinec 1:4 000, H16)

| Kontrola | Rada |
|---|---|
| 1 ![](reference/ztraceny/sprint-msk-1.jpg) | Jsi u cesty, drž se jí. Pak podél ní na východ asi 85 m, kontrola je přímo u ní. |
| 5 ![](reference/ztraceny/sprint-msk-5.jpg) | Do 50 m od tebe vede cesta (nejblíž na západ, asi 15 m): najdi ji. Pak podél ní na sever asi 120 m, kontrola je přímo u ní. |
| 10 ![](reference/ztraceny/sprint-msk-10.jpg) | Do 50 m od tebe vede cesta (nejblíž na severozápad, asi 10 m): najdi ji. Pak podél ní na sever asi 85 m, kontrola je 10 m vpravo. |
| 12 ![](reference/ztraceny/sprint-msk-12.jpg) | Jsi u cesty, drž se jí. Pak podél ní na sever ke konci cesty (asi 270 m), odtud kontrola 100 m na azimut 160°. *(nedává smysl, viz níže)* |
| 13 ![](reference/ztraceny/sprint-msk-13.jpg) | Kolem není nic, čeho by ses dal jistě chytit. *(nedává smysl, viz níže)* |

Po závodě:

| Místo | Co appka napíše |
|---|---|
| 12, otočka 35 m od kontroly ![](reference/ztraceny/sprint-msk-12_zpet_237.jpg) | 35 m od kontroly otočil ses. Měl jsi vidět: zeď 5 m na sever, plot 5 m na severovýchod, cesta 10 m na severovýchod, okraj otevřené plochy 10 m na západ. Přešel jsi zeď 5 m předtím, okraj otevřené plochy 25 m předtím. Kudy zpět: Jsi u plotu, drž se ho. Kontrola je od něj 40 m na azimut 225°. |
| 14, ztráta kontaktu 95 m od kontroly ![](reference/ztraceny/sprint-msk-14_zpet_250.jpg) | 95 m od kontroly tady jsi ztratil kontakt s mapou. Měl jsi vidět: okraj otevřené plochy 5 m na severovýchod, cesta 5 m na jihozápad, zeď 5 m na jihozápad, konec cesty 20 m na jih. Kudy zpět: Jsi u cesty, drž se jí. Pak podél ní na severozápad asi 150 m, kontrola je přímo u ní. |

## Noční: Mistrovství oblasti v nočním OB (Borovec 1:4 000, H14C, bez běhu)

| Kontrola | Rada |
|---|---|
| 1 ![](reference/ztraceny/nocni-borovec-1.jpg) | Jsi u vodoteče, drž se jí. Pak podél ní na severovýchod asi 75 m, kontrola je přímo u ní. |
| 3 ![](reference/ztraceny/nocni-borovec-3.jpg) | Jsi u cesty, drž se jí. Pak podél ní na jihozápad asi 75 m, kontrola je přímo u ní. |
| 5 ![](reference/ztraceny/nocni-borovec-5.jpg) | Nehádej směr ke kontrole. Nejdřív dojdi na jihovýchod k cestě (asi 130 m, azimut 150°), ta se nedá minout. Pak podél ní na sever asi 55 m, kontrola je 10 m vlevo. |
| 9 ![](reference/ztraceny/nocni-borovec-9.jpg) | Do 50 m od tebe vede cesta (nejblíž na jihovýchod, asi 15 m): najdi ji. Pak podél ní na jihozápad ke křížení cest (asi 50 m), odtud kontrola 110 m na azimut 20°. |
| 12 ![](reference/ztraceny/nocni-borovec-12.jpg) | Do 50 m od tebe vede cesta (nejblíž na jih, asi 20 m): najdi ji. Pak podél ní na jih asi 60 m, kontrola je přímo u ní. |
| 10 ![](reference/ztraceny/nocni-borovec-10.jpg) | Nehádej směr ke kontrole. Nejdřív dojdi na severozápad k cestě (asi 65 m, azimut 310°), ta se nedá minout. Kontrola je od ní 5 m na azimut 320°. *(nedává smysl, viz níže)* |

## Stránka

| Telefon, „Jen kontrola a okolí“ (kontrola 5) | Počítač |
|---|---|
| ![](reference/ztraceny/ztraceny-mobil-okoli.jpg) | ![](reference/ztraceny/ztraceny-desktop.jpg) |

Snímky jsou ze samostatné instance s nočním závodem bez běhu (`tools/pruchod_ztraceny.py`, `tools/shot.mjs`), v
bezhlavém Chromu bez chyb JavaScriptu. Popis kontroly 3 („rozcestí, západní cesta“) je zadaný ručně a ukáže se jako
poslední věta rady.

## Kde rada nedává smysl

- **Vede od kontroly pryč a zpátky.** Petřvald 1: běžec je 70 m od kontroly, rada ho pošle 35 m k cestě a odtud
  100 m azimutem zpět. Petřvald 10 po závodě: 150 m k vodoteči, 85 m podél ní a 120 m zpět ke kontrole, která byla
  75 m daleko. Pravidlo „nejdřív jistá věc“ tady vyhraje nad krátkou cestou, protože kolem kontroly není nic, co by
  se z kruhu 30 až 50 m nedalo minout (kupky, prohlubně). Skóre už takovou okliku penalizuje (od 1,5× přímé cesty),
  ale když nic lepšího není, zůstane. Pro zkušeného běžce je tu lepší rada „jdi azimutem a hledej kupku“; appka ji
  nedá, protože bodový objekt z kruhu 50 m netrefí jistě.
- **Běžec stojí na široké cestě.** Noční 10: kruh leží na silnici (hnědá plocha s černými okraji), která vede ke
  kontrole, ale rada pošle „k cestě 65 m na severozápad“. Silnice se v masce cest bere jen jako dva černé okraje;
  uprostřed silnice tedy běžec „u cesty“ není a okraje vedou souběžně se směrem, takže je paprsky netrefí.
- **Sprint a budovy.** Ve městě je cesta (ulice) do 50 m skoro vždycky, takže rada často zní „Jsi u cesty, drž se
  jí“ a nepozná, o kterou ulici jde. U MSK 10 (dřívější varianta bez pravidla o linii v kruhu) radila „jdi k budově“
  ve čtvrti, kde je budova každých 30 m. Na sprintu dává smysl kruh 25 m.
- **Dlouhé „podél ní“.** MSK 12: 270 m podél cesty ke konci cesty a 100 m zpět; noční 8: 260 m podél cesty.
  Povolené je až 300 m; je to správně, ale v terénu se to špatně počítá.
- **Nic jistého.** MSK 13: na sprintu, kde je kolem jen zástavba, zdi a dlažba, nevyšlo nic. Náběhový bod tu chybí
  také.
- **Noc.** Viditelnost bodového objektu je 8 m pro den i noc; v noci by měla být menší a okraje porostů a pasek by
  měly váhu nižší (za tmy se nepoznají). Noční závod s během, na kterém by šla zpětná analýza, nemáme (otázka 39).
- **Bez vrstevnic a skal.** Údolí, hřbety, srázy a skály appka z mapy nečte (`terrain.py`), takže rada „po hřbetu“
  nebo „pod skálou“ nikdy nepadne.
- **Plot, který nic neuzavírá, je cesta** (jako u záchytných bodů): „drž se cesty“ pak může být plot u pole.

## Bělá (Oblastní žebříček 18. 10. 2026, H18C, snímek z Livelox 0,97 m/px), noc 25. 10.

Obrázky před (kolo 6, kód ze 24. 10.) a po (nový kód): `docs/reference/oplocenky-vodotece/ztraceny-K-pred.png` a
`-po.png`. Podrobně v `docs/oplocenky-vodotece.md`.

| Kontrola | Dřív | Teď |
|---|---|---|
| 4 | Jdi na východ k vodoteči (70 m), pak podél ní na jih 85 m (ta „vodoteč“ byla severka) | Byl jsi u cesty, měl ses jí držet. Odtud kontrola 75 m na azimut 150°. |
| 11 | podél cesty na východ ke křížení 60 m, pak 95 m zpět | Byl jsi u cesty, měl ses jí držet. Odtud kontrola 70 m na azimut 0°. |
| 3 | k cestě, podél ní 140 m ke křížení, pak 100 m zpět | Do 50 m od tebe vedla cesta (asi 35 m): měl jsi ji najít. Odtud kontrola 95 m na azimut 75°. |
| 1, 6, 7 | viz obrázky | bez okliky; 6 zůstává „ke křížení 30 m, odtud 90 m“ (z křížení vede kratší azimut) |

Stránka na Bělé (samostatná instance, `tools/pruchod_ztraceny.py --bela`, `tools/shot.mjs`):

| Po závodě (počítač) | Kde jsem asi byl (telefon) | Závod zítra bez stopy |
|---|---|---|
| ![](reference/oplocenky-vodotece/stranka-bela-po-zavode-desktop.jpg) | ![](reference/oplocenky-vodotece/stranka-bela-kde-jsem-byl-mobil.jpg) | ![](reference/oplocenky-vodotece/stranka-bela-zitra-ztraceny.jpg) |

## Testy a ověření

- Rychlé testy: nové `tests/test_lost.py` (21, umělé rastry s ručně spočítanými vzdálenostmi a azimuty: výběr
  nejjistějšího místo nejbližšího, krátká cesta není jistá, nic v oplocence, obchůzka, co přejdeš cestou, podél linie
  vpravo, ke křížení a azimut 198°, relokace, linie v kruhu, kotvy po závodě, afinní převod na KMZ Pohory) a
  `tests/test_web_lost.py` (8: stránka připraví scénu jednou, rada, chybné požadavky a cizí závod, zastaralá scéna
  po posunu mapy, neúspěch se sám neopakuje, popis kontroly nic nepřepočítá, místa po závodě, migrace databáze).
- `relocate.json` je po úpravě `relocate.py` na Pohoře a MSK sprintu bajtově stejný jako na `main`.
