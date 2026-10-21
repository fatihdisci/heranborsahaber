import registry from '../sources.json';
import {tick,seed,deliver,errorCode,type DraftRow} from './pipeline';
import {leaseJob,submitJob,enqueueEdit,ingestOfficial} from './bridge';
import {isOwner,telegram} from './telegram';
import {parseCallback,transition,publicationGate} from './approval';
import type {Env,Status} from './types';
const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
export async function secretEqual(a:string,b:string):Promise<boolean>{
 if(!a||!b)return false;
 const hash=async(s:string)=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));
 const [aa,bb]=await Promise.all([hash(a),hash(b)]);let diff=0;for(let i=0;i<aa.length;i++)diff|=aa[i]^bb[i];return diff===0;
}
async function body(request:Request,max=80_000):Promise<Record<string,unknown>> {
 if(Number(request.headers.get('content-length'))>max)throw new Error('request_too_large');
 const reader=request.body?.getReader();if(!reader)throw new Error('empty_request');let length=0;const parts:Uint8Array[]=[];
 try {while(true){const v=await reader.read();if(v.done)break;length+=v.value.length;if(length>max)throw new Error('request_too_large');parts.push(v.value);}}
 finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
 const all=new Uint8Array(length);let at=0;for(const p of parts){all.set(p,at);at+=p.length;}const value=JSON.parse(new TextDecoder().decode(all));if(!value||Array.isArray(value)||typeof value!=='object')throw new Error('invalid_request');return value;
}
async function webhook(request:Request,env:Env):Promise<Response> {
 if(!await secretEqual(request.headers.get('x-telegram-bot-api-secret-token')??'',env.TELEGRAM_WEBHOOK_SECRET??''))return json({error:'unauthorized'},401);
 const update=await body(request);const id=update.update_id;if(!Number.isSafeInteger(id))return json({ok:true});
 const message=update.message as {text?:string;from?:{id:number};chat?:{id:number;type:string};reply_to_message?:{message_id:number}}|undefined;
 if(message?.chat&&message.from&&message.text&&isOwner(env,String(message.from.id),String(message.chat.id),message.chat.type)) {
  const edit=await env.DB.prepare('SELECT * FROM edits WHERE user_id=? AND expires_at>?').bind(env.TELEGRAM_USER_ID!,Math.floor(Date.now()/1000)).first<{draft_id:string;revision:number;prompt_message_id:number}>();
  if(edit&&message.reply_to_message?.message_id===edit.prompt_message_id) {
   try {await enqueueEdit(env,edit.draft_id,edit.revision,message.text);await env.DB.prepare('DELETE FROM edits WHERE user_id=?').bind(env.TELEGRAM_USER_ID!).run();}
   catch {await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:'Düzenleme kaydedilemedi. Karttaki Düzenle düğmesinden tekrar deneyebilirsin.'}));}
  }
  return json({ok:true});
 }
 const cb=update.callback_query as {id:string;data:string;from:{id:number};message?:{message_id:number;chat:{id:number;type:string}}}|undefined;
 if(!cb||!cb.message||!isOwner(env,String(cb.from?.id),String(cb.message.chat?.id),cb.message.chat?.type))return json({ok:true});
 let answer='İşlem tamamlandı.';
 try {
  const action=parseCallback(cb.data);
  const row=await env.DB.prepare('SELECT * FROM drafts WHERE id=?').bind(action.id).first<DraftRow>();
  if(!row||row.revision!==action.revision||row.message_id!==cb.message.message_id)throw new Error('stale_callback');
  const state=transition(row.state as Status,action.action,row.verification,row.expires_at<Math.floor(Date.now()/1000));
  if(action.action==='edit') {
   const prompt=await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:'Bu mesaja yanıt olarak istediğin düzenlemeyi yaz. Metin kaynakla yeniden denetlenecek.',reply_markup:JSON.stringify({force_reply:true,selective:true})}));
   await env.DB.prepare('INSERT INTO edits(user_id,draft_id,revision,expires_at,prompt_message_id) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET draft_id=excluded.draft_id,revision=excluded.revision,expires_at=excluded.expires_at,prompt_message_id=excluded.prompt_message_id').bind(env.TELEGRAM_USER_ID!,row.id,row.revision,Math.floor(Date.now()/1000)+900,Number(prompt.message_id)).run();
   answer='Düzenleme isteğini gönder.';
  } else {
   const time=Math.floor(Date.now()/1000);
   const result=await env.DB.batch([
    env.DB.prepare('INSERT OR IGNORE INTO actions(update_id,draft_id,action,actor,created_at) VALUES(?,?,?,?,?)').bind(id,row.id,action.action,env.TELEGRAM_USER_ID!,time),
    env.DB.prepare('UPDATE drafts SET state=?,revision=revision+1,defer_until=? WHERE id=? AND revision=? AND state=?').bind(state,action.action==='defer'?time+3600:null,row.id,row.revision,row.state)
   ]);
   if(!result[1].meta.changes)throw new Error('stale_callback');
   if(action.action==='approve') {
    publicationGate(env.TARGET_X_USERNAME);
    await env.DB.prepare('INSERT OR IGNORE INTO publication_log(id,draft_id,revision,target,status,created_at) VALUES(?,?,?,?,?,?)').bind(crypto.randomUUID(),row.id,row.revision,'sectorhaber','approved_x_disabled',time).run();
    answer='Onaylandı. X yayını sen açtırana kadar paylaşılmayacak.';
   }else if(action.action==='defer')answer='1 saat ertelendi.';else answer='Reddedildi.';
   await telegram(env,'editMessageReplyMarkup',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(row.message_id),reply_markup:JSON.stringify({inline_keyboard:[]})}));
  }
 }catch{answer='Bu kart güncellenmiş, süresi dolmuş veya işlem daha önce tamamlanmış.';}
 await telegram(env,'answerCallbackQuery',new URLSearchParams({callback_query_id:cb.id,text:answer})).catch(()=>{});
 return json({ok:true});
}
export default {
 async fetch(request:Request,env:Env,ctx:ExecutionContext):Promise<Response> {
  const url=new URL(request.url);
  if(url.pathname==='/health')return json({service:'SECTOR HABER',mode:env.MODE,x_publishing:false,model:'Hermes / '+env.AI_MODEL});
  if(url.pathname==='/telegram/webhook'&&request.method==='POST'){try{return await webhook(request,env);}catch{return json({error:'invalid_update'},400);}}
  const bridge=url.pathname.startsWith('/api/bridge/');
  const key=bridge?env.BRIDGE_TOKEN:env.ADMIN_TOKEN;
  if(!await secretEqual(request.headers.get('authorization')??'',key?'Bearer '+key:''))return json({error:'unauthorized'},401);
  try {
   if(request.method==='POST'&&url.pathname==='/api/bridge/lease')return json(await leaseJob(env));
   if(request.method==='POST'&&url.pathname==='/api/bridge/official'){await seed(env);return json(await ingestOfficial(env,await body(request,500_000)));}
   if(request.method==='POST'&&url.pathname==='/api/bridge/result') {const result=await submitJob(env,await body(request,7_000_000));ctx.waitUntil(deliver(env));return json(result);}
   if(request.method==='POST'&&url.pathname==='/api/tick'){ctx.waitUntil(tick(env));return json({queued:true});}
   if(request.method==='GET'&&url.pathname==='/api/sources'){await seed(env);return json((await env.DB.prepare('SELECT id,enabled,next_poll,failures,last_ok,last_error,last_count FROM sources').all()).results);}
   const source=url.pathname.match(/^\/api\/sources\/([a-z0-9-]+)$/);
   if(request.method==='POST'&&source){const input=await body(request);const known=registry.find(s=>s.id===source[1]);if(!known||typeof input.enabled!=='boolean')return json({error:'invalid_source'},400);await env.DB.prepare('UPDATE sources SET enabled=?,next_poll=0 WHERE id=?').bind(Number(input.enabled),source[1]).run();return json({ok:true});}
   if(request.method==='GET'&&url.pathname==='/api/status')return json({x_publishing:false,mode:env.MODE,articles:(await env.DB.prepare('SELECT status,COUNT(*) AS count FROM articles GROUP BY status').all()).results,drafts:(await env.DB.prepare('SELECT state,delivery_state,COUNT(*) AS count FROM drafts GROUP BY state,delivery_state').all()).results,jobs:(await env.DB.prepare('SELECT state,COUNT(*) AS count FROM model_jobs GROUP BY state').all()).results});
   return json({error:'not_found'},404);
  }catch(e){return json({error:errorCode(e)},400);}
 },
 async scheduled(_event:ScheduledController,env:Env,_ctx:ExecutionContext){await tick(env);}
} satisfies ExportedHandler<Env>;
