import {chooseLayout,savedLayout} from './card-layout';
import {withKapUnitEvidence} from './kap-unit-evidence';
import {chooseTheme,savedTheme,legacyTheme} from './card-theme';
import {editorialPolicy} from './style';
import {DRAFT_SCHEMA,EDITOR_PROMPT,topicScore,MIN_DRAFT_IMPORTANCE} from './editorial';
import {AUDIT_PROMPT,acceptHermes} from './ai';
import {eventIdentity,sameEvent} from './dedupe';
import {draftCard} from './card';
import {sha256} from './utils/text';
import type {Env,Document,Draft} from './types';
import {readDocument} from './article';
import registry from '../sources.json';
import type {Source} from './types';
import {readPublic,safeUrl} from './network';
type Job={id:string;article_id:string;documents:string;related_ids:string;input_hash:string;lease_token:string;lease_until:number;state:string;kind:string;draft_id:string|null;expected_revision:number;edit_request:string|null;result_draft:string|null;};
const now=()=>Math.floor(Date.now()/1000);
export async function ingestOfficial(env:Env,input:Record<string,unknown>):Promise<{accepted:boolean}> {
 const doc=input.document as Document,source=(registry as Source[]).find(s=>s.id===doc?.source_id&&s.method==='bridge_pdf');
 if(!source||source.id!=='spk'||!/^https:\/\/(?:www\.)?spk\.gov\.tr\/data\/[a-f\d]+\/20\d{2}-\d+\.pdf$/.test(doc.url)||typeof doc.body!=='string'||doc.body.length<80||doc.body.length>120_000||!Array.isArray(doc.passages)||doc.passages.some(p=>typeof p.id!=='string'||typeof p.text!=='string')||!doc.published_at||!Number.isFinite(Date.parse(doc.published_at))||Date.parse(doc.published_at)>Date.now()+300_000||Date.now()-Date.parse(doc.published_at)>48*3600_000)throw new Error('invalid_official_document');
 safeUrl(doc.url,source.allowed_hosts);
 const pdf=await readPublic(doc.url,source.allowed_hosts,{Accept:'application/pdf'},fetch,true);
 const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',pdf.bytes! as BufferSource))].map(n=>n.toString(16).padStart(2,'0')).join('');
 if(input.pdf_hash!==actual)throw new Error('official_document_changed');
 const id=await sha256(doc.url),document=JSON.stringify({...doc,source_name:'SPK',family:'spk',official:true});
 await env.DB.batch([
  env.DB.prepare('INSERT OR IGNORE INTO articles(id,source_id,url,title,summary,published_at,first_seen,status) VALUES(?,?,?,?,?,?,?,?)').bind(id,'spk',doc.url,doc.title,'',doc.published_at,now(),'queued'),
  env.DB.prepare('UPDATE articles SET document=?,document_expires=?,summary=? WHERE id=?').bind(document,now()+7*24*3600,doc.passages[0]?.text.slice(0,700)??'',id),
  env.DB.prepare('UPDATE sources SET last_ok=?,last_error=NULL WHERE id=?').bind(now(),'spk')]);
 return {accepted:true};
}
export async function leaseJob(env:Env) {
 // Ambiguous jobs expire into review, rather than replaying model calls.
 await env.DB.prepare("UPDATE model_jobs SET state='needs_review',error='lease_expired' WHERE state='leased' AND lease_until<?").bind(now()).run();
 const job=await env.DB.prepare("SELECT * FROM model_jobs WHERE state IN ('queued','retry_pending') AND created_at>? AND (kind NOT IN ('initial','news') OR EXISTS (SELECT 1 FROM news_cards c WHERE c.article_id=model_jobs.article_id AND c.state='model_queued')) ORDER BY CASE WHEN state='retry_pending' THEN 1 ELSE 0 END,CASE WHEN kind IN ('news','edit','manual') THEN 0 ELSE 1 END,created_at LIMIT 1").bind(now()-24*3600).first<Job>();if(!job)return null;
 const token=crypto.randomUUID();
 const lock=await env.DB.prepare("UPDATE model_jobs SET state='leased',lease_token=?,lease_until=? WHERE id=? AND state IN ('queued','retry_pending')").bind(token,now()+600,job.id).run();if(!lock.meta.changes)return null;
 const normalized=JSON.stringify(withKapUnitEvidence(JSON.parse(job.documents)));
 if(normalized!==job.documents){job.documents=normalized;job.input_hash=await sha256(normalized);await env.DB.prepare('UPDATE model_jobs SET documents=?,input_hash=? WHERE id=? AND lease_token=?').bind(normalized,job.input_hash,job.id,token).run();}
 const editing=job.kind==='edit'?await env.DB.prepare('SELECT content FROM drafts WHERE id=?').bind(job.draft_id).first<{content:string}>():null;
 const theme=editing?(await savedTheme(env,'draft:'+job.draft_id)??legacyTheme((JSON.parse(editing.content) as Draft).template)):await chooseTheme(env,job.article_id);
 const layout=editing?(await savedLayout(env,'draft:'+job.draft_id)??'editorial'):await chooseLayout(env,job.article_id);
 const previous=await env.DB.prepare('SELECT id,content FROM drafts WHERE created_at>? ORDER BY created_at DESC LIMIT 40').bind(now()-48*3600).all<{id:string;content:string}>();
 const existing_events=(previous.results??[]).map(r=>{const d=JSON.parse(r.content) as Draft;return {id:r.id,headline:d.headline,event_key:d.event_key,entities:d.entities};});
 return {id:job.id,card_theme:theme,card_layout:layout,lease_token:token,input_hash:job.input_hash,deadline:now()+600,model:env.AI_MODEL,effort:env.AI_EFFORT,provider:'openai-codex',allowed_tools:[],documents:JSON.parse(job.documents),editorial_policy:editorialPolicy(JSON.parse(job.documents)),existing_events,edit_request:job.edit_request,prompt:EDITOR_PROMPT,schema:DRAFT_SCHEMA,audit_prompt:AUDIT_PROMPT};
}
export async function enqueueEdit(env:Env,id:string,revision:number,request:string):Promise<void> {
 if(!request.trim()||request.length>12_000)throw new Error('invalid_edit_request');
 const row=await env.DB.prepare("SELECT * FROM drafts WHERE id=? AND revision=? AND state='pending' AND expires_at>?").bind(id,revision,now()).first<{documents:string}>();if(!row)throw new Error('stale_edit');
 const article=await env.DB.prepare('SELECT * FROM articles WHERE draft_id=? ORDER BY first_seen LIMIT 1').bind(id).first<{id:string;source_id:string;url:string;title:string;summary:string;published_at:string}>();if(!article)throw new Error('edit_source_missing');
 const stored=JSON.parse(row.documents) as Document[];
 const localEvidence=stored[0]?.source_id==='kap'||stored[0]?.source_id==='manual-input';
 const source=(registry as Source[]).find(s=>s.id===article.source_id);
 if(!localEvidence&&!source)throw new Error('edit_source_missing');
 const documents=localEvidence?stored:[await readDocument(article,source!)];
 if(documents.some(d=>!d.body||!d.passages.length))throw new Error('edit_source_incomplete');
 const input=JSON.stringify(documents);
 await env.DB.prepare("INSERT INTO model_jobs(id,article_id,documents,input_hash,created_at,kind,draft_id,expected_revision,edit_request) VALUES(?,?,?,?,?,'edit',?,?,?)").bind(crypto.randomUUID(),article.id,input,await sha256(input),now(),id,revision,request).run();
}
export function pngBytes(base64:unknown):Uint8Array {
 if(typeof base64!=='string'||base64.length>6_000_000)throw new Error('invalid_card_image');
 const b=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));
 const signature=[137,80,78,71,13,10,26,10];if(!signature.every((n,i)=>b[i]===n)||b.length<1000)throw new Error('invalid_png');
 const view=new DataView(b.buffer);if(view.getUint32(16)!==1080||view.getUint32(20)!==1350)throw new Error('invalid_card_dimensions');
 return b;
}
export async function submitJob(env:Env,input:Record<string,unknown>):Promise<{id:string;duplicate:boolean}> {
 const job=await env.DB.prepare('SELECT * FROM model_jobs WHERE id=?').bind(String(input.id)).first<Job>();
 if(!job||input.lease_token!==job.lease_token||input.input_hash!==job.input_hash)throw new Error('invalid_job_lease');
 if(job.state==='complete')return {id:job.result_draft??job.id,duplicate:true};
 if(job.lease_until<now())throw new Error('invalid_job_lease');
 if(job.state!=='leased')throw new Error('invalid_job_state');
 const meta=input.runtime as {model?:string;effort?:string;provider?:string;tool_count?:number;fallback_count?:number};
 if(!meta||meta.model!==env.AI_MODEL||meta.effort!==env.AI_EFFORT||meta.provider!=='openai-codex'||meta.tool_count!==0||meta.fallback_count!==0)throw new Error('model_route_mismatch');
 const documents=JSON.parse(job.documents) as Document[];
 const checked=acceptHermes(input.draft,input.audit,documents),draft=checked.draft;
 draft.importance=Math.min(draft.importance,topicScore(documents[0].title,documents[0].body,documents[0].official).score+10);
 const existingCard=job.kind==='edit'?await env.DB.prepare('SELECT content FROM drafts WHERE id=?').bind(job.draft_id).first<{content:string}>():null;
 const theme=existingCard?(await savedTheme(env,'draft:'+job.draft_id)??legacyTheme((JSON.parse(existingCard.content) as Draft).template)):(await savedTheme(env,job.article_id)??legacyTheme(draft.template));
 const layout=await savedLayout(env,job.kind==='edit'?'draft:'+job.draft_id:job.article_id)??'editorial';
 const svg=draftCard(draft,documents.map(d=>d.source_name),String(input.card_date),true,theme,layout);
 if(input.svg_hash!==await sha256(svg))throw new Error('card_content_mismatch');
 const image=pngBytes(input.png_base64),time=now();
 if(job.kind==='edit') {
  const current=await env.DB.prepare("SELECT revision FROM drafts WHERE id=? AND state='pending'").bind(job.draft_id).first<{revision:number}>();
  if(!current||current.revision!==job.expected_revision)throw new Error('stale_edit');
  const revision=current.revision+1,media=`drafts/${job.draft_id}/${revision}.png`;
  await env.MEDIA.put(media,image,{httpMetadata:{contentType:'image/png'}});
  const result=await env.DB.batch([
   env.DB.prepare("UPDATE drafts SET content=?,documents=?,verification=?,revision=?,delivery_state='waiting',message_id=NULL,media_key=? WHERE id=? AND revision=? AND state='pending'").bind(JSON.stringify(draft),JSON.stringify(documents),checked.verification,revision,media,job.draft_id,job.expected_revision),
   env.DB.prepare("UPDATE model_jobs SET state='complete',documents='[]',result_draft=? WHERE id=?").bind(job.draft_id,job.id),
   env.DB.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind('card_theme:draft:'+job.draft_id,theme),
   env.DB.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind('card_layout:draft:'+job.draft_id,layout)
  ]);
  if(!result[0].meta.changes){await env.MEDIA.delete(media);throw new Error('stale_edit');}
  return {id:job.draft_id!,duplicate:false};
 }
 const recent=await env.DB.prepare('SELECT id,content FROM drafts WHERE created_at>? LIMIT 200').bind(time-48*3600).all<{id:string;content:string}>();
 const duplicate=documents[0].source_id==='kap'?undefined:(recent.results??[]).find(r=>sameEvent(draft,JSON.parse(r.content)));
 if(duplicate){await env.DB.batch([
  env.DB.prepare("UPDATE model_jobs SET state='complete',result_draft=? WHERE id=?").bind(duplicate.id,job.id),
  env.DB.prepare("UPDATE articles SET status='duplicate',draft_id=? WHERE id=?").bind(duplicate.id,job.article_id)]);return {id:duplicate.id,duplicate:true};}
 const id=crypto.randomUUID(),key=documents[0].source_id==='kap'?await sha256(documents[0].url):await eventIdentity(draft,documents),media=`drafts/${id}/1.png`;
 await env.MEDIA.put(media,image,{httpMetadata:{contentType:'image/png'}});
 const cited=documents[0].source_id==='kap'||documents[0].source_id==='manual-input'?documents:documents.map((d,i)=>({...d,body:'',passages:d.passages.filter(p=>draft.claims.some(c=>c.evidence.some(e=>e.document===i&&e.passage===p.id)))}));
 try {await env.DB.batch([
  env.DB.prepare('INSERT INTO drafts(id,event_key,fingerprint,content,documents,verification,state,created_at,expires_at,media_key) VALUES(?,?,?,?,?,?,?,?,?,?)').bind(id,key,await sha256(draft.headline+'\n'+draft.body),JSON.stringify(draft),JSON.stringify(cited),checked.verification,checked.verification==='needs_review'||job.kind==='initial'&&draft.importance<MIN_DRAFT_IMPORTANCE?'needs_review':'pending',time,time+24*3600,media),
  env.DB.prepare("UPDATE model_jobs SET state='complete',result_draft=?,documents='[]' WHERE id=? AND state='leased'").bind(id,job.id),
  env.DB.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind('card_theme:draft:'+id,theme),
  env.DB.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind('card_layout:draft:'+id,layout),
  env.DB.prepare("UPDATE articles SET status='prepared',draft_id=? WHERE id=?").bind(id,job.article_id),
  ...(JSON.parse(job.related_ids) as string[]).map(other=>env.DB.prepare("UPDATE articles SET status='duplicate',draft_id=? WHERE id=? AND status='queued'").bind(id,other))
 ]);}catch(e){await env.MEDIA.delete(media);throw e;}
 return {id,duplicate:false};
}
