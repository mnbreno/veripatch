; VeriPatch Windows installer (Inno Setup 6)
; Build via scripts/build-windows-installer.ps1

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef StagingDir
  #define StagingDir "staging"
#endif

[Setup]
AppId={{A7B3C4D5-E6F7-4890-ABCD-EF1234567890}
AppName=VeriPatch
AppVersion={#AppVersion}
AppVerName=VeriPatch {#AppVersion}
DefaultDirName={autopf}\VeriPatch
DefaultGroupName=VeriPatch
OutputDir=..\..\artifacts
OutputBaseFilename=VeriPatch-{#AppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "{#StagingDir}\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs
Source: "{#StagingDir}\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs createallsubdirs
Source: "{#StagingDir}\VeriPatch.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\VeriPatch"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\VeriPatch.ps1"""; WorkingDir: "{app}"; Comment: "Official source system updates"
Name: "{autodesktop}\VeriPatch"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\VeriPatch.ps1"""; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\VeriPatch.ps1"""; Description: "Launch VeriPatch"; Flags: nowait postinstall skipifsilent
