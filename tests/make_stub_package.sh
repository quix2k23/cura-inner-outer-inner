#!/bin/sh
# Builds a small fake package (a stand-in engine that only prints its banner) to test the install scripts without a real build.
#   tests/make_stub_package.sh <output folder>
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$1
rm -rf "$OUT"
mkdir -p "$OUT/engine/lib" "$OUT/plugin"
printf '#!/bin/sh\necho "Cura_SteamEngine version 5.13.0"\n' > "$OUT/engine/CuraEngine"
cp "$OUT/engine/CuraEngine" "$OUT/engine/CuraEngine.bin"
printf '# stub\ninner_outer_inner\narc_fitting\nbone_infill\n' > "$OUT/engine/FEATURES"
chmod +x "$OUT/engine/CuraEngine" "$OUT/engine/CuraEngine.bin"
cp -r "$ROOT/plugin/InnerOuterInnerWalls" "$OUT/plugin/"
cp "$ROOT/scripts/linux/install.sh" "$ROOT/scripts/linux/uninstall.sh" "$OUT/"
chmod +x "$OUT/install.sh" "$OUT/uninstall.sh"
