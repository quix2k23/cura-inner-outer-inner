# Assembles the Windows add-on archive contents: package-windows.ps1 <path to built CuraEngine.exe> <output dir>
param([Parameter(Mandatory)][string]$Exe, [Parameter(Mandatory)][string]$Out)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$binDir = Split-Path -Parent (Resolve-Path $Exe)

if (Test-Path $Out) { Remove-Item -Recurse -Force $Out }
New-Item -ItemType Directory -Force -Path (Join-Path $Out 'engine'), (Join-Path $Out 'plugin') | Out-Null
Copy-Item $Exe (Join-Path $Out 'engine\CuraEngine.exe')
# DLLs Conan put next to the executable (Arcus, TBB, ...).
Copy-Item (Join-Path $binDir '*.dll') (Join-Path $Out 'engine') -ErrorAction SilentlyContinue
# Tells the Cura plugin which features this engine has, so that it only offers settings the engine understands.
Set-Content -Path (Join-Path $Out 'engine\FEATURES') -Value "# Features of this CuraEngine build, read by the Cura plugin.`ninner_outer_inner`narc_fitting`nbone_infill" -Encoding ascii
# The engine is installed outside Cura's own folder, so ship the Visual C++ runtime next to it (app-local deployment).
foreach ($name in 'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'concrt140.dll') {
    $source = Join-Path $env:windir "System32\$name"
    if ((Test-Path $source) -and -not (Test-Path (Join-Path $Out "engine\$name"))) { Copy-Item $source (Join-Path $Out 'engine') }
}
Copy-Item -Recurse (Join-Path $root 'plugin\InnerOuterInnerWalls') (Join-Path $Out 'plugin')
Copy-Item (Join-Path $root 'scripts\windows\*') $Out
Copy-Item (Join-Path $root 'README.md'), (Join-Path $root 'LICENSE') $Out
Get-ChildItem (Join-Path $Out 'engine') | Select-Object Name, Length | Format-Table | Out-String | Write-Host
