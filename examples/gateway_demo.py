"""Development-only example. Not an actual router or network traffic interceptor.

Run the CRM, configure an API key in Settings, then:
  set MDTECH_GATEWAY_KEY=<key>   (Windows CMD)
  python examples/gateway_demo.py

This intentionally sends synthetic data so you can verify API integration.
"""
import json
import os
import urllib.error
import urllib.request

BASE=os.getenv('MDTECH_URL','http://127.0.0.1:8765')
KEY=os.getenv('MDTECH_GATEWAY_KEY','')
if not KEY: raise SystemExit('Set MDTECH_GATEWAY_KEY first. Create one under Settings.')

def post(path, payload):
    request=urllib.request.Request(BASE+path, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type':'application/json','X-Gateway-Key':KEY},method='POST')
    try:
        with urllib.request.urlopen(request, timeout=8) as response: return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'Gateway request failed: {exc.code} {exc.read().decode()}')

mac='02:00:00:00:00:77'  # Locally administered demo MAC
print('Synthetic device:',post('/api/integrations/event',{'type':'device_seen','mac':mac,'name':'DEMO device','ip':'192.0.2.44'}))
print('Synthetic 10 MB transfer:',post('/api/integrations/event',{'type':'traffic','mac':mac,'rx_bytes':10485760}))
print('Example request authorization:',post('/api/integrations/authorize',{'mac':mac,'ip':'192.0.2.44','domain':'youtube.com','require_active_session':False}))
print('REMINDER: This script never controls real devices or internet traffic.')
