# Vzhled aplikace „Kudy jsem měl běžet“

Od 3. 11. 2026 platí vzhled **Lesní klid** podle návrhu z PDF „Kudy jsem měl běžet – Návrh uživatelského rozhraní“. Nahradil dřívější petrolejovou paletu Buzola (ta zůstává jako `OB_THEME=kudy`).

## Jak je to poskládané

- `webapp/static/skob.css`: klubová kostra (rozložení, tabulky, menu). Beze změny, je to kopie z webu oddílu.
- `webapp/static/ob.css`: prvky aplikace (mapa, úseky, formuláře). Barvy bere z proměnných.
- `webapp/static/les.css`: vzhled Lesní klid. Načítá se **jako poslední** a přepíše proměnné (tmavé pozadí, fialový akcent), přidá levý panel 220 px, spodní lištu na telefonu a komponenty návrhu (metriky, pruhy rychlostí, graf ztrát, panel vrstev nad mapou, O aplikaci).
- `webapp/static/kudy.css`: starší petrolejový vzhled (`OB_THEME=kudy`).
- `OB_THEME=skob` vypne obě vlastní sady a aplikace vypadá jako klubový web. Výchozí je `les`.
- Tmavý režim je výchozí. Tlačítko ◐ v hlavičce přepíná tmavý, světlý a podle zařízení (světlý se hodí venku na slunci).

## Tokeny (z PDF)

| Token | Hodnota | Použití |
|---|---|---|
| `--bg-app` | `#10251E` | pozadí okna |
| `--bg-panel-primary` | `#19382C` | karty, levý panel, hlavička |
| `--bg-panel-secondary` | `#214535` | vnořené karty, ovládací bloky |
| `--bg-surface-elevated` | `#2A503E` | hover, vybraný řádek |
| `--accent-iof-purple` | `#C9A6F3` | aktivní položka, hlavní tlačítko, vybraný úsek |
| `--status-model-green` | `#B8D68C` | model, v pořádku |
| `--status-loss-amber` | `#E5B86B` | ztráta, málo dat |

Písma: **Manrope** (text) a **JetBrains Mono** (čísla, časy), oba OFL, soubory i licence v `webapp/static/fonts/`, nic se nestahuje z internetu.

Na mapě se barvy nemění: stopa podle ztráty (zelená, oranžová, červená), nejlepší postup modrý čárkovaný, trať fialová. Čáry mají bílé lemování, ať je vidět na každé mapě.

## Odchylky od PDF (záměrné)

- PDF obsahuje ukázková data, položky bez zdroje v aplikaci (výběr modelu jiného běžce, „učebnicový model“, přepínač ČÚZK, rastr průchodnosti) a mapu se sloupcovým grafem přes mapu. Zobrazuje se jen to, co appka opravdu spočítá; graf ztrát je pod mapou, aby nezakrýval trať.
- Světlý režim navíc (PDF je jen tmavé).
- Zkratky vrstev mapy: M mapa, T mapa s tratí, 1 další možnosti, 2 průměrný běžec, 3 záchytné body. Šipky přepínají úseky.
- Detail úseku je ve stejné stránce jako detail závodu (pravý panel), ne zvláštní obrazovka: tak zůstává mapa, poznámky i kreslení postupu beze změny.

## Aplikace pro Windows a macOS

Okno (`desktop/app.py`) zobrazuje stejné rozhraní. Minimální velikost okna je 960 × 600 (vejde se levý panel i mapa), pozadí okna má barvu aplikace, ať při startu neblikne bílá.
