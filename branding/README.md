# Aura - identidad visual

Paleta: tinta `#0e0e18`, noche `#1d1b3a`, ciruela `#3a1b2a`, brasa `#d97757` (acento).
Marca: anillo abierto con degradado de brasa y un punto de luz, sobre fondo tinta.

## Regenerar todo

```
python branding/build.py
```

Requiere Windows con Microsoft Edge (render SVG a PNG en modo headless; ruta por defecto
`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, o define la variable `EDGE`).
Solo usa la libreria estandar de Python (el `.ico` y los `.bmp` se construyen con `struct`).

## Archivos

| Ruta | Uso |
|---|---|
| `icon/aura.svg` | fuente del icono |
| `icon/aura.ico` | 16,24,32,48,64,128,256 (entradas PNG) |
| `icon/aura-512.png` | icono 512 px |
| `tray/tray-light.png`, `tray-light-16.png` | bandeja en barra clara (glifo oscuro), 32 y 16 px |
| `tray/tray-dark.png`, `tray-dark-16.png` | bandeja en barra oscura (glifo blanco), 32 y 16 px |
| `logo/wordmark.svg` | icono + «Aura», texto claro (para fondos oscuros) |
| `logo/wordmark-light.svg` | igual, texto oscuro (para fondos claros) |
| `installer/wizard.bmp`, `small.bmp` | Inno Setup (164x314 y 55x58) |
| `social/social-preview.png` | GitHub social preview (1280x640) |
| `social/banner.png` | banner del README (1600x500) |

La palabra «Aura» esta dibujada con trazos (sin fuentes). El lema de las imagenes sociales usa
Segoe UI con fallback del sistema.
