# Arquitectura (derivada del análisis de Lively 2.2.1 con REA)

Análisis estático (sin ejecutar código) de la copia en `~\tools\lively_ref`. Lively es de código abierto (GPLv3):
AuraWall reimplementa solo las **ideas**, con código propio; si algún día se copia código de Lively hay que respetar la GPL.

## Cómo está hecho Lively
| Pieza | Evidencia | Qué hace |
|---|---|---|
| `Lively.exe` / `Lively.dll` (.NET 9, 1623 miembros) | metadatos PE/CLI | Motor: ciclo de vida de fondos, monitores, reglas de pausa |
| `Lively.Common.dll` | cadenas `Progman`, `WorkerW`, `SHELLDLL_DefView`, `SendMessageTimeout`, `SetParent` | Inserta el reproductor tras los iconos del escritorio |
| `Plugins\Mpv\mpv.exe` | binario incluido | Reproductor de vídeo (proceso aparte) |
| `Plugins\WebView2\Lively.Player.WebView2.exe` | binario incluido | Reproductor de páginas HTML (proceso aparte) |
| `Plugins\UI\Lively.UI.WinUI.exe` | binario incluido | Interfaz WinUI, proceso aparte |
| `Lively.Grpc.*` + `GrpcDotNetNamedPipes` | cadenas `NamedPipe`, `PipeClient` | IPC por tuberías con nombre entre UI y motor |
| `Plugins\Watchdog` | binario incluido | Vigila y reinicia procesos |
| Tipos `PauseRule`, `DisplayCoveredByWindow*`, `Screensaver*`, `DesktopSlideshow*` | nombres de tipos | Pausa por ventana que cubre el monitor, salvapantallas, presentación |
| P/Invoke: `user32!SetWindowCompositionAttribute`, `Kernel32!GetUserPreferredUILanguages` | `ImplMap` | Solo cosmética de la UI; el resto va por Windows SDK projection |

## Técnica de incrustación (WorkerW)
1. `FindWindow("Progman")`.
2. `SendMessageTimeout(progman, 0x052C, ...)` para que el shell cree la capa `WorkerW`.
3. Localizar `WorkerW`: hijo de Progman (Win11 24H2+) o hermano posterior al que contiene `SHELLDLL_DefView` (anteriores).
4. `SetParent(reproductor, WorkerW)`, estilo `WS_CHILD`, ajustar al tamaño de pantalla.

## Qué replica AuraWall (v0.1) y qué no
- Sí: pasos 1-4, reproductor externo (ffplay), pausa por pantalla completa y por batería, start/stop/status.
- No aún: varios monitores, HTML/WebView2, interfaz gráfica, galería, IPC, watchdog, arranque con Windows.

## Hoja de ruta
1. Multi-monitor (EnumDisplayMonitors, un reproductor por pantalla).
2. Reproductor HTML con WebView2 (Edge runtime ya instalado) para fondos interactivos.
3. Interfaz mínima en bandeja (pystray o WinUI) y pausa/volumen.
4. Fondos propios del estilo "sorpresa" (shaders/partículas en HTML).
