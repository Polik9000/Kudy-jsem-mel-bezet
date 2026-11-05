# MSIX a Microsoft Store

Workflow `.github/workflows/instalatory.yml` nově vedle stávajícího EXE a DMG sestavuje také
nepodepsaný x64 balíček `KudyJsemMelBezet.msix`. MSIX je zabalený z existujícího výstupu PyInstaller
(`dist/KudyJsemMelBezet`); nejde o novou implementaci aplikace. Balíček používá
`runFullTrust`, protože aplikace spouští lokální Flask server, výpočetní podprocesy a pracuje se soubory.

## Publisher identity – nutné před Store submission

Manifest má Publisher identity. Pro CI sestavení bez nakonfigurovaného tajemství se používá
`CN=KudyJsemMelBezet.TestOnly`. Takový balíček je pouze pro kontrolu sestavení a **nelze jej odeslat
do Microsoft Store**.

V GitHub repozitáři nastav secret `MSIX_PUBLISHER` na přesnou hodnotu **Publisher** z
Partner Center → Settings → Account settings → Identity details. Hodnota musí přesně odpovídat
identitě přiřazené aplikaci v Partner Center. Po nastavení secretu vytvoří další běh workflow balíček
s touto identitou. Před podáním zkontroluj také rezervované Package/Identity Name a verzi v Partner Center.

Balíček se záměrně nepodepisuje vlastním certifikátem. Odeslání do Store, validace a podpis distribučního
balíčku jsou samostatný krok v Partner Center; tento PR nic do Store neposílá a nic nevydává.

## Sestavení lokálně

Na Windows s Pythonem 3.12, Pillow a Windows 10/11 SDK:

```powershell
python desktop/icons.py build/icons
python desktop/msix/build_msix.py --source dist/KudyJsemMelBezet --output dist/KudyJsemMelBezet.msix --version 0.1.0 --publisher "CN=HODNOTA_Z_PARTNER_CENTER"
```

Předtím je nutné vytvořit PyInstaller výstup jako u běžného instalátoru. Bez parametru
`--publisher` skript použije testovací identitu.

## Data a upgrade

Desktopová aplikace aktuálně používá `%LOCALAPPDATA%\KudyJsemMelBezet`; Inno Setup při odinstalaci
tuto složku nemaže. MSIX má vlastní správu balíčku a jeho datového prostoru. Tento PR proto **netvrdí,
že přechod z EXE instalace automaticky migruje existující data**.

Před běžným používáním MSIX je nutné na testovacím Windows účtu ověřit:
1. Zálohovat celou složku `%LOCALAPPDATA%\KudyJsemMelBezet` (zejména `app.db`, uploads a cache).
2. Nainstalovat MSIX vedle/po testovací kopii stávající instalace a ověřit, odkud aplikace čte a zapisuje data.
3. Ověřit vytvoření závodu, nahrání KMZ a FIT, dokončení analýzy a restart aplikace.
4. Ověřit aktualizaci MSIX na vyšší verzi a odinstalaci/reinstalaci; zkontrolovat, že data zůstala dostupná.
5. Teprve poté rozhodnout, zda je potřeba explicitní migrace ze staré složky.

EXE/Inno Setup a macOS DMG zůstávají beze změny.
