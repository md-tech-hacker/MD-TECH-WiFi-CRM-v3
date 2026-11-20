# MD TECH — Open Wi-Fi CRM

**Version 3.1: open-source, local-first Wi-Fi account and network policy management with a redesigned light-first web interface.** Runs as a modern browser dashboard on **Windows 11 without Docker, WSL, or Node.js**. Python 3.10+ is the only runtime needed; an internet connection is required the first time to download Python packages.

> **Important distinction:** This application is a functional CRM, authentication database, guest login portal, policy decision engine, and gateway integration API. **It is not a router, firewall, captive portal redirector, DNS server, or packet interceptor.** It cannot force an unmodified TP-Link TL-WR841N v14 (or any other unsupported router) to redirect guests, block apps, apply speed limits, or disconnect devices. For real enforcement, install/configure a separately compatible gateway and implement the documented integration protocol.

## Version 3.1.1 — network connection, custom controls and feedback

Confirmations use accessible custom dialogs, and notifications use dismissible status cards. Settings text and search/filter/sort controls share consistent alignment.

All selection menus use bundled custom searchable controls, including account status,
owner assignment, rule action/type/scope, dynamic app/user/device targets, router
platform/mode/address presets, and record filters/sorting. Login includes inline
errors and password visibility controls. Sessions show gateway-verification status;
access policies include a read-only decision preview.

After sign-in, **Router & network** checks the CRM host's actual Windows interfaces.
It shows Ethernet/Wi-Fi, adapters, addresses, subnet, gateway, DNS, DHCP and any
available SSID/radio details, plus Windows network/location settings links.
The Windows network-access dialog can open the actual Windows location/Wi-Fi settings from a local admin session and recheck the result. No Windows permission or router setting is changed automatically. Live SSID areas
never fall back to a manually typed label.

The same page includes V14 manual configuration paths, labelled factory address
suggestions, a saved private management IP, a bounded TCP web-port check and links
to the router's actual admin interface. Successful TCP connection does not prove
router identity or give the CRM control. Stock WR841N V14 firmware still requires
its own admin UI; captive enforcement still needs a compatible gateway adapter.

## October 2026 update

The Windows launcher now probes working Python commands instead of assuming
`py -3` works. The observed launcher/runtime mismatch is fixed; no Python reinstall
is needed when a valid `python` command already exists. Run
`START_WINDOWS.bat -SetupOnly` to install without starting the server.

New: 15 locally bundled SVG brand icons, custom Wi-Fi favicon, domain previews,
account/device policy selectors, compact sidebar, and Router & network with saved
profiles, authenticated heartbeat telemetry and freshness status. Initial admin
setup must run locally at `127.0.0.1`. Existing gateway adapters must send the
one-time `bind_token` at session binding; older unbound sessions need a new login.

Read [ROUTER_SETUP.md](ROUTER_SETUP.md) for your **TL-WR841N V14**, `MD_TECH`
and your main Wi-Fi connection. Read [SECURITY_REVIEW.md](SECURITY_REVIEW.md) for the
confirmed security fixes and limits. No actual router connector is shipped.

## 1. Install on Windows — no Docker

1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/windows/). On Windows, make sure `py` or `python` is available in a Command Prompt.
2. Extract this whole ZIP into a folder you control (for example `Documents\MD-TECH-Open-WiFi-CRM`). **Do not run it from inside the ZIP.**
3. Double-click `START_WINDOWS.bat`. It creates a private Python environment, installs FastAPI/Uvicorn/Pydantic, and starts the local server.
4. Open **http://127.0.0.1:8765** in your browser.
5. Create your administrator username and a **12+ character password** on the first-run setup screen. No default password exists.
6. Open the **Guest portal** link from the dashboard or visit **http://127.0.0.1:8765/portal**.
7. Keep the Command Prompt window running while using the CRM. Close it to stop the app.

**Manual command alternative** in PowerShell:

```powershell
cd "C:\path\to\MD-TECH-Open-WiFi-CRM"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

The browser frontend is bundled and works offline after Python packages are installed; no external fonts, frameworks, CDNs, or web assets are required.

### Network access from other devices

By default the server listens only on `127.0.0.1`. Other Wi-Fi users **cannot** visit this host unless you deliberately expose it. To bind it to your LAN:

```powershell
$env:MDTECH_HOST="0.0.0.0"
.\.venv\Scripts\python.exe run.py
```

That makes plain HTTP accessible on your network. **Do not send admin passwords, guest passwords, vouchers, or gateway secrets over unsecured Wi-Fi HTTP.** For deployment outside a trusted development machine, use HTTPS through a properly configured reverse proxy, restrict the admin panel to trusted IPs or a VPN, configure firewall rules, and avoid exposing the server to the public internet. Opening the Windows firewall is a separate administrative decision. Do not port-forward this server to the internet.

## Version 3.0 complete frontend

The frontend now uses a cohesive light palette, calmer blue accents, tabular numbers, improved card hierarchy, a new dashboard overview, genuine empty states (no invented traffic or devices), a responsive mobile off-canvas navigation drawer, optional collapsible desktop sidebar, navigation search (Ctrl+K), smooth interaction feedback, keyboard focus indicators, reduced-motion support, and matching light admin-login and guest-access screens. It runs from bundled CSS and JavaScript and **does not need Node, npm, React, Docker, external CDNs or Google Fonts**.

The visual redesign followed the GitHub [Taste Skill: redesign-existing-projects](https://github.com/Leonxlnx/taste-skill/blob/main/skills/redesign-skill/SKILL.md) guidance. It is an original implementation, not a copy of any theme or framework, and no upstream skill runtime is required.

**Upgrading from the earlier ZIP while keeping your database:** stop the old app. Back up the complete old `instance/` folder, including `mdtech.sqlite3` and `voucher_secret.key`. Extract v3 into a new folder, copy your backed-up `instance/` folder into that new folder, then start the v3 `START_WINDOWS.bat`. Avoid copying `.venv` from the old folder. The backend/database schema is unchanged in this UI-only release.

### New in v3 — actual application pages

- **Overview** — real database KPIs, seven-day reported traffic chart, recent events/devices, and quick navigation shortcuts.
- **User accounts** — browse, search, create, update, disable, delete guest credentials; summary cards.
- **Access vouchers** — batch generation, expiry/use details, pause/resume, one-time code download.
- **Devices** — recorded IP/MAC/device owner, reported traffic, configured block flag and edit controls.
- **Access policies** — advanced domain/app/IP/device rules with scopes and priorities.
- **Apps & websites (new)** — filterable grid of actual supported app presets, one-click creation/pause of global block policies, plus custom domain rule management.
- **Live sessions** — stored login sessions, expiry, session revocation and reported data.
- **Analytics & reports (new)** — report cards, usage chart, session summary, device access proportions, policy breakdown, activity and exports; all backed by real saved records.
- **Activity log** — searchable audit trail.
- **Settings** — guest portal branding, gateway API key and administrator password.
- **Admin login and guest login portal** — actual authenticated screens, not mockup images.

The small `static/index.html` file is **intentional**: it is the shell loaded by the browser. Most UI rendering is in `static/main.js` and `static/studio.js`; theme styling is in `static/styles.css`, `static/refined.css`, and `static/studio.css`. **You must extract the entire ZIP**, not just `index.html`. Open the real running app at `http://127.0.0.1:8765` rather than opening the HTML file directly.

### Test coverage / truthful previews

- `python -m pytest -q` runs backend tests.
- `node tests/frontend_smoke.cjs` runs a **developer-only** JavaScript rendering and API-contract smoke test (Node is not required to operate the app).
- The October update was checked in the in-app browser using an isolated test database; older builds did not have browser verification. Screens visible in the application are rendered from the source files, not AI-generated images.
- No prepopulated demo accounts, passwords, or fake traffic are shipped. Create an admin on first launch.

## 2. Features

| Capability | Current functionality |
| --- | --- |
| Modern CRM UI | Light-first nine-section management dashboard, responsive drawer, app cards, reports, real-data chart, forms, search, navigation shortcuts |
| First-run setup | No default credentials; admin with scrypt-hashed password |
| User credentials | Create, edit, disable, delete accounts; reset guest passwords |
| Access vouchers | Cryptographically random batch codes, expiry, one-time or limited-use, session limits, quotas |
| Guest login page | Account login or voucher login, guest session records |
| Device inventory | MAC/IP, assigned account, block flag, last seen, traffic totals |
| Blocking rules | Domain, common application-domain presets, IP/CIDR, device MAC; scoped by user/device/all |
| Policy decision API | Ask whether a verified device's request should be allowed |
| Guest sessions | Login time, expiry, data quota, revocation in CRM |
| Monitoring | Audited actions, 7-day reported traffic chart, connected devices from gateway events |
| Data export | CSV for accounts, vouchers (hints only), devices, policies, sessions, logs |
| Gateway API | API-key-authenticated events, verified device-session binding, allow/deny responses, sync state |
| Storage | Local SQLite database; entirely self-hosted |
| Licensing | MIT, source included |

**Not provided out of the box:** forced captive portal Wi-Fi interception, real-time packet capture, OS-wide or router-wide app blocking, bandwidth shaping, direct TP-Link v14 control, real connected-client discovery without gateway events, payment processing, multi-admin roles, production-grade network assurance. Gateway-dependent sections do not invent traffic or claim restrictions were enforced.

## 3. How to use

**Users:** Create a guest account and password. Share the credentials via your own trusted channel. A guest may verify them at `/portal`.

**Access vouchers:** Choose quantity, duration in minutes, data quota (0 means unlimited), use count, and expiry in days. Download the generated codes **immediately**: only keyed hashes and code hints are stored. Previously created full codes cannot be recovered.

**Devices:** Enroll MAC addresses manually or import real gateway observations through `/api/integrations/event`. Toggle block to store a device restriction; a cooperating gateway must consult the policy decision API or the block sync API to enforce it.

**Access policies:** Block/allow websites, common app-domain presets, IP addresses/networks, and MACs. Rules may be global, user-scoped, or device-scoped. Explicit device block flags always deny. For matching scoped policy exceptions, a user-specific allow can override a global block; equal-specificity blocks beat allows.

**Sessions:** A successful login records an authorized application session. A cooperating gateway must independently establish which device belongs to that session before permitting network traffic. CRM revocation needs gateway polling or per-request checks to take effect on clients.

**Monitoring:** Traffic is derived from gateway event reports, never from made-up LAN discovery. No gateway → zero live traffic data.

## 4. Gateway integration

See **[INTEGRATION.md](INTEGRATION.md)** for the security model, REST APIs, event reporting, trusted session binding, quota handling, and limitations.

`examples/gateway_demo.py` only sends **simulated** events to demonstrate the API; it never intercepts or controls actual traffic.

Interactive API specification is available at **http://127.0.0.1:8765/api/docs** when running.

## 5. Data, security, and backups

- `instance/mdtech.sqlite3` stores accounts, policies, devices, metadata, traffic counters and activity logs.
- `instance/voucher_secret.key` contains the key used to hash voucher codes. **Back up the entire `instance/` directory**, not only the SQLite database. On Windows, restrict read/write access to your Windows account.
- Admin and user passwords are hashed using scrypt with random salts. Session cookies are opaque, HttpOnly, SameSite=Strict and HTTPS-secure when using HTTPS.
- All admin write endpoints use CSRF protection; gateway APIs use a separate randomly generated secret.
- Neither guest account passwords nor voucher full codes are returned in list APIs or CSV exports.
- Stop the CRM before copying its database folder for a consistent manual backup.
- To reset the project deliberately, stop the server and move the entire `instance/` directory somewhere safe; the next startup will create a new blank instance. **This loses access to your previous data unless you restore the directory.**
- For production use, arrange TLS termination, network/firewall isolation, backups, log retention, third-party security review, and gateway-specific hardening.

## 6. Developer commands

```sh
python -m pip install -r requirements.txt
python -m pip install pytest httpx
python -m pytest -q
python run.py
```

### Project layout

```text
MD-TECH-Open-WiFi-CRM/
├── START_WINDOWS.bat      # Double-click launcher; auto-installs venv
├── run.py                 # Python server launcher
├── requirements.txt       # Runtime dependencies
├── app/
│   ├── main.py            # Auth, accounts, vouchers, devices, policy, integration REST endpoints
│   ├── db.py              # SQLite schema, settings, audit logging
│   ├── security.py        # Password/session/voucher security
│   └── policy.py          # Deterministic matching/authorization engine
├── static/
│   ├── index.html         # Admin entry point
│   ├── main.js            # Dashboard, CRUD forms, charts, state management
│   ├── portal.html        # Guest sign-in page
│   ├── portal.js          # Guest login interactions
│   ├── styles.css         # Original foundational styles
│   └── refined.css        # v2 light theme, polish, responsive layout
├── tests/                 # API and policy tests
├── examples/gateway_demo.py
├── INTEGRATION.md
├── LICENSE                # MIT
└── instance/              # Auto-generated private local data (excluded from source ZIP)
```

## 7. Your TP-Link TL-WR841N v14

A WISP/range-extender operating mode by itself does **not** expose a documented, universal API for captive portal redirection and arbitrary app blocking. The exact firmware/hardware capability must be verified. This app deliberately does **not** claim the router supports OpenWrt or recommend flashing unverified firmware. You can run and explore the local CRM immediately, and choose compatible gateway hardware/software later.

## 8. Known limitations of version 3.0

- Single administrator account created at first setup; no role-based multi-admin system yet.
- Account sessions default to 120 minutes; vouchers supply their chosen minutes and data limits.
- Application-domain presets are incomplete by design. Apps may use dynamic domains, QUIC, DNS-over-HTTPS, VPNs, cellular connections or encrypted protocols. An accurate application firewall requires a suitable gateway and, where appropriate, advanced traffic identification.
- No built-in router firmware management, interception, full DNS resolver, or gateway deployment wizard.
- A gateway integration must verify device identity independently before binding sessions. The demo integration is not an authentic enforcement device.
- Basic local rate limiting is in memory and is not a substitute for hardened public-facing authentication.

Made for practical local development and future open-source contributions.
