# INSTALADOR DE AURADESK: NO SE HA EJECUTADO. Ejecutarlo solo cuando quieras instalar.
# Crea un acceso directo en el menú Inicio y (opcional) arranque con Windows. Reversible con -Uninstall.
# Uso: pwsh -File install.ps1 [-Autostart]    |    pwsh -File install.ps1 -Uninstall
param([switch]$Autostart, [switch]$Uninstall)

$app  = Join-Path $PSScriptRoot 'auradesk.py'
$pyw  = (Get-Command pythonw).Source
$menu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$boot = Join-Path $menu 'Startup'

if ($Uninstall) {
  Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object CommandLine -match 'auradesk\.py' |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  foreach ($d in $menu, $boot) { Remove-Item (Join-Path $d 'AuraDesk.lnk') -ErrorAction SilentlyContinue }
  "AuraDesk desinstalado (los archivos de $PSScriptRoot se conservan)."; return
}
function New-Lnk($path) {
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
  $s.TargetPath = $pyw; $s.Arguments = "`"$app`""; $s.WorkingDirectory = $PSScriptRoot; $s.Save()
}
New-Lnk (Join-Path $menu 'AuraDesk.lnk')
if ($Autostart) { New-Lnk (Join-Path $boot 'AuraDesk.lnk') }
"Instalado. Búscalo como 'AuraDesk' en Inicio. Autostart: $Autostart"
