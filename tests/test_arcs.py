#!/usr/bin/env python3
"""Checks arc fitting (G2/G3 output) of a CuraEngine binary.

    python tests/test_arcs.py <path to CuraEngine or CuraEngine.exe>

A round part is sliced twice, with straight moves only and with arc fitting. The arcs must follow the original path
within the tolerance, extrude the same amount of material, be valid for firmware (the start and end of an arc are the
same distance from its centre), and make the G-code clearly smaller. Straight parts must not be turned into arcs.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slicelib  # noqa: E402
from compare_gcode_paths import compare  # noqa: E402
from slicelib import report, slice_model  # noqa: E402

TOLERANCE = 0.05


def count_arcs(gcode):
    with open(gcode) as f:
        return sum(1 for line in f if line.startswith(("G2 ", "G3 ")))


def main():
    engine = os.path.abspath(sys.argv[1])
    ok = True
    with tempfile.TemporaryDirectory() as work:
        ring = os.path.join(work, "ring.stl")
        slicelib.round_ring(ring, height=2.4)
        settings = {"wall_line_count": 3, "infill_pattern": "gyroid", "infill_line_distance": 4}

        straight = slice_model(engine, work, ring, os.path.join(work, "straight.gcode"), settings)
        off = slice_model(engine, work, ring, os.path.join(work, "off.gcode"), dict(settings, arc_fitting_enable="false"))
        arcs = slice_model(engine, work, ring, os.path.join(work, "arcs.gcode"),
                           dict(settings, arc_fitting_enable="true", arc_fitting_tolerance=TOLERANCE, arc_fitting_max_radius=1000))

        ok &= report("no arcs unless arc fitting is turned on", count_arcs(straight) == 0 and count_arcs(off) == 0)
        arc_count, deviation, extruded, radius_error = compare(straight, arcs)
        ok &= report("arc fitting produces arcs (%d)" % arc_count, arc_count > 50)
        ok &= report("arcs stay within the tolerance: worst deviation %.3f mm (allowed %.3f)" % (deviation, TOLERANCE), deviation <= TOLERANCE + 0.005)
        ok &= report("arcs extrude the same material: worst difference %.3f %% in a layer (allowed 1 %%)" % (extruded * 100), extruded <= 0.01)
        ok &= report("start and end of every arc are the same distance from its centre: worst %.4f mm (allowed 0.01)" % radius_error, radius_error <= 0.01)
        size_off, size_on = os.path.getsize(straight), os.path.getsize(arcs)
        ok &= report("G-code is much smaller: %d -> %d bytes (%.1f times)" % (size_off, size_on, size_off / size_on), size_on < size_off * 0.6)

        # A larger tolerance replaces more segments with arcs, a smaller one fewer.
        loose = slice_model(engine, work, ring, os.path.join(work, "loose.gcode"), dict(settings, arc_fitting_enable="true", arc_fitting_tolerance=0.2))
        tight = slice_model(engine, work, ring, os.path.join(work, "tight.gcode"), dict(settings, arc_fitting_enable="true", arc_fitting_tolerance=0.01))
        ok &= report("larger tolerance gives larger G-code reduction: %d bytes (0.2 mm) vs %d (0.01 mm)" % (os.path.getsize(loose), os.path.getsize(tight)), os.path.getsize(loose) < os.path.getsize(tight))

    print("\nALL PASSED" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
