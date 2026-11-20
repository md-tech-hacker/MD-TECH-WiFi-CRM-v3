# Connecting a Real Network Gateway

The CRM owns account/voucher records and calculates authorization decisions. **A gateway you control must perform the network interception, redirection, device identification, policy enforcement, bandwidth throttling and actual disconnection.** No feature here claims to give your Windows laptop arbitrary control over a different router.

## Security boundary

- Authenticate gateway requests with header `X-Gateway-Key: <secret>`. The administrator generates/rotates the key in **Settings**. The server stores only a SHA-256 digest.
- **Use HTTPS** for any remote calls. The key must never travel over plain HTTP outside local-only development.
- Do not accept a user-entered MAC address as authenticated identity. Your gateway must determine the client's real device address from its own trusted association table or access-control system.
- Do not accept arbitrary `session_id` values supplied by a client as sufficient proof to bind another device. The integrating gateway must securely associate the original authenticated browser login with the station (e.g. captive-portal gateway token, secure callback or gateway-owned session state).
- API endpoints are not automatically invoked by TP-Link firmware. This is an integration contract for an independently developed adapter.
- Verify that a device has an active, **gateway-verified** session on access checks. Never set `require_active_session=false` for a real captive portal's internet authorization.
- On any API/network failure, the gateway should fail closed unless your operational security policy explicitly provides a different behavior.

## API contract

Base URL: `https://your-mdtech-host` (or `http://127.0.0.1:8765` for local testing).

### 1. Discover device

`POST /api/integrations/event`

```json
{
  "type":"device_seen",
  "mac":"aa:bb:cc:dd:ee:ff",
  "ip":"192.168.50.24",
  "name":"Guest laptop"
}
```

### 2. Guest credential verification

Send a user to `GET /portal` **via the gateway's captive portal redirection mechanism** (not implemented here). The guest submits voucher or account credentials to `POST /api/portal/login`. A successful response contains a `session_id` and `expires_at`, but **not proof of actual Wi-Fi access**.

Example successful response:

```json
{
  "ok":true,
  "session_id":12,
  "bind_token":"<one-time random proof returned only at login>",
  "expires_at":"2026-10-17T16:00:00+00:00",
  "message":"Your credentials were accepted. Actual Wi-Fi access depends on a configured compatible gateway."
}
```

### 3. Secure gateway binding

After independently verifying the device–session association, a trusted adapter calls `POST /api/integrations/bind`:

```json
{
  "session_id":12,
  "bind_token":"<proof from this guest login>",
  "mac":"aa:bb:cc:dd:ee:ff",
  "ip":"192.168.50.24",
  "name":"Guest laptop"
}
```

The proof is required, stored only as a digest and consumed atomically. Missing, incorrect or replayed proofs are rejected. Existing unbound sessions from an older build must log in again. Transfer this proof only through the audited gateway-owned handoff over HTTPS; never place it in a URL, log or localStorage. The bundled generic portal does not yet implement a vendor callback.

The CRM flags the session as `gateway_verified` only after this authenticated call. It refuses to bind one session to a second device. **Implementers are responsible for correctly securing the handoff**. The reference project does not include that hardware-specific browser-to-gateway handshake.

### 4. Check access on a verified device

`POST /api/integrations/authorize`:

```json
{
  "mac":"aa:bb:cc:dd:ee:ff",
  "ip":"192.168.50.24",
  "domain":"youtube.com",
  "app":"youtube",
  "require_active_session":true
}
```

Response:

```json
{
  "allowed":false,
  "reason":"Policy: Block YouTube",
  "policy_id":2,
  "enforcement":"gateway-must-apply-decision"
}
```

If no policy denies the request, a real access check still requires a verified, active device session. For quota-bound vouchers, the CRM considers per-session traffic bytes **reported by that gateway**.

Network authorization derives user scope from the active verified guest session. A supplied `user_id` is ignored in normal network authorization. `require_active_session=false` is a trusted-adapter policy-evaluation mode only; it must never be used to admit guests. The supplied gateway secret should be restricted to a trusted and isolated service.

### 5. Report real traffic (delta bytes, not cumulative readings)

`POST /api/integrations/event`:

```json
{
  "type":"traffic",
  "mac":"aa:bb:cc:dd:ee:ff",
  "session_id":12,
  "rx_bytes":524288,
  "tx_bytes":65536
}
```

Only the gateway can measure real traffic. Send byte **increments** (deltas); resending cumulative counters inflates totals. Production adapter should deduplicate telemetry and handle reconnections.

To report a blocked request:

```json
{
  "type":"blocked_request",
  "mac":"aa:bb:cc:dd:ee:ff",
  "domain":"youtube.com"
}
```

### 6. Apply revocations/blocks

`GET /api/integrations/state` returns `blocked_macs`, `revoked_session_ids` (including expired sessions), and a timestamp. Account disable/delete, password reset and voucher disable revoke associated sessions. Poll this endpoint regularly, or check `/authorize` on each new connection/flow. The CRM cannot remotely disconnect clients without gateway action.

To close a session based on a real disconnect:

```json
{"type":"session_disconnected","mac":"aa:bb:cc:dd:ee:ff","session_id":12}
```

### 7. Optional dev-only API exercise

From Windows CMD:

```bat
set MDTECH_GATEWAY_KEY=YOUR_NEWLY_GENERATED_KEY
.venv\Scripts\python.exe examples\gateway_demo.py
```

This generates obvious **synthetic** traffic for testing. Do not mistake it for live client capture or access control.

## What the CRM does **not** enforce

- DHCP leases, MAC admission, firewall packets, packet shaping, captive portal redirection, access point deauthentication, DNS request interception, or HTTPS filtering.
- App labels are best-effort domain-based presets unless your gateway provides reliable app identification.
- DNS-based rules alone do not reliably block mobile apps, encrypted DNS, VPN tunnels or hardcoded IP connections.
- The TP-Link TL-WR841N v14 is **not** supported out of the box as a gateway adapter.

## Production roadmap

1. Verify topology and select a supported gateway platform (OpenWrt-capable hardware, an OPNsense/pfSense gateway, or a dedicated Linux bridge/router).
2. Develop and audit a gateway-side connector that verifies client identity, sends session bindings and measurements, and applies decisions atomically.
3. Add HTTPS, secure gateway callback tokens and signed session handoff.
4. Add gateway-specific traffic shaping, DNS sinkholing, captive redirects and disconnect handling.
5. Load-test telemetry and make events idempotent before handling real networks.

## Router telemetry and deployment profile

Version 3.1: `/api/network/host` returns read-only observations of the **CRM host**,
not a router discovered elsewhere. It requires an administrator session, caches for
20 seconds and never reads Wi-Fi passwords. Windows location permission or WLAN
service availability can limit the SSID/radio information. Browser Windows-settings
links open on the computer using the browser; host observations run on the server.

`POST /api/network/check` requires admin + CSRF and uses the saved management IP.
It checks TCP ports 80/443 only, with a 1.5-second timeout per port, at most six
checks per minute per administrator. It accepts RFC1918 IPv4 targets only; loopback,
link-local/metadata, public addresses and arbitrary hostnames/ports are rejected.
Success means a TCP web-admin port responded; identity, credentials and control
are **not** verified. No HTTP requests or passwords are sent by this check.

`POST /api/policies/preview` requires admin + CSRF and runs the gateway decision
engine without binding, admitting or modifying any device. `enforcement` is
`not-applied`. The generic portal's `ssid` field now contains only a fresh enabled
gateway report (or empty), while `network_label` carries manual portal branding.

`POST /api/integrations/heartbeat` requires `X-Gateway-Key` and accepts:

```json
{"name":"Guest gateway","model":"<actual model>","firmware":"<actual firmware>","ssid":"MD_TECH","lan_ip":"192.168.50.1","wan_ip":"","uptime_seconds":3600,"connected_clients":4,"capabilities":["captive_portal","disconnect","traffic"]}
```

Send every 30 seconds. `GET /api/network` requires an administrator session and
returns the saved profile and latest report. Status is disabled, not_reporting,
reporting or stale (over 90 seconds). Reports are adapter claims, not independent
enforcement verification. Rotating the key clears the previous heartbeat. Optional
capabilities are captive_portal, disconnect, dns_filter, traffic and rate_limit.
`PATCH /api/network` is admin/CSRF-protected and stores planning fields only; it
does not contact arbitrary hosts or change the router. See ROUTER_SETUP.md for
the WR841N V14 topology and researched platform choices.
