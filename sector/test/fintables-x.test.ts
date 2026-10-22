import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {parseFintablesPosts,selectFintablesPost,pollFintablesX,fintablesPostDocuments,isFintablesNavigation} from '../src/fintables-x';
import {localDatabase} from '../src/local-adapters';import type {Env} from '../src/types';
const now=Date.now();const item=(id:string,account='fintables',text='$KLGYO 2026/9 finansal tabloları açıklandı.')=>`<item><link>https://nitter.pp.ua/${account}/status/${id}</link><pubDate>${new Date(now).toUTCString()}</pubDate><description><![CDATA[<p>${text}</p><a href="https://fintables.com/sirketler/KLGYO">Detaylar</a><a href="https://app.adjust.com/b8veq3c">Mobil</a><img src="https://pbs.twimg.com/media/test.jpg"/>]]></description></item>`;
const xml=(items=item('123'))=>`<rss><channel><title>Fintables / @fintables</title>${items}</channel></rss>`;
const post=()=>parseFintablesPosts(xml())[0];
const evidence={body:'2026/9 net dönem karı: -748.598.000 TL; 2025/9: -948.659.000 TL',passages:[{id:'image_visual_1',text:'2026/9 net dönem karı: -748.598.000 TL'}],images:['original.png'],coverage:{complete:true,page_count:1,pages:[{}]}};
test('Fintables parses own posts, skips retweets and filters promotions but keeps financial and sector posts',()=>{
 assert.equal(parseFintablesPosts(xml(item('123')+item('124','FintablesHaber'))).length,1);
 for(const text of ['2026 3. Çeyrek Bilanço Tarihini Açıklayan Şirketler','Banka dışı finans sektörü verileri açıklandı','PGSUS uçuş trafik verilerini açıkladı'])assert(selectFintablesPost({...post(),text}));
 for(const text of ['Banka dışı finans bülteninin tamamını okumak için','Bilanço #reklam','CNBC-e konuğu','Nakit döngüsü nedir? arkadaşına gönder'])assert(!selectFintablesPost({...post(),text}));
 assert.throws(()=>parseFintablesPosts(xml().replace('@fintables','@other')),/account/);
});
test('financial images retain original pixels and evidence; navigation does not mix current dashboard values into old periods',async()=>{
 let calls=0;const docs=await fintablesPostDocuments(post(),async()=>{throw Error('unexpected_pdf');},async()=>evidence,(async()=>{calls++;return new Response(new Uint8Array([1]));}) as typeof fetch);
 assert.equal(calls,1);assert.equal(docs.length,2);assert.deepEqual(docs[1].images,['original.png']);assert.equal(docs[1].official,false);
 assert(!isFintablesNavigation('https://fintables.com/sirketler/KLGYO/report.pdf'));
 await assert.rejects(()=>fintablesPostDocuments(post(),async()=>evidence,async()=>({...evidence,coverage:{complete:false,page_count:1,pages:[]}}),(async()=>new Response('image')) as typeof fetch),/incomplete/);
 await assert.rejects(()=>fintablesPostDocuments({...post(),links:['https://evil.example/report']},async()=>evidence,async()=>evidence),/unregistered/);
});
test('linked PDF attachments are read and unreadable PDFs block the entire bundle',async()=>{
 const p={...post(),links:['https://fintables.com/report.pdf'],images:[]};const fetcher=(async()=>new Response('%PDF-fixture')) as typeof fetch;
 assert.equal((await fintablesPostDocuments(p,async()=>evidence,async()=>evidence,fetcher)).length,2);
 await assert.rejects(()=>fintablesPostDocuments(p,async()=>{throw Error('unreadable');},async()=>evidence,fetcher),/unreadable/);
});
test('Fintables has an independent persistent ten-minute state; initial history silent, new relevant posts only once',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));const env={DB} as Env;
 await DB.prepare("INSERT INTO sources(id,config,enabled) VALUES('fintables-x','{}',1)").run();
 let posts=[post()],calls=0;const load=async()=>{calls++;return {posts,host:'fixture'};};
 await pollFintablesX(env,now,load);await pollFintablesX(env,now+599999,load);assert.equal(calls,1);
 posts=[{...post(),id:'125',url:'https://x.com/fintables/status/125',at:new Date(now+1000).toISOString()}, {...post(),id:'126',url:'https://x.com/fintables/status/126',text:'Reklam duyurusu',at:new Date(now+1000).toISOString()},post()];
 await pollFintablesX(env,now+600000,load);await pollFintablesX(env,now+1200000,load);
 assert.equal((await DB.prepare('SELECT count(*) n FROM articles').first<{n:number}>())!.n,1);
 assert.equal(await DB.prepare("SELECT value FROM system_state WHERE key='spk_x_state'").first(),null);
 await pollFintablesX(env,now+1800000,async()=>{throw Error('offline');});const state=JSON.parse((await DB.prepare("SELECT value FROM system_state WHERE key='fintables_x_state'").first<{value:string}>())!.value);assert.equal(state.seen.length,3);assert.equal(state.failures,1);
});

test('proxied link-card thumbnail does not invalidate unrelated financial posts',()=>{
 const raw=xml().replace('https://pbs.twimg.com/media/test.jpg','http://nitter.meowing.monster/pic/card_img%2F2113245328686112768%2FxWqG_xMJ%3Fformat%3Djpg%26name%3D800x419');
 assert.equal(parseFintablesPosts(raw)[0].images[0],'https://pbs.twimg.com/card_img/2113245328686112768/xWqG_xMJ?format=jpg&name=800x419');
 assert.throws(()=>parseFintablesPosts(raw.replace('card_img%2F','other%2F')),/image_host/);
});
test('stale first mirror cannot hide new posts available from another mirror',async()=>{
 const {fetchFintablesPosts}=await import('../src/fintables-x');
 const r=await fetchFintablesPosts((async(url:unknown)=>String(url).includes('netbub')?new Response(xml(item('123'))):String(url).includes('meowing')?new Response(xml(item('124')+item('123'))):new Response('rate limited',{status:429})) as typeof fetch);
 assert.deepEqual(new Set(r.posts.map(p=>p.id)),new Set(['123','124']));assert.equal(r.posts.length,2);
});
