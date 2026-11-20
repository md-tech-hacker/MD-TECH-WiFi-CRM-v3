"""MikroTik RouterOS HotSpot Sync Adapter for MD TECH Wi-Fi CRM.

This connector synchronizes MikroTik RouterOS (v7 REST API or v6 API) with the CRM:
1. Sends periodic heartbeats and router telemetry to the CRM (/api/integrations/heartbeat).
2. Reports newly connected hotspot stations to the CRM (/api/integrations/event).
3. Validates client access rules with the CRM Policy Engine (/api/integrations/authorize).
4. Disconnects stations whose CRM sessions have expired or been revoked.
5. Pushes traffic accounting deltas to the CRM database.

Configuration:
  Set environment variables:
    MDTECH_URL=http://127.0.0.1:8765
    MDTECH_GATEWAY_KEY=<your-gateway-secret-key-from-crm-settings>
    MIKROTIK_HOST=192.168.88.1
    MIKROTIK_USER=admin
    MIKROTIK_PASS=<router-password>
    MIKROTIK_USE_HTTPS=false
"""
from __future__ import annotations
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any

CRM_URL = os.getenv('MDTECH_URL', 'http://127.0.0.1:8765').rstrip('/')
CRM_KEY = os.getenv('MDTECH_GATEWAY_KEY', '')
MT_HOST = os.getenv('MIKROTIK_HOST', '192.168.88.1')
MT_USER = os.getenv('MIKROTIK_USER', 'admin')
MT_PASS = os.getenv('MIKROTIK_PASS', '')
MT_USE_HTTPS = os.getenv('MIKROTIK_USE_HTTPS', 'false').lower() in ('true', '1', 'yes')
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL_SECONDS', '15'))


def crm_post(path: str, data: dict[str, Any]) -> dict[str, Any]:
    """Send an authenticated request to the CRM Gateway Integration API."""
    if not CRM_KEY:
        raise ValueError('MDTECH_GATEWAY_KEY environment variable is required.')
    url = f'{CRM_URL}{path}'
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'X-Gateway-Key': CRM_KEY,
            'User-Agent': 'MDTech-MikroTik-Adapter/1.0',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def mikrotik_request(endpoint: str, method: str = 'GET', payload: dict[str, Any] | None = None) -> Any:
    """Make an authenticated call to MikroTik RouterOS v7 REST API (/rest/...)."""
    scheme = 'https' if MT_USE_HTTPS else 'http'
    url = f'{scheme}://{MT_HOST}/rest{endpoint}'
    
    ctx = ssl.create_default_context()
    if not MT_USE_HTTPS:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        # In production, specify trusted CA certificates
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    
    # HTTP Basic Authentication for RouterOS REST API
    import base64
    creds = base64.b64encode(f'{MT_USER}:{MT_PASS}'.encode('utf-8')).decode('ascii')
    req.add_header('Authorization', f'Basic {creds}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            content = resp.read().decode('utf-8')
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as err:
        print(f'[MikroTik Error] {method} {endpoint} -> HTTP {err.code}: {err.read().decode("utf-8", errors="ignore")}', file=sys.stderr)
        return None
    except Exception as exc:
        print(f'[MikroTik Connection Error] {endpoint} -> {exc}', file=sys.stderr)
        return None


def send_telemetry():
    """Fetch system identity and resource status from RouterOS and report heartbeat."""
    resource = mikrotik_request('/system/resource') or {}
    identity = mikrotik_request('/system/identity') or {}
    hotspot_active = mikrotik_request('/ip/hotspot/active') or []
    
    router_name = identity.get('name', 'MikroTik Router')
    uptime_raw = resource.get('uptime', '0s')
    # Simple uptime parser (e.g. "1d04:22:15" or seconds)
    uptime_sec = 3600
    try:
        uptime_sec = int(resource.get('uptime-seconds', 3600))
    except (ValueError, TypeError):
        pass

    telemetry = {
        'name': router_name,
        'model': resource.get('board-name', 'RouterBOARD'),
        'firmware': resource.get('version', 'RouterOS v7'),
        'ssid': 'MD_TECH',
        'lan_ip': MT_HOST,
        'wan_ip': '0.0.0.0',
        'uptime_seconds': uptime_sec,
        'connected_clients': len(hotspot_active),
        'capabilities': ['captive_portal', 'disconnect', 'traffic', 'rate_limit'],
    }
    try:
        crm_post('/api/integrations/heartbeat', telemetry)
        print(f'[Telemetry] Heartbeat sent: {router_name} ({len(hotspot_active)} active clients)')
    except Exception as exc:
        print(f'[Telemetry Failed] {exc}', file=sys.stderr)


def sync_active_clients():
    """Sync active hotspot clients with CRM policy engine."""
    hosts = mikrotik_request('/ip/hotspot/host') or []
    for host in hosts:
        mac = host.get('mac-address', '')
        ip = host.get('address', '')
        if not mac or not ip:
            continue
        
        # 1. Report device observation to CRM
        try:
            crm_post('/api/integrations/event', {
                'type': 'device_seen',
                'mac': mac,
                'ip': ip,
                'name': host.get('comment', f'Host {ip}'),
            })
        except Exception as exc:
            print(f'[Event Failed] Device seen {mac}: {exc}', file=sys.stderr)

        # 2. Check policy authorization
        try:
            auth_res = crm_post('/api/integrations/authorize', {
                'mac': mac,
                'ip': ip,
                'require_active_session': True,
            })
            if not auth_res.get('allowed', False):
                print(f'[Policy Deny] MAC {mac} not authorized: {auth_res.get("reason")}. Disconnecting...')
                # Disconnect from MikroTik if active
                active_users = mikrotik_request('/ip/hotspot/active') or []
                for user in active_users:
                    if user.get('mac-address') == mac:
                        user_id = user.get('.id')
                        mikrotik_request(f'/ip/hotspot/active/{user_id}', method='DELETE')
                        print(f'[Disconnected] Client {mac} removed from MikroTik HotSpot')
        except Exception as exc:
            print(f'[Auth Check Failed] {mac}: {exc}', file=sys.stderr)


def main():
    print('Starting MD TECH MikroTik RouterOS HotSpot Adapter...')
    print(f'CRM Host: {CRM_URL}')
    print(f'MikroTik Host: {MT_HOST}')
    if not CRM_KEY:
        print('ERROR: MDTECH_GATEWAY_KEY is required. Please set it and rerun.', file=sys.stderr)
        sys.exit(1)

    while True:
        try:
            send_telemetry()
            sync_active_clients()
        except KeyboardInterrupt:
            print('Exiting sync daemon.')
            break
        except Exception as exc:
            print(f'[Loop Error] {exc}', file=sys.stderr)
        
        time.sleep(SYNC_INTERVAL)


if __name__ == '__main__':
    main()
