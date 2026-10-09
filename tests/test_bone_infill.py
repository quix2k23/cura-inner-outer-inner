#!/usr/bin/env python3
"""Checks the bone-like infill pattern of a CuraEngine binary.

    python tests/test_bone_infill.py <path to CuraEngine or CuraEngine.exe>

Properties that are checked: the amount of infill follows the line distance, the result is reproducible and depends on
the seed, neighbouring layers are connected (so every layer is supported by the one below), the alignment setting makes
the struts run along the main direction, and the infill stays inside the part.
"""
import filecmp
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slicelib  # noqa: E402
from slicelib import PointIndex, layer_lengths, report, sample_points, slice_model  # noqa: E402

BONE = {"infill_pattern": "bone", "bone_cortical_width": 0}
SIZE = 30.0
HEIGHT = 8.0


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def continuity(gcode, layers, limit=0.4):
    """Fraction of infill points of a layer that have infill within `limit` mm in the layer below."""
    points = sample_points(gcode, "FILL")
    found = total = 0
    for layer in layers:
        below = PointIndex(points[layer - 1])
        for p in points[layer][::3]:
            total += 1
            found += below.nearest(p, limit) <= limit
    return found / total


def main():
    engine = os.path.abspath(sys.argv[1])
    ok = True
    with tempfile.TemporaryDirectory() as work:
        stl = os.path.join(work, "block.stl")
        slicelib.block(stl, SIZE, HEIGHT)

        def run(name, **settings):
            merged = dict(BONE)
            merged.update(settings)
            return slice_model(engine, work, stl, os.path.join(work, name + ".gcode"), merged)

        # 1. Density: the printed infill length per layer follows the line distance.
        layers = range(8, 32)
        for distance in (1.5, 3.0):
            gcode = run("density_%s" % distance, infill_line_distance=distance)
            lengths = layer_lengths(gcode, "FILL")
            expected = (SIZE - 4 * 0.4) ** 2 / distance
            ratio = mean(lengths[n] for n in layers) / expected
            ok &= report("density with line distance %.1f mm: measured / expected = %.2f (allowed 0.85 to 1.15)" % (distance, ratio), 0.85 <= ratio <= 1.15)

        # 2. Reproducible, and different for a different seed.
        a = run("seed_a1", infill_line_distance=3, bone_seed=11)
        b = run("seed_a2", infill_line_distance=3, bone_seed=11)
        c = run("seed_b", infill_line_distance=3, bone_seed=12)
        ok &= report("same seed gives identical G-code", filecmp.cmp(a, b, shallow=False))
        ok &= report("different seed gives different G-code", not filecmp.cmp(a, c, shallow=False))

        # 3. Neighbouring layers are connected, so that every layer has support.
        value = continuity(a, range(8, 24))
        ok &= report("layer to layer continuity: %.0f %% of the infill has infill below it (needs 90 %%)" % (value * 100), value >= 0.90)

        # 4. Alignment: with strong alignment the struts stand upright, so a layer matches the one below more closely
        # than in the same structure without alignment.
        isotropic = run("align_0", infill_line_distance=3, bone_alignment=0)
        aligned = run("align_95", infill_line_distance=3, bone_alignment=95)
        tight = lambda gcode: continuity(gcode, range(8, 24), limit=0.15)
        low, high = tight(isotropic), tight(aligned)
        ok &= report("alignment 95 %% keeps struts upright: %.0f %% match within 0.15 mm vs %.0f %% without alignment (needs 15 points more)" % (high * 100, low * 100), high >= low + 0.15)

        # Where the engine put the model: the extent of its outer wall.
        walls = [p for pts in sample_points(a, "WALL-OUTER").values() for p in pts]
        x0, x1 = min(p[0] for p in walls), max(p[0] for p in walls)
        y0, y1 = min(p[1] for p in walls), max(p[1] for p in walls)

        # 5. The infill stays inside the part, clear of the outer wall.
        points = sample_points(a, "FILL")
        margin = 0.3
        outside = sum(1 for n in points for (x, y) in points[n] if not (x0 + margin <= x <= x1 - margin and y0 + margin <= y <= y1 - margin))
        ok &= report("infill stays inside the walls (%d points outside)" % outside, outside == 0)

        # 6. The dense zone along the walls adds infill there and not in the middle.
        dense = sample_points(run("dense", infill_line_distance=3, bone_cortical_width=4, bone_cortical_lines=1), "FILL")
        plain = sample_points(run("plain", infill_line_distance=3, bone_cortical_width=0), "FILL")
        wall_distance = lambda p: min(p[0] - x0, x1 - p[0], p[1] - y0, y1 - p[1])
        count = lambda pts, test: sum(1 for n in pts for p in pts[n] if test(wall_distance(p)))
        more_edge = count(dense, lambda d: d < 4) / count(plain, lambda d: d < 4)
        same_middle = count(dense, lambda d: d > 6) / count(plain, lambda d: d > 6)
        ok &= report("dense zone: %.1f times the infill near the walls, %.2f times in the middle (needs > 1.5 and 0.9 to 1.1)" % (more_edge, same_middle), more_edge > 1.5 and 0.9 <= same_middle <= 1.1)

    print("\nALL PASSED" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
