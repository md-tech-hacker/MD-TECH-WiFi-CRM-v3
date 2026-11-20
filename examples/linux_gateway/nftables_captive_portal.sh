#!/usr/bin/env bash
# MD TECH Wi-Fi CRM — Linux nftables Gateway Setup
# Turns a Linux host, Raspberry Pi, or mini-PC into a captive portal gateway
#
# Topology:
#   Internet (WAN: eth0) <---> [Linux Gateway] <---> Wi-Fi APs / Guests (LAN: eth1)

set -euo pipefail

WAN_IF="eth0"
LAN_IF="eth1"
LAN_SUBNET="192.168.50.0/24"
CRM_HOST_PORT="192.168.50.1:8765"

echo "=== Configuring MD TECH Linux Captive Gateway ==="

# 1. Enable IPv4 Forwarding
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-captive-gateway.conf

# 2. Reset and build nftables ruleset
nft flush ruleset

nft -f - <<EOF
table ip captive_filter {
    # Set of MAC addresses authorized by the CRM
    set authenticated_macs {
        type ether_addr
        flags timeout
    }

    # Set of Walled Garden IPs (CRM server, DNS, Captive checks)
    set walled_garden_ips {
        type ipv4_addr
        elements = { 192.168.50.1, 8.8.8.8, 1.1.1.1 }
    }

    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;

        # Allow authenticated MACs to pass through without redirection
        iif "$LAN_IF" ether saddr @authenticated_macs accept

        # Allow access to Walled Garden destinations
        iif "$LAN_IF" ip daddr @walled_garden_ips accept

        # Intercept unauthenticated HTTP traffic (port 80) and redirect to CRM Portal
        iif "$LAN_IF" tcp dport 80 dnat to $CRM_HOST_PORT
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;

        # Masquerade outbound traffic to WAN
        oif "$WAN_IF" masquerade
    }

    chain forward {
        type filter hook forward priority filter; policy drop;

        # Allow established and related connections
        ct state established,related accept

        # Allow DNS queries from guest LAN
        iif "$LAN_IF" udp dport 53 accept
        iif "$LAN_IF" tcp dport 53 accept

        # Allow authenticated stations to forward to WAN
        iif "$LAN_IF" oif "$WAN_IF" ether saddr @authenticated_macs accept
    }
}
EOF

echo "Captive portal nftables rules successfully applied."
echo "Unauthenticated clients on $LAN_IF will be redirected to $CRM_HOST_PORT"
echo "To authorize a device MAC dynamically, run:"
echo "  nft add element ip captive_filter authenticated_macs { aa:bb:cc:dd:ee:ff timeout 3600s }"
