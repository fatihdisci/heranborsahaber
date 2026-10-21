import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {KapStore} from '../src/kap/store';
import {KapDelivery} from '../src/kap-delivery';
import {parseDisclosure,fullText} from '../src/kap/parser';
import {completeKapDocuments} from '../src/kap-evidence';
import {localDatabase} from '../src/local-adapters';
import {pdfBytes} from '../src/pdf-transport';
import {enqueueEvidence} from '../src/ingest';
import {queueManual} from '../src/manual';
import type {Env,Document} from '../src/types';
const NOW=Date.now();
function page(summary='Açıklama',count=0){const date=new Date(NOW+3*3600_000).toISOString().replace(/-/g,'.').replace('T',' ').slice(0,19);
 const basic={disclosureIndex:101,title:'Payların Geri Alınmasına İlişkin Bildirim',companyTitle:'TEST SANAYİ A.Ş.',stockCode:'TEST',relatedStocks:null,disclosureClass:'ODA',disclosureType:'ODA',disclosureCategory:'ODA',publishDate:date,disclosureId:'a'.repeat(32),relatedDisclosureOid:null,isChanged:null,summary,attachmentCount:count};
 return `<script>self.__next_f.push(${JSON.stringify([1,JSON.stringify({disclosureBasic:basic})])})</script><div class="disclosureScrollableArea"><p>Tam metin işlem hakkında bilgi verir.</p><table><tr><td>İşlem Tarihi</td><td>20.10.2026</td></tr></table></div>`;
}
async function setup(){const s=new KapStore(':memory:');const l=s.claim('discovery',NOW)!;s.discover([{id:100,publishedAt:new Date(NOW-5000).toISOString()}],l,NOW-2000);
 const d=parseDisclosure(page(),101);s.save(d,s.claim('live',NOW)!,NOW,true);
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));const env={DB,MODE:'telegram_review',AI_DAILY_DRAFT_LIMIT:'240',TELEGRAM_USER_ID:'7',TELEGRAM_CHAT_ID:'42'} as Env;
 const docs=await completeKapDocuments(fullText(page(),101),async()=>{throw Error('no attachment');});return {s,env,docs};}
test('KAP enqueues complete evidence idempotently, never marks model preparation as delivered',async()=>{
 const {s,env,docs}=await setup();try{let reads=0;const c=new KapDelivery(s,env,async()=>{reads++;return docs;},()=>NOW);
 assert.equal((await c.run()).state,'model_queued');await c.run();assert.equal(reads,1);
 assert.equal(s.row<{state:string}>('SELECT state FROM queue')!.state,'model_queued');assert.equal(s.row<{sent_at:number|null}>('SELECT sent_at FROM queue')!.sent_at,null);
 const job=await env.DB.prepare('SELECT id,documents FROM model_jobs').first<{id:string;documents:string}>();assert(job);assert(JSON.parse(job.documents)[0].body.includes('20.10.2026'));
 assert.equal(await enqueueEvidence(env,docs,'kap'),job.id);assert.equal((await env.DB.prepare('SELECT COUNT(*) n FROM model_jobs').first<{n:number}>())!.n,1);
 }finally{s.close();}
});
test('KAP missing or unreadable PDF never enters the model or sends a metadata-only fallback',async()=>{
 const p=fullText(page('Özet',1),101);await assert.rejects(()=>completeKapDocuments(p,async()=>{throw Error('unreadable');}),/attachments_incomplete/);
 const withLink={...p,attachmentStatus:'links_available',attachments:[{url:'https://www.kap.org.tr/tr/api/file/download/'+'a'.repeat(32),label:'ek.pdf',contentStatus:'not_fetched' as const}]};
 await assert.rejects(()=>completeKapDocuments(withLink,async()=>{throw Error('pdf_page_unreadable');}),/pdf_page_unreadable/);
 const {s,env}=await setup();try{const c=new KapDelivery(s,env,async()=>{throw Error('pdf_page_unreadable');},()=>NOW);assert.equal((await c.run()).state,'evidence_failed');assert.equal((await env.DB.prepare('SELECT COUNT(*) n FROM model_jobs').first<{n:number}>())!.n,0);assert.equal(s.row<{sent_at:number|null}>('SELECT sent_at FROM queue')!.sent_at,null);}finally{s.close();}
});
test('all KAP PDFs retain every page and visual evidence, while spans preserve table column meaning',async()=>{
 const html=page().replace('</div>','<table><tr><th rowspan="2">İşlem</th><th colspan="2">Tutar</th></tr><tr><td>Alım</td><td>Satım</td></tr><tr><td>20.10.2026</td><td>100</td><td>0</td></tr></table></div>');
 const p=fullText(html,101);assert.deepEqual(p.tables[1][1],['İşlem','Alım','Satım']);
 const docs=await completeKapDocuments({...p,expectedAttachments:1,attachments:[{url:'https://www.kap.org.tr/tr/api/file/download/'+'a'.repeat(32),label:'ek.pdf',contentStatus:'not_fetched'}]},async()=>({body:'Bütün sayfalar',passages:[{id:'page1',text:'İşlem 20.10.2026'}],images:['source/page.png'],coverage:{complete:true,page_count:1,pages:[{page:1}]}}));
 assert.equal(docs.length,2);assert.equal(docs[1].images?.length,1);assert.equal(docs[1].coverage?.complete,true);
});
test('KAP preference recheck excludes breakers before expensive reading; no notifications in dry run',async()=>{
 const {s,env}=await setup();try{const row=s.row<{metadata:string}>('SELECT metadata FROM disclosures')!;const d=JSON.parse(row.metadata);d.summary='Devre Kesici';s.run('UPDATE disclosures SET metadata=?',JSON.stringify(d));let reads=0;
 const c=new KapDelivery(s,env,async()=>{reads++;return [];},()=>NOW);assert.equal((await c.run()).state,'idle');assert.equal(reads,0);assert.equal(s.row<{state:string}>('SELECT state FROM queue')!.state,'suppressed');
 assert.equal((await new KapDelivery(s,{...env,MODE:'dry_run'},async()=>[],()=>NOW).run()).state,'disabled');
 }finally{s.close();}
});
test('KAP PDF transport accepts exact serialized byte arrays, never arbitrary prefixes or corrupt lengths',()=>{
 const pdf=new TextEncoder().encode('%PDF-1.7 test');assert.deepEqual(pdfBytes(pdf),pdf);
 const h=Buffer.from('aced0005757200025b42acf317f8060854e00200007870','hex'),len=Buffer.alloc(4);len.writeUInt32BE(pdf.length);const bytes=Buffer.concat([h,len,pdf]);assert.deepEqual([...pdfBytes(bytes)],[...pdf]);
 bytes[26]++;assert.throws(()=>pdfBytes(bytes),/length/);assert.throws(()=>pdfBytes(new TextEncoder().encode('junk %PDF-1.7')),/invalid/);
});
test('manual intake requires owner and private chat; same Telegram update queues only once',async()=>{
 const {s,env}=await setup();try{const m={message_id:3,from:{id:7},chat:{id:42,type:'private'},text:'https://www.cnbce.com/test'};
 assert.equal(await queueManual(env,10,{...m,from:{id:8}}),false);assert.equal(await queueManual(env,10,{...m,chat:{id:42,type:'group'}}),false);
 assert.equal(await queueManual(env,10,m),true);assert.equal(await queueManual(env,10,m),true);
 assert.equal((await env.DB.prepare('SELECT COUNT(*) n FROM manual_requests').first<{n:number}>())!.n,1);
 assert.equal(await queueManual(env,11,{...m,text:undefined,document:{file_id:'safe',file_name:'bildirim.pdf'}}),true);
 }finally{s.close();}
});

test('focused preferences suppress existing routine queue entries without deleting source records',async()=>{
 const {s}=await setup();try{
  const row=s.row<{metadata:string}>('SELECT metadata FROM disclosures')!;
  const d=JSON.parse(row.metadata);d.title='Özel Durum Açıklaması (Genel)';d.summary='Yönetim Kurulu Üye Değişikliği';
  s.run('UPDATE disclosures SET metadata=?',JSON.stringify(d));
  s.configure({...s.prefs(),priorityIndices:false,otherCompanies:'topics',otherTopics:['business','financial','buyback','share_trade','dividend','capital']});
  assert.equal(s.row<{state:string}>('SELECT state FROM queue')!.state,'suppressed');
  assert.equal(s.rows('SELECT * FROM disclosures').length,1);assert.equal(s.rows('SELECT * FROM feed').length,1);
 }finally{s.close();}
});
