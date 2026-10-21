// Exact registered hosts only. No credentials, IPs, ports, private endpoints or
// redirect to another provider. No auth cookies and no bypass proxies.
export function safeUrl(value:string,hosts:string[]):string {
  const u=new URL(value);
  if(u.protocol!=='https:'||u.username||u.password||u.port||!hosts.includes(u.hostname.toLowerCase())||!u.hostname.includes('.')||/^[\d.]+$/.test(u.hostname)||u.hostname.includes(':'))throw new Error('unregistered_url');
  u.hash=''; return u.href;
}
export async function readPublic(url:string,hosts:string[],headers:Record<string,string>={},fetcher:typeof fetch=fetch,binary=false):Promise<{text:string;bytes?:Uint8Array;url:string;status:number;headers:Headers}> {
  let current=safeUrl(url,hosts);
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),18_000);
  try {
    for(let i=0;i<4;i++) {
      const response=await fetcher(current,{headers:{'User-Agent':'SectorHaber/1.0 (editorial RSS reader)',Accept:'application/rss+xml,application/atom+xml,text/html;q=0.8',...headers},redirect:'manual',signal:controller.signal});
      if([301,302,303,307,308].includes(response.status)) {
        await response.body?.cancel();
        const location=response.headers.get('location');if(!location)throw new Error('redirect_without_location');
        current=safeUrl(new URL(location,current).href,hosts);continue;
      }
      if(response.status===304){await response.body?.cancel();return {text:'',url:current,status:304,headers:response.headers};}
      if(!response.ok){await response.body?.cancel();throw new Error(`source_http_${response.status}`);}
      const reader=response.body?.getReader();if(!reader)throw new Error('empty_response');
      const chunks:Uint8Array[]=[];let size=0;
      try {while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>3_000_000)throw new Error('source_too_large');chunks.push(value);}}
      finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
      const all=new Uint8Array(size);let offset=0;for(const c of chunks){all.set(c,offset);offset+=c.length;}
      return {text:binary?'':new TextDecoder('utf-8',{fatal:true}).decode(all),bytes:all,url:current,status:response.status,headers:response.headers};
    }
    throw new Error('too_many_redirects');
  } finally {clearTimeout(timer);}
}
