Adds three things to Cura 5.13, all opt-in:

- **Inner/Outer/Inner** wall ordering: the deeper walls print first, then the outer wall, then wall 1 last (the "sandwich" order known from OrcaSlicer).
- **Bone** infill pattern: a connected, bone-like network of thin plates and rods that you can line up with a direction, with settings for alignment, irregularity, connectivity and a denser zone along the walls.
- **Arc fitting**: curves are written as G2/G3 arcs, which makes the G-code about 3 to 4 times smaller. Your firmware must support arcs (Klipper needs a `[gcode_arcs]` section).

**Install:** download the archive for your system below, unpack it, close Cura and run `install.sh` (Linux) or `install.bat` (Windows). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#install) for the settings, the firmware notes, the limits and how to undo it.

- `cura-inner-outer-inner-5.13.0-linux-x86_64.tar.gz`: for the Cura Flatpak, AppImage or distro packages
- `cura-inner-outer-inner-5.13.0-windows-x64.zip`: for the Windows installer version of Cura

Built from CuraEngine 5.13.0 plus the changes in this repository (AGPL-3.0). The Windows package passes the automated tests but has not been tried in a real Windows Cura yet. Unofficial and not affiliated with UltiMaker.
