# Vzhled aplikace „Kudy jsem měl běžet“

Od 3. 11. 2026 má aplikace vlastní vzhled místo klubového (zelená hlavička a trikolóra SKOB). Tobias vybral ze tří návrhů paletu **C · Buzola**.

## Jak je to poskládané

- `webapp/static/skob.css`: klubová kostra (rozložení, menu, tabulky). Zůstává beze změny, je to kopie z webu oddílu.
- `webapp/static/kudy.css`: vlastní vzhled. Přepisuje barvy (proměnné `--c-*` a neutrály), písmo nadpisů, hlavičku a levé menu.
- `webapp/static/ob.css`: prvky aplikace (mapa, úseky, formuláře). Barvy bere jen z proměnných.
- `OB_THEME=skob` vypne `kudy.css`, takže aplikace vypadá zase přesně jako klubový web (pro nasazení u oddílu). Výchozí je `kudy`.
- Jiný klub si může dát vlastní barvu přepsáním `--c-primary` atd. v dalším souboru za `kudy.css`.

## Paleta

| Role | Světlý | Tmavý | Kde |
|---|---|---|---|
| Značka (petrolejová) | `#0F5C6E` | text `#6CC4D6` | hlavička, hlavní tlačítko, aktivní položka |
| Signál (žlutá) | `#F2C230` | `#F2C230` | linka pod hlavičkou, odznaky, vybraný řádek |
| Text | `#16232A` | `#E4ECEE` | |
| Podklad stránky | `#F3F6F7` | `#0E1619` | |
| Karta | `#FFFFFF` | `#152024` | |
| Linka | `#E0E7EA` | `#22313A` | |
| V pořádku | `#2B8A3E` | `#69DB7C` | stav „hotovo“, „je“ |

Na mapě se barvy nemění: tvoje stopa červená, nejlepší postup modrý čárkovaný, trať fialová jako přetisk, plánovaný postup oranžový. Ztráta na úseku je semafor zelená, oranžová, červená (`--flag-a/b/c`).

## Písmo

Nadpisy a hlavička: **Barlow Semi Condensed** 600/700 (OFL 1.1, soubory i licence ve `webapp/static/fonts/`, nic se nestahuje z internetu). Text a tabulky: systémové písmo, čísla zarovnaná pod sebe.

Stránka ke stažení (`docs/index.html`) používá stejnou paletu.
