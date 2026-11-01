# Instalátory: aplikace na vlastním počítači

Aplikace ke stažení je stejná Flask aplikace jako v Dockeru, jen spuštěná jinak (`desktop/app.py`):

- **jeden běžec, bez přihlášení** (`OB_LOCAL=1`): účet `ja` se založí sám, přihlášení a registrace vedou na
  Moje závody. Registrační číslo ORIS se zadá jednou v Profilu (nepovinné; bez něj jde závod přidat z ORIS nebo
  ručně). Žádné odkazy na klubový web, vlastní logo (kontrolní lampion).
- **data v uživatelské složce**, ne u programu, takže je aktualizace ani odinstalace nesmaže:
  Windows `%LOCALAPPDATA%\KudyJsemMelBezet`, macOS `~/Library/Application Support/KudyJsemMelBezet`.
  Uvnitř je stejné `app.db` (SQLite) a soubory jako v Docker volume. Záloha = zkopírovat složku.
- **úlohy ve vlákně** stejného procesu místo kontejneru `worker` (`webapp.worker.run_once`). Zavřená aplikace
  uprostřed výpočtu: úloha se při dalším spuštění pustí znovu.
- **okno** přes pywebview (Windows: WebView2, macOS: WebKit). Když okno nejde otevřít, otevře se výchozí prohlížeč
  a aplikace běží, dokud se v nabídce neklikne na Ukončit aplikaci. Server poslouchá jen na 127.0.0.1.
- **výpočty**: webová vrstva spouští `analyze.py`, `bestroute.py` a `python -m oroute.…` jako podprocesy přes
  `sys.executable`. V zabalené aplikaci je `sys.executable` aplikace sama, proto se při takovém příkazovém řádku
  chová jako python (`desktop.app.as_python`).
- **certifikáty**: na macOS zabalený Python nečte systémové certifikáty, proto se nastaví `SSL_CERT_FILE` na
  certifi (jinak by ORIS, ČÚZK i OpenStreetMap hlásily chybu certifikátu).

Balíček obsahuje jen kód (`desktop/kudy.spec`): `webapp/`, `oroute/` (včetně výchozího modelu rychlosti
`personal_model.json` a `slope_prior.json`), `analyze.py`, `bestroute.py`, `LICENSE`. **Žádné mapy, běhy, závody
ani `data/` a `tests/`.**

## Sestavení

GitHub Actions, workflow `.github/workflows/instalatory.yml`:

- **ručně** (Actions → Instalátory → Run workflow): sestaví a otestuje Windows i macOS, instalátory jsou ke stažení
  dole na stránce běhu (Artifacts). Nic se nezveřejní.
- **tag** `v*`: navíc založí **koncept** vydání v Releases s oběma soubory. Zveřejní se až tlačítkem Publish.

```
git tag v0.1.0
git push origin v0.1.0
```

Soubory: `KudyJsemMelBezet-windows-setup.exe` (Inno Setup, instaluje se jen pro přihlášeného uživatele, bez
správce) a `KudyJsemMelBezet-macos.dmg` (Apple Silicon, M1 a novější; Intel Mac zatím ne). Názvy jsou bez verze,
takže stránka ke stažení může odkazovat napořád na poslední vydání:

```
https://github.com/Polik9000/Kudy-jsem-mel-bezet/releases/latest/download/KudyJsemMelBezet-windows-setup.exe
https://github.com/Polik9000/Kudy-jsem-mel-bezet/releases/latest/download/KudyJsemMelBezet-macos.dmg
```

Každé sestavení se v Actions samo vyzkouší (`--smoke-test`): stránky odpovídají a všechny výpočetní skripty se
spustí (numpy, scipy, Pillow, fitdecode jsou v balíčku). Rozbor skutečného závodu se tam nezkouší, v repu nejsou
mapy.

Doma bez GitHubu (z kořene repa, Python 3.12):

```
pip install -r requirements.txt -r requirements-desktop.txt
python desktop/icons.py build/icons
pyinstaller --noconfirm desktop/kudy.spec          # -> dist/
python -m desktop.app                              # nebo bez balení, rovnou ze zdrojáků
```

`APP_CONSOLE=1 pyinstaller …` udělá na Windows verzi s konzolí, kde je vidět výpis (na hledání chyb).

## Podpis

Instalátory nejsou podepsané (podpis stojí peníze: Windows certifikát, Apple Developer 99 USD/rok).

- Windows: SmartScreen ukáže „Systém Windows ochránil váš počítač“ → Další informace → Přesto spustit.
- macOS: aplikace je podepsaná jen ad hoc. Při prvním spuštění macOS řekne, že ji nelze ověřit → Nastavení
  systému → Soukromí a zabezpečení → dole „Přesto otevřít“. Potom už se spouští normálně.

## Co je ověřené a co ne (1. 11. 2026)

Ověřeno v cloudu na Linuxu, se stejným `kudy.spec`:

- zabalená aplikace se spustí, bez přihlášení, stránky i styly odpovídají;
- **celý rozbor závodu přes zabalenou aplikaci**: ručně přidaný závod Azymut E5, nahrané KMZ s tratí, KMZ bez
  tratě a .fit přes formulář, úloha doběhla za 40 s, celkový čas 77:02 jako v testech, nejlepší postupy spočítané,
  model přepočítaný (mapy jen z lokálního testu, do balíčku nejdou);
- Ukončit aplikaci ukončí proces, data zůstanou;
- rychlé testy: 272 prošlo (nové `tests/test_desktop.py`), Docker verze se nemění.

Neověřeno (cloud nemá Windows ani macOS), musí se vyzkoušet **na čistém počítači** (bez Pythonu, bez Dockeru):

1. instalace (Windows: SmartScreen, macOS: Přesto otevřít), zástupce v nabídce Start / v Aplikacích;
2. otevře se okno aplikace, ne prohlížeč (WebView2 / WebKit);
3. Profil → registrační číslo ORIS → závody se načtou (ověří certifikáty a síť);
4. nahrát KMZ s tratí, KMZ bez tratě a .fit k jednomu závodu → rozbor doběhne, mapa se ukáže (ověří výpočty
   v podprocesech zabalené aplikace a výškopis ČÚZK);
5. nahrát celý export z Garminu (zip) → běhy se spárují, model kopců se spočítá (ověří paralelní výpočet
   `oroute.slopefit` v zabalené aplikaci);
6. zavřít okno, spustit znovu → závody tam jsou; odinstalovat → složka s daty zůstane.
