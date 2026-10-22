import socket
import pytest
from app.network import validate_url,audit_website,fetch_public
@pytest.mark.parametrize('url',['file:///etc/passwd','http://127.0.0.1','http://[::1]','http://169.254.169.254/latest/meta-data/','http://10.0.0.1','http://user:pass@example.com','http://example.com:22'])
def test_ssrf_blocked(url):
    with pytest.raises((ValueError,socket.gaierror)):validate_url(url)
def test_dns_rebinding_mixed_addresses(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',80)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',80))])
    with pytest.raises(ValueError):validate_url('http://example.test')
def test_missing_site_is_not_nonexistent():
    result=audit_website('');assert result['state']=='unknown'
    assert result['findings']==[] and 'non identifié' in result['limitations'][0]
def test_redirect_private_blocked(monkeypatch):
    import app.network as n
    n._robots_cache.clear()
    monkeypatch.setattr(socket,'getaddrinfo',lambda host,*a,**kw:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(host if host=='127.0.0.1' else '8.8.8.8',80))])
    class Response:
        status=302
        def getheaders(self):return [('Location','http://127.0.0.1/private')]
    class Connection:
        def __init__(self,*a):pass
        def request(self,*a,**kw):pass
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(n,'PinnedHTTP',Connection)
    with pytest.raises(ValueError):fetch_public('http://example.test')

def test_html_audit_with_observed_evidence(monkeypatch):
    import app.network as n
    n._robots_cache.clear()
    monkeypatch.setattr(n,'validate_url',lambda url:(__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(url),'8.8.8.8'))
    monkeypatch.setattr(n.time,'sleep',lambda *_:None)
    def fixture_fetch(url,**kwargs):
        if url.endswith('/robots.txt'):return 200,{},'User-agent: *\nAllow: /',url
        return 200,{'content-type':'text/html'},'<html><head></head><body><img src="a"></body></html>',url
    monkeypatch.setattr(n,'fetch_public',fixture_fetch)
    result=n.audit_website('https://example.test')
    assert result['state']=='observed' and result['status']==200
    assert {'title','description','h1','viewport','alt'}=={f['code'] for f in result['findings']}
    assert all(f['source']=='https://example.test' for f in result['findings'])
    assert result['metadata']['missing_alt']==1

def test_robots_denial_not_scored_as_site_failure(monkeypatch):
    import app.network as n
    n._robots_cache.clear()
    monkeypatch.setattr(n,'validate_url',lambda url:(__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(url),'8.8.8.8'))
    monkeypatch.setattr(n.time,'sleep',lambda *_:None)
    calls=[]
    def fixture_fetch(url,**kwargs):
        calls.append(url);return 200,{},'User-agent: *\nDisallow: /',url
    monkeypatch.setattr(n,'fetch_public',fixture_fetch)
    result=n.audit_website('https://example.test')
    assert result['state']=='unavailable' and result['findings']==[]
    assert 'robots' in result['error'] and calls==['https://example.test/robots.txt']
