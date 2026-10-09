#!/bin/sh
# Removes the inner/outer/inner CuraEngine + plugin and points Cura back at its own engine. Close Cura first.
#   ./uninstall.sh [--flatpak | --native] [--data-dir DIR]
set -eu

VERSION_DIR=5.13
MODE=auto
DATA=

die() { echo "error: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        --flatpak) MODE=flatpak ;;
        --native) MODE=native ;;
        --data-dir) shift; DATA=${1:-}; [ -n "$DATA" ] || die "--data-dir needs a directory" ;;
        -h|--help) sed -n 2,3p "$0"; exit 0 ;;
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
        auto) if [ -d "$FLATPAK_DATA" ]; then DATA=$FLATPAK_DATA; else DATA=$NATIVE_DATA; fi ;;
    esac
fi

CFG="$DATA/cura.cfg"
DEST="$(dirname "$(dirname "$DATA")")/cura-inner-outer-inner"

if [ -f "$CFG" ]; then
    # Drop only our location line from [backend]; leave everything else as it is.
    awk -v dest="$DEST/" '
        { line = $0; sub(/\r$/, "", line) }  # Match without a Windows line ending, but write the line back unchanged.
        line ~ /^\[/ { inb = (line == "[backend]") }
        inb && line ~ /^location[ \t]*=/ && index(line, dest) { next }
        { print }
    ' "$CFG" > "$CFG.new" && mv "$CFG.new" "$CFG"
    echo "Cura now uses its own engine again."
fi
rm -rf "$DATA/plugins/InnerOuterInnerWalls" "$DEST"
echo "Removed the plugin and $DEST."
echo "If a print profile still says Inner/Outer/Inner, change Wall Ordering back before slicing."
