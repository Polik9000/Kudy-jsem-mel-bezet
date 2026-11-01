# Logo

Varianty loga (náhled `nahled.png`). Použitá je **A, otazník z postupu**: start (trojúhelník), trasa ve tvaru
otazníku a kontrola (kroužek), tedy „Kudy?“. Barva je fialová značka tratě (#C2185B), stejná jako na stránce ke stažení.

- `a-otaznik.svg` (použitá), `b-dve-cesty.svg`, `c-lampion.svg`: návrhy, vlastní kresba bez cizích prvků.
- Zdroj pravdy je `desktop/icons.py`: z jedné geometrie kreslí SVG (`python desktop/icons.py --svg` přepíše
  `webapp/static/ob-logo.svg` a `docs/logo.svg`) i ikony instalátorů (`python desktop/icons.py build/icons`:
  `app.png`, `app.ico` pro Windows, `app.icns` pro macOS s okrajem podle Applu 824/1024).
- `docs/ikona-180.png` je ikona pro plochu iPhonu (apple-touch-icon).

## Varianty otazníku

`otaznik/`: šest obměn varianty A (lampion jako tečka, na kousku mapy, z vrstevnic, GPS stopa proti čáře tratě, zelená dlaždice, v kontrolním kruhu), náhled `otaznik/nahled.png`.
