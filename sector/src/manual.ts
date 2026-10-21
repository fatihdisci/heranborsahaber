import {isOwner,telegram} from './telegram';
import type {Env} from './types';
export interface InputMessage {message_id:number;text?:string;caption?:string;document?:{file_id:string;file_size?:number;file_name?:string;mime_type?:string};from?:{id:number};chat?:{id:number;type:string};reply_to_message?:{message_id:number};}
export async function queueManual(env:Env,updateId:number,m:InputMessage):Promise<boolean> {
 if(!m.from||!m.chat||!isOwner(env,String(m.from.id),String(m.chat.id),m.chat.type)||!Number.isSafeInteger(m.message_id)||!Number.isSafeInteger(updateId))return false;
 const text=(m.text??m.caption??'').trim();
 if(text.startsWith('/start')||text==='/help'){
  if(env.MODE!=='telegram_review')return true;
  const source=text.match(/^\/start source_(\d+)$/);
  if(source){const id=Number(source[1]),row=await env.DB.prepare('SELECT message_id FROM manual_requests WHERE message_id=?').bind(id).first();
   if(row)await telegram(env,'copyMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,from_chat_id:env.TELEGRAM_CHAT_ID!,message_id:String(id)}));
  }else await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text:'Haber bağlantısını, KAP bağlantısını, PDF dosyasını veya haber metnini buraya gönder. Kaynağın tamamını okuyup SECTOR HABER tarzında tweet ve görsel hazırlayacağım. Okunamayan içerikten taslak üretmem.'}));
  return true;
 }
 const url=text.match(/https:\/\/[^\s<>]+/)?.[0]?.replace(/[),.;]+$/,'');
 const kind=m.document?'pdf':url?'url':text.length>=100?'text':null;
 if(!kind)return false;
 const input=JSON.stringify({url,text,document:m.document??null});if(input.length>150_000)throw Error('manual_input_limit');
 await env.DB.prepare('INSERT OR IGNORE INTO manual_requests(update_id,message_id,kind,input,created_at) VALUES(?,?,?,?,?)').bind(updateId,m.message_id,kind,input,Math.floor(Date.now()/1000)).run();
 return true;
}
