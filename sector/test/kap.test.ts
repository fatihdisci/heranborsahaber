import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {parseDisclosure,flightText,jsonValue,kapDate,parseListing,parseIndices,fullText,type Disclosure} from '../src/kap/parser';
import {DEFAULTS,preferences,decide,classify,digestAt,type Preferences} from '../src/kap/rules';
import {KapStore,type Lease} from '../src/kap/store';
import {KapCollector,type Source} from '../src/kap/collector';
import {KapClient} from '../src/kap/client';
const NOW=Date.parse('2026-10-21T13:00:00Z');
const basic=(more:Record<string,unknown>={})=>({disclosureIndex:101,title:'Yeni İş İlişkisi',companyTitle:'TEST SANAYİ A.Ş.',stockCode:'TEST',relatedStocks:null,disclosureClass:'ODA',disclosureType:'ODA',disclosureCategory:'ODA',publishDate:'2026.10.21 16:00:00',disclosureId:'a'.repeat(32),relatedDisclosureOid:null,isChanged:null,summary:'Sözleşme imzalandı.',...more});
function page(b=basic(),body=''){const data='7:'+JSON.stringify({disclosureBasic:b});const split=23;return `<script>self.__next_f.push(${JSON.stringify([1,data.slice(0,split)])})</script><script>self.__next_f.push(${JSON.stringify([1,data.slice(split)])})</script>${body}`;}
const item=(id=101,more:Record<string,unknown>={})=>parseDisclosure(page(basic({disclosureIndex:id,...more})),id);
const setup=()=>{const dir=mkdtempSync(join(tmpdir(),'sector-kap-test-')),path=join(dir,'kap.sqlite'),store=new KapStore(path);const lease=store.claim('discovery',NOW)!;store.discover([{id:100,publishedAt:new Date(NOW-1000).toISOString()}],lease,NOW);store.finish(lease,NOW,60_000);return {store,path,close:()=>{store.close();rmSync(dir,{recursive:true,force:true});}};};
const pref=(p:Partial<Preferences>={})=>preferences({...structuredClone(DEFAULTS),...p});

test('KAP Flight preserves split chunks, quoted names and nested JSON; scripts never execute',()=>{
 const d=item(101,{companyTitle:'ŞİRKET "A {B}" \\ TEST',summary:'Satır\nİkinci [satır]'});assert.equal(d.company,'ŞİRKET "A {B}" \\ TEST');assert.equal(d.publishedAt,'2026-10-21T13:00:00.000Z');
 assert.deepEqual(jsonValue('{"a":[{"x":"}\\\""}]}',0),{a:[{x:'}"'}]});assert.throws(()=>jsonValue('{"a":[}',0));assert.throws(()=>flightText('<script>self.__next_f.push([1,"x"]);evil()</script>'));
 assert.throws(()=>parseDisclosure(page(basic({disclosureIndex:102})),101),/id_mismatch/);assert.throws(()=>item(101,{title:''}));assert.throws(()=>item(101,{summary:{bad:true}}));assert.throws(()=>parseDisclosure('<html>captcha</html>',101),/basic_missing/);
});
test('KAP source dates are Istanbul times; invalid calendar dates fail closed',()=>{
 assert.equal(kapDate('21.10.2026 16:00:00',true),new Date(NOW).toISOString());for(const value of ['2026.02.30 10:00:00','2026.10.21 24:00:00','not a date'])assert.throws(()=>kapDate(value));
 assert.throws(()=>parseListing([{disclosureIndex:101,subject:'a',publishDate:'21.10.2027 16:00:00'}],NOW));
});
test('KAP issuer and related stocks stay separate; portfolio/fund codes cannot become shares',()=>{
 assert.deepEqual(item(101,{stockCode:'SKP',companyTitle:'ÖRNEK PORTFÖY YÖNETİMİ A.Ş.',relatedStocks:'AKBNK,THYAO'}).subjectCodes,[]);
 assert.deepEqual(item(101,{stockCode:'FUND',disclosureType:'FON',companyTitle:'ÖRNEK FON'}).subjectCodes,[]);
 assert.deepEqual(item(101,{stockCode:null,relatedStocks:'THYAO, AKBNK,THYAO, ABC, -BAD'}).relatedCodes,['THYAO','AKBNK']);
 assert.deepEqual(item(101,{stockCode:null,relatedStocks:'THYAO'}).subjectCodes,['THYAO']);
 const d=item(101,{stockCode:null,title:'Piyasa Duyurusu',relatedStocks:'THYAO,AKBNK'});
 const result=decide(d,pref({otherCompanies:'off'}),{bist30:['THYAO'],bist100:['THYAO','AKBNK'],checkedAt:'',source:''});assert.equal(result.action,'off');assert.equal(result.indexTier,null);
});
test('KAP topic matching covers Turkish accents and all selected topics',()=>{
 const examples:Record<string,string>={'Kâr Payı Dağıtımı':'dividend','payların geri alınmasına ilişkin bildirim':'buyback','Geri Satım Bildirimi':'buyback','Finansal Sonuç':'financial','Faaliyet Raporu':'financial','Bedelsiz Sermaye Artırımı':'capital','Yeni İş İlişkisi':'business','Pay Satım Bildirimi':'share_trade','Pay Bazında Devre Kesici Bildirimi':'circuit'};
 for(const [title,topic] of Object.entries(examples))assert.ok(classify(item(101,{title})).includes(topic as never),title);
});
test('KAP exact legacy precedence: funds off first, shares override exclusions, no BIST50 restriction',()=>{
 const share=item(101,{title:'Pay Alım Bildirimi - Kredi Kullanımı'});assert.equal(decide(share,pref({otherCompanies:'off',priorityIndices:false}),null).action,'instant');
 assert.equal(decide({...share,isFund:true},pref(),null).action,'off');
 const crisis=item(101,{title:'Tasfiye ve Ödeme',disclosureType:'FON'});assert.equal(decide(crisis,pref(),null).action,'off');assert.equal(decide(crisis,pref({funds:'digest'}),null).action,'instant');
 const muted=item(101,{title:'İç Tüzük Tasfiye',disclosureType:'FON'});assert.equal(decide(muted,pref({funds:'instant'}),null).action,'off');
});
test('KAP storage and notification differ; routine explicit tracking and mandatory mutes',()=>{
 const routine=item(101,{title:'Kredi Derecelendirmesi'});assert.equal(decide(routine,pref(),null).store,false);
 const tracked=pref({watchlist:[{ticker:'TEST',mode:'all',topics:[]}]});assert.equal(decide(routine,tracked,null).action,'instant');
 const excluded=item(101,{title:'İhraç Belgesi'});assert.equal(decide(excluded,pref(),null).store,true);assert.equal(decide(excluded,pref(),null).action,'off');
 for(const title of ['İç Tüzük','Fon Gider Bilgileri','Fon Toplam Giderinin Dağılımı','Faizsiz Pay Dışı Sermaye Piyasası Aracı İşlemleri','Kurumsal Yönetim Bilgi Formu (Güncelleme) – Yönetim Kurulu-2'])assert.equal(decide(item(101,{title}),tracked,null).action,'off',title);
 assert.equal(decide(routine,pref({otherCompanies:'topics',otherTopics:['other']}),null).store,true);
});
test('KAP fund digest uses Istanbul 19:00 and preference validation is strict',()=>{
 assert.equal(new Date(digestAt(NOW,'19:00')).toISOString(),'2026-10-21T16:00:00.000Z');assert.equal(new Date(digestAt(NOW+4*3600_000,'19:00')).toISOString(),'2026-10-22T16:00:00.000Z');
 assert.equal(decide(item(101,{disclosureType:'FON',title:'Portföy Dağılım Raporu'}),pref({funds:'digest'}),null).action,'digest');
 assert.throws(()=>pref({fundDigestTime:'25:90'}));assert.throws(()=>pref({watchlist:[{ticker:'ABC',mode:'all',topics:[]}]}));
});
test('KAP full text preserves labeled transaction/board dates and never substitutes summary',()=>{
 const html=page(basic(),'<div class="disclosureScrollableArea"><p>Tam açıklama</p><table><tr><td>Yönetim Kurulu Karar Tarihi</td><td>01.10.2026</td></tr></table><table><tr><th>İşlem Tarihi</th><th>Tutar</th></tr><tr><td>21.10.2026</td><td>500.000</td></tr></table></div>');
 const d=fullText(html,101);assert.equal(d.status,'available');assert.equal(d.boardDecisionDates[0].value,'01.10.2026');assert.equal(d.transactionDates[0].value,'21.10.2026');assert.equal(d.transactionRows[0].Tutar,'500.000');assert.equal(fullText(page(),101).status,'unavailable');assert.equal(fullText(page(),101).text,null);
});
test('KAP indices require exact 30/100 counts and subset, with no bundled fallback',()=>{
 const codes=Array.from({length:100},(_,i)=>'T'+String(i).padStart(3,'0'));
 const html=(a:string[],b:string[])=>`<script>self.__next_f.push(${JSON.stringify([1,JSON.stringify([{code:'XU030',content:a.map(stockCode=>({stockCode}))},{code:'XU100',content:b.map(stockCode=>({stockCode}))}])])})</script>`;
 assert.equal(parseIndices(html(codes.slice(0,30),codes)).bist100.length,100);assert.throws(()=>parseIndices(html(codes.slice(0,29),codes)));assert.throws(()=>parseIndices(html([...codes.slice(0,29),'NOPE'],codes)));
});
test('KAP source/feed/queue/cursor transaction rolls back on queue failure; duplicates stay single',()=>{
 const {store,close}=setup();try{const l=store.claim('live',NOW)!;
 store.db.exec("CREATE TRIGGER fail_queue BEFORE INSERT ON queue BEGIN SELECT RAISE(ABORT,'synthetic storage failure'); END;");assert.throws(()=>store.save(item(),l,NOW,true));assert.equal(store.health().sources,0);assert.equal(store.row<{cursor:number}>("SELECT cursor FROM jobs WHERE name='live'")!.cursor,100);
 store.db.exec('DROP TRIGGER fail_queue');store.save(item(),l,NOW,true);store.save(item(),l,NOW,true);assert.equal(store.health().sources,1);assert.equal(store.health().queue,1);assert.equal(store.rows('SELECT * FROM queue_members').length,1);
 }finally{close();}
});
test('KAP startup and backfill are silent; KAP does not inherit RSS 30 minute cutoff',()=>{
 const {store,close}=setup();try{const l=store.claim('live',NOW)!;store.save(item(101,{publishDate:'2026.10.21 15:59:59'}),l,NOW,true);assert.equal(store.health().queue,0);
 store.set('notification_start',NOW-3*3600_000);store.save(item(102,{publishDate:'2026.10.21 14:00:00'}),l,NOW,true);assert.equal(store.health().queue,1);
 const b=store.claim('backfill',NOW)!;store.save(item(99),b,NOW,true);assert.equal(store.health().queue,1);store.save(item(98,{publishDate:'2026.10.19 16:00:00'}),b,NOW,true);assert.equal(store.row('SELECT * FROM disclosures WHERE id=98'),undefined);
 }finally{close();}
});
test('KAP lease fences survive restart and reject stale writers, other application DB rejected',()=>{
 const {store,path,close}=setup();try{const first=store.claim('live',NOW)!;assert.equal(store.claim('live',NOW),null);const second=new KapStore(path);try{assert.equal(second.claim('live',NOW),null);const next=second.claim('live',NOW+121_000)!;assert.ok(next);assert.throws(()=>store.save(item(),first,NOW+121_000,true),/lease_lost/);}finally{second.close();}
 const other=path+'.other',db=new DatabaseSync(other);db.exec('CREATE TABLE private_data(x)');db.close();assert.throws(()=>new KapStore(other),/namespace/);
 }finally{close();}
});
test('KAP circuit groups freeze after 12s without edge, max100 and late members start another group',()=>{
 const {store,close}=setup();try{const l=store.claim('live',NOW)!;for(let id=101;id<=201;id++)store.save(item(id,{title:'Devre Kesici',relatedStocks:'AKBNK,THYAO',stockCode:null}),l,NOW,true);
 const g=store.claim('groups',NOW)!;store.freeze(g,NOW+11_999);assert.equal(store.health().queue,0);store.freeze(g,NOW+12_000);const q=store.rows<{payload:string}>('SELECT payload FROM queue');assert.equal(q.length,2);assert.equal(JSON.parse(q[0].payload).disclosureIds.length,100);assert.deepEqual(JSON.parse(q[0].payload).codes,['AKBNK','THYAO']);
 store.save(item(202,{title:'Devre Kesici',stockCode:null,relatedStocks:'MEPET'}),l,NOW+13_000,true);store.freeze(g,NOW+24_999);assert.equal(store.health().queue,2);store.freeze(g,NOW+25_000);assert.equal(store.health().queue,3);
 }finally{close();}
});
test('KAP a missing ID cannot stall later disclosures; later publication is recovered once',async()=>{
 const {store,close}=setup();let now=NOW,missing=true;const source:Source={listing:async()=>[],indices:async()=>{throw Error('unused');},disclosure:async id=>id===101&&missing?null:item(id)};
 try{store.set('last_listing',{max:103});const c=new KapCollector(store,source,()=>now);await c.run('live');assert.equal(store.row<{cursor:number}>("SELECT cursor FROM jobs WHERE name='live'")!.cursor,103);assert.equal(store.health().queue,2);assert.equal(store.health().unresolvedGaps,1);
 now+=30_000;missing=false;await c.run('reconcile');assert.equal(store.health().queue,3);assert.equal(store.health().unresolvedGaps,0);
 }finally{close();}
});
test('KAP parser/HTTP failures never advance cursor; discovery repair can still ingest later IDs',async()=>{
 const {store,close}=setup();let now=NOW;const source:Source={listing:async()=>[],indices:async()=>{throw Error('kap_index_missing');},disclosure:async id=>{if(id===101)throw Error('kap_id_mismatch');return item(id);}};
 try{store.run('INSERT INTO discovered VALUES(?,?,?)',102,new Date(NOW).toISOString(),NOW);const c=new KapCollector(store,source,()=>now);await c.run('live');assert.equal(store.row<{cursor:number}>("SELECT cursor FROM jobs WHERE name='live'")!.cursor,100);await c.run('reconcile');assert.equal(store.health().queue,1);
 for(let n=0;n<7;n++){now+=300_000;await c.run('live');const r=store.row<{next_at:number}>("SELECT next_at FROM jobs WHERE name='live'")!;assert.ok(r.next_at-now<=300_000);}
 const old={bist30:['TEST'],bist100:['TEST'],checkedAt:new Date(NOW).toISOString(),source:'verified fixture'};store.set('indices',old);await c.run('indices');assert.deepEqual(store.get('indices'),old);
 }finally{close();}
});
test('KAP full batch speeds to 5 seconds; empty edge returns to 30 seconds',async()=>{
 const {store,close}=setup();let now=NOW;const source:Source={listing:async()=>[],indices:async()=>{throw Error('unused');},disclosure:async id=>id<=103?item(id):null};
 try{const c=new KapCollector(store,source,()=>now);await c.run('live');assert.equal(store.row<{next_at:number}>("SELECT next_at FROM jobs WHERE name='live'")!.next_at,NOW+5000);now+=5000;await c.run('live');assert.equal(store.row<{next_at:number}>("SELECT next_at FROM jobs WHERE name='live'")!.next_at,now+30000);}finally{close();}
});
test('KAP network errors, protection HTML, redirect and oversize are not interpreted as no news',async()=>{
 for(const response of [new Response('denied',{status:403}),new Response('redirect',{status:302,headers:{location:'https://evil.test'}}),new Response('<html>protection</html>',{headers:{'content-type':'text/html'}}),new Response('huge',{headers:{'content-type':'text/html','content-length':String(17*1024*1024)}})]){const c=new KapClient(async()=>response);await assert.rejects(()=>c.disclosure(101));}
 assert.equal(await new KapClient(async()=>new Response('',{status:404})).disclosure(101),null);
});
test('KAP bootstrap reconciliation does not accelerate the separate silent backfill job',async()=>{
 const {store,close}=setup();let calls=0;const source:Source={listing:async()=>[],indices:async()=>{throw Error('unused');},disclosure:async id=>{calls++;return item(id);}};
 try{await new KapCollector(store,source,()=>NOW).run('reconcile');assert.equal(calls,0);assert.equal(store.health().queue,0);}finally{close();}
});
test('KAP digest and correction IDs persist independently; no title-based event merge',()=>{
 const {store,close}=setup();try{store.configure(pref({funds:'digest'}));const l=store.claim('live',NOW)!;
 store.save(item(101,{title:'Fon Duyurusu',disclosureType:'FON'}),l,NOW,true);store.save(item(102,{title:'Fon Duyurusu',disclosureType:'FON',isChanged:'DUZENLENEN',relatedDisclosureOid:'a'.repeat(32)}),l,NOW,true);
 const rows=store.rows<{kind:string;available_at:number}>('SELECT kind,available_at FROM queue');assert.equal(rows.length,2);assert.equal(rows[0].kind,'digest');assert.equal(rows[0].available_at,digestAt(NOW,'19:00'));assert.equal(store.row<{correction:number}>('SELECT correction FROM disclosures WHERE id=102')!.correction,1);
 }finally{close();}
});
test('KAP unread HTTP response body is covered by the 12 second timeout',async()=>{
 const source=new KapClient(async(_url,init)=>new Response(new ReadableStream({start(controller){init!.signal!.addEventListener('abort',()=>controller.error(new DOMException('aborted','AbortError')),{once:true});}}),{headers:{'content-type':'text/html'}}));
 await assert.rejects(()=>source.disclosure(101),{name:'AbortError'});
});
test('KAP captured public metadata contracts remain valid across five actual disclosure types',()=>{
 for(const kind of ['breaker','fund','buyback','company','finance']){const b=JSON.parse(readFileSync(new URL(`fixtures/kap/${kind}.json`,import.meta.url),'utf8'));const d=parseDisclosure(page(b),b.disclosureIndex);assert.equal(d.id,b.disclosureIndex);assert.ok(d.publishedAt.endsWith('Z'));if(kind==='fund')assert.deepEqual(d.subjectCodes,[]);if(kind==='buyback')assert.equal(classify(d)[0],'buyback');if(kind==='breaker')assert.equal(classify(d)[0],'circuit');}
});
test('KAP older retry cannot starve behind an unending stream of newer discoveries',()=>{
 const {store,close}=setup();try{const lease=store.claim('live',NOW)!;store.gap(101,'error','kap_http_503',lease,NOW);store.run('INSERT INTO discovered VALUES(?,?,?)',102,new Date(NOW+60_000).toISOString(),NOW+60_000);assert.equal(store.nextRepair(NOW+60_000),101);}finally{close();}
});
