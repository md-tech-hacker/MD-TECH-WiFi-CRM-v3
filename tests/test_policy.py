from app.policy import matches, decide

def test_domains_are_suffix_bounded():
    assert matches('domain','youtube.com',domain='www.youtube.com')
    assert not matches('domain','youtube.com',domain='fake-youtube.com')
    assert not matches('domain','youtube.com',domain='youtube.com.evil.net')
    assert matches('app','youtube',domain='r3.googlevideo.com')
    assert matches('ip','192.168.10.0/24',ip='192.168.10.11')
    assert not matches('ip','192.168.10.0/24',ip='192.168.11.11')

def test_scope_and_blocks():
    rules=[{'id':1,'enabled':1,'name':'Global block','kind':'domain','target':'example.com','action':'block','scope_type':'all','scope_id':None},
           {'id':2,'enabled':1,'name':'User exception','kind':'domain','target':'example.com','action':'allow','scope_type':'user','scope_id':3}]
    assert decide(rules,domain='example.com',user_id=3)['allowed']
    assert not decide(rules,domain='example.com',user_id=4)['allowed']
    assert not decide(rules,domain='example.com',user_id=3,device_blocked=True)['allowed']
