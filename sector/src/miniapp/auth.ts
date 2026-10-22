const bytes=new TextEncoder();
export async function hmac(key:Uint8Array,text:string):Promise<Uint8Array>{const k=await crypto.subtle.importKey('raw',key as BufferSource,{name:'HMAC',hash:'SHA-256'},false,['sign']);return new Uint8Array(await crypto.subtle.sign('HMAC',k,bytes.encode(text)));}
export function hex(value:Uint8Array){return [...value].map(v=>v.toString(16).padStart(2,'0')).join('');}
export async function equal(a:string,b:string){if(!a||!b)return false;const hash=async(v:string)=>new Uint8Array(await crypto.subtle.digest('SHA-256',bytes.encode(v)));const [x,y]=await Promise.all([hash(a),hash(b)]);return x.reduce((diff,v,i)=>diff|(v^y[i]),0)===0;}
export async function owner(raw:string,token:string,id:string,now=Math.floor(Date.now()/1000)):Promise<boolean>{
 try{if(!raw||raw.length>12000||!token||!id)return false;const p=new URLSearchParams(raw),seen=new Set<string>();for(const [key] of p){if(seen.has(key))return false;seen.add(key);}
 const signature=p.get('hash')??'';if(!/^[a-f0-9]{64}$/.test(signature))return false;p.delete('hash');
 const date=Number(p.get('auth_date'));if(!Number.isSafeInteger(date)||date>now+30||now-date>3600)return false;
 const data=[...p].sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,v])=>k+'='+v).join('\n');
 if(!await equal(signature,hex(await hmac(await hmac(bytes.encode('WebAppData'),token),data))))return false;
 const user=JSON.parse(p.get('user')??'null');return Number.isSafeInteger(user?.id)&&String(user.id)===id;
 }catch{return false;}
}
