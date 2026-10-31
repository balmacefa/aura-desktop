# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
el proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [1.1.0] - 2026-10-30

### Rendimiento
- Coste en reposo con un fondo interactivo: de 126 % a 21 % de un núcleo; con una ventana maximizada encima, de 127 % a 0,4 %.
- El panel consulta el estado sin lanzar procesos (18 % de núcleo menos); `aura.py status` pasa de ~900 ms a ~100 ms.
- Puente del ratón con conexiones persistentes, estado lento en caché y consulta por fotograma; en reposo, 30 fps y ~9 consultas/s.
- El fondo se pausa cuando cualquier ventana visible cubre el área de trabajo (no solo la de primer plano a pantalla completa).
- Memoria de la escena web: ~1,1 GB → ~0,55 GB (opciones de Edge).

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
