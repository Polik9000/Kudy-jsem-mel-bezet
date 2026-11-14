# Výkon: kde se tráví čas a paměť

Změřeno 1. 11. 2026 skriptem `tools/profil.py` (`python tools/profil.py pohora petrvald azymut-e5`). Stroj: cloudový
Linux, 4 jádra, 16 GB paměti, Python 3.13. Na notebooku uživatele to bude pomalejší, ale poměry mezi kroky a nároky
na paměť platí. Výškopis je z `tests/golden`, takže se v časech nestahuje nic. Kroky jsou ty, které pouští webová vrstva
(`webapp/services/runner.py`), každý ve vlastním procesu, takže špička paměti je špička toho kroku. Sprint v datech
repa není (je jen v Tobiasově lokální složce `data-extra/`), místo něj je druhá mapa velikosti Pohory (Azymut E5).

## Souhrn

| Závod | Obrázek mapy | analyze | terén + vzorky | postupy | záchytné body | **celkem** | **špička paměti** |
|---|---|---|---|---|---|---|---|
| Pohora | 1 510 × 1 037 (1,6 Mpx) | 5 s / 180 MB | 9 s / 481 MB | 10 s / 326 MB | 8 s / 197 MB | **31 s** | **481 MB** |
| Azymut E5 | podobně velký | 4 s / 206 MB | 11 s / 601 MB | 15 s / 531 MB | 9 s / 278 MB | **39 s** | **601 MB** |
| Petřvald | 5 016 × 3 691 (18,5 Mpx) | 65 s / 946 MB | 109 s / 2 040 MB | 197 s / 3 004 MB | 70 s / 1 292 MB | **442 s (7 min 20 s)** | **3 004 MB** |

Čas i paměť rostou zhruba lineárně s počtem pixelů mapy (Petřvald má 12× víc pixelů než Pohora: 14× víc času a
6× víc paměti), ne s počtem kontrol. Zhruba 160 B paměti na pixel v nejhorším kroku, takže mapa s 50 Mpx by chtěla
kolem 8 GB. To odpovídá pádu na Žebříčku B při 10 GB paměti Dockeru (úkol 39 v TODO.md). Běžný notebook s 8 GB
zvládne mapu do asi 25 Mpx, s 16 GB asi do 50 Mpx. Velikost běžných KMZ z Livelox jsem neměřil; Pohora a Petřvald mají 1,6 a 18,5 Mpx.

## Nejdražší místa (Petřvald, kumulativní čas)

| Krok | Funkce | Čas | Podíl kroku |
|---|---|---|---|
| analyze | `course.hough_circles` (hledání kružnic kontrol) | 40 s | 62 % |
| analyze | `course._find_triangle` (start) | 8 s | 12 % |
| terén + vzorky | `mapdata.terrain` → `terrain.classify` | 59 s | 54 % |
| terén + vzorky | `mapdata.obstacles` (zdi, ploty, vodoteče) | 40 s | 37 % |
| postupy | `routing.alternatives` + `_search` (hledání cest) | 79 s | 40 % |
| postupy | `mapdata.obstacles` (znovu) | 44 s | 22 % |
| postupy | `routing._build` (graf buněk) | 22 s | 11 % |
| záchytné body | `relocate.prepare` → `mapdata.obstacles` (potřetí) | 41 s | 59 % |

Hlavní zjištění: **`mapdata.obstacles` se pro jednu mapu počítá třikrát** (ve vzorcích, v postupech i v záchytných
bodech), dohromady asi 125 s ze 442 s. Uvnitř jsou to hlavně morfologické operace `scipy.ndimage`
(`binary_erosion`, `binary_dilation`, `binary_opening`, `distance_transform_edt`) na celém obrázku.

## Návrhy zrychlení (nové úkoly, ještě nezařazené do TODO.md)

1. **Uložit výsledek `mapdata.obstacles` vedle mapy** (klíč: mapa, zakázané čáry, verze kódu) a použít ho ve všech
   třech krocích. Odhad: úspora asi 85 s ze 442 s (19 %) na Petřvaldu, na Pohoře asi 4 s. Malé riziko, vyžaduje jen
   správný klíč mezipaměti (jinak by zůstaly staré překážky po změně zakázaných čar).
2. **Hledat kružnice jen na fialové masce a na zmenšeném obrázku** (`course.hough_circles`, teď přes celý obraz).
   Odhad: z 40 s na asi 5 až 10 s, tedy úspora asi 30 s (7 %) a méně paměti v `analyze`. Zlaté soubory by měly
   zůstat, ale musí se ověřit na všech závodech, které máme (poloměr kružnice se po zmenšení zaokrouhluje).
3. **Pustit záchytné body ve stejném procesu jako postupy**, aby sdílely překážky, terén a výškopis, které se teď
   načítají znovu. Odhad: dalších asi 40 s (9 %) na Petřvaldu. Po návrhu 1 menší přínos (asi 15 s).
4. **Snížit paměť: `float32` a `uint8` místo `float64` v terénu a grafu buněk** (`terrain.classify`, `routing._build`).
   Špička 3 GB je v postupech. Odhad: o třetinu až polovinu méně paměti (asi 1,5 až 2 GB), čas stejný nebo kratší.
   Riziko: drobné rozdíly v cenách, takže se musí zkontrolovat zlaté soubory.
5. **Hlídat velikost mapy při nahrání**: nad asi 25 Mpx říct česky, že analýza bude chtít víc paměti a potrvá déle
   (a nad asi 60 Mpx ji odmítnout nebo zmenšit mapu při čtení). Žádná úspora času, ale místo pádu srozumitelná věta.

## Jak to znovu změřit

```
python tools/profil.py pohora petrvald azymut-e5 --out /tmp/profil --top 10
```

Vypíše tabulky a deset nejdražších funkcí každého kroku; soubory `.prof` zůstanou v `--out` (`python -m pstats` nebo
`snakeviz`). Potřebuje `data/` a `tests/golden`, tedy data na autorově počítači (`docs/data-lokalne.md`). Kód rozboru skript nemění.
