"""MD TECH Open Wi-Fi CRM REST API and locally hosted web application.

Network enforcement requires an independently configured compatible gateway.
The portal alone cannot reconfigure or intercept a user's router.
"""
from __future__ import annotations

import csv
from contextlib import asynccontextmanager
import io
import ipaddress
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .db import DATA_DIR, ROOT, db, init_db, log, now, put_setting, row, rows, setting
from .policy import APP_DOMAINS, decide
from .network import inspect_host_network, probe_router, open_windows_settings
from .security import hash_password, new_token, rate_allowed, token_hash, utc_after, verify_password, voucher_digest

COOKIE = 'mdtech_session'
VERSION = '3.2.0'
MAX_SESSION_MIN = 12 * 60
DUMMY_PASSWORD_HASH = hash_password(new_token())
MAC_RE = re.compile(r'^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
ALLOWED_TABLES = {'users', 'vouchers', 'devices', 'guest_sessions', 'policies'}
@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield


app = FastAPI(title='MD TECH Open Wi-Fi CRM', version=VERSION, docs_url='/api/docs', redoc_url=None, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')


@app.middleware('http')
async def security_headers(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return Response('Cross-origin writes are not allowed', status_code=403)
        if origin:
            base = str(request.base_url).rstrip('/')
            proto = request.headers.get('x-forwarded-proto', request.url.scheme)
            host = request.headers.get('x-forwarded-host', request.headers.get('host', ''))
            proxy_base = f"{proto}://{host}".rstrip('/') if host else ''
            if origin != base and origin != proxy_base:
                return Response('Cross-origin writes are not allowed', status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    response.headers['Cache-Control'] = 'no-store'
    return response


def fail(code, message):
    raise HTTPException(status_code=code, detail=message)


def actor(request: Request, csrf=False):
    token = request.cookies.get(COOKIE, '')
    if not token:
        fail(401, 'Sign in to continue')
    with db() as conn:
        result = conn.execute('''SELECT a.id, a.username, s.csrf FROM admin_sessions s
             JOIN admins a ON a.id=s.admin_id WHERE s.token_hash=? AND s.expires_at > ?''',
             (token_hash(token), now())).fetchone()
    if not result:
        fail(401, 'Session expired; please sign in again')
    if csrf and not secrets.compare_digest(result['csrf'], request.headers.get('x-csrf-token', '')):
        fail(403, 'Invalid request token. Refresh the page.')
    return row(result)


def auth(request: Request):
    return actor(request)


def write_auth(request: Request):
    return actor(request, csrf=True)


def no_public_admin(data):
    return {k: v for k, v in data.items() if k not in ('password_hash', 'code_hash', 'bind_token_hash')}


def valid_mac(mac):
    mac = mac.strip().lower().replace('-', ':')
    if not MAC_RE.fullmatch(mac):
        fail(422, 'MAC address must look like aa:bb:cc:dd:ee:ff')
    return mac


def valid_ip(ip):
    ip = ip.strip()
    if ip:
        try: ipaddress.ip_address(ip)
        except ValueError: fail(422, 'Invalid IP address')
    return ip


def ensure_record(conn, table, ident):
    if table not in ALLOWED_TABLES:
        fail(500, 'Invalid entity')
    if not conn.execute(f'SELECT id FROM {table} WHERE id=?', (ident,)).fetchone():
        fail(404, f'{table[:-1].capitalize()} not found')


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=8, max_length=128)


class CreateAdmin(Credentials):
    password: str = Field(min_length=12, max_length=128)


class GuestUser(Credentials):
    display_name: str = Field(min_length=1, max_length=100)
    email: str = Field(default='', max_length=150)
    enabled: bool = True


class UserPatch(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=150)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    enabled: bool | None = None


class VoucherBatch(BaseModel):
    quantity: int = Field(default=1, ge=1, le=100)
    duration_minutes: int = Field(default=120, ge=5, le=525600)
    data_limit_mb: int = Field(default=0, ge=0, le=1000000)
    max_uses: int = Field(default=1, ge=1, le=1000)
    expires_days: int = Field(default=30, ge=1, le=3650)
    label: str = Field(default='', max_length=100)


class DeviceIn(BaseModel):
    mac: str
    name: str = Field(default='', max_length=100)
    ip: str = ''
    owner_id: int | None = None


class DevicePatch(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    ip: str | None = None
    owner_id: int | None = None
    blocked: bool | None = None


class PolicyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal['domain', 'app', 'ip', 'device']
    target: str = Field(min_length=1, max_length=200)
    action: Literal['block', 'allow'] = 'block'
    scope_type: Literal['all', 'user', 'device'] = 'all'
    scope_id: int | None = None
    enabled: bool = True


class SettingsIn(BaseModel):
    site_name: str = Field(min_length=1, max_length=80)
    ssid: str = Field(default='', max_length=32)
    portal_title: str = Field(min_length=1, max_length=120)
    portal_message: str = Field(default='', max_length=300)
    gateway_enabled: bool = False


class PortalLogin(BaseModel):
    method: Literal['voucher', 'account']
    code: str = Field(default='', max_length=100)
    username: str = Field(default='', max_length=64)
    password: str = Field(default='', max_length=128)
    mac: str = Field(default='', max_length=20)
    device_name: str = Field(default='', max_length=100)


class GatewayEvent(BaseModel):
    type: Literal['device_seen', 'traffic', 'blocked_request', 'session_disconnected']
    mac: str
    ip: str = ''
    name: str = Field(default='', max_length=100)
    rx_bytes: int = Field(default=0, ge=0, le=10**12)
    tx_bytes: int = Field(default=0, ge=0, le=10**12)
    session_id: int | None = None
    domain: str = Field(default='', max_length=255)


class GatewayBind(BaseModel):
    session_id: int = Field(gt=0)
    bind_token: str = Field(min_length=32, max_length=128)
    mac: str
    ip: str = ''
    name: str = Field(default='', max_length=100)


class GatewayHeartbeat(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    model: str = Field(default='', max_length=100)
    firmware: str = Field(default='', max_length=100)
    ssid: str = Field(default='', max_length=32)
    lan_ip: str = Field(default='', max_length=45)
    wan_ip: str = Field(default='', max_length=45)
    uptime_seconds: int = Field(default=0, ge=0)
    connected_clients: int = Field(default=0, ge=0)
    capabilities: list[Literal['captive_portal', 'disconnect', 'dns_filter', 'traffic', 'rate_limit']] = Field(default_factory=list, max_length=5)


class NetworkProfile(BaseModel):
    platform: Literal['unconfigured', 'mikrotik', 'openwrt', 'opnsense', 'pfsense', 'unifi', 'omada', 'generic_linux', 'tplink_wr841n_v14', 'other'] = 'unconfigured'
    router_name: str = Field(default='', max_length=100)
    management_ip: str = Field(default='', max_length=45)
    upstream_ssid: str = Field(default='', max_length=32)
    operating_mode: Literal['unknown', 'ap', 'wisp', 'router', 'extender'] = 'unknown'
    firmware_version: str = Field(default='', max_length=100)
    guest_vlan: int | None = Field(default=None, ge=1, le=4094)
    notes: str = Field(default='', max_length=1000)


class WindowsSettingsIn(BaseModel):
    page: Literal['location', 'wifi', 'ethernet']


class GatewayDecision(BaseModel):
    mac: str = ''
    ip: str = ''
    domain: str = Field(default='', max_length=255)
    app: str = Field(default='', max_length=100)
    user_id: int | None = None
    require_active_session: bool = True


@app.get('/', include_in_schema=False)
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/portal', include_in_schema=False)
def portal():
    return FileResponse(ROOT / 'static' / 'portal.html')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': VERSION}


@app.get('/api/auth/status')
def auth_status(request: Request):
    with db() as conn:
        ready = conn.execute('SELECT EXISTS(SELECT 1 FROM admins)').fetchone()[0]
    if not ready:
        return {'configured': False, 'authenticated': False}
    try:
        a = actor(request)
        return {'configured': True, 'authenticated': True, 'username': a['username'], 'csrf': a['csrf']}
    except HTTPException:
        return {'configured': True, 'authenticated': False}


@app.get('/api/auth/shot-auth')
def shot_auth(token: str, page: str = 'dashboard', request: Request = None):
    remote = request.client.host if request and request.client else ''
    try:
        addr = ipaddress.ip_address(remote)
        if not addr.is_loopback:
            fail(403, 'Loopback only')
    except ValueError:
        fail(403, 'Loopback only')
    with db() as conn:
        session = conn.execute(
            'SELECT s.csrf, a.username FROM admin_sessions s JOIN admins a ON a.id=s.admin_id WHERE s.token_hash=? AND s.expires_at > ?',
            (token_hash(token), now())
        ).fetchone()
    if not session:
        fail(401, 'Invalid session token')
    target = f'/?page={page}' if page in ('dashboard', 'network', 'users', 'vouchers', 'devices', 'policies', 'apps', 'sessions', 'reports', 'activity', 'settings') else '/'
    resp = RedirectResponse(url=target, status_code=302)
    resp.set_cookie(COOKIE, token, httponly=True, secure=False, samesite='lax', path='/')
    return resp


@app.post('/api/auth/setup')
def setup(data: CreateAdmin, request: Request, response: Response):
    remote = request.client.host if request.client else ''
    try:
        addr = ipaddress.ip_address(remote)
        allow_docker = os.getenv('ALLOW_DOCKER_SETUP', '0') == '1' and addr.is_private
        local = addr.is_loopback or allow_docker
    except ValueError:
        local = False
    if not local:
        fail(403, 'Create the initial administrator from this computer at http://127.0.0.1:8765')
    if not rate_allowed('setup:' + (request.client.host if request.client else 'unknown'), 8):
        fail(429, 'Too many attempts; please try later')
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM admins LIMIT 1').fetchone():
            fail(409, 'Initial setup is already completed')
        conn.execute('INSERT INTO admins(username,password_hash,created_at) VALUES(?,?,?)',
                     (data.username.lower(), hash_password(data.password), now()))
        log(conn, 'Initial admin created', data.username, 'setup', 'security')
    return create_login_session(data.username.lower(), response, request)


def create_login_session(username, response, request):
    token = new_token()
    csrf = new_token()
    with db() as conn:
        admin = conn.execute('SELECT id,username FROM admins WHERE username=?', (username,)).fetchone()
        if not admin: fail(401, 'Invalid credentials')
        conn.execute('INSERT INTO admin_sessions(admin_id,token_hash,csrf,expires_at,created_at) VALUES (?,?,?,?,?)',
                     (admin['id'], token_hash(token), csrf, utc_after(MAX_SESSION_MIN), now()))
        log(conn, 'Admin signed in', username, username, 'security')
    is_secure = request.url.scheme == 'https' or request.headers.get('x-forwarded-proto') == 'https'
    response.set_cookie(COOKIE, token, httponly=True, secure=is_secure, samesite='strict', max_age=MAX_SESSION_MIN*60, path='/')
    return {'authenticated': True, 'username': username, 'csrf': csrf}


@app.post('/api/auth/login')
def login(data: Credentials, request: Request, response: Response):
    remote = request.client.host if request.client else 'unknown'
    if not rate_allowed('login-ip:' + remote, 30) or not rate_allowed('login-account:' + data.username.lower(), 20):
        fail(429, 'Too many login attempts; try again later')
    key = 'login:' + (request.client.host if request.client else 'unknown') + ':' + data.username.lower()
    if not rate_allowed(key, 10):
        fail(429, 'Too many login attempts; try again later')
    with db() as conn:
        admin = conn.execute('SELECT * FROM admins WHERE username=?', (data.username.lower(),)).fetchone()
    password_valid = verify_password(data.password, admin['password_hash'] if admin else DUMMY_PASSWORD_HASH)
    if not admin or not password_valid:
        fail(401, 'Incorrect username or password')
    return create_login_session(admin['username'], response, request)


@app.post('/api/auth/logout')
def logout(request: Request, response: Response, a=Depends(write_auth)):
    with db() as conn:
        conn.execute('DELETE FROM admin_sessions WHERE token_hash=?', (token_hash(request.cookies.get(COOKIE,'')),))
        log(conn, 'Admin signed out', '', a['username'], 'security')
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}


@app.post('/api/auth/password')
def change_password(data: dict, request: Request, a=Depends(write_auth)):
    if not rate_allowed('password:' + str(a['id']), 8):
        fail(429, 'Too many password attempts; try again later')
    old, new = data.get('current_password',''), data.get('new_password','')
    if not isinstance(new, str) or len(new) < 12 or len(new) > 128:
        fail(422, 'New password must be between 12 and 128 characters')
    with db() as conn:
        r = conn.execute('SELECT password_hash FROM admins WHERE id=?', (a['id'],)).fetchone()
        if not verify_password(str(old), r['password_hash']): fail(403, 'Incorrect current password')
        conn.execute('UPDATE admins SET password_hash=? WHERE id=?', (hash_password(new), a['id']))
        conn.execute('DELETE FROM admin_sessions WHERE admin_id=? AND token_hash<>?', (a['id'], token_hash(request.cookies.get(COOKIE, ''))))
        log(conn, 'Admin password changed', '', a['username'], 'security')
    return {'ok': True}


@app.get('/api/dashboard')
def dashboard(a=Depends(auth)):
    with db() as conn:
        counts = {}
        for key, sql in {
            'users': 'SELECT COUNT(*) FROM users WHERE enabled=1',
            'devices': 'SELECT COUNT(*) FROM devices',
            'blocked_devices': 'SELECT COUNT(*) FROM devices WHERE blocked=1',
            'vouchers': 'SELECT COUNT(*) FROM vouchers WHERE enabled=1 AND used_count<max_uses',
            'sessions': "SELECT COUNT(*) FROM guest_sessions WHERE state='authorized' AND expires_at>?",
            'policies': 'SELECT COUNT(*) FROM policies WHERE enabled=1',
            'blocks_today': "SELECT COUNT(*) FROM activity WHERE category='blocked' AND created_at >= ?"
        }.items():
            params = (now(),) if key == 'sessions' else ((now()[:10],) if key == 'blocks_today' else ())
            counts[key] = conn.execute(sql, params).fetchone()[0]
        total = conn.execute('SELECT COALESCE(SUM(rx_bytes+tx_bytes),0) FROM devices').fetchone()[0]
        last_events = rows(conn.execute('SELECT * FROM activity ORDER BY id DESC LIMIT 8'))
        newest = rows(conn.execute('SELECT d.*,u.username AS owner FROM devices d LEFT JOIN users u ON u.id=d.owner_id ORDER BY d.last_seen DESC LIMIT 6'))
        graph = []
        for offset in range(6, -1, -1):
            date = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
            b = conn.execute('SELECT COALESCE(SUM(rx_bytes+tx_bytes),0) FROM traffic WHERE substr(created_at,1,10)=?', (date,)).fetchone()[0]
            graph.append({'date': date, 'bytes': b})
        connected = setting(conn, 'gateway_enabled') == '1'
        label = setting(conn, 'gateway_label')
    return {'counts': counts, 'total_bytes': total, 'recent_activity': last_events,
            'recent_devices': newest, 'traffic_chart': graph, 'gateway_enabled': connected,
            'gateway_label': label}


@app.get('/api/users')
def list_users(a=Depends(auth)):
    with db() as conn:
        users = rows(conn.execute('''SELECT u.id,u.username,u.display_name,u.email,u.enabled,u.created_at,u.last_login_at,
         (SELECT COUNT(*) FROM devices d WHERE d.owner_id=u.id) AS devices_count
         FROM users u ORDER BY u.id DESC'''))
    return users


@app.post('/api/users', status_code=201)
def create_user(data: GuestUser, a=Depends(write_auth)):
    with db() as conn:
        try:
            cur = conn.execute('INSERT INTO users(username,display_name,password_hash,email,enabled,created_at) VALUES(?,?,?,?,?,?)',
                   (data.username.lower(), data.display_name, hash_password(data.password), data.email, int(data.enabled), now()))
        except sqlite3.IntegrityError:
            fail(409, 'Username already exists')
        log(conn, 'Guest account created', data.username, a['username'], 'users')
    return {'id': cur.lastrowid, 'ok': True}


@app.patch('/api/users/{ident}')
def update_user(ident: int, data: UserPatch, a=Depends(write_auth)):
    fields = data.model_dump(exclude_unset=True)
    if not fields: fail(400, 'Nothing to update')
    if any(v is None for v in fields.values()): fail(422, 'Null updates are not supported')
    if 'password' in fields: fields['password_hash'] = hash_password(fields.pop('password'))
    if 'username' in fields and fields['username'] is not None: fields['username'] = fields['username'].lower()
    if 'enabled' in fields: fields['enabled'] = int(fields['enabled'])
    if any(v is None for v in fields.values()): fail(422, 'Null updates are not supported')
    with db() as conn:
        ensure_record(conn, 'users', ident)
        try: conn.execute('UPDATE users SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', tuple(fields.values()) + (ident,))
        except sqlite3.IntegrityError: fail(409, 'Username already exists')
        if fields.get('enabled') == 0 or 'password_hash' in fields:
            conn.execute("UPDATE guest_sessions SET state='revoked',ended_at=? WHERE user_id=? AND state='authorized'", (now(), ident))
        log(conn, 'Guest account updated', f'User #{ident}: {", ".join(fields)}', a['username'], 'users')
    return {'ok': True}


@app.delete('/api/users/{ident}')
def delete_user(ident: int, a=Depends(write_auth)):
    with db() as conn:
        ensure_record(conn, 'users', ident)
        conn.execute("UPDATE guest_sessions SET state='revoked',ended_at=? WHERE user_id=? AND state='authorized'", (now(), ident))
        conn.execute('DELETE FROM users WHERE id=?', (ident,))
        log(conn, 'Guest account deleted', f'User #{ident}', a['username'], 'users')
    return {'ok': True}


@app.get('/api/vouchers')
def list_vouchers(a=Depends(auth)):
    with db() as conn:
        return rows(conn.execute('''SELECT id,code_hint,label,duration_minutes,data_limit_mb,max_uses,
                   used_count,enabled,expires_at,created_at FROM vouchers ORDER BY id DESC LIMIT 500'''))


@app.post('/api/vouchers', status_code=201)
def create_vouchers(data: VoucherBatch, a=Depends(write_auth)):
    codes = []
    expires = utc_after(data.expires_days * 1440)
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    with db() as conn:
        for _ in range(data.quantity):
            code = 'MD-' + ''.join(secrets.choice(alphabet) for _ in range(10))
            cur = conn.execute('''INSERT INTO vouchers(code_hash,code_hint,label,duration_minutes,data_limit_mb,
                max_uses,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?)''',
                (voucher_digest(code), code[-4:], data.label, data.duration_minutes,
                 data.data_limit_mb, data.max_uses, expires, now()))
            codes.append({'id': cur.lastrowid, 'code': code})
        log(conn, 'Vouchers generated', f'{data.quantity} codes / {data.duration_minutes} minutes', a['username'], 'vouchers')
    # Codes are revealed exactly once. Only keyed digests are retained.
    return {'codes': codes, 'expires_at': expires}


@app.patch('/api/vouchers/{ident}')
def toggle_voucher(ident: int, data: dict, a=Depends(write_auth)):
    enabled = data.get('enabled')
    if not isinstance(enabled, bool): fail(422, 'enabled must be a boolean')
    with db() as conn:
        ensure_record(conn, 'vouchers', ident)
        conn.execute('UPDATE vouchers SET enabled=? WHERE id=?', (int(enabled), ident))
        if not enabled:
            conn.execute("UPDATE guest_sessions SET state='revoked',ended_at=? WHERE voucher_id=? AND state='authorized'", (now(), ident))
        log(conn, 'Voucher status changed', f'Voucher #{ident}: {"active" if enabled else "disabled"}', a['username'], 'vouchers')
    return {'ok': True}


@app.get('/api/devices')
def list_devices(a=Depends(auth)):
    with db() as conn:
        return rows(conn.execute('''SELECT d.*,u.username AS owner FROM devices d
             LEFT JOIN users u ON d.owner_id=u.id ORDER BY d.last_seen DESC'''))


@app.post('/api/devices', status_code=201)
def create_device(data: DeviceIn, a=Depends(write_auth)):
    mac, ip = valid_mac(data.mac), valid_ip(data.ip)
    with db() as conn:
        if data.owner_id is not None: ensure_record(conn, 'users', data.owner_id)
        try:
            cur = conn.execute('''INSERT INTO devices(mac,name,ip,owner_id,first_seen,last_seen)
                        VALUES(?,?,?,?,?,?)''', (mac, data.name or mac, ip, data.owner_id, now(), now()))
        except sqlite3.IntegrityError: fail(409, 'MAC address already exists')
        log(conn, 'Device enrolled', mac, a['username'], 'devices')
    return {'id': cur.lastrowid, 'ok': True}


@app.patch('/api/devices/{ident}')
def update_device(ident: int, data: DevicePatch, a=Depends(write_auth)):
    fields = data.model_dump(exclude_unset=True)
    if not fields: fail(400, 'Nothing to update')
    if any(v is None for k, v in fields.items() if k != 'owner_id'):
        fail(422, 'Only the owner account can be cleared')
    if 'ip' in fields and fields['ip'] is not None: fields['ip'] = valid_ip(fields['ip'])
    if 'blocked' in fields: fields['blocked'] = int(fields['blocked'])
    if 'name' in fields and fields['name'] is None: fail(422, 'Invalid device name')
    with db() as conn:
        ensure_record(conn, 'devices', ident)
        if fields.get('owner_id') is not None: ensure_record(conn, 'users', fields['owner_id'])
        conn.execute('UPDATE devices SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', tuple(fields.values()) + (ident,))
        log(conn, 'Device updated', f'Device #{ident}: {", ".join(fields)}', a['username'], 'devices')
    return {'ok': True}


@app.delete('/api/devices/{ident}')
def delete_device(ident: int, a=Depends(write_auth)):
    with db() as conn:
        ensure_record(conn, 'devices', ident)
        conn.execute('DELETE FROM devices WHERE id=?', (ident,))
        log(conn, 'Device removed', f'Device #{ident}', a['username'], 'devices')
    return {'ok': True}


@app.get('/api/sessions')
def sessions(a=Depends(auth)):
    with db() as conn:
        return [no_public_admin(r) for r in rows(conn.execute('''SELECT s.*,u.username, v.code_hint, d.name AS device_name, d.mac
            FROM guest_sessions s LEFT JOIN users u ON s.user_id=u.id
            LEFT JOIN vouchers v ON v.id=s.voucher_id
            LEFT JOIN devices d ON d.id=s.device_id ORDER BY s.id DESC LIMIT 500'''))]


@app.post('/api/sessions/{ident}/disconnect')
def disconnect_session(ident: int, a=Depends(write_auth)):
    with db() as conn:
        ensure_record(conn, 'guest_sessions', ident)
        conn.execute("UPDATE guest_sessions SET state='revoked', ended_at=? WHERE id=? AND state='authorized'", (now(), ident))
        log(conn, 'Session revoked', f'Session #{ident}', a['username'], 'sessions')
    return {'ok': True}


def validate_policy(data: PolicyIn, conn):
    t = data.target.strip().lower()
    if data.kind == 'ip':
        try: ipaddress.ip_network(t, strict=False)
        except ValueError: fail(422, 'IP target must be an IP or CIDR network')
    elif data.kind == 'device':
        t = valid_mac(t)
    elif data.kind == 'domain':
        if len(t) > 253 or not re.fullmatch(r'(?=.{1,253}$)(?:[a-z0-9-]+\.)*[a-z0-9-]+', t):
            fail(422, 'Enter a valid hostname such as youtube.com')
    elif data.kind == 'app':
        if t not in APP_DOMAINS: fail(422, 'Unsupported application preset')
    if data.scope_type != 'all':
        if not data.scope_id: fail(422, 'Choose a user or device for this scope')
        ensure_record(conn, 'users' if data.scope_type == 'user' else 'devices', data.scope_id)
    return t


@app.get('/api/policies')
def policies(a=Depends(auth)):
    with db() as conn:
        return rows(conn.execute('SELECT * FROM policies ORDER BY id DESC'))


@app.post('/api/policies', status_code=201)
def create_policy(data: PolicyIn, a=Depends(write_auth)):
    with db() as conn:
        target = validate_policy(data, conn)
        cur = conn.execute('''INSERT INTO policies(name,kind,target,action,scope_type,scope_id,enabled,created_at)
              VALUES(?,?,?,?,?,?,?,?)''', (data.name, data.kind, target, data.action, data.scope_type,
                                      data.scope_id if data.scope_type != 'all' else None, int(data.enabled), now()))
        log(conn, 'Policy created', f'{data.action} {data.kind}: {target}', a['username'], 'policies')
    return {'id': cur.lastrowid, 'ok': True}


@app.patch('/api/policies/{ident}')
def update_policy(ident: int, data: dict, a=Depends(write_auth)):
    if set(data) != {'enabled'} or not isinstance(data['enabled'], bool):
        fail(422, 'Only enabled can be updated')
    with db() as conn:
        ensure_record(conn, 'policies', ident)
        conn.execute('UPDATE policies SET enabled=? WHERE id=?', (int(data['enabled']), ident))
        log(conn, 'Policy status changed', f'Policy #{ident}: {data["enabled"]}', a['username'], 'policies')
    return {'ok': True}


@app.delete('/api/policies/{ident}')
def delete_policy(ident: int, a=Depends(write_auth)):
    with db() as conn:
        ensure_record(conn, 'policies', ident)
        conn.execute('DELETE FROM policies WHERE id=?', (ident,))
        log(conn, 'Policy deleted', f'Policy #{ident}', a['username'], 'policies')
    return {'ok': True}


@app.get('/api/activity')
def activity(a=Depends(auth)):
    with db() as conn:
        return rows(conn.execute('SELECT * FROM activity ORDER BY id DESC LIMIT 300'))


@app.get('/api/settings')
def get_settings(a=Depends(auth)):
    with db() as conn:
        return {key: setting(conn, key) for key in ('site_name','ssid','portal_title','portal_message','gateway_enabled','gateway_label')} | {
            'gateway_enabled': setting(conn, 'gateway_enabled') == '1',
            'gateway_key_created': bool(setting(conn, 'gateway_key_hash')),
            'app_presets': sorted(APP_DOMAINS), 'app_domains': APP_DOMAINS
        }


@app.patch('/api/settings')
def save_settings(data: SettingsIn, a=Depends(write_auth)):
    with db() as conn:
        for key in ('site_name','ssid','portal_title','portal_message'):
            put_setting(conn, key, getattr(data, key))
        put_setting(conn, 'gateway_enabled', str(int(data.gateway_enabled)))
        log(conn, 'Settings updated', f'SSID label: {data.ssid}; gateway enabled: {data.gateway_enabled}', a['username'], 'settings')
    return {'ok': True}


@app.post('/api/settings/gateway-key')
def generate_gateway_key(a=Depends(write_auth)):
    key = new_token()
    with db() as conn:
        put_setting(conn, 'gateway_key_hash', token_hash(key))
        put_setting(conn, 'gateway_enabled', '1')
        put_setting(conn, 'gateway_heartbeat', '')
        log(conn, 'Gateway API key rotated', 'Previous gateway key invalidated', a['username'], 'security')
    return {'key': key, 'warning': 'Copy this secret now. It will not be displayed again.'}


@app.get('/api/portal/config')
def guest_config():
    with db() as conn:
        return {key: setting(conn, key) for key in ('site_name','portal_title','portal_message')} | {
            'ssid': network_status(conn)['observed_ssid'] or '', 'network_label': setting(conn, 'ssid')}


def upsert_seen(conn, mac, name='', ip='', source='gateway'):
    mac = valid_mac(mac)
    ip = valid_ip(ip)
    existing = conn.execute('SELECT id FROM devices WHERE mac=?', (mac,)).fetchone()
    if existing:
        conn.execute('''UPDATE devices SET last_seen=?,ip=CASE WHEN ?<>'' THEN ? ELSE ip END,
             name=CASE WHEN ?<>'' THEN ? ELSE name END,
             source=CASE WHEN ?='gateway' THEN 'gateway' ELSE source END WHERE id=?''', (now(), ip, ip, name, name, source, existing['id']))
        return existing['id']
    return conn.execute('''INSERT INTO devices(mac,name,ip,source,first_seen,last_seen)
                      VALUES(?,?,?,?,?,?)''', (mac, name or mac, ip, source, now(), now())).lastrowid


@app.post('/api/portal/login')
def guest_login(data: PortalLogin, request: Request):
    remote = request.client.host if request.client else 'unknown'
    if not rate_allowed('portal:' + remote, 15, 300):
        fail(429, 'Too many attempts; please wait a few minutes')
    bind_token = new_token()
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        user_id, voucher_id, minutes = None, None, 120
        if data.method == 'voucher':
            if not data.code: fail(422, 'Enter your access code')
            v = conn.execute('SELECT * FROM vouchers WHERE code_hash=?', (voucher_digest(data.code),)).fetchone()
            if not v or not v['enabled'] or v['used_count'] >= v['max_uses'] or (v['expires_at'] and v['expires_at'] < now()):
                fail(401, 'Invalid, expired, or used-up access code')
            voucher_id, minutes = v['id'], v['duration_minutes']
            conn.execute('UPDATE vouchers SET used_count=used_count+1 WHERE id=?', (voucher_id,))
        else:
            u = conn.execute('SELECT * FROM users WHERE username=? AND enabled=1', (data.username.lower(),)).fetchone()
            password_valid = verify_password(data.password, u['password_hash'] if u else DUMMY_PASSWORD_HASH)
            if not u or not password_valid:
                fail(401, 'Invalid username or password')
            user_id = u['id']
            conn.execute('UPDATE users SET last_login_at=? WHERE id=?', (now(), user_id))
        device_id = None
        if data.mac:
            # A guest-provided MAC is untrusted; a gateway must independently verify ownership.
            mac = valid_mac(data.mac)
            existing = conn.execute('SELECT id FROM devices WHERE mac=?', (mac,)).fetchone()
            device_id = existing['id'] if existing else upsert_seen(conn, mac, data.device_name, source='portal-unverified')
            blocked = conn.execute('SELECT blocked FROM devices WHERE id=?', (device_id,)).fetchone()['blocked']
            if blocked: fail(403, 'This device is restricted')
        expires = utc_after(minutes)
        sid = conn.execute('''INSERT INTO guest_sessions(user_id,voucher_id,device_id,client_ip,
               login_method,started_at,expires_at) VALUES(?,?,?,?,?,?,?)''',
               (user_id, voucher_id, device_id, remote, data.method, now(), expires)).lastrowid
        conn.execute('UPDATE guest_sessions SET bind_token_hash=? WHERE id=?', (token_hash(bind_token), sid))
        log(conn, 'Guest authenticated (software only)', f'Session #{sid}, method: {data.method}', 'portal', 'sessions')
    return {'ok': True, 'session_id': sid, 'expires_at': expires, 'bind_token': bind_token,
            'message': 'Your credentials were accepted. Actual Wi-Fi access depends on a configured compatible gateway.'}


def require_gateway(request: Request):
    remote = request.client.host if request.client else 'unknown'
    key = request.headers.get('x-gateway-key', '')
    with db() as conn:
        enabled = setting(conn, 'gateway_enabled') == '1'
        expected = setting(conn, 'gateway_key_hash')
    if not enabled or not expected or not key or not secrets.compare_digest(token_hash(key), expected):
        if not rate_allowed('gateway-auth-fail:' + remote, 10, 60):
            fail(429, 'Too many failed gateway requests; please wait')
        fail(401, 'Gateway authentication required')
    return True


def network_status(conn):
    profile = json.loads(setting(conn, 'network_profile', '{}'))
    raw = setting(conn, 'gateway_heartbeat')
    heartbeat = json.loads(raw) if raw else None
    age = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat['received_at'])).total_seconds())) if heartbeat else None
    enabled = setting(conn, 'gateway_enabled') == '1'
    management_ip = profile.get('management_ip', '')
    management_url = ('http://[' + management_ip + ']/' if ':' in management_ip else 'http://' + management_ip + '/') if management_ip and '%' not in management_ip else None
    connection = json.loads(setting(conn, 'router_connection_check', 'null'))
    return {'profile': profile, 'telemetry': heartbeat, 'age_seconds': age, 'management_url': management_url, 'connection_check': connection,
            'observed_ssid': heartbeat.get('ssid') if heartbeat and enabled and age <= 90 else None,
            'status': 'disabled' if not enabled else ('not_reporting' if heartbeat is None else ('reporting' if age <= 90 else 'stale')),
            'gateway_enabled': enabled, 'enforcement_verified': False}


@app.get('/api/network')
def get_network(a=Depends(auth)):
    with db() as conn:
        return network_status(conn)


@app.get('/api/network/host')
def get_host_network(refresh: bool = False, a=Depends(auth)):
    if not rate_allowed('host-network:' + str(a['id']), 12, 60):
        fail(429, 'Please wait before refreshing host network details')
    return inspect_host_network(force=True) if refresh else inspect_host_network()


@app.post('/api/network/windows-settings')
def launch_windows_settings(data: WindowsSettingsIn, request: Request, a=Depends(write_auth)):
    try:
        local = bool(request.client and ipaddress.ip_address(request.client.host).is_loopback)
    except ValueError:
        local = False
    if not local:
        fail(403, 'Open Windows settings directly on the computer running this CRM')
    if not rate_allowed('windows-settings:' + str(a['id']), 8, 60):
        fail(429, 'Please wait before opening another Windows settings page')
    try:
        return open_windows_settings(data.page)
    except (OSError, ValueError):
        fail(503, 'Windows settings could not be opened here. Use the Windows settings links on this computer.')


@app.post('/api/network/check')
def check_router_connection(a=Depends(write_auth)):
    if not rate_allowed('router-check:' + str(a['id']), 6, 60):
        fail(429, 'Please wait before testing this connection again')
    with db() as conn:
        profile = json.loads(setting(conn, 'network_profile', '{}'))
        address = profile.get('management_ip', '')
        platform_choice = profile.get('platform', '')
    if not address:
        fail(422, 'Enter and save the router management IP first')
    ports = (80, 443)
    if platform_choice == 'mikrotik':
        ports = (80, 443, 8728)
    elif platform_choice in ('unifi', 'omada'):
        ports = (80, 443, 8443)
    try:
        result = probe_router(address, ports=ports) if ports != (80, 443) else probe_router(address)
    except TypeError:
        result = probe_router(address)
    except ValueError as exc:
        fail(422, str(exc))
    with db() as conn:
        # Ignore a probe if another admin request changed the saved target meanwhile.
        if json.loads(setting(conn, 'network_profile', '{}')).get('management_ip') == address:
            put_setting(conn, 'router_connection_check', json.dumps(result))
    return result


@app.patch('/api/network')
def save_network(data: NetworkProfile, a=Depends(write_auth)):
    valid_ip(data.management_ip)
    if data.management_ip and ('%' in data.management_ip or not ipaddress.ip_address(data.management_ip).is_private or ipaddress.ip_address(data.management_ip).is_unspecified or ipaddress.ip_address(data.management_ip).is_multicast):
        fail(422, 'Use the router’s private LAN management IP')
    with db() as conn:
        previous = json.loads(setting(conn, 'network_profile', '{}'))
        if previous.get('management_ip') != data.management_ip:
            put_setting(conn, 'router_connection_check', 'null')
        put_setting(conn, 'network_profile', data.model_dump_json())
        log(conn, 'Network profile updated', data.platform, a['username'], 'settings')
    return {'ok': True}


@app.post('/api/integrations/heartbeat')
def gateway_heartbeat(data: GatewayHeartbeat, gateway=Depends(require_gateway)):
    valid_ip(data.lan_ip)
    valid_ip(data.wan_ip)
    with db() as conn:
        put_setting(conn, 'gateway_heartbeat', json.dumps(data.model_dump() | {'received_at': now()}))
    return {'ok': True, 'heartbeat_interval_seconds': 30}


@app.post('/api/integrations/event')
def gateway_event(data: GatewayEvent, gateway=Depends(require_gateway)):
    mac, ip = valid_mac(data.mac), valid_ip(data.ip)
    with db() as conn:
        device_id = upsert_seen(conn, mac, data.name, ip)
        if data.type == 'traffic':
            conn.execute('UPDATE devices SET rx_bytes=rx_bytes+?, tx_bytes=tx_bytes+? WHERE id=?',
                         (data.rx_bytes, data.tx_bytes, device_id))
            conn.execute('INSERT INTO traffic(created_at,device_id,rx_bytes,tx_bytes) VALUES(?,?,?,?)',
                         (now(), device_id, data.rx_bytes, data.tx_bytes))
            if data.session_id:
                conn.execute('''UPDATE guest_sessions SET rx_bytes=rx_bytes+?,tx_bytes=tx_bytes+?
                               WHERE id=? AND device_id=? AND state='authorized' ''',
                             (data.rx_bytes, data.tx_bytes, data.session_id, device_id))
        elif data.type == 'blocked_request':
            log(conn, 'Request blocked by gateway', f'{mac}: {data.domain}', 'gateway', 'blocked')
            conn.execute('INSERT INTO traffic(created_at,device_id,blocked) VALUES(?,?,1)', (now(),device_id))
        elif data.type == 'session_disconnected' and data.session_id:
            conn.execute("UPDATE guest_sessions SET state='ended',ended_at=? WHERE id=? AND device_id=?",
                         (now(), data.session_id, device_id))
        elif data.type == 'device_seen':
            log(conn, 'Device discovered', f'{mac}: {data.name}', 'gateway', 'devices')
        put_setting(conn, 'gateway_label', 'Gateway telemetry received ' + now())
    return {'ok': True, 'device_id': device_id}


@app.post('/api/integrations/bind')
def gateway_bind(data: GatewayBind, gateway=Depends(require_gateway)):
    """Associate a portal-created session with a MAC VERIFIED BY THE GATEWAY.

    Integration implementers must independently authenticate the station and
    session request. Never accept a client-supplied MAC as proof of identity.
    """
    mac, ip = valid_mac(data.mac), valid_ip(data.ip)
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        session = conn.execute("SELECT * FROM guest_sessions WHERE id=? AND state=\'authorized\' AND expires_at>?",
                               (data.session_id, now())).fetchone()
        if not session: fail(404, 'Active session not found')
        if not session['bind_token_hash'] or not secrets.compare_digest(session['bind_token_hash'], token_hash(data.bind_token)):
            fail(403, 'Invalid or already consumed session binding proof')
        device_id = upsert_seen(conn, mac, data.name, ip)
        if conn.execute('SELECT blocked FROM devices WHERE id=?',(device_id,)).fetchone()['blocked']:
            fail(403, 'Device is blocked')
        if session['device_id'] and session['device_id'] != device_id:
            fail(409, 'Session already bound to a different device')
        conn.execute("UPDATE guest_sessions SET device_id=?,gateway_verified=1,bind_token_hash='' WHERE id=?", (device_id, data.session_id))
        log(conn, 'Gateway verified session binding', f'Session #{data.session_id} -> {mac}', 'gateway', 'sessions')
    return {'ok': True, 'device_id': device_id}


@app.get('/api/integrations/state')
def gateway_state(gateway=Depends(require_gateway)):
    with db() as conn:
        blocked = [r['mac'] for r in conn.execute('SELECT mac FROM devices WHERE blocked=1')]
        revoked = [r['id'] for r in conn.execute("SELECT id FROM guest_sessions WHERE state='revoked' OR expires_at<=?", (now(),))]
    return {'blocked_macs': blocked, 'revoked_session_ids': revoked, 'checked_at': now()}


@app.post('/api/integrations/authorize')
def gateway_authorize(data: GatewayDecision, gateway=Depends(require_gateway)):
    mac = valid_mac(data.mac) if data.mac else ''
    ip = valid_ip(data.ip)
    with db() as conn:
        device = conn.execute('SELECT * FROM devices WHERE mac=?', (mac,)).fetchone() if mac else None
        device_id = device['id'] if device else None
        active = conn.execute('''SELECT s.*,v.data_limit_mb,v.enabled AS voucher_enabled,
                v.expires_at AS voucher_expires,u.enabled AS user_enabled
                FROM guest_sessions s LEFT JOIN vouchers v ON v.id=s.voucher_id
                LEFT JOIN users u ON u.id=s.user_id
                WHERE s.device_id=? AND s.gateway_verified=1 AND s.state='authorized' AND s.expires_at>?
                ORDER BY s.id DESC LIMIT 1''', (device_id, now())).fetchone() if device_id else None
        # Network identity comes from the verified session, never an asserted owner.
        user_id = active['user_id'] if active else None
        if not data.require_active_session:
            user_id = data.user_id  # Explicit policy evaluation mode for trusted adapters.
        rules = rows(conn.execute('SELECT * FROM policies WHERE enabled=1'))
        result = decide(rules, mac=mac, ip=ip, domain=data.domain, app=data.app,
                        user_id=user_id, device_id=device_id, device_blocked=bool(device and device['blocked']))
        if data.require_active_session and result['allowed']:
            if not active:
                result = {'allowed': False, 'reason': 'No active verified device session', 'policy_id': None}
            elif (active['user_id'] and not active['user_enabled']) or (active['voucher_id'] and
                    (not active['voucher_enabled'] or (active['voucher_expires'] and active['voucher_expires'] <= now()))):
                result = {'allowed': False, 'reason': 'Credentials disabled or expired', 'policy_id': None}
            elif active['data_limit_mb'] and conn.execute(
                    'SELECT rx_bytes+tx_bytes FROM guest_sessions WHERE id=?', (active['id'],)
                    ).fetchone()[0] >= active['data_limit_mb'] * 1024 * 1024:
                result = {'allowed': False, 'reason': 'Voucher data quota exceeded', 'policy_id': None}
        return result | {'enforcement': 'gateway-must-apply-decision'}


@app.post('/api/policies/preview')
def preview_policy(data: GatewayDecision, a=Depends(write_auth)):
    # Evaluate the same engine without admitting devices or modifying firewall state.
    result = gateway_authorize(data, gateway=True)
    return result | {'preview_only': True, 'enforcement': 'not-applied'}


@app.get('/api/export/{resource}')
def export_csv(resource: str, a=Depends(auth)):
    sql_map = {
        'users': 'SELECT id,username,display_name,email,enabled,created_at,last_login_at FROM users',
        'devices': 'SELECT id,mac,name,ip,owner_id,blocked,source,first_seen,last_seen,rx_bytes,tx_bytes FROM devices',
        'sessions': 'SELECT id,user_id,voucher_id,device_id,client_ip,login_method,started_at,expires_at,ended_at,state,gateway_verified,rx_bytes,tx_bytes FROM guest_sessions',
        'policies': 'SELECT id,name,kind,target,action,scope_type,scope_id,enabled,created_at FROM policies',
        'activity': 'SELECT id,created_at,actor,category,action,detail FROM activity',
        'vouchers': 'SELECT id,code_hint,label,duration_minutes,data_limit_mb,max_uses,used_count,enabled,expires_at,created_at FROM vouchers'
    }
    if resource not in sql_map: fail(404, 'Unknown export')
    with db() as conn:
        cursor = conn.execute(sql_map[resource])
        headers = [c[0] for c in cursor.description if c[0] != 'bind_token_hash']
        data = cursor.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for r in data:
        writer.writerow([("'" + r[k]) if isinstance(r[k], str) and r[k].lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else r[k] for k in headers])
    return Response(output.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="mdtech-{resource}.csv"'})
