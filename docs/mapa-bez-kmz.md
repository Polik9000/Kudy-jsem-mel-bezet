# Mapa, když Livelox nedovolí stáhnout KMZ

Průzkum z 23. 11. 2026. Nic se podle něj zatím nemění. Popisuje, jaké jsou možnosti a co z nich doporučujeme.
„Obtížnost“ znamená, kolik práce to dá závodníkovi. Přesnost platí pro výpočet v aplikaci.

## Co aplikace umí teď

Zdroje mapy jsou ve formuláři v tomto pořadí (`webapp/templates/ob/race.html`):

1. **KMZ z Livelox**. Nejpřesnější, 1 až 1,33 m na pixel.
2. **Dva snímky obrazovky z Livelox**, s tratí a bez ní (`oroute/pair.py`). Mapa se usadí s chybou 6 až 15 m.
   Snímky se dělají přes Chrome DevTools v okně 5000 × 4000 (`help.html`, `docs/snimky-livelox.md`). Pro běžného
   závodníka je to nejtěžší krok.
3. **Fotka papírové mapy** (`oroute/georef.py`). Usadí se sama podle kontrol a stopy z hodinek. Automaticky se usadí
   95 % fotek, dobře 89 %. Medián chyby v rozích je 16 m. Z fotky je jen trať, terén se z ní spolehlivě nečte
   (`docs/foto-mapy.md`).

Mapu z obrázku aplikace usazuje podle kontrol. Kde kontrola leží v terénu, zjistí z mezičasů: je to místo, kde
byla stopa v čase ražení podle ORIS (`georef.control_positions`). Hodinky stačí mít zapnuté po celý závod. Dřívější
zapnutí nevadí, časy se párují podle skutečných hodin. Kontroly ale musí aplikace najít i na obrázku, jako kroužky
tratě. Proto potřebuje mapu s tratí té kategorie, kterou člověk běžel.

## Možnosti

| # | Možnost | Obtížnost | Kvalita mapy | Právně | Hodnocení |
|---|---|---|---|---|---|
| 1 | Požádat pořadatele o KMZ nebo obrázek | nízká, ale čeká se | nejlepší | v pořádku | ✅ zmínit vždy |
| 2 | **Fotka mapy mobilem** (už umíme) | **nejnižší**, jedna fotka | střední, ±16 až 36 m, bez terénu | v pořádku, vlastní mapa | ✅ **nejlehčí cesta** |
| 3 | **Archiv map ČSOS** (mapy.ceskyorientak.cz), obrázek podržet a uložit | nízká | dobrá, asi 1,1 m/px, s vodoznakem | prohlížení ano, další šíření ne | 🟡 jen když je tam tvoje kategorie |
| 4 | Jeden obyčejný snímek obrazovky z Livelox (Win+Shift+S, Cmd+Shift+4), trasy skryté | nízká | horší, 2 až 4 m/px | jen pro sebe | 🟡 aplikace zatím chce dva snímky |
| 5 | Dva snímky přes DevTools (dnešní postup) | střední až vysoká | dobrá, terén jde | jen pro sebe | 🟡 funguje, ale je složitý |
| 6 | Víc snímků přiblížené mapy a slepit je (Hugin, MS ICE) | vysoká | dobrá | jen pro sebe | ❌ moc práce |
| 7 | OB Postupy (obpostupy.orientacnisporty.cz, dřív obpostupy.cz) | nízká, pokud tam mapa je | dobrá, s tratí | podle pořadatele | ❌ teď nefunguje, zkusit později |
| 8 | Odstranit vodoznak z archivu | pro závodníka nízká | rozmaže drobné značky | riziko, viz níže | ❌ nedělat |
| 9 | Uložit obrázek mapy z Livelox přes DevTools, Network | nízká až střední | plná | obchází vůli pořadatele | ❌ nedoporučovat |
| 10 | Rozšíření a skripty na stažení z Livelox (livelox-dl, importer Routechoices a podobně) | nízká | plná, se souřadnicemi | obchází vypnuté stažení | ❌ nedělat, neodkazovat |
| 11 | Routechoices, 3DRerun, WorldofO, RouteGadget, DOMA | různá | dobrá | podle pořadatele | 🟡 v Česku jen pár závodů |

### Livelox

- Stažení mapy vypíná pořadatel. Závodník to obejít nemůže, jen ho požádat.
- API mapy nedává ([dokumentace](https://www.livelox.com/Documentation/Api)). Práva k mapám mají pořadatelé
  ([uživatelská smlouva](https://www.livelox.com/UserAgreement)).
- Prohlížeč technicky stahuje celý obrázek mapy, takže vypnuté stažení jen schová tlačítko. Existují rozšíření
  a skripty, které ho stáhnou. Neděláme to a neodkazujeme na ně: jde to proti vůli pořadatele a proti dřívějšímu
  rozhodnutí (`docs/pruzkum.md`, `docs/automatizace.md`).
- Trasy ostatních závodníků jdou v prohlížeči skrýt. Tisk tam podle všeho není (ověřeno jen zběžně).

### Archiv map ČSOS (mapy.ceskyorientak.cz)

Vyzkoušeno na dvou mapách: Galánečka (2. JKŽ Bílá, 30. 3. 2025, D12C) a Zbojníček II (POŽ SFM Bílá, H10C,
stav 9/2026). Měřilo se jen nad obrázky. Celý rozbor neproběhl, protože k těm závodům nebyla stopa ani mezičasy.

- **Rozlišení**: 2700 × 1909 px, 244 dpi. Při 1 : 10 000 je to asi 1,1 m/px, stejně jako KMZ z Livelox.
  Starší zápis v `docs/pruzkum.md` (96 dpi) neplatí.
- **Trať**: mapa je vzorový výtisk závodu s tratí **jedné kategorie**. Pro jinou kategorii se mapa podle tvých
  kontrol neusadí, leda podle kontrol se stejným kódem.
- **Stažení**: jen obrázek (pravým tlačítkem Uložit, na mobilu podržet). KMZ ani KML tam není.
- **Vodoznak**: šikmý nápis „Mapový portál ČSOS“, všude jedna barva (asi RGB 167, 186, 216), poloprůhledný,
  asi 5 % plochy. Hledání fialové tratě ho nebere (`georef.loose_purple`), pro usazení tedy nevadí.
- **Barva tratě**: u Galánečky je fialová, aplikace ji najde. U Zbojníčku je **červená** (asi RGB 181, 40, 45)
  a tu aplikace dnes nenajde. Taková mapa by šla usadit jen ručně.
- Zbojníček je sken (otočený, s okraji papíru), Galánečka je čistý export.

Použití: když je v archivu tvoje kategorie, nahraj obrázek jako fotku. Vodoznak se neodstraňuje.

### Proč neodstraňovat vodoznak

- Pro usazení ani pro trať to není potřeba.
- Mapa je autorské dílo vydavatele. Odstranění údajů o právech je podle § 44 zákona č. 121/2000 Sb. samo o sobě
  zásah do práva. Jestli sem patří i viditelný vodoznak, je sporné, ale riziko je skutečné.
- Domalování místo vodoznaku (například `cv2.inpaint`) rozmaže vrstevnice a drobné značky.

### OB Postupy

ČSOS službu znovu spustil na obpostupy.orientacnisporty.cz
([orientacnibeh.cz](https://www.orientacnibeh.cz/novinky-sekce-ob/nove-ob-postupy-pro-analyzu-zavodu),
[o-news.cz](https://o-news.cz/nove-obpostupy-cz/)). Pořadatelé tam nahrávají mapy s tratí a výsledky jsou z ORIS.
Dne 23. 11. 2026 web nešel otevřít: chybný certifikát a pak `ERR_TOO_MANY_REDIRECTS`. Zkusit znovu později.

## Doporučení

1. **Fotka mobilem je nejlehčí záloha.** Funguje už teď. V nápovědě ji dát na první místo.
2. **Archiv ČSOS jako tip**, když je tam tvoje kategorie. Nahrát jako fotku.
3. **Jednodušší snímek obrazovky**: jeden obyčejný snímek s celou mapou a tratí, trasy skryté. Aplikace by ho
   usadila jako snímek (`place(..., screen=True)`). Postup přes DevTools zůstane jako přesnější volba.
4. **Nedělat**: odstranění vodoznaku, obcházení Livelox, hromadné stahování z archivu.

Nápady na později, nedělat bez schválení:

- hledat trať i v červené barvě (`georef.loose_purple`);
- usadit mapu jiné kategorie podle kontrol se stejným kódem (kódy jsou v popisu kontrol, kódy ražení v ORIS).
