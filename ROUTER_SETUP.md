# Universal Router Setup & Deployment Guide

This guide explains how to connect **any router or gateway** to the MD TECH Open Wi-Fi CRM:
- **MikroTik RouterOS** (HotSpot, Walled Garden, REST API)
- **OpenWrt** (openNDS with Forward Authentication Service)
- **pfSense / OPNsense** (Captive Portal, FreeRADIUS)
- **Ubiquiti UniFi & TP-Link Omada** (SDN Controllers with External Guest Portal)
- **Generic Consumer Routers** (TP-Link, ASUS, Netgear, D-Link, etc.) in AP mode behind an enforcement gateway

---

## 1. Network Architecture Overview

The CRM manages user accounts, generates vouchers, tracks quotas, records device observations, and computes policy decisions. An **enforcement gateway** (your router, firewall, or gateway appliance) intercepts guest traffic, redirects unauthenticated users to the portal, and enforces admission.

```
+-----------------------------------------------------------+
|                     Internet / WAN                        |
+-----------------------------+-----------------------------+
                              |
                     [Enforcement Gateway]
           (MikroTik / OpenWrt / pfSense / Linux Gateway)
           - DHCP Server for Guests (e.g. 192.168.50.0/24)
           - DNS Interception & Walled Garden
           - Captive Portal Redirect
                              |
         +--------------------+--------------------+
         | (Guest Interface)                       | (Management / LAN)
         v                                         v
   [Wi-Fi Access Points]                 [MD TECH Wi-Fi CRM Server]
  - Stock TP-Link, ASUS, Netgear        - Local PC / VM / Docker host
  - Ubiquiti UniFi / Omada EAPs          - Runs on http://127.0.0.1:8765
  - Broadcasts SSID: MD_TECH               (or behind HTTPS reverse proxy)
  - Operates in AP Bridge mode
         |
         v
   [Guest Devices]
   (Phones, Laptops, Tablets)
```

---

## 2. Platform Guides

### A. MikroTik RouterOS (v6 & v7)

MikroTik routers (hEX, hAP, RB series, CCR) feature built-in HotSpot capabilities:

1. **Configure HotSpot**:
   - In WinBox or WebFig: Go to **IP** -> **Hotspot** -> **Hotspot Setup**.
   - Select your guest interface or guest bridge (e.g. `bridge-guest`).
   - Set the guest IP pool (e.g. `192.168.88.0/24` or `192.168.50.0/24`).
2. **Configure Walled Garden**:
   - In **IP** -> **Hotspot** -> **Walled Garden IP List**:
     - Add the IP and port of your CRM server (e.g. `192.168.50.1` port `8765`).
     - Allow DNS (`53`) and standard captive portal detection hosts.
3. **Run the MikroTik Sync Adapter**:
   - Use the provided connector script: `examples/mikrotik/mikrotik_hotspot_sync.py`.
   - Set environment variables:
     ```bash
     export MDTECH_URL="http://192.168.50.1:8765"
     export MDTECH_GATEWAY_KEY="your-secret-gateway-key"
     export MIKROTIK_HOST="192.168.88.1"
     export MIKROTIK_USER="admin"
     export MIKROTIK_PASS="your-password"
     python examples/mikrotik/mikrotik_hotspot_sync.py
     ```
   - The adapter pushes real-time heartbeats, device discovery, and synchronizes active users.

---

### B. OpenWrt (with openNDS)

OpenWrt turns standard Wi-Fi routers into flexible captive portals using `openNDS`:

1. **Install openNDS**:
   ```bash
   opkg update
   opkg install opennds
   ```
2. **Configure openNDS for FAS (Forward Authentication Service)**:
   - Edit `/etc/config/opennds`:
     ```uci
     config opennds
         option enabled '1'
         option gatewayinterface 'br-guest'
         option fasport '8080'
         option faspath '/fas'
         option fasserver '192.168.1.50'
     ```
   - Restart the service: `/etc/init.d/opennds restart`.
3. **Run the FAS Server**:
   - Run `examples/openwrt/opennds_fas_server.py` on your management host:
     ```bash
     export MDTECH_URL="http://192.168.1.50:8765"
     export MDTECH_GATEWAY_KEY="your-secret-gateway-key"
     python3 examples/openwrt/opennds_fas_server.py --port 8080
     ```

---

### C. pfSense / OPNsense

pfSense and OPNsense provide enterprise-grade captive portals:

1. **Configure Captive Portal**:
   - In the web administration (**Services** -> **Captive Portal**), add a new zone on your Guest interface or VLAN.
   - Set **Authentication Method** to External Authentication or RADIUS.
   - In **Pre-authentication redirect**, point guests to the CRM portal URL (`https://your-crm-host/portal`).
2. **Allowed IP Addresses**:
   - In the **Allowed IP Addresses** tab, whitelist your CRM host's IP address.
3. **API Integration**:
   - Use the OPNsense REST API or pfSense FauxAPI / FreeRADIUS package to sync active vouchers and sessions with `/api/integrations/authorize` and `/api/integrations/event`.

---

### D. Ubiquiti UniFi & TP-Link Omada

For managed deployments with software or hardware controllers:

1. **UniFi Network**:
   - In UniFi Controller: **Settings** -> **Guest Control** (or **Hotspot Manager**).
   - Enable **Hotspot Portal** and select **External Portal Server**.
   - Set the IP address of your CRM host.
   - In **Pre-Authorization Access**, add the CRM IP.
2. **TP-Link Omada**:
   - In Omada Controller: **Wireless Networks** -> **Guest Network** -> **Portal**.
   - Select **External Web Portal** pointing to your CRM host `/portal`.
   - Configure Omada's OpenAPI controller credentials on an adapter script to bind admitted MACs.

---

### E. Consumer & Stock Routers (TP-Link WR841N, ASUS, Netgear, D-Link)

Stock consumer routers typically do not include built-in captive portal redirection APIs. You can easily use them as **Wi-Fi Access Points (APs)** in combination with an upstream gateway:

1. **Switch to Access Point Mode**:
   - Connect to the router's web admin (e.g. `192.168.0.1` or `192.168.1.1`).
   - In **Operation Mode**, select **Access Point Mode** (or disable DHCP server and connect Ethernet from your gateway to a LAN port on the router).
   - Set the Wi-Fi SSID to `MD_TECH` (or your chosen brand name).
   - Leave the Wi-Fi security as **Open** (no WPA password), because authentication will take place at the captive portal.
2. **Use a Linux / Raspberry Pi Gateway**:
   - Place a Raspberry Pi or Linux mini-PC between your internet connection and the consumer router.
   - Run the provided setup script: `examples/linux_gateway/nftables_captive_portal.sh`.
   - The Linux gateway intercepts guest HTTP traffic and redirects users to the CRM portal.

---

## 3. General Deployment Checklist

1. **Isolation**: Separate guest devices from administrative networks using a dedicated interface or VLAN.
2. **Portal URL**: Provide HTTPS access to the guest portal for smooth device captive detection.
3. **Gateway Key**: Generate an API Key under CRM **Settings** -> **Gateway API Key** and configure it on your adapter.
4. **Heartbeat**: Ensure your adapter sends a heartbeat every 30 seconds to `/api/integrations/heartbeat` so the CRM dashboard reflects live telemetry.
