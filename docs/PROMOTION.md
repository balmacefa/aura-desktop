# Plan de promoción de Aura (honesto y conforme a las normas)

Estado: **borradores preparados, nada publicado**. Cada publicación en un tercero necesita el visto bueno explícito de la persona responsable del proyecto.

## Reglas innegociables
1. **Solo afirmaciones verdaderas y comprobables.** Permitido: «gratis, código abierto (MIT)», «sin telemetría en la app», «5 escenas interactivas y 7 widgets», «unos 0,3 % de CPU con una ventana encima (medido en un i5-1135G7; en tu equipo puede variar)». Prohibido: «el mejor», «más rápido que X», cifras sin medir, comparaciones con Lively/Wallpaper Engine/Rainmeter sin datos publicados.
2. **Decir quién eres.** Todo mensaje debe dejar claro que lo hace el autor («lo hice yo»). Nada de cuentas falsas, reseñas pagadas, estrellas o votos comprados, ni pedir votos en grupos organizados (rompe las normas de Product Hunt, HN y Reddit y la publicidad engañosa es ilegal).
3. **Ser claros con las limitaciones:** solo Windows 10/11; el instalador no está firmado, así que SmartScreen avisa (y cómo continuar); aún no probado en todas las configuraciones.
4. **Publicidad de pago:** etiquetada como anuncio por la plataforma, sin segmentar por datos sensibles, sin remarketing con píxeles en la web (la web no los lleva), con la misma promesa de privacidad que en la página.
5. **Marcas:** «para Windows» se puede decir (uso descriptivo); no usar logos ni nombres de otros productos como si hubiera afiliación.
6. **Cada comunidad tiene sus reglas.** Leer las reglas de cada subreddit/foro antes de publicar (muchos limitan la autopromoción; típico: contribuir antes de promocionar). Una publicación por comunidad, sin repetir.
7. **Responder a las críticas y a los fallos con rapidez y en abierto.** Registrar los problemas en GitHub Issues.

## Orden recomendado
| Fase | Acción | Quién | Medición |
|---|---|---|---|
| 0 | Web con SEO, imagen social y contador anónimo (hecho en el repo; falta desplegarlo) | listo | `report_aura_website_stats.yml` |
| 0 | Registrar la web en Google Search Console y Bing Webmaster | la persona responsable (requiere cuenta) | impresiones/clics |
| 1 | Entradas en directorios de software libre (AlternativeTo, awesome-lists de Windows, Fosshub/Softpedia) | con OK | `utm_source=<directorio>` |
| 2 | Lanzamiento orgánico: Show HN, Reddit (r/Windows11, r/software, r/opensource, según reglas), Product Hunt, dev.to | con OK, uno cada varios días | utm por canal |
| 3 | Contenido: artículo «Cómo hicimos un fondo animado con 0,3 % de CPU» (la parte técnica interesa) y vídeo corto con las escenas | con OK | visitas orgánicas |
| 4 | Publicidad de pago pequeña (X/Reddit Ads) solo si la conversión descarga/visita orgánica es razonable | con OK y presupuesto | coste por descarga |

## Borradores (no publicados)

### Show HN
**Título:** Show HN: Aura – open-source animated desktop wallpapers for Windows (about 0.3% CPU when covered)
**Texto:** I'm the author. Aura renders interactive wallpapers (trail, constellation, orbs, aurora, wave mesh) behind the desktop icons and pauses completely when a window covers the desktop, which keeps CPU around 0.3% on my i5-1135G7. It also has 7 small widgets. MIT licensed, no telemetry in the app (the only network call is GitHub to check for updates). Limitations: Windows 10/11 only, the installer is not code-signed so SmartScreen will warn, and I've only tested on my own machines so far. Code and download: https://github.com/balmacefa/aura-desktop. Feedback and bug reports welcome.

### Reddit (adaptar a las reglas de cada sub)
**Título:** I made a free, open-source animated wallpaper app for Windows that pauses when you're not looking at the desktop
**Texto:** Disclosure: I'm the developer. [mismo cuerpo que arriba, con capturas/GIF]. Happy to answer questions and to hear what scenes you'd like.

### Product Hunt
**Tagline (≤60):** Animated, interactive wallpapers for Windows. Free & open source.
**Descripción:** Aura brings your desktop to life with interactive scenes and 7 widgets, uses ~0.3% CPU when a window covers it, and sends no telemetry. MIT licensed. Made by one person.

### Español (comunidades hispanas, p. ej. r/Windows, foros, X)
**Texto:** Soy el autor. Aura es una app gratuita y de código abierto de fondos de escritorio animados e interactivos para Windows 10/11. Se pausa sola cuando una ventana tapa el escritorio (≈0,3 % de CPU en mi portátil) y la app no envía telemetría. Aviso: el instalador aún no está firmado, así que SmartScreen mostrará una advertencia. Descarga y código: https://aura.balmacefa.com — cualquier comentario es bienvenido.

### Enlaces con campaña
`https://aura.balmacefa.com/?utm_source=hn&utm_medium=social&utm_campaign=lanzamiento` (cambiar `hn` por `reddit`, `producthunt`, `devto`, `x`...).

## Checklist antes de publicar en cada canal
- [ ] Las cifras del texto siguen siendo ciertas con la última versión.
- [ ] Hay GIF/captura real, no maquetas.
- [ ] Se declara que soy el autor.
- [ ] Se mencionan SmartScreen, Smart App Control (bloqueo sin “ejecutar de todas formas”) y la compatibilidad.
- [ ] Se han leído las reglas de la comunidad.
- [ ] El enlace lleva su `utm_source`.
- [ ] Hay alguien disponible para responder en las siguientes horas.
