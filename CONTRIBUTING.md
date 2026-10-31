# Contributing to Aura

Thanks for helping. Aura is MIT-licensed and maintained by [@balmacefa](https://github.com/balmacefa). By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development environment
Requires Windows 10/11, Python 3.10+ and Microsoft Edge.

```powershell
git clone https://github.com/balmacefa/aura-desktop.git
cd aura-desktop
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m aura ui         # run Aura from source
```

The code lives in `src/aura/` (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). To use the CLI from source: `python -m aura <command>`.

## Tests and benchmark
```powershell
python -m unittest discover -s tests
# benchmark with quality gates: see tools/bench and docs/RENDIMIENTO.md
```
The benchmark minimizes your windows, changes the wallpaper (and restores it) and needs the mouse to stay still. Run it plugged in. Open a PR that touches rendering or polling only with before/after numbers.

## Creating a new scene
A scene is one `.html` file in the scenes folder (`src/aura/assets/scenes/`) that loads `lib/aura.js` and registers a frame callback:

```html
<script src="/lib/aura.js"></script>
<script>
  const ctx = Aura.canvas().getContext('2d');
  Aura.onFrame((dt, s) => { /* draw */ });
</script>
```

The contract is documented at the top of `aura.js`. In short, the state `s` contains: cursor `x, y` (0..1), smoothed `sx, sy`, velocity `vx, vy`, `down`, `clicked` (true only on the frame of a click on the empty desktop), `cpu`, `ram` (0..1), `bat` (0..100), `hour`, `night` (0..1), `t`, `dt`, `w`, `h`, `dpr`. The palette is `Aura.pal` (4 `#rrggbb` colours: background, accent, secondary, tertiary); helpers `Aura.rgb(i)`, `Aura.mix`, `Aura.css`.

Rules for scenes:
- Colours come from `Aura.pal`, never hard-coded.
- No external requests (the CSP is `connect-src 'self'`) and no external assets or CDNs.
- Be cheap when idle: the library already drops to 30 fps when nothing moves; avoid per-frame allocations and measure with the benchmark.
- Test it by running Aura from source and choosing it with `python -m aura scene <name>`.
- It appears automatically in `scenes`. Contributed scenes are MIT-licensed like the rest.

## Commit style
[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `perf:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`. Subject in the imperative, up to 72 characters, English preferred. One logical change per commit.

## Pull request flow
1. Open an issue first for anything bigger than a small fix.
2. Fork, branch from `main` (`feat/my-scene`), commit.
3. Make sure tests pass and add tests for new logic.
4. Update `CHANGELOG.md` (Keep a Changelog) under *Unreleased*.
5. Open the PR using the template. CI must be green; the maintainer reviews and squash-merges.

## Adding a language
UI texts are in `src/aura/assets/locales/*.json` (English and Spanish today). To add one, see `src/aura/i18n.py`.

## Building the installer
```powershell
python scripts/build.py
```
This runs PyInstaller (onedir) and Inno Setup and produces `Aura-Setup-X.Y.Z.exe`, `Aura-portable-X.Y.Z.zip` and `SHA256SUMS.txt`. The release workflow (`.github/workflows/release.yml`) does the same and publishes to GitHub Releases when a `v*` tag is pushed. Brand assets are rebuilt with `python branding/build.py`; developer tools are in `tools/devtools`.
