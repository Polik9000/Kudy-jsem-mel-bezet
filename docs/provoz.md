# Provoz pro klub: denní načítání z ORIS, zálohy, obnova

Všechno je vypnuté, dokud to správce nezapne. Nic z toho nemění přihlášení ani výpočty.

## Denní načítání z ORIS (`flask sync-oris-all`)

Načte nové závody všech účtů s registračním číslem. ORIS se ptá co nejméně:

- u každého účtu jednou `getUserEventEntries` (přihlášky);
- `getUser` jen u účtu, u kterého ještě neznáme ORIS ID (to se uloží při registraci);
- `getEvent` a `getSplits` jen u závodu, který v databázi ještě není, a u čerstvého závodu (do 30 dnů), dokud
  nemá oficiální čas (výsledky bývají v ORIS až pár dní po závodě);
- před každým dotazem 0,4 s pauza, účty jdou po jednom;
- účet načtený v posledních 20 hodinách (tlačítkem, nahráním exportu nebo předchozím během) se přeskočí.
  `--hours 0` načte všechny.

Když jeden účet selže (ORIS neodpovídá, číslo v ORIS není), vypíše se a ostatní pokračují. Nové oficiální
časy samy zařadí přepočet analýzy (běží v `worker`).

Ruční spuštění v Dockeru:

```sh
docker compose exec web flask --app webapp.wsgi sync-oris-all
```

## Zálohy (`flask backup`)

```sh
docker compose exec web flask --app webapp.wsgi backup            # do OB_BACKUP_DIR, jinak /data/backups
docker compose exec web flask --app webapp.wsgi backup --to /zalohy --keep 30
```

Jedna záloha jsou tři věci ve složce záloh:

| Co | Popis |
|---|---|
| `ob-RRRR-MM-DD_HHMM.db` | kopie databáze (vlastní záloha SQLite, správná i za běhu webu a workeru), zkontrolovaná `PRAGMA integrity_check` |
| `ob-RRRR-MM-DD_HHMM-soubory.txt` | seznam nahraných souborů, které nejdou znovu získat: `.fit`, mapy s tratí a bez tratě, fotky map, trať usazená z fotky, vlastní sklon z exportu Garmin (export se po načtení maže). U každého velikost a SHA-1. |
| `soubory/` | zrcadlo těch souborů. Kopíruje se jen nový nebo změněný soubor; soubor, který už žádná ponechaná záloha neuvádí, se smaže. |

Ponechá se posledních 14 záloh (`OB_BACKUP_KEEP`, nebo `--keep`). Analýzy, modely, výškopis a data z OSM se
nezálohují: appka je spočítá znovu.

Složka záloh má být mimo svazek s daty (jiný disk, jiný stroj). Ve službě `cron` níže je to složka `zalohy/`
vedle `docker-compose.yml`; tu stačí jednou za čas zkopírovat jinam (`rsync -a zalohy/ jiny-stroj:ob-zalohy/`).

## Obnova (`flask restore`)

1. Zastav web a worker: `docker compose stop web worker` (a `cron`, když běží).
2. Obnov databázi a soubory ze zálohy:

   ```sh
   docker compose run --rm -v "$PWD/zalohy:/zalohy" web \
       flask --app webapp.wsgi restore /zalohy/ob-2026-10-20_0430.db --yes
   ```

   Bez `--yes` příkaz jen řekne, co by přepsal. Soubory bere ze `soubory/` vedle zálohy (`--files` jinou
   složku). Na konci vypíše, kolik souborů vrátil a které v záloze chybí.
3. Spusť web a worker: `docker compose up -d`. Starší analýzy appka nabídne přepočítat (tlačítko u závodu).

Test `tests/test_backup.py` zálohuje účet se vším, co nejde znovu získat, obnoví ho do prázdné instance,
přihlásí se a závod vidí.

## Spouštění jednou denně

Stačí jedno z toho.

### Cron na hostiteli (doporučeno, když server cron má)

`crontab -e` uživatele, který smí spouštět Docker, a do něj (cesta k repozitáři podle serveru):

```cron
# OB tracker: ve 4:30 nové závody z ORIS, v 4:45 záloha
30 4 * * *  cd /srv/OB_tracker && docker compose exec -T web flask --app webapp.wsgi sync-oris-all >> /var/log/ob-tracker.log 2>&1
45 4 * * *  cd /srv/OB_tracker && docker compose exec -T web flask --app webapp.wsgi backup --to /data/backups >> /var/log/ob-tracker.log 2>&1
```

Zálohy jsou pak ve svazku `ob_data`; ven je dostane `docker compose cp web:/data/backups ./zalohy`, nebo místo
`--to /data/backups` připoj do služby `web` složku hostitele (jako ve službě `cron`).

### Služba `cron` v `docker-compose.yml` (server bez cronu)

Je ve výchozím stavu vypnutá (profil `cron`). Zapne se:

```sh
docker compose --profile cron up -d
```

Každý den v `OB_CRON_AT` (výchozí 04:30, čas Europe/Prague) načte závody z ORIS a udělá zálohu do složky
`zalohy/` vedle `docker-compose.yml`. Jednotlivé úlohy vypíná `OB_CRON_ORIS=0` a `OB_CRON_BACKUP=0`. Výpis:
`docker compose logs cron`. Jednou hned: `docker compose run --rm cron python -m webapp.cron --once`.

## Nastavení

| Proměnná | Výchozí | Co dělá |
|---|---|---|
| `OB_BACKUP_DIR` | `backups/` ve složce instance | kam `flask backup` a služba `cron` ukládají zálohy |
| `OB_BACKUP_KEEP` | 14 | kolik záloh ponechat |
| `OB_CRON_AT` | 04:30 | kdy služba `cron` pouští denní úlohy |
| `OB_CRON_TZ` | Europe/Prague | v jakém čase je `OB_CRON_AT` |
| `OB_CRON_ORIS` | 1 | 0 = služba `cron` nenačítá z ORIS |
| `OB_CRON_BACKUP` | 1 | 0 = služba `cron` nezálohuje |
