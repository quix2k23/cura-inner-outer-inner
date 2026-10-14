Fix for Plate Autosave: opening a model file now opens that file. On top of 1.3.0 (Plate Autosave), 1.2.0 (faster slicing, quicker settings panel) and 1.1.0 (inner/outer/inner walls, bone infill, arc fitting).

- **Fixed:** when Cura was started by opening a model file (for example double-clicking an STL in the file manager), the saved plate from the last session was loaded instead of that file. Plate Autosave now leaves the plate alone when Cura is started with files; a normal start still restores the saved plate.
- **From 1.3.0:** Plate Autosave saves the build plate every 5 minutes and when Cura quits, and restores it when Cura starts. See the [README](https://github.com/quix2k23/cura-inner-outer-inner#plate-autosave).


**Install or update:** download the archive for your system below, unpack it, close Cura and run `install.sh` (Linux) or `install.bat` (Windows). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#install). Running the installer again over an earlier version updates it.

- `cura-inner-outer-inner-5.13.0-linux-x86_64.tar.gz`: for the Cura Flatpak, AppImage or distro packages
- `cura-inner-outer-inner-5.13.0-windows-x64.zip`: for the Windows installer version of Cura

Modified builds show as `5.13.0 (ioi 1.3.1)` on the splash screen and in the About dialog; Cura itself still sees 5.13.0.

Built from CuraEngine 5.13.0 plus the changes in this repository (AGPL-3.0). The Windows package passes the automated tests but has not been tried in a real Windows Cura yet, and Plate Autosave has only been tried in Cura on Linux. Unofficial and not affiliated with UltiMaker.
