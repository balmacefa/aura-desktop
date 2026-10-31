# Rendimiento de Aura

Optimización guiada por una métrica con el skill `ce-optimize` (EveryInc/compound-engineering-plugin, MIT; instalado tras leer su `SKILL.md`,
las referencias y los scripts `scripts/*.sh|mjs`: sin red, sin código remoto). Método: medir → atribuir el coste → una hipótesis por experimento →
conservar o revertir con el decisor del skill (`decide.mjs`, mediana de 3 mediciones y umbral de ruido).

## Resultado (Windows 11, i5-1135G7, pantalla 3000×2000 al 200 %, fondo interactivo en reposo, ratón quieto)

| Métrica | Antes | Después |
|---|---|---|
| **Coste en reposo** (widgets + panel + escena, % de un núcleo) | **126,5** | **21,3** (−83 %, 5,9× menos) |
| Con una ventana maximizada encima | 126,9 | **0,4** (−99,7 %) |
| Refrescar el estado del panel (cada 5 s) | 18,6 % de un núcleo | 0,006 % |
| `python aura.py status` | 898 ms | ~100 ms |
| Memoria de la escena (Edge) | ~1.108 MB | ~556 MB |
| Peticiones/s al puente del ratón | 62 | 9 |
| Fluidez medida dentro de la página | 60 fps | 60 fps con actividad, 30 fps en reposo |

Las mediciones tienen un ruido de unos ±3 puntos de núcleo; las diferencias menores no son concluyentes.

## Experimentos (`optimize/aura-idle-cost`)

| # | Hipótesis | Resultado | Efecto |
|---|---|---|---|
| 1 | El panel lanza PowerShell y Python cada 5 s | Conservado | 126,5 → 116,3; panel 18,6 → 0,006 % |
| 2 | El puente abre una conexión TCP por petición y recalcula CPU/RAM/batería cada vez | Conservado | 116,3 → 66,6 (HTTP/1.1 persistente, estado lento en caché, consulta por fotograma) |
| 3 | Limitar la resolución interna de dibujo a 1× | Revertido | sin mejora: el coste no depende de los píxeles |
| 4 | 30 fps tras 2 s sin actividad (60 al instante con actividad) | Conservado | 66,6 → 41,0 |
| 5 | En reposo basta consultar el cursor cada 100 ms | Conservado | 41,0 → 22,7 (puente 60 → 9 peticiones/s) |
| 6 | Pausar si **cualquier** ventana visible cubre el área de trabajo | Conservado | cubierto 20,7 → 0,4 |
| 7 | Opciones de Edge (GPU en proceso, rasterización por GPU, sin servicios de fondo) | **Corregido** | ver abajo |
| 8 | Sprites prerenderizados en Estela | Revertido | 14,7 → 19,6: en reposo dominan las luciérnagas, no la estela |

**Lección del experimento 7.** Con `--in-process-gpu` el benchmark midió una mejora (21,7 → 14,7) que era falsa: la página dibujaba pero Windows no
la componía bajo el escritorio, así que no se veía nada. La puerta de calidad de entonces solo miraba los fotogramas de la página. Se añadió
la puerta `scenes_visible`, que compara píxeles reales del escritorio con el fondo de Windows; sin esa opción el fondo se ve y la mejora real de ese
experimento es la memoria (1.048 → 556 MB), no la CPU.

## Cómo ejecutar el benchmark

```
python bench/bench.py --quick                 # una pasada rápida (≈1 min)
python bench/measure.py <etiqueta> 3          # 3 pasadas completas; guarda la instantánea
python bench/decide.py <base> <candidato>     # conservar / revertir con el decisor de ce-optimize
python bench/attribute.py                     # qué proceso consume la CPU de la escena activa
```
Efectos mientras mide: **minimiza todas las ventanas** (las restaura al terminar), **cambia el fondo** (y restaura el tuyo) y no debes mover el ratón.
Con batería baja se pausa el fondo en uso normal; el benchmark lo desactiva para poder medir. Conviene tener el portátil enchufado.
Puertas de calidad: `tests_ok`, `scenes_ok`, `scenes_visible`, `fps_min ≥ 28`, `frame_p95_ms_max ≤ 45`. Especificación: `bench/optimize-spec.yaml`.

## Qué queda y por qué no es «exponencial»
Cada mejora elimina un coste concreto; al quitar los grandes (procesos lanzados, conexiones, ventanas tapadas) la curva se aplana. Lo que queda
(~14-21 %) es el renderizado de Edge a 30 fps. Ideas sin probar: bajar a 15-20 fps en reposo en escenas lentas, escenas WebGL en vez de canvas 2D,
pausar al bloquear la sesión o al apagarse la pantalla, y medir Godot y varios monitores. Los fondos de vídeo (ffplay) no se han optimizado.
