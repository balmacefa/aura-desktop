# Aura: escritorio personalizado (monolito)

Todo el proyecto en una carpeta: `C:\Users\fabia\OneDrive\Escritorio\aura`.

```
aura/
├── aura.py            punto de entrada único (start/stop/status/gen/install)
├── desk/              AuraDesk: widgets (botón Claude Code, reloj, sistema) + claude-widget.ps1 + install.ps1
├── wall/              AuraWall: fondo animado tras los iconos (WorkerW + ffplay) + install.ps1 + media/
├── bridge/            Puente Windows<->WSL (bridge.ps1 / bridge.sh): ESCRITO, SIN APLICAR (ver abajo)
├── refs/              Copias de referencia analizadas con REA: lively/ (396 MB) y rainmeter/ (7 MB)
├── backup/            Respaldo de tus skins y config originales de Rainmeter
└── docs/              Notas y estado del proyecto
```

Ver `docs/ESTADO.md` para qué está hecho y qué falta. Arquitectura detallada en `desk/docs/` y `wall/docs/`.

## Uso rápido
```
python aura.py gen          # crea el fondo animado propio (una vez)
python aura.py start        # widgets + fondo
python aura.py status
python aura.py stop
```
Requisitos: Python 3.12 (solo stdlib + tkinter), ffmpeg/ffplay (ya instalados).
