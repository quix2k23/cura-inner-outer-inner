# Removes the inner/outer/inner CuraEngine + plugin and points Cura back at its own engine. Close Cura first.
param(
    [string]$DataDir = (Join-Path $env:APPDATA 'cura\5.13'),
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'cura-inner-outer-inner')
)
$ErrorActionPreference = 'Stop'
$cfg = Join-Path $DataDir 'cura.cfg'
if (Test-Path $cfg) {
    # Drop only our location line from [backend]; leave everything else as it is.
    $lines = [System.Collections.Generic.List[string]]::new()
    $inBackend = $false
    foreach ($line in (Get-Content -LiteralPath $cfg)) {
        if ($line -match '^\[') { $inBackend = ($line -eq '[backend]') }
        if ($inBackend -and $line -match '^location\s*=' -and $line.Contains($InstallDir)) { continue }
        $lines.Add($line)
    }
    [System.IO.File]::WriteAllLines($cfg, $lines, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host 'Cura now uses its own engine again.'
}
foreach ($path in @((Join-Path $DataDir 'plugins\InnerOuterInnerWalls'), $InstallDir)) {
    if (Test-Path $path) { Remove-Item -Recurse -Force $path }
}
Write-Host "Removed the plugin and $InstallDir."
Write-Host 'If a print profile still says Inner/Outer/Inner, change Wall Ordering back before slicing.'
