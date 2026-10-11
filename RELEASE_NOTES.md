Faster slicing and a settings panel that appears at once, on top of everything in 1.1.0 (inner/outer/inner walls, bone infill, arc fitting).

- **Faster slicing.** Infill-heavy parts slice noticeably faster: about 25 to 28 % on a large test part (about 6 s instead of 8 s), and 13.7 s down to 9.5 s for one slice in Cura. Parts with little infill gain only a few percent. The G-code is not changed: byte-for-byte identical for the test part on one thread; on a large model the previous engine does not always give the same file twice, so print time, layer count and move counts were compared there and match.
- **Settings panel.** Choosing the *All* visibility preset used to build about 700 setting widgets at once (about 10 s, with the interface frozen for several seconds). The plugin now collapses the setting categories when a preset with hundreds of settings is chosen, like *Collapse All Categories*, so the panel appears at once and each category opens in a fraction of a second. Basic, Advanced and Expert are unchanged. To turn it off, put `{"mode": "measure"}` in `settings_panel.json` in the plugin folder.

**Install or update:** download the archive for your system below, unpack it, close Cura and run `install.sh` (Linux) or `install.bat` (Windows). See the [README](https://github.com/quix2k23/cura-inner-outer-inner#install). Running the installer again over 1.1.0 updates it.

- `cura-inner-outer-inner-5.13.0-linux-x86_64.tar.gz`: for the Cura Flatpak, AppImage or distro packages
- `cura-inner-outer-inner-5.13.0-windows-x64.zip`: for the Windows installer version of Cura

Modified builds show as `5.13.0 (ioi 1.2.0)` on the splash screen and in the About dialog; Cura itself still sees 5.13.0.

Built from CuraEngine 5.13.0 plus the changes in this repository (AGPL-3.0). The Windows package passes the automated tests but has not been tried in a real Windows Cura yet. Unofficial and not affiliated with UltiMaker.
