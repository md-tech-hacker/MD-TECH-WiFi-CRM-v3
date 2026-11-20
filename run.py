"""Windows/local launcher: python run.py"""
import os
import uvicorn

if __name__ == '__main__':
    host = os.getenv('MDTECH_HOST', '127.0.0.1')
    port = int(os.getenv('MDTECH_PORT', '8765'))
    print(f'\n  MD TECH Wi-Fi CRM → http://{host}:{port}\n')
    if host not in ('127.0.0.1', 'localhost', '::1'):
        print('WARNING: Remote logins over unencrypted HTTP are unsafe. Configure HTTPS before production use.\n')
    uvicorn.run('app.main:app', host=host, port=port, reload=False)
