# MD TECH — Frontend source guide (v3)

**This is real, editable source code, not an image mockup.** The UI is built from standard HTML, CSS and JavaScript. A short `index.html` is expected because the application dynamically renders page content in JavaScript after authentication. It is **not** an HTML-only template, nor does it need React, npm, Docker, or internet-hosted UI libraries.

## Files to edit

| File | What it does |
| --- | --- |
| `static/index.html` | Initial browser shell, CSS and JavaScript includes |
| `static/main.js` | Authentication, navigation, dashboard, users, vouchers, devices, policies, sessions, activity, settings, dialogs, API access |
| `static/studio.js` | Apps & Websites page, Reports page, dashboard quick access, summary cards, policy-toggle interactions |
| `static/styles.css` | Basic layout, forms, table, portal base styles |
| `static/refined.css` | Original v2 light theme and responsive behavior |
| `static/studio.css` | v3 design system, app tiles, analytics, light card treatments, mobile polish |
| `static/portal.html` + `static/portal.js` | Separate guest login screen with account/code tabs |
| `app/main.py` | Actual server routes and authenticated JSON APIs (not fake mock data) |

## UI pages and what each one uses

- **Overview:** `/api/dashboard`, `/api/settings`.
- **Users:** `/api/users` (GET, POST, PATCH, DELETE).
- **Vouchers:** `/api/vouchers` (GET, POST, PATCH).
- **Devices:** `/api/devices` (GET, POST, PATCH).
- **Access policies:** `/api/policies` (GET, POST, PATCH, DELETE).
- **Apps & websites:** `/api/policies` and `/api/settings`. App buttons **persist real policy rules**.
- **Live sessions:** `/api/sessions`, `/api/sessions/{id}/disconnect`.
- **Reports:** `/api/dashboard`, `/api/sessions`, `/api/devices`, `/api/users`, `/api/vouchers`, `/api/activity`, `/api/policies`, `/api/export/*`.
- **Activity:** `/api/activity`.
- **Settings:** `/api/settings`, `/api/settings/gateway-key`, `/api/auth/password`.
- **Guest portal:** `/api/portal/config`, `/api/portal/login`.

## Run on Windows

Extract the entire ZIP. Double-click `START_WINDOWS.bat`. Open `http://127.0.0.1:8765`. The first launch asks for an admin account. **Opening `static/index.html` directly will not work**, as the interface needs a running FastAPI server for login and data.

## Tests

From the extracted project directory:

```bash
python -m pip install -r requirements.txt
python -m pip install pytest httpx
python -m pytest -q
node tests/frontend_smoke.cjs
```

The JavaScript test is optional developer tooling; **Node is not required to run the app**. It checks rendered page HTML and a working policy-toggle interaction with a mocked API contract. The Python tests exercise the actual backend. During the v3 build, a Chromium browser screenshot was not possible because the host environment denied the browser access to localhost; no AI-generated screenshot is being passed off as an application preview.

## Network enforcement

Creating a block rule **does not by itself block traffic** on your TP-Link. The source provides a policy decision engine and API for a *compatible gateway* to consult. Real Wi-Fi redirection, packet filtering, and per-device Internet control require an independently configured, trusted gateway that can enforce the decisions. See `INTEGRATION.md`.
