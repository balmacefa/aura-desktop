# Third-party notices

Aura itself is MIT-licensed (see `LICENSE`). The Windows installer and portable build also contain the following third-party components.

| Component | Used for | License |
|---|---|---|
| [Inter](https://rsms.me/inter/) (static TTF files in `src/aura/assets/fonts/`) | User-interface typeface | SIL Open Font License 1.1 — full text in `src/aura/assets/fonts/OFL-Inter.txt` |
| [Python](https://www.python.org/) runtime and standard library | Runs Aura | PSF License Agreement |
| [Tcl/Tk](https://www.tcl.tk/software/tcltk/license.html) (via Python's `tkinter`) | Settings window and widgets | Tcl/Tk (BSD-style) license |
| [PyInstaller](https://pyinstaller.org/) bootloader | Builds `Aura.exe` | GPL-2.0 with the PyInstaller bootloader exception (permits non-GPL applications) |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | Builds the installer | Inno Setup License (free, permits redistributing the generated installers) |

Not bundled (used if already present on your PC): Microsoft Edge or Google Chrome (renders the wallpapers) and Godot Engine (optional 3D scene; MIT).

The names "Windows", "Microsoft Edge", "Chrome", "Godot" and "Claude Code" belong to their respective owners; Aura is not affiliated with or endorsed by them.
