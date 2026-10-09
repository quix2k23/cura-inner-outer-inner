# Better walls, bone-like infill and arcs for UltiMaker Cura

Three additions for **UltiMaker Cura 5.13**, as a patched slicing engine (CuraEngine) plus a small Cura plugin and installers for Linux and Windows:

| Feature | What it does | Where it shows up in Cura |
|---|---|---|
| [**Inner/Outer/Inner walls**](#innerouterinner-walls) | Prints the outer wall sandwiched between the walls inside it, like OrcaSlicer's wall sequence of the same name | *Wall Ordering* setting |
| [**Bone infill**](#bone-infill) | A new infill pattern that imitates spongy (trabecular) bone: a connected network of thin plates and rods, lined up with a direction you choose, denser near the walls | *Infill Pattern* setting, with its own settings under it |
| [**Arc fitting**](#arc-fitting-g2g3) | Writes curves as G2/G3 arcs instead of many tiny straight moves: much smaller G-code and smoother motion | *Experimental* settings |

This is an independent, unofficial modification and is not affiliated with UltiMaker. Everything is opt-in: with the default settings Cura slices exactly as before.

## Install

You need **UltiMaker Cura 5.13** installed and started at least once. Download the archive for your system from the [latest release](../../releases/latest), unpack it, and **close Cura** before running the installer. Nothing in Cura's own install folder is modified.

### Linux (Flatpak, AppImage or distro package)

```sh
tar xzf cura-inner-outer-inner-5.13.0-linux-x86_64.tar.gz
cd cura-inner-outer-inner-5.13.0-linux-x86_64
./install.sh
```

The script finds your Flatpak or native Cura settings folder by itself. Use `--flatpak` or `--native` if you have both, or `--data-dir DIR` for a custom location. For the Flatpak it needs no extra permissions: the engine is placed inside Cura's own data folder.

### Windows

1. Unzip `cura-inner-outer-inner-5.13.0-windows-x64.zip`.
2. Close Cura.
3. Double-click `install.bat` (or run `powershell -ExecutionPolicy Bypass -File install.ps1`).

### Find the settings

Start Cura and use the search box in **Print Settings** (it is the quickest way):

- search **Wall Ordering**: choose *Inner/Outer/Inner*
- search **Infill Pattern**: choose *Bone*; the bone settings appear right below it
- search **Arc Fitting**: turn it on (read [the firmware notes](#arc-fitting-g2g3) first)

The new settings are added to Cura's visibility list automatically. The plugin only offers a feature when the installed engine supports it (the engine carries a small `FEATURES` file), so the settings can never ask a stock engine for something it does not know.

### What the installer does

1. Copies the patched engine to a folder next to Cura's settings (`.../cura-inner-outer-inner`).
2. Checks that the engine runs. If it does not, **nothing else is changed**.
3. Copies the plugin to Cura's `plugins/InnerOuterInnerWalls` folder.
4. Backs up `cura.cfg` (as `cura.cfg.bak-inner-outer-inner`) and adds one line, `location = <path to the engine>`, under `[backend]`. That is the standard Cura preference for choosing the slicing engine.

### Uninstall

Close Cura and run `uninstall.sh` (Linux) or `uninstall.bat` (Windows). It removes the plugin, deletes the engine and removes that one line from `cura.cfg`. If a saved profile still says *Bone* or *Inner/Outer/Inner*, change the setting back before you slice with Cura's own engine: an unpatched engine treats an unknown infill pattern as "no infill".

## Inner/Outer/Inner walls

With **Inner/Outer/Inner** selected in *Wall Ordering*, each layer's walls are printed in this order:

| Walls per layer | Print order |
|---|---|
| 4 | wall 3, wall 2, **outer wall**, wall 1 |
| 3 | wall 2, **outer wall**, wall 1 |
| 2 | **outer wall**, wall 1 |
| 1 | outer wall |

(wall 0 is the outer wall, wall 1 the one just inside it, and so on.)

The outer wall is laid down against walls that are already in place, and wall 1 is then printed against it. The idea is a more consistent outer surface and better dimensional control than printing the outer wall first or last. How much that helps depends on your printer, filament and speeds, so try it on a test part. I have not done a systematic print-quality comparison.

- With **two walls or fewer** there is nothing to sandwich with, so it prints the outer wall first, then the inner one (OrcaSlicer does the same).
- The first layer has its own **Initial Layer Wall Ordering** setting, which offers *Inner/Outer/Inner* as well. By default it follows *Wall Ordering*, so choosing Inner/Outer/Inner for the walls applies it to the first layer too; set the initial layer one to something else if you want the first layer printed differently.
- It only applies when the outer wall and the inner walls use the **same extruder**; otherwise it falls back to *Inside To Outside*.
- **Group Outer Walls** has no effect in this mode.
- It works with "Optimize Wall Printing Order" on and off.

## Bone infill

Spongy bone is a connected network of thin plates and rods. The struts line up with the direction of the load the bone carries, and the network gets denser towards the hard outer shell. The **Bone** infill pattern imitates that:

- The structure is the level surface of a smooth random 3D field, a sum of 64 cosine waves (the idea behind bone-like "spinodoid" structures, see e.g. Kumar et al., *Inverse-designed spinodoid metamaterials*, npj Computational Materials, 2020). The result is an irregular, organic network of connected plates, not a repeating cell.
- **Alignment:** the directions of the waves decide how the structure is oriented. Waves mostly perpendicular to the main direction give struts that run along it. At 0 % the structure is the same in every direction; at high values it turns into upright, branching struts with a few cross-links, like the trabeculae in a vertebra.
- **Layer to layer:** the field is continuous, so the pattern changes smoothly between layers and each layer is supported by the one below it. In the automated test 99 % of the infill of a layer has infill directly below it.
- **Density:** the scale is calibrated so that the amount of infill follows the *Infill Line Distance* (and so the *Infill Density*) like for the other patterns. The test measures it within a few percent.
- **Dense zone:** next to the walls, extra struts are added beside every strut, like the thickening towards the cortical shell of a bone.

### Settings

They appear under *Infill Pattern* when *Bone* is selected.

| Setting | Range (default) | Effect |
|---|---|---|
| Bone Structure Seed | 0 to 99999 (1) | Picks one of the many possible structures. The same number always gives the same one. |
| Bone Alignment | 0 to 97 % (60) | How strongly the struts follow one main direction. 0 = same in every direction. |
| Bone Alignment Tilt | 0 to 90° (0) | Tilts the main direction away from vertical (0 = straight up). |
| Bone Alignment Direction | 0 to 360° (0) | The direction in the layer plane the tilt leans towards. |
| Bone Irregularity | 0 to 100 % (40) | How much strut thickness and spacing vary. Low = regular, high = organic. |
| Bone Connectivity | 0 to 100 % (100) | 100 % = one fully connected network. Lower = separate cells and rods with gaps, lighter and more porous but weaker. |
| Bone Dense Zone Width | 0 to 20 mm (3) | Width of the denser zone along the walls. 0 turns it off. |
| Bone Dense Zone Struts | 0 to 3 (1) | Extra struts on each side of every strut in that zone. |

Cura's own **Infill Density / Line Distance** sets how much infill there is, and **Infill Line Direction** rotates the whole structure.

Tips: for a part that is loaded along its vertical axis try alignment 60 to 80 with tilt 0. Struts that are close to vertical are also the most reliable to print. For a lighter, more porous part lower the connectivity. Try a few seeds on a test part and keep the one you like.

Limits: this is meant to imitate the *structure* of bone. The strength of printed parts has not been measured, so do not assume it is stronger than another pattern. Slicing is slower than for simple patterns: about 40 s instead of 4 s for a 150 x 150 x 30 mm part on a 12-core desktop; for typical part sizes the difference is a second or two.

## Arc fitting (G2/G3)

Slicers normally describe curves as many tiny straight moves. With **Arc Fitting** on, runs of moves that lie on one circle are written as a single G2 (clockwise) or G3 (counter-clockwise) arc. The G-code gets about 3 to 4 times smaller on curved parts, which means less to upload and parse, and the slicer's many-sided polygons are replaced by exact circles. Note that firmware such as Klipper and Marlin still splits an arc into very short straight moves internally, so the motion itself is not different in kind; do not expect a big change in surface quality.

The idea and the acceptance rules are taken from the arc fitting in OrcaSlicer (itself derived from ArcWelder): keep adding points to a candidate arc while one circle still passes within the tolerance of every point and the points keep turning the same way, and take the longest arc that fits. On top of that, an arc is rejected if it would bulge away from the original path between two points, so corners are never rounded off.

**Your printer firmware must understand arcs, or the print will fail:**

- **Klipper:** add a `[gcode_arcs]` section to `printer.cfg` (without it Klipper rejects G2/G3 as unknown commands). The step-by-step guide, with a safe test and troubleshooting, is in [docs/klipper-arc-gcode.md](docs/klipper-arc-gcode.md). The short version:
  ```
  [gcode_arcs]
  resolution: 0.1
  ```
- **Marlin:** build it with `ARC_SUPPORT` (it is on in most configurations).
- Arcs are only written for the *Marlin*, *Marlin (Volumetric)*, *RepRap* and *Repetier* G-code flavors, and only for flat moves at a constant height. Paths that are printed with *coasting* are written as straight lines.

| Setting | Range (default) | Effect |
|---|---|---|
| Arc Fitting | on/off (off) | Turns the feature on. |
| Arc Fitting Tolerance | 0.005 to 1 mm (0.05) | The largest distance an arc may deviate from the original path. Larger = more arcs and smaller G-code. |
| Arc Fitting Maximum Radius | 1 to 100000 mm (1000) | Larger arcs are written as straight lines. |

The extruded amount follows the arc's real length. Cura's live layer view after slicing is unchanged (it shows the original path), but Cura's G-code *file* viewer does not handle G2/G3 (checked in its source), so a finished `.gcode` file opened in Cura will look incomplete there; other viewers vary.

## How it was tested

Every build runs these checks on the packaged engine, on **both Linux and Windows**:

- `tests/test_wall_order.py`: the printed wall order for 2, 3 and 4 walls, that "Inside To Outside" is unchanged, and that the first layer follows *Initial Layer Wall Ordering* while the other layers follow *Wall Ordering*.
- `tests/test_arcs.py`: a round part is sliced with and without arcs. The arcs must stay within the tolerance of the original path (measured 0.036 mm for a 0.05 mm tolerance), extrude the same material (within 0.05 %), have matching start and end radius for the firmware, and make the G-code at least 40 % smaller (measured 3.3 times smaller).
- `tests/test_bone_infill.py`: the infill length follows the line distance (the test allows 15 %; measured within 5 %), the same seed gives identical G-code and another seed a different one, 99 % of the infill is supported by infill below it, alignment makes the struts upright (99 % of the points line up with the layer below vs 62 % without alignment), the infill stays inside the walls, and the dense zone adds infill near the walls but not in the middle.
- The install and uninstall scripts are run against a throwaway Cura settings folder, including running the installer twice and checking that uninstall restores `cura.cfg` exactly.
- The arc fitting was also replayed with the exact settings Cura sent to the engine for a real Klipper printer profile: 3,511 arcs, deviation 0.040 mm, extruded amount within 0.07 %, file size halved.

By hand, in Cura 5.13.0 (Flatpak on Linux): the new options and all the new settings appear for the printer, the sliced G-code has the expected wall order, and the bone infill and arcs were checked by rendering layers and vertical sections of the sliced G-code. The Windows package passes the automated tests above but has **not yet been tried inside a real Windows Cura install**. Printed parts made with the bone infill or with arcs have not been checked yet, so print quality and strength are unverified; please open an issue if you find problems.

## Version label

The splash screen and the About dialog of a modified Cura show the version as **`5.13.0 (ioi 1.1.0)`**: the Cura version it is based on, then the version of this add-on. In file names and release names the same thing is written `5.13.0+ioi.1.1.0` (everything after the `+` is "build metadata" in SemVer and Python's version rules, which marks a modified build without changing which release it is based on). Only those two places show the label. Cura itself still sees its real version (`5.13.0`) for backups, update checks and plugin compatibility. Official Cura 5.13.1 or 5.13.2 numbers are never used here, so a modified build cannot be mistaken for an official one.

## Updates

The engine is built from CuraEngine **5.13.0** and is meant for Cura 5.13.x. When Cura updates to a new version, the engine from this project is no longer matched to it: uninstall, then check whether a new release is available here.

## What changed in the source

The full CuraEngine source is in [`curaengine/`](curaengine). The history is arranged so each change is easy to see:

1. `Import unmodified CuraEngine 5.13.0`: the upstream tree exactly as released.
2. `CuraEngine: add inner/outer/inner (sandwich) wall ordering`: four files, about 60 added lines.
3. `CuraEngine: add arc fitting (G2/G3 output)`: new `ArcFitter` (`include/utils/ArcFitter.h`, `src/utils/ArcFitter.cpp`), a `GCodeExport::writeExtrusionArc` that writes G2/G3, the use of both in `LayerPlan::writeGCode`, and `Settings::hasRecursive`.
4. `CuraEngine: add a bone-like (trabecular) infill pattern`: new `BoneInfill` (`include/infill/BoneInfill.h`, `src/infill/BoneInfill.cpp`), and the plumbing for the `bone` pattern (`EFillMethod::BONE`, the settings parser, the infill dispatch, the line stitching list and bridging).

The Cura side is the plugin in [`plugin/InnerOuterInnerWalls`](plugin/InnerOuterInnerWalls). It adds the new option values with Cura's own `extend_category` call, adds the setting definitions from [`settings.def.json`](plugin/InnerOuterInnerWalls/settings.def.json) to the printer definition, and makes them visible.

## Development

Quick checks (script syntax, JSON and YAML, no personal data in the published files, and the install and uninstall scripts against a stand-in engine) run in about a second with `scripts/preflight.sh`, and on GitHub for every push (`checks` workflow). To run them automatically before each push: `git config core.hooksPath .githooks`. Pass `CURA_ENGINE=/path/to/CuraEngine` to the script to run the engine tests on a binary too. The release build (`build` workflow) takes much longer, so it only runs for version tags and when started by hand.

## Build from source

The release archives are built by [GitHub Actions](.github/workflows/build.yml). To build the engine yourself, use UltiMaker's Conan setup:

```sh
pip install "conan>=2.7,<3"
conan config install https://github.com/ultimaker/conan-config.git
conan profile detect --force
cd curaengine
conan build . --build=missing -pr:h=cura_build.jinja -pr:b=cura_build.jinja \
  -s build_type=Release -s compiler.cppstd=20 \
  -o "curaengine/*:enable_plugins=True" -o "curaengine/*:enable_arcus=True" \
  -c tools.build:skip_test=True -of out
for t in test_wall_order test_arcs test_bone_infill; do python ../tests/$t.py out/build/Release/CuraEngine; done
```

The first build compiles all dependencies (Boost, gRPC, protobuf, ...) and takes a while on a typical machine. `tests/render_layers.py` and `tests/render_section.py` draw layers and vertical sections of a G-code file as images, which is handy for looking at the infill.

## Licence and credits

- CuraEngine is © UltiMaker and licensed under the **AGPL-3.0-or-later**. This repository, including the plugin and scripts, is distributed under the same licence (see [`LICENSE`](LICENSE)). The complete source of the binaries in the releases is in this repository.
- The wall order and the arc fitting are modelled on the behaviour of [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) (AGPL-3.0); the code here is a separate implementation written for CuraEngine. The arc fitting follows the approach of [ArcWelder](https://github.com/FormerLurker/ArcWelderLib) as used by OrcaSlicer.
- "Cura" and "UltiMaker" are trademarks of UltiMaker. Please do not report problems with this build to UltiMaker.
