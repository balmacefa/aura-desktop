<# Desinstala Aura (revierte install.ps1). -KeepSettings conserva aura.json. #>
param(
    [string]$InstallDir = $PSScriptRoot,
    [switch]$KeepSettings,
    [switch]$NoShortcuts,
    [switch]$NoRegistry
)
$ErrorActionPreference = 'Continue'
$aura = Join-Path $InstallDir 'aura.py'
$py = (Get-Command python -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' } | Select-Object -First 1).Source
if ($py -and (Test-Path $aura)) {
    & $py $aura stop
    if (-not $NoShortcuts) { & $py $aura uninstall }
}
if (-not $NoRegistry) {
    Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Aura' -Recurse -Force -ErrorAction SilentlyContinue
    Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'Aura' -ErrorAction SilentlyContinue
}

# SEGURIDAD: solo se borran archivos de una carpeta que install.ps1 creó (marca .aura-installed). Ejecutarlo desde un repositorio o carpeta de
# desarrollo no borra nada.
$marker = Join-Path $InstallDir '.aura-installed'
if ((Test-Path $InstallDir) -and -not (Test-Path $marker)) {
    Write-Host "'$InstallDir' no es una instalación de Aura (falta .aura-installed): se quitaron accesos y registro, pero NO se borró ningún archivo." -ForegroundColor Yellow
}
elseif (Test-Path $InstallDir) {
    $self = $MyInvocation.MyCommand.Path
    $inside = $self -and $self.StartsWith($InstallDir.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)
    Get-ChildItem $InstallDir -Force |
        Where-Object { -not ($inside -and $_.FullName -eq $self) -and -not ($KeepSettings -and $_.Name -eq 'aura.json') } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    if ($inside) {
        $cmd = "Start-Sleep 2; Remove-Item -LiteralPath '$self' -Force -ErrorAction SilentlyContinue; if (-not (Get-ChildItem -LiteralPath '$InstallDir' -Force)) { Remove-Item -LiteralPath '$InstallDir' -Force }"
        Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-Command',$cmd
    } elseif (-not $KeepSettings) {
        Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host 'Aura desinstalado.' -ForegroundColor Green
