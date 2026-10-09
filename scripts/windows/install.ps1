# Installs the inner/outer/inner CuraEngine + Cura plugin for UltiMaker Cura 5.13 on Windows.
# Close Cura first.  Run:  powershell -ExecutionPolicy Bypass -File install.ps1   (or double-click install.bat)
param(
    [switch]$Force,
    [string]$DataDir = (Join-Path $env:APPDATA 'cura\5.13'),
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'cura-inner-outer-inner')
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$cfg = Join-Path $DataDir 'cura.cfg'
if (-not (Test-Path $cfg)) {
    throw "$cfg not found. Start Cura 5.13 once so it creates its settings, then run this again."
}
if (-not $Force -and (Get-Process -Name 'UltiMaker-Cura' -ErrorAction SilentlyContinue)) {
    throw 'Cura is running. Close it first (or use -Force).'
}
if (-not (Test-Path (Join-Path $here 'engine\CuraEngine.exe'))) { throw 'engine\CuraEngine.exe missing next to this script' }
if (-not (Test-Path (Join-Path $here 'plugin\InnerOuterInnerWalls\plugin.json'))) { throw 'plugin\ missing next to this script' }

Write-Host "Cura settings : $DataDir"
Write-Host "Engine install: $InstallDir"

# Install the engine first and check that it runs before touching any Cura settings.
if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $here 'engine\*') $InstallDir
$engine = Join-Path $InstallDir 'CuraEngine.exe'
$out = (& $engine help 2>&1 | Out-String)
if ($out -notmatch 'Cura_SteamEngine') {
    Remove-Item -Recurse -Force $InstallDir
    Write-Host $out
    throw 'the engine does not run on this system. Nothing was changed.'
}
Write-Host ("Engine check : OK (" + ($out -split "`n" | Where-Object { $_ -match 'Cura_SteamEngine' } | Select-Object -First 1).Trim() + ")")

# Plugin that adds the menu entry.
$plugins = Join-Path $DataDir 'plugins'
New-Item -ItemType Directory -Force -Path $plugins | Out-Null
$pluginDest = Join-Path $plugins 'InnerOuterInnerWalls'
if (Test-Path $pluginDest) { Remove-Item -Recurse -Force $pluginDest }
Copy-Item -Recurse -Force (Join-Path $here 'plugin\InnerOuterInnerWalls') $pluginDest

# Point Cura at the patched engine ([backend] location in cura.cfg).
$backup = "$cfg.bak-inner-outer-inner"
if (-not (Test-Path $backup)) { Copy-Item $cfg $backup }
$lines = [System.Collections.Generic.List[string]]::new()
$inBackend = $false; $seen = $false; $done = $false
foreach ($line in (Get-Content -LiteralPath $cfg)) {
    if ($line -match '^\[') {
        if ($inBackend -and -not $done) { $lines.Add("location = $engine"); $done = $true }
        $inBackend = ($line -eq '[backend]')
        if ($inBackend) { $seen = $true }
    }
    if ($inBackend -and $line -match '^location\s*=') {
        if (-not $done) { $lines.Add("location = $engine"); $done = $true }
        continue
    }
    $lines.Add($line)
}
if ($inBackend -and -not $done) { $lines.Add("location = $engine") }
if (-not $seen) { $lines.Add(''); $lines.Add('[backend]'); $lines.Add("location = $engine") }
[System.IO.File]::WriteAllLines($cfg, $lines, (New-Object System.Text.UTF8Encoding($false)))

Write-Host ''
Write-Host "Done. Start Cura, open Print Settings, search for 'Wall Ordering' and choose 'Inner/Outer/Inner'."
Write-Host 'To undo: run uninstall.ps1.'
