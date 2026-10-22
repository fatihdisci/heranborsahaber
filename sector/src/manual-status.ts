import {telegram,TelegramError} from './telegram';
import type {Env} from './types';
const key=(id:number)=>'manual_status:'+id;
export async function manualStatusId(env:Env,id:number):Promise<number|undefined>{
 const row=await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind(key(id)).first<{value:string}>();
 const value=Number(row?.value);return Number.isSafeInteger(value)&&value>0?value:undefined;
}
export async function ensureManualStatus(env:Env,id:number,replyTo:number,text='İçeriğini aldım. Kaynağı okuyup tweet ve görselini hazırlıyorum. Hazır olduğunda bu mesaj güncellenecek.'):Promise<void>{
 if(env.MODE!=='telegram_review')return;
 // Claim first: a timeout must not create duplicate acknowledgements.
 const claimed=await env.DB.prepare("INSERT INTO system_state(key,value) VALUES(?,'sending') ON CONFLICT(key) DO UPDATE SET value='sending' WHERE value='retry'").bind(key(id)).run();
 if(!claimed.meta.changes)return;
 try{
  const sent=await telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text,reply_parameters:JSON.stringify({message_id:replyTo,allow_sending_without_reply:true})}));
  await env.DB.prepare('UPDATE system_state SET value=? WHERE key=?').bind(String(sent.message_id),key(id)).run();
 }catch(e){
  await env.DB.prepare('UPDATE system_state SET value=? WHERE key=?').bind(e instanceof TelegramError&&e.code===429?'retry':'uncertain',key(id)).run();
 }
}
