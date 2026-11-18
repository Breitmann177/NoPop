; NoPop Setup – one double-click, no admin rights.
; Build: python packaging/build.py, then  iscc /DVersion=x.y.z packaging\nopop.iss
#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppId=NoPop
AppName=NoPop
AppVersion={#Version}
AppPublisher=NoPop
AppPublisherURL=https://github.com/Breitmann177/NoPop
DefaultDirName={localappdata}\Programs\NoPop
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableWelcomePage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=NoPop-Setup
SetupIconFile=..\assets\nopop.ico
UninstallDisplayIcon={app}\app\assets\nopop.ico
UninstallDisplayName=NoPop
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "..\dist\NoPop\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: "Install.cmd,install.ps1"

[Icons]
Name: "{userprograms}\NoPop"; Filename: "{app}\pythonw.exe"; Parameters: """{app}\app\nopop.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\assets\nopop.ico"

[Registry]
; entry of the old script installer (replaced by this setup)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\NoPop"; Flags: deletekey

[Run]
Filename: "{app}\pythonw.exe"; Parameters: """{app}\app\nopop.py"""; WorkingDir: "{app}\app"; Flags: nowait postinstall

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/Delete /TN NoPop /F"; Flags: runhidden; RunOnceId: "Autostart"
Filename: "reg.exe"; Parameters: "delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v NoPop /f"; Flags: runhidden; RunOnceId: "RunKey"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\NoPop"
Type: filesandordirs; Name: "{app}"

[Code]
procedure StopNoPop();
var R: Integer;
begin
  Exec('powershell.exe', '-NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name=''pythonw.exe''\" | Where-Object { $_.CommandLine -like ''*nopop.py*'' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"',
       '', SW_HIDE, ewWaitUntilTerminated, R);
  Sleep(500);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopNoPop();
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then StopNoPop();
end;
