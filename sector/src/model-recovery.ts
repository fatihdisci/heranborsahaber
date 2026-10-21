import type {Env,Document} from './types';
import {quota} from './pipeline';
const RETRYABLE=new Set(['semantic_review_failed','unsupported_number_or_unit','claim_number_mismatch','invented_evidence','missing_market_hashtags','missing_evidence','unsupported_entity','incomplete_draft','subscription_turn_failed','hermes_job_failed','JSONDecodeError','lease_expired','repair_budget_expired']);
export async function recordModelReview(env:Env,id:string,audit:unknown,time=Math.floor(Date.now()/1000)){
 const a=audit as {issues?:unknown};
 const issues=Array.isArray(a?.issues)?a.issues.filter((i):i is string=>typeof i==='string').slice(0,20).map(i=>i.slice(0,4500)):[];
 await env.DB.prepare('INSERT INTO model_reviews(job_id,issues,next_retry,updated_at) VALUES(?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET issues=excluded.issues,next_retry=MAX(model_reviews.next_retry,excluded.next_retry),updated_at=excluded.updated_at').bind(id,JSON.stringify(issues),time+30,time).run();
}
export async function previousModelIssues(env:Env,id:string):Promise<string[]>{
 const r=await env.DB.prepare('SELECT issues FROM model_reviews WHERE job_id=?').bind(id).first<{issues:string}>();
 return r?JSON.parse(r.issues):[];
}
export async function retryKapModel(env:Env,id:string,time=Math.floor(Date.now()/1000)):Promise<boolean>{
 const job=await env.DB.prepare("SELECT documents,error FROM model_jobs WHERE id=? AND kind='kap' AND state='needs_review' AND result_draft IS NULL AND created_at>?").bind(id,time-86400).first<{documents:string;error:string}>();
 if(!job||!RETRYABLE.has(job.error))return false;
 const docs=JSON.parse(job.documents) as Document[];
 if(!docs.length||docs.some(d=>!d.body?.trim()||!d.passages?.length||d.coverage&&!d.coverage.complete))return false;
 await env.DB.prepare('INSERT OR IGNORE INTO model_reviews(job_id,updated_at) VALUES(?,?)').bind(id,time).run();
 const review=await env.DB.prepare('SELECT retries,next_retry FROM model_reviews WHERE job_id=?').bind(id).first<{retries:number;next_retry:number}>();
 if(!review||review.retries>=2||review.next_retry>time||!await quota(env,'kap-ai-budget'))return false;
 const results=await env.DB.batch([
  env.DB.prepare("UPDATE model_jobs SET state='retry_pending',lease_until=0,lease_token=NULL WHERE id=? AND state='needs_review' AND result_draft IS NULL AND EXISTS(SELECT 1 FROM model_reviews r WHERE r.job_id=model_jobs.id AND r.retries<2 AND r.next_retry<=?)").bind(id,time),
  env.DB.prepare("UPDATE model_reviews SET retries=retries+1,next_retry=?,updated_at=? WHERE job_id=? AND retries<2 AND next_retry<=? AND EXISTS(SELECT 1 FROM model_jobs j WHERE j.id=model_reviews.job_id AND j.state='retry_pending')").bind(time+300,time,id,time)
 ]);
 return !!results[0].meta.changes;
}
