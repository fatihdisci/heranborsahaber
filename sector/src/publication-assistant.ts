import type {Env} from './types';
import {telegram,keyboard} from './telegram';
import {postText} from './editorial';
export const publicationSQL=`SELECT draft_id,MIN(finished_at) published_at,'api' method FROM x_posts WHERE state='sent' GROUP BY draft_id UNION ALL SELECT draft_id,published_at,'manual' method FROM publication_marks m WHERE state='published' AND NOT EXISTS(SELECT 1 FROM x_posts x WHERE x.draft_id=m.draft_id AND x.state='sent')`;
export function cadence(last:number|null,now=Date.now()){
 if(!last)return 'İlk kayıt. Son dakika haberini bekletme.';
 const minutes=Math.max(0,Math.floor((now-last)/60000)),hour=new Date(now+10800000).getUTCHours();
 return `${minutes} dakika geçti. `+(hour<8||hour>=22?'Dinlenme saatleri; paylaşım zorunlu değil.':minutes<20?'Çok yakın. Rutin içerikse bekletebilirsin; son dakika hariç.':minutes<45?'Kısa aralık. Rutin içerik biraz bekleyebilir.':minutes<=90?'Rutin paylaşım için uygun aralık.':'Uzun ara. Yeni, değerli haber varsa paylaşabilirsin; zorunlu değil.');
}
export async function publicationSummary(env:Env,now=Date.now()){
 const day=new Date(now+10800000).toISOString().slice(0,10),start=Date.parse(day+'T00:00:00+03:00');
 const all=(await env.DB.prepare(publicationSQL).all<{draft_id:string;published_at:number;method:string}>()).results;
 const today=all.filter(r=>r.published_at>=start&&r.published_at<start+86400000);const last=all.length?Math.max(...all.map(r=>r.published_at)):null;
 const reserved=(await env.DB.prepare("SELECT COUNT(*) n FROM x_posts WHERE day=? AND state IN ('queued','uploading','posting','sent','uncertain')").bind(day).first<{n:number}>())?.n??0;
 const api=today.filter(r=>r.method==='api').length;return {day,reserved,total:today.length,manual:today.length-api,api,last,note:cadence(last,now)};
}
export async function refreshPublicationCard(env:Env,id:string){
 const r=await env.DB.prepare('SELECT * FROM drafts WHERE id=?').bind(id).first<any>();if(!r?.message_id)return;
 const mark=await env.DB.prepare('SELECT state FROM publication_marks WHERE draft_id=?').bind(id).first<{state:string}>();
 const api=await env.DB.prepare("SELECT state FROM x_posts WHERE draft_id=? AND state IN ('queued','uploading','posting','sent','uncertain') LIMIT 1").bind(id).first<{state:string}>();
 const published=api?.state==='sent'||mark?.state==='published';
 const m=keyboard(id,r.revision,JSON.parse(r.documents),postText(JSON.parse(r.content)),env.X_PUBLISH_ENABLED==='true'&&!published&&!api);
 if(published){m.inline_keyboard=m.inline_keyboard.map(row=>row.filter(b=>!('callback_data'in b&&(b.callback_data?.startsWith('pub:mark:')||b.callback_data?.startsWith('pub:defer:'))))).filter(row=>row.length);m.inline_keyboard.push([{text:'☑️',callback_data:'pub:stats:'+id},...(api?[]:[{text:'🕒',callback_data:'pub:time:'+id},{text:'↩️',callback_data:'pub:undo:'+id}])]);}
 if(JSON.parse(r.content).card_data?.report?.general)m.inline_keyboard.push([{text:'📄',callback_data:`asset:csv:${id}:${r.revision}`},{text:'🖼',callback_data:`asset:image:${id}:${r.revision}`}]);
 if(mark?.state==='deferred'&&!published)m.inline_keyboard.push([{text:'▶️',callback_data:'pub:undo:'+id}]);
 await telegram(env,'editMessageReplyMarkup',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(r.message_id),reply_markup:JSON.stringify(m)}));
}
export async function publicationAction(env:Env,action:string,id:string,update:number,messageId?:number,now=Date.now()){
 const row=await env.DB.prepare("SELECT message_id,delivery_state FROM drafts WHERE id=?").bind(id).first<{message_id:number;delivery_state:string}>();
 if(!row||row.delivery_state!=='sent'||messageId!==undefined&&row.message_id!==messageId)return 'Güncel içerik kartını kullan.';
 if(!['mark','undo','defer','time','stats'].includes(action))return 'Geçersiz işlem.';
 if(action==='time'){
  const p=await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:'Manuel yayın zamanını bu mesaja yanıtla: YYYY-MM-DD HH:MM veya yalnız HH:MM (bugün). İstanbul saati.',reply_markup:JSON.stringify({force_reply:true,selective:true})}));
  await env.DB.prepare('INSERT OR REPLACE INTO publication_time_edits VALUES(?,?,?,?)').bind(env.TELEGRAM_USER_ID!,id,Number(p.message_id),now+900000).run();return 'Yayın saatini yanıt olarak yaz.';
 }
 const before=await publicationSummary(env,now);
 if(action!=='stats'){
  if(action==='defer'&&await env.DB.prepare("SELECT 1 FROM publication_marks WHERE draft_id=? AND state='published'").bind(id).first())return 'Yayımlanmış içerik ertelenemez. Hatalı işaret için geri al düğmesini kullan.';
  const existing=await env.DB.prepare("SELECT 1 FROM x_posts WHERE draft_id=? AND state IN ('queued','uploading','posting','sent','uncertain')").bind(id).first();
  if(existing)return 'API yayını mevcut veya sonucu bekleniyor. Manuel işaret değişmedi.';
  await env.DB.batch([
   env.DB.prepare(`INSERT INTO publication_marks(draft_id,state,published_at,updated_at) SELECT ?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM publication_actions WHERE update_id=?) AND NOT EXISTS(SELECT 1 FROM x_posts WHERE draft_id=? AND state IN ('queued','uploading','posting','sent','uncertain')) ON CONFLICT(draft_id) DO UPDATE SET state=excluded.state,published_at=CASE WHEN publication_marks.state='published' AND excluded.state='published' THEN publication_marks.published_at ELSE excluded.published_at END,updated_at=excluded.updated_at WHERE NOT (publication_marks.state='published' AND excluded.state='deferred')`).bind(id,action==='mark'?'published':action==='defer'?'deferred':'ready',action==='mark'?now:null,now,update,id),
   env.DB.prepare('INSERT OR IGNORE INTO publication_actions VALUES(?,?)').bind(update,now)
  ]);
 }
 await refreshPublicationCard(env,id);
 const s=await publicationSummary(env,now);return `${action==='mark'?'✅ Manuel yayın kaydedildi. ':action==='undo'?'↩️ İşaret geri alındı. ':action==='defer'?'⏸ Ertelendi (otomatik paylaşılmaz). ':''}Bugün ${s.total}: ${s.manual} manuel / ${s.api} API. Bütçe ${s.reserved}/20. Son: ${s.last?new Date(s.last).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit'}):'—'}. ${action==='mark'?before.note:s.note}`;
}
export async function publicationMessage(env:Env,m:any,update:number){
 if(m.text==='/yayinlar'||m.text==='/yayınlar'){const s=await publicationSummary(env);await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:`Bugün ${s.total} paylaşım: ${s.manual} manuel / ${s.api} API. API bütçesi ${s.reserved}/20. Son yayın: ${s.last?new Date(s.last).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'}):'—'}. ${s.note}`}));return true;}
 const start=m.text?.match(/^\/start pub_(mark|undo|defer|time|stats)_([a-f0-9-]{36})$/);
 if(start){const text=await publicationAction(env,start[1],start[2],update);await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text}));return true;}
 const edit=await env.DB.prepare('SELECT * FROM publication_time_edits WHERE user_id=? AND expires_at>? AND prompt_message_id=?').bind(env.TELEGRAM_USER_ID!,Date.now(),m.reply_to_message?.message_id??0).first<any>();if(!edit)return false;
 const v=m.text?.trim().match(/^(?:(\d{4}-\d{2}-\d{2}) )?(\d{2}):(\d{2})$/);const date=v?.[1]??new Date(Date.now()+10800000).toISOString().slice(0,10);const at=v?Date.parse(`${date}T${v[2]}:${v[3]}:00+03:00`):NaN;
 let text='Geçerli, gelecekte olmayan bir İstanbul tarihi ve saati yaz.';
 if(Number.isFinite(at)&&at<=Date.now()&&new Date(at+10800000).toISOString().slice(0,10)===date){
  const r=await env.DB.prepare("UPDATE publication_marks SET published_at=?,updated_at=? WHERE draft_id=? AND state='published' AND NOT EXISTS(SELECT 1 FROM x_posts WHERE draft_id=? AND state='sent')").bind(at,Date.now(),edit.draft_id,edit.draft_id).run();text=r.meta.changes?'Manuel yayın saati güncellendi.':'Önce manuel paylaşıldı işaretle. API yayın saati değiştirilemez.';

 }
 await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text}));if(Number.isFinite(at)&&at<=Date.now()&&new Date(at+10800000).toISOString().slice(0,10)===date)await env.DB.prepare('DELETE FROM publication_time_edits WHERE user_id=?').bind(env.TELEGRAM_USER_ID!).run();return true;
}
