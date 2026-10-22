import {owner,equal} from './auth';import {validSnapshot} from './types';
export interface PanelEnv {ASSETS:Fetcher;PANEL:R2Bucket;BOT_TOKEN:string;OWNER_ID:string;SYNC_TOKEN:string;ENABLED:string;}
const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
const json=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status,headers:{...headers,'Content-Type':'application/json'}});
async function bounded(r:Request,max:number){if(Number(r.headers.get('content-length'))>max)throw Error('large');const reader=r.body?.getReader();if(!reader)throw Error('empty');const parts:Uint8Array[]=[];let size=0;try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max)throw Error('large');parts.push(value);}}finally{await reader.cancel().catch(()=>{});}const out=new Uint8Array(size);let at=0;for(const p of parts){out.set(p,at);at+=p.length;}return out;}
export default {
 async fetch(r:Request,env:PanelEnv):Promise<Response>{
 const path=new URL(r.url).pathname;if(env.ENABLED!=='true')return json({error:'panel_disabled'},503);
 if(path==='/health')return json({ok:true,mode:'read_only'});
 if(path.startsWith('/sync/')){
  if(r.method!=='PUT'||!await equal(r.headers.get('authorization')??'','Bearer '+env.SYNC_TOKEN)||!env.SYNC_TOKEN)return json({error:'unauthorized'},401);
  if(path==='/sync/disable'){await env.PANEL.put('disabled','1');return json({ok:true});}
  if(path==='/sync/enable'){await env.PANEL.delete('disabled');return json({ok:true});}
  try{if(path==='/sync/feed'){const data=await bounded(r,4000000),value=JSON.parse(new TextDecoder().decode(data));if(!validSnapshot(value)||Math.abs(Date.now()-value.generatedAt)>300000)return json({error:'invalid_snapshot'},400);await env.PANEL.put('feed.json',data,{httpMetadata:{contentType:'application/json'}});return json({ok:true});}
   const m=path.match(/^\/sync\/media\/([a-f0-9]{64})$/);if(m){const data=await bounded(r,5000000);if(data.length<8||![137,80,78,71,13,10,26,10].every((v,i)=>data[i]===v))return json({error:'invalid_png'},400);await env.PANEL.put('media/'+m[1]+'.png',data,{httpMetadata:{contentType:'image/png'}});return json({ok:true});}
  }catch{return json({error:'invalid_upload'},400);}return json({error:'not_found'},404);
 }
 if(await env.PANEL.get('disabled'))return json({error:'panel_disabled'},503);
 if(path.startsWith('/api/')){
  if(!await owner((r.headers.get('authorization')??'').replace(/^tma /,''),env.BOT_TOKEN,env.OWNER_ID))return json({error:'telegram_owner_required'},401);
  if(r.method==='GET'&&path==='/api/feed'){const value=await env.PANEL.get('feed.json');return value?new Response(value.body,{headers:{...headers,'Content-Type':'application/json'}}):json({error:'sync_pending'},503);}
  const media=path.match(/^\/api\/media\/([a-f0-9]{64})$/);if(r.method==='GET'&&media){const o=await env.PANEL.get('media/'+media[1]+'.png');return o?new Response(o.body,{headers:{...headers,'Content-Type':'image/png'}}):json({error:'media_pending'},404);}
  return json({error:'not_found'},404);
 }
 if(r.method!=='GET'&&r.method!=='HEAD')return json({error:'method_not_allowed'},405);
 const response=await env.ASSETS.fetch(r);const h=new Headers(response.headers);h.set('Content-Security-Policy',"default-src 'self'; script-src 'self' https://telegram.org; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'");for(const [k,v] of Object.entries(headers))h.set(k,v);return new Response(response.body,{status:response.status,headers:h});
 },
 async scheduled(_event:ScheduledController,env:PanelEnv){let cursor:string|undefined;for(let page=0;page<10;page++){const list=await env.PANEL.list({prefix:'media/',cursor,limit:500});const expired=list.objects.filter(o=>o.uploaded.getTime()<Date.now()-14*86400000).map(o=>o.key);if(expired.length)await env.PANEL.delete(expired);if(!list.truncated)break;cursor=list.cursor;}}
};
