# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
el proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [2.0.0] - 2026-10-30

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

## [1.1.0] - 2026-10-30

### Rendimiento
- Coste en reposo con un fondo interactivo: de 126 % a 21 % de un núcleo; con una ventana maximizada encima, de 127 % a 0,4 %.
- El panel consulta el estado sin lanzar procesos (18 % de núcleo menos); `aura.py status` pasa de ~900 ms a ~100 ms.
- Puente del ratón con conexiones persistentes, estado lento en caché y consulta por fotograma; en reposo, 30 fps y ~9 consultas/s.
- El fondo se pausa cuando cualquier ventana visible cubre el área de trabajo (no solo la de primer plano a pantalla completa).
- Memoria de la escena web: ~1,1 GB → ~0,55 GB (opciones de Edge).
- Escritorio tapado: el fondo de Godot se congela (antes seguía dibujando oculto, 21 % de núcleo → 0,3 %) y los widgets dejan de actualizarse (0,5 % → 0).

### Añadido
- `bench/`: benchmark de rendimiento con puertas de calidad (incluida una comprobación de píxeles reales), `measure`, `decide` y `attribute`.
- `docs/RENDIMIENTO.md`: método, resultados y experimentos revertidos.

## [1.0.0] - 2026-10-30

### Añadido
- Punto de entrada único `aura.py` (status, start, stop, gen, install, uninstall, ui, scene, scenes, config, wallpaper, palette, speed, doctor, version, logs).
- AuraDesk: widgets de escritorio (botón Claude Code, reloj, sistema).
- AuraWall: fondo animado en vídeo tras los iconos del escritorio, compatible con Windows 11 24H2+ (hijo de Progman con `WS_EX_LAYERED` y render por GPU).
- Aura Live: fondos interactivos que reaccionan al ratón, clics y CPU. Escenas web (estela, constelacion, orbes, aurora, malla) y escena 3D opcional en Godot 4 (cristal).
- Transiciones suaves entre fondos (relevo con fundido, sin mostrar el fondo de Windows) que respetan el ajuste «Mostrar animaciones».
- Panel de ajustes (`aura.py ui`) con Resumen, Fondo, Colores, Widgets y General; atajos Ctrl+1 a 5 y Esc.
- Generación de degradados animados propios con paleta de 4 colores y velocidad ajustable (ffmpeg).
- `aura.py doctor` para diagnóstico y `aura.py logs` para localizar el registro.
- Configuración validada (`aura.json`) con escritura atómica.
- Instalador por usuario (`install.ps1`), desinstalador (`uninstall.ps1`) y script de empaquetado (`scripts/build-release.ps1`).

### Seguridad y privacidad
- Sin telemetría ni conexiones externas.
- El servidor local de Aura Live escucha solo en 127.0.0.1, con comprobación de la cabecera Host y CSP restringida.
- Edge se ejecuta en modo InPrivate, sin sincronización ni extensiones, con perfil temporal.

[1.0.0]: https://github.com/balmacefa/aura/releases/tag/v1.0.0
