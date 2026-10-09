#!/bin/sh
# Assembles the Linux add-on archive contents: package-linux.sh <path to built CuraEngine> <output dir>
set -eu
BIN=$1
OUT=$2
ROOT=$(cd "$(dirname "$0")/.." && pwd)

rm -rf "$OUT"
mkdir -p "$OUT/engine/lib" "$OUT/plugin"
cp "$BIN" "$OUT/engine/CuraEngine.bin"

# Bundle the shared libraries the engine needs that the system does not provide: the ones Conan built (Arcus, TBB, ...)
# and GCC's C++ runtime. ldd needs the Conan library folders on its search path to resolve them, like a normal run would.
CONAN_LIBS=$(find "${CONAN_HOME:-$HOME/.conan2}/p" -name '*.so*' -printf '%h\n' 2>/dev/null | sort -u | paste -sd: -)
export LD_LIBRARY_PATH="$CONAN_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "ldd of the built engine:"
ldd "$BIN"
if ldd "$BIN" | grep -q "not found"; then echo "error: some libraries could not be resolved" >&2; exit 1; fi
ldd "$BIN" | awk '/=> \// { print $3 }' | sort -u | while read -r lib; do
    case "$lib" in
        /lib/*|/lib64/*|/usr/lib/*|/usr/lib64/*)
            case "$(basename "$lib")" in
                libstdc++.so.6*|libgcc_s.so.1) ;;
                *) continue ;;
            esac ;;
    esac
    cp -L "$lib" "$OUT/engine/lib/"
done
patchelf --set-rpath '$ORIGIN/lib' --force-rpath "$OUT/engine/CuraEngine.bin"

# Check in a clean environment that the packaged engine resolves every library on its own.
echo "Bundled libraries:"; ls "$OUT/engine/lib"
if env -i LD_LIBRARY_PATH="$OUT/engine/lib" ldd "$OUT/engine/CuraEngine.bin" | grep "not found"; then
    echo "error: the packaged engine is missing libraries (see above)" >&2; exit 1
fi

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
