// Explicit operator recovery, bounded to one retry per job/version. No AI or network calls.
import {homedir} from 'node:os';
import {readFile} from 'node:fs/promises';
import {localDatabase} from '../src/local-adapters';
import {KapStore} from '../src/kap/store';
import {decide} from '../src/kap/rules';
import {withKapTableEvidence} from '../src/kap-table-evidence';
import {sha256} from '../src/utils/text';
import type {Disclosure} from '../src/kap/parser';
const root=homedir()+'/Library/Application Support/sector-haber';
const db=await localDatabase(root+'/sector-haber.sqlite',await readFile('migrations/0001_sector.sql','utf8'));
const kap=new KapStore(root+'/kap/kap.sqlite'),apply=process.argv.includes('--apply');
const counts={retry:0,filtered:0,unchanged:0,upgraded_queued:0};
try{
 for(const row of kap.rows<{id:string;metadata:string;job_id:string}>(`SELECT q.id,d.metadata,m.job_id FROM queue q JOIN queue_members qm ON qm.queue_id=q.id JOIN disclosures d ON d.id=qm.disclosure_id JOIN kap_model_jobs m ON m.queue_id=q.id WHERE q.state IN ('needs_review','model_queued')`)){
  const job=await db.prepare('SELECT state,error,documents,created_at,result_draft FROM model_jobs WHERE id=?').bind(row.job_id).first<{state:string;error:string;documents:string;created_at:number;result_draft:string|null}>();
  if(!job||job.result_draft||!['needs_review','queued'].includes(job.state)||job.created_at<Date.now()/1000-86400){counts.unchanged++;continue;}
  if(decide(JSON.parse(row.metadata) as Disclosure,kap.prefs(),null).action!=='instant'){
   counts.filtered++;if(apply){await db.prepare("UPDATE model_jobs SET state='paused' WHERE id=? AND state IN ('needs_review','queued')").bind(row.job_id).run();kap.run("UPDATE queue SET state='suppressed' WHERE id=?",row.id);}continue;
  }
  const key='kap-practical-retry-v2:'+row.job_id;
  if(job.state==='needs_review'&&(!['unsupported_number_or_unit','claim_number_mismatch','subscription_turn_failed','missing_market_hashtags','invented_evidence'].includes(job.error)||await db.prepare('SELECT value FROM system_state WHERE key=?').bind(key).first())){counts.unchanged++;continue;}
  const docs=JSON.parse(job.documents);if(!docs.length||docs.some((d:{body?:string;passages?:unknown[];coverage?:{complete:boolean}})=>!d.body?.trim()||!d.passages?.length||d.coverage&&!d.coverage.complete)){counts.unchanged++;continue;}
  const input=JSON.stringify(withKapTableEvidence(docs));if(input.length>3_500_000){counts.unchanged++;continue;}
  counts[job.state==='queued'?'upgraded_queued':'retry']++;
  if(apply){
   await db.batch([
    db.prepare("UPDATE model_jobs SET state=?,documents=?,input_hash=?,error=NULL WHERE id=? AND state=?").bind(job.state==='queued'?'queued':'retry_pending',input,await sha256(input),row.job_id,job.state),
    db.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind(key,JSON.stringify({at:new Date().toISOString(),previous_error:job.error}))
   ]);
   kap.run("UPDATE queue SET state='model_queued' WHERE id=?",row.id);
  }
 }
 console.log(JSON.stringify({apply,...counts}));
}finally{kap.close();}
