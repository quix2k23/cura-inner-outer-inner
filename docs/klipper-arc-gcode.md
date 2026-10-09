# Using arc G-code (G2/G3) with Klipper

Cura's **Arc Fitting** setting (added by this project) writes curves as G2/G3 arc commands. Klipper does not understand them by default: without the steps below it stops with `Unknown command:"G2"` at the first arc. This guide shows how to enable them, how to check that they work, and how to choose the one setting involved.

## What to expect

Klipper accepts an arc, then **splits it into short straight moves** of at most `resolution` millimetres and runs those like any other G1 moves. So the motion your printer makes is not different in kind; the benefits are elsewhere:

- the G-code file is about 3 to 4 times smaller on curved parts (less to upload, store and parse);
- the slicer's many-sided polygons are replaced by exact circles, which Klipper then cuts into segments much finer than the slicer's own.

Do not expect a large change in surface quality. The setting is optional: with Arc Fitting off, Cura writes ordinary G1 moves and nothing here is needed.

## 1. Add the section to `printer.cfg`

Add this anywhere **above** the auto-generated block at the bottom of the file that starts with `#*# <--- SAVE_CONFIG --->` (everything below that line is rewritten by Klipper, so never put your own settings there):

```
[gcode_arcs]
resolution: 0.1
```

You can edit the file in Mainsail or Fluidd (Machine tab). If you prefer to keep it separate, put the two lines in a file called `arcs.cfg` next to `printer.cfg` and add `[include arcs.cfg]` to `printer.cfg`.

Back up `printer.cfg` first (in Mainsail: Machine, then the three dots on the file, then Download) so you can go back.

## 2. Restart Klipper

Use **Restart** (the `RESTART` command) in Mainsail or Fluidd. You do not need a firmware restart. Never restart in the middle of a print: it aborts the print.

If Klipper reports a config error, the usual cause is a typo in the section name (it is `gcode_arcs`, with an `s`) or the section placed below the `SAVE_CONFIG` block.

## 3. Check that it works

**a) The config was loaded.** On the Klipper host, this should print the two lines:

```sh
grep -a -A1 "^\[gcode_arcs\]" ~/printer_data/logs/klippy.log | tail -2
```

**b) A harmless test move.** In the Mainsail or Fluidd console, with nothing on the bed (adjust the numbers to your printer: the circle is drawn around the point you move to, so keep 10 mm clear all round). The arc commands only work in absolute mode, which `G90` sets:

```
G28
G90
G0 Z20 F600
G0 X110 Y110 F3000
G2 X110 Y110 I10 J0 F3000
```

The head should move in a full circle of 10 mm radius (a G2 whose end point is its start point is a full circle). If the console says `Unknown command:"G2"` the section is missing or Klipper has not been restarted since you added it.

**c) A real print.** In Cura turn on **Arc Fitting** (search for it in the print settings), slice a small round object, and check that the G-code really contains arcs:

```sh
grep -c "^G[23] " yourfile.gcode
```

Watch the first layers of the first arc print and keep a hand near the emergency stop, like for any new G-code.

## Choosing `resolution`

`resolution` is the length of the straight pieces an arc is cut into. The curve ends up slightly polygonal; the error between a piece and the true circle is about `resolution² / (8 × radius)`:

| resolution | radius 2 mm | radius 5 mm | radius 20 mm |
|---|---|---|---|
| 1.0 (Klipper's default) | 0.063 mm | 0.025 mm | 0.006 mm |
| **0.1 (recommended)** | 0.0006 mm | 0.0003 mm | 0.00006 mm |

Klipper's default of 1.0 mm is too coarse for small holes and tight curves, which is why this guide uses 0.1. A smaller value gives more, shorter moves for the host to plan. If you see stutter or `Timer too close` errors on a slow host while printing arcs, raise it to 0.2.

## Things that can go wrong

| Message or symptom | Cause and fix |
|---|---|
| `Unknown command:"G2"` | The `[gcode_arcs]` section is missing, misspelled, below the `SAVE_CONFIG` block, or Klipper was not restarted. |
| `G2/G3 does not support relative move mode` | The machine is in relative positioning (G91) when the first arc comes. Cura prints in absolute mode, so this means your start G-code or a macro left G91 on. Add `G90` at the end of the start G-code (and at the end of any macro that uses `G91`). |
| `G2/G3 does not support R moves` | Not from Cura, which always writes I and J. Another tool wrote a radius-style arc. |
| `G2/G3 requires IJ, IK or JK parameters` | A hand-written arc without a centre. Add `I` and `J`. |
| Circles look faceted | `resolution` is too large. Lower it. |
| A G-code preview does not show the arcs | Some viewers do not draw G2/G3. Cura's own G-code file viewer does not; its live layer view after slicing is not affected. |

## Other firmware

- **Marlin:** arcs need `ARC_SUPPORT` in `Configuration_adv.h` (on in most builds). The segment length is `MM_PER_ARC_SEGMENT`.
- **RepRapFirmware (Duet):** supports G2/G3 without extra configuration.

Check your firmware's documentation for the details of your version. Arcs are only written for the Marlin, Marlin (Volumetric), RepRap and Repetier G-code flavors that Cura offers; Klipper is normally used with the Marlin flavor.

## Undo

Delete the two lines (or the `arcs.cfg` include) and restart Klipper. In Cura, turn Arc Fitting off before slicing the next job; G-code that was already sliced with arcs needs the section in place.
