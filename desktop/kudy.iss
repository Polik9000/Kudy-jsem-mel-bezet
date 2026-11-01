; Inno Setup: the Windows installer from the folder PyInstaller made (dist\KudyJsemMelBezet).
;   iscc /DAppVersion=1.0.0 desktop\kudy.iss      ->  dist\KudyJsemMelBezet-windows-setup.exe
; Installs for the current user only (no administrator needed). The data folder
; (%LOCALAPPDATA%\KudyJsemMelBezet) is not touched by the installer or the uninstaller.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{20E0F14C-55F7-484E-827F-82CB30BCE8FF}
AppName=Kudy jsem měl běžet
AppVersion={#AppVersion}
AppPublisher=Tobiáš Otta
AppPublisherURL=https://github.com/Polik9000/Kudy-jsem-mel-bezet
DefaultDirName={localappdata}\Programs\KudyJsemMelBezet
DefaultGroupName=Kudy jsem měl běžet
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=KudyJsemMelBezet-windows-setup
SetupIconFile=..\build\icons\app.ico
UninstallDisplayIcon={app}\KudyJsemMelBezet.exe
LicenseFile=..\LICENSE
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "cs"; MessagesFile: "compiler:Languages\Czech.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\KudyJsemMelBezet\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Kudy jsem měl běžet"; Filename: "{app}\KudyJsemMelBezet.exe"
Name: "{autodesktop}\Kudy jsem měl běžet"; Filename: "{app}\KudyJsemMelBezet.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KudyJsemMelBezet.exe"; Description: "{cm:LaunchProgram,Kudy jsem měl běžet}"; Flags: nowait postinstall skipifsilent
