def test_voucher_flow(client, admin):
    r=client.post('/api/vouchers',headers=admin,json={'quantity':1,'duration_minutes':60,'max_uses':1})
    assert r.status_code==201, r.text
    code=r.json()['codes'][0]['code']
    assert 'code_hash' not in str(client.get('/api/vouchers').json())
    assert code not in str(client.get('/api/vouchers').json())
    r=client.post('/api/portal/login',json={'method':'voucher','code':code,'device_name':'Laptop'})
    assert r.status_code==200,r.text
    assert r.json()['message'].find('gateway')>=0
    assert len(client.get('/api/sessions').json())==1
    assert client.post('/api/portal/login',json={'method':'voucher','code':code}).status_code==401
    assert client.post('/api/sessions/1/disconnect',headers=admin).status_code==200
    assert client.get('/api/sessions').json()[0]['state']=='revoked'


def test_guest_account_flow(client, admin):
    client.post('/api/users',headers=admin,json={'username':'employee','display_name':'Employee','password':'userpass333'})
    assert client.post('/api/portal/login',json={'method':'account','username':'employee','password':'wrongpass88'}).status_code==401
    assert client.post('/api/portal/login',json={'method':'account','username':'employee','password':'userpass333'}).status_code==200
    assert client.patch('/api/users/1',headers=admin,json={'enabled':False}).status_code==200
    assert client.post('/api/portal/login',json={'method':'account','username':'employee','password':'userpass333'}).status_code==401
