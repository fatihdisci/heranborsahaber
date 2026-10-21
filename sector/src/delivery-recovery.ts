import {manualStatusId} from './manual-status';
import type {Env} from './types';
export async function deliveryTarget(env:Env,id:string,messageId?:number|null):Promise<number|undefined>{
 for(const key of ['telegram_photo:'+id,'telegram_target:'+id]){
  const row=await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind(key).first<{value:string}>();
  const value=Number(row?.value);if(Number.isSafeInteger(value)&&value>0)return value;
 }
 if(Number.isSafeInteger(messageId)&&messageId!>0)return messageId!;
 const manual=await env.DB.prepare('SELECT m.update_id FROM manual_requests m JOIN model_jobs j ON j.id=m.job_id WHERE j.result_draft=? ORDER BY m.created_at LIMIT 1').bind(id).first<{update_id:number}>();
 return manual?manualStatusId(env,manual.update_id):undefined;
}
export async function retryDraftDelivery(env:Env,id:string,confirmedRevision?:number):Promise<'queued'|'confirm'|'blocked'|'sent'> {
 const row=await env.DB.prepare('SELECT state,delivery_state,revision,expires_at,delivery_attempts,message_id FROM drafts WHERE id=?').bind(id).first<{state:string;delivery_state:string;revision:number;expires_at:number;delivery_attempts:number;message_id:number|null}>();
 if(!row)return 'blocked';if(row.delivery_state==='sent')return 'sent';
 if(row.state!=='pending'||row.expires_at<=Date.now()/1000||row.delivery_attempts>=3)return 'blocked';
 if(['waiting','sending'].includes(row.delivery_state))return 'queued';
 if(!['uncertain','failed'].includes(row.delivery_state))return 'blocked';
 const target=await deliveryTarget(env,id,row.message_id);
 if(row.delivery_state==='uncertain'&&!target&&confirmedRevision!==row.revision)return 'confirm';
 const result=await env.DB.prepare("UPDATE drafts SET delivery_state='waiting',lease_until=0,next_delivery=0 WHERE id=? AND revision=? AND state='pending' AND delivery_state=? AND delivery_attempts<3").bind(id,row.revision,row.delivery_state).run();
 return result.meta.changes?'queued':'blocked';
}
