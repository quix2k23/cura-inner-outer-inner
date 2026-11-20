#!/usr/bin/env python3
"""Checks that "Retract Before Outer Wall: Always" also retracts at layer changes with Inner/Outer/Inner and two walls.

    python tests/test_layer_change_retract.py <path to CuraEngine or CuraEngine.exe>

With two walls, Inner/Outer/Inner prints the outer wall first, the same as Outside To Inside, so the travel to the next
layer must be retracted like it is for Outside To Inside. Inside To Outside is the control: there the engine does not
force this retraction, which shows that the test can see the difference.
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slicelib  # noqa: E402
from slicelib import report, slice_model  # noqa: E402

_E = re.compile(r"\bE(-?\d*\.?\d+)")


def retracted_layer_changes(gcode):
    """Returns (layer changes with a retraction between the last extrusion and the next layer's first extrusion, total)."""
    e = 0.0
    relative = False
    retracted = False
    changes = 0
    with_retract = 0
    seen_layer = False
    with open(gcode) as f:
        for raw in f:
            if raw.startswith(";LAYER:"):
                if seen_layer:
                    changes += 1
                    with_retract += retracted
                seen_layer = True
                continue
            line = raw.split(";")[0].strip()
            if line == "M83":
                relative = True
            elif line == "M82":
                relative = False
            elif line.startswith("G92"):
                m = _E.search(line)
                if m:
                    e = float(m.group(1))
            elif line.startswith("G10"):
                retracted = True
            elif line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
                m = _E.search(line)
                if not m:
                    continue
                value = float(m.group(1))
                delta = value if relative else value - e
                if not relative:
                    e = value
                if delta < 0:
                    retracted = True
                elif delta > 0 and ("X" in line or "Y" in line):
                    retracted = False  # Printing again: only a retraction after the last extrusion counts.
    return with_retract, changes


def main():
    engine = os.path.abspath(sys.argv[1])
    ok = True
    with tempfile.TemporaryDirectory() as work:
        ring = os.path.join(work, "ring.stl")
        slicelib.round_ring(ring, height=3.0)
        base = {"wall_line_count": 2, "retraction_enable": "true", "retract_at_layer_change": "false",
                "travel_retract_before_outer_wall": "force_retracted", "retraction_min_travel": 100,
                "infill_sparse_density": 0, "top_layers": 0, "bottom_layers": 0}
        results = {}
        for direction in ("inside_out", "outside_in", "inner_outer_inner"):
            gcode = slice_model(engine, work, ring, os.path.join(work, direction + ".gcode"),
                                dict(base, inset_direction=direction, initial_layer_inset_direction=direction))
            results[direction] = retracted_layer_changes(gcode)
            print("    %-18s %d of %d layer changes retracted" % (direction, *results[direction]))

        done, total = results["outside_in"]
        ok &= report("outside in: every layer change is retracted", total > 5 and done == total)
        done, total = results["inner_outer_inner"]
        ok &= report("inner/outer/inner with 2 walls: every layer change is retracted", total > 5 and done == total)
        done, total = results["inside_out"]
        ok &= report("inside out (control): layer changes are not forced to retract", done < total)
    print("\nALL PASSED" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
