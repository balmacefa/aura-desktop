# Funding the maintenance of Aura

An honest, realistic plan. Aura is a niche desktop customization tool; expect modest income. The goal is to cover time and costs (code signing, hosting), not to get rich. Everything marked *Planned* does not exist yet.

## Principles
- The core stays MIT and free. Paid extras never remove or degrade free features.
- **Do NOT:** add telemetry, ads, bundled adware/crypto miners, nag screens, or sell user data. The privacy promise ("no telemetry") is Aura's main selling point.
- No feature that phones home for licensing without explicit, documented opt-in.

## Channels
1. **GitHub Sponsors** (Active: `.github/FUNDING.yml` points to `balmacefa`). Lowest friction; add a Sponsors tier README. Open Collective is an alternative if a fiscal host / expense transparency is wanted.
2. **"Supporter" edition (Planned).** A paid build or license key that unlocks an extra scene pack and early access to new scenes. The scenes are the only gated part; the engine and the free scenes remain identical. Offline verification only, no activation server.
3. **Scene packs (Planned).** Sell themed packs on Gumroad or itch.io (Supporter edition users get them included). Scenes follow the open `aura.js` contract, so third-party creators can sell packs too.
4. **Microsoft Store (Planned).** Listing removes the SmartScreen warning and gives a paid or free-with-IAP option. Cost: a developer account fee and packaging work (MSIX). The Inno Setup installer and in-app updates already exist (2.0), so evaluate once there is demand.
5. **Services (Optional).** Custom scenes for brands/streamers, or paid support for companies deploying Aura. Only if requested; do not build a business around it prematurely.

## Costs to cover
Code-signing certificate (removes SmartScreen friction, recurring yearly cost), Microsoft Store account (one-time), domain, and the maintainer's time.

## Milestones (indicative)
| Milestone | Goal |
|---|---|
| M0 | Public repo, GitHub Sponsors enabled, first release |
| M1 | Covers the code-signing certificate |
| M2 | Supporter edition and first scene pack on sale |
| M3 | Microsoft Store listing |
| M4 | Covers a few paid maintenance hours per month |

Review the plan every six months and drop channels that do not work.
