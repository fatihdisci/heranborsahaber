import {draftCard} from './card';
import {sha256} from './utils/text';
import {postText} from './editorial';
import type {Env,Document,Draft} from './types';
// Deterministic reports use the existing delivery/retry ledger, without a model
// lease or an additional Telegram sender.
export async function saveReport(env:Env,row:{update_id:number;message_id:number},result:{draft:Draft;documents:Document[]}){
 if(!env.RENDER_REPORT)throw Error('kap_report_renderer_unavailable');
 if(postText(result.draft).length>1024)throw Error('kap_report_caption_limit');
 const id=await sha256('kap-report:'+row.update_id),media=`drafts/${id}/1.png`,time=Math.floor(Date.now()/1000),doc=result.documents[0];
 if(!await env.DB.prepare('SELECT id FROM drafts WHERE id=?').bind(id).first()){
  await env.MEDIA.put(media,await env.RENDER_REPORT(draftCard(result.draft)),{httpMetadata:{contentType:'image/png'}});
  await env.DB.batch([
   env.DB.prepare('INSERT OR IGNORE INTO sources(id,config,enabled) VALUES(?,?,0)').bind(doc.source_id,JSON.stringify({id:doc.source_id,name:doc.source_name,method:'reference'})),
   env.DB.prepare("INSERT OR IGNORE INTO articles(id,source_id,url,title,summary,published_at,first_seen,status) VALUES(?,?,?,?,?,?,?,'prepared')").bind(id,doc.source_id,doc.url+'-'+row.update_id,doc.title,'',doc.published_at,time),
   env.DB.prepare("INSERT OR IGNORE INTO drafts(id,event_key,fingerprint,content,documents,verification,state,created_at,expires_at,media_key) VALUES(?,?,?,?,?,?,'pending',?,?,?)").bind(id,id,id,JSON.stringify(result.draft),JSON.stringify(result.documents),'verified',time,time+86400,media),
   env.DB.prepare("INSERT OR IGNORE INTO model_jobs(id,article_id,documents,input_hash,created_at,kind,state,result_draft) VALUES(?,?,?,?,?,'manual','complete',?)").bind(id,id,JSON.stringify(result.documents),id,time,id),
   env.DB.prepare("UPDATE manual_requests SET state='model_queued',job_id=?,lease_until=0,error=NULL WHERE update_id=?").bind(id,row.update_id)
  ]);
 }else await env.DB.prepare("UPDATE manual_requests SET state='model_queued',job_id=?,lease_until=0,error=NULL WHERE update_id=?").bind(id,row.update_id).run();
}
