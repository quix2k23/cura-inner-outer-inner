"""Helpers shared by the tests: test models, slicing with a CuraEngine binary, and reading G-code back."""
import math
import os
import re
import subprocess
import urllib.request
from collections import defaultdict

CURA_TAG = "5.13.0"
DEFINITION_URL = "https://raw.githubusercontent.com/Ultimaker/Cura/%s/resources/definitions/%%s" % CURA_TAG


def write_stl(path, triangles):
    with open(path, "w") as f:
        f.write("solid test\n")
        for t in triangles:
            f.write("facet normal 0 0 0\nouter loop\n")
            for p in t:
                f.write("vertex %f %f %f\n" % p)
            f.write("endloop\nendfacet\n")
        f.write("endsolid test\n")


def _box(x0, y0, z0, x1, y1, z1):
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


def block(path, size_xy, height):
    """A solid block."""
    write_stl(path, _box(0, 0, 0, size_xy, size_xy, height))


def round_ring(path, outer=15.0, inner=5.0, height=6.0, wedges=120):
    """A ring made of small wedge-shaped blocks, so that the walls are round."""
    triangles = []
    quad = lambda a, b, c, d: [(a, b, c), (a, c, d)]
    for n in range(wedges):
        a0, a1 = 2 * math.pi * n / wedges, 2 * math.pi * (n + 1) / wedges
        P = lambda r, a, z: (r * math.cos(a) + 50, r * math.sin(a) + 50, z)
        ob0, ob1, ot0, ot1 = P(outer, a0, 0), P(outer, a1, 0), P(outer, a0, height), P(outer, a1, height)
        ib0, ib1, it0, it1 = P(inner, a0, 0), P(inner, a1, 0), P(inner, a0, height), P(inner, a1, height)
        triangles += quad(ob0, ob1, ot1, ot0) + quad(ib0, it0, it1, ib1) + quad(ot0, ot1, it1, it0)
        triangles += quad(ob0, ib0, ib1, ob1) + quad(ob0, ot0, it0, ib0) + quad(ob1, ib1, it1, ot1)
    write_stl(path, triangles)


def slice_model(engine, workdir, stl, gcode, settings=None):
    """Slice a model with the given settings; returns the path of the G-code."""
    for name in ("fdmprinter.def.json", "fdmextruder.def.json"):
        target = os.path.join(workdir, name)
        if not os.path.exists(target):
            urllib.request.urlretrieve(DEFINITION_URL % name, target)
    merged = {"machine_width": 300, "machine_depth": 300, "machine_height": 300, "machine_center_is_zero": "false",
              "layer_height": 0.2, "layer_height_0": 0.2, "adhesion_type": "none", "wall_line_count": 2,
              "top_layers": 3, "bottom_layers": 3, "infill_angle": 0}
    merged.update(settings or {})
    common = []
    for key, value in merged.items():
        common += ["-s", "%s=%s" % (key, value)]
    defs = [os.path.join(workdir, "fdmprinter.def.json"), os.path.join(workdir, "fdmextruder.def.json")]
    cmd = [engine, "slice", "--force-read-parent", "-j", defs[0]] + common + \
          ["-e0", "--force-read-parent", "-j", defs[1], "-j", defs[0], "-s", "machine_nozzle_size=0.4"] + common + \
          ["-l", stl, "-o", gcode]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(gcode) or os.path.getsize(gcode) == 0:
        raise SystemExit("slicing failed (%s):\n%s%s" % (merged, result.stdout[-2000:], result.stderr[-2000:]))
    return gcode


_WORD = re.compile(r"([A-Z])(-?\d*\.?\d+)")


def extrusion_segments(gcode, wanted_type=None):
    """Yields (layer, type, (x0, y0), (x1, y1)) for every printed straight move; arcs are sampled every 0.1 mm."""
    layer, kind, x, y, e = -1, None, 0.0, 0.0, 0.0
    relative = False
    with open(gcode) as f:
        for raw in f:
            if raw.startswith(";LAYER:"):
                layer = int(raw[7:])
                continue
            if raw.startswith(";TYPE:"):
                kind = raw[6:].strip()
                continue
            line = raw.split(";")[0].strip()
            if line == "M83":
                relative = True
            elif line == "M82":
                relative = False
            if not line.startswith(("G0 ", "G1 ", "G2 ", "G3 ", "G92")):
                continue
            p = {k: float(v) for k, v in _WORD.findall(line)}
            if line.startswith("G92"):
                e = p.get("E", e)
                continue
            nx, ny = p.get("X", x), p.get("Y", y)
            extruded = 0.0
            if "E" in p:
                extruded = p["E"] if relative else p["E"] - e
                e = e + p["E"] if relative else p["E"]
            if layer >= 0 and extruded > 0 and (wanted_type is None or kind == wanted_type):
                if line.startswith(("G0", "G1")):
                    yield layer, kind, (x, y), (nx, ny)
                else:
                    cx, cy = x + p["I"], y + p["J"]
                    r = math.hypot(x - cx, y - cy)
                    a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                    sweep = (a1 - a0) % (2 * math.pi) if line.startswith("G3") else -((a0 - a1) % (2 * math.pi))
                    n = max(2, int(abs(sweep) * r / 0.1))
                    prev = (x, y)
                    for i in range(1, n + 1):
                        a = a0 + sweep * i / n
                        point = (cx + r * math.cos(a), cy + r * math.sin(a))
                        yield layer, kind, prev, point
                        prev = point
            x, y = nx, ny


def layer_lengths(gcode, wanted_type):
    """Total printed length per layer for one feature type."""
    totals = defaultdict(float)
    for layer, _, a, b in extrusion_segments(gcode, wanted_type):
        totals[layer] += math.hypot(b[0] - a[0], b[1] - a[1])
    return totals


def sample_points(gcode, wanted_type, spacing=0.2):
    """Points along the printed paths, per layer."""
    points = defaultdict(list)
    for layer, _, a, b in extrusion_segments(gcode, wanted_type):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(length / spacing))
        for i in range(n):
            t = i / n
            points[layer].append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return points


class PointIndex:
    """Nearest-neighbour lookups for a set of 2D points, using a grid."""

    def __init__(self, points, cell=0.5):
        self.cell = cell
        self.grid = defaultdict(list)
        for p in points:
            self.grid[(int(p[0] // cell), int(p[1] // cell))].append(p)

    def nearest(self, p, limit):
        reach = int(limit // self.cell) + 1
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        best = float("inf")
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                for q in self.grid.get((cx + dx, cy + dy), ()):
                    best = min(best, math.hypot(p[0] - q[0], p[1] - q[1]))
        return best


def report(label, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", label, ("\n    " + detail) if detail else ""))
    return ok
