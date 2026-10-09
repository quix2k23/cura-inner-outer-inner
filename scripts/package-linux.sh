#!/bin/sh
# Assembles the Linux add-on archive contents: package-linux.sh <path to built CuraEngine> <output dir>
set -eu
BIN=$1
OUT=$2
ROOT=$(cd "$(dirname "$0")/.." && pwd)

rm -rf "$OUT"
mkdir -p "$OUT/engine/lib" "$OUT/plugin"
cp "$BIN" "$OUT/engine/CuraEngine.bin"

# Bundle the shared libraries Conan built (Arcus, TBB), so the engine does not depend on Cura's own library path.
ldd "$BIN" | awk '/\.conan2/ { print $3 }' | sort -u | while read -r lib; do cp -L "$lib" "$OUT/engine/lib/"; done
patchelf --set-rpath '$ORIGIN/lib' --force-rpath "$OUT/engine/CuraEngine.bin"

# The launcher replaces Cura's library path so the engine only sees the system runtime plus ./lib.
cat > "$OUT/engine/CuraEngine" <<'WRAP'
#!/bin/sh
DIR=$(dirname "$(readlink -f "$0")")
export LD_LIBRARY_PATH="$DIR/lib"
exec "$DIR/CuraEngine.bin" "$@"
WRAP
chmod +x "$OUT/engine/CuraEngine" "$OUT/engine/CuraEngine.bin"

cp -r "$ROOT/plugin/InnerOuterInnerWalls" "$OUT/plugin/"
cp "$ROOT/scripts/linux/install.sh" "$ROOT/scripts/linux/uninstall.sh" "$ROOT/README.md" "$ROOT/LICENSE" "$OUT/"
chmod +x "$OUT/install.sh" "$OUT/uninstall.sh"
