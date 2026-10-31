First public release.

### Added
- **One-click installer** (`Aura-Setup-X.Y.Z.exe`, Inno Setup, English/Spanish, per-user, no administrator rights, ~12 MB) and a portable zip. No Python, ffmpeg or anything else to install: only Microsoft Edge, which ships with Windows 10/11 (Chrome works too).
- **Automatic updates** from GitHub Releases: one anonymous check per day, a banner and a tray notice, SHA-256 verification, strict HTTPS/host/file-name rules; can be turned off.
- **Tray icon** (open, pause/resume, switch wallpaper, start with Windows, check for updates, quit) and a **first-run welcome**.
- **English and Spanish** interface (follows the Windows language; selectable), Inter typeface bundled (SIL OFL), app icon and branding.
- **Gradient** wallpaper (palette-driven shader) and **video/GIF** wallpapers played by the browser (no ffmpeg).
- Settings reorganized in five tabs; update banner; start-with-Windows switch; open data folder / log.
- `Aura.exe doctor | status | scene | video | palette | config | update | quit | logs | version`.
- Open-source project setup: package layout (`src/aura`), 31 tests, CI, release workflow, website, contribution and security docs.

### Changed
- Config moved to `%LOCALAPPDATA%\Aura\aura.json` (single `scene` key; the 1.x format is migrated automatically).
- The Claude Code widget only appears when Claude Code is installed; the 3D crystals scene only when Godot 4 is installed.

### Removed
- ffmpeg/ffplay dependency and the generated gradient video.

---
Install: download **Aura-Setup-2.0.0.exe**, open it and follow the steps. Windows may show a SmartScreen notice because the installer is not code-signed yet: click *More info* then *Run anyway*. The checksums are in **SHA256SUMS.txt**.

Instalar: descarga **Aura-Setup-2.0.0.exe**, ábrelo y sigue los pasos. Windows puede mostrar un aviso de SmartScreen porque el instalador aún no está firmado: pulsa *Más información* y luego *Ejecutar de todas formas*.
