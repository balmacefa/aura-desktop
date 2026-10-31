# Aura architecture

## Package layout
```
src/aura/
  cli.py       command-line entry (doctor, status, scene, scenes, video, palette, config, update, quit, logs, version)
  ui.py        settings panel (Summary, Background, Colours, Widgets, General) and first-run welcome
  desk.py      desktop widgets (clock, system, calendar, battery, Pomodoro, network, Claude Code button)
  live.py      Aura Live: wallpaper engine, local server, Edge/Godot hosting
  win.py       Win32 helpers: Progman embedding, layered windows, fades, covered detection
  update.py    update check against GitHub Releases (HTTPS, github.com only, SHA-256)
  tray.py      tray icon and quick actions
  config.py    validated, atomically written configuration
  state.py     runtime state shared between processes
  i18n.py      translations (English / Spanish)
  fonts.py     bundled Inter typeface
  autostart.py start with Windows
  procs.py     process launching and control
  log.py       rotating log in %LOCALAPPDATA%\Aura\logs
  paths.py     resolves bundled assets vs user data
  assets/
    scenes/  web scenes (.html)
    lib/     aura.js (scene contract)
    media/   video wallpapers
    godot/   3D scene project/export
    fonts/
    icons/
    locales/ en/es JSON texts
    scripts/
```
Other top-level folders: `tests/` (unittest), `tools/bench` (benchmark with quality gates), `tools/devtools`, `branding/`, `site/` (GitHub Pages) and `scripts/build.py` (PyInstaller onedir + Inno Setup).

## Data locations
- Program and assets: install folder (per user, no administrator).
- User data in `%LOCALAPPDATA%\Aura`: `aura.json`, `logs\aura.log`, `media\` (your videos) and `updates\`.
- Temporary Edge profiles: system temp, deleted when the wallpaper stops.

## Processes by role
A single executable, `Aura.exe`, started with `--role <name>`: for example `ui`, `desk`, `wall`/`live`, `tray`. Roles are independent processes so a crash in one does not take down the others.

## How it works
- **Wallpaper behind icons.** The wallpaper window is made a child of `Progman`, between `SHELLDLL_DefView` and `WorkerW`, with `WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE` applied before `SetParent`. Progman is `NOREDIRECTIONBITMAP`, so only GPU-composed content shows (Edge, Godot on D3D12, ffplay on Direct3D 11).
- **Bridge `/state`.** Progman does not deliver mouse input to the wallpaper, so a local server on `127.0.0.1` (random port) exposes `/state` (cursor, button, click counter, CPU, RAM, battery, hour). Scenes poll it through `aura.js`: persistent HTTP/1.1, slow values cached, one poll per frame (about 9 requests/s idle). Only `/scenes`, `/lib`, `/state` are served; `Host` is validated; CSP `connect-src 'self'`.
- **Fades and handover.** Switching wallpapers starts a new daemon with a transparent window, lets it settle, fades it in over about 0.9 s on top, and only then publishes its PID to the state file; the previous daemon sees `handed_over` and exits. Windows' own wallpaper is never visible between scenes. Disabled when Windows "Show animations" is off.
- **Pause with a window on top.** If any visible window covers the work area, the wallpaper hides; Godot and video processes are frozen and widgets stop updating (the daemon marks `covered` in its state). Low battery (<30 %) also pauses.
- **Atomic state.** Config and state are written to a temporary file then `os.replace`; unreadable JSON is kept as `.bad`.

## Updates
`update.py` queries the GitHub Releases API once a day, downloads only when the user clicks Update, accepts only `Aura-Setup-X.Y.Z.exe` over HTTPS from `github.com`, and verifies its SHA-256 against `SHA256SUMS.txt`. See [ROADMAP.md](../ROADMAP.md) for what comes next.
