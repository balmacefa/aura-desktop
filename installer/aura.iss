; Instalador de Aura (Inno Setup 6). Se construye con `python scripts/build.py` (o a mano: ISCC /DAppVersion=2.0.0 installer\aura.iss).
; Por usuario (sin permisos de administrador), en inglés y español, sin acciones sorpresa: siguiente → instalar → listo.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Aura"
#define Repo "https://github.com/balmacefa/aura-desktop"

[Setup]
AppId={{6B1D3F52-8C4E-4E0B-9A57-2D7C41E5A9F3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=balmacefa
AppPublisherURL={#Repo}
AppSupportURL={#Repo}/issues
AppUpdatesURL={#Repo}/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Aura-Setup-{#AppVersion}
SetupIconFile=..\src\aura\assets\icons\aura.ico
UninstallDisplayIcon={app}\Aura.exe
UninstallDisplayName={#AppName}
LicenseFile=..\LICENSE
WizardStyle=modern
WizardImageFile=..\branding\installer\wizard.bmp
WizardSmallImageFile=..\branding\installer\small.bmp
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no
UsePreviousLanguage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
english.AutoStart=Start Aura with Windows
spanish.AutoStart=Iniciar Aura con Windows
english.LaunchAura=Open Aura
spanish.LaunchAura=Abrir Aura
english.KeepData=Do you want to delete your Aura settings and added videos too?%n%nChoose No to keep them in case you reinstall.
spanish.KeepData=¿Quieres borrar también tus ajustes y vídeos añadidos de Aura?%n%nElige No para conservarlos por si vuelves a instalar.

[Tasks]
Name: "autostart"; Description: "{cm:AutoStart}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Aura\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Aura.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Aura.exe"; Tasks: desktopicon

[Registry]
; Iniciar con Windows: entrada del usuario (se borra al desinstalar). Aura la puede cambiar desde Ajustes > General.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Aura"; ValueData: """{app}\Aura.exe"" --background"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Instalación normal: ofrece abrir Aura (la primera vez muestra la bienvenida). Actualización silenciosa: vuelve a arrancar en segundo plano.
Filename: "{app}\Aura.exe"; Description: "{cm:LaunchAura}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\Aura.exe"; Parameters: "--background"; Flags: nowait skipifnotsilent

[UninstallRun]
Filename: "{app}\Aura.exe"; Parameters: "quit"; Flags: runhidden; RunOnceId: "QuitAura"

[Code]
procedure QuitAura();
var Code: Integer;
begin
  { Cierra Aura (icono, ajustes, widgets y fondo) antes de sustituir archivos. }
  if FileExists(ExpandConstant('{app}\Aura.exe')) then
    Exec(ExpandConstant('{app}\Aura.exe'), 'quit', '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  QuitAura();
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if not UninstallSilent then
      if MsgBox(CustomMessage('KeepData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(ExpandConstant('{localappdata}\Aura'), True, True, True);
end;
