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
