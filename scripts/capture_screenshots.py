"""Screenshot generation script using Microsoft Edge headless.

Starts a temporary test instance of MD TECH Wi-Fi CRM with realistic demo data,
captures high-resolution screenshots into docs/screenshots/, and terminates cleanly.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / 'docs' / 'screenshots'
DOCS_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
if not EDGE_PATH.exists():
    EDGE_PATH = Path(r'C:\Program Files\Microsoft\Edge\Application\msedge.exe')


def run_headless_edge(url: str, output_png: Path | None, user_data_dir: Path, budget_ms: int = 1500):
    """Invoke Microsoft Edge headless with a persistent profile."""
    cmd = [
        str(EDGE_PATH),
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--hide-scrollbars',
        '--window-size=1280,820',
        f'--user-data-dir={user_data_dir}',
        f'--virtual-time-budget={budget_ms}',
    ]
    if output_png:
        cmd.append(f'--screenshot={output_png}')
    cmd.append(url)
    subprocess.run(cmd, capture_output=True, timeout=25)
    if output_png and output_png.exists():
        print(f'[Screenshot] Saved: {output_png.name} ({output_png.stat().st_size} bytes)')


def main():
    if not EDGE_PATH.exists():
        print(f'ERROR: Microsoft Edge not found at {EDGE_PATH}', file=sys.stderr)
        sys.exit(1)

    temp_dir = tempfile.mkdtemp(prefix='mdtech_shots_')
    edge_profile = tempfile.mkdtemp(prefix='edge_prof_')
    env = os.environ.copy()
    env['MDTECH_DATA_DIR'] = temp_dir
    env['MDTECH_HOST'] = '127.0.0.1'
    env['MDTECH_PORT'] = '8799'

    print(f'Starting test server on http://127.0.0.1:8799 in {temp_dir}...')
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / 'run.py')],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for server startup
        time.sleep(3.5)
        base = 'http://127.0.0.1:8799'
        
        # 1. Setup admin
        setup_req = urllib.request.Request(
            f'{base}/api/auth/setup',
            data=json.dumps({'username': 'admin', 'password': 'DemoAdministrator99!'}).encode(),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(setup_req, timeout=5) as resp:
            login_data = json.loads(resp.read().decode())
            csrf = login_data['csrf']
            cookie_val = resp.headers.get('set-cookie', '').split(';')[0].split('=')[1]

        headers = {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrf,
            'Cookie': f'mdtech_session={cookie_val}',
        }

        # 2. Add sample devices
        devices = [
            {'mac': '00:1A:2B:3C:4D:5E', 'name': 'MacBook Pro (Sarah)', 'ip': '192.168.88.24'},
            {'mac': '00:1A:2B:3C:4D:6F', 'name': 'iPhone 15 Pro', 'ip': '192.168.88.35'},
            {'mac': '00:1A:2B:3C:4D:7A', 'name': 'ThinkPad X1 (Dev)', 'ip': '192.168.88.42'},
            {'mac': '00:1A:2B:3C:4D:8B', 'name': 'Guest iPad Air', 'ip': '192.168.88.50'},
        ]
        for d in devices:
            req = urllib.request.Request(f'{base}/api/devices', data=json.dumps(d).encode(), headers=headers)
            urllib.request.urlopen(req, timeout=5)

        # 3. Add sample vouchers
        v_req = urllib.request.Request(
            f'{base}/api/vouchers',
            data=json.dumps({'quantity': 5, 'duration_minutes': 240, 'data_limit_mb': 1024, 'label': 'Event Pass'}).encode(),
            headers=headers,
        )
        urllib.request.urlopen(v_req, timeout=5)

        # 4. Add policies
        for p in [
            {'name': 'Block TikTok', 'kind': 'app', 'target': 'tiktok', 'action': 'block', 'scope_type': 'all'},
            {'name': 'Block Roblox', 'kind': 'app', 'target': 'roblox', 'action': 'block', 'scope_type': 'all'},
            {'name': 'Allow Spotify', 'kind': 'app', 'target': 'spotify', 'action': 'allow', 'scope_type': 'all'},
        ]:
            p_req = urllib.request.Request(
                f'{base}/api/policies',
                data=json.dumps(p).encode(),
                headers=headers,
            )
            urllib.request.urlopen(p_req, timeout=5)

        # 5. Configure Network Profile
        net_req = urllib.request.Request(
            f'{base}/api/network',
            data=json.dumps({
                'platform': 'mikrotik',
                'router_name': 'MikroTik CCR2004 Gateway',
                'management_ip': '192.168.88.1',
                'operating_mode': 'router',
                'guest_vlan': 50,
                'notes': 'RouterOS v7 HotSpot on ether3, bandwidth shaping active.',
            }).encode(),
            headers=headers,
            method='PATCH',
        )
        urllib.request.urlopen(net_req, timeout=5)

        # 6. Gateway key & heartbeat
        key_req = urllib.request.Request(f'{base}/api/settings/gateway-key', data=b'{}', headers=headers)
        with urllib.request.urlopen(key_req, timeout=5) as resp:
            gw_key = json.loads(resp.read().decode())['key']

        hb_req = urllib.request.Request(
            f'{base}/api/integrations/heartbeat',
            data=json.dumps({
                'name': 'MikroTik CCR2004 Gateway',
                'model': 'CCR2004-16G-2S+',
                'firmware': 'RouterOS v7.14.3',
                'ssid': 'MD_TECH',
                'lan_ip': '192.168.88.1',
                'wan_ip': '203.0.113.15',
                'uptime_seconds': 144000,
                'connected_clients': 14,
                'capabilities': ['captive_portal', 'disconnect', 'traffic', 'rate_limit'],
            }).encode(),
            headers={'Content-Type': 'application/json', 'X-Gateway-Key': gw_key},
        )
        urllib.request.urlopen(hb_req, timeout=5)

        print('Capturing screenshots with Edge headless...')
        # 1. Capture Guest Portal
        run_headless_edge(f'{base}/portal', DOCS_DIR / 'guest_portal.png', Path(edge_profile), budget_ms=1500)

        # 2. Capture Dashboard Overview
        run_headless_edge(
            f'{base}/api/auth/shot-auth?token={cookie_val}&page=dashboard',
            DOCS_DIR / 'dashboard_overview.png',
            Path(edge_profile),
            budget_ms=3000,
        )

        # 3. Capture Router & Network
        run_headless_edge(
            f'{base}/api/auth/shot-auth?token={cookie_val}&page=network',
            DOCS_DIR / 'router_network.png',
            Path(edge_profile),
            budget_ms=3000,
        )

        # 4. Capture Applications & Content Policies
        run_headless_edge(
            f'{base}/api/auth/shot-auth?token={cookie_val}&page=apps',
            DOCS_DIR / 'app_policies.png',
            Path(edge_profile),
            budget_ms=3000,
        )

        print('All screenshots generated successfully!')

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(edge_profile, ignore_errors=True)


if __name__ == '__main__':
    main()
