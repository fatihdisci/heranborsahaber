import type {Env} from './types';import {telegram} from './telegram';import {draftKeyboard,publicationState,type DraftView} from './telegram-ui';
export async function draftMenu(env:Env,row:any,view:DraftView='main'){
 const state=await publicationState(env,row.id),editable=row.state==='pending'&&row.expires_at>Math.floor(Date.now()/1000);
 return draftKeyboard(row.id,row.revision,JSON.parse(row.documents),env.X_PUBLISH_ENABLED==='true',JSON.parse(row.content),state,view,editable);
}
export async function refreshDraftMenu(env:Env,id:string,view:DraftView='main'){
 const row=await env.DB.prepare('SELECT * FROM drafts WHERE id=?').bind(id).first<any>();if(!row?.message_id||!['sent','expired'].includes(row.delivery_state))return false;
 await telegram(env,'editMessageReplyMarkup',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(row.message_id),reply_markup:JSON.stringify(await draftMenu(env,row,view))}));return true;
}
export async function cardMenuCallback(env:Env,data:string,messageId:number):Promise<string|null>{
 const m=/^dm:(main|more|layouts|summary):([a-f0-9-]{36}):(\d+)$/.exec(data);if(!m)return null;
 const row=await env.DB.prepare("SELECT * FROM drafts WHERE id=? AND revision=? AND message_id=? AND delivery_state IN ('sent','expired')").bind(m[2],Number(m[3]),messageId).first<any>();if(!row)return 'Kart değişmiş; güncel kartı kullan.';
 if(m[1]==='summary'){const s=await publicationState(env,row.id);return s.published?`${s.manual?'Elle paylaşıldı':'X API ile paylaşıldı'}${s.published_at?' · '+new Date(s.published_at).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'}):''}.`:s.api==='uncertain'?'X gönderiminin sonucu belirsiz; tekrar gönderilmez.':s.api?'X paylaşımı sırada veya işleniyor.':'Bu içerik henüz paylaşıldı olarak kayıtlı değil.';}
 await refreshDraftMenu(env,row.id,m[1] as DraftView);return '';
}
