from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.db import db, put_setting


def make_session(client, admin):
    user = client.post('/api/users', headers=admin, json={
        'username': 'visitor', 'display_name': 'Visitor', 'password': 'GuestPassword77!'}).json()['id']
    session = client.post('/api/portal/login', json={
        'method': 'account', 'username': 'visitor', 'password': 'GuestPassword77!'}).json()
    gh = {'X-Gateway-Key': client.post('/api/settings/gateway-key', headers=admin).json()['key']}
    binding = {'session_id': session['session_id'], 'bind_token': session['bind_token'], 'mac': 'aa:bb:cc:dd:ee:51'}
    return user, session, gh, binding


def test_binding_requires_one_time_proof(client, admin):
    _, _, gh, binding = make_session(client, admin)
    assert client.post('/api/integrations/bind', headers=gh, json={**binding, 'bind_token': 'x'*48}).status_code == 403
    assert client.post('/api/integrations/bind', headers=gh, json=binding).status_code == 200
    assert client.post('/api/integrations/bind', headers=gh, json=binding).status_code == 403


def test_disabled_user_immediately_denied(client, admin):
    user, session, gh, binding = make_session(client, admin)
    assert client.post('/api/integrations/bind', headers=gh, json=binding).status_code == 200
    decision = {'mac': binding['mac'], 'domain': 'example.com'}
    assert client.post('/api/integrations/authorize', headers=gh, json=decision).json()['allowed']
    assert client.patch(f'/api/users/{user}', headers=admin, json={'enabled': False}).status_code == 200
    assert not client.post('/api/integrations/authorize', headers=gh, json=decision).json()['allowed']
    assert session['session_id'] in client.get('/api/integrations/state', headers=gh).json()['revoked_session_ids']


def test_scope_uses_authenticated_guest(client, admin):
    user, _, gh, binding = make_session(client, admin)
    client.post('/api/integrations/bind', headers=gh, json=binding)
    client.post('/api/policies', headers=admin, json={'name':'Visitor restriction','kind':'domain',
        'target':'example.com','scope_type':'user','scope_id':user})
    decision = {'mac':binding['mac'],'domain':'example.com','user_id':9999}
    result = client.post('/api/integrations/authorize', headers=gh, json=decision).json()
    assert not result['allowed'] and 'Visitor restriction' in result['reason']


def test_heartbeat_has_real_freshness_and_is_private(client, admin):
    gh = {'X-Gateway-Key': client.post('/api/settings/gateway-key', headers=admin).json()['key']}
    assert client.get('/api/network').json()['status'] == 'not_reporting'
    payload = {'name':'Test gateway','model':'Reported model','ssid':'MD_TECH','lan_ip':'192.168.50.1','capabilities':['traffic']}
    assert client.post('/api/integrations/heartbeat', json=payload).status_code == 401
    assert client.post('/api/integrations/heartbeat', headers=gh, json=payload).status_code == 200
    result = client.get('/api/network').json()
    assert result['status'] == 'reporting' and not result['enforcement_verified']
    assert result['telemetry']['model'] == 'Reported model'
    with db() as conn:
        import json
        result['telemetry']['received_at'] = (datetime.now(timezone.utc)-timedelta(seconds=100)).isoformat()
        put_setting(conn, 'gateway_heartbeat', json.dumps(result['telemetry']))
    assert client.get('/api/network').json()['status'] == 'stale'
    client.post('/api/auth/logout', headers=admin)
    assert client.get('/api/network').status_code == 401


def test_cross_origin_and_remote_setup_denied(client):
    assert client.post('/api/auth/setup', headers={'Origin':'https://evil.example'}, json={
        'username':'admin','password':'StrongPassword44!'}).status_code == 403
    # An independent transport must not claim an unconfigured LAN instance.
    with TestClient(app, client=('192.168.50.20', 50001)) as remote:
        assert remote.post('/api/auth/setup', json={'username':'admin','password':'StrongPassword44!'}).status_code == 403


def test_password_change_invalidates_other_admin_sessions(client, admin):
    old_cookie = client.cookies.get('mdtech_session')
    login = client.post('/api/auth/login', json={'username':'admin','password':'VeryStrongAdminSecret17!'}).json()
    assert client.post('/api/auth/password', headers={'X-CSRF-Token':login['csrf']}, json={
        'current_password':'VeryStrongAdminSecret17!', 'new_password':'NewStrongPassword88!'}).status_code == 200
    assert client.get('/api/users').status_code == 200
    client.cookies.set('mdtech_session', old_cookie)
    assert client.get('/api/users').status_code == 401


def test_csv_formula_and_null_update(client, admin):
    user = client.post('/api/users', headers=admin, json={
        'username':'csvuser','display_name':'=HYPERLINK("https://example.com")','password':'GuestPassword77!'}).json()['id']
    assert client.patch(f'/api/users/{user}', headers=admin, json={'password':None}).status_code == 422
    assert "'=HYPERLINK" in client.get('/api/export/users').text


def test_network_profile_validation_and_csrf(client, admin):
    profile = {'platform':'tplink_wr841n_v14','router_name':'WR841N V14','guest_vlan':50}
    assert client.patch('/api/network', json=profile).status_code == 403
    assert client.patch('/api/network', headers=admin, json=profile).status_code == 200
    assert client.get('/api/network').json()['profile']['router_name'] == 'WR841N V14'
    assert client.patch('/api/network', headers=admin, json={**profile,'management_ip':'https://evil.example'}).status_code == 422
    assert client.patch('/api/network', headers=admin, json={**profile,'guest_vlan':4095}).status_code == 422


def test_guest_cannot_relabel_existing_device(client, admin):
    mac = 'aa:bb:cc:dd:ee:77'
    client.post('/api/devices', headers=admin, json={'mac':mac,'name':'Admin-owned name'})
    code = client.post('/api/vouchers', headers=admin, json={'quantity':1}).json()['codes'][0]['code']
    assert client.post('/api/portal/login', json={'method':'voucher','code':code,'mac':mac,'device_name':'Forged name'}).status_code == 200
    assert client.get('/api/devices').json()[0]['name'] == 'Admin-owned name'
    assert 'bind_token_hash' not in client.get('/api/sessions').text
    assert 'bind_token_hash' not in client.get('/api/export/sessions').text


def test_voucher_disable_and_expiry_disconnect(client, admin):
    voucher = client.post('/api/vouchers', headers=admin, json={'quantity':1}).json()['codes'][0]
    login = client.post('/api/portal/login', json={'method':'voucher','code':voucher['code']}).json()
    client.patch('/api/vouchers/'+str(voucher['id']), headers=admin, json={'enabled':False})
    gh = {'X-Gateway-Key':client.post('/api/settings/gateway-key', headers=admin).json()['key']}
    assert login['session_id'] in client.get('/api/integrations/state', headers=gh).json()['revoked_session_ids']
    with db() as conn:
        conn.execute("UPDATE guest_sessions SET state='authorized',expires_at=?", ((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),))
    assert login['session_id'] in client.get('/api/integrations/state', headers=gh).json()['revoked_session_ids']


def test_rotating_usernames_cannot_bypass_ip_limit(client):
    for i in range(30):
        assert client.post('/api/auth/login', json={'username':f'unknown{i}','password':'wrongpass123'}).status_code == 401
    assert client.post('/api/auth/login', json={'username':'another','password':'wrongpass123'}).status_code == 429


def test_device_null_patch_does_not_raise_server_error(client, admin):
    ident = client.post('/api/devices', headers=admin, json={'mac':'aa:bb:cc:dd:ee:88'}).json()['id']
    for field in ('name', 'ip', 'blocked'):
        assert client.patch(f'/api/devices/{ident}', headers=admin, json={field:None}).status_code == 422
    assert client.patch(f'/api/devices/{ident}', headers=admin, json={'owner_id':None}).status_code == 200


def test_gateway_key_brute_force_throttled(client):
    for _ in range(10):
        assert client.post('/api/integrations/heartbeat', headers={'X-Gateway-Key':'invalid_secret'}, json={'name':'test'}).status_code == 401
    assert client.post('/api/integrations/heartbeat', headers={'X-Gateway-Key':'invalid_secret'}, json={'name':'test'}).status_code == 429


def test_domain_with_port_matches_policy(client, admin):
    client.post('/api/policies', headers=admin, json={'name':'Block YouTube','kind':'app','target':'youtube','action':'block'})
    gh = {'X-Gateway-Key': client.post('/api/settings/gateway-key', headers=admin).json()['key']}
    res = client.post('/api/integrations/authorize', headers=gh, json={'mac':'aa:bb:cc:dd:ee:01','domain':'www.youtube.com:443','require_active_session':False}).json()
    assert res['allowed'] is False
    assert 'Block YouTube' in res['reason']


def test_ensure_record_table_whitelist():
    import pytest
    import app.main as main
    from app.db import db
    with db() as conn:
        with pytest.raises(main.HTTPException) as exc:
            main.ensure_record(conn, 'admins', 1)
        assert exc.value.status_code == 500
