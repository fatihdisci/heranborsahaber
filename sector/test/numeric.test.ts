import test from 'node:test';
import assert from 'node:assert/strict';
import {validateDraft,numericTokens,numericIssues} from '../src/editorial';
import type {Draft,Document} from '../src/types';
const base:Draft={headline:'Example yatırım planını duyurdu',body:'Yeni üretim kapasitesi için hazırlıklar sürüyor.',card_headline:'Example yatırım planlıyor',card_body:'Üretim kapasitesinin artırılması hedefleniyor.',hashtags:['#Yatırım','#Şirketler'],entities:['Example'],category:'companies',importance:70,template:'company',event_key:'example-investment',uncertainties:[],claims:[]};
function document(text:string,language='tr'):Document{return {source_id:'official',source_name:'Official',family:'official',official:true,language,url:'https://official.example/a',title:'Example announcement',body:text,published_at:'2026-10-21T00:00:00Z',passages:[{id:'p1',text}]};}
function amount(value:string,doc:Document):Draft{return {...base,headline:`Example ${value} yatırım planlıyor`,claims:[{text:`Example ${value} yatırım planlıyor.`,evidence:[{document:0,passage:'p1',quote:doc.body}]}]};}
test('English decimal/scales map to exact Turkish quantity without floating point',()=>{
 const doc=document('Example plans an investment of $8.5 billion, subject to regulatory approvals.','en');
 assert.doesNotThrow(()=>validateDraft(amount('8,5 milyar dolar',doc),[doc]));
 assert.throws(()=>validateDraft(amount('8,5 milyar euro',doc),[doc]),/unsupported_number/);
});
test('English decimal and thousands separators cannot silently swap magnitudes',()=>{
 const thousand=document('Example plans an investment of 1,234 dollars after approval.','en');
 assert.doesNotThrow(()=>validateDraft(amount('1.234 dolar',thousand),[thousand]));
 const decimal=document('Example plans an investment of 1.234 dollars after approval.','en');
 assert.throws(()=>validateDraft(amount('1.234 dolar',decimal),[decimal]),/unsupported_number/);
});
test('SPK global TL note qualifies table quantities and preserves scales',()=>{
 const doc=document('Example nominal ihraç tavanı 1.000.000.000 olarak onaylandı. Aksi belirtilmedikçe tüm parasal tutarlar TL cinsindendir.');
 assert.doesNotThrow(()=>validateDraft(amount('1 milyar TL',doc),[doc]));
 assert.throws(()=>validateDraft(amount('1 milyon TL',doc),[doc]),/unsupported_number/);
});
test('multiple cited passages jointly support a compound claim',()=>{
 const doc=document('Example üretimi yüzde 3 artırdı. İhracat yüzde 5 yükseldi.');
 doc.passages=[{id:'p1',text:'Example üretimi yüzde 3 artırdı.'},{id:'p2',text:'İhracat yüzde 5 yükseldi.'}];
 const d={...base,headline:'Example üretimi %3 artırdı',claims:[{text:'Üretim %3, ihracat %5 arttı.',evidence:doc.passages.map(p=>({document:0,passage:p.id,quote:p.text}))}]};
 assert.doesNotThrow(()=>validateDraft(d,[doc]));
});

test('price ranges share explicit currency without inventing negative prices',()=>{
 const doc=document('Example işlemleri 1,76 TL - 1,87 TL fiyat aralığındadır.');
 for(const value of ['1,76-1,87 TL','1,76–1,87 TL','1,76 TL–1,87 TL'])assert.doesNotThrow(()=>validateDraft(amount(value,doc),[doc]));
 assert.deepEqual(numericTokens('-1,87 TL zarar'),['-1,87 tl']);
 assert.throws(()=>validateDraft(amount('-1,87 TL',doc),[doc]),/unsupported_number/);
 assert.throws(()=>validateDraft(amount('1,76-1,88 TL',doc),[doc]),/unsupported_number/);
});
test('rounded card quantities remain blocked with actionable preflight feedback',()=>{
 const doc=document('Example toplam 10.493.920 pay geri aldı.');
 const d={...amount('10.493.920',doc),card_body:'Toplam 10,49 milyon pay.'};
 assert.match(numericIssues(d,[doc])[0],/card_body.*10,49 milyon/);
 assert.throws(()=>validateDraft(d,[doc]),/unsupported_number/);
});
test('written calendar ranges do not invent negative day quantities',()=>{
 assert.deepEqual(numericTokens('1 Ocak–30 Eylül 2026'),['1','30','2026']);
 assert.deepEqual(numericTokens('1 Ocak - 30 Eylül 2026'),['1','30','2026']);
 assert.deepEqual(numericTokens('-30 TL zarar'),['-30 tl']);
});
