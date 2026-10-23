import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {localDatabase} from '../src/local-adapters';
import {cleanupRawDocuments} from '../src/pipeline';
import {OFFICIAL_PDF_DOCUMENT_TTL_SECONDS} from '../src/bridge';
import type {Env} from '../src/types';

test('official SPK PDF source bodies follow the 24-hour raw document retention policy',()=>{
 assert.equal(OFFICIAL_PDF_DOCUMENT_TTL_SECONDS,24*3600);
});

test('raw documents expire on terminal or stale jobs while active and fresh review evidence remains',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),time=2_000_000_000;
 await DB.prepare("INSERT INTO sources(id,config) VALUES('s','{}')").run();
 for(const [state,age] of [['complete',0],['failed',0],['expired',0],['cancelled',0],['queued',25*3600],['needs_review',25*3600],['leased',25*3600],['queued',0]] as const){
  const n=String(Math.random()).slice(2),article='a'+n;
  await DB.prepare('INSERT INTO articles(id,source_id,url,title,summary,published_at,first_seen,document,document_expires) VALUES(?,?,?,?,?,?,?,?,?)').bind(article,'s',`https://example.test/${article}`,article,'','2026-10-22',time-100,'raw',time-1).run();
  await DB.prepare('INSERT INTO model_jobs(id,article_id,documents,input_hash,state,created_at) VALUES(?,?,?,?,?,?)').bind('j'+n,article,'["raw"]','hash',state,time-age).run();
 }
 await cleanupRawDocuments({DB} as Env,time);
 const rows=await DB.prepare('SELECT state,documents FROM model_jobs ORDER BY id').all<{state:string;documents:string}>();
 assert.equal(rows.results?.filter(r=>r.documents==='[]').length,6);
 assert.equal(rows.results?.filter(r=>r.state==='leased'&&r.documents==='["raw"]').length,1);
 assert.equal(rows.results?.filter(r=>r.state==='queued'&&r.documents==='["raw"]').length,1);
 assert.equal((await DB.prepare('SELECT COUNT(*) n FROM articles WHERE document IS NOT NULL').first<{n:number}>())?.n,0);
});
