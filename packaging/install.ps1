# NoPop installer – installs for the current user only, no admin rights needed.
$ErrorActionPreference = "Stop"
$de = (Get-UICulture).TwoLetterISOLanguageName -eq "de"
function T($deText, $enText) { if ($de) { $deText } else { $enText } }

$quelle = $PSScriptRoot
$ziel   = Join-Path $env:LOCALAPPDATA "Programs\NoPop"
$pyw    = Join-Path $ziel "pythonw.exe"
$skript = Join-Path $ziel "app\nopop.py"
$icon   = Join-Path $ziel "app\assets\nopop.ico"

Write-Host (T "NoPop wird installiert ..." "Installing NoPop ...")

# stop a running NoPop (only our own pythonw processes)
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*nopop.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Milliseconds 500

if ((Resolve-Path $quelle).Path -ne $ziel) {
    if (Test-Path $ziel) { Remove-Item $ziel -Recurse -Force }
    New-Item -ItemType Directory -Force $ziel | Out-Null
    Copy-Item (Join-Path $quelle "*") $ziel -Recurse -Force
}
Get-ChildItem $ziel -Recurse -File | Unblock-File

# Start menu shortcut
$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\NoPop.lnk"))
$lnk.TargetPath = $pyw
$lnk.Arguments = "`"$skript`""
$lnk.WorkingDirectory = Join-Path $ziel "app"
$lnk.IconLocation = "$icon,0"
$lnk.Description = (T "Hält die Lautsprecher wach, damit nichts ploppt" "Keeps your speakers awake so they don't pop")
$lnk.Save()

# entry in Settings > Apps (uninstall), current user only
$version = (Get-Content (Join-Path $ziel "app\VERSION") -Raw).Trim()
$u = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\NoPop"
New-Item $u -Force | Out-Null
Set-ItemProperty $u DisplayName "NoPop"
Set-ItemProperty $u DisplayVersion $version
Set-ItemProperty $u DisplayIcon $icon
Set-ItemProperty $u Publisher "NoPop"
Set-ItemProperty $u InstallLocation $ziel
Set-ItemProperty $u UninstallString "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ziel\uninstall.ps1`""
Set-ItemProperty $u NoModify 1 -Type DWord
Set-ItemProperty $u NoRepair 1 -Type DWord

# start (first start opens the window and turns on "start with Windows")
Start-Process $pyw -ArgumentList "`"$skript`"" -WorkingDirectory (Join-Path $ziel "app")
Write-Host (T "Fertig! NoPop läuft jetzt (Symbol unten rechts bei den ausgeblendeten Symbolen)." "Done! NoPop is running (icon in the system tray, under the ^ arrow).")
Start-Sleep 3
