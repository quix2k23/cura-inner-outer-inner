Plate Autosave: Cura remembers the models on the build plate across restarts. On top of 1.2.0 (faster slicing, quicker settings panel) and 1.1.0 (inner/outer/inner walls, bone infill, arc fitting).

- **Plate Autosave.** The build plate is saved every 5 minutes and when Cura quits, and the models come back, in the same places and with their per-model settings, when Cura starts. Turn it on or off and set the interval (1 to 1440 minutes) in *Preferences > General > Opening and saving files*. Each save is checked before it replaces the previous one, which is kept as a backup. Only models are saved, not the printer or print profile, and only the active build plate. See the [README](https://github.com/quix2k23/cura-inner-outer-inner#plate-autosave).
- **From 1.2.0**, not released separately: infill-heavy parts slice about 25 to 28 % faster, and choosing the *All* visibility preset shows the settings panel at once instead of after about 10 s.

**Install or update:** download the archive for your system below, unpack it, close Cura and run `install.sh` (Linux) or `install.bat` (Windows). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#install). Running the installer again over an earlier version updates it.

- `cura-inner-outer-inner-5.13.0-linux-x86_64.tar.gz`: for the Cura Flatpak, AppImage or distro packages
- `cura-inner-outer-inner-5.13.0-windows-x64.zip`: for the Windows installer version of Cura

Modified builds show as `5.13.0 (ioi 1.3.0)` on the splash screen and in the About dialog; Cura itself still sees 5.13.0.

Built from CuraEngine 5.13.0 plus the changes in this repository (AGPL-3.0). The Windows package passes the automated tests but has not been tried in a real Windows Cura yet, and Plate Autosave has only been tried in Cura on Linux. Unofficial and not affiliated with UltiMaker.
