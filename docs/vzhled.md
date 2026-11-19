# Vzhled aplikace „Kudy jsem měl běžet“

Aplikace používá jediný vzhled: **Kartografie** (od 11/2026, předtím Lesní klid). Kartografie a sportovní analytika:
mapový papír, lesní zelená, tlumená oranžová, patkové písmo pro nadpisy a velká čísla, čáry místo karet.

## Jak je vzhled poskládaný

- `webapp/static/base.css`: obecné rozložení stránky, tabulky, navigace a základní komponenty aplikace.
- `webapp/static/ob.css`: specifické prvky rozboru (mapy, úseky, formuláře a grafy); barvy bere z proměnných.
- `webapp/static/les.css`: jediná barevná a typografická vrstva (načítá se poslední): tokeny, světlý a tmavý režim,
  postranní panel, horní lišta a společné komponenty stránek.
- `webapp/static/app-icons.svg`: jedna sada liniových SVG ikon pro navigaci, akce a stavy (`ikona('jmeno')`).
- `webapp/static/ob-logo.svg`: logo aplikace.

Světlý „mapový papír“ je výchozí; tmavá „noční mapa“ platí, když ji chce zařízení, nebo když si ji běžec zvolí
(tlačítko ◐ v horní liště nebo Profil → Vzhled a jazyk). Tmavé hodnoty tokenů jsou v `les.css` dvakrát (podle
zařízení a ručně zvolené) a musí být stejné.

## Tokeny

| Token | Světlý | Použití |
|---|---|---|
| `--forest` | `#172B25` | postranní panel, hlavní tlačítko, nadpisy |
| `--paper`, `--paper-2`, `--paper-3` | `#F1EEE5`, `#E7E2D4`, `#EBE7DC` | plocha stránky, bloky, panely |
| `--orange` / `--orange-ink` | `#C46C3B` / `#98501F` | akcent (čáry, výběr) / oranžový text (kontrast 4,9:1) |
| `--green` / `--green-ink` | `#55765D` / `#3B5A43` | stav hotovo / zelený text |
| `--red` / `--red-ink` | `#B65343` / `#973627` | chyba, nebezpečná akce |
| `--rule`, `--rule-2` | `#D2CBBB`, `#BDB5A4` | linky tabulek a bloků |
| `--muted` | `#5A6157` | vedlejší text (5,4:1 na papíru) |

Plné akcentní barvy jsou pro čáry, pruhy a okraje; drobný text má vlastní tmavší odstín (`*-ink`).

## Společné komponenty

- Záhlaví stránky `.pagehead` (`.eyebrow`, `h1`, `.sub`, `.page-actions`), drobečková navigace v horní liště
  (`{% block crumbs %}`), řádek čísel `.statrow` / `.stat`.
- Stavové štítky `.stav` s tečkou a textem (`ob-ok`, `ob-warn`, `ob-bad`, `ob-run`, `ob-wait`, `ob-off`): stav
  nikdy nenese jen barva.
- Tlačítka `.btn`, `.btn-hlavni`, `.btn-maly`, `.btn-tichy`, `.btn-nebezpeci`; potvrzení rizikové akce
  atributem `data-potvrdit="…"` na formuláři nebo tlačítku (`ob.js`).
- Filtry a řazení tabulek: `data-filter`, `data-filter-attr`, `data-filter-empty`, `data-filter-count`,
  `data-filter-reset`, `select[data-razeni]` (`ob.js`). Hledání nerozlišuje velikost písmen ani diakritiku.
- Volba ve tvaru karet `.volby` / `.volba[aria-pressed]` s částmi `[data-volba-panel]` (výběr podoby mapy
  v Podkladech).
- Výběr souboru ukáže jméno, velikost a náhled obrázku (`input[type=file][data-vyber]` nebo pole ve
  `form[data-nahravani]`).
- Osobní a společné nastavení: `.rozsah` a `.rozsah.spolecne`.

## Rozvržení

- od 1100 px: plný postranní panel 232 px,
- 760–1099 px: úzký pruh s ikonami (popisky zůstávají pro čtečky a v `title`),
- pod 760 px: horní lišta s nabídkou a spodní lišta.

Mapa závodu a panel úseku stojí vedle sebe od 900 px, pod tím pod sebou.
