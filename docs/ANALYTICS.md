# Analítica del sitio web (aura.balmacefa.com)

**Principio:** medir lo mínimo para saber si la promoción funciona, sin identificar a nadie. La aplicación sigue **sin telemetría**; esto solo afecta a la web.

## Qué se registra
Una línea por evento en `/opt/aura-website/logs/events.log` del servidor:

| Campo | Ejemplo | Nota |
|---|---|---|
| hora UTC | `2026-11-01T10:03:11+00:00` | |
| evento | `pv`, `download`, `demo_play`, `scene_aurora`, `lang_es`, `section_faq`, `sponsor_click`, `github_click` | |
| referente | `news.ycombinator.com` | solo el dominio, vacío si es directo |
| utm_source / utm_medium / utm_campaign | `reddit` / `social` / `lanzamiento` | solo si el enlace los lleva |
| país | `ES` | cabecera de Cloudflare |
| dispositivo | `mobile` / `desktop` | |

## Qué NO se registra
IP, user agent, cookies, identificadores, huella del navegador, historial entre visitas, ni nada se envía a terceros. Por eso no se puede reconstruir "un visitante": las descargas no se ligan a una visita concreta (se comparan totales y tasas).

## Respeto a la privacidad
- No se cuenta nada si el navegador envía **Do Not Track** o **Global Privacy Control**.
- Solo cuenta en `aura.balmacefa.com` (no en local ni en `github.io`).
- Está explicado en la propia web (sección «Estadísticas de esta web»).
- Sin cookies ni identificadores no suele hacer falta banner de consentimiento (RGPD/ePrivacy), pero no es asesoramiento legal: si se añade cualquier píxel, cookie o servicio de terceros, hay que revisar esto antes.
- **No instalar** píxeles de Meta, X, Google Ads, etc. en la web: contradicen lo que prometemos. La eficacia de los anuncios se mide con enlaces UTM + este contador.

## Cómo ver el informe
```
wsl ansible-playbook -i inventory.ini playbooks/services/report_aura_website_stats.yml -e stats_days=7
```
(en el repo `ansible_coolify`). Muestra visitas por día, eventos, conversión descargas/visitas, referentes, campañas, países y dispositivo.

## Enlaces con campaña
`https://aura.balmacefa.com/?utm_source=reddit&utm_medium=social&utm_campaign=lanzamiento`
Usar siempre minúsculas, sin espacios, y una campaña por acción para poder comparar.

## Cambiar de sistema
Si más adelante se prefiere GoatCounter autoalojado, ya existe `deploy_goatcounter.yml` en `ansible_coolify`; requiere la API de Coolify activa.
