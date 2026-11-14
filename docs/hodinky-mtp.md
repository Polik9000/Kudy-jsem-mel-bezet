# Hodinky přes USB: disk a MTP

Issue #39. Stav k 14. 11. 2026.

## Jak se hodinky Garmin připojují

- **Režim Garmin** (velkokapacitní úložiště, disk). Hodinky se ukážou jako disk: ve Windows s písmenem, na Macu
  v `/Volumes/GARMIN`, na Linuxu v `/media/...`. Běhy jsou v `GARMIN/Activity/*.fit`. Tohle appka umí
  (`webapp/services/watch.py`).
- **MTP** (Media Transfer Protocol, jako telefon). Hodinky nejsou disk, jen „zařízení“. Mnoho novějších modelů jiný
  režim nemá. Appka MTP nečte.

Fēnix 5X Plus má oba režimy: na hodinkách **Nastavení → Systém → Režim USB → Garmin** (anglicky Settings → System →
USB Mode → Garmin). Pak kabel odpojit a znovu připojit.

## Co appka dělá od tohoto PR

- Na **Přehledu závodů** a v **Nahrát běhy** (jen lokální appka) se po zobrazení stránky `ob.js` zeptá na
  `/upload/hodinky/nove.json`. Server se v samostatném vlákně podívá na připojené hodinky (`watch.look_now`), čeká
  nejvýš 2 s a výsledek drží 60 s. Když to trvá déle (disk bez karty, odpojený síťový disk), stránka se zeptá znovu
  (nejvýš 4×).
- Co je který soubor (`sha1`, jestli je to aktivita), si appka pamatuje podle cesty, velikosti a času změny, dokud
  běží. Hodinky se stovkami běhů se tak čtou jednou.
- Když hodinky mají běhy, které v appce nejsou, ukáže se řádek „Našly se nové aktivity z hodinek (N). Načíst…“
  s odkazem na stránku hodinek, kde jsou nové běhy předvybrané. Načítá se až tam, tlačítkem.
- **Teď ne** schová běhy, které hodinky mají teď (tabulka `watch_seen`). Běhy nezaškrtnuté na stránce hodinek se
  berou stejně. Nový běh na hodinkách se nabídne znovu.
- Bez hodinek se nic neukáže.

## MTP: co by šlo bez nových závislostí

| Systém | Možnost | Proč ne teď |
|---|---|---|
| Windows | Shell COM (`Shell.Application`, složka „Tento počítač“) přes `pywin32`/`pythoncom`. | `pywin32` v sestavení není (`requirements.txt`, `desktop/`). Byla by to nová knihovna (licence PSF, ~10 MB). |
| Windows | Stejný Shell COM přes PowerShell (`powershell -Command`, je v každých Windows), kopírování `CopyHere` do dočasné složky. | Bez nové knihovny, ale `CopyHere` je asynchronní, u MTP může ukázat okno a nehlásí konec ani chybu. Nemám na čem to ověřit. Spolehlivé to není. |
| Windows | Windows Portable Devices API přes `ctypes` (COM rozhraní `IPortableDevice`). | Desítky rozhraní a GUID ručně, bez testu na skutečných hodinkách. Velké riziko, malý užitek. |
| macOS | Nic vestavěného. MTP umí jen další programy (Android File Transfer, OpenMTP, `libmtp`). | Nová závislost s jinou licencí (`libmtp` LGPL 2.1) a balení do `.app`. Garmin Express hodinky zabere. |
| Linux | `gvfs`/`jmtpfs` připojí MTP jako složku (`/run/user/*/gvfs/mtp:*`). | Lokální appka se na Linux nebalí. Složku jde zadat ručně. |

**Rozhodnutí:** MTP se nečte. Rozšířená je nápověda (`watch.html`, `help.html`): přepnout na režim Garmin, na
Windows zkopírovat `GARMIN\Activity` z Průzkumníka do složky a tu zadat, jinak Garmin Connect (klíč, nebo export).
Ruční nahrání `.fit` a zipu zůstává.

Když by bylo potřeba MTP na Windows, první na řadě je PowerShell varianta, a to jen po testu na skutečných hodinkách
(otázka 63 v `co-zbyva.md`). Nová knihovna by šla do `docs/zavislosti.md` s licencí.

## Čemu se vyhnout

- Garmin Express a Android File Transfer si hodinky po připojení zaberou. Zavřít je.
- Hodinky v režimu Garmin před odpojením bezpečně odebrat (Windows: ikona USB, Mac: vysunout disk).
- Na hodinkách nic nemazat ani nepřesouvat. Appka soubory jen čte.
