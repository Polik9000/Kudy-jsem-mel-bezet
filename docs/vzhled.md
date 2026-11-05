# Vzhled aplikace „Kudy jsem měl běžet“

Aplikace používá jediný vzhled: **Lesní klid**. Starší alternativní vzhled Buzola a původní klubové vzhledové soubory byly odstraněny.

## Jak je vzhled poskládaný

- `webapp/static/base.css`: obecné rozložení stránky, tabulky, navigace a základní komponenty aplikace.
- `webapp/static/ob.css`: specifické prvky rozboru (mapy, úseky, formuláře a grafy); barvy bere z proměnných.
- `webapp/static/les.css`: jediná barevná a typografická vrstva – vzhled Lesní klid, tmavý a světlý režim, postranní panel a mobilní navigace.
- `webapp/static/app-icons.svg`: SVG symboly používané v navigaci a rozhraní.
- `webapp/static/ob-logo.svg`: logo aplikace.

Tmavý režim je výchozí. Tlačítko ◐ v hlavičce přepíná tmavý, světlý a režim podle zařízení.
