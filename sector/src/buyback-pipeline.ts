import {parseFeed} from './feed';
import {readPublic} from './network';
import {buybackSource,BUYBACK_HOST,reportImage,validateTable,buybackDraft,buybackSelectionEvidence} from './is-buyback';
import {draftCard} from './card';
import {sha256} from './utils/text';
import {kapIndexMembership} from './kap/index-tags';
import type {Indices} from './kap/parser';
import type {Env} from './types';
import type {BuybackEvidence} from './buyback-types';
export interface BuybackIO {readImage:(bytes:Uint8Array)=>Promise<unknown>;indices:()=>Promise<Indices|null>;fetcher?:typeof fetch;now?:()=>number;}
export async function pollBuybacks(env:Env,io:BuybackIO){
 const at=(io.now??Date.now)(),now=Math.floor(at/1000),fetcher=io.fetcher??fetch;
 const feed=await readPublic(buybackSource.url,[BUYBACK_HOST],{},fetcher);
 const items=parseFeed(feed.text,buybackSource).filter(i=>i.published_at&&Date.parse(i.published_at)<=at+300000&&Date.parse(i.published_at)>=at-48*3600000).sort((a,b)=>Date.parse(b.published_at!)-Date.parse(a.published_at!));
 // A first installation establishes a boundary, not a historical backfill.
 await env.DB.prepare("INSERT OR IGNORE INTO system_state(key,value) VALUES('buyback_discovery_since',?)").bind(String(at)).run();
 const boundary=Number((await env.DB.prepare("SELECT value FROM system_state WHERE key='buyback_discovery_since'").first<{value:string}>())?.value);
 if(!Number.isSafeInteger(boundary)||boundary<0)throw Error('buyback_discovery_boundary_invalid');
 const item=items[0];if(!item)return {state:'no_new_report'};
 if(Date.parse(item.published_at!)<boundary&&!await env.DB.prepare('SELECT 1 FROM buyback_reports WHERE url=? LIMIT 1').bind(item.url).first())return {state:'before_activation'};
 const page=await readPublic(item.url,[BUYBACK_HOST],{},fetcher),imageUrl=reportImage(page.text,page.url),image=await readPublic(imageUrl,[BUYBACK_HOST],{},fetcher,true);
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',image.bytes! as BufferSource)),b=>b.toString(16).padStart(2,'0')).join(''),id=await sha256(item.url+':'+hash);
 const previous=await env.DB.prepare('SELECT state,lease_until FROM buyback_reports WHERE id=?').bind(id).first<{state:string;lease_until:number}>();
 if(previous&&!(previous.state==='reading'&&previous.lease_until<now))return {state:previous.state,id};
 const claim=await env.DB.prepare(`INSERT INTO buyback_reports(id,url,image_url,image_hash,published_at,state,created_at,lease_until) VALUES(?,?,?,?,?,'reading',?,?) ON CONFLICT(id) DO UPDATE SET lease_until=excluded.lease_until WHERE state='reading' AND lease_until<?`).bind(id,item.url,imageUrl,hash,item.published_at,now,now+300,now).run();
 if(!claim.meta.changes)return {state:'busy'};
 try{
  const table=validateTable(await io.readImage(image.bytes!),item.published_at!);
  const semantic=await sha256(JSON.stringify({day:table.day,rows:table.rows.map(r=>[r.ticker,r.day,r.nominal,r.price,r.amount])}));
  // Never produce a second daily product alongside a pre-existing legacy report.
  const legacy=await env.DB.prepare(`SELECT id FROM drafts WHERE json_extract(content,'$.card_data.report.general.day')=? OR (json_extract(content,'$.event_key') LIKE 'buyback-%' AND CAST(substr(json_extract(content,'$.event_key'),9) AS INTEGER) BETWEEN ? AND ?) LIMIT 1`).bind(table.day,Date.parse(table.day+'T00:00:00+03:00'),Date.parse(table.day+'T23:59:59+03:00')).first<{id:string}>();
  if(legacy)await env.DB.prepare("INSERT OR IGNORE INTO buyback_days VALUES(?,'kap',?,'legacy')").bind(table.day,legacy.id).run();
  const day=await env.DB.prepare('SELECT * FROM buyback_days WHERE day=?').bind(table.day).first<{producer:string;draft_id:string;version:string}>();
  const indices=await io.indices(),membership=kapIndexMembership(table.rows.map(r=>r.ticker),indices,at);
  const originalKey=`evidence/buyback/${hash}.image`;await env.MEDIA.put(originalKey,image.bytes!,{httpMetadata:{contentType:image.headers.get('content-type')??'application/octet-stream'}});
  const evidence:BuybackEvidence={selection:await buybackSelectionEvidence(table,indices,at),original_key:originalKey,report_url:item.url,image_url:imageUrl,image_hash:hash,published_at:item.published_at!,version:semantic,index_checked_at:membership?.checked_at??null,index_source:membership?.source??null,reader:table.reader,raw_rows:table.rows};
  await env.DB.prepare('UPDATE buyback_reports SET day=?,semantic_hash=?,evidence=? WHERE id=?').bind(table.day,semantic,JSON.stringify(evidence),id).run();
  const finish=async(state:string,result:string|null=null,error:string|null=null)=>{await env.DB.prepare('UPDATE buyback_reports SET state=?,result_draft=?,error=?,lease_until=0 WHERE id=?').bind(state,result,error,id).run();return {state,id,draft_id:result,error};};
  if(day?.producer==='kap')return finish('blocked_existing',day.draft_id);
  if(day?.version===semantic)return finish('duplicate',day.draft_id);
  if(day&&await env.DB.prepare("SELECT 1 FROM drafts WHERE id=? AND delivery_state IN ('sending','uncertain') UNION ALL SELECT 1 FROM x_posts WHERE draft_id=? AND state IN ('queued','uploading','posting','uncertain') LIMIT 1").bind(day.draft_id,day.draft_id).first())return finish('needs_review',day.draft_id,'existing_delivery_unresolved');
  const result=buybackDraft(table,evidence,indices,at,!!day),draftId=crypto.randomUUID(),media=`drafts/${draftId}/1.png`;
  if(!env.RENDER_REPORT)throw Error('buyback_renderer_unavailable');const bytes=await env.RENDER_REPORT(draftCard(result.draft));
  if(bytes.length>5_000_000)throw Error('buyback_png_capacity_exceeded');
  await env.MEDIA.put(media,bytes,{httpMetadata:{contentType:'image/png'}});
  // Atomic day ownership + immutable report version + ordinary delivery queue.
  const statements=[env.DB.prepare('INSERT INTO buyback_days(day,producer,draft_id,version) VALUES(?,?,?,?) ON CONFLICT(day) DO UPDATE SET draft_id=excluded.draft_id,version=excluded.version WHERE producer=excluded.producer AND version=?').bind(table.day,'is-buyback',draftId,semantic,day?.version??''),
   env.DB.prepare(`INSERT INTO drafts(id,event_key,fingerprint,content,documents,verification,state,created_at,expires_at,media_key) SELECT ?,?,?,?,?,'single_source_attributed','pending',?,?,? WHERE EXISTS(SELECT 1 FROM buyback_days WHERE day=? AND draft_id=?)`).bind(draftId,'daily-buyback:'+table.day+':'+semantic,semantic,JSON.stringify(result.draft),JSON.stringify(result.documents),now,now+86400,media,table.day,draftId),
   env.DB.prepare("UPDATE buyback_reports SET state='ready',result_draft=?,lease_until=0 WHERE id=? AND EXISTS(SELECT 1 FROM drafts WHERE id=?)").bind(draftId,id,draftId)];
  if(day)statements.push(env.DB.prepare("UPDATE drafts SET state='rejected' WHERE id=? AND state='pending' AND EXISTS(SELECT 1 FROM drafts WHERE id=?)").bind(day.draft_id,draftId));
  await env.DB.batch(statements);
  if(!await env.DB.prepare('SELECT id FROM drafts WHERE id=?').bind(draftId).first()){await env.MEDIA.delete(media);return finish('blocked_existing');}
  return {state:day?'correction':'ready',id,draft_id:draftId,rows:table.rows.length};
 }catch(e){const code=e instanceof Error&&/^[a-z_]+$/.test(e.message)?e.message:'buyback_read_failed';await env.DB.prepare("UPDATE buyback_reports SET state='needs_review',error=?,lease_until=0 WHERE id=?").bind(code,id).run();return {state:'needs_review',id,error:code};}
}
