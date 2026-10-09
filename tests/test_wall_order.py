#!/usr/bin/env python3
"""Slices a ring-shaped test part with a CuraEngine binary and checks the order in which the walls are printed.

    python tests/test_wall_order.py <path to CuraEngine or CuraEngine.exe>

The ring is a 30x30 mm block with a 10x10 mm hole, so every layer has an outer contour and a hole. Each wall loop is
identified from its size: wall N is N * 0.4 mm further inside than the outer wall.
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

CURA_TAG = "5.13.0"
DEFINITION_URL = "https://raw.githubusercontent.com/Ultimaker/Cura/%s/resources/definitions/%%s" % CURA_TAG
LAYER = 10  # a layer well away from the first layer and the top/bottom skin


def write_ring_stl(path):
    def box(x0, y0, x1, y1, z0=0.0, z1=6.0):
        v = lambda x, y, z: (x, y, z)
        quad = lambda a, b, c, d: [(a, b, c), (a, c, d)]
        f = []
        f += quad(v(x0, y0, z0), v(x0, y1, z0), v(x1, y1, z0), v(x1, y0, z0))
        f += quad(v(x0, y0, z1), v(x1, y0, z1), v(x1, y1, z1), v(x0, y1, z1))
        f += quad(v(x0, y0, z0), v(x1, y0, z0), v(x1, y0, z1), v(x0, y0, z1))
        f += quad(v(x1, y0, z0), v(x1, y1, z0), v(x1, y1, z1), v(x1, y0, z1))
        f += quad(v(x1, y1, z0), v(x0, y1, z0), v(x0, y1, z1), v(x1, y1, z1))
        f += quad(v(x0, y1, z0), v(x0, y0, z0), v(x0, y0, z1), v(x0, y1, z1))
        return f

    triangles = []
    for slab in [(0, 0, 30, 10), (0, 20, 30, 30), (0, 10, 10, 20), (20, 10, 30, 20)]:
        triangles += box(*slab)
    with open(path, "w") as f:
        f.write("solid ring\n")
        for t in triangles:
            f.write("facet normal 0 0 0\nouter loop\n")
            for p in t:
                f.write("vertex %f %f %f\n" % p)
            f.write("endloop\nendfacet\n")
        f.write("endsolid ring\n")


def slice_ring(engine, workdir, inset_direction, walls, gcode, initial_direction=None):
    for name in ("fdmprinter.def.json", "fdmextruder.def.json"):
        target = os.path.join(workdir, name)
        if not os.path.exists(target):
            urllib.request.urlretrieve(DEFINITION_URL % name, target)
    stl = os.path.join(workdir, "ring.stl")
    write_ring_stl(stl)
    common = ["-s", "wall_line_count=%d" % walls, "-s", "inset_direction=%s" % inset_direction,
              "-s", "layer_height=0.2", "-s", "layer_height_0=0.2", "-s", "adhesion_type=none",
              "-s", "infill_sparse_density=10"]
    if initial_direction:
        common += ["-s", "initial_layer_inset_direction=%s" % initial_direction]
    cmd = [engine, "slice", "--force-read-parent", "-j", os.path.join(workdir, "fdmprinter.def.json"),
           "-s", "machine_width=200", "-s", "machine_depth=200", "-s", "machine_height=200",
           "-s", "machine_center_is_zero=false"] + common + \
          ["-e0", "--force-read-parent", "-j", os.path.join(workdir, "fdmextruder.def.json"),
           "-j", os.path.join(workdir, "fdmprinter.def.json"), "-s", "machine_nozzle_size=0.4"] + common + \
          ["-l", stl, "-o", gcode]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(gcode) or os.path.getsize(gcode) == 0:
        raise SystemExit("slicing failed (%s, %d walls):\n%s%s" % (inset_direction, walls, result.stdout[-2000:], result.stderr[-2000:]))


def wall_order(gcode, layer):
    """Returns ['contour wall3', 'hole wall3', ...] in print order for one layer."""
    loops, pts, in_layer, wall_type, x, y = [], [], False, None, None, None

    def flush():
        nonlocal pts
        if len(pts) > 3 and wall_type in ("WALL-OUTER", "WALL-INNER"):
            xs = [p[0] for p in pts]
            width = max(xs) - min(xs)
            if width > 25:
                kind, offset = "contour", (30 - width) / 2
            else:
                kind, offset = "hole", (width - 10) / 2
            loops.append("%s wall%d" % (kind, round((offset - 0.2) / 0.4)))
        pts = []

    with open(gcode) as f:
        for line in f:
            if line.startswith(";LAYER:"):
                flush()
                in_layer = int(line[7:]) == layer
                continue
            if not in_layer:
                continue
            if line.startswith(";TYPE:"):
                flush()
                wall_type = line[6:].strip()
                continue
            m = re.match(r"G([01]) ", line)
            if not m:
                continue
            nx, ny = re.search(r"X([-\d.]+)", line), re.search(r"Y([-\d.]+)", line)
            x = float(nx.group(1)) if nx else x
            y = float(ny.group(1)) if ny else y
            if m.group(1) == "0":
                flush()
                pts = [(x, y)]
            elif "E" in line and (nx or ny):
                pts.append((x, y))
    flush()
    return loops


def expect(label, actual, expected):
    ok = actual == expected
    print("%s %s\n    got      %s%s" % ("PASS" if ok else "FAIL", label, actual, "" if ok else "\n    expected %s" % expected))
    return ok


def main():
    engine = os.path.abspath(sys.argv[1])
    ok = True
    with tempfile.TemporaryDirectory() as workdir:
        def run(direction, walls, initial=None, layer=LAYER):
            gcode = os.path.join(workdir, "%s-%d-%s.gcode" % (direction, walls, initial))
            slice_ring(engine, workdir, direction, walls, gcode, initial)
            return wall_order(gcode, layer)

        def contour(order):
            return [int(w.split("wall")[1]) for w in order if w.startswith("contour")]

        both = lambda order: [("%s wall%d" % (k, w)) for k in ("contour", "hole") for w in order]

        got = run("inner_outer_inner", 4)
        ok &= expect("inner_outer_inner, 4 walls: 3,2,outer(0),1 for each loop", sorted(got), sorted(both([3, 2, 0, 1])))
        for kind in ("contour", "hole"):
            seq = [int(w.split("wall")[1]) for w in got if w.startswith(kind)]
            ok &= expect("  %s order" % kind, seq, [3, 2, 0, 1])
        for kind in ("contour", "hole"):
            seq = [int(w.split("wall")[1]) for w in run("inner_outer_inner", 3) if w.startswith(kind)]
            ok &= expect("inner_outer_inner, 3 walls, %s" % kind, seq, [2, 0, 1])
        for kind in ("contour", "hole"):
            seq = [int(w.split("wall")[1]) for w in run("inner_outer_inner", 2) if w.startswith(kind)]
            ok &= expect("inner_outer_inner, 2 walls, %s (outer then inner)" % kind, seq, [0, 1])
        for kind in ("contour", "hole"):
            seq = [int(w.split("wall")[1]) for w in run("inside_out", 4) if w.startswith(kind)]
            ok &= expect("inside_out unchanged, 4 walls, %s" % kind, seq, [3, 2, 1, 0])

        # The first layer has its own setting ("Initial Layer Wall Ordering"); all other layers use "Wall Ordering".
        for wall_ordering, initial, first, later in (("inside_out", "inner_outer_inner", [3, 2, 0, 1], [3, 2, 1, 0]),
                                                      ("inner_outer_inner", "inside_out", [3, 2, 1, 0], [3, 2, 0, 1]),
                                                      ("inner_outer_inner", "inner_outer_inner", [3, 2, 0, 1], [3, 2, 0, 1])):
            ok &= expect("first layer with Initial Layer Wall Ordering %s, Wall Ordering %s" % (initial, wall_ordering),
                         contour(run(wall_ordering, 4, initial, layer=0)), first)
            ok &= expect("  other layers with the same settings", contour(run(wall_ordering, 4, initial, layer=LAYER)), later)
    print("\nALL PASSED" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
