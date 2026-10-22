import {retryDraftDelivery,deliveryTarget} from './delivery-recovery';
import {topicScore} from './editorial';
import type {Source} from './types';
import {telegram,TelegramError} from './telegram';
import {titleSimilarity} from './dedupe';
import type {Env} from './types';
export function previewText(source:string,title:string,summary:string):string {
 const clean=(s:string)=>s.replace(/\s+/g,' ').trim();
 const t=clean(title),s=clean(summary);
 return [source,t,s&&s!==t?(s.length>700?s.slice(0,697)+'…':s):''].filter(Boolean).join('\n\n').slice(0,3500);
}
export function previewDuplicate(a:string,b:string):boolean {
 const numbers=(s:string)=>[...s.matchAll(/\d+(?:[.,]\d+)*/g)].map(m=>m[0]).join('|');
 const subject=(s:string)=>s.normalize('NFKC').toLocaleLowerCase('tr-TR').replace(/[^\p{L}\p{N}]+/gu,' ').trim().split(' ').slice(0,2).join(' ');
 return subject(a)===subject(b)&&numbers(a)===numbers(b)&&titleSimilarity(a,b)>=.9;
}
function markup(id:string,url:string){return {inline_keyboard:[[{text:'Kaynağı aç',url}],[{text:'✨ Tweet ve görsel oluştur',callback_data:'news:'+id}]]};}
export async function requestNews(env:Env,id:string,messageId:number,confirmedRevision?:number):Promise<string> {
 const row=await env.DB.prepare('SELECT * FROM news_cards WHERE id=? AND message_id=?').bind(id,messageId).first<{article_id:string;state:string}>();
 if(!row)return 'Bu haber kartı artık kullanılamıyor.';
 const existing=await env.DB.prepare('SELECT d.id,d.delivery_state,d.revision,a.url FROM articles a LEFT JOIN model_jobs j ON j.article_id=a.id AND j.expected_revision=0 JOIN drafts d ON d.id=COALESCE(a.draft_id,j.result_draft) WHERE a.id=?').bind(row.article_id).first<{id:string;delivery_state:string;revision:number;url:string}>();
 if(existing){
  const result=await retryDraftDelivery(env,existing.id,confirmedRevision);
  if(result==='sent'){await env.DB.prepare("UPDATE news_cards SET state='complete' WHERE id=?").bind(id).run();return 'Bu haberin tweet ve görseli zaten hazırlandı.';}
  if(result==='queued'){await env.DB.prepare("UPDATE news_cards SET state='model_queued' WHERE id=?").bind(id).run();return 'Hazır tweet ve görselin teslimatı sıraya alındı. Yeniden AI kullanılmayacak.';}
  if(result==='confirm'){
   if(env.MODE==='telegram_review')await telegram(env,'editMessageReplyMarkup',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(messageId),reply_markup:JSON.stringify({inline_keyboard:[[{text:'Kaynağı aç',url:existing.url}],[{text:'Mesaj gelmediyse yeniden gönder (çift olabilir)',callback_data:`newsretry:${id}:${existing.revision}`}]]})}));
   return 'Teslimat belirsiz; mesaj gelmiş olabilir. Yeniden gönderim için karttaki onay düğmesini kullan.';
  }
  return 'Hazır taslak için güvenli yeniden deneme sınırı veya süre doldu; yeniden içerik üretilmedi.';
 }

 if(['requested','model_queued'].includes(row.state))return 'Hazırlama isteğin zaten sırada.';
 if(row.state==='complete')return 'Bu haberin tweet ve görseli zaten hazırlandı.';
 if(!['sent','failed'].includes(row.state))return 'Bu kart için işlem yapılamıyor.';
 const claimed=await env.DB.prepare("UPDATE news_cards SET state='requested',requested_at=? WHERE id=? AND state IN ('sent','failed')").bind(Math.floor(Date.now()/1000),id).run();
 if(!claimed.meta.changes)return 'Hazırlama isteğin zaten sırada.';
 await env.DB.prepare("UPDATE articles SET status='queued',attempts=0,next_try=0,lease_until=0,error=NULL WHERE id=? AND status NOT IN ('prepared','duplicate')").bind(row.article_id).run();
 return 'Tam haber okunup tweet ve görsel hazırlanacak.';
}
export async function announceNews(env:Env):Promise<void> {
 if(env.MODE!=='telegram_review')return;
 const time=Math.floor(Date.now()/1000);
 await env.DB.prepare("UPDATE news_cards SET state='uncertain' WHERE state='sending' AND next_try<?").bind(time).run();
 const cutoff=(await env.DB.prepare("SELECT value FROM system_state WHERE key='news_preview_since'").first<{value:string}>())?.value??new Date(Date.now()-300_000).toISOString();
 // Already displayed stories and uncertain sends are never replayed after restart.
 const rows=await env.DB.prepare(`SELECT a.*,s.config,c.id AS card_id,c.state AS card_state FROM articles a JOIN sources s ON s.id=a.source_id LEFT JOIN news_cards c ON c.article_id=a.id WHERE s.enabled=1 AND a.status='queued' AND a.published_at>=? AND (c.id IS NULL OR (c.state='waiting' AND c.next_try<=?)) ORDER BY (julianday(a.published_at)*1440+COALESCE(json_extract(s.config,'$.editorial_priority'),50)/10) DESC LIMIT 3`).bind(cutoff,time).all<{id:string;title:string;summary:string;url:string;published_at:string;config:string;card_id:string|null}>();
 for(const a of rows.results??[]){
  const source=JSON.parse(a.config) as Source;if(topicScore(a.title,a.summary,source.official).score<(source.minimum_score??60))continue;
  const id=a.card_id??crypto.randomUUID();
  if(!a.card_id){
   const existing=await env.DB.prepare("SELECT c.id,a.title FROM news_cards c JOIN articles a ON a.id=c.article_id WHERE c.state!='duplicate' AND ABS(julianday(a.published_at)-julianday(?))<0.25").bind(a.published_at).all<{id:string;title:string}>();
   const parent=(existing.results??[]).find(r=>previewDuplicate(a.title,r.title));
   const inserted=await env.DB.prepare("INSERT OR IGNORE INTO news_cards(id,article_id,state,created_at,parent_id) VALUES(?,?,?,?,?)").bind(id,a.id,parent?'duplicate':'waiting',time,parent?.id??null).run();
   if(!inserted.meta.changes||parent)continue;
  }
  const locked=await env.DB.prepare("UPDATE news_cards SET state='sending',next_try=? WHERE id=? AND state='waiting'").bind(time+120,id).run();if(!locked.meta.changes)continue;
  try{
   const sent=await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:previewText(JSON.parse(a.config).name,a.title,a.summary),link_preview_options:JSON.stringify({is_disabled:true}),reply_markup:JSON.stringify(markup(id,a.url))}));
   await env.DB.prepare("UPDATE news_cards SET state='sent',message_id=? WHERE id=?").bind(Number(sent.message_id),id).run();
  }catch(e){const retry=e instanceof TelegramError&&e.code===429;await env.DB.prepare('UPDATE news_cards SET state=?,next_try=? WHERE id=?').bind(retry?'waiting':'uncertain',time+(e instanceof TelegramError?e.retryAfter:300),id).run();}
 }
}
export async function refreshNewsRequests(env:Env):Promise<void>{
 const rows=await env.DB.prepare(`SELECT c.id,c.message_id,c.state,a.title,a.summary,a.url,a.error,a.status,s.config,j.state AS job_state,d.id AS draft_id,d.message_id AS draft_message_id,d.delivery_state FROM news_cards c JOIN articles a ON a.id=c.article_id JOIN sources s ON s.id=a.source_id LEFT JOIN model_jobs j ON j.article_id=a.id AND j.expected_revision=0 LEFT JOIN drafts d ON d.id=COALESCE(j.result_draft,a.draft_id) WHERE c.state IN ('requested','model_queued')`).all<{id:string;message_id:number;state:string;title:string;summary:string;url:string;error:string|null;status:string;config:string;job_state:string|null;delivery_state:string|null;draft_id:string|null;draft_message_id:number|null}>();
 for(const r of rows.results??[]){
  if(r.delivery_state==='sent'){await env.DB.prepare("UPDATE news_cards SET state='complete' WHERE id=?").bind(r.id).run();continue;}
  if(r.status!=='needs_review'&&!['needs_review','expired'].includes(r.job_state??'')&&!['uncertain','failed','suppressed'].includes(r.delivery_state??''))continue;
  const changed=await env.DB.prepare("UPDATE news_cards SET state='failed' WHERE id=? AND state IN ('requested','model_queued')").bind(r.id).run();
  const deliveryProblem=['uncertain','failed','suppressed'].includes(r.delivery_state??'');
  const known=r.draft_id?await deliveryTarget(env,r.draft_id,r.draft_message_id):undefined;
  const note=r.delivery_state==='suppressed'?'Bu içerik güncel gönderim tercihlerine göre kapatıldı.':deliveryProblem?(r.delivery_state==='uncertain'&&!known?'Tweet ve görsel hazır, ancak teslimat doğrulanamadı. Mesaj gelmiş olabilir. Aynı düğme güvenli yeniden gönderim seçeneğini açar.':'Tweet ve görsel hazır. Teslimatı aynı düğmeyle yeniden deneyebilirsin; AI tekrar çalışmaz.'):'Taslak doğrulanamadı. Aynı düğmeyle yeniden deneyebilirsin.';
  if(changed.meta.changes&&env.MODE==='telegram_review')await telegram(env,'editMessageText',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(r.message_id),text:previewText(JSON.parse(r.config).name,r.title,r.summary)+'\n\n'+note,link_preview_options:JSON.stringify({is_disabled:true}),reply_markup:JSON.stringify(markup(r.id,r.url))})).catch(()=>{});
 }
}
