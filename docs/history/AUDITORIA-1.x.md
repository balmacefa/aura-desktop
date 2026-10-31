# Auditoría de producción de Aura 1.0.0

Realizada con el skill `production-audit` (affaan-m/ecc, MIT; instalado tras leer su `SKILL.md` completo: trabaja solo con evidencia local y prohíbe
ejecutar código remoto o subir el repositorio a terceros). El skill está pensado para servicios web; se aplicaron sus lentes de seguridad, datos,
operaciones y experiencia de usuario y se descartaron las de pagos/webhooks, que no existen aquí.

**Resultado: 78/100, «lanzable con salvedades».** Antes de esta pasada: 52/100, «arriesgado». Las puntuaciones son una estimación para ordenar
prioridades, no una medida exacta.

## Evidencia revisada
`git log`/`status`, todo el código Python, `desk/install.ps1`, el servidor del puente (`wall/live/live.py`), las rutas de configuración y estado,
las dependencias externas (Edge, ffmpeg, Godot), búsqueda de secretos y de rutas fijas de usuario, y 27 pruebas automáticas.

## Hallazgos y estado

| # | Hallazgo | Gravedad | Estado |
|---|---|---|---|
| 1 | Los daemons corren con `pythonw`: un fallo no dejaba rastro y los `sys.exit('...')` se perdían | Alto | Corregido: `aura_log.py` (registro rotativo en `%LOCALAPPDATA%\Aura\logs`, gancho de excepciones en procesos e hilos) |
| 2 | El panel decía «aplicado» aunque el fondo no arrancara | Alto | Corregido: `wait_started` confirma que un daemon NUEVO publica el fondo; si no, error visible con la ruta del registro |
| 3 | Sin pruebas, CI, versión, licencia ni changelog | Alto | Corregido: 27 pruebas `unittest`, CI de GitHub Actions, `__version__`, MIT, CHANGELOG |
| 4 | El servidor local servía todo `wall/live` (incluido el código del motor) y no validaba `Host` (DNS rebinding) | Medio | Corregido: solo `/scenes`, `/lib` y `/state`; `Host` 127.0.0.1/localhost; CSP con `connect-src 'self'` (una escena no puede hablar con internet); `nosniff` |
| 5 | Configuración y estado escritos sin atomicidad; un corte dejaba JSON corrupto | Medio | Corregido: temporal + `os.replace`; JSON ilegible se aparta como `.bad` |
| 6 | Entradas sin validar llegaban a ffmpeg (paleta, velocidad) y a rutas (`video` en `aura.json`) | Medio | Corregido: paleta = 4 hex de 6 dígitos, velocidad acotada, vídeo siempre dentro del proyecto |
| 7 | El panel podía abrirse varias veces | Bajo | Corregido: instancia única con foco en la existente |
| 8 | Requisitos externos sin comprobación amable | Medio | Corregido: `python aura.py doctor` (Python, tkinter, Progman, ffmpeg, Edge, Godot, registro, configuración) |
| 9 | Herramientas de depuración mezcladas con el código | Bajo | Movidas a `wall/devtools/` y excluidas del paquete |
| 10 | Sin empaquetado, instalador ni desinstalador | Alto | Corregido: `install.ps1`/`uninstall.ps1` por usuario (sin administrador) + `scripts/build-release.ps1` con SHA-256 |
| 11 | `uninstall.ps1` borraba todo el contenido de su carpeta: ejecutado desde el repositorio habría destruido código e historial | Alto | Corregido: solo borra carpetas con la marca `.aura-installed` que crea `install.ps1`; probado con y sin marca |
| 12 | Sin telemetría, sin secretos, servidor solo en 127.0.0.1, Edge en InPrivate sin sincronización | — | Ya correcto; documentado en el README |

## Lo que sigue sin cubrirse (por qué no es 100)
- **El CI nunca se ha ejecutado**: no hay remoto de GitHub; solo se probó en local. Al subir el repo, la primera ejecución puede revelar diferencias de entorno.
- **Sin pruebas de interfaz ni de integración con el escritorio** (embebido en Progman, fundidos, Godot): se verificaron a mano con capturas y la sonda de píxeles
  (`wall/devtools/transition_probe.py`), no de forma automática.
- **Rendimiento no medido** (fps, CPU y batería con un fondo activo); la pausa por pantalla completa y por batería baja existe pero no se probó con cada escena.
- **No hay firma de código ni ejecutable**: se distribuye como script + instalador PowerShell, que exige Python 3.10+ instalado. Un `.exe` con PyInstaller
  requeriría reestructurar el arranque de procesos (hoy se lanzan scripts con `pythonw`) y firmarlo con un certificado para evitar SmartScreen.
- **Compatibilidad**: probado solo en Windows 11 build 26200 con pantalla 3000×2000 al 200 %; Windows 10, otros DPI y varios monitores sin probar.
- **Dependencias de terceros no incluidas** (Edge, ffmpeg, Godot): el panel y `doctor` avisan si faltan.
- **Licencia**: se eligió MIT por defecto; cámbiala si prefieres otra.

## Próximo paso recomendado
Subir el repositorio a GitHub, comprobar que el CI pasa y probar el instalador en una máquina limpia (o una VM) con Windows 10 y con Windows 11.
