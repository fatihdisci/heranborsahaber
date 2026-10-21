import type {Document,Env} from './types';
import {sha256} from './utils/text';
// Trusted local readers only. This is not an endpoint accepting arbitrary evidence.
export async function enqueueEvidence(env:Env,documents:Document[],kind:'kap'|'manual'):Promise<string> {
 if(!documents.length||documents.some(d=>!d.body?.trim()||!d.passages?.length||d.coverage&&!d.coverage.complete))throw Error('incomplete_source_evidence');
 const input=JSON.stringify(documents);if(input.length>3_500_000)throw Error('source_evidence_limit');
 const doc=documents[0],id=await sha256(doc.url),time=Math.floor(Date.now()/1000),jobId=await sha256('evidence:'+id);
 await env.DB.batch([
  env.DB.prepare('INSERT OR IGNORE INTO sources(id,config,enabled) VALUES(?,?,0)').bind(doc.source_id,JSON.stringify({id:doc.source_id,name:doc.source_name,method:'reference'})),
  env.DB.prepare('INSERT OR IGNORE INTO articles(id,source_id,url,title,summary,published_at,first_seen,status) VALUES(?,?,?,?,?,?,?,?)').bind(id,doc.source_id,doc.url,doc.title,'',doc.published_at??new Date().toISOString(),time,'model_queued'),
  env.DB.prepare('UPDATE articles SET status=\'model_queued\',lease_until=0 WHERE id=? AND status=\'queued\'').bind(id),
  env.DB.prepare('INSERT OR IGNORE INTO model_jobs(id,article_id,documents,input_hash,created_at,kind) VALUES(?,?,?,?,?,?)').bind(jobId,id,input,await sha256(input),time,kind)
 ]);
 const job=await env.DB.prepare('SELECT id FROM model_jobs WHERE article_id=? AND expected_revision=0').bind(id).first<{id:string}>();if(!job)throw Error('evidence_job_missing');return job.id;
}
