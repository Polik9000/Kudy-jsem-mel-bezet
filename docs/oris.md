# ORIS: jak ho appka čte

ORIS (`https://oris.ceskyorientak.cz/API/`, JSON, bez klíče) je hlavní zdroj závodů, kategorií, startů, cílů
a mezičasů. Appka volá čtyři metody (`webapp/oris.py`), před každým dotazem počká `sync_oris.PAUSE_S`
(0,4 s) a co už má v databázi, se znovu neptá. ORIS má nezveřejněné limity dotazů; při zkoumání se odpovědi
ukládají do `kontrola/oris-cache/` (mimo git) a v testech se ORIS nevolá nikdy (falešný klient v `tests/`).

| Metoda | Co appka čte | Kdy |
|---|---|---|
| `getUser?rgnum=` | `ID` (ORIS ID osoby), `FirstName`, `LastName` | registrace, Profil, načtení závodů |
| `getUserEventEntries?userid=` | `EventID`, `ClassID`, `ClassDesc`, `EventDate`, `RegNo` | načtení závodů |
| `getEvent?id=` | název, datum, místo, disciplína, Livelox, místa, odkazy, kategorie, `Stages`, `Stage1..7`, `ParentID` | jen závod nový pro databázi |
| `getSplits?classid=` | řádek každého běžce kategorie (`RegNo`, časy, mezičasy) | jednou na kategorii (u čerstvého závodu, dokud nejsou výsledky) |

Ověřeno 8. a 9. 11. 2026 na odpovědích ORIS (uložené v `kontrola/oris/` a `kontrola/oris-cache/`).

## Přestup do jiného oddílu

Po přestupu dostane běžec nové registrační číslo (jiná tři písmena, někdy i jiné číslice):

| Běžec | Staré číslo | Nové číslo | ORIS ID |
|---|---|---|---|
| Jiří Vlach | AOV7900 (do 24. 1. 2025, 344 přihlášek) | SFM7900 (od 5. 2. 2025, 65 přihlášek) | 6521 pro obě |
| Matěj Toman | LBM0909 (do 1/2023), JMO0909 (hostování 2021–2023) | ZBM0919 (od 28. 1. 2023) | 14563 pro všechna tři |

- **`getUser` odpovídá jen na dnešní číslo.** Na staré číslo vrátí prázdno (AOV7900, LBM0909).
- **ORIS ID osoby zůstává stejné.** `getUserEventEntries` pod tím ID vrátí přihlášky ze všech oddílů a každá
  nese číslo, pod kterým byla (`RegNo`).
- **Výsledky a mezičasy starých závodů mají staré číslo** (`RegNo` v `getSplits`, v uložených výsledcích appky
  AOV7900 v roce 2024, SFM7900 od roku 2025).

Co z toho appka dělá (`webapp/services/regnos.py`, tabulka `user_regnos`):

- Účet má seznam čísel. První číslo účtu (`users.oris_regno`) zůstává napořád; triggery ho kopírují do seznamu.
- Při načtení z ORIS se ptá na každé číslo; staré číslo, které ORIS už nezná, nevadí, ID zná appka z dřívějška.
  Účet založený se starým číslem tak po přestupu funguje dál.
- Čísla z vlastních přihlášek pod stejným ORIS ID appka sama připíše (`source = 'oris'`), když nepatří jinému účtu.
  Účet s novým číslem tak najde oficiální čas a mezičasy i u starých závodů.
- V lokální appce jde číslo přidat v Profilu („Přestoupil jsem do jiného oddílu…“). Dnešní číslo se ověří
  `getUser` (stejné ORIS ID, nebo stejné jméno); staré číslo se hledá v přihláškách běžce. Smazat jde jen ručně
  přidané číslo, pod kterým není žádný závod. Na serveru se čísla ručně nepřidávají.
- Přihlásit se jde kterýmkoli číslem účtu.

## Etapový závod

Příklady: 5EOB Tis 2022 (6778), Grand prix Silesia 2025 (8702), Bohemia orienteering 2025 (8711).

| | Zastřešující závod | Etapa |
|---|---|---|
| `Stages` | počet etap (`"5"`) | `"0"` |
| `Stage1`…`Stage7` | ORIS ID etap, `"0"` = nic | `"0"` |
| `ParentID` | `null` | ID zastřešujícího závodu |
| `Discipline` | `ET`, „Etapový závod“ | vlastní: `MD` střední, `LD` dlouhá, `SP` sprint |
| `Level` | `ET`, „Etapový závod“ | `E`, „Jednotlivá etapa“ |
| název | „5EOB Tis“ | „5EOB Tis - E1“ |
| kategorie | stejné názvy jako v etapách, bez délky trati (`Distance 0.00`) | vlastní délka, převýšení, mezičasy |

- Přihláška se dělá na zastřešující závod. `getUserEventEntries` pak u Tobiase vrací **zastřešující závod i každou
  etapu zvlášť**, se stejným názvem kategorie (H14 na 5EOB, H16B na GP Silesia i Bohemia).
- Mapy, tratě a mezičasy patří etapám. Zastřešující závod nemá mapu ani mezičasy.

Co z toho appka dělá (`webapp/services/stages.py`, tabulka `oris_umbrellas`):

- Zastřešující závod se jako závod nezakládá; appka si jen zapamatuje jeho etapy (jedno `getEvent`).
- Přihláška na zastřešující závod se rozloží na etapy: kategorie stejného názvu v každé etapě. Etapa, kterou ORIS
  vypisuje zvlášť (nebo kterou běžec už má), se nezdvojí.
- Etapa ukazuje svoji disciplínu a „E1 / 5“.
- Zastřešující závod uložený starší verzí: přihláška bez běhu, poznámek, fotky a snímků se smaže; s během se
  přesune na etapu ze dne běhu (s mapami). Když to nejde, závod zůstane. Na Tobiasově databázi (kopie,
  9. 11. 2026) se všechny tři smazaly, 110 → 107 závodů, žádný nezůstal.
- Přidat závod z ORIS podle čísla zastřešujícího závodu nabídne výběr etapy.

## Vícezávod (`MultiEvents`)

Víkend dvou samostatných závodů se v ORIS propojuje polem `MultiEvent1` (a `ParentMultiID`), ne etapami. Tak je
popsaný **KITL 2025**: 8228 (střední trať, 6. 9. 2025) a 8229 (dlouhá trať, 7. 9. 2025), každý s vlastními
přihláškami, mapou a mezičasy. Etapový závod to není a appka ho nemění. `getEventList` pro 4.–7. 9. 2025 jiný KITL
neukáže (jen ještě Žebříček B-Čechy 8507, 8508).
