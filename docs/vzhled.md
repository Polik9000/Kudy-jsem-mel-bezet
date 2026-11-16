# Vzhled aplikace „Kudy jsem měl běžet“

Aplikace používá jediný vzhled: **Lesní klid**. Starší alternativní vzhled Buzola a původní klubové vzhledové soubory byly odstraněny.

## Jak je vzhled poskládaný

- `webapp/static/base.css`: obecné rozložení stránky, tabulky, navigace a základní komponenty aplikace.
- `webapp/static/ob.css`: specifické prvky rozboru (mapy, úseky, formuláře a grafy); barvy bere z proměnných.
- `webapp/static/les.css`: jediná barevná a typografická vrstva – vzhled Lesní klid, tmavý a světlý režim, postranní panel a mobilní navigace.
- `webapp/static/app-icons.svg`: SVG symboly používané v navigaci a rozhraní.
- `webapp/static/ob-logo.svg`: logo aplikace.

Tmavý režim je výchozí. Přepínač režimu (dole v levém panelu, na úzkém okně v hlavičce) přepíná světlý, tmavý a režim podle zařízení.

## Nový vzhled podle návrhu (prompty 9 až 12, listopad 2026)

Oproti prvnímu „Lesnímu klidu“ (3. 11. 2026) se změnilo rozvržení, barvy zůstaly:

- **Méně stránek, jasný další krok.** Přehled závodů má u každého závodu jeden odkaz „Další krok“ (Otevřít rozbor,
  Doplnit běh, Doplnit mapu, Pokračovat). Nahrát má běh ze tří zdrojů a mapy závodu na jedné stránce. Stránka závodu
  nemá záložky: mapa a úseky vedle sebe, vybraný úsek pod nimi, zbytek v rozbalovacích oddílech.
- **Levé menu** jen se skutečnými odkazy: Závody, Nahrát, pak Další. Dole „Data zůstávají v tomto počítači“, přepínač
  režimu a jazyk.
- **Prvky jsou jednotné:** tlačítko 34 px (malé 30 px), roh 5 px. Zelené je jen hlavní tlačítko stránky. Štítky stavu
  (`.stav`) mají vždy text, barva jen doplňuje. Tabulky mají záhlaví 12 px velkými písmeny, číslice vpravo.
- **Typografie:** Manrope pro text (základ 14 px), JetBrains Mono jen pro čísla (časy, vzdálenosti, ztráty).
  Nic v tabulkách a štítcích není menší než 12 px.
- **Ovládání klávesnicí:** viditelný `:focus-visible` na všem, ↑ ↓ v seznamu úseků, ← → mezi úseky u mapy,
  Esc zavře nabídku Další možnosti a vrátí se z úseku na celou trať. `aria-current` v menu, `role="status"` u průběhů.

### Kde jsou tokeny

Barvy jsou proměnné na začátku `webapp/static/les.css`: tmavý režim v `:root`, světlý v `:root[data-theme="svetly"]`.
Komponenty berou barvy jen z proměnných, nikdy napřímo. Barvy mapy (stopa podle ztráty, nejlepší postup, trať) jsou
v `webapp/static/ob.css` a se režimem se nemění.

### Barva je význam, ne ozdoba

Zelená znamená akci nebo „hotovo“, jantarová ztrátu nebo „chybí“, červená chybu, fialová trať (jako přetisk na mapě).
Jinde barva není. Každý stav má i slovo, aby byl čitelný bez barev a pro barvoslepé.

### Kontrast (WCAG 2, `python tools/kontrast.py`, hlídá `tests/test_kontrast.py`)

Běžný text potřebuje aspoň 4,5 : 1. Šedý tlumený text ve světlém režimu byl 4,4 : 1, proto je tmavší (`#55695B`).

| Kde | Barvy | Tmavý | Světlý |
|---|---|---|---|
| text na pozadí stránky | `--text-primary` na `--bg-app` | 14.4 : 1 | 13.8 : 1 |
| text na panelu | `--text-primary` na `--bg-panel-primary` | 11.4 : 1 | 15.5 : 1 |
| vedlejší text na panelu | `--text-secondary` na `--bg-panel-primary` | 6.2 : 1 | 6.7 : 1 |
| vedlejší text v záhlaví tabulky | `--text-secondary` na `--bg-panel-secondary` | 5.2 : 1 | 5.7 : 1 |
| tlumený text na panelu | `--text-muted` na `--bg-panel-primary` | 4.9 : 1 | 5.9 : 1 |
| tlumený text na pozadí (patička) | `--text-muted` na `--bg-app` | 6.1 : 1 | 5.3 : 1 |
| odkaz na panelu | `--odkaz` na `--bg-panel-primary` | 7.3 : 1 | 8.1 : 1 |
| odkaz na pozadí | `--odkaz` na `--bg-app` | 9.2 : 1 | 7.2 : 1 |
| hlavní tlačítko | `--on-brand` na `--zelena` | 7.0 : 1 | 8.1 : 1 |
| tlačítko | `--text-primary` na `--bg-panel-secondary` | 9.5 : 1 | 13.2 : 1 |
| štítek „hotovo“ / Nahráno | `--status-model-green` na `--bg-panel-primary` | 7.9 : 1 | 5.0 : 1 |
| ztráta, štítek „chybí“ | `--status-loss-amber` na `--bg-panel-primary` | 6.9 : 1 | 5.9 : 1 |
| štítek „chybí“ na podbarvení | `--status-loss-amber` na `--bg-panel-primary+--status-loss-dim` | 5.1 : 1 | 5.0 : 1 |
| chyba | `--cerv-cit` na `--bg-panel-primary` | 5.8 : 1 | 6.5 : 1 |
| aktivní filtr, odkaz Další krok | `--zelena` na `--bg-panel-primary` | 5.6 : 1 | 8.1 : 1 |

Nejhorší: 4.9 : 1

Okno lokální aplikace (`desktop/app.py`) má nejmenší velikost 960 × 600 a při startu barvu pozadí tmavého režimu
`#10251E`, takže nebliká bíle. Ve světlém režimu na okamžik problikne tmavá; je to kratší než načtení stránky.
