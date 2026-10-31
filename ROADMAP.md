# Roadmap

Items marked **Planned** do not exist yet. Order is indicative, not a promise.

## Done
### 1.x
- Wallpaper behind icons (Windows 11 24H2+), video and interactive scenes.
- Smooth fades and handover between wallpapers.
- Settings panel, `doctor`, validated configuration, rotating logs.
- Benchmark with quality gates; idle cost reduced from 126 % to 21 % of a core (0.3 % when covered).

### 2.0
- Package layout `src/aura/` and single executable `Aura.exe` (no Python needed; only Edge, which ships with Windows).
- `Aura-Setup-X.Y.Z.exe` installer (Inno Setup, per user, English/Spanish) and portable zip, built by a release workflow on `v*` tags and published with `SHA256SUMS.txt`.
- Update check against GitHub Releases (HTTPS, `github.com`, SHA-256), switchable off.
- Tray icon with quick actions, first-run welcome, Start with Windows.
- English/Spanish interface (i18n) with bundled Inter typeface.
- Scenes: Trail, Constellation, Orbs, Aurora, Wave mesh, Gradient, own video/GIF via Edge (no ffmpeg), and 3D Crystals (Godot 4, optional).
- Widgets: clock, system, calendar, battery, Pomodoro, network, Claude Code button.

## Later (Planned)
- Verify and fix Windows 10 and multi-monitor behaviour (currently tested only on Windows 11, one display).
- Pause when the session locks or the screen turns off; lower fps for slow scenes.
- Pause when a smaller window partially covers the desktop (known limit today).
- WebGL scenes, more scenes, community scene gallery.
- Declarative widget skins.
- Code signing and Microsoft Store listing.
- "Supporter" edition and scene packs (see [docs/MONETIZATION.md](docs/MONETIZATION.md)).
- Automated UI/integration tests.

Propose changes through a [feature request](https://github.com/balmacefa/aura-desktop/issues/new?template=feature_request.yml).
