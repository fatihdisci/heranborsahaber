import {parseHTML} from 'linkedom';
import {parseSpkPosts,pollSpkX,SPK_X_HOSTS,type SpkPost,type EvidenceReader} from './spk-x';
import {readPublic,safeUrl} from './network';
import {stripHtml} from './utils/text';
import type {Document,Env} from './types';
const hosts=['fintables.com','www.fintables.com'];
export function selectFintablesPost(post:SpkPost):boolean{
 const text=post.text.toLocaleLowerCase('tr');
 if(/#reklam|#işbirliği|konuğu|konuk oluyor|canlı yayın|tamamını okumak|arkadaşına gönder/.test(text))return false;
 return /finansal tablolar|bilanço|sektör.*verileri|sektörel|uçuş trafik|trafik verileri/.test(text);
}
export const parseFintablesPosts=(xml:string)=>parseSpkPosts(xml,'fintables');
export async function fetchFintablesPosts(fetcher:typeof fetch=fetch){
 for(const host of SPK_X_HOSTS)try{const r=await readPublic('https://'+host+'/fintables/rss',[host],{},fetcher);return {posts:parseFintablesPosts(r.text),host};}catch{/* Validate each independent mirror. */}
 throw Error('x_all_mirrors_unavailable');
}
export const pollFintablesX=(env:Env,now=Date.now(),load=fetchFintablesPosts)=>pollSpkX(env,now,load,'fintables-x',selectFintablesPost);
// These links navigate to changing company dashboards / app install, not the
// period-specific report. Do not contaminate the posted table with live values.
export function isFintablesNavigation(url:string){
 const u=new URL(url);return u.protocol==='https:'&&!u.username&&!u.password&&!u.port&&((hosts.includes(u.hostname)&&/^\/sirketler\/[A-Z0-9]+\/?$/i.test(u.pathname))||(u.hostname==='app.adjust.com'&&u.pathname==='/b8veq3c'));
}
export async function fintablesPostDocuments(post:SpkPost,pdf:EvidenceReader,image:EvidenceReader,fetcher:typeof fetch=fetch):Promise<Document[]>{
 if(!post||!/^\d+$/.test(post.id)||post.url!=='https://x.com/fintables/status/'+post.id||!Array.isArray(post.links)||!Array.isArray(post.images))throw Error('x_manifest_invalid');
 if(post.unsupported)throw Error('x_video_requires_review');
 if(post.links.length>6||post.images.length>4)throw Error('x_attachment_limit');
 const base={source_id:'fintables-x',source_name:'Fintables (@fintables)',family:'fintables',official:false,published_at:post.at,language:'tr'};
 const docs:Document[]=[{...base,url:post.url,title:post.text.split('\n')[0],body:post.text,passages:[{id:'tweet_text',text:post.text}]}];
 const seen=new Set<string>();let attachments=0;
 async function media(url:string,allowed:string[],title:string){
  if(++attachments>8)throw Error('x_attachment_limit');const r=await readPublic(safeUrl(url,allowed),allowed,{Accept:'image/*'},fetcher,true);
  const evidence=await image(r.bytes!);if(!evidence.coverage?.complete)throw Error('x_image_incomplete');docs.push({...base,url,title,...evidence});
 }
 async function visit(url:string,depth:number){
  if(isFintablesNavigation(url))return;
  url=safeUrl(url,hosts);if(seen.has(url))return;seen.add(url);if(depth>2||seen.size>10)throw Error('x_link_depth_limit');
  const r=await readPublic(url,hosts,{Accept:'application/pdf,text/html;q=0.9'},fetcher,true);
  if(new TextDecoder().decode(r.bytes!.slice(0,5))==='%PDF-'){
   if(++attachments>8)throw Error('x_attachment_limit');const evidence=await pdf(r.bytes!);if(!evidence.coverage?.complete)throw Error('x_pdf_incomplete');docs.push({...base,url:r.url,title:docs[0].title,...evidence});return;
  }
  if(!/html/i.test(r.headers.get('content-type')??''))throw Error('x_link_type_unsupported');
  const {document}=parseHTML(new TextDecoder('utf-8',{fatal:true}).decode(r.bytes!));const main=document.querySelector('article');
  if(!main||document.querySelector('[itemprop="isAccessibleForFree"][content="false"]')||/abone ol|giriş yaparak|üyelik gerektir/i.test(main.textContent??''))throw Error('x_article_access_incomplete');
  const body=stripHtml(main.innerHTML);if(body.length<80)throw Error('x_article_empty');
  docs.push({...base,url:r.url,title:document.querySelector('h1')?.textContent?.trim()||docs[0].title,body,passages:[{id:'linked_article',text:body}]});
  for(const a of main.querySelectorAll('a[href]'))await visit(new URL(a.getAttribute('href')!,r.url).href,depth+1);
  for(const a of main.querySelectorAll('img[src]'))await media(new URL(a.getAttribute('src')!,r.url).href,[...hosts,'pbs.twimg.com'],'Fintables bağlantılı görsel');
 }
 for(const link of post.links)await visit(link,0);
 for(const url of post.images)await media(url,['pbs.twimg.com'],'Fintables finansal veri görseli');
 if(docs.length>15||JSON.stringify(docs).length>3_500_000)throw Error('x_evidence_limit');return docs;
}
