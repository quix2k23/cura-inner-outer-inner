#!/bin/sh
# Quick checks to run before pushing. The same checks run on GitHub for every push (.github/workflows/checks.yml), and a
# git hook can run them for you:   git config core.hooksPath .githooks
#   scripts/preflight.sh            fast checks only (about a second)
#   CURA_ENGINE=/path/to/CuraEngine scripts/preflight.sh    also runs the engine tests on that binary
set -u
cd "$(dirname "$0")/.."
FAILED=0

step() {
    label=$1
    shift
    printf '%-62s ' "$label"
    if output=$("$@" 2>&1); then
        echo ok
    else
        echo FAILED
        echo "$output" | sed 's/^/    /'
        FAILED=1
    fi
}

step "shell scripts parse" sh -c 'for f in scripts/*.sh scripts/linux/*.sh tests/*.sh .githooks/*; do sh -n "$f" || exit 1; done'
step "python scripts compile" sh -c 'for f in tests/*.py plugin/InnerOuterInnerWalls/*.py; do python3 -c "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], \"exec\")" "$f" || exit 1; done'
step "plugin settings and metadata are valid JSON" python3 -c "import json; json.load(open('plugin/InnerOuterInnerWalls/settings.def.json')); json.load(open('plugin/InnerOuterInnerWalls/plugin.json'))"
step "workflows are valid YAML" python3 -c "import glob, yaml; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"
step "no personal paths or addresses in the files to publish" sh -c '! git grep -n -I -E "/home/[a-z]+/|@gmail\.com|192\.168\.[0-9]+\.[0-9]+" -- . ":(exclude)curaengine" ":(exclude)scripts/preflight.sh"'

stub=$(mktemp -d)
step "install and uninstall scripts against a stub package" sh -c "tests/make_stub_package.sh '$stub/pkg' && tests/test_installer.sh '$stub/pkg' | tail -1 | grep -q 'ALL PASSED'"
rm -rf "$stub"

# Pushing workflow files needs the "workflow" permission on the GitHub login; check before GitHub refuses the push.
if command -v gh > /dev/null 2>&1 && git rev-parse --verify -q origin/main > /dev/null && git diff --name-only origin/main...HEAD | grep -q '^\.github/workflows/'; then
    step "GitHub login may push workflow files (needs the 'workflow' scope)" sh -c "gh auth status 2>&1 | grep -q \"Token scopes:.*'workflow'\" || { echo \"run: gh auth refresh -h github.com -s workflow\"; exit 1; }"
fi

if [ -n "${CURA_ENGINE:-}" ]; then
    for t in test_wall_order test_arcs test_bone_infill; do
        step "$t on $CURA_ENGINE" sh -c "python3 tests/$t.py '$CURA_ENGINE' | tail -1 | grep -q 'ALL PASSED'"
    done
fi

if [ "$FAILED" = 0 ]; then echo "All checks passed."; else echo "Some checks FAILED: fix them before pushing."; exit 1; fi
