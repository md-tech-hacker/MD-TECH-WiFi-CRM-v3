# Changelog

## 3.1.0 — Network connection workflow and custom controls

- Replace visible native dropdowns with a shared searchable custom control throughout forms and records, including dynamic scope and app selections; support keyboard navigation, Escape, form validation and reset.
- Start sign-in at Router & network; move it directly below Overview in navigation.
- Show only reported SSIDs in live identity areas. Keep manual portal labels separate and remove the default SSID from new instances.
- Add authenticated Windows host inspection: Ethernet/Wi-Fi interfaces, addresses, subnets, MAC, gateways, DNS, DHCP, installed adapters, WLAN service and available Wi-Fi signal/radio/security details.
- Add Windows network/permission settings links, manufacturer-labelled IP presets, documented WR841N V14 configuration menu paths, router admin links and a fixed-port LAN connection check.
- Add filter/sort controls for accounts, vouchers, devices, policies, sessions and audit records; maintain summary cards during searches.
- Add an authenticated, CSRF-protected policy decision preview with no admission side effects.
- Add inline sign-in errors, duplicate-submit prevention, password visibility/Caps Lock helpers, and clearer session verification / device policy labels.
- Extend regression coverage for network privacy, probe restrictions and policy previews. Inspect all management pages and custom form controls in a separate browser test instance.

## 2026-10-18 — Runtime, security and router readiness

- Fix Windows launcher detection when `py -3` fails despite an installed Python; add setup-only diagnostics.
- Bundle 15 brand SVGs, an original Wi-Fi favicon, domain previews and named policy selectors.
- Add Router & network profiles, authenticated heartbeat API, router detail reporting and stale-data status.
- Compact desktop navigation and show the configured SSID label.
- Harden first-run setup, account/voucher revocation, policy identity, admin session invalidation, rate limiting, CSV export and device updates.
- Require an atomic one-time proof for gateway session binding; update adapters before upgrading.
- Document the WR841N V14 / MD_TECH / MUNIRAJ deployment path and platform comparison in ROUTER_SETUP.md.
- Add regression tests and verify the UI in an isolated browser instance. No physical gateway adapter or router configuration is included.

## 3.0 — Frontend expansion

- Added full App & Website Control page: actual app presets, status cards, working create/pause block-rule actions, search/category filters and domain policy table.
- Added Analytics & Reports page using existing authenticated APIs, a session summary, report charts, device/policy breakdowns, activity, CSV export links and print styles.
- Updated overview with quick navigation tiles, refreshed all list screens with data-derived summary cards.
- Added polished light UI styling for the new modules, adaptive mobile layouts, responsive cards and accessible button states.
- No placeholder telemetry or simulated Wi-Fi enforcement. Zero-state charts clearly identify that a gateway must report traffic.
- Added `tests/frontend_smoke.cjs` for JavaScript page rendering and app-rule toggle contract checks.
- Retained unchanged FastAPI APIs, SQL schema, credentials and Windows no-Docker launcher. 

# Changelog

## v2.0 — Light UI refresh (2026-10-17)

- New cohesive light design across dashboard, records, system settings, admin sign-in and guest portal.
- Redesigned navigation shell, responsive mobile drawer, collapsible desktop icon rail, and quick-navigation command panel (`Ctrl+K`).
- Reworked overview cards, gateway-integrity status banner, polished activity feed and native-SVG usage graph.
- Clear empty/loading states that never pretend the CRM has live router telemetry without a connected gateway.
- Improved search field, tables, forms, badges, keyboard focus and motion-reduction handling.
- No new runtime dependencies, database migrations, remote assets or CDN requirements.
- Backend and gateway enforcement semantics unchanged.

Design research: [Taste Skill — redesign existing projects](https://github.com/Leonxlnx/taste-skill/blob/main/skills/redesign-skill/SKILL.md).

## v1.0 — Initial backend and web CRM

- Local-first account/voucher/device/policy/session management and gateway integration API.
