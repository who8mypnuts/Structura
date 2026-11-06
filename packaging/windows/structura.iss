; Inno Setup 6 script: wraps dist\Structura (from packaging\build.py) into an installer.
; Sign with: iscc /Ssigntool="signtool sign /a /fd sha256 /tr http://timestamp.digicert.com /td sha256 $f" structura.iss
#define AppVersion "0.1.0"

[Setup]
AppId={{7C1B2F6E-4C8B-4E7E-9E54-1F0A4D8B2A11}
AppName=Structura
AppVersion={#AppVersion}
AppPublisher=The Structura Authors
DefaultDirName={autopf}\Structura
DefaultGroupName=Structura
OutputDir=..\..\dist
OutputBaseFilename=Structura-Setup-{#AppVersion}
SetupIconFile=..\..\src\structura\resources\brand\structura.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
LicenseFile=..\..\LICENSE

[Files]
Source: "..\..\dist\Structura\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Structura"; Filename: "{app}\Structura.exe"
Name: "{autodesktop}\Structura"; Filename: "{app}\Structura.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Registry]
Root: HKA; Subkey: "Software\Classes\.es"; ValueType: string; ValueData: "Structura.Script"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.structura"; ValueType: string; ValueData: "Structura.Project"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Structura.Script\shell\open\command"; ValueType: string; ValueData: """{app}\Structura.exe"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Structura.Project\shell\open\command"; ValueType: string; ValueData: """{app}\Structura.exe"" ""%1"""

[Run]
; compile the kernels once, for the installing user (later users compile at first start in the background)
Filename: "{app}\structura.exe"; Parameters: "warmup"; StatusMsg: "Preparing render kernels..."; Flags: runhidden
Filename: "{app}\Structura.exe"; Description: "Start Structura"; Flags: nowait postinstall skipifsilent
