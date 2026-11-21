For **Cura 5.14**: fixes the engine crash report at exit. On top of 1.4.0 (Cura 5.14 build), 1.3.1 (Plate Autosave fix), 1.3.0 (Plate Autosave), 1.2.0 (faster slicing, quicker settings panel) and 1.1.0 (inner/outer/inner walls, bone infill, arc fitting).

- **Fixed:** CuraEngine could abort when it exited after Cura had already closed the connection ("terminate called without an active exception"). On Linux this showed up as a crash report for CuraEngine; the slice itself was fine. The cause is in UltiMaker's libArcus, and this release ships a patched copy. The fix is offered upstream in [libArcus #168](https://github.com/Ultimaker/libArcus/pull/168).
- **From 1.4.0:** built from CuraEngine 5.14.0 for Cura 5.14 (use 1.3.1 if you stay on Cura 5.13); inner/outer/inner with two walls now also retracts at layer changes when "Retract Before Outer Wall" is Always.
- **From 1.3.0 and 1.3.1:** Plate Autosave saves the build plate every 5 minutes and when Cura quits, and restores it when Cura starts (not when Cura is started by opening a model file). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#plate-autosave).


**Install or update:** download the archive for your system below, unpack it, close Cura and run `install.sh` (Linux) or `install.bat` (Windows). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#install). Running the installer again over an earlier version updates it.

- `cura-inner-outer-inner-5.14.0-linux-x86_64.tar.gz`: for the Cura Flatpak, AppImage or distro packages
- `cura-inner-outer-inner-5.14.0-windows-x64.zip`: for the Windows installer version of Cura

Modified builds show as `5.14.0 (ioi 1.4.1)` on the splash screen and in the About dialog; Cura itself still sees 5.14.0.

Built from CuraEngine 5.14.0 plus the changes in this repository (AGPL-3.0). The Windows package passes the automated tests but has not been tried in a real Windows Cura yet, and Plate Autosave has only been tried in Cura on Linux. Unofficial and not affiliated with UltiMaker.
