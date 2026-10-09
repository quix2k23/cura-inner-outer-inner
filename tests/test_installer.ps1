# Installs a package into throwaway Cura settings folders and checks install, a second install and uninstall.
#   powershell -File tests\test_installer.ps1 -Package <unpacked package folder>
# It never touches a real Cura: everything happens in a temporary folder.
param([Parameter(Mandatory)][string]$Package)
$ErrorActionPreference = 'Stop'
$pkg = (Resolve-Path $Package).Path
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("ioi-installer-test-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $work | Out-Null
$script:failed = $false

function Check($ok, $message) {
    if ($ok) { Write-Host "PASS $message" } else { Write-Host "FAIL $message"; $script:failed = $true }
}
# Compare the content, not the line endings (the scripts write Windows line endings), and ignore an empty [backend]
# header: Cura writes those itself, so one left behind by uninstall is harmless.
function Normalize($text) { return (($text -replace "`r`n", "`n") -replace "(?m)^\[backend\]\n(\n)?", "").Trim() }

function RunCase($name, $startingConfig) {
    $root = Join-Path $work $name
    $data = Join-Path $root 'cura\5.13'
    $install = Join-Path $root 'engine'
    New-Item -ItemType Directory -Force -Path $data | Out-Null
    $cfg = Join-Path $data 'cura.cfg'
    [System.IO.File]::WriteAllText($cfg, $startingConfig)
    $before = [System.IO.File]::ReadAllText($cfg)

    & "$pkg\install.ps1" -Force -DataDir $data -InstallDir $install | Out-Null
    & "$pkg\install.ps1" -Force -DataDir $data -InstallDir $install | Out-Null   # a second time
    $locations = @(Select-String -Path $cfg -Pattern '^location = ')
    Check ($locations.Count -eq 1 -and $locations[0].Line -eq "location = $install\CuraEngine.exe") "${name}: one location line pointing at the engine, also after installing twice"
    # Cura reads cura.cfg with Python's strict config parser, which refuses a file that has the same section twice.
    $sections = @(Get-Content $cfg | Where-Object { $_ -match '^\[.+\]\s*$' } | ForEach-Object { $_.Trim() })
    Check ($sections.Count -eq @($sections | Select-Object -Unique).Count) "${name}: cura.cfg has no duplicate sections"
    Check ((Test-Path (Join-Path $data 'plugins\InnerOuterInnerWalls\plugin.json')) -and (Test-Path (Join-Path $data 'plugins\InnerOuterInnerWalls\settings.def.json'))) "${name}: plugin files installed"
    Check ((Test-Path (Join-Path $install 'FEATURES')) -and (Test-Path (Join-Path $install 'CuraEngine.exe'))) "${name}: engine and FEATURES file installed"

    & "$pkg\uninstall.ps1" -DataDir $data -InstallDir $install | Out-Null
    Check ((Normalize ([System.IO.File]::ReadAllText($cfg))) -eq (Normalize $before)) "${name}: uninstall restores cura.cfg"
    Check (-not (Test-Path $install) -and -not (Test-Path (Join-Path $data 'plugins\InnerOuterInnerWalls'))) "${name}: uninstall removes the engine and the plugin"
}

RunCase 'empty_backend_section' "[general]`nversion = 6`n`n[backend]`n`n[mesh]`n"
RunCase 'no_backend_section' "[general]`nversion = 6`n`n[mesh]`n"
RunCase 'other_backend_keys' "[general]`nversion = 6`n`n[backend]`nsome_key = 1`n`n[mesh]`n"
RunCase 'windows_line_endings' "[general]`r`nversion = 6`r`n`r`n[backend]`r`n`r`n[mesh]`r`n"

Remove-Item -Recurse -Force $work
if ($script:failed) { Write-Host "FAILED"; exit 1 } else { Write-Host "ALL PASSED" }
