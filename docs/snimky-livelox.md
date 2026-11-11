# Snímky z Livelox: Chrome, Mac a Safari

Z testu na Macu (7. 11. 2026, issue 4). Postup je v nápovědě (`webapp/templates/ob/help.html`, `#snimky`).

## Co nápověda dělá

- Ukáže zkratky podle systému. Lokální aplikace zná systém sama (`sys.platform`, `data-os` na kartě), web ho pozná
  v prohlížeči (`navigator`). Dvěma tlačítky „Windows / Mac“ jde přepnout ručně. Bez skriptu jsou vidět obě verze.
- Doporučuje **Chrome i na Macu**: postup je stejný a ověřený. Windows: F12, Ctrl+Shift+M. Mac: ⌥⌘I, ⇧⌘M.
- Safari je druhá možnost (pod „Safari na Macu“).

## Co víme o Safari (z dokumentace Apple a WebKitu)

- Nabídka Vývojář se zapíná v Nastavení → Pokročilé. Režim responzivního designu je Vývojář → Vstoupit do režimu
  responzivního designu, zkratka **⌃⌘R** (ne ⌥⌘R).
- Velikost se mění tažením úchytů, poslední rozměr je předvolba „Vlastní velikost“. Pole pro zadání 5000 × 4000 v
  dokumentaci není a okno nejde zvětšit nad obrazovku.
- Tlačítko pro snímek celé stránky tam není. Zbývá snímek obrazovky (⇧⌘4, ⇧⌘5), tedy menší a méně ostrý než z Chrome.
- **Neověřeno na Macu:** jestli Web Inspector (Elements → pravým na prvek → Capture Screenshot) dá větší snímek.
  Otázka 58 v `docs/co-zbyva.md`.

## Obrázek mapy z canvasu v Safari: zatím ne

Nápad: Livelox kreslí mapu do `<canvas>`; Safari ji může uložit v plném rozlišení a bez tratě.

- Lepší: plné rozlišení, žádná trať, žádné zakryté místo.
- Problém: obrázek není usazený a nemá stejný pohled jako snímek s tratí. `oroute/pair.py` (`place_pair`) a
  `webapp/services/screens.py` počítají, že oba snímky jsou ze **stejného pohledu** a druhému dají stejné usazení.
  Obrázek z canvasu by se musel napasovat (posun, otočení, měřítko; hledání stejných míst, numpy/scipy/Pillow,
  bez nové knihovny).
- Neověřeno: že obrázek opravdu nemá trať a má plné rozlišení.
- Rozhodnutí: bez vzorových dat (obrázek z canvasu + snímek s tratí z jednoho závodu) pole do Podkladů nepřidávám,
  nešlo by změřit, že napasování vyjde na pár metrů. Otázka 57 v `docs/co-zbyva.md`.
