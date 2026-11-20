import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import app.main as api
import app.network as network
from app.db import db, put_setting


def test_host_inventory_is_admin_only(client, admin, monkeypatch):
    observation = {'source':'crm_host_operating_system','wifi_ssid':None,'wifi_status':'service_stopped','interfaces':[]}
    monkeypatch.setattr(api, 'inspect_host_network', lambda: observation)
    assert client.get('/api/network/host').json() == observation
    client.post('/api/auth/logout', headers=admin)
    assert client.get('/api/network/host').status_code == 401


def test_saved_label_is_not_live_ssid(client, admin):
    with db() as conn:
        put_setting(conn, 'ssid', 'Manually typed network label')
    assert client.get('/api/network').json()['observed_ssid'] is None
    config = client.get('/api/portal/config').json()
    assert config['ssid'] == '' and config['network_label'] == 'Manually typed network label'


def test_router_probe_requires_csrf_and_saved_address(client, admin, monkeypatch):
    assert client.post('/api/network/check').status_code == 403
    assert client.post('/api/network/check', headers=admin).status_code == 422
    profile = {'platform':'tplink_wr841n_v14','management_ip':'192.168.50.1','operating_mode':'ap','upstream_ssid':'Main Wi-Fi'}
    assert client.patch('/api/network', headers=admin, json=profile).status_code == 200
    response = {'target':'192.168.50.1','reachable':True,'reachable_ports':[80],'checked_at':'2026-10-18T12:00:00+00:00','router_identity_verified':False}
    monkeypatch.setattr(api, 'probe_router', lambda address: response)
    assert client.post('/api/network/check', headers=admin).json() == response
    assert client.get('/api/network').json()['management_url'] == 'http://192.168.50.1/'
    assert client.get('/api/network').json()['connection_check'] == response
    client.patch('/api/network', headers=admin, json={**profile,'management_ip':'192.168.50.2'})
    assert client.get('/api/network').json()['connection_check'] is None


@pytest.mark.parametrize('address',['127.0.0.1','169.254.169.254','8.8.8.8','0.0.0.0','::1'])
def test_probe_refuses_non_lan_targets(address, monkeypatch):
    connect=Mock();monkeypatch.setattr(network.socket,'create_connection',connect)
    with pytest.raises(ValueError): network.probe_router(address)
    connect.assert_not_called()


def test_probe_uses_only_fixed_ports_and_timeout(monkeypatch):
    connection=Mock();connection.__enter__=Mock(return_value=connection);connection.__exit__=Mock(return_value=None)
    connect=Mock(return_value=connection);monkeypatch.setattr(network.socket,'create_connection',connect)
    result=network.probe_router('192.168.50.1')
    assert result['reachable_ports']==[80,443] and not result['router_identity_verified']
    assert [c.args[0][1] for c in connect.call_args_list]==[80,443]
    assert all(c.kwargs['timeout']==1.5 for c in connect.call_args_list)


def test_windows_inventory_parses_without_exposing_command_output(monkeypatch):
    inventory={'interfaces':[{'Description':'Wi-Fi','IPAddress':['192.168.50.20'],'DefaultIPGateway':['192.168.50.1'],'DHCPEnabled':True}],
               'adapters':[{'Name':'Wireless adapter','NetEnabled':True}],'wlan_service':'Running'}
    calls=iter([SimpleNamespace(returncode=0,stdout=json.dumps(inventory)),SimpleNamespace(stdout='SSID : MD_TECH\nBSSID : aa:bb:cc:dd:ee:ff\nSignal : 90%\nAuthentication : WPA2-Personal',stderr='')])
    monkeypatch.setattr(network,'_cached',None);monkeypatch.setattr(network.platform,'system',lambda:'Windows')
    monkeypatch.setattr(network.subprocess,'run',lambda *a,**k:next(calls))
    r=network.inspect_host_network()
    assert r['wifi_ssid']=='MD_TECH' and r['wifi']['signal']=='90%'
    assert r['wifi_status']=='connected' and not r['router_identity_verified']
    assert r['interfaces'][0]['gateways']==['192.168.50.1']
    monkeypatch.setattr(network,'_cached',None)


def test_policy_preview_is_read_only_and_protected(client, admin):
    client.post('/api/policies',headers=admin,json={'name':'Block video','kind':'app','target':'youtube'})
    payload={'domain':'www.youtube.com','require_active_session':False}
    assert client.post('/api/policies/preview',json=payload).status_code==403
    result=client.post('/api/policies/preview',headers=admin,json=payload).json()
    assert result['preview_only'] and result['enforcement']=='not-applied' and not result['allowed']
    assert client.get('/api/devices').json()==[] and client.get('/api/sessions').json()==[]
    client.post('/api/auth/logout',headers=admin)
    assert client.post('/api/policies/preview',json=payload).status_code==401


def test_manually_enrolled_device_becomes_gateway_reported(client, admin):
    mac='02:00:00:00:00:22'
    client.post('/api/devices',headers=admin,json={'mac':mac,'name':'Enrolled device'})
    key=client.post('/api/settings/gateway-key',headers=admin).json()['key']
    client.post('/api/integrations/event',headers={'X-Gateway-Key':key},json={'type':'device_seen','mac':mac,'ip':'192.168.50.22'})
    device=client.get('/api/devices').json()[0]
    assert device['source']=='gateway' and device['ip']=='192.168.50.22'


@pytest.mark.parametrize('mode',['router','ap','wisp','extender'])
def test_router_role_profile_round_trip(client, admin, mode):
    profile={'platform':'tplink_wr841n_v14','operating_mode':mode,'management_ip':'192.168.0.1'}
    assert client.patch('/api/network',headers=admin,json=profile).status_code==200
    assert client.get('/api/network').json()['profile']['operating_mode']==mode


def test_windows_settings_requires_local_admin_and_csrf(client, admin, monkeypatch):
    from fastapi.testclient import TestClient
    opened=[]
    def launch(page):
        opened.append(page)
        return {'opened':True,'page':page,'permission_granted':False}
    monkeypatch.setattr(api,'open_windows_settings',launch)
    assert client.post('/api/network/windows-settings',json={'page':'location'}).status_code==403
    result=client.post('/api/network/windows-settings',headers=admin,json={'page':'location'})
    assert result.status_code==200 and result.json()['permission_granted'] is False
    assert client.post('/api/network/windows-settings',headers=admin,json={'page':'cmd.exe'}).status_code==422
    with TestClient(api.app,client=('192.168.50.20',50001)) as remote:
        remote.cookies.set('mdtech_session',client.cookies.get('mdtech_session'))
        assert remote.post('/api/network/windows-settings',headers=admin,json={'page':'wifi'}).status_code==403
    assert opened==['location']


def test_windows_settings_uses_only_fixed_uris(monkeypatch):
    launch=Mock()
    monkeypatch.setattr(network.platform,'system',lambda:'Windows')
    monkeypatch.setattr(network.os,'startfile',launch)
    assert network.open_windows_settings('location')['permission_granted'] is False
    launch.assert_called_once_with('ms-settings:privacy-location')
    with pytest.raises(ValueError): network.open_windows_settings('file:///C:/Windows/System32/cmd.exe')
    assert launch.call_count==1


def test_network_recheck_bypasses_cached_observation(client, admin, monkeypatch):
    inspect=Mock(return_value={'status':'observed','interfaces':[]})
    monkeypatch.setattr(api,'inspect_host_network',inspect)
    assert client.get('/api/network/host?refresh=true').status_code==200
    inspect.assert_called_once_with(force=True)
