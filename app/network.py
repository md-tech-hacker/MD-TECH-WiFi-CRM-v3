"""Read-only network observations of the CRM host. No router login or scanning."""
from __future__ import annotations
import json
import ipaddress
import os
import platform
import re
import subprocess
import socket
import time
from pathlib import Path
from threading import Lock
from .db import now

_lock = Lock()
_cached = None
_cached_at = 0


def probe_router(management_ip):
    """Check only the two fixed web-admin ports on an explicitly saved LAN IP."""
    address = ipaddress.ip_address(management_ip)
    private_lan = address.version == 4 and any(address in ipaddress.ip_network(net) for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
    if not private_lan:
        raise ValueError('Use the router’s private IPv4 LAN address for this connection check')
    reachable = []
    for port in (80, 443):
        try:
            with socket.create_connection((str(address), port), timeout=1.5):
                reachable.append(port)
        except OSError:
            pass
    return {'target': str(address), 'checked_at': now(), 'reachable_ports': reachable,
            'reachable': bool(reachable), 'router_identity_verified': False,
            'message': 'A web administration port responded. Router identity and login are not verified.' if reachable else 'No web administration port responded. Check the IP, connection, firewall and router power.'}


def open_windows_settings(page):
    pages={'location':'ms-settings:privacy-location','wifi':'ms-settings:network-wifi','ethernet':'ms-settings:network-ethernet'}
    if page not in pages or platform.system() != 'Windows':
        raise ValueError('This action is available only for supported Windows settings pages')
    os.startfile(pages[page])
    return {'opened': True, 'page': page, 'permission_granted': False,
            'message': 'Windows settings opened. Review the permission there, then recheck network access.'}


def inspect_host_network(force=False):
    global _cached, _cached_at
    with _lock:
        if not force and _cached is not None and time.monotonic() - _cached_at < 20:
            return _cached
        result = {'source': 'crm_host_operating_system', 'observed_at': now(),
                  'interfaces': [], 'wifi_ssid': None, 'router_identity_verified': False,
                  'adapters': [], 'wifi': {}, 'wifi_status': 'unavailable', 'wlan_service': 'unknown',
                  'status': 'unavailable', 'message': ''}
        if platform.system() != 'Windows':
            result['message'] = 'Automatic host inspection currently supports Windows only. Use gateway telemetry for router details.'
            return result
        system32 = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
        try:
            script = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); $svc=Get-Service WlanSvc -ErrorAction SilentlyContinue; @{interfaces=@(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=True' | Select-Object Description,IPAddress,IPSubnet,DefaultIPGateway,DHCPEnabled,DHCPServer,DNSServerSearchOrder,MACAddress); adapters=@(Get-CimInstance Win32_NetworkAdapter -Filter 'PhysicalAdapter=True' | Select-Object Name,NetConnectionID,NetEnabled,Speed,AdapterType); wlan_service=$(if($svc){$svc.Status.ToString()}else{'NotInstalled'})} | ConvertTo-Json -Compress -Depth 6"
            proc = subprocess.run([str(system32 / 'WindowsPowerShell/v1.0/powershell.exe'), '-NoProfile', '-NonInteractive', '-Command', script],
                                  capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
            if proc.returncode != 0:
                raise ValueError('Network inventory could not be read')
            inventory = json.loads(proc.stdout.strip() or '{}')
            records = inventory.get('interfaces') or []
            result['wlan_service'] = inventory.get('wlan_service', 'unknown')
            result['adapters'] = [{'name': a.get('Name', ''), 'connection': a.get('NetConnectionID', ''),
                'enabled': bool(a.get('NetEnabled')), 'speed_bps': a.get('Speed'), 'type': a.get('AdapterType', '')}
                for a in (inventory.get('adapters') or [])]
            for r in records:
                result['interfaces'].append({'name': r.get('Description', ''), 'addresses': r.get('IPAddress') or [],
                    'gateways': r.get('DefaultIPGateway') or [], 'dns_servers': r.get('DNSServerSearchOrder') or [],
                    'dhcp_enabled': bool(r.get('DHCPEnabled')), 'subnets': r.get('IPSubnet') or [],
                    'dhcp_server': r.get('DHCPServer') or '', 'mac': r.get('MACAddress') or ''})
            wlan = subprocess.run([str(system32 / 'netsh.exe'), 'wlan', 'show', 'interfaces'],
                                  capture_output=True, text=True, errors='replace', timeout=4, creationflags=subprocess.CREATE_NO_WINDOW)
            ssid = re.search(r'^\s*SSID\s*:\s*(.+)$', wlan.stdout, re.MULTILINE)
            if ssid:
                result['wifi_ssid'] = ssid.group(1).strip()
                result['wifi_status'] = 'connected'
                for label, key in [('BSSID','bssid'),('Signal','signal'),('Authentication','authentication'),('Cipher','cipher'),('Radio type','radio_type'),('Channel','channel'),('Receive rate (Mbps)','receive_mbps'),('Transmit rate (Mbps)','transmit_mbps')]:
                    match = re.search(r'^\s*' + re.escape(label) + r'\s*:\s*(.+)$', wlan.stdout, re.MULTILINE)
                    if match: result['wifi'][key] = match.group(1).strip()
            elif result['wlan_service'] == 'Stopped':
                result['wifi_status'] = 'service_stopped'
            elif re.search(r'location|permission|access is denied', wlan.stdout + wlan.stderr, re.IGNORECASE):
                result['wifi_status'] = 'permission_required'
            else:
                result['wifi_status'] = 'not_connected'
            result['status'] = 'observed'
            result['message'] = 'These are this computer’s network settings. A default gateway is not proof that it is your TP-Link router.'
            if not ssid:
                result['message'] += ' No active Wi-Fi SSID was detected; Wi-Fi may be disconnected, unavailable or restricted by Windows permissions.'
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            result['message'] = 'Windows network inspection is unavailable. Enter the router management IP or connect a trusted gateway adapter.'
        _cached, _cached_at = result, time.monotonic()
        return result
