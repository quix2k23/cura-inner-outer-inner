#!/usr/bin/env python3
"""Draws a vertical cross-section of the infill in a G-code file: where the printed lines cross the plane y = Y.

    python tests/render_section.py out.png Y file.gcode [file.gcode ...]

Each file becomes one panel; x runs left to right and the layers stack upwards.
"""
import math
import re
import sys

from PIL import Image, ImageDraw


def crossings(path, y_plane):
    layer, kind, x, y, e = -1, None, 0.0, 0.0, 0.0
    word = re.compile(r"([A-Z])(-?\d*\.?\d+)")
    dots = []
    with open(path) as f:
        for raw in f:
            if raw.startswith(";LAYER:"):
                layer = int(raw[7:])
                continue
            if raw.startswith(";TYPE:"):
                kind = raw[6:].strip()
                continue
            line = raw.split(";")[0].strip()
            if not line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
                continue
            p = {k: float(v) for k, v in word.findall(line)}
            nx, ny = p.get("X", x), p.get("Y", y)
            if kind == "FILL" and line.startswith("G1") and "E" in p and p["E"] > e and (y - y_plane) * (ny - y_plane) <= 0 and ny != y:
                t = (y_plane - y) / (ny - y)
                dots.append((layer, x + t * (nx - x)))
            if "E" in p:
                e = p["E"]
            x, y = nx, ny
    return dots


def main():
    out, y_plane, files = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
    px = 14
    panels = []
    for path in files:
        dots = crossings(path, y_plane)
        xs = [d[1] for d in dots]
        layers = max(d[0] for d in dots) + 1
        x0 = min(xs) - 1
        w, h = int((max(xs) - x0 + 1) * px), int(layers * 0.2 * px) + 24
        img = Image.new("RGB", (w, h), "white")
        d = ImageDraw.Draw(img)
        d.text((4, 3), path.split("/")[-1], fill=(0, 0, 0))
        for layer, x in dots:
            cx = (x - x0) * px
            cy = h - (layer * 0.2 + 0.1) * px
            d.rectangle([cx - 0.2 * px, cy - 0.1 * px - 0.5, cx + 0.2 * px, cy + 0.1 * px + 0.5], fill=(30, 90, 200))
        panels.append(img)
    sheet = Image.new("RGB", (sum(p.width for p in panels) + 8 * (len(panels) - 1), max(p.height for p in panels)), "white")
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0))
        x += p.width + 8
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
