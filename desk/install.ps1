# Accesos de Aura en el menú Inicio (y, opcional, arranque de los widgets con Windows). Reversible con -Uninstall.
# Uso: pwsh -File install.ps1 [-Autostart]    |    pwsh -File install.ps1 -Uninstall
# No requiere permisos de administrador: solo escribe en el perfil del usuario.
param([switch]$Autostart, [switch]$Uninstall)

$root = Split-Path $PSScriptRoot -Parent
$pyw  = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
$menu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$boot = Join-Path $menu 'Startup'
$links = @(
  @{ Name = 'Aura';     Script = Join-Path $root 'aura_ui.py';           Dir = $root },       # panel de ajustes
  @{ Name = 'AuraDesk'; Script = Join-Path $root 'desk\auradesk.py';     Dir = Join-Path $root 'desk' }  # widgets
)

if ($Uninstall) {
  Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -match 'auradesk\.py|aura_ui\.py|aurawall\.py|live\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  foreach ($d in $menu, $boot) { foreach ($l in $links) { Remove-Item (Join-Path $d "$($l.Name).lnk") -ErrorAction SilentlyContinue } }
  "Aura desinstalada (accesos y procesos). Los archivos de $root se conservan."; return
}
if (-not $pyw) { Write-Error "No se encontró pythonw. Instala Python 3.10+ (winget install Python.Python.3.12)."; exit 1 }
function New-Lnk($path, $l) {
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
  $s.TargetPath = $pyw; $s.Arguments = "`"$($l.Script)`""; $s.WorkingDirectory = $l.Dir; $s.Save()
}
foreach ($l in $links) { New-Lnk (Join-Path $menu "$($l.Name).lnk") $l }
if ($Autostart) { New-Lnk (Join-Path $boot 'AuraDesk.lnk') $links[1] }
"Instalado. Busca 'Aura' (panel) y 'AuraDesk' (widgets) en Inicio. Autostart de widgets: $Autostart"
