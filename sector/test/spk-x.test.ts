import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {parseSpkPosts,fetchSpkPosts,pollSpkX,spkPostDocuments} from '../src/spk-x';import {localDatabase} from '../src/local-adapters';import type {Env} from '../src/types';
const now=Date.now(),id='2113250433733161013';
const xml=(account='spkgovtr')=>`<rss><channel><title>SPK / @${account}</title><item><title>Duyuru</title><link>http://nitter.pp.ua/${account}/status/${id}#m</link><pubDate>${new Date(now-1000).toUTCString()}</pubDate><description><![CDATA[<p>Takas kesinliği ve PBLK duyurusu <a href="https://spk.gov.tr/duyuru">Detaylar</a></p><img src="http://nitter.pp.ua/pic/media%2FHVPGD56W8AA7EsW.jpg"/>]]></description></item></channel></rss>`;
const post=()=>parseSpkPosts(xml())[0];
const evidence={body:'Belgedeki açık ve doğrulanmış açıklama metni.',passages:[{id:'p1',text:'Belgedeki açık ve doğrulanmış açıklama metni.'}],images:[],coverage:{complete:true,page_count:1,pages:[{}]}};
test('SPK RSS validates account, ID, links and images; challenges fail',()=>{const p=post();assert.equal(p.url,'https://x.com/spkgovtr/status/'+id);assert.deepEqual(p.links,['https://spk.gov.tr/duyuru']);assert.deepEqual(p.images,['https://pbs.twimg.com/media/HVPGD56W8AA7EsW.jpg']);assert.throws(()=>parseSpkPosts(xml('other')),/account/);assert.throws(()=>parseSpkPosts('<html>Challenge</html>'));assert.throws(()=>parseSpkPosts('<!DOCTYPE rss>'+xml()),/unsafe/);});
test('failed mirror falls back without X credentials',async()=>{let count=0;const r=await fetchSpkPosts((async()=>++count===1?new Response('Forbidden',{status:403}):new Response(xml())) as typeof fetch);assert.equal(count,2);assert.equal(r.posts[0].id,id);});
test('SPK warm start is silent; ten-minute scan deduplicates across restarts and preserves cursor on failure',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));const env={DB} as Env;await DB.prepare("INSERT INTO sources(id,config,enabled) VALUES('spk-x','{}',1)").run();let calls=0;
 let posts=[post()];const load=async()=>{calls++;return {posts,host:'fixture'};};await pollSpkX(env,now,load);assert.equal((await DB.prepare('SELECT count(*) n FROM articles').first<{n:number}>())!.n,0);
 await pollSpkX(env,now+599999,load);assert.equal(calls,1);
 posts=[{...post(),id:'2113250433733161014',url:'https://x.com/spkgovtr/status/2113250433733161014',at:new Date(now+2000).toISOString()},post()];
 await pollSpkX(env,now+600000,load);await pollSpkX(env,now+1200000,load);assert.equal((await DB.prepare('SELECT count(*) n FROM articles').first<{n:number}>())!.n,1);
 await pollSpkX(env,now+1800000,async()=>{throw Error('offline');});const state=JSON.parse((await DB.prepare("SELECT value FROM system_state WHERE key='spk_x_state'").first<{value:string}>())!.value);assert.equal(state.seen.length,2);assert.equal(state.failures,1);assert.equal(state.since,now);
});
test('tweet, scoped page, PDF and image form a complete bundle; unreadable or unregistered attachments fail',async()=>{
 const paths:string[]=[];const fetcher=(async(url:any)=>{paths.push(String(url));return String(url).endsWith('.pdf')?new Response('%PDF-fixture',{headers:{'content-type':'application/pdf'}}):String(url).includes('pbs.twimg')?new Response(new Uint8Array([1,2])):new Response('<nav><a href="https://spk.gov.tr/unrelated.pdf">Unrelated</a></nav><div class="page-content"><h3 class="baslik">SPK duyurusu</h3><div class="icerik">Bu resmi açıklamanın tam metni ve ilgili dosyalar.<a href="/notice.pdf">PDF</a></div></div>',{headers:{'content-type':'text/html'}});}) as typeof fetch;
 let pdf=0,img=0;const docs=await spkPostDocuments(post(),async()=>{pdf++;return evidence;},async()=>{img++;return evidence;},fetcher);assert.equal(docs.length,4);assert.equal(pdf,1);assert.equal(img,1);assert.equal(docs[0].official,false);assert.equal(docs[1].official,true);assert(!paths.some(p=>p.includes('unrelated')));
 await assert.rejects(()=>spkPostDocuments(post(),async()=>{throw Error('pdf_unreadable');},async()=>evidence,fetcher),/pdf_unreadable/);
 await assert.rejects(()=>spkPostDocuments({...post(),links:['http://127.0.0.1/private']},async()=>evidence,async()=>evidence,fetcher),/unregistered/);
 await assert.rejects(()=>spkPostDocuments({...post(),unsupported:true},async()=>evidence,async()=>evidence,fetcher),/video_requires_review/);
});
test('image-only posts do not poison the feed',()=>{const raw=xml().replace(/<p>.*?<\/p>/,'');const p=parseSpkPosts(raw)[0];assert.equal(p.images.length,1);assert(p.text);});
test('generation queues the entire evidence bundle only after request and retains its manifest/cache',async()=>{
 const {prepare}=await import('../src/pipeline');const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));let reads=0;
 const docs=[{...evidence,source_id:'spk-x',source_name:'SPK',family:'spk',official:false,url:post().url,title:'SPK PBLK açıklaması',published_at:new Date().toISOString()},{...evidence,source_id:'spk-x',source_name:'SPK',family:'spk',official:true,url:'https://spk.gov.tr/notice.pdf',title:'SPK PDF',published_at:new Date().toISOString()}];
 const env={DB,MODE:'dry_run',AI_DAILY_DRAFT_LIMIT:'240',READ_SPK_X:async()=>{reads++;return docs;}} as unknown as Env;
 await DB.prepare("INSERT INTO sources(id,config,enabled) VALUES('spk-x',?,1)").bind(JSON.stringify({id:'spk-x',official:false,method:'reference'})).run();
 await DB.prepare("INSERT INTO articles(id,source_id,url,title,summary,published_at,first_seen,document) VALUES('a','spk-x',?,'SPK PBLK açıklaması','Fon tasfiye',?,0,?)").bind(post().url,new Date().toISOString(),JSON.stringify(post())).run();
 await prepare(env);assert.equal(reads,0);
 await DB.prepare("INSERT INTO news_cards(id,article_id,state,message_id,created_at) VALUES('n','a','requested',1,0)").run();await prepare(env);assert.equal(reads,1);
 const job=await DB.prepare('SELECT documents FROM model_jobs').first<{documents:string}>();assert.equal(JSON.parse(job!.documents).length,2);
 const article=await DB.prepare("SELECT document,document_expires FROM articles WHERE id='a'").first<{document:string;document_expires:number}>(),cache=JSON.parse(article!.document);assert.equal(cache.id,id);assert.equal(cache.cached_documents.length,2);assert(article!.document_expires>=Math.floor(Date.now()/1000)+6*86400);
 await prepare(env);assert.equal(reads,1);
});
