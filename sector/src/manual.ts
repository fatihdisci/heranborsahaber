import {ensureManualStatus} from './manual-status';
import {isOwner,telegram} from './telegram';
import {marketInput} from './market-input';
import type {Env} from './types';
export interface InputMessage {message_id:number;text?:string;caption?:string;photo?:{file_id:string;file_size?:number;width:number;height:number}[];document?:{file_id:string;file_size?:number;file_name?:string;mime_type?:string};forward_origin?:{type:string;sender_user?:{is_bot?:boolean;username?:string}};from?:{id:number};chat?:{id:number;type:string};reply_to_message?:{message_id:number};}
export async function queueManual(env:Env,updateId:number,m:InputMessage):Promise<boolean> {
 if(!m.from||!m.chat||!isOwner(env,String(m.from.id),String(m.chat.id),m.chat.type)||!Number.isSafeInteger(m.message_id)||!Number.isSafeInteger(updateId))return false;
 const text=(m.text??m.caption??'').trim();
 if(text.startsWith('/start')||text==='/help'){
  if(env.MODE!=='telegram_review')return true;
  const source=text.match(/^\/start source_(\d+)$/);
  if(source){const id=Number(source[1]),row=await env.DB.prepare('SELECT message_id FROM manual_requests WHERE message_id=?').bind(id).first();
   if(row)await telegram(env,'copyMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,from_chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(id)}));
  }else await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:'Haber veya KAP bağlantısını, PDF dosyasını, metni ya da görseli buraya gönder. Diğer botun /kurum, /akd ve /takas yanıtlarını da iletebilirsin. Kaynağı okuyup ENDEKS HABER tarzında tweet ve kart hazırlayacağım. Veri tarihini tahmin etmem; okunamayan sayıdan içerik üretmem.'}));
  return true;
 }
 const url=text.match(/https:\/\/[^\s<>]+/)?.[0]?.replace(/[),.;]+$/,'');
 const photo=Array.isArray(m.photo)?m.photo.filter(p=>p&&typeof p.file_id==='string'&&Number.isSafeInteger(p.width)&&p.width>0&&Number.isSafeInteger(p.height)&&p.height>0).sort((a,b)=>b.width*b.height-a.width*a.height)[0]:undefined;
 const imageDocument=m.document&&(/^image\/(?:jpeg|png|webp)$/.test(m.document.mime_type??'')||/\.(?:jpe?g|png|webp)$/i.test(m.document.file_name??''))?m.document:undefined;
 const image=photo??imageDocument;
 const kind=image?'image':m.document?'pdf':marketInput(text)?'text':url?'url':text.length>=100?'text':null;
 if(!kind)return false;
 const username=m.forward_origin?.type==='user'&&m.forward_origin.sender_user?.is_bot?m.forward_origin.sender_user.username:undefined;
 const input=JSON.stringify({url,text,document:m.document??null,image:image??null,...(username&&/^[a-zA-Z0-9_]{5,32}$/.test(username)?{origin_bot:username}:{})});if(input.length>150_000)throw Error('manual_input_limit');
 const inserted=await env.DB.prepare('INSERT OR IGNORE INTO manual_requests(update_id,message_id,kind,input,created_at) VALUES(?,?,?,?,?)').bind(updateId,m.message_id,kind,input,Math.floor(Date.now()/1000)).run();
 if(inserted.meta.changes)await ensureManualStatus(env,updateId,m.message_id);
 return true;
}
