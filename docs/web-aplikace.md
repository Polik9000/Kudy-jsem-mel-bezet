# Webová aplikace (stav 7. 10. 2026)

Web je obal nad analyzátorem. Výpočty jsou ve skriptech `analyze.py`, `bestroute.py` a v balíku `oroute`; složka `webapp/` řeší jen účty, ORIS, nahrávání, frontu úloh a stránky. Žádné AI API. Vzhled je klubový web SKOB Frýdek-Místek (`skob.css` beze změny).

Co kde je popsané: adresy, cizí služby, databáze a nastavení v `docs/api-a-data.md`, volby a jejich důvody v `docs/rozhodnuti.md`, měření přesnosti v `docs/validace.md`, co není hotové v `docs/co-zbyva.md`.

## Spuštění

```
docker compose up --build  # http://localhost:8000/ob/
```

Běží dvě služby ze stejného image: `web` (stránky, gunicorn) a `worker` (analýzy na pozadí). Databáze a nahrané soubory jsou v Docker svazku `ob_data`, ne v repozitáři. Databáze ze starší verze se při startu sama doplní o nové sloupce.

Ukázková data (čtyři závody z `data/`, patří k registračce `BFM0903`) a správa účtů:

```
docker compose exec web flask --app webapp.wsgi seed-demo BFM0903                 # pro existující účet
docker compose exec web flask --app webapp.wsgi seed-demo JMENO --password HESLO  # založí účet, když registračku ještě nikdo nemá
docker compose exec web flask --app webapp.wsgi invite BFM0903 BFM0305 --site http://localhost:8000   # kódy k registraci
docker compose exec web flask --app webapp.wsgi reset-code BFM0903 --site http://localhost:8000        # jednorázový kód k novému heslu
docker compose exec web flask --app webapp.wsgi delete-account JMENO_NEBO_REGISTRACKA          # vypíše, co by se smazalo
docker compose exec web flask --app webapp.wsgi delete-account JMENO_NEBO_REGISTRACKA --yes    # smaže
```

`invite` vypíše ke každé registračce její kód a odkaz na registraci s vyplněným číslem i kódem (`--site` je adresa webu, bez něj vypíše jen cestu). Kód nebo odkaz pošli členovi; bez kódu si účet nezaloží nikdo, ani na vlastní číslo.

Smazání účtu odstraní jeho závody, aktivity, analýzy, poznámky, modely a ručně přidané závody, které nemá nikdo jiný. Závody z ORIS a jejich mapy zůstávají, jsou sdílené. Totéž udělá člen sám v profilu („Zrušení účtu“, potvrzuje heslem).

`reset-code` vypíše jednorázový kód k novému heslu (platí 24 hodin, jedno použití, pět špatných pokusů ho zneplatní; v databázi je jen jeho hash). Člen ho zadá na stránce „Zapomenuté heslo“ (`/ob/forgot`, odkaz je v přihlášení) spolu s registračkou a novým heslem.

Testy a linter:

```
docker compose run --rm web pytest -m "not slow"     # asi minuta
docker compose run --rm web pytest -m slow           # asi 10 minut: čtyři závody skripty i přes web
docker compose run --rm web ruff check .
```

Vývoj bez přestavování image (zdrojáky připojené do kontejneru, vlastní svazek dat):

```
docker compose -p obdev -f docker-compose.yml -f docker-compose.dev.yml up
```

## Jak se to používá

1. **Účet** se zakládá registračním číslem ORIS (tři písmena oddílu a čtyři číslice, formuláře ukazují příklad `BFM0000`), kódem od správce a heslem na adrese `/ob/register`. Kód patří k registračnímu číslu a vypíše ho správce příkazem `invite` (výše); díky němu si účet na cizí číslo nikdo nezaloží. Jméno a ORIS ID se vezmou z ORIS, závody se načtou samy. Na jedno registrační číslo může být jen jeden účet a číslo účtu se už nedá změnit (v profilu se jen ukazuje); přihlásit se dá registračkou (u starších účtů i původním jménem). Přihlášení vydrží 90 dní od poslední návštěvy.
2. **Moje závody**: u každého je stav „chybí aktivita“, „chybí mapa“ nebo „hotovo“; stav, kterému něco chybí, vede rovnou do Podkladů závodu. Filtr podle sezóny (pamatuje se) a stavu, filtr „S během“, hledání.
3. **Nahrát běhy** (v lokální appce je nahoře odkaz **Načíst z Garmin Connect**, i na Přehledu závodů; tlačítko Načíst vybrané je na té stránce v liště nad tabulkou, která zůstává vidět): jednotlivé `.fit` (i víc najednou) nebo celý export účtu Garmin (zip). Běhy se spárují se závody podle data, času startu a vzdálenosti od centra závodu z ORIS. U závodu jde aktivitu vybrat ručně. Úloha exportu si nejdřív sama načte tvoje závody z ORIS, pak páruje. Z celého exportu se spočítá model kopců a potom zůstanou jen běhy spárované se závody a běhy ze dne závodu do 15 km od něj, které se nespárovaly; ty mají v seznamu nahraných aktivit označení „nespárované u závodu“ a tlačítka Přiřadit a Smazat. Zpráva úlohy říká, kolik běhů zůstalo a kolik bylo smazáno; smazané se vrátí jen opětovným nahráním exportu.
4. **Mapy** u závodu, záložka Podklady: KMZ s tratí (platí pro kategorii) a KMZ bez tratě (platí pro celý závod, stačí jednou za oddíl). Místo KMZ s tratí jde nahrát obrázek (jpg, png, sken, fotka): usadí se sám podle koleček kontrol a tvé stopy v oficiálních časech ražení.
5. **Analýza** se zařadí do fronty sama. Bez mapy bez tratě vyjdou mezičasy a typy chyb, s ní i nejlepší postupy. Stopa na mapě, mezičasy a typy chyb se u nového závodu ukážou hned, jak je první skript hotový; postupy přibydou, až doběhnou. Stránka závodu mezitím píše, co se právě počítá (například „hledám nejlepší postupy: 7 z 18 úseků“) a kolik úloh je ve frontě před ní.
6. **Závod mimo ORIS** (zahraničí) se přidá ručně.

### Stránka závodu

- **Mapa a úseky**: mapa závodu jako překryv, stopa obarvená podle ztráty, nejlepší postup a po kliknutí na úsek až dvě další odlišné možnosti s rozdílem času. U vyrovnaných postupů značka ≈ a upozornění. Tabulka úseků: ztráta volbou postupu, ztráta provedením, ztráta podle mezičasů kategorie, typ chyby (přeběhnutí, nedoběhnutí, úhyb ze směru, hledání v kruhu, nové určení polohy), vysvětlení česky. U vybraného úseku náběhový bod před kontrolou (bodový objekt ze směru, kterým přichází nejlepší postup) a zarážka za kontrolou (na co narazí, kdo kontrolu přeběhl: vlevo, rovně a vpravo od směru doběhu cesta, vodoteč, břeh, plot oplocenky, okraj paseky, pole nebo zástavby, se vzdáleností a azimutem zpět; na mapě čárkovaná čára); oba jsou odhad z mapy. Při vybraném úseku jsou na mapě jen jeho čáry; čip „Celá trať“ nebo Esc vrátí celou trať. Když tvoje stopa vede tudy, kudy nejlepší postup nesmí (železnice mimo přechod, zakázaný prostor, oplocenka), panel to řekne a označí místo: proto může stopa vyjít rychlejší než „nejlepší“.
- **Plánovaný postup**: čáru nakreslenou k úseku ocení model hned po uložení (krátká úloha na pozadí, výsledek se na stránce objeví sám). Panel úseku má jednu tabulku: nejlepší postup, plán, tvoje stopa a další možnosti, u každého čas podle modelu, rozdíl proti nejlepšímu, délka a stoupání. Pod ní věta, například „Plán byl o 0:19 pomalejší než nejlepší postup, hlavně kvůli 34 m v zelené nebo bažině navíc. Dalších 0:43 jsi ztratil při provedení: od plánu ses odchýlil až o 72 m.“ Po nové analýze závodu se plány ocení znovu.
- **Kdyby ses ztratil**: rozbalovací část v panelu úseku se 2 až 4 záchytnými body do 150 m od kontroly (křížení cest, konec cesty, cesta, vodoteč, cesta přes vodoteč, budova, vodní plocha, oplocenka, paseka, okraj otevřené plochy nebo zakázaného prostoru, vrchol z výškopisu a bodové značky mapy: kupka, prohlubeň, jáma, výrazný terénní objekt, balvan, jáma s vodou, studna, výrazný strom, posed, umělý objekt): kde bod leží (azimut k severu mapy a vzdálenost) a jak se od něj dostat ke kontrole („z křížení cest 71 m na azimut 315°, z kopce“). Kde stopa ukazuje bloudění, napíše, kde jsi opustil přímý směr, kolik jsi naběhal navíc a který bod byl nejblíž. Volba „záchytné body“ pod mapou je kreslí do mapy i s místem ztráty kontaktu a prochozenou stopou. Body se čtou z kresby mapy bez tratě a jmenují se podle českého ISOM 2017-2; bodové značky kromě kupky a stromu jen z obrázků ostrých aspoň 0,9 m na pixel. Plot, který nic neuzavírá, čte aplikace jako cestu. Popisy kontrol aplikace nezná. Rozbor se záchytnými body ze starší verze výpočtu má nad mapou tlačítko „Přepočítat záchytné body“ (krátká úloha, postupy nemění).
- **Mezičasy kategorie**: funguje i bez `.fit` a bez mapy. Normální výkon, chyby metodou WinSplits (ztráta přes 30 s a 25 %), graf mezičasů, ztráta po úsecích, tabulka běžců, a kontrola, jestli model řadí úseky stejně jako kategorie.
- **Podklady**: jeden formulář na běh z hodinek (`.fit`, spáruje se rovnou s tímhle závodem) a obě mapy; soubory jde do polí přetáhnout, při nahrávání je vidět průběh a analýza se zařadí jednou. Dokud něco chybí, jsou nad záložkami tři kroky se stavem a závod se otevírá na Podkladech.
- **Procházení úseků**: pás úseků nad mapou obarvený podle ztráty, šipky v něm a klávesy ← →. Alternativy postupu mají v mapě čísla 2 a 3 jako v panelu. Na telefonu je hned pod mapou řádek s úsekem, časem, ztrátou a typem chyby.
- **Poznámky** se ukládají samy vteřinu po dopsání.
- **Kreslení do mapy** (plánovaný postup, zakázaná čára, občerstvovačka): nad mapou je lišta, která říká, co se kreslí, s tlačítky Zpět o bod, Hotovo a Zrušit. Dvojklik nebo Enter uloží, Esc zruší.
- **Vybraný úsek je v adrese** (`…/races/12#usek-7`), takže přežije načtení stránky a jde poslat odkazem.
- **Stránka se načte znovu sama**, jen když ukazuje stav úloh (seznam závodů, úlohy, závod s čekající analýzou), a nikdy přes vybraný soubor, rozepsaný formulář, kreslenou čáru nebo psanou poznámku. Po načtení se vrátí na stejné místo: otevřená záložka a prvek, který byl nahoře v okně, se drží v `sessionStorage` jen pro tuhle záložku prohlížeče.
- **Co se počítá** ukazuje lišta dole v okně (na telefonu nad spodní nabídkou), ne odstavec nad mapou: nic pod ní se během výpočtu neposune. Když úloha selže, lišta na chvíli řekne, že je hláška nahoře na stránce.
- **Nastavení závodu**: železnice a dálnice z OpenStreetMap „zakázáno / jen znevýhodněno / nepoužívat“ a zakázané prostory přečtené ze šrafování mapy s tratí „zakázáno / nepoužívat“ si každý nastavuje jen pro sebe (výchozí je „jako závod“) a změna přepočítá jen jeho postupy. Výchozí hodnotu závodu mění jen ten, kdo nahrál mapu bez tratě. Ruční zakázané a těžko překonatelné čáry a občerstvovačky jsou sdílené pro všechny, kdo závod běželi; u každé je vidět, kdo ji přidal, a smazat ji smí jen on.

### Poznámky k úseku a co změní

| Volba | Ztráta úseku | Osobní model |
|---|---|---|
| Záměrná zastávka (zaškrtnutá, nebo do 30 m od značky občerstvovačky) | sekundy stání se nepočítají jako chyba | čas úseku se bere bez zastávky, úsek může být čistý |
| Ztráta kontaktu s mapou | celá ztráta je chyba, ne volba postupu | úsek se nepočítá |
| Zelená: obíhal | beze změny | body stopy, které GPS dala do zelené, se vynechají |
| Zelená: proběhl | beze změny | beze změny |
| Únava 4 až 5 | ztráta provedením je únava, ne chyba | úsek se nepočítá |
| Text, plánovaný postup | beze změny (plán se jen ocení a ukáže vedle skutečnosti) | beze změny |

Pravidla jsou v `oroute/annotations.py`. Tabulka se přepočítá hned, model na pozadí.

## Nastavení rozhraní

Světlý / tmavý režim a jazyk se ukládají k účtu (`users.theme`, `users.lang`), ne jen v prohlížeči. Lokální appka startuje pokaždé na jiném portu a prohlížeč drží `localStorage` zvlášť pro každou adresu i s portem, takže režim uložený jen tam se po restartu ztratil. Server píše režim rovnou do `<html data-theme>` (žádné bliknutí); `localStorage` je jen kopie pro stránky bez účtu (přihlášení).

## ORIS má přednost

Když ORIS zná čas startu a mezičasy, jsou pravdou ony: stopa z hodinek se jen rozřeže v oficiálních okamžicích (`oroute/official.py`). Proto Pohora dává 50:22 (z GPS samotné 51:05). Nesedí-li počet kontrol s mapou, nepokrývá-li záznam čas závodu, nebo je-li stopa v oficiálních časech daleko od kontrol, použije se odhad z GPS a stránka napíše proč. Závody mimo ORIS (Azymut) jedou z GPS: E5 77:02, Day 4 55:07.

## Osobní model

Každý uživatel má svůj. Při každé analýze s mapou bez tratě se přepočítá ze všech jeho závodů (poločas 365 dní), a to ještě před hledáním postupů: úloha nejdřív zjistí, co se model z nového závodu naučí (`bestroute.py --samples-only`), model přepočítá a postupy pak hledá jednou, už s ním. Stránka modelu ukazuje rychlost v každém terénu (km/h, min/km), kolik dat v něm je, nejistotu, křivku sklonu s naměřenými body a zkoušku „předpověď z ostatních závodů“. Tvar kopců je výchozí z `oroute/slope_prior.json`; po nahrání celého Garmin exportu vlastní.

## Jak aplikaci přidat k tátovu webu (cesta A: vedle něj)

Aplikace je samostatný proces s vlastní databází a přihlášením. Klubový web zůstává bez účtů; propojení je jen odkazy a společným CSS.

1. **Proces.** Na serveru běží `gunicorn webapp.wsgi:app` (stránky) a pracovní úloha. Bez Dockeru:

   ```
   OB_INSTANCE=/cesta/k/datum gunicorn --bind 127.0.0.1:8010 --workers 2 --threads 4 --timeout 900 webapp.wsgi:app
   */5 * * * *  cd /cesta/k/OB_tracker && OB_INSTANCE=/cesta/k/datum python -m webapp.worker --once     # cron
   ```

   Analýza jednoho závodu vytíží jedno jádro; Petřvald, nejtěžší ze čtyř ukázkových, trvá necelé 3 minuty a potřebuje asi 1,5 GB paměti (měření v `docs/co-zbyva.md`). `worker --once` zpracuje frontu a skončí, takže neběží trvale.
2. **Cesta `/ob`.** Proxy před klubovým webem (Cloudflare → jeho server) přepošle `/ob/...` na náš proces **beze změny cesty**. Aplikace si předponu `/ob` řeší sama (`OB_URL_PREFIX`), včetně cookie `ob_session` s cestou `/ob`. Za proxy nastav `OB_PROXY=1`, ať aplikace věří hlavičkám `X-Forwarded-Proto` a `X-Forwarded-Host`. Příklad pro nginx:

   ```
   location /ob/ { proxy_pass http://127.0.0.1:8010; proxy_set_header Host $host;
                   proxy_set_header X-Forwarded-Proto $scheme; proxy_set_header X-Forwarded-For $remote_addr;
                   client_max_body_size 4g; proxy_read_timeout 900s; }
   ```

3. **Sdílené CSS.** `webapp/static/skob.css` je kopie jeho `/static/skob.css`; při změně klubového vzhledu se soubor jen přepíše novou verzí (a s ním `docs/reference/skob-klubovy-web.css`, test hlídá shodu). Vlastní styly jsou v `ob.css` a stojí jen na jeho proměnných. Logo a ikony jsou také kopie. Aplikace posílá stejné hlavičky CSP jako klubový web a nic nenačítá z cizí domény.
4. **Odkazy z klubového webu k nám** se zatím nepřidávají (rozhodnutí 7. 10.). Adresy jsou připravené: u závodu `https://…/ob/zavod/oris-<ORIS ID závodu>`, na vizitce `https://…/ob/clen/<ORIS ID osoby>`. Přihlášenému se otevře jeho rozbor, nepřihlášenému přihlášení a pak rozbor.
5. **Odkazy od nás na klubový web** jdou podle `OB_CLUB_URL` (závod, vizitka, archiv člena). Název klubu a logo jsou v `OB_CLUB_NAME` a `OB_CLUB_LOGO` (`webapp/club.py`).
6. **Místo na disku.** Mapa závodu má 5 až 30 MB, výstupy analýzy jednoho běžce asi 4 MB (obrázky skriptů web od 7. 10. nedělá). Na serveru s 1,6 GB volného místa je potřeba buď jiný disk pro `OB_INSTANCE`, nebo mazat obrázky skriptů po uložení výsledků (viz `co-zbyva.md`).
7. **Registrace a hesla.** Heslo si člen změní v profilu; k zapomenutému mu správce vypíše jednorázový kód (`flask --app webapp.wsgi reset-code REGISTRACKA`) a člen si nové nastaví sám na `/ob/forgot`. Účet si člen založí jen s kódem své registračky, který mu dá správce (`flask --app webapp.wsgi invite REGISTRACKA`). Kódy se nikam neukládají, počítají se z tajného klíče aplikace: pro jedno číslo vyjde vždy stejný kód a po výměně `OB_SECRET_KEY` přestanou nevyužité kódy platit (a všichni se musí znovu přihlásit). `OB_REGISTRATION=0` registraci zavře úplně. Na jednu registračku je jeden účet a číslo se u účtu nemění; zrušit účet jde příkazem `delete-account` nebo ho člen zruší sám v profilu.

Cesta B (blueprint uvnitř jeho aplikace) zůstává možná, `webapp/views` je blueprint `ob`, ale do webu bez účtů by přinesla přihlašování a nahrávání souborů; nedoporučuji.

## Co není hotové

Viz `docs/co-zbyva.md`.
