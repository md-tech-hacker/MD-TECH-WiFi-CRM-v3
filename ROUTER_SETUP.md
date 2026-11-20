# MD TECH network deployment

Research checked: 18 October 2026. User-confirmed equipment: TP-Link TL-WR841N,
hardware V14; guest SSID `MD_TECH`; upstream Wi-Fi `MUNIRAJ`. Installed firmware,
region, subnet, management address and administrator access are not yet verified.

## Your existing router

The [TP-Link V14 manual](https://www.tp-link.com/us/user-guides/tl-wr841n_v14/chapter-2-connect-to-the-internet)
documents Wireless Router, WISP, Range Extender and Access Point modes.
The [WISP configuration guide](https://www.tp-link.com/us/user-guides/tl-wr841n_v14/chapter-5-configure-the-router-in-wisp-mode)
documents manual host/target/schedule access controls. These are useful basic
controls, but do not connect CRM sessions to network admission. I found no documented
external portal authentication API in that stock manual. That is a documentation
finding, not a hardware-tested assertion about every regional firmware.

Do not install OpenWrt on this router for this deployment. The
[V14 device entry](https://openwrt.org/toh/hwdata/tp-link/tp-link_tl-wr841n_v14)
flags resource limits and ended support. It is not a suitable current secure
enforcement gateway. The CRM does not flash firmware or scrape router passwords.

## Recommended topology

```text
Internet / MUNIRAJ upstream router
             |
       wired uplink, or separate Wi-Fi client bridge
             |
      compatible enforcement gateway
       |                   |
  guest interface     management interface / VPN
       |                   |
  WR841N V14 in AP mode    HTTPS CRM + trusted connector
  broadcasts MD_TECH
       |
  guest phones / laptops
```

All guest internet traffic must cross the enforcement gateway. A CRM laptop sitting
beside the router cannot enforce authentication on other devices.

If only wireless `MUNIRAJ` access is available, choose an upstream client bridge or
a gateway with a supported Wi-Fi WAN. Do not assume the WR841N can simultaneously
provide its current WISP uplink and act as an isolated AP behind another gateway.
Avoid placing the WR841N's NAT between guests and the enforcement gateway: it
can hide individual device identities. Keep guests off the upstream `MUNIRAJ` SSID.

## Platform comparison

| Platform | Native capability | Work required for this CRM |
| --- | --- | --- |
| MikroTik RouterOS with HotSpot | Portal, sessions, accounting, RADIUS and rate profiles | A connector mapping CRM authentication, policy, expiry and disconnect to RouterOS; check model/license/device-mode |
| Supported OpenWrt hardware + openNDS | Captive detection and FAS authentication handoff | FAS connector, firewall/DNS filtering and accounting; verify exact device support |
| OPNsense gateway | Captive portal, portal APIs, sessions | Connector using supported portal APIs or a separately implemented RADIUS service; separate AP required |
| Compatible Omada EAP/gateway + controller | External portal workflow | Controller-version-specific authentication connector, accounting and revoke handling |
| WR841N V14 stock | AP/WISP, basic manual rules | Use as an AP behind a compatible gateway; no built-in MD TECH connector |

These platforms are integration candidates, **not shipped adapters**. Their APIs
do not directly understand the CRM REST protocol. Verify actual hardware and
firmware before buying or changing equipment.

Official references:

- [MikroTik HotSpot](https://help.mikrotik.com/docs/spaces/ROS/pages/56459266/HotSpot+-+Captive+portal): supports local/RADIUS authentication, accounting and walled gardens. Its HotSpot implementation requires IPv4; separately prevent IPv6 bypass.
- [OpenWrt openNDS](https://openwrt.org/docs/guide-user/services/captive-portal/opennds): FAS is the interface for a third-party authentication service.
- [OPNsense portal](https://docs.opnsense.org/manual/captiveportal.html) and [API](https://docs.opnsense.org/development/api/core/captiveportal.html): consult portal/session operations for the installed release.
- [Omada external portal API](https://support.omadanetworks.com/us/document/13080/): this particular guide covers controller 5.0.15–6.2.0; other releases need their matching specification.
- [WR841N V14 AP guide](https://www.tp-link.com/us/user-guides/tl-wr841n_v14/chapter-6-configure-the-router-in-access-point-mode) and [regional firmware/download page](https://www.tp-link.com/us/support/download/tl-wr841n/v14/).

## Configuration sequence

1. Back up the router's configuration. Record its firmware, region, LAN address,
   subnet and operation mode in **Router & network**. Confirm local admin access
   before changing addresses; keep a wired management connection available.
2. Put the enforcement gateway on the upstream network. Assign a non-overlapping
   guest subnet; for example `192.168.50.0/24` only if unused. The gateway should
   provide guest DHCP and DNS. Keep administration on another interface or VPN.
3. Configure the WR841N using its AP-mode guide, with SSID `MD_TECH` and the uplink
   on the guest side of the enforcement gateway. Verify it bridges guest clients
   and does not supply a competing DHCP server. Assign a reserved management IP.
4. On the gateway, deny unauthenticated internet forwarding and guest-to-management
   traffic. Configure client isolation where supported. Control IPv6 as well as
   IPv4. Allow the HTTPS portal and required assets before authentication.
5. Configure the platform's captive portal / external authentication mechanism.
   Automatic display depends on device captive-network detection. Provide a manual
   portal URL too; do not intercept arbitrary HTTPS or ask guests to bypass
   certificate errors. Do not broadly allow shared CDNs in the pre-login garden.
6. Run the CRM on an always-on host behind HTTPS. Complete first-admin setup at
   `127.0.0.1` first. Restrict admin `/`, `/api/auth/*` and management APIs to the
   management network at the reverse proxy/firewall. Guests need `/portal`,
   `/static/*` and `/api/portal/*` only. Restrict integration APIs to the adapter.
7. Implement the chosen platform adapter. Generate a gateway key in Settings;
   store it on the adapter, never in browser JavaScript. Follow **INTEGRATION.md**.
   A successful guest response includes a one-time `bind_token`; a session number
   alone is insufficient. Independently verify station ownership before binding.
8. Apply admission with a local expiry timer; send usage deltas and heartbeats.
   Poll revoked sessions and re-evaluate quotas. Remove established flows on
   revoke/block. Fail closed on new admissions if the CRM is unreachable. Enforce
   expiry locally even during an outage; bound cached decisions with short leases.

App preset domains are a starting list, not complete application classification.
Gateway DNS/firewall rules must account for encrypted DNS, QUIC, VPNs and shared
hosting. Avoid blanket shared-IP blocking that disrupts unrelated services.

## Hardware acceptance checks

Use a real phone with mobile data disabled. Before login, internet must fail while
the portal works. Incorrect credentials must never admit it. A valid voucher must
admit only the verified station. Check expired/disabled vouchers, account disable,
password reset, quota exhaustion, session expiry, admin revoke, gateway restart,
CRM outage, existing downloads, IPv6 and manual DNS/VPN bypass attempts. Confirm
guests cannot access the router, the CRM admin API or other guest stations.

The repository tests verify software behavior only. They do not replace these
hardware acceptance checks. No physical router was configured during this update.
