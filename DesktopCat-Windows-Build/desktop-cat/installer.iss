[Setup]
AppId={{8C23A3EC-10E1-47AF-A4D1-FC8D64BA326E}
AppName=DesktopCat
AppVersion=0.4.5
DefaultDirName={localappdata}\Programs\DesktopCat
DefaultGroupName=DesktopCat
PrivilegesRequired=lowest
OutputDir=installer-output
OutputBaseFilename=DesktopCat-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\cat.ico
UninstallDisplayIcon={app}\DesktopCat-v0.4.5.exe

[Files]
Source: "dist\DesktopCat-v0.4.5.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Icons]
Name: "{group}\DesktopCat"; Filename: "{app}\DesktopCat-v0.4.5.exe"
Name: "{autodesktop}\DesktopCat"; Filename: "{app}\DesktopCat-v0.4.5.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DesktopCat-v0.4.5.exe"; Description: "Launch DesktopCat"; Flags: nowait postinstall skipifsilent
