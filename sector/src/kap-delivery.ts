// KAP -> complete evidence -> shared audited model -> existing single-photo sender.
// No metadata-only messages. Collector and external delivery remain independent.
import {KapStore} from './kap/store';
import {decide} from './kap/rules';
import type {Disclosure,Indices} from './kap/parser';
import {enqueueEvidence} from './ingest';
import {quota} from './pipeline';
import {retryKapModel} from './model-recovery';
import type {Document,Env} from './types';
export class KapDelivery {
 constructor(private store:KapStore,private env:Env,private load:(id:number)=>Promise<Document[]>,private clock=Date.now){
  store.db.exec(`CREATE TABLE IF NOT EXISTS kap_model_jobs(queue_id TEXT PRIMARY KEY REFERENCES queue(id),job_id TEXT,attempts INTEGER NOT NULL DEFAULT 0,lease_until INTEGER NOT NULL DEFAULT 0,last_error TEXT,message_id INTEGER);`);
 }
 private allowed(d:Disclosure){return decide(d,this.store.prefs(),this.store.get<Indices>('indices')).action==='instant';}
 async run():Promise<{state:string;id?:string}> {
  if(this.env.MODE!=='telegram_review')return {state:'disabled'};
  const s=this.store,now=this.clock();s.set('telegram_delivery',{enabled:true,heartbeatAt:now});
  // A completed AI job is not a delivery receipt. Wait for the photo sender.
  for(const pending of s.rows<{queue_id:string;job_id:string}>("SELECT m.queue_id,m.job_id FROM kap_model_jobs m JOIN queue q ON q.id=m.queue_id WHERE q.state IN ('model_queued','needs_review')")){
   const job=await this.env.DB.prepare('SELECT state,error,result_draft FROM model_jobs WHERE id=?').bind(pending.job_id).first<{state:string;error:string|null;result_draft:string|null}>();
   const draft=job?.result_draft?await this.env.DB.prepare('SELECT state,delivery_state,delivered_at,message_id FROM drafts WHERE id=?').bind(job.result_draft).first<{state:string;delivery_state:string;delivered_at:number;message_id:number}>():null;
   if(draft?.delivery_state==='sent'){s.transaction(()=>{s.run("UPDATE queue SET state='sent',sent_at=? WHERE id=?",draft.delivered_at*1000,pending.queue_id);s.run('UPDATE kap_model_jobs SET message_id=?,last_error=NULL WHERE queue_id=?',draft.message_id,pending.queue_id);});}
   else if(job&&['queued','leased','retry_pending'].includes(job.state))s.run("UPDATE queue SET state='model_queued' WHERE id=?",pending.queue_id);
   else if(job?.state==='needs_review'||job?.state==='expired'||draft?.state==='needs_review'||draft?.delivery_state==='uncertain'){s.run("UPDATE queue SET state='needs_review' WHERE id=?",pending.queue_id);s.run('UPDATE kap_model_jobs SET last_error=? WHERE queue_id=?',job?.error??'draft_review_required',pending.queue_id);}
  }
  const waiting=await this.env.DB.prepare("SELECT COUNT(*) AS n FROM model_jobs WHERE state IN ('queued','leased','retry_pending') AND kind='kap'").first<{n:number}>();
  const total=await this.env.DB.prepare("SELECT COUNT(*) AS n FROM model_jobs WHERE state IN ('queued','leased','retry_pending')").first<{n:number}>();
  if((waiting?.n??0)>=2||(total?.n??0)>=4)return {state:'model_busy'};
  const row=s.transaction(()=>{
   s.run("UPDATE queue SET state='ready' WHERE state='preparing' AND id IN (SELECT queue_id FROM kap_model_jobs WHERE lease_until<?)",now);
   for(let i=0;i<100;i++){
    const r=s.row<{id:string;metadata:string}>(`SELECT q.id,d.metadata FROM queue q JOIN queue_members m ON m.queue_id=q.id JOIN disclosures d ON d.id=m.disclosure_id WHERE q.kind='instant' AND q.state='ready' AND q.available_at<=? AND d.silent=0 ORDER BY d.published_at DESC,q.id LIMIT 1`,now);
    if(!r)return null;const d=JSON.parse(r.metadata) as Disclosure;
    if(!this.allowed(d)){s.run("UPDATE queue SET state='suppressed' WHERE id=?",r.id);continue;}
    s.run("UPDATE queue SET state='preparing' WHERE id=?",r.id);
    s.run('INSERT INTO kap_model_jobs(queue_id,attempts,lease_until) VALUES(?,1,?) ON CONFLICT(queue_id) DO UPDATE SET attempts=attempts+1,lease_until=excluded.lease_until',r.id,now+300_000);
    return {...r,disclosure:d};
   }return null;
  });
  if(!row){
   // Fresh notifications above always win. Retry only source-complete model
   // failures, never a completed draft or an ambiguous Telegram delivery.
   for(const r of s.rows<{id:string;metadata:string;job_id:string}>("SELECT q.id,d.metadata,m.job_id FROM queue q JOIN queue_members qm ON qm.queue_id=q.id JOIN disclosures d ON d.id=qm.disclosure_id JOIN kap_model_jobs m ON m.queue_id=q.id WHERE q.state='needs_review' AND d.silent=0 ORDER BY d.published_at DESC")){
    if(!this.allowed(JSON.parse(r.metadata))){s.run("UPDATE queue SET state='suppressed' WHERE id=?",r.id);continue;}
    if(await retryKapModel(this.env,r.job_id,Math.floor(now/1000))){s.run("UPDATE queue SET state='model_queued' WHERE id=?",r.id);return {state:'model_retry_queued',id:r.id};}
   }
   return {state:s.row<{n:number}>("SELECT COUNT(*) n FROM queue WHERE state='needs_review'")!.n?'needs_review':'idle'};
  }
  try{
   const docs=await this.load(row.disclosure.id);
   if(!this.allowed(row.disclosure)){s.run("UPDATE queue SET state='suppressed' WHERE id=?",row.id);return {state:'suppressed',id:row.id};}
   if(!await quota(this.env,'kap-ai-budget')){s.run("UPDATE queue SET state='ready',available_at=? WHERE id=?",now+1800_000,row.id);return {state:'budget_wait',id:row.id};}
   const jobId=await enqueueEvidence(this.env,docs,'kap');
   s.transaction(()=>{s.run('UPDATE kap_model_jobs SET job_id=?,lease_until=0,last_error=NULL WHERE queue_id=?',jobId,row.id);s.run("UPDATE queue SET state='model_queued' WHERE id=?",row.id);});
   return {state:'model_queued',id:row.id};
  }catch(e){
   const attempts=s.row<{attempts:number}>('SELECT attempts FROM kap_model_jobs WHERE queue_id=?',row.id)!.attempts;
   const error=e instanceof Error&&/^[a-z_]{3,70}$/.test(e.message)?e.message:'kap_evidence_failed';
   s.transaction(()=>{s.run("UPDATE queue SET state=?,available_at=? WHERE id=?",attempts<3?'ready':'needs_review',now+Math.min(300_000,30_000*2**attempts),row.id);s.run('UPDATE kap_model_jobs SET lease_until=0,last_error=? WHERE queue_id=?',error,row.id);});
   return {state:'evidence_failed',id:row.id};
  }
 }
}
