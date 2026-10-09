#!/bin/sh
# Installs the inner/outer/inner CuraEngine + Cura plugin for UltiMaker Cura 5.13 on Linux.
# Works for the Flatpak (com.ultimaker.cura) and for native/AppImage installs. Close Cura first.
#   ./install.sh [--flatpak | --native] [--data-dir DIR] [--force]
set -eu

VERSION_DIR=5.13
HERE=$(cd "$(dirname "$0")" && pwd)
MODE=auto
DATA=
FORCE=0

die() { echo "error: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --flatpak) MODE=flatpak ;;
        --native) MODE=native ;;
        --data-dir) shift; DATA=${1:-}; [ -n "$DATA" ] || die "--data-dir needs a directory" ;;
        --force) FORCE=1 ;;
        -h|--help) sed -n 2,5p "$0"; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
    shift
done

FLATPAK_DATA="$HOME/.var/app/com.ultimaker.cura/data/cura/$VERSION_DIR"
NATIVE_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/cura/$VERSION_DIR"

if [ -z "$DATA" ]; then
    case "$MODE" in
        flatpak) DATA=$FLATPAK_DATA ;;
        native) DATA=$NATIVE_DATA ;;
        auto)
            if [ -d "$FLATPAK_DATA" ]; then DATA=$FLATPAK_DATA; MODE=flatpak
            elif [ -d "$NATIVE_DATA" ]; then DATA=$NATIVE_DATA; MODE=native
            else die "no Cura $VERSION_DIR settings folder found. Start Cura 5.13 once, then run this again (or pass --data-dir)."; fi ;;
    esac
elif [ "$MODE" = auto ]; then
    case "$DATA" in *.var/app/com.ultimaker.cura*) MODE=flatpak ;; *) MODE=native ;; esac
fi

CFG="$DATA/cura.cfg"
[ -f "$CFG" ] || die "$CFG not found. Start Cura $VERSION_DIR once so it creates its settings, then run this again."

if [ "$FORCE" -eq 0 ] && pgrep -x UltiMaker-Cura >/dev/null 2>&1; then
    die "Cura is running. Close it first (or use --force)."
fi

# Engine goes next to Cura's data folder, which the Flatpak sandbox can read without any extra permissions.
DEST="$(dirname "$(dirname "$DATA")")/cura-inner-outer-inner"
ENGINE="$DEST/CuraEngine"

echo "Cura settings : $DATA ($MODE)"
echo "Engine install: $DEST"

[ -x "$HERE/engine/CuraEngine" ] || die "engine/CuraEngine missing next to this script"
[ -f "$HERE/plugin/InnerOuterInnerWalls/plugin.json" ] || die "plugin/ missing next to this script"

# Install the engine first and check that it runs before touching any Cura settings.
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$HERE/engine/." "$DEST/"
chmod +x "$DEST/CuraEngine" "$DEST/CuraEngine.bin"

if [ "$MODE" = flatpak ]; then
    OUT=$(flatpak run --command="$ENGINE" com.ultimaker.cura help 2>&1 || true)
else
    OUT=$("$ENGINE" help 2>&1 || true)
fi
case "$OUT" in
    *Cura_SteamEngine*) echo "Engine check : OK ($(echo "$OUT" | grep -m1 Cura_SteamEngine))" ;;
    *) rm -rf "$DEST"; echo "$OUT" | head -5 >&2; die "the engine does not run on this system. Nothing was changed." ;;
esac

# Plugin that adds the menu entry.
mkdir -p "$DATA/plugins"
rm -rf "$DATA/plugins/InnerOuterInnerWalls"
cp -a "$HERE/plugin/InnerOuterInnerWalls" "$DATA/plugins/InnerOuterInnerWalls"

# Point Cura at the patched engine ([backend] location in cura.cfg).
[ -f "$CFG.bak-inner-outer-inner" ] || cp -a "$CFG" "$CFG.bak-inner-outer-inner"
awk -v loc="$ENGINE" '
    /^\[/ { if (inb && !done) { print "location = " loc; done = 1 } inb = ($0 == "[backend]"); if (inb) seen = 1 }
    inb && /^location[ \t]*=/ { if (!done) { print "location = " loc; done = 1 } ; next }
    { print }
    END { if (inb && !done) print "location = " loc; if (!seen) { print ""; print "[backend]"; print "location = " loc } }
' "$CFG" > "$CFG.new" && mv "$CFG.new" "$CFG"

echo
echo "Done. Start Cura, open Print Settings, search for 'Wall Ordering' and choose 'Inner/Outer/Inner'."
echo "To undo: run uninstall.sh."
