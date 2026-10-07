"""No proxy inheritance. Exact host allowlist; DNS is resolved and pinned per hop."""
import http.client, ipaddress, socket, ssl, time, os, json, base64
from urllib.parse import urlsplit, urljoin

DENIED = ('kap.org.tr','spk.gov.tr','discilaw.com','heranborsa.com','api.cloudflare.com','cloudflare.com','x.com','twitter.com')
class UnsafeURL(ValueError): pass
class HTTPFailure(RuntimeError):
    def __init__(self,status,retry=0): self.status=status; self.retry=retry; super().__init__(f'http_{status}')

def host_ok(host, allowed):
    return host in set(allowed) and not any(host == d or host.endswith('.'+d) for d in DENIED)

def validate(url, allowed, resolver=socket.getaddrinfo):
    p=urlsplit(url)
    if p.scheme != 'https' or p.username or p.password or p.port not in (None,443) or not p.hostname or p.fragment:
        raise UnsafeURL('https_only_no_userinfo_port_fragment')
    host=p.hostname.encode('idna').decode().lower().rstrip('.')
    if host=='localhost' or host.endswith(('.localhost','.local','.internal')):raise UnsafeURL('local_hostname')
    try:ipaddress.ip_address(host)
    except ValueError:pass
    else:raise UnsafeURL('ip_literal_denied')
    if not host_ok(host,allowed): raise UnsafeURL('host_not_allowed')
    try: addrs=resolver(host,443,type=socket.SOCK_STREAM)
    except OSError: raise UnsafeURL('dns_failed') from None
    ips={r[4][0] for r in addrs}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips): raise UnsafeURL('nonpublic_dns')
    return host, sorted(ips)[0]

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, timeout):
        super().__init__(host,timeout=timeout,context=ssl.create_default_context()); self.pinned_ip=ip
    def connect(self):
        sock=socket.create_connection((self.pinned_ip,443),self.timeout)
        self.sock=self._context.wrap_socket(sock,server_hostname=self.host)

class Fetcher:
    def __init__(self, allowed, guard=lambda:None, timeout=15, max_bytes=2_000_000, resolver=socket.getaddrinfo):
        self.allowed=allowed; self.guard=guard; self.timeout=timeout; self.max_bytes=max_bytes; self.resolver=resolver
    def get(self,url,headers=None):
        broker=os.environ.get('HABNEWS_FETCH_SOCKET')
        if broker:
            self.guard()
            if broker!='/broker/fetch.sock':raise UnsafeURL('broker_path')
            p=urlsplit(url)
            if not p.hostname or not host_ok(p.hostname,self.allowed):raise UnsafeURL('host_not_allowed')
            conn=http.client.HTTPConnection('localhost',timeout=self.timeout+5)
            sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(self.timeout+5);sock.connect(broker);conn.sock=sock
            try:
                conn.request('POST','/fetch',body=json.dumps({'url':url,'headers':headers or {},'max_bytes':self.max_bytes}),headers={'Content-Type':'application/json'})
                result=json.loads(conn.getresponse().read(self.max_bytes*2+16384))
                if result.get('error'):
                    if result.get('status'):raise HTTPFailure(result['status'],result.get('retry',0))
                    raise UnsafeURL(result['error'])
                if not host_ok(urlsplit(result['url']).hostname,self.allowed):raise UnsafeURL('redirect_host_not_allowed')
                data=base64.b64decode(result['body'],validate=True)
                if len(data)>self.max_bytes:raise UnsafeURL('body_too_large')
                self.guard();return data,result['headers'],result['url'],result['status']
            finally:conn.close()
        for _ in range(4):
            self.guard(); host,ip=validate(url,self.allowed,self.resolver)
            p=urlsplit(url); conn=PinnedHTTPS(host,ip,self.timeout)
            try:
                conn.request('GET',p.path+('?' + p.query if p.query else ''),headers={'User-Agent':'habnews/0.1 contact=operator','Accept-Encoding':'identity',**(headers or {})})
                response=conn.getresponse(); meta={k.lower():v for k,v in response.getheaders()}
                if response.status in (301,302,303,307,308):
                    url=urljoin(url,meta.get('location','')); continue
                if response.status == 304: return b'',meta,url,304
                if response.status != 200:
                    retry=meta.get('retry-after','0')
                    try: retry=float(retry)
                    except ValueError:
                        from email.utils import parsedate_to_datetime
                        try: retry=max(0,parsedate_to_datetime(retry).timestamp()-time.time())
                        except (ValueError,TypeError): retry=60
                    raise HTTPFailure(response.status,retry)
                if int(meta.get('content-length','0')) > self.max_bytes: raise UnsafeURL('body_too_large')
                data=bytearray()
                while chunk:=response.read(65536):
                    data.extend(chunk)
                    if len(data)>self.max_bytes: raise UnsafeURL('body_too_large')
                self.guard()
                return bytes(data),meta,url,200
            finally: conn.close()
        raise UnsafeURL('redirect_limit')
