# Arquitectura (derivada del análisis de Rainmeter 4.5.28 con REA)

Copia analizada: `~\tools\rainmeter_ref`. Respaldo de tus skins y config originales: `~\tools\rainmeter_user_backup`.

## Qué se pudo establecer
- **Limitación:** el proveedor de decompilación (Ghidra) agotó su tiempo de arranque (330 s) con `Rainmeter.dll` (2.6 MB) en este equipo.
  Los datos de abajo salen de un escaneo estático de cadenas e imports del propio binario, no de decompilación.
  Para ir más hondo hay que subir `REA_GHIDRA_STARTUP_TIMEOUT_MS` o desactivar analizadores pesados.
- **Binarios:** `Rainmeter.exe` (468 KB, lanzador), `Rainmeter.dll` (2.6 MB, motor), `SkinInstaller.exe`, `RestartRainmeter.exe`,
  18 plugins DLL (ActionTimer, AdvancedCPU, AudioLevel, CoreTemp, FileView, FolderInfo, InputText, iTunes, PerfMon, Ping,
  Power, Quote, ResMon, RunCommand, SpeedFan, UsageMonitor, Win7Audio, WindowMessage).
- **Dibujo:** imports de `gdiplus`, `d2d1`, `d3d11`, `DWrite`, `dwmapi`, `UxTheme`; cadena `UpdateLayeredWindow`
  (ventanas por capas con transparencia por píxel) y `DwmEnableBlurBehindWindow`.
- **Ventana:** `SetWindowPos` (z-order al fondo), opciones `Draggable`, `SnapEdges`, `KeepOnScreen`, `ClickThrough`,
  `DynamicWindowSize`; cadenas `Progman`/`WorkerW`/`SHELLDLL_DefView` para anclar al escritorio.
- **Modelo de skins:** archivos `.ini` con secciones `[Measure…]` (65 menciones, datos) y `[Meter…]` (37, dibujo: String, Bitmap,
  Shape…), acciones (`LeftMouseUpAction`, `MouseOverAction`, `OnRefreshAction`) y "bangs" (`!ActivateConfig`, `!Move`, `!Refresh`).
- **Estado:** `Rainmeter.ini` por usuario; skins en `Documents\Rainmeter\Skins`, recursos en `@Resources`.
- **Sesión:** `WTSRegisterSessionNotification` (reacciona a bloqueo/cambio de sesión), `WININET` (medidas web), `WINMM` (audio).

## Qué replica AuraDesk v0.1
| Rainmeter | AuraDesk |
|---|---|
| Ventanas por capas al fondo | Toplevel sin borde, `-transparentcolor`, `HWND_BOTTOM`, `WS_EX_TOOLWINDOW` |
| `[Measure]` CPU/RAM/Disk | `GetSystemTimes`, `GlobalMemoryStatusEx`, `shutil.disk_usage` (ctypes, sin psutil) |
| `[Meter]` String/Shape | Canvas de tkinter (polígono redondeado, barras, texto) |
| `Draggable` + `Rainmeter.ini` | Arrastrar y guardar posición en `%LOCALAPPDATA%\AuraDesk\config.json` |
| `LeftMouseUpAction` | `on_click()` por widget (el botón ejecuta `claude-widget.ps1`) |

No replica aún: skins declarativos `.ini`, plugins, multi-monitor, blur DWM, pantalla completa/bloqueo de sesión, redes.

## Hoja de ruta
1. Cargador de skins declarativos (JSON/TOML) en vez de clases fijas.
2. Pausa/ocultación cuando hay pantalla completa (reutilizar la lógica de AuraWall).
3. Widgets de red, papelera y disco extra (equivalentes a los `illustro` de Rainmeter).
4. Integrar con AuraWall en un único proceso "AuraShell".
