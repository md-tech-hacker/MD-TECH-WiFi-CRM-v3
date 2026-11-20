def test_setup_and_auth(client):
    assert client.get('/api/auth/status').json()['configured'] is False
    setup=client.post('/api/auth/setup', json={'username':'admin','password':'DifferentStrongPassword22!'})
    assert setup.status_code == 200
    csrf=setup.json()['csrf']
    assert client.get('/api/auth/status').json()['authenticated']
    assert client.post('/api/auth/setup',json={'username':'other','password':'AnotherStrongPassword44!'}).status_code==409
    assert client.post('/api/users',json={'username':'guest','display_name':'Guest','password':'testpass99'}).status_code==403
    r=client.post('/api/users',headers={'X-CSRF-Token':csrf},json={'username':'guest','display_name':'Guest','password':'testpass99'})
    assert r.status_code==201
    assert client.get('/api/users').json()[0]['username']=='guest'
    assert client.post('/api/auth/logout',headers={'X-CSRF-Token':csrf}).status_code==200
    assert client.get('/api/users').status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'wrongpassword'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'DifferentStrongPassword22!'}).status_code==200


def test_unauthorized_user_data_hidden(client):
    for route in ['/api/dashboard','/api/users','/api/vouchers','/api/policies','/api/devices','/api/sessions','/api/activity','/api/settings','/api/export/users']:
        assert client.get(route).status_code == 401, route
