# Estado de Aura (2026-10-28)

## Hecho
| Pieza | Estado |
|---|---|
| Monolito `~\tools\aura` | Consolidado: desk, wall, refs, backup, bridge, docs, `aura.py` |
| Lively y Rainmeter | Desinstalados; copias de referencia en `refs/` y respaldo de skins en `backup/` |
| REA sobre Lively (.NET) | Completado: arquitectura en `wall/docs/ARQUITECTURA.md` |
| REA sobre Rainmeter (nativo) | Parcial: Ghidra agotó 330 s; se usó escaneo de cadenas/imports (`desk/docs/ARQUITECTURA.md`) |
| AuraDesk (widgets) | **Instalado y funcionando** (menú Inicio, sin autostart): botón Claude Code, reloj, sistema |
| Fondo animado `wall/media/aura_flow.mp4` | Generado (20 s, 1500x1000, paleta Aura) con `aura.py gen` |
| `aura.py` | Operativo: status / start / stop / gen / install / uninstall |

## Pendiente
1. **AuraWall no pinta en este equipo (Win11 build 26200).** Verificado: `Progman` -> [`SHELLDLL_DefView`, `SDL_app` (player), `WorkerW`],
   ventana visible, 3000x2000, orden Z correcto, iconos intactos; aun así se ve el fondo normal. Probado: hijo de WorkerW, hijo de
   Progman bajo DefView, `SDL_RENDER_DRIVER=software`. Ideas: (a) reproductor propio con DirectComposition/WebView2 en vez de SDL,
   (b) `mpv --wid` con mpv (no instalado), (c) copiar frames al fondo vía `IDesktopWallpaper` (lento), (d) capa `WS_EX_LAYERED`
   por encima del fondo, (e) subir `REA_GHIDRA_STARTUP_TIMEOUT_MS` y mirar cómo `Lively.Common` coloca el reproductor en 24H2+.
2. **Puente Windows<->WSL (`bridge/`)**: escrito, SIN aplicar. Escribir en `$PROFILE`, `~/.bashrc` y `settings.json` lo bloquea el
   clasificador de permisos; necesita OK explícito de Fabián o aplicarlo a mano.
3. Hook SessionStart para `mi-equipo/refresh.ps1`: bloqueado por el mismo motivo.
4. AuraDesk: autostart, skins declarativos, multi-monitor, pausa con pantalla completa.
5. Aviso: `settings.json` de Claude tiene claves Stripe (test y live) en texto plano; moverlas y rotar la live.

## Diagnóstico de AuraWall con REA (2026-10-29)
Análisis de `Lively.Core.WinDesktopCore` (REA, sin ejecutar nada): `SetupDesktopLayer` (Progman + mensaje 0x052C + localizar WorkerW),
`TryAttachToDesktop` (SetParent(player, WorkerW) + estilo sin borde + SetWindowPos), `EnsureWorkerWZOrder` (WorkerW al fondo de los hijos de
Progman) y un gancho de eventos sobre WorkerW. Cadenas relevantes: "Raised desktop with layered ShellView detected." y
"Unexpected WorkerW Z-order.". Lively también incluye `Wallpapers.DwmThumbnailPlayer` (técnica de miniaturas DWM) y `VideoMpvPlayer`.

Medido en este equipo: `Progman` exstyle 0x200080 (**WS_EX_NOREDIRECTIONBITMAP**), `SHELLDLL_DefView` exstyle 0x80000 (**LAYERED**) = exactamente el
caso "raised desktop". Pruebas (todas verificadas con captura):
| Prueba | Resultado |
|---|---|
| ffplay como ventana normal | Pinta el degradado correctamente (el vídeo es válido) |
| ffplay hijo de WorkerW (D3D y software) | Ventana visible, tamaño correcto, **no se ve** |
| ffplay hijo de Progman bajo DefView | **No se ve** |
| STATIC blanco hijo de WorkerW | **No se ve** (ninguna ventana hija de WorkerW se compone) |
| DwmRegisterThumbnail con destino hijo/WorkerW ajeno | E_INVALIDARG (el destino debe ser ventana de nivel superior del propio proceso) |
| Host propio (tkinter) con miniatura registrada ANTES de SetParent a WorkerW | Registro OK (hr=0), **no se ve** |
| Igual, colgado de Progman | Tapa los iconos, **no se ve** el degradado |
Conclusión: en la build 26200 el WorkerW "raised" no se compone como superficie de fondo; falta la pieza que Lively hace en su rama
"raised desktop" (no resuelta con análisis de metadatos; requiere decompilar los cuerpos IL de `SetupDesktopLayer`/`TryAttachToDesktop`).
Siguientes pasos: (1) decompilar IL de esos métodos (ILSpy/ilspycmd, no instalado) o usar REA nativo con más tiempo para Lively.Common;
(2) volver a instalar Lively desde `refs/lively` (copia) o winget solo para comprobar visualmente que SU fondo sí se ve en este equipo y entonces comparar
la jerarquía de ventanas (Progman/WorkerW/DefView y estilos) con la nuestra: es el experimento que más información daría.
Scripts de prueba: `wall/dwm_test.py`.

## Lecciones
- Suspender (NtSuspendProcess) un proceso cuya ventana cuelga del escritorio congela el shell: ocultar antes de suspender (ya corregido).
- La ventana del propio reproductor puede tomar el foco y dispararse a sí misma la regla de "pantalla completa" (ya corregido).
- `SetWindowPos` con `SWP_NOZORDER` ignora `hWndInsertAfter` (ya corregido).
- Win+D oculta también los widgets de AuraDesk; volver a pulsarlo los restaura.

## Hallazgo decisivo (2026-10-30): jerarquía real de Lively en esta build
Lively ejecutado desde `refs/lively` SÍ pinta aquí. Su reproductor (WinForms con WebView2) es hijo directo de **Progman**, entre `SHELLDLL_DefView` y `WorkerW`
(orden Z: DefView, player, WorkerW), con style 0x56010000 (CHILD|VISIBLE|CLIPSIBLINGS|CLIPCHILDREN) y exstyle **0x8090080 = LAYERED|TOOLWINDOW|NOACTIVATE|CONTROLPARENT**.
Es decir, NO cuelga de WorkerW. La pieza que nos faltaba: WS_EX_LAYERED en el hijo de Progman.

### Solución aplicada (2026-10-30)
`embed()` ahora replica a Lively: exstyle LAYERED|TOOLWINDOW|NOACTIVATE aplicado **antes** de `SetParent` (si se aplica después, Windows lo ignora en un hijo de Progman),
SetParent(player, **Progman**), style CHILD|VISIBLE|CLIPSIBLINGS|CLIPCHILDREN, `SetLayeredWindowAttributes(255, LWA_ALPHA)` y `SetWindowPos(player, DefView)` (justo detrás de DefView).
Verificado con captura: el degradado animado se ve tras los iconos. Scripts de prueba: `wall/embed_test.py`, `wall/step_test.py`, `wall/dump_tree.py`.

**Segunda pieza (clave):** `Progman` es NOREDIRECTIONBITMAP, así que el contenido GDI/software de sus hijos NO se compone (ni un STATIC blanco ni SDL software). Solo se ve contenido GPU
(Chrome/D3D en Lively). Con `SDL_RENDER_DRIVER=direct3d11` el degradado de Aura se ve tras los iconos. **AuraWall funciona.** Pausa por batería ahora solo con <30 %.

## Fondos interactivos: Aura Live (2026-10-30)
Motor `wall/live/live.py`: el fondo se dibuja en Edge (modo InPrivate, sin sincronización ni extensiones; perfil temporal) o en Godot y se pega al escritorio con la receta de AuraWall.
Progman no entrega el ratón a un fondo, así que un servidor local (127.0.0.1, puerto aleatorio) expone `/state` (cursor, clic sobre el escritorio vacío, CPU, RAM, batería, hora) y las escenas lo consultan.
- Escenas web (`wall/live/scenes/*.html`, contrato en `wall/live/lib/aura.js`): estela, constelacion, orbes, aurora, malla.
- Escena Godot (`wall/godot/cristal`): arrancar con `--rendering-method mobile --rendering-driver d3d12`. OpenGL directo (WGL) y ANGLE NO se componen bajo Progman; D3D12 sí.
- Lecciones: título de ventana de Edge InPrivate = "AuraLive - [InPrivate]" (buscar por prefijo); `--start-fullscreen` quita el marco; sin `--inprivate --disable-sync` Edge sincroniza la cuenta y abre pestañas de extensiones.
- Desarrollo: `python wall/live/live.py serve 8791` y abrir `http://127.0.0.1:8791/scenes/<escena>.html` en cualquier navegador.
- Uso: `python aura.py scene <nombre>` / `python aura.py scenes` / panel Aura > Fondo.
