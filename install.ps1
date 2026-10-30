<# Instala Aura por usuario (sin administrador). #>
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Programs\Aura'),
    [switch]$Autostart,
    [switch]$NoShortcuts,
    [switch]$NoRegistry
)
$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot

function Get-Real($name) {
    Get-Command $name -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' } | Select-Object -First 1
}
$py = Get-Real 'python'
$pyw = Get-Real 'pythonw'
$ok = $false
if ($py -and $pyw) {
    & $py.Source -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
    $ok = ($LASTEXITCODE -eq 0)
}
if (-not $ok) {
    Write-Host 'Aura necesita Python 3.10+ con pythonw y tkinter.' -ForegroundColor Red
    Write-Host 'Instalalo con:  winget install Python.Python.3.12   (y abre una consola nueva)'
    exit 1
}
$py = $py.Source

Write-Host "Instalando en $InstallDir"
New-Item -ItemType Directory -Force $InstallDir | Out-Null
$same = ((Resolve-Path $InstallDir).Path.TrimEnd('\') -ieq $src.TrimEnd('\'))
if (-not $same) {
    Get-ChildItem $src -Force | Where-Object { $_.Name -notin 'aura.json','dist','.git','__pycache__' } | ForEach-Object {
        Copy-Item $_.FullName $InstallDir -Recurse -Force
    }
}

Set-Content -LiteralPath (Join-Path $InstallDir '.aura-installed') -Value (Get-Date -Format o) -Encoding ASCII   # marca: uninstall.ps1 solo borra carpetas con ella
Push-Location $InstallDir
try {
    & $py aura.py doctor
    if ($LASTEXITCODE -ne 0) { Write-Warning 'doctor indica requisitos sin cumplir; revisa la salida anterior.' }
    if (-not $NoShortcuts) { & $py aura.py install }
} finally { Pop-Location }

if ($Autostart) {
    $run = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    $cmd = '"{0}" "{1}" start' -f $pyw.Source, (Join-Path $InstallDir 'aura.py')
    Set-ItemProperty -Path $run -Name 'Aura' -Value $cmd
}

if (-not $NoRegistry) {
    $ver = (& $py (Join-Path $InstallDir 'aura.py') version | Select-Object -First 1).Trim()
    $k = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Aura'
    New-Item -Path $k -Force | Out-Null
    $un = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f (Join-Path $InstallDir 'uninstall.ps1')
    Set-ItemProperty $k DisplayName 'Aura'
    Set-ItemProperty $k DisplayVersion $ver
    Set-ItemProperty $k Publisher 'balmacefa'
    Set-ItemProperty $k InstallLocation $InstallDir
    Set-ItemProperty $k UninstallString $un
    Set-ItemProperty $k NoModify 1 -Type DWord
    Set-ItemProperty $k NoRepair 1 -Type DWord
}
Write-Host "Aura instalado. Abrelo con:  python `"$InstallDir\aura.py`" ui" -ForegroundColor Green
