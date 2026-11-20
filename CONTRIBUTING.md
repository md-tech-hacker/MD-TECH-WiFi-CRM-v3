# Contributing to MD TECH Open Wi-Fi CRM

Thank you for your interest in contributing! This project is an open-source, local-first Wi-Fi CRM, policy decision engine, and gateway integration system supporting multiple router platforms.

## How to Contribute

### 1. Developing Router Adapters
We welcome new gateway and router adapters under `examples/` or as community extensions!
Popular router targets:
- MikroTik RouterOS (HotSpot, API, RADIUS)
- OpenWrt (openNDS, uclient, CoovaChilli)
- pfSense & OPNsense (Captive Portal API, FreeRADIUS)
- Ubiquiti UniFi & TP-Link Omada (External Portal APIs)
- Linux nftables / iptables gateways

When authoring an adapter:
- Keep the adapter decoupled from the core CRM database.
- Use the REST API endpoints documented in `INTEGRATION.md` (`/api/integrations/heartbeat`, `/api/integrations/event`, `/api/integrations/authorize`, `/api/integrations/bind`).
- Authenticate with the `X-Gateway-Key` header.

### 2. Reporting Issues
- Use the provided [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md).
- Include your router platform, Python version, and relevant server log excerpts.

### 3. Submitting Pull Requests
1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/my-new-adapter
   ```
2. Set up the development environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .\.venv\Scripts\Activate.ps1 on Windows
   pip install -r requirements.txt pytest httpx
   ```
3. Run test suites before submitting:
   ```bash
   python -m pytest -v
   node tests/frontend_smoke.cjs
   ```
4. Commit your changes with clear, descriptive commit messages.
5. Push to your fork and submit a Pull Request.

## Code Style
- **Python**: Follow PEP 8 guidelines. Type annotations are encouraged for API schemas.
- **Frontend**: Plain, zero-build vanilla ES6+ JavaScript and clean CSS. No external CDNs or heavy frameworks.
- **Security**: Never commit keys, hashes, tokens, or personal IP addresses.
