def gateway_key(client, admin):
    return {'X-Gateway-Key':client.post('/api/settings/gateway-key',headers=admin).json()['key']}


def test_device_policy_and_gateway(client,admin):
    mac='aa:bb:cc:dd:ee:10'
    assert client.post('/api/integrations/event',json={'type':'device_seen','mac':mac}).status_code==401
    gh=gateway_key(client,admin)
    r=client.post('/api/integrations/event',headers=gh,json={'type':'device_seen','mac':mac,'ip':'192.168.1.44','name':'Test laptop'})
    assert r.status_code==200,r.text
    device_id=r.json()['device_id']
    assert client.get('/api/devices').json()[0]['name']=='Test laptop'
    r=client.post('/api/policies',headers=admin,json={'name':'Block video','kind':'app','target':'youtube','action':'block'})
    assert r.status_code==201,r.text
    request={'mac':mac,'domain':'www.youtube.com','require_active_session':False}
    result=client.post('/api/integrations/authorize',headers=gh,json=request)
    assert result.status_code==200 and not result.json()['allowed']
    assert 'Block video' in result.json()['reason']
    request['domain']='example.org'
    assert client.post('/api/integrations/authorize',headers=gh,json=request).json()['allowed']
    request['require_active_session']=True
    assert not client.post('/api/integrations/authorize',headers=gh,json=request).json()['allowed']
    assert client.patch('/api/devices/'+str(device_id),headers=admin,json={'blocked':True}).status_code==200
    assert mac in client.get('/api/integrations/state',headers=gh).json()['blocked_macs']
    assert not client.post('/api/integrations/authorize',headers=gh,json=request).json()['allowed']
    assert client.get('/api/export/devices').status_code==200


def test_binding_and_traffic(client,admin):
    r=client.post('/api/vouchers',headers=admin,json={'quantity':1,'data_limit_mb':1})
    code=r.json()['codes'][0]['code']
    login=client.post('/api/portal/login',json={'method':'voucher','code':code}).json()
    session=login['session_id']
    gh=gateway_key(client,admin)
    mac='aa:bb:cc:dd:ee:11'
    decision={'mac':mac,'domain':'example.com'}
    assert client.post('/api/integrations/bind',headers=gh,json={'session_id':session,'bind_token':login['bind_token'],'mac':mac,'ip':'192.168.0.5'}).status_code==200
    assert client.post('/api/integrations/authorize',headers=gh,json=decision).json()['allowed']
    assert client.post('/api/integrations/event',headers=gh,json={'type':'traffic','mac':mac,'rx_bytes':1048576,'session_id':session}).status_code==200
    r=client.post('/api/integrations/authorize',headers=gh,json=decision).json()
    assert not r['allowed'] and 'quota' in r['reason']
    assert client.get('/api/dashboard').json()['total_bytes']==1048576
    assert client.post('/api/sessions/'+str(session)+'/disconnect',headers=admin).status_code==200
    assert session in client.get('/api/integrations/state',headers=gh).json()['revoked_session_ids']


def test_guest_mac_is_unverified(client, admin):
    mac='aa:bb:cc:dd:ee:99'
    code=client.post('/api/vouchers',headers=admin,json={'quantity':1}).json()['codes'][0]['code']
    login=client.post('/api/portal/login',json={'method':'voucher','code':code,'mac':mac})
    assert login.status_code==200
    gh=gateway_key(client,admin)
    # Guest typing a MAC cannot authorize that station by itself.
    request={'mac':mac,'domain':'example.com','require_active_session':True}
    assert not client.post('/api/integrations/authorize',headers=gh,json=request).json()['allowed']
    assert client.post('/api/integrations/bind',headers=gh,json={'session_id':login.json()['session_id'],'bind_token':login.json()['bind_token'],'mac':mac}).status_code==200
    assert client.post('/api/integrations/authorize',headers=gh,json=request).json()['allowed']
