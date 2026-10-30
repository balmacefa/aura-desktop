<# Crea dist/Aura-<version>.zip (lista blanca) y dist/SHA256SUMS.txt #>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$m = Select-String -Path (Join-Path $root 'aura.py') -Pattern "^__version__\s*=\s*'([^']+)'" | Select-Object -First 1
if (-not $m) { throw 'No se encontró __version__ en aura.py' }
$ver = $m.Matches[0].Groups[1].Value
$dist = Join-Path $root 'dist'
$stageRoot = Join-Path $dist 'stage'
$stage = Join-Path $stageRoot "Aura-$ver"
if (Test-Path $stageRoot) { Remove-Item $stageRoot -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null

foreach ($f in 'aura.py','aura_ui.py','aura_log.py','LICENSE','README.md','CHANGELOG.md','install.ps1','uninstall.ps1') {
    Copy-Item (Join-Path $root $f) $stage
}
foreach ($d in 'desk','wall','docs') {
    $src = Join-Path $root $d; $dst = Join-Path $stage $d
    New-Item -ItemType Directory -Force $dst | Out-Null
    Get-ChildItem $src -Recurse -File -Force | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length + 1)
        if ($rel -match '(^|\\)(__pycache__|devtools)(\\|$)' -or $_.Name -eq 'custom.mp4' -or $_.Extension -eq '.pyc') { return }
        $target = Join-Path $dst $rel
        New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
        Copy-Item $_.FullName $target
    }
}
$zip = Join-Path $dist "Aura-$ver.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $stage -DestinationPath $zip
Remove-Item $stageRoot -Recurse -Force
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
Set-Content -Path (Join-Path $dist 'SHA256SUMS.txt') -Value "$hash  Aura-$ver.zip" -Encoding ascii
Write-Host "Creado $zip"
Write-Host "SHA256 $hash"
