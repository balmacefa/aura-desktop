# Aura

Escritorio personalizado para Windows 10/11: fondos animados (vídeo) o interactivos (reaccionan al ratón, a los clics y a la carga del equipo) que se ven detrás de los iconos, más widgets de escritorio (reloj, sistema, botón de Claude Code). Todo con Python y su biblioteca estándar, sin dependencias que instalar.

## Requisitos
- Windows 10 u 11.
- Python 3.10 o superior con tkinter (el instalador oficial de python.org lo incluye).
- Opcionales:
  - **ffmpeg** (con ffplay): fondos en vídeo y degradados propios. `winget install Gyan.FFmpeg`
  - **Microsoft Edge**: fondos interactivos web (viene con Windows).
  - **Godot 4**: solo para la escena 3D `godot-cristal`.

## Instalación
Con el paquete de versión (`Aura-<versión>.zip`): extráelo y, en PowerShell, ejecuta

```powershell
.\install.ps1
```

Instala por usuario en `%LOCALAPPDATA%\Programs\Aura`, sin permisos de administrador. Opciones:

| Parámetro | Efecto |
|---|---|
| `-InstallDir <ruta>` | otra carpeta de instalación |
| `-Autostart` | arranca Aura al iniciar sesión |
| `-NoShortcuts` | no crea accesos en el menú Inicio |
| `-NoRegistry` | no aparece en «Agregar o quitar programas» |

Si falta Python: `winget install Python.Python.3.12`.
También puedes usar Aura directamente desde la carpeta del código, sin instalar.

## Uso
### Panel
`python aura.py ui` (o el acceso «Aura» del menú Inicio). Paneles: Resumen, Fondo, Colores, Widgets y General. Atajos: Ctrl+1 a 5 para cambiar de panel, Esc para cerrar.

### Línea de comandos
```
python aura.py start [desk|wall|all]   arranca widgets y/o fondo
python aura.py stop  [desk|wall|all]   detiene
python aura.py status                  estado
python aura.py scenes                  lista de escenas interactivas
python aura.py scene <nombre>          aplica una escena interactiva
python aura.py wallpaper <archivo>     usa un vídeo o GIF propio como fondo
python aura.py gen [segundos]          genera el degradado animado propio
python aura.py palette c0 c1 c2 c3     paleta de 4 colores hex (ej. 0e0e18 d97757 1d1b3a 3a1b2a)
python aura.py speed <0.003-0.05>      velocidad del degradado
python aura.py config                  muestra aura.json
python aura.py install | uninstall     accesos del menú Inicio
python aura.py doctor | version | logs
```

## Escenas
Interactivas, en Edge: `estela`, `constelacion`, `orbes`, `aurora`, `malla`. En Godot 4: `godot-cristal`. Cambiar de fondo se hace con un fundido suave, sin mostrar nunca el fondo de Windows entre ambos.

## Personalizar
- **Colores y velocidad**: panel > Colores, o `aura.py palette ...` / `aura.py speed ...`.
- **Fondo propio**: `aura.py wallpaper mi_video.mp4`.
- **Configuración**: `aura.json` en la carpeta de Aura (se valida al leer; si está corrupto se conserva como `aura.json.bad` y se usan los valores por defecto).

## Privacidad y seguridad
- Sin telemetría: Aura no envía datos a ningún sitio.
- Los fondos interactivos usan un servidor local que escucha solo en `127.0.0.1` (puerto aleatorio), valida la cabecera `Host` y aplica una CSP restringida.
- Edge se lanza en modo InPrivate, sin sincronización ni extensiones y con un perfil temporal que se borra al parar.

## Solución de problemas
1. `python aura.py doctor` comprueba requisitos (Python, tkinter, escritorio, ffmpeg, Edge, Godot, registro, configuración).
2. `python aura.py logs` muestra la ruta del registro; adjúntalo al informar de un fallo.
3. El fondo no aparece: ejecuta `python aura.py stop` y luego `python aura.py start`.

## Desinstalar
```powershell
.\uninstall.ps1                # desde la carpeta de instalación
.\uninstall.ps1 -KeepSettings  # conserva aura.json
```
Detiene los procesos, quita accesos, la entrada del registro y los archivos.

## Desarrollo
- Tests: `python -m unittest discover -s tests`
- Herramientas de diagnóstico del escritorio: `wall/devtools` (no se incluyen en el paquete).
- Servir una escena en el navegador: `python wall/live/live.py serve 8791` y abrir `http://127.0.0.1:8791/scenes/<escena>.html`.
- Crear una escena: añade `wall/live/scenes/<nombre>.html` que cargue `wall/live/lib/aura.js` y registre un callback con `Aura.onFrame((dt, s) => ...)`. El estado `s` trae cursor (`x`, `y`, suavizado `sx`, `sy`, velocidad `vx`, `vy`), `down`, `clicked`, `cpu`, `ram`, `bat`, `hour`, `night`, `t`, `dt`, `w`, `h`, `dpr`; la paleta está en `Aura.pal` (4 colores). La cabecera de `aura.js` documenta el contrato completo. La escena aparece sola en `aura.py scenes`.
- Empaquetar: `.\scripts\build-release.ps1` crea `dist/Aura-<versión>.zip` y `dist/SHA256SUMS.txt`.

## Avisos de terceros
Godot, Microsoft Edge y ffmpeg **no se incluyen** en Aura: son software de terceros con sus propias licencias, que se instalan por separado y cuyas marcas pertenecen a sus titulares.

## Licencia
MIT, ver [LICENSE](LICENSE).
