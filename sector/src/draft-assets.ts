import {generalCsv} from './general-buyback';
import {postText} from './editorial';
import {telegram} from './telegram';
import type {DraftRow} from './pipeline';
import type {Env} from './types';

// Called only after the webhook's private-chat owner check. Downloads never
// invoke the model, change a draft's state, or expose a public media URL.
export async function sendDraftAsset(env:Env,data:string,messageId:number,updateId:number,callbackId:string):Promise<void> {
 const answer=(text:string)=>telegram(env,'answerCallbackQuery',new URLSearchParams({callback_query_id:callbackId,text})).catch(()=>{});
 if(env.MODE!=='telegram_review'){await answer('Bu işlem deneme modunda kapalı.');return;}
 const match=data.match(/^asset:(text|image|csv):([a-f\d-]{36}):(\d{1,6})$/);
 if(!match){await answer('Geçersiz düğme.');return;}
 const row=await env.DB.prepare('SELECT * FROM drafts WHERE id=?').bind(match[2]).first<DraftRow>();
 if(!row||row.revision!==Number(match[3])||row.message_id!==messageId){await answer('Kart güncellenmiş. Güncel karttaki düğmeyi kullan.');return;}
 const claim=await env.DB.prepare('INSERT OR IGNORE INTO actions(update_id,draft_id,action,actor,created_at) VALUES(?,?,?,?,?)').bind(updateId,row.id,`asset_${match[1]}`,env.TELEGRAM_USER_ID!,Math.floor(Date.now()/1000)).run();
 if(!claim.meta.changes){await answer('Bu istek zaten işlendi.');return;}
 await answer(match[1]==='text'?'Tam metin açılıyor; metnin kopyalama seçeneğini kullan.':'Orijinal görsel dosyası hazırlanıyor.');
 try {
  if(match[1]==='text'){
   const text=postText(JSON.parse(row.content));
   if(!text||text.length>4096)throw new Error('invalid_copy_text');
   // Entity offsets use UTF-16, as does JavaScript length. No Markdown/HTML
   // parsing: punctuation, tags and emojis remain byte-for-byte intact.
   await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text,entities:JSON.stringify([{type:'pre',offset:0,length:text.length}]),link_preview_options:JSON.stringify({is_disabled:true})}));
  }else if(match[1]==='csv'){
   const g=JSON.parse(row.content).card_data?.report?.general;if(!g)throw Error('report_missing');
   const form=new FormData();form.set('chat_id',env.TELEGRAM_CHAT_ID!);form.set('document',new Blob([generalCsv(g)],{type:'text/csv;charset=utf-8'}),'endeks-genel-gerialim-'+g.day+'.csv');await telegram(env,'sendDocument',form);
  }else{
   const object=row.media_key?await env.MEDIA.get(row.media_key):null;
   if(!object)throw new Error('draft_media_missing');
   const png=await object.arrayBuffer();
   const form=new FormData();form.set('chat_id',env.TELEGRAM_CHAT_ID!);
   form.set('document',new Blob([png],{type:'image/png'}),'endeks-haber.png');
   form.set('disable_content_type_detection','true');
   await telegram(env,'sendDocument',form);
  }
 }catch{
  // A timeout may follow successful delivery. Do not automatically duplicate
  // the file/message; a new explicit press is safe to try again.
  await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:'Gönderim doğrulanamadı. Metin veya dosya gelmediyse karttaki düğmeye yeniden basabilirsin.'})).catch(()=>{});
 }
}
