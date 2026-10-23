import type {Env} from './types';import {telegram} from './telegram';import {newsKeyboard} from './telegram-ui';
export async function newsMenuRow(env:Env,id:string,messageId?:number){return env.DB.prepare(`SELECT c.id,c.article_id,c.message_id,c.state,a.url,a.source_id,n.id candidate_id,i.choice FROM news_cards c JOIN articles a ON a.id=c.article_id LEFT JOIN news_candidates n ON n.article_id=a.id LEFT JOIN news_interests i ON i.article_id=a.id AND i.actor=? WHERE c.id=? AND (? IS NULL OR c.message_id=?) AND c.state IN ('sending','sent','failed','requested','model_queued','complete')`).bind(env.TELEGRAM_USER_ID!,id,messageId??null,messageId??null).first<any>();}
export async function previewMarkup(env:Env,id:string,url:string,view:'main'|'more'='main'){
 const row=await newsMenuRow(env,id);let retryRevision: number|undefined;
 if(view==='more'){const d=await env.DB.prepare("SELECT d.revision FROM articles a LEFT JOIN model_jobs j ON j.article_id=a.id AND j.expected_revision=0 JOIN drafts d ON d.id=COALESCE(a.draft_id,j.result_draft) WHERE a.id=? AND d.delivery_state='uncertain' ORDER BY d.revision DESC LIMIT 1").bind(row?.article_id??'').first<{revision:number}>();retryRevision=d?.revision;}
 return newsKeyboard(id,url,row?.choice??null,view,retryRevision,!!row?.candidate_id);
}
export async function refreshNewsMenu(env:Env,id:string,messageId?:number,view:'main'|'more'='main'){
 const row=await newsMenuRow(env,id,messageId);if(!row?.message_id)return false;
 await telegram(env,'editMessageReplyMarkup',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(row.message_id),reply_markup:JSON.stringify(await previewMarkup(env,id,row.url,view))}));return true;
}
export async function newsMenuCallback(env:Env,data:string,messageId:number,update:number):Promise<string|null>{
 const menu=/^nm:(main|more):([a-f0-9-]{36})$/.exec(data),interest=/^ni:(l|d):([a-f0-9-]{36})$/.exec(data);if(!menu&&!interest)return null;
 const id=(menu??interest)![2],row=await newsMenuRow(env,id,messageId);if(!row)return 'Bu haber kartı artık kullanılamıyor.';
 if(menu){await refreshNewsMenu(env,id,messageId,menu[1] as 'main'|'more');return '';}
 const choice=interest![1]==='l'?'like':'dislike',actor=env.TELEGRAM_USER_ID!,at=Date.now();
 // State change + callback receipt are atomic. Duplicate and older callbacks never retoggle.
 await env.DB.batch([
 env.DB.prepare(`INSERT INTO news_interests(actor,article_id,candidate_id,source_id,choice,update_id,updated_at) SELECT ?,?,?,?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM news_interest_actions WHERE update_id=?) ON CONFLICT(actor,article_id) DO UPDATE SET choice=CASE WHEN news_interests.choice=excluded.choice THEN NULL ELSE excluded.choice END,candidate_id=excluded.candidate_id,source_id=excluded.source_id,update_id=excluded.update_id,updated_at=excluded.updated_at WHERE excluded.update_id>news_interests.update_id`).bind(actor,row.article_id,row.candidate_id,row.source_id,choice,update,at,update),
 env.DB.prepare('INSERT OR IGNORE INTO news_interest_actions(update_id,actor,article_id,choice,created_at) VALUES(?,?,?,?,?)').bind(update,actor,row.article_id,choice,at)
 ]);
 await refreshNewsMenu(env,id,messageId);return '';
}
export async function interestSummary(env:Env){
 const counts=(await env.DB.prepare("SELECT choice,COUNT(*) n FROM news_interests WHERE choice IS NOT NULL AND actor=? GROUP BY choice").bind(env.TELEGRAM_USER_ID!).all<{choice:string;n:number}>()).results;
 const sources=(await env.DB.prepare('SELECT source_id,choice,COUNT(*) n FROM news_interests WHERE choice IS NOT NULL AND actor=? GROUP BY source_id,choice').bind(env.TELEGRAM_USER_ID!).all()).results;
 return {likes:counts.find(r=>r.choice==='like')?.n??0,dislikes:counts.find(r=>r.choice==='dislike')?.n??0,sources,note:'Sahibin haber/konu ilgisi; yayın onayı, anlık rota veya üç rotalı insan incelemesi değildir. Tıklanmama olumsuz sayılmaz; kaynak/şirket otomatik susturulmaz.'};
}
