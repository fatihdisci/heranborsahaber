import {test} from 'node:test';
import assert from 'node:assert/strict';
import {withKapUnitEvidence} from '../src/kap-unit-evidence';
import {headlineWithEmoji} from '../src/style';
import type {Document} from '../src/types';
const doc:Document={source_id:'kap',source_name:'KAP',family:'kap',official:true,url:'https://www.kap.org.tr/tr/Bildirim/1685332',title:'Payların Geri Alınmasına İlişkin Bildirim',body:'Borsa İstanbul pay işlemi',published_at:null,equity_codes:['KPEKS'],passages:[{id:'p1',text:'Kendi paylarının nominal tutarı 1.135.381 TL’ye ulaştı. Toplam 750.000.000 TL bütçe, fiyat 48,8533 TL.'}]};
test('BIST nominal quantity converts without converting cash or price and is idempotent',()=>{const [d]=withKapUnitEvidence([doc]);assert.match(d.body,/1.135.381 adet pay/);assert.doesNotMatch(d.body,/750.000.000 adet|48,8533 adet/);assert.deepEqual(withKapUnitEvidence([d]),[d]);assert.deepEqual(d.passages[0],doc.passages[0]);});
test('no unverified fund/private/security conversion',()=>{for(const patch of [{official:false},{source_id:'fund'},{equity_codes:[]},{equity_codes:['ISKUR']},{body:'Özel şirket hisseleri'},{title:'Fon raporu'}]){const d={...doc,...patch};assert.deepEqual(withKapUnitEvidence([d]),[d]);}});
test('building emoji is replaced with the permitted headline emoji',()=>assert.equal(headlineWithEmoji('🏢 KAPEKS pay aldı'),'📢 KAPEKS pay aldı'));

test('table amount preserves its price column',()=>{
 const d={...doc,passages:[{id:'table1row1',text:'İşleme Konu Pay: KPEKS | Payların Nominal Tutarı (TL): 25.000 TL | İşlem Fiyatı (TL/Adet): 48,56 TL'}]};
 const [out]=withKapUnitEvidence([d]);assert.match(out.body,/25.000 adet pay/);assert.doesNotMatch(out.body,/48,56 adet/);
});

import {repairKapShareWording} from '../src/kap-unit-evidence';
import type {Draft} from '../src/types';
test('quantity before nominal wording and general own-share disclosure receive exact equivalences',()=>{
 const text='Gülermak A.Ş. payları ile ilgili olarak 121,99–122 TL fiyat aralığından 400.000 toplam nominal tutarlı alış işlemi gerçekleştirilmiştir.';
 const general={...doc,title:'GÜLERMAK A.Ş. — Özel Durum Açıklaması (Genel)',equity_codes:['GLRMK'],body:text,passages:[{id:'p1',text}]};
 const [out]=withKapUnitEvidence([general]);assert.match(out.body,/400.000 adet pay/);assert.deepEqual(withKapUnitEvidence([out]),[out]);
 const privateDeal={...general,body:text.replace('Gülermak A.Ş. payları','Başka Özel Şirket A.Ş. payları')};
 assert.deepEqual(withKapUnitEvidence([privateDeal]),[privateDeal]);
});
test('tweet, card and claims use verified share count while cash, price and quotes remain intact',()=>{
 const text='Borsa İstanbul’da toplam 40.000 TL nominal değerli PRKME payları geri alınmıştır. Payların toplam nominal değeri 1.800.000 TL olmuştur. Fiyat 12,45 TL, bütçe 500.000.000 TL.';
 const documents=withKapUnitEvidence([{...doc,body:text,passages:[{id:'p1',text}]}]);
 const draft={headline:'Park Elektrik 40.000 TL nominal PRKME payı geri aldı',body:'Payların toplam nominal değeri 1.800.000 TL oldu. Fiyat 12,45 TL, bütçe 500.000.000 TL.',card_headline:'40.000 TL nominal değerli pay geri alındı',card_body:'Payların toplam nominal değeri 1.800.000 TL oldu.',claims:[{text:'40.000 TL nominal değerli PRKME payı alındı.',evidence:[{document:0,passage:'p1',quote:text}]}]} as Draft;
 const fixed=repairKapShareWording(draft,documents);
 for(const field of ['headline','body','card_headline','card_body'] as const)assert.doesNotMatch(fixed[field],/nominal/iu);
 assert.match(fixed.headline,/40.000 adet PRKME payı/);assert.match(fixed.body,/toplam pay adedi 1.800.000/);
 assert.match(fixed.body,/Fiyat 12,45 TL, bütçe 500.000.000 TL/);assert.equal(fixed.claims[0].evidence[0].quote,text);
 assert(fixed.claims[0].evidence.some(e=>e.passage==='p1_units'));assert.deepEqual(repairKapShareWording(fixed,documents),fixed);
 assert.deepEqual(repairKapShareWording(draft,[doc]),draft);
});

test('older conversion passages are augmented once with newly supported wording',()=>{
 const text='Borsa İstanbul’da 40.000 TL nominal değerli KPEKS payı geri alındı. Payların toplam nominal değeri 1.800.000 TL oldu.';
 const old={...doc,body:text,passages:[{id:'p1',text},{id:'bist_units',text:'BIST işlem birimi'},{id:'p1_units',text:text+'\nBIST işlem birimi karşılıkları: 1.800.000 TL nominal pay miktarı = 1.800.000 adet pay'}]};
 const [out]=withKapUnitEvidence([old]);assert.match(out.passages.find(p=>p.id==='p1_units')!.text,/40.000 adet pay/);
 assert.equal(out.passages.filter(p=>p.id==='p1_units').length,1);assert.deepEqual(withKapUnitEvidence([out]),[out]);
});
