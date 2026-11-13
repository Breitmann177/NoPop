# NoPop uninstaller – removes everything NoPop created.
$de = (Get-UICulture).TwoLetterISOLanguageName -eq "de"
function T($deText, $enText) { if ($de) { $deText } else { $enText } }
$ziel = Join-Path $env:LOCALAPPDATA "Programs\NoPop"

Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*nopop.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Milliseconds 500

schtasks /Delete /TN NoPop /F 2>$null | Out-Null                       # autostart
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name NoPop -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\NoPop.lnk") -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\NoPop" -Recurse -ErrorAction SilentlyContinue
# settings (retry briefly: Windows may still hold the sound file for a moment)
$einst = Join-Path $env:APPDATA "NoPop"
for ($i = 0; $i -lt 10 -and (Test-Path $einst); $i++) {
    Remove-Item $einst -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $einst) { Start-Sleep -Milliseconds 500 }
}
# the program folder is deleted after this script has ended
Start-Process cmd.exe -ArgumentList "/c timeout /t 2 >nul & rmdir /s /q `"$ziel`"" -WindowStyle Hidden
Write-Host (T "NoPop wurde entfernt." "NoPop has been removed.")
Start-Sleep 2
