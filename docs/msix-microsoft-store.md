# MSIX a Microsoft Store

Zásady ochrany osobních údajů pro Store listing: [Privacy Policy (CZ/EN)](privacy.html). Po sloučení tohoto PR a nasazení GitHub Pages bude veřejná adresa:
`https://polik9000.github.io/Kudy-jsem-mel-bezet/privacy.html`.

Workflow `.github/workflows/instalatory.yml` nově vedle stávajícího EXE a DMG sestavuje dva x64 MSIX artefakty:
- `windows-msix-store-package`: nepodepsaný `KudyJsemMelBezet.msix`, připravený pro další krok publikování v Partner Center;
- `windows-msix-test-package`: podepsaný `KudyJsemMelBezet-test.msix`, veřejný testovací certifikát `.cer` a návod `README.txt`. Ten lze stáhnout z konkrétního běhu GitHub Actions, přidat certifikát do důvěryhodných certifikátů aktuálního uživatele a nainstalovat.

Oba balíčky vycházejí ze stejného výstupu PyInstaller (`dist/KudyJsemMelBezet`); nejde o novou implementaci aplikace. Testovací podpis je vytvořený při každém CI běhu novým dočasným certifikátem. Soukromý klíč (.pfx) se do artefaktu nikdy nepřidává a po podpisu se z CI runneru odstraní. Proto je potřeba vždy použít .cer stažený společně s konkrétním MSIX. Balíček používá
`runFullTrust`, protože aplikace spouští lokální Flask server, výpočetní podprocesy a pracuje se soubory.

## Publisher identity – nutné před Store submission

Manifest má Publisher identity. Pro CI sestavení bez nakonfigurovaného tajemství se používá
`CN=KudyJsemMelBezet.TestOnly` a `KudyJsemMelBezet.TestOnly`. Takový balíček je pouze pro kontrolu sestavení a **nelze jej odeslat
do Microsoft Store**.

V GitHub repozitáři nastav secrets `MSIX_PUBLISHER` a `MSIX_IDENTITY_NAME` na přesné hodnoty **Publisher** a **Package/Identity Name** z
Partner Center → Settings → Account settings → Identity details. Hodnota musí přesně odpovídat
identitě přiřazené aplikaci v Partner Center. Po nastavení obou secrets vytvoří další běh workflow balíček
s touto identitou. Před podáním zkontroluj také rezervované Package/Identity Name a verzi v Partner Center.

Store artefakt se záměrně nepodepisuje vlastním certifikátem. Odeslání do Store, validace a podpis distribučního
balíčku jsou samostatný krok v Partner Center; tento PR nic do Store neposílá a nic nevydává.

## Stažení a instalace testovací verze

1. Otevři [Pull Request #30](https://github.com/Polik9000/Kudy-jsem-mel-bezet/pull/30), v části **Checks** otevři úspěšný běh workflow **Instalátory** a stáhni artefakt `windows-msix-test-package`.
2. Rozbal ZIP. V něm jsou pouze `KudyJsemMelBezet-test.msix`, odpovídající veřejný certifikát `KudyJsemMelBezet-test.cer` a `README.txt`.
3. V PowerShellu otevřeném v této složce spusť:
   ```powershell
   Import-Certificate -FilePath .\KudyJsemMelBezet-test.cer -CertStoreLocation Cert:\CurrentUser\TrustedPeople
   Add-AppxPackage -Path .\KudyJsemMelBezet-test.msix
   ```
4. Aplikaci spusť z nabídky Start. Případně lze po importu certifikátu otevřít MSIX dvojklikem.

Certifikát je self-signed a je určený pouze pro tento test. Importuj ho pouze z artefaktu staženého z tohoto důvěryhodného repozitáře. Smart App Control nebo firemní zásady Windows mohou i tak instalaci nepovolit; kvůli testu nevypínej bezpečnostní ochrany. Při potížích pošli přesné znění chyby.

Testovací certifikát se při každém běhu Actions mění. Nový testovací balíček proto vyžaduje i nový soubor `.cer`. Testovací balíček používá stejnou Publisher/Identity konfiguraci jako Store balíček daného běhu. Pokud v repozitáři nejsou nastavené secrets `MSIX_PUBLISHER` a `MSIX_IDENTITY_NAME`, používá se výchozí identita `KudyJsemMelBezet.TestOnly`; takový build netestuje budoucí Store identitu. Pro skutečný test stejné identity nastav obě hodnoty podle Partner Center.

## Sestavení lokálně

Na Windows s Pythonem 3.12, Pillow a Windows 10/11 SDK:

```powershell
python desktop/icons.py build/icons
python desktop/msix/build_msix.py --source dist/KudyJsemMelBezet --output dist/KudyJsemMelBezet.msix --version 0.1.0 --publisher "CN=HODNOTA_Z_PARTNER_CENTER" --identity-name "PACKAGE_IDENTITY_NAME"
```

Předtím je nutné vytvořit PyInstaller výstup jako u běžného instalátoru. Bez parametrů `--publisher` a `--identity-name` skript použije testovací identity.



## Smart App Control (SAC)

Testovací .cer je self-signed. Jeho import do `LocalMachine\\TrustedPeople` může vyřešit důvěru App Installeru při instalaci, ale **neznamená, že Smart App Control aplikaci povolí spustit**. SAC posuzuje spouštěný kód a podle dokumentace Microsoftu, pokud cloudová služba nedokáže aplikaci vyhodnotit jako bezpečnou, vyžaduje podpis certifikátem vydaným CA v Microsoft Trusted Root Programu. Náš dočasný self-signed certifikát tuto podmínku nesplňuje; aplikace může být i po instalaci zablokována. MSIX není obcházení SAC.

Kvůli testu SAC nevypínej. Pokud je SAC zapnutý a aplikaci zablokuje, je to očekávané omezení testovacího podpisu, ne důkaz, že Store varianta bude také blokována. Microsoft Store po certifikaci balíček automaticky znovu podepíše svým certifikátem; pro přímou distribuci mimo Store by byl potřeba odpovídající podpis od důvěryhodné CA.

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
