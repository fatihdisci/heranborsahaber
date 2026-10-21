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
export function keyboard(id:string,revision:number) {
 return {inline_keyboard:[[{text:'Onayla',callback_data:callback('approve',id,revision)},{text:'Reddet',callback_data:callback('reject',id,revision)}],[{text:'Düzenle',callback_data:callback('edit',id,revision)},{text:'1 saat ertele',callback_data:callback('defer',id,revision)}]]};
}
export async function sendDraft(env:Env,id:string,revision:number,draft:Draft,docs:Document[],png:Uint8Array,verification:string):Promise<number> {
 if(env.MODE!=='telegram_review')throw new Error('telegram_dry_run');
 const caption=postText(draft,docs.map(d=>d.source_name));
 const meta=`SECTOR HABER · Önem: ${draft.importance}/100\n${verification==='official_attributed'?'Resmî kaynağa dayalı':verification==='multiple_families_attributed'?'Birden çok kaynak ailesi':'Kaynak aktarımı'}\n\n${docs.map(d=>d.url).join('\n')}\n\nDeneme yayını: X kapalı.`;
 // Photo bytes are uploaded; a link preview is never substituted for an image.
 const form=new FormData();form.set('chat_id',env.TELEGRAM_CHAT_ID!);form.set('photo',new Blob([png as BlobPart],{type:'image/png'}),'sector-haber.png');
 if(caption.length<=1000)form.set('caption',caption);
 const photo=await telegram(env,'sendPhoto',form);
 if(caption.length>1000)for(const chunk of splitMessage(caption))await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:chunk,link_preview_options:JSON.stringify({is_disabled:true})}));
 const card=await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:meta,reply_to_message_id:String(photo.message_id),link_preview_options:JSON.stringify({is_disabled:true}),reply_markup:JSON.stringify(keyboard(id,revision))}));
 return Number(card.message_id);
}
export function splitMessage(value:string):string[] {
 const result:string[]=[];let rest=value;
 while(rest.length>3900){let cut=rest.lastIndexOf('\n',3900);if(cut<1900)cut=rest.lastIndexOf(' ',3900);if(cut<1900)cut=3900;if(/[\uD800-\uDBFF]/.test(rest[cut-1]))cut--;result.push(rest.slice(0,cut));rest=rest.slice(cut).trimStart();}
 if(rest)result.push(rest);return result;
}
