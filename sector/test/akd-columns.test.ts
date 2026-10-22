import test from 'node:test';
import assert from 'node:assert/strict';
import {akdColumns} from '../src/akd-columns';
import {cardSvg} from '../src/card';
import {CARD_LAYOUTS} from '../src/card-layout';
import {png} from '../scripts/render_local';
test('AKD columns preserve explicit ratio, signed lot and currency-free cost',()=>{
 assert.deepEqual(akdColumns({label:'Ünlü',value:'%30,04 · 7.419.604 lot · 4,70'}),{ratio:'%30,04',quantity:'7.419.604',unit:'lot',cost:'4,70'});
 assert.equal(akdColumns({label:'İnfo',value:'%78,89 · -19.488.386 lot · 4,68'})?.quantity,'-19.488.386');
 assert.equal(akdColumns({label:'İnfo',value:'19.488.386 adet'})?.unit,'adet');
 assert.equal(akdColumns({label:'İnfo',value:'19.488.386 TL'}),null);
});
test('AKD tables label each column, omit footer prose and render every theme/layout',async()=>{
 const rows=Array.from({length:5},(_,i)=>({label:['Ünlü','BofA','İş','Yapı Kr.','Ak'][i],value:'%30,04 · 7.419.604 lot · 4,70'}));
 for(const theme of ['navy','paper'] as const)for(const layout of CARD_LAYOUTS){
  const svg=cardSvg({template:'akd',headline:'Gün ortası — KTLEV aracı kurum dağılımı',body:'Sıra: oran · net lot · maliyet. Gereksiz alt açıklama.',card_data:{ticker:'KTLEV',buy:rows,sell:rows}},[],'',false,theme,layout);
  for(const h of ['KURUM','ORAN','NET LOT','MALİYET'])assert(svg.includes('>'+h+'</text>'));
  assert(!svg.includes('Gereksiz'));assert(!svg.includes('Sıra:'));assert(svg.includes('>7.419.604</text>'));assert(svg.includes('>4,70</text>'));
  const bytes=Buffer.from(await png(svg));assert.equal(bytes.readUInt32BE(16),1080);assert.equal(bytes.readUInt32BE(20),1350);
 }
});
