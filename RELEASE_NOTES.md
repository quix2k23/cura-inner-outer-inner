For **Cura 5.14**: the engine is rebuilt on CuraEngine 5.14.0, plus one fix. On top of 1.3.1 (Plate Autosave fix), 1.3.0 (Plate Autosave), 1.2.0 (faster slicing, quicker settings panel) and 1.1.0 (inner/outer/inner walls, bone infill, arc fitting).

- **Cura 5.14:** the engine of 1.3.1 was built for Cura 5.13. Cura 5.14 rejects it: slicing starts over and over and never finishes. This release is built from CuraEngine 5.14.0, and the installers now use the Cura 5.14 settings folder. Use 1.3.1 if you stay on Cura 5.13.
- **Fixed:** with "Retract Before Outer Wall" set to Always, inner/outer/inner with two walls now also retracts at layer changes (with two walls it prints the outer wall first, like Outside To Inside).
- **From 1.3.0 and 1.3.1:** Plate Autosave saves the build plate every 5 minutes and when Cura quits, and restores it when Cura starts (not when Cura is started by opening a model file). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#plate-autosave).


**Install or update:** download the archive for your system below, unpack it, close Cura and run `install.sh` (Linux) or `install.bat` (Windows). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#install). Running the installer again over an earlier version updates it.

- `cura-inner-outer-inner-5.14.0-linux-x86_64.tar.gz`: for the Cura Flatpak, AppImage or distro packages
- `cura-inner-outer-inner-5.14.0-windows-x64.zip`: for the Windows installer version of Cura

Modified builds show as `5.14.0 (ioi 1.4.0)` on the splash screen and in the About dialog; Cura itself still sees 5.14.0.

Built from CuraEngine 5.14.0 plus the changes in this repository (AGPL-3.0). The Windows package passes the automated tests but has not been tried in a real Windows Cura yet, and Plate Autosave has only been tried in Cura on Linux. Unofficial and not affiliated with UltiMaker.
