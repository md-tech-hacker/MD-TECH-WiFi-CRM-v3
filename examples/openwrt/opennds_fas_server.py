"""OpenWrt openNDS Forward Authentication Service (FAS) Server for MD TECH Wi-Fi CRM.

This lightweight service integrates OpenWrt's openNDS captive portal with the CRM:
1. Receives client redirects from openNDS with fas tokens (e.g. ?fas=<token>&authdir=<addr>).
2. Redirects the user to the CRM Guest Portal (/portal) with the session context.
3. Upon authenticated login, verifies the one-time bind token with the CRM (/api/integrations/bind).
4. Authorizes the client through openNDS via its local gateway port (default :2050/opennds_auth/).

Can run directly on OpenWrt routers with python3 or on an external management server.

Usage:
  export MDTECH_URL=http://192.168.1.50:8765
  export MDTECH_GATEWAY_KEY=<gateway-key>
  python3 opennds_fas_server.py --port 8080
"""
from __future__ import annotations
import argparse
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

CRM_URL = os.getenv('MDTECH_URL', 'http://127.0.0.1:8765').rstrip('/')
GATEWAY_KEY = os.getenv('MDTECH_GATEWAY_KEY', '')


class FASHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f'[FAS Server] {self.address_string()} - {format % args}')

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url_parts.query)

        # 1. OpenNDS Captive Portal Redirect
        # openNDS sends: ?fas=<token>&authdir=<url>&clientip=<ip>&gatewayname=<name>&hid=<hash>
        if 'fas' in params or 'clientip' in params:
            fas_token = params.get('fas', [''])[0]
            client_ip = params.get('clientip', [''])[0]
            gateway_hash = params.get('hid', [''])[0]
            
            # Forward the client to the CRM portal with query parameters
            portal_url = f'{CRM_URL}/portal?fas={urllib.parse.quote(fas_token)}&ip={urllib.parse.quote(client_ip)}&hid={urllib.parse.quote(gateway_hash)}'
            self.send_response(302)
            self.send_header('Location', portal_url)
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            return

        # 2. Authentication callback endpoint
        # The CRM portal or user calls this endpoint once login is completed with the bind token
        if url_parts.path == '/callback':
            bind_token = params.get('bind_token', [''])[0]
            session_id = params.get('session_id', [''])[0]
            mac = params.get('mac', [''])[0]
            ip = params.get('ip', [''])[0]

            if not (bind_token and session_id and mac):
                self.send_response(400)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'<h3>Missing authentication parameters.</h3>')
                return

            # Verify and bind the session in the CRM
            try:
                bind_payload = json.dumps({
                    'session_id': int(session_id),
                    'bind_token': bind_token,
                    'mac': mac,
                    'ip': ip,
                }).encode('utf-8')

                req = urllib.request.Request(
                    f'{CRM_URL}/api/integrations/bind',
                    data=bind_payload,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Gateway-Key': GATEWAY_KEY,
                    },
                    method='POST',
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    bind_res = json.loads(resp.read().decode('utf-8'))
                    if bind_res.get('ok'):
                        # Successfully bound in CRM. Now authorize in openNDS:
                        # Redirect client to openNDS auth URL
                        opennds_auth_url = f'http://{ip.rsplit(".", 1)[0]}.1:2050/opennds_auth/?tok={fas_token}'
                        self.send_response(302)
                        self.send_header('Location', opennds_auth_url)
                        self.end_headers()
                        return
            except Exception as exc:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Gateway binding failed: {exc}'.encode('utf-8'))
                return

        # Default fallback
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'<html><body><h2>MD TECH openNDS FAS Gateway Running</h2></body></html>')


def run(port: int = 8080):
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, FASHandler)
    print(f'Starting openNDS FAS server on 0.0.0.0:{port}...')
    print(f'Target CRM: {CRM_URL}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping FAS server.')
        httpd.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='openNDS FAS Server for MD TECH Wi-Fi CRM')
    parser.add_argument('--port', type=int, default=8080, help='Listening port (default 8080)')
    args = parser.parse_args()
    run(port=args.port)
