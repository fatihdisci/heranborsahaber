import {DOMParser,parseHTML} from 'linkedom';
import {SaxesParser} from 'saxes';
import {readPublic,safeUrl} from './network';
import {stripHtml,sha256} from './utils/text';
import type {Env,Document} from './types';
export const SPK_X_HOSTS=['nitter.netbub.com','nitter.meowing.monster','nitter.pp.ua'];
export interface SpkPost {id:string;url:string;text:string;at:string;links:string[];images:string[];unsupported:boolean;}
const unique=(a:string[])=>[...new Set(a)];
export function parseSpkPosts(xml:string,account='spkgovtr'):SpkPost[]{
 if(!['spkgovtr','fintables'].includes(account))throw Error('x_account_mismatch');
 if(/<!DOCTYPE|<!ENTITY/i.test(xml))throw Error('x_unsafe_xml');new SaxesParser({xmlns:true}).write(xml).close();
 const root=new DOMParser().parseFromString(xml,'text/xml');
 if(root.documentElement.tagName!=='rss'||!new RegExp('@'+account+'(?:$|[^a-z0-9_])','i').test(root.querySelector('channel > title')?.textContent??''))throw Error('x_account_mismatch');
 const items=[...root.querySelectorAll('item')];if(!items.length)throw Error('x_empty_feed');
 return items.filter(i=>account==='spkgovtr'||new URL(i.querySelector('link')?.textContent??'').pathname.toLowerCase().startsWith('/'+account+'/status/')).map(i=>{
  const url=new URL(i.querySelector('link')?.textContent??''),m=url.pathname.match(new RegExp('^/'+account+'/status/(\\d+)$','i'));
  if(!SPK_X_HOSTS.includes(url.hostname)||!m)throw Error('x_post_identity');
  const raw=i.querySelector('description')?.textContent??'',{document}=parseHTML(raw);
  const at=Date.parse(i.querySelector('pubDate')?.textContent??'');if(!Number.isFinite(at)||at>Date.now()+300000)throw Error('x_post_date');
  const links=unique([...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')!).filter(u=>!/^https?:\/\/(?:x\.com|twitter\.com|nitter\.)[^ ]*\/(?:search|hashtag)\b/.test(u)));
  const images=unique([...document.querySelectorAll('img[src]')].map(a=>{
   const u=new URL(a.getAttribute('src')!,url);u.protocol='https:';
   if(u.hostname==='pbs.twimg.com')return safeUrl(u.href,['pbs.twimg.com']);
   if(SPK_X_HOSTS.includes(u.hostname)){const path=decodeURIComponent(u.pathname.replace(/^\/pic\//,''));if(/^media\/[A-Za-z0-9_-]+\.(jpg|png|webp)$/.test(path))return 'https://pbs.twimg.com/'+path;if(/^card_img\/\d+\/[A-Za-z0-9_-]+\?format=(?:jpg|png|webp)&name=[A-Za-z0-9_x]+$/.test(path))return safeUrl('https://pbs.twimg.com/'+path,['pbs.twimg.com']);}
   throw Error('x_image_host');
  }));
  const text=stripHtml(raw)||stripHtml(i.querySelector('title')?.textContent??'')||(images.length?account+' görsel paylaşımı':'');if(!text.trim())throw Error('x_post_empty');
  return {id:m[1],url:'https://x.com/'+account+'/status/'+m[1],text,at:new Date(at).toISOString(),links,images,unsupported:!!document.querySelector('video,audio,iframe')||/video\.twimg|\/video\//i.test(raw)};
 });
}
export async function fetchSpkPosts(fetcher:typeof fetch=fetch){
 for(const host of SPK_X_HOSTS)try{const r=await readPublic('https://'+host+'/spkgovtr/rss',[host],{},fetcher);return {posts:parseSpkPosts(r.text),host};}catch{/* Each mirror must independently pass identity/XML checks. */}
 throw Error('x_all_mirrors_unavailable');
}
export async function pollSpkX(env:Env,now=Date.now(),load=fetchSpkPosts,sourceId='spk-x',select:(p:SpkPost)=>boolean=()=>true){
 const source=await env.DB.prepare("SELECT enabled FROM sources WHERE id=?").bind(sourceId).first<{enabled:number}>();if(!source?.enabled)return;
 const row=await env.DB.prepare("SELECT value FROM system_state WHERE key=?").bind(sourceId.replace(/-/g,'_')+'_state').first<{value:string}>();
 const state=row?JSON.parse(row.value):null;if(state?.next>now)return;
 try{
  const {posts,host}=await load();const seen=new Set<string>(state?.seen??[]),since=state?.since??now;
  const coverageGap=!!state?.seen?.length&&!posts.some(p=>seen.has(p.id));
  const fresh=state?posts.filter(p=>!seen.has(p.id)&&Date.parse(p.at)>=since&&select(p)):[];
  const inserts=await Promise.all(fresh.map(async p=>env.DB.prepare('INSERT OR IGNORE INTO articles(id,source_id,url,title,summary,published_at,first_seen,document,document_expires) VALUES(?,?,?,?,?,?,?,?,?)').bind(await sha256(p.url),sourceId,p.url,p.text.split('\n')[0].slice(0,220),p.text,p.at,Math.floor(now/1000),JSON.stringify(p),Math.floor(now/1000)+7*86400)));
  await env.DB.batch([...inserts,env.DB.prepare("INSERT INTO system_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(sourceId.replace(/-/g,'_')+'_state',JSON.stringify({since,next:now+600000,seen:unique([...seen,...posts.map(p=>p.id)]).slice(-2000),host,last_ok:now,failures:0,count:posts.length,new_count:fresh.length,coverage_gap:coverageGap}))]);
 }catch{
  await env.DB.prepare("INSERT INTO system_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").bind(sourceId.replace(/-/g,'_')+'_state',JSON.stringify({...state,next:now+600000,failures:(state?.failures??0)+1,error:'x_all_mirrors_unavailable'})).run();
 }
}
export type EvidenceReader=(b:Uint8Array)=>Promise<Pick<Document,'body'|'passages'|'images'|'coverage'>>;
export async function spkPostDocuments(post:SpkPost,pdf:EvidenceReader,image:EvidenceReader,fetcher:typeof fetch=fetch):Promise<Document[]>{
 if(!post||!/^\d+$/.test(post.id)||post.url!=='https://x.com/spkgovtr/status/'+post.id||!Array.isArray(post.links)||!Array.isArray(post.images))throw Error('x_manifest_invalid');
 if(post.unsupported)throw Error('x_video_requires_review');
 if(post.links.length>6||post.images.length>4)throw Error('x_attachment_limit');
 const base={source_id:'spk-x',source_name:'SPK (@spkgovtr)',family:'spk',official:false,published_at:post.at,language:'tr'};
 const documents:Document[]=[{...base,url:post.url,title:post.text.split('\n')[0],body:post.text,passages:[{id:'tweet_text',text:post.text}]}];
 const seen=new Set<string>();let attachments=0;
 async function visit(url:string,depth:number){
  url=safeUrl(url,['spk.gov.tr','www.spk.gov.tr','t.co']);if(seen.has(url))return;seen.add(url);
  if(depth>2||seen.size>10)throw Error('x_link_depth_limit');
  const r=await readPublic(url,['spk.gov.tr','www.spk.gov.tr','t.co'],{Accept:'application/pdf,text/html;q=0.9,*/*;q=0.8'},fetcher,true);
  const official=['spk.gov.tr','www.spk.gov.tr'].includes(new URL(r.url).hostname);if(!official)throw Error('x_link_not_official');
  if(new TextDecoder().decode(r.bytes!.slice(0,5))==='%PDF-'){
   if(++attachments>6)throw Error('x_attachment_limit');const evidence=await pdf(r.bytes!);if(!evidence.coverage?.complete)throw Error('x_pdf_incomplete');
   documents.push({...base,official:true,url:r.url,title:documents[0].title,...evidence});return;
  }
  if(!/html/i.test(r.headers.get('content-type')??''))throw Error('x_link_type_unsupported');
  const {document}=parseHTML(new TextDecoder('utf-8',{fatal:true}).decode(r.bytes!));
  const main=document.querySelector('.page-content .icerik')??document.querySelector('article');if(!main)throw Error('x_article_root_missing');
  const body=stripHtml(main.innerHTML);if(body.length<30)throw Error('x_article_empty');
  documents.push({...base,official:true,url:r.url,title:document.querySelector('.page-content .baslik,h1')?.textContent?.trim()||documents[0].title,body,passages:[{id:'linked_article',text:body}]});
  for(const a of main.querySelectorAll('a[href]'))await visit(new URL(a.getAttribute('href')!,r.url).href,depth+1);
  for(const img of main.querySelectorAll('img[src]')){
   if(++attachments>6)throw Error('x_attachment_limit');const u=safeUrl(new URL(img.getAttribute('src')!,r.url).href,['spk.gov.tr','www.spk.gov.tr']);const media=await readPublic(u,['spk.gov.tr','www.spk.gov.tr'],{Accept:'image/*'},fetcher,true);const e=await image(media.bytes!);if(!e.coverage?.complete)throw Error('x_image_incomplete');documents.push({...base,official:true,url:u,title:'SPK duyuru görseli',...e});
  }
 }
 for(const link of post.links)await visit(link,0);
 for(const url of post.images){const r=await readPublic(safeUrl(url,['pbs.twimg.com']),['pbs.twimg.com'],{Accept:'image/*'},fetcher,true);const e=await image(r.bytes!);if(!e.coverage?.complete)throw Error('x_image_incomplete');documents.push({...base,url:post.url,title:'SPK tweet görseli',...e});}
 if(documents.length>15||JSON.stringify(documents).length>3_500_000)throw Error('x_evidence_limit');return documents;
}
