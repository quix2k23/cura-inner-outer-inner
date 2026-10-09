# Inner/Outer/Inner walls for UltiMaker Cura

Adds a third choice, **Inner/Outer/Inner**, to Cura's **Wall Ordering** setting (Cura 5.13). It prints the outer wall *sandwiched* between the walls inside it, the same idea as the "Inner-Outer-Inner" wall sequence in OrcaSlicer.

Cura itself only offers two orders: *Inside To Outside* and *Outside To Inside*. This project is a small patch to **CuraEngine** (the slicing engine), a Cura plugin that adds the new choice to the settings panel, and installers for Linux and Windows that put both on top of a normal Cura 5.13 install.

## What it does

With **Inner/Outer/Inner** selected, each layer's walls are printed in this order:

| Walls per layer | Print order |
|---|---|
| 4 | wall 3, wall 2, **outer wall**, wall 1 |
| 3 | wall 2, **outer wall**, wall 1 |
| 2 | **outer wall**, wall 1 |
| 1 | outer wall |

(wall 0 is the outer wall, wall 1 the one just inside it, and so on.)

The outer wall is laid down against walls that are already in place, and wall 1 is then printed against it. The point is to get a more consistent outer surface and better dimensional control than printing the outer wall first or last. How much that helps depends on your printer, filament and speeds, so try it on a test part before relying on it. I have not done a systematic print-quality comparison.

Details and limits:

- With **two walls or fewer** there is nothing to sandwich with, so it prints the outer wall first, then the inner one (OrcaSlicer does the same).
- It applies to the **Wall Ordering** setting. The first layer follows Cura's separate **Initial Layer Wall Ordering** setting, which is unchanged.
- It only applies when the outer wall and the inner walls use the **same extruder**. With different extruders it falls back to *Inside To Outside*.
- **Group Outer Walls** has no effect in this mode (that option assumes the outer walls are at the start or end of the order).
- Works with both "Optimize Wall Printing Order" on and off.
- If you pick the new option while using Cura's *own* engine, Cura silently treats it as *Inside To Outside*. You need the patched engine from this project for it to take effect.

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

### Use it

Start Cura, open **Print Settings**, search for **Wall Ordering** and choose **Inner/Outer/Inner**. Slice a part with three or more walls and check the layer view: the outer wall should come second to last.

### What the installer does

1. Copies the patched engine to a folder next to Cura's settings (`.../cura-inner-outer-inner`).
2. Checks that the engine runs. If it does not, **nothing else is changed**.
3. Copies the plugin to Cura's `plugins/InnerOuterInnerWalls` folder.
4. Backs up `cura.cfg` (as `cura.cfg.bak-inner-outer-inner`) and adds one line, `location = <path to the engine>`, under `[backend]`. That is the standard Cura preference for choosing the slicing engine.

### Uninstall

Close Cura and run `uninstall.sh` (Linux) or `uninstall.bat` (Windows). It removes the plugin, deletes the engine and removes that one line from `cura.cfg`. If a saved profile still says Inner/Outer/Inner, set Wall Ordering back before you slice.

## How it was tested

- **Wall order:** `tests/test_wall_order.py` slices a ring-shaped part and checks the order of the printed walls (2, 3 and 4 walls, plus "Inside To Outside" unchanged). The build runs it on the packaged engine for **both Linux and Windows**, so every release has passed it on both.
- **Installers:** the install and uninstall scripts are run on both systems against a throwaway Cura settings folder, including running the installer twice and checking that uninstall restores `cura.cfg` exactly.
- **In Cura (Linux):** tried by the author in Cura 5.13.0 (Flatpak): the option shows in the Wall Ordering dropdown, and the sliced G-code has the walls in the expected order. The Linux engine from the build also starts inside the Cura Flatpak sandbox.
- **In Cura (Windows):** the Windows engine and scripts pass the automated tests above, but the package has **not yet been tried inside a real Windows Cura install** by the author. If something goes wrong there, please open an issue.

## Updates

The engine is built from CuraEngine **5.13.0** and is meant for Cura 5.13.x. When Cura updates to a new version, the engine from this project is no longer matched to it: uninstall, then check whether a new release is available here. (The change itself is small and carries over to new CuraEngine versions easily.)

## What changed in the source

The full CuraEngine source is in [`curaengine/`](curaengine). The history is arranged so the change is easy to see:

1. [`Import unmodified CuraEngine 5.13.0`](../../commits/main) is the upstream tree exactly as released.
2. [`CuraEngine: add inner/outer/inner (sandwich) wall ordering`](../../commits/main) is the whole change: four files, about 60 added lines.

| File | Change |
|---|---|
| `include/settings/EnumSettings.h` | new `InsetDirection::INNER_OUTER_INNER` |
| `src/settings/Settings.cpp` | parses the setting value `inner_outer_inner` |
| `include/InsetOrderOptimizer.h`, `src/InsetOrderOptimizer.cpp` | the new ordering constraints for both wall-ordering code paths, the single-extruder fallback, and ignoring *Group Outer Walls* |

The Cura side is the plugin in [`plugin/InnerOuterInnerWalls`](plugin/InnerOuterInnerWalls). It adds `inner_outer_inner` to the options of the `inset_direction` setting using Cura's own `extend_category` call.

`tests/test_wall_order.py` slices a ring-shaped part and checks the printed wall order for 2, 3 and 4 walls. The build runs it against the packaged engine on both Linux and Windows.

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
python ../tests/test_wall_order.py out/build/Release/CuraEngine
```

The first build compiles all dependencies (Boost, gRPC, protobuf, ...) and takes a while on a typical machine.

## Licence and credits

- CuraEngine is © UltiMaker and licensed under the **AGPL-3.0-or-later**. This repository, including the plugin and scripts, is distributed under the same licence (see [`LICENSE`](LICENSE)). The complete source of the binaries in the releases is in this repository.
- The wall order is modelled on the Inner-Outer-Inner behaviour of [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer); the code here is a separate implementation written for CuraEngine's wall-ordering code.
- This is an independent, unofficial modification. It is **not affiliated with or supported by UltiMaker**; "Cura" and "UltiMaker" are their trademarks. Please do not report problems with this build to UltiMaker.
