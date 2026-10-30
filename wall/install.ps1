# INSTALADOR DE AURAWALL: NO SE HA EJECUTADO. Ejecutarlo solo cuando quieras instalar.
# Qué hace: acceso directo en el menú Inicio y (opcional) arranque con Windows. Es reversible con -Uninstall.
# Uso: pwsh -File install.ps1 -Video C:\ruta\fondo.mp4 [-Autostart]    |    pwsh -File install.ps1 -Uninstall
param([string]$Video, [switch]$Autostart, [switch]$Uninstall)

$app   = Join-Path $PSScriptRoot 'aurawall.py'
$pyw   = (Get-Command pythonw).Source
$menu  = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$start = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$names = @('AuraWall.lnk')

function New-Lnk($path, $args_) {
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
  $s.TargetPath = $pyw; $s.Arguments = $args_; $s.WorkingDirectory = $PSScriptRoot; $s.Save()
}

if ($Uninstall) {
  & $pyw $app stop
  foreach ($d in $menu, $start) { Remove-Item (Join-Path $d 'AuraWall.lnk') -ErrorAction SilentlyContinue }
  "AuraWall desinstalado (los archivos de $PSScriptRoot se conservan)."; return
}
if (-not $Video -or -not (Test-Path $Video)) { throw 'Indica -Video con la ruta de un archivo de vídeo existente.' }
$a = "`"$app`" run `"$((Resolve-Path $Video).Path)`""
New-Lnk (Join-Path $menu 'AuraWall.lnk') $a
if ($Autostart) { New-Lnk (Join-Path $start 'AuraWall.lnk') $a }
"Instalado. Búscalo como 'AuraWall' en Inicio. Autostart: $Autostart"
