# Security Policy

## Reporting a vulnerability
Please do **not** open a public issue. Use GitHub Private Vulnerability Reporting: go to the repository's **Security** tab and choose **Report a vulnerability** (https://github.com/balmacefa/aura-desktop/security/advisories/new). Include the version (`aura version`), Windows build, steps to reproduce and impact.

You can expect an acknowledgement within 7 days and a fix or mitigation plan within 30 days for confirmed issues. Credit is given in the advisory unless you prefer otherwise.

## Supported versions
Only the latest release receives security fixes.

## Scope
In scope: the Aura code in this repository, its local server, the scene sandbox (CSP), process launching, the installer and uninstaller, and the update mechanism.
Out of scope: vulnerabilities in third-party software Aura launches (Microsoft Edge, Godot, ffmpeg, Windows), issues requiring an already-compromised account or administrator access, and social-engineering.

## Threat model
- **Local server.** Interactive scenes are served from a server bound to `127.0.0.1` on a random port. It serves only `/scenes`, `/lib` and `/state`, rejects requests whose `Host` header is not `127.0.0.1`/`localhost` (against DNS rebinding), sends `X-Content-Type-Options: nosniff` and a CSP with `connect-src 'self'`, so a scene cannot contact the internet. `/state` exposes only cursor position, click state, CPU, RAM, battery and hour.
- **Browser.** Edge is launched InPrivate, without sync or extensions, with a temporary per-process profile deleted on stop.
- **Configuration.** `aura.json` is validated on read (palette = four 6-digit hex values, bounded speed, video path confined to the project) and written atomically.
- **Updater.** One anonymous request per day to the GitHub Releases API; it downloads only when the user clicks Update, accepts only an asset named exactly `Aura-Setup-X.Y.Z.exe`, only over HTTPS from `github.com`, and verifies the SHA-256 listed in `SHA256SUMS.txt` before running anything. It can be disabled in *Settings > General*. This is the only external connection.
- **Telemetry.** None.
- **Known limitation.** Releases (installer and portable zip) are not yet code-signed, so Windows SmartScreen warns on first run; verify the SHA-256 of your download.
