# Vzhled klubového webu SKOB Frýdek-Místek (popis pro pozdější převzetí)

Stav k 6. 10. 2026, web https://skobfm.vzdyonline.cz/ ve verzi „2026.09.17 v84“. Popis vychází z jeho CSS (`/static/skob.css`, 116 kB, stejný obsah je vložený i přímo v `<style>` každé stránky) a ze screenshotů.

**Stav k 7. 10. 2026:** vzhled je v aplikaci převzatý. `webapp/static/skob.css` je nezměněná kopie, vlastní styly jsou v `webapp/static/ob.css`, screenshoty naší aplikace (světlý, tmavý, mobil, tablet) jsou v `docs/reference/nase-aplikace/`. Co se s body z konce tohoto dokumentu stalo, je v části „Co hlídat při převzetí“.

Podklady v `docs/reference/`:

| Soubor | Co to je |
|---|---|
| `skob-klubovy-web.css` | Stažená kopie `/static/skob.css`. Aplikace používá její bajtově stejnou kopii `webapp/static/skob.css` (hlídá test). |
| `skob-logo.svg` | Logo z adresy `/logo` (SVG, 269 × 233). |
| `skob-ikony-sprite.svg` | Sada 18 ikon (SVG `<symbol>`), kterou web vkládá na začátek každé stránky. |
| `01` až `08-*-desktop.png` | Úvod, budoucí závody, archiv, stránka závodu, vizitka člena, žebříčky, statistiky, náměty (1440 px). |
| `09`, `10-*-tmavy-desktop.png` | Úvod a stránka závodu v tmavém režimu. |
| `11` až `13-*-mobil.png` | Úvod, archiv a stránka závodu na mobilu (390 px, 2×). |
| `14-uvod-tablet.png` | Úvod na tabletu (820 px). |
| `nase-aplikace/01` až `16-*.png` | Naše aplikace: moje závody, stránka závodu (mapa, mezičasy, nastavení, podklady), model, nahrávání, přihlášení; světlý a tmavý režim, mobil, tablet. Pořizuje je `tools/shot.mjs` podle `tools/shots-*.json`. |

Screenshoty jsou pořízené bezhlavým Chromem přes DevTools protokol. Playwright v prostředí nainstalovaný není (`npx playwright` ani Python modul), takže jsem ho nepoužil.

## Nejdůležitější zjištění

- CSS je psané jako sdílené. Hlavička souboru říká, že je to „jediný zdroj pravdy o tom, jak vypadá web oddílu“, používají ho už dvě aplikace (`skob-results` a `oris2sidroid`) a kopie v další aplikaci se nemá upravovat ručně. Naše aplikace by měla být třetí odběratel: převzít soubor beze změny a vlastní styly (mapa, úseky) psát do samostatného souboru jen přes jeho proměnné.
- Barvy oddílu jsou v `:root` jako výchozí hodnoty `--c-*` a web je přepisuje druhým blokem `<style>` z databáze. Kdo převezme jen soubor, dostane stejné barvy, protože výchozí hodnoty jsou dnes shodné s těmi z databáze.
- Všechno je bez frameworku: žádný Bootstrap ani Tailwind, žádné externí fonty, žádný build. Skripty jsou krátké, vložené přímo ve stránce.

## Barvy

Barvy oddílu (stejné ve světlém i tmavém režimu):

| Proměnná | Hex | Použití |
|---|---|---|
| `--c-primary` / `--brand` | `#0E7A1C` | hlavička, levé menu, hlavní tlačítko, seřazený sloupec tabulky |
| `--c-secondary` / `--brand-2` | `#FBD08C` | odznaky (`.badge`), pruh aktivní položky v levém menu |
| `--c-accent` / `--accent` | `#CC1417` | varování, tlačítko výsledků, záporné skóre |
| `--c-support` / `--support` | `#1A1AC6` | doplňková modrá (grafy, měřítka pořadí) |
| `--c-on-brand` / `--on-brand` | `#FFFFFF` | text na zelené |
| `--c-flag-green` / `--flag-a` | `#6CBE45` | první třetina pruhu pod hlavičkou |
| `--c-flag-orange` / `--flag-b` | `#F59B32` | druhá třetina pruhu, okraj poznámek |
| `--c-flag-red` / `--flag-c` | `#D2232A` | třetí třetina pruhu, tečka „živě“ |

Logo používá `#FBD08C`, `#0E7A1C`, `#1A1AC6`, `#CC1417`, černou a bílou. Meta `theme-color` je `#0E7A1C`.

Neutrální a významové barvy:

| Proměnná | Světlý režim | Tmavý režim | Použití |
|---|---|---|---|
| `--ink` | `#14181a` | `#e7ecea` | hlavní text |
| `--ink-soft` | `#39423f` | `#c3ccc8` | vedlejší text, záhlaví tabulek |
| `--muted` | `#66706a` | `#96a09b` | popisky, metadata |
| `--line` | `#e3e8e4` | `#2a312e` | jemné linky, okraje karet |
| `--line-2` | `#ccd4ce` | `#3b4340` | okraje tlačítek a polí |
| `--bg` | `#ffffff` | `#171c1a` | pozadí polí a tlačítek |
| `--bg-page` | `#f4f7f5` | `#0e1211` | pozadí stránky |
| `--bg-elev` | `#ffffff` | `#181e1c` | karty, tabulky |
| `--bg-soft` | `#f1f5f2` | `#1f2523` | záhlaví tabulek, hover |
| `--zebra` | `#f6faf7` | `#1d2422` | sudé řádky tabulek |
| `--odkaz` | `#417229` | `#6CBE45` | odkazy, obrys fokusu |
| `--brand-svetla` | `#0E7A1C` | směs 55 % `--brand` s bílou | zelená, která musí být čitelná i na tmavém |
| `--vtisk` | `#7A2F86` | `#C3A1C9` | fialová „přetisku trati“ |
| `--zlato` / `--stribro` / `--bronz` | `#8f640e` / `#626c71` / `#94572a` | `#e0b64a` / `#b9c3c8` / `#cf8b52` | 1., 2., 3. místo |
| `--badge-ink` | `#241a06` | stejné | text na pískovém odznaku |

Stíny: `--stin1` = `0 1px 2px rgba(18,28,22,.05), 0 1px 3px rgba(18,28,22,.06)` (karty), `--stin2` = `0 .5rem 1.6rem rgba(18,28,22,.16)` (rozbalené menu). V tmavém režimu `0 1px 2px rgba(0,0,0,.45)` a `0 .5rem 1.6rem rgba(0,0,0,.55)`.

Tmavý režim se zapne buď nastavením zařízení (`prefers-color-scheme: dark`), nebo atributem `data-theme="tmavy"` na `<html>`; `data-theme="svetly"` světlý vynutí. Volbu ukládá přepínač v hlavičce do `localStorage` pod klíčem `skob-rezim` (`svetly` / `tmavy`, bez hodnoty = podle zařízení) a krátký skript v `<head>` ji nasadí ještě před styly. Rozbor postupů si od 19. 10. volbu ukládá pod vlastní klíč `ob-rezim`; dokud ho nemá, převezme hodnotu `skob-rezim` (tu nechá být, patří klubovému webu).

## Písmo a velikosti

- Základ: `font: 14px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Žádné webové fonty.
- Čísla v tabulkách a metadatech: `font-variant-numeric: tabular-nums`.
- `h1` (název v hlavičce): 1.1rem, váha 650; přípona „— závodní centrum“ váha 400, průhlednost .82.
- `h2`: 1.24rem, váha 640, `letter-spacing: -.01em`, řádkování 1.25, okraje `1.9rem 0 .75rem`. Před textem zelený svislý proužek .25rem × 1.05em se zaoblením, nebo místo něj ikona 1.15rem v barvě `--brand-svetla` (třída `s-ikonou`).
- `h3`: 1rem, váha 640.
- Drobný text: `.evdetail` .84em, `.evhead` (podtitul pod nadpisem) barva `--muted`, záhlaví tabulek .88em, odznaky .76em, patička .86em.
- Odkazy: barva `--odkaz`, podtržené (`text-decoration-thickness: 1px; text-underline-offset: .15em`), při najetí `--brand-svetla`.
- Fokus z klávesnice: `outline: 2px solid var(--odkaz); outline-offset: 2px`.

## Rozměry, zaoblení, mezery

- Mezery: `--s1` .25rem, `--s2` .5rem, `--s3` .75rem, `--s4` 1rem, `--s5` 1.35rem, `--s6` 1.9rem.
- Zaoblení: `--r1` .35rem (tlačítka, pole), `--r2` .55rem (tabulky, poznámky), `--r3` .85rem (karty, levé menu), `--r-pill` 999px (odznaky).
- Šířky: levé menu `--menu-sirka` 14.5rem, sloupec novinek `--novinky-sirka` 16rem, obsah nejvýš 100rem. Celý obal `.shell` má `max-width: calc(100rem + 14.5rem + 16rem)` a je vystředěný.

## Rozložení stránky

```
<div class="sitehead">            přišpendlená nahoře (position: sticky, z-index 30)
  <header class="site">           zelená hlavička
  <div class="flagstrip">         tříbarevný pruh, výška .3rem
<div class="shell">               flex
  <nav class="sidemenu">          levé menu, jen od 64rem
  <aside class="novinky">         sloupec novinek, jen na úvodní stránce
  <div class="obsah">
    <main>                        obsah
    <footer class="site">         patička
```

- Pozadí stránky: `--bg-page` a přes něj opakovaný SVG vzor 45rem × 45rem (vrstevnice, trojúhelník startu, kolečka kontrol, dvojité kolečko cíle, čárkované postupy) s průhledností kolem 0,09. Vzor je přímo v CSS jako `--mapa-pozadi`, ve dvou barvách pro světlý a tmavý režim.
- `main`: odsazení `1.35rem 1.25rem 4rem`, od 64rem `1.75rem 1.5rem 4rem`, do 40rem `1rem .75rem 3rem`.
- `html` má `overflow-y: scroll` (stránka neposkakuje při změně výšky) a `scroll-padding-top` podle skutečné výšky hlavičky, kterou skript ukládá do `--vyska-hlavicky`.

## Hlavička

- `header.site`: pozadí `--brand` s přechodem `linear-gradient(105deg, rgba(255,255,255,.08), rgba(0,0,0,.12))`, bílý text, odsazení `.85rem 1.25rem` (mobil `.7rem 1rem`).
- Vlevo odkaz na úvod (`a.brandlink`): logo výšky 2.5rem (mobil 2.1rem) na bílé dlaždici se zaoblením .55rem, vnitřním okrajem .18rem a stínem `0 1px 3px rgba(0,0,0,.25)`, vedle něj název „SKOB Frýdek-Místek — závodní centrum“.
- Vpravo (`.headmeta`): kulaté tlačítko režimu (1.7rem, okraj `rgba(255,255,255,.45)`, pozadí `rgba(255,255,255,.12)`, znaky ◐ ☀ ☾), aktuální datum a čas (.88rem, váha 600, tiká po vteřině) a pod ním verze (.78em, průhlednost .75).
- Pod hlavičkou `.flagstrip`: tři stejně široké pruhy `#6CBE45`, `#F59B32`, `#D2232A`.

## Menu

Položky a ikony: LIVE (`i-live`), oddělovač, Novinky (`i-vlajka`), Budoucí závody (`i-kalendar`), Minulé závody (`i-archiv`), Žebříčky (`i-zebricek`), Členové (`i-lide`), Statistiky (`i-graf`), Porovnání v letech (`i-vyvoj`), Chyby a náměty (`i-chyba`), Plán vývoje (`i-plan`), Stav (`i-stav`). Aktivní položka nese `aria-current="page"`.

- Od šířky 64rem: levý sloupec `.sidemenu` široký 14.5rem, přišpendlený pod hlavičkou. Zelený (`--brand` s přechodem `165deg`), zaoblení .85rem, nahoře malý tříbarevný proužek (.25rem). Odkazy bílé, odsazení `.5rem .7rem`, ikona 1.05rem s průhledností .8. Najetí: pozadí `rgba(255,255,255,.14)`. Aktivní: váha 650, pozadí `rgba(255,255,255,.18)`, levý okraj .18rem v barvě `#FBD08C`.
- Oddělovač mezi LIVE a zbytkem: dvě ikony kolečka kontroly spojené tenkou čarou, šířka 75 %, průhlednost .55.
- Pod 64rem: levé menu zmizí a v hlavičce vpravo je tlačítko se třemi čárkami (`<details class="menu">`). Rozbalí panel `min-width: 12rem` s bílým pozadím, okrajem, zaoblením .55rem a stínem `--stin2`; položky mají odsazení `.7rem .8rem`. Kliknutí mimo menu ho zavře (krátký skript).

## Karty a boxy

- `.karta`: pozadí `--bg-elev`, okraj `1px solid var(--line)`, zaoblení .85rem, odsazení `1rem 1.1rem`, stín `--stin1`.
- `.live` (hlavní box „DNES ZÁVODÍME“, „BUDOUCÍ“): jako karta, navíc horní okraj `.2rem solid var(--brand)`; nadpis uvnitř zelený, 1.12rem, `letter-spacing: .02em`.
- `.nota`: poznámka s levým okrajem `.25rem` v oranžové `--flag-b`, pozadí `--bg-soft`, .93em.
- `.stalewarn`: totéž s červeným levým okrajem a tučným textem.
- `.alfa`: upozornění „ve vývoji“, pozadí 12 % oranžové, levý okraj .35rem.
- `.empty` / `.prazdno`: šedý text prázdného stavu, vystředěný, nad ním velká ikona 3rem v barvě `--line-2`.
- `.detaily` a `.zaklad`: seznam „popisek: hodnota“ jako mřížka `max-content 1fr`, popisek v `--muted`. Na stránce závodu je v kartě `.zavodkarta` uvnitř `.detailmrizka` (od 64rem dva sloupce `minmax(22rem, 34rem) minmax(0, 1fr)`, jedna karta nejvýš 46rem).

## Tlačítka a přepínače

| Třída | Vzhled |
|---|---|
| `.btn` | výška aspoň 2.4rem (mobil 2.6rem), odsazení `.42rem .8rem`, okraj `1px solid var(--line-2)`, zaoblení .35rem, pozadí `--bg`, text `--ink`. Najetí: okraj `--brand`, pozadí `--bg-soft`. |
| `.btn-hlavni` | pozadí i okraj `--brand`, bílý text, váha 600; najetí průhlednost .9. |
| `.btn-maly` | odsazení `.25rem .55rem`, písmo .88em (např. „← zpět do archivu“). |
| `.btn-filtr` | čárkovaný okraj, pozadí `--bg-soft` (zrušitelný filtr). |
| `.btn-zdroj` + `.zdroj-start` / `.zdroj-prostor` / `.zdroj-cil` | odkazy na zdroj s ikonou z mapového klíče: zelený obrys (startovka, trojúhelník), oranžový (detaily závodu, plocha), červený (výsledky, dvojité kolečko). Najetí vyplní barvou. |
| `.genderfilter` | tři spojená tlačítka (Vše / Muži / Ženy); stisknuté (`aria-pressed="true"`) zelené s bílým textem. |
| `.oblast-pilulka` | zaškrtávací pilulka (výška 1.6rem, .8rem, váha 600); zaškrtnutá zelená. |
| `.taby` + `.tab` | záložky s podtržením: spodní linka `--line-2`, aktivní záložka má spodní okraj 3px `--brand-svetla`. |

## Tabulky

- Obal `.tablewrap`: `overflow-x: auto`, pozadí `--bg-elev`, okraj `--line`, zaoblení .55rem, stín `--stin1`.
- `table`: šířka 100 %, `border-collapse: collapse`, tabulkové číslice.
- Buňky: odsazení `.5rem .65rem` (první a poslední sloupec .9rem od kraje), `white-space: nowrap`, spodní linka `--line`. Mobil: `.42rem .4rem`, písmo .92em.
- Záhlaví: pozadí `--bg-soft`, text `--ink-soft`, váha 600, .88em. Řaditelný sloupec (`th[data-sort="text|number"]`) má za textem „⇅“; seřazený sloupec má zelené záhlaví s bílým textem a šipkou ↑ nebo ↓ a buňky sloupce dostanou `--bg-soft`.
- Sudé řádky `--zebra`, najetí `--bg-soft`. Čísla vpravo (`.num`). Hodnotu pro řazení nese `data-value`.
- Umístění: `.medal-1/2/3` tučně v barvě zlata, stříbra, bronzu s tečkou před číslem.
- Odznaky: `.badge` (pilulka, pískové pozadí `#FBD08C`, text `#241a06`), `.badge-tichy` (šedá s okrajem), `.stav` (pilulka stavu DNF, DISK apod.).
- Měřítko v buňce: `.mericka` (lišta 3rem × .4rem, výplň podle `--p`).

## Formuláře

- `.controls`: řádek ovládacích prvků, `display: flex; flex-wrap: wrap; gap: .5rem`. Pole a výběry: výška aspoň 2.4rem, odsazení `.42rem .6rem`, okraj `--line-2`, zaoblení .35rem, při fokusu okraj `--brand`.
- Hledání (`input[type=search]`): lupa vlevo jako obrázek na pozadí, `min-width: 15rem`, na mobilu přes celou šířku. Filtruje řádky tabulky v prohlížeči.
- Formulář námětu (`.napadform`, styl je jen na stránce `/napady`): karta do šířky 46rem, popisky nad poli (váha 600), pole přes celou šířku, nápověda `.hint` v `--muted` .86em, odeslání tlačítkem `.btn-hlavni`.

## Patička

`footer.site`: horní linka `--line`, text `--muted` .86em, odsazení `1rem 1.25rem 3rem`. Obsah: věta o původu výsledků, odkaz na RSS a řádek s verzí (`.patverze`).

## Ikony

Čárové SVG ikony (`fill: none`, obrys v barvě textu), vložené jednou na začátku stránky jako skrytý sprite (`<svg class="sprite">` se `<symbol id="i-…">`) a používané přes `<svg class="ikona"><use href="#i-live"></use></svg>`. Velikost `.ikona` 1.05rem, `.ikona-nadpis` 1.15rem, `.ikona-velka` 3rem. Motivy berou z mapového klíče OB: start je trojúhelník, cíl dvě kružnice, kontrola kroužek.

## Chování podle šířky

| Šířka | Co se změní |
|---|---|
| od 64rem (1024 px) | levé menu místo tlačítka se třemi čárkami; širší odsazení obsahu; kalendář a stránka závodu ve dvou sloupcích |
| od 48rem (768 px) | sloupec novinek vpravo, přišpendlený; pod 48rem padá pod obsah přes celou šířku |
| do 63.99rem | v hlavičce zmizí čas a verze, tlačítko režimu se zvětší na 2.4rem |
| do 40rem (640 px) | menší odsazení (hlavička, `main`, buňky tabulek), vyšší tlačítka a pole (2.6rem), hledání přes celou šířku, schovají se lišty měřítek |
| do 29rem (464 px) | z názvu v hlavičce zmizí „— závodní centrum“ |

Pozor na jednotky: 14px je nastaveno na `body`, ne na `html`, takže `1rem` zůstává 16 px (levé menu 14.5rem = 232 px, obsah nejvýš 1600 px), kdežto hodnoty v `em` se počítají ze 14 px.

Široké tabulky se na mobilu neskládají, posouvají se vodorovně uvnitř `.tablewrap`.

## Tisk a pohyb

- `@media print`: černobílé proměnné, bez pozadí, menu, filtrů, novinek a záložek; všechny panely záložek se vytisknou pod sebou.
- Animace (pulzující tečka `.zivo`, otáčení šipky rozbalení) respektují `prefers-reduced-motion`.

## Co hlídat při převzetí do naší aplikace

Stav k 7. 10. 2026: CSP posíláme stejnou (navíc `img-src blob:`), Leaflet i obrázky map jdou ze stejného původu a žádná cizí dlaždicová mapa se nenačítá. Stránka závodu s mapou je přes celou šířku, levé menu je na ní pod třemi čárkami. Barvy tratě, nejlepšího postupu a chyby jdou z `--vtisk`, `--support` a `--accent`; jediná barva natvrdo je světlá hodnota `--vtisk` pro trať kreslenou na mapě (obrázek mapy je světlý i v tmavém režimu). CSS se nepřebírá po kouscích. Otevřené zůstává, jak se kopie udržuje při změně klubového webu (otázka na tátu v `co-zbyva.md`).

Původní body:

- Hlavička CSP webu je `default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; form-action 'self'`. Pokud by naše stránky běžely pod stejnou doménou a stejnými hlavičkami, musí být Leaflet, obrázky map i data ze stejného původu (to dnes splňujeme, Leaflet je v repozitáři) a nepůjde vložit žádná cizí dlaždicová mapa. Vložení přes `<iframe>` web zakazuje (`frame-ancestors 'none'`, `X-Frame-Options: DENY`).
- Stránka s mapou potřebuje větší šířku než 100rem obsahu jen výjimečně; levé menu 14.5rem je na ní spíš na obtíž. Rozhodnout, zda mapu ukazovat přes celou šířku pod hlavičkou.
- Barvy úseků a tras na mapě by měly vycházet z palety (`--vtisk` pro trať, `--support` modrá pro nejlepší postup, `--accent` pro chybu), aby seděly i v tmavém režimu.
- Nepřebírat ručně kusy CSS. Domluvit s tátou, jak se kopie souboru udržuje (hlavička CSS říká, že zdrojem je repozitář `skob-results`).
