#!/usr/bin/env python3
"""Draws layers of a G-code file as images, to look at infill patterns.

    python tests/render_layers.py file.gcode out.png layer [layer ...] [--types INFILL,WALL-OUTER,...]
"""
import math
import re
import sys

from PIL import Image, ImageDraw

COLORS = {"WALL-OUTER": (40, 40, 40), "WALL-INNER": (110, 110, 110), "SKIN": (200, 120, 60), "FILL": (30, 90, 200)}


def read_layers(path, wanted):
    layers = {n: [] for n in wanted}
    layer, kind, x, y, e = -1, None, 0.0, 0.0, 0.0
    word = re.compile(r"([A-Z])(-?\d*\.?\d+)")
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
            extrude = "E" in p and p["E"] > (e if True else 0) if not line.startswith("G0") else False
            if "E" in p:
                e_new = p["E"]
            else:
                e_new = e
            if layer in layers and kind and line[:2] in ("G1", "G2", "G3") and "E" in p and e_new > e:
                if line.startswith("G1"):
                    layers[layer].append((kind, [(x, y), (nx, ny)]))
                else:
                    cx, cy = x + p["I"], y + p["J"]
                    r = math.hypot(x - cx, y - cy)
                    a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                    sweep = (a1 - a0) % (2 * math.pi) if line.startswith("G3") else -((a0 - a1) % (2 * math.pi))
                    n = max(2, int(abs(sweep) * r / 0.1))
                    layers[layer].append((kind, [(cx + r * math.cos(a0 + sweep * i / n), cy + r * math.sin(a0 + sweep * i / n)) for i in range(n + 1)]))
            e = e_new
            x, y = nx, ny
    return layers


def main():
    args = sys.argv[1:]
    types = None
    if "--types" in args:
        i = args.index("--types")
        types = set(args[i + 1].split(","))
        del args[i:i + 2]
    path, out, wanted = args[0], args[1], [int(a) for a in args[2:]]
    layers = read_layers(path, wanted)
    pixels_per_mm = 14
    panels = []
    allpts = [pt for segs in layers.values() for kind, pts in segs for pt in pts]
    minx, maxx = min(p[0] for p in allpts), max(p[0] for p in allpts)
    miny, maxy = min(p[1] for p in allpts), max(p[1] for p in allpts)
    w, h = int((maxx - minx + 2) * pixels_per_mm), int((maxy - miny + 2) * pixels_per_mm)
    for n in wanted:
        img = Image.new("RGB", (w, h + 20), "white")
        d = ImageDraw.Draw(img)
        d.text((4, 3), "layer %d" % n, fill=(0, 0, 0))
        for kind, pts in layers[n]:
            if types and kind not in types:
                continue
            xy = [((px - minx + 1) * pixels_per_mm, h - (py - miny + 1) * pixels_per_mm + 20) for px, py in pts]
            d.line(xy, fill=COLORS.get(kind, (0, 150, 0)), width=max(1, int(0.4 * pixels_per_mm)))
        panels.append(img)
    sheet = Image.new("RGB", (w * len(panels) + 6 * (len(panels) - 1), h + 20), "white")
    for i, panel in enumerate(panels):
        sheet.paste(panel, (i * (w + 6), 0))
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
