import {callback} from './approval';
import {postText} from './editorial';
import type {Env,Draft,Document} from './types';
export function isOwner(env:Env,from:string,chat:string,type:string):boolean {
 return !!env.TELEGRAM_USER_ID&&!!env.TELEGRAM_CHAT_ID&&type==='private'&&from===env.TELEGRAM_USER_ID&&chat===env.TELEGRAM_CHAT_ID;
}
export class TelegramError extends Error {constructor(public code:number,public retryAfter=60){super(`telegram_http_${code}`);}}
export async function telegram(env:Env,method:string,body:URLSearchParams|FormData,fetcher:typeof fetch=fetch):Promise<Record<string,unknown>> {
 if(!env.TELEGRAM_BOT_TOKEN||!env.TELEGRAM_VERIFIED_BOT_ID||!env.TELEGRAM_BOT_TOKEN.startsWith(env.TELEGRAM_VERIFIED_BOT_ID+':'))throw new Error('telegram_identity_not_configured');
 const r=await fetcher(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`,{method:'POST',body,signal:AbortSignal.timeout(20_000)});
 const data=await r.json() as {ok:boolean;error_code?:number;parameters?:{retry_after?:number};result:Record<string,unknown>};
 if(!r.ok||!data.ok)throw new TelegramError(data.error_code??r.status,Math.min(3600,data.parameters?.retry_after??60));return data.result;
}
export function sourceKeyboard(docs:Document[]) {
 const urls=[...new Set(docs.map(d=>d.url))];
 if(!urls.length)throw new Error('source_url_missing');
 for(const value of urls){const u=new URL(value);if(u.protocol!=='https:'||u.username||u.password)throw new Error('source_url_invalid');}
 return [[{text:'Kaynağı aç',url:urls[0]}]];
}
export function keyboard(id:string,revision:number,docs:Document[],caption:string) {
 // Telegram's native clipboard button accepts at most 256 characters. Never
 // truncate a post to fit it; longer posts use a copyable preformatted message.
 const copy=caption.length<=256?{text:'Tweet’i kopyala',copy_text:{text:caption}}:{text:'Tweet’i kopyala',callback_data:`asset:text:${id}:${revision}`};
 return {inline_keyboard:[...sourceKeyboard(docs),[copy],[{text:'Düzenle',callback_data:callback('edit',id,revision)}]]};
}
export async function sendDraft(env:Env,id:string,revision:number,draft:Draft,docs:Document[],png:Uint8Array,_verification:string,existingMessageId?:number,fetcher:typeof fetch=fetch):Promise<number> {
 if(env.MODE!=='telegram_review')throw new Error('telegram_dry_run');
 const caption=postText(draft);
 // Fail before uploading anything; never produce an orphan photo or split post.
 if(caption.length>1024)throw new Error('telegram_caption_too_long');
 const markup=keyboard(id,revision,docs,caption);
 const form=new FormData();form.set('chat_id',env.TELEGRAM_CHAT_ID!);form.set('photo',new Blob([png as BlobPart],{type:'image/png'}),'sector-haber.png');
 form.set('reply_markup',JSON.stringify(markup));
 if(existingMessageId){
  form.set('message_id',String(existingMessageId));form.set('media',JSON.stringify({type:'photo',media:'attach://photo',caption}));
  const result=await telegram(env,'editMessageMedia',form,fetcher);return Number(result.message_id??existingMessageId);
 }
 form.set('caption',caption);
 const result=await telegram(env,'sendPhoto',form,fetcher);return Number(result.message_id);
}
