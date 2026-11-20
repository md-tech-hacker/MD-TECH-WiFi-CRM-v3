# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.x     | :white_check_mark: |
| < 3.0   | :x:                |

## Reporting a Vulnerability

Security is a core priority of MD TECH Open Wi-Fi CRM. If you discover a security vulnerability, please report it responsibly:

1. **Do not disclose the issue publicly** on GitHub issues, forums, or social media.
2. Please open a private security advisory on GitHub under the **Security** tab of the repository, or email the project maintainer.
3. Provide detailed steps to reproduce the issue, including request payloads and system configuration.

You should receive an acknowledgement within 48 hours. Validated security issues will be patched and credited in release notes.

## Security Architecture Guidelines
- **Gateway Keys**: Store gateway keys only on trusted gateway adapters. Never embed gateway keys in client-side browser JavaScript.
- **HTTPS in Production**: The CRM listens on HTTP by default for local development (`127.0.0.1`). For any production LAN or multi-device deployment, place the CRM behind an HTTPS reverse proxy (e.g. Caddy, Nginx, or Traefik).
- **Network Isolation**: Always isolate guest traffic from management interfaces and administrator dashboards using VLANs or separate subnets.
