#!/usr/bin/env python3
"""Export a patched libArcus recipe into the local Conan cache, so the engine build uses it.

UltiMaker's libArcus deletes a still-joinable thread in Socket::~Socket() when the connection was already closed,
which makes CuraEngine abort at exit ("terminate called without an active exception"). Upstream PR:
https://github.com/Ultimaker/libArcus/pull/168 . Once a fixed arcus is released, drop this step.

Usage (from the repo root):
    python3 scripts/patch-arcus.py WORK_DIR CONAN_ARGS...
WORK_DIR gets the libArcus checkout. CONAN_ARGS are the same profile/options as the engine build; they are used to
check that the engine graph now resolves to the patched recipe revision.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATCH = ROOT / "scripts" / "patches" / "libarcus-socket-join.patch"


def run(*cmd, cwd=None, inp=None):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, input=inp, text=True, check=True, stdout=subprocess.PIPE).stdout


def main():
    work = pathlib.Path(sys.argv[1]).resolve()
    conan_args = sys.argv[2:]
    m = re.search(r'"arcus/([0-9.]+)"', (ROOT / "curaengine" / "conandata.yml").read_text())
    version = m.group(1)

    # Resolve the graph once so the published arcus recipe is in the cache; the commit it was made from is recorded
    # in its conandata.yml.
    run("conan", "graph", "info", str(ROOT / "curaengine"), *conan_args, "--format=json")
    export_dir = pathlib.Path(run("conan", "cache", "path", f"arcus/{version}").strip())
    commit = re.search(r"commit:\s*([0-9a-f]{40})", (export_dir / "conandata.yml").read_text()).group(1)
    print(f"arcus {version} is libArcus commit {commit}")

    if not (work / ".git").exists():
        run("git", "-c", "core.autocrlf=false", "clone", "-q", "https://github.com/Ultimaker/libArcus.git", str(work))
    run("git", "-c", "core.autocrlf=false", "checkout", "-q", "-f", commit, cwd=work)
    # Normalise line endings: the patch may have been checked out with CRLF on Windows.
    run("git", "apply", "-", cwd=work, inp=PATCH.read_text().replace("\r\n", "\n"))

    out = run("conan", "export", ".", "--version", version, "--format=json", cwd=work)
    ref = json.loads(out)["reference"]          # "arcus/5.11.1#<recipe revision>"
    rrev = ref.split("#", 1)[1]
    print(f"exported {ref}")
    # The recipe builds from its exported sources (src/ is copied from WORK_DIR), so the fix must be in them.
    es = pathlib.Path(run("conan", "cache", "path", ref, "--folder", "export_source").strip())
    if "joinable()" not in (es / "src" / "Socket.cpp").read_text():
        sys.exit(f"error: the exported sources of {ref} do not contain the fix")

    graph = json.loads(run("conan", "graph", "info", str(ROOT / "curaengine"), *conan_args, "--format=json"))
    used = [n["ref"] for n in graph["graph"]["nodes"].values() if n.get("ref", "").startswith(f"arcus/{version}")]
    print(f"engine graph uses {used}")
    if not used or not all(u.endswith("#" + rrev) for u in used):
        sys.exit(f"error: the engine does not resolve to the patched arcus revision {rrev}")


if __name__ == "__main__":
    main()
