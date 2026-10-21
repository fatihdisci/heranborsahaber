import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {localDatabase,localMedia} from '../src/local-adapters';
import {prepare} from '../src/pipeline';
import type {Env,Source} from '../src/types';
test('local production adapter preserves atomic batches and media path isolation',async()=>{
 const dir=await mkdtemp(tmpdir()+'/sector-test-');try{
  const db=await localDatabase(dir+'/sector.sqlite',await readFile('migrations/0001_sector.sql','utf8'));
  await db.prepare("INSERT INTO system_state VALUES('own','1')").run();
  await assert.rejects(()=>db.batch([db.prepare("UPDATE system_state SET value='changed' WHERE key='own'"),db.prepare('INSERT INTO missing VALUES(1)')]));
  assert.equal((await db.prepare("SELECT value FROM system_state WHERE key='own'").first<{value:string}>())!.value,'1');
  assert(await localDatabase(dir+'/sector.sqlite',await readFile('migrations/0001_sector.sql','utf8')));
  const media=await localMedia(dir+'/media');await media.put('drafts/own/1.png',new Uint8Array([1,2,3]));assert.equal((await media.get('drafts/own/1.png'))!.size,undefined);
  await assert.rejects(()=>media.put('../outside.png',new Uint8Array()));
 }finally{await rm(dir,{recursive:true,force:true});}
});
test('startup archive stays out of live jobs and an important older item outranks routine fresh news',async()=>{
 const dir=await mkdtemp(tmpdir()+'/sector-queue-'),original=globalThis.fetch;
 try {
  const db=await localDatabase(dir+'/sector.sqlite',await readFile('migrations/0001_sector.sql','utf8'));
  const source:Source={id:'test',name:'Test',url:'https://test.example.org/rss',allowed_hosts:['test.example.org'],family:'test',language:'tr',official:false,poll_seconds:120,fresh_hours:72,enabled:true,checked_at:'2026-10-21',terms_url:'https://test.example.org/terms',rights_note:'test',review_mode:'official_facts'};
  await db.prepare('INSERT INTO sources(id,config,enabled) VALUES(?,?,1)').bind('test',JSON.stringify(source)).run();
  await db.prepare("INSERT INTO system_state VALUES('live_since',?)").bind(new Date(Date.now()-10*60_000).toISOString()).run();
  const articles=[['archive','TCMB eski faiz kararı',-24*3600_000],['important','TCMB yeni faiz kararını açıkladı',-5*60_000],['fresh1','Örnek şirket yatırım planlıyor',-1000],['fresh2','Farklı şirket yatırım duyurdu',-2000]] as const;
  for(const [id,title,age] of articles)await db.prepare('INSERT INTO articles(id,source_id,url,title,summary,published_at,first_seen) VALUES(?,?,?,?,?,?,?)').bind(id,'test','https://test.example.org/'+id,title,'',new Date(Date.now()+age).toISOString(),Date.now()/1000).run();
  globalThis.fetch=(async(input:RequestInfo|URL)=>{const id=String(input).split('/').at(-1),title=articles.find(a=>a[0]===id)![1];return new Response('<article><h1>'+title+'</h1><p>Kurum, yatırım hazırlıklarının sürdüğünü ve gelişmelerin kamuoyuyla paylaşılacağını bildirdi. İlgili süreç için gerekli değerlendirmeler devam ediyor.</p></article>',{headers:{'content-type':'text/html'}});}) as typeof fetch;
  await prepare({DB:db,MEDIA:await localMedia(dir+'/media'),AI_DAILY_DRAFT_LIMIT:'10'} as Env);
  const jobs=await db.prepare('SELECT article_id FROM model_jobs').all<{article_id:string}>();const ids=jobs.results.map(r=>r.article_id);
  assert.equal(ids.length,2);assert(ids.includes('important'));assert(!ids.includes('archive'));
 }finally{globalThis.fetch=original;await rm(dir,{recursive:true,force:true});}
});
