#!/bin/sh
# Installs a package into throwaway Cura settings folders and checks install, a second install and uninstall.
#   tests/test_installer.sh <unpacked package folder>
# It never touches a real Cura: everything happens in a temporary folder.
set -eu

PKG=$(cd "$1" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
FAILED=0

fail() { echo "FAIL $*"; FAILED=1; }
pass() { echo "PASS $*"; }

# $1 = name of the case, $2 = content of the starting cura.cfg (printf format)
run_case() {
    NAME=$1
    ROOT="$WORK/$NAME"
    DATA="$ROOT/data/cura/5.13"
    DEST="$ROOT/data/cura-inner-outer-inner"
    mkdir -p "$DATA"
    printf "$2" > "$DATA/cura.cfg"
    cp "$DATA/cura.cfg" "$ROOT/original.cfg"

    "$PKG/install.sh" --native --force --data-dir "$DATA" > "$ROOT/install1.log" 2>&1 || { cat "$ROOT/install1.log"; fail "$NAME: install failed"; return; }
    "$PKG/install.sh" --native --force --data-dir "$DATA" > "$ROOT/install2.log" 2>&1 || { cat "$ROOT/install2.log"; fail "$NAME: second install failed"; return; }

    [ "$(grep -c '^location = ' "$DATA/cura.cfg")" = 1 ] && grep -q "^location = $DEST/CuraEngine\$" "$DATA/cura.cfg" \
        && pass "$NAME: one location line pointing at the engine, also after installing twice" || fail "$NAME: location line wrong"
    # Cura reads cura.cfg with Python's strict config parser, which refuses a file that has the same section twice.
    if python3 -c "import configparser, sys; configparser.ConfigParser(interpolation=None, strict=True).read(sys.argv[1])" "$DATA/cura.cfg" 2> /dev/null; then pass "$NAME: cura.cfg is still valid for Cura's config parser"; else fail "$NAME: cura.cfg is no longer valid (duplicate section?)"; fi
    [ -f "$DATA/plugins/InnerOuterInnerWalls/plugin.json" ] && [ -f "$DATA/plugins/InnerOuterInnerWalls/settings.def.json" ] \
        && pass "$NAME: plugin files installed" || fail "$NAME: plugin files missing"
    [ -f "$DEST/FEATURES" ] && [ -x "$DEST/CuraEngine" ] && pass "$NAME: engine and FEATURES file installed" || fail "$NAME: engine files missing"

    "$PKG/uninstall.sh" --native --data-dir "$DATA" > /dev/null 2>&1 || fail "$NAME: uninstall failed"
    # An empty [backend] header left behind is fine: Cura writes those itself.
    strip() { tr -d '\r' < "$1" | grep -v '^\[backend\]$' | grep -v '^$' || true; }
    if cmp -s "$ROOT/original.cfg" "$DATA/cura.cfg" || [ "$(strip "$ROOT/original.cfg")" = "$(strip "$DATA/cura.cfg")" ]; then pass "$NAME: uninstall restores cura.cfg"; else fail "$NAME: cura.cfg not restored"; fi
    [ ! -e "$DEST" ] && [ ! -e "$DATA/plugins/InnerOuterInnerWalls" ] && pass "$NAME: uninstall removes the engine and the plugin" || fail "$NAME: leftovers after uninstall"
}

run_case empty_backend_section '[general]\nversion = 6\n\n[backend]\n\n[mesh]\n'
run_case no_backend_section '[general]\nversion = 6\n\n[mesh]\n'
run_case other_backend_keys '[general]\nversion = 6\n\n[backend]\nsome_key = 1\n\n[mesh]\n'
run_case windows_line_endings '[general]\r\nversion = 6\r\n\r\n[backend]\r\n\r\n[mesh]\r\n'

# Refuses to run while Cura is running (the installer checks for the process by name).
if [ "$FAILED" = 0 ]; then echo "ALL PASSED"; else echo "FAILED"; exit 1; fi
