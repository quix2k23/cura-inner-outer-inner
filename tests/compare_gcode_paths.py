#!/usr/bin/env python3
"""Compares the toolpaths of two G-code files: one printed with straight lines, one with G2/G3 arcs.

    python tests/compare_gcode_paths.py lines.gcode arcs.gcode [max_deviation_mm]

Checks, per layer, that (1) every point of the arc toolpath lies within the allowed distance of the line toolpath and
the other way around (so arcs run in the right direction and do not cut corners), (2) the extruded amount agrees, and
(3) the start and end radius of every arc agree, which firmware requires.
"""
import math
import re
import sys
from collections import defaultdict


def parse(path):
    """Returns {layer: (segments, extruded_mm, arcs)} with segments as ((x0, y0), (x1, y1))."""
    layers = defaultdict(lambda: [[], 0.0, 0])
    layer = -1
    x = y = e = 0.0
    relative_e = False
    arc_radius_errors = []
    arc_count = 0
    word = re.compile(r"([A-Z])(-?\d*\.?\d+)")
    with open(path) as f:
        for raw in f:
            line = raw.split(";")[0].strip()
            if raw.startswith(";LAYER:"):
                layer = int(raw[7:])
                continue
            if line == "M83":
                relative_e = True
            elif line == "M82":
                relative_e = False
            if not (line.startswith(("G0 ", "G1 ", "G2 ", "G3 ", "G92"))):
                continue
            params = {k: float(v) for k, v in word.findall(line)}
            if line.startswith("G92"):
                e = params.get("E", e)
                continue
            nx, ny = params.get("X", x), params.get("Y", y)
            ne = params.get("E")
            extruded = 0.0
            if ne is not None:
                extruded = ne if relative_e else ne - e
                e = e + ne if relative_e else ne
            if layer >= 0 and extruded > 0:
                if line.startswith(("G0", "G1")):
                    layers[layer][0].append(((x, y), (nx, ny)))
                else:
                    arc_count += 1
                    cx, cy = x + params["I"], y + params["J"]
                    r0, r1 = math.hypot(x - cx, y - cy), math.hypot(nx - cx, ny - cy)
                    arc_radius_errors.append(abs(r0 - r1))
                    a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                    sweep = (a1 - a0) % (2 * math.pi) if line.startswith("G3") else -((a0 - a1) % (2 * math.pi))
                    steps = max(2, int(abs(sweep) * r0 / 0.05))  # sample every 0.05 mm
                    prev = (x, y)
                    for i in range(1, steps + 1):
                        a = a0 + sweep * i / steps
                        point = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
                        layers[layer][0].append((prev, point))
                        prev = point
                layers[layer][1] += extruded
                layers[layer][2] += 0 if line.startswith(("G0", "G1")) else 1
            x, y = nx, ny
    return layers, arc_radius_errors, arc_count


def distance_to_segment(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


class Index:
    def __init__(self, segments, cell=1.0):
        self.cell = cell
        self.grid = defaultdict(list)
        for seg in segments:
            (x0, y0), (x1, y1) = seg
            for cx in range(int(min(x0, x1) // cell) - 1, int(max(x0, x1) // cell) + 2):
                for cy in range(int(min(y0, y1) // cell) - 1, int(max(y0, y1) // cell) + 2):
                    self.grid[(cx, cy)].append(seg)

    def nearest(self, p):
        best = float("inf")
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        for seg in self.grid.get((cx, cy), []):
            best = min(best, distance_to_segment(p, seg[0], seg[1]))
        return best


def one_sided(segments_from, index_to):
    worst = 0.0
    for a, b in segments_from:
        for t in (0.0, 0.5, 1.0):
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            worst = max(worst, index_to.nearest(p))
    return worst


def compare(lines_path, arcs_path):
    """Returns (arc count, worst deviation in mm, worst extruded-amount difference as a fraction, worst arc radius mismatch in mm)."""
    lines, _, _ = parse(lines_path)
    arcs, radius_errors, arc_count = parse(arcs_path)
    worst_dev, worst_e = 0.0, 0.0
    for layer in sorted(set(lines) & set(arcs)):
        dev = max(one_sided(arcs[layer][0], Index(lines[layer][0])), one_sided(lines[layer][0], Index(arcs[layer][0])))
        e_diff = abs(arcs[layer][1] - lines[layer][1]) / max(lines[layer][1], 1e-9)
        worst_dev, worst_e = max(worst_dev, dev), max(worst_e, e_diff)
    return arc_count, worst_dev, worst_e, (max(radius_errors) if radius_errors else 0.0)


def main():
    lines_path, arcs_path = sys.argv[1], sys.argv[2]
    limit = float(sys.argv[3]) if len(sys.argv) > 3 else 0.06
    arc_count, worst_dev, worst_e, radius_error = compare(lines_path, arcs_path)
    print("arcs in the arc file: %d" % arc_count)
    print("worst deviation between the toolpaths: %.4f mm (allowed %.3f)" % (worst_dev, limit))
    print("worst extruded-amount difference in a layer: %.3f %%" % (worst_e * 100))
    print("worst arc start/end radius mismatch: %.4f mm" % radius_error)
    ok = arc_count > 0 and worst_dev <= limit and worst_e <= 0.02 and radius_error <= 0.01
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
