"""Narrow Unix-socket read broker; caller cannot choose credentials, method or IP."""
import base64,json,os,socketserver
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from .config import sources
from .network import Fetcher

class Handler(BaseHTTPRequestHandler):
    timeout=15
    def log_message(self,*args):pass
    def do_POST(self):
        if self.path!='/fetch':self.send_error(404);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=8192:raise ValueError('request_limit')
            request=json.loads(self.rfile.read(length))
            if not isinstance(request,dict) or set(request)-{'url','headers','max_bytes'} or not isinstance(request.get('url'),str):raise ValueError('request_schema')
            headers=request.get('headers',{})
            if not isinstance(headers,dict) or set(headers)-{'If-None-Match','If-Modified-Since'} or any(not isinstance(v,str) for v in headers.values()):raise ValueError('header_denied')
            max_bytes=request.get('max_bytes',2_000_000)
            if type(max_bytes) is not int or max_bytes<=0:raise ValueError('response_limit')
            from .article_media import media_hosts
            active=sources()
            allowed=sorted({h for s in active if s['enabled'] for h in s['allowed_hosts']}|media_hosts(active)|{'commons.wikimedia.org','upload.wikimedia.org','live.staticflickr.com'})
            from urllib.parse import urlsplit
            from .social import ACCOUNTS
            parsed=urlsplit(request['url'])
            if parsed.hostname=='nitter.cf' and (parsed.query or parsed.path not in {'/'+account+'/rss' for account in ACCOUNTS}):raise ValueError('social_read_path_denied')
            if parsed.hostname=='live.staticflickr.com' and (parsed.query or parsed.path!='/65535/55462088240_2fb7910355_b.jpg'):raise ValueError('archive_asset_path_denied')
            def guard():
                if not json.loads(Path('/control/runtime-state.json').read_text()).get('enabled'):raise RuntimeError('paused')
            data,meta,url,status=Fetcher(allowed,guard,max_bytes=min(max_bytes,10_000_000)).get(request['url'],headers)
            payload={'body':base64.b64encode(data).decode(),'headers':meta,'url':url,'status':status}
        except Exception as exc:payload={'error':type(exc).__name__,'status':getattr(exc,'status',None),'retry':getattr(exc,'retry',0)}
        body=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
class Server(socketserver.UnixStreamServer):allow_reuse_address=True

def main():
    path=Path('/broker/fetch.sock');path.parent.mkdir(parents=True,exist_ok=True)
    path.unlink(missing_ok=True)
    with Server(str(path),Handler) as server:
        os.chmod(path,0o660);server.serve_forever()
if __name__=='__main__':main()
