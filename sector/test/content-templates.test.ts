import test from 'node:test';
import assert from 'node:assert/strict';
import {cardSvg} from '../src/card';
import {CARD_LAYOUTS} from '../src/card-layout';
import {png} from '../scripts/render_local';
import {validateDraft,numericIssues,documentScore} from '../src/editorial';
import {cardDataFields} from '../src/card-data';
import type {Draft,Document,Template,CardData} from '../src/types';
const text='Alfa Yatırım, ABCD payında 1.250.000 adet net alım yaptı. Beta Menkul 890.000 adet net satış yaptı. İşlem hacmi 125 milyon TL oldu. Veriler 22 Ekim 2026 seansına aittir.';
const doc:Document={source_id:'manual-input',source_name:'Gönderdiğin belge',official:true,family:'test',url:'https://example.test/report',title:'ABCD AKD ve işlem hacmi',body:text,published_at:null,passages:[{id:'p1',text}],equity_codes:['ABCD']};
const base:Draft={headline:'📊 ABCD kurum dağılımı açıklandı',body:'Alfa Yatırım alıcı, Beta Menkul satıcı tarafında yer aldı.',card_headline:'ABCD aracı kurum dağılımı',card_body:'Kurumların net işlem miktarları açıklandı.',hashtags:['#Borsa','#BIST','#ABCD'],entities:['ABCD'],category:'bist',importance:86,template:'akd',event_key:'abcd-akd-22-ekim',uncertainties:[],claims:[{text,evidence:[{document:0,passage:'p1',quote:text}]}]};
const data:CardData={ticker:'ABCD',as_of:'22 Ekim 2026',buy:[{label:'Alfa Yatırım',value:'1.250.000 adet'}],sell:[{label:'Beta Menkul',value:'890.000 adet'}],metrics:[{label:'İşlem hacmi',value:'125 milyon TL'}]};
test('structured figures share numeric, entity and ticker validation with the tweet',()=>{
 assert.doesNotThrow(()=>validateDraft({...base,card_data:data},[doc]));
 assert.throws(()=>validateDraft({...base,card_data:{...data,metrics:[{label:'Hacim',value:'999 milyon TL'}]}},[doc]),/unsupported_number_or_unit/);
 assert.throws(()=>validateDraft({...base,card_data:{...data,metrics:[{label:'Hacim',value:'125 milyon USD'}]}},[doc]),/unsupported_number_or_unit/);
 assert.throws(()=>validateDraft({...base,card_data:{...data,ticker:'ZZZZ'}},[doc]),/unsupported_card_ticker/);
 assert.throws(()=>validateDraft({...base,card_data:{...data,buy:[{label:'Uydurma Kurum',value:'1.250.000 adet'}]}},[doc]),/unsupported_card_entity/);
 assert(numericIssues({...base,card_data:{...data,as_of:'23 Ekim 2026'}},[doc]).some(x=>x.includes('card_data.as_of')));
 assert.throws(()=>validateDraft({...base,card_data:{buy:Array(6).fill(data.buy![0])}},[doc]),/invalid_card_data/);
 assert.doesNotThrow(()=>validateDraft(base,[doc]));
 assert(documentScore({...doc,equity_codes:undefined}).score>=80);
 assert(documentScore({...doc,source_id:'cnbce'},true).score>=80);
 assert.equal(documentScore({...doc,source_id:'cnbce'},false).score,0);
});
test('five content types remain visibly distinct and all redesign layouts render actual PNGs',async()=>{
 const designs=new Set<string>();
 for(const template of ['circuit','news','institutional','akd','volume'] as Template[]){
  for(const theme of ['navy','paper'] as const){
   const layouts=new Set<string>();
   for(const layout of CARD_LAYOUTS){
    const svg=cardSvg({headline:'ABCD payında doğrulanmış gelişme',body:'Kaynak verileriyle hazırlanan kısa açıklama.',template,card_data:template==='news'?undefined:data},[],'',false,theme,layout);
    const b=Buffer.from(await png(svg));assert.equal(b.readUInt32BE(16),1080);assert.equal(b.readUInt32BE(20),1350);
    assert.match(svg,/ENDEKS HABER/);assert(!/linearGradient|radialGradient|filter=/.test(svg));layouts.add(svg);designs.add(svg);
    if(['institutional','akd'].includes(template))assert.match(svg,/1.250.000 adet/);
   }
   assert.equal(layouts.size,6);
  }
 }
 assert.equal(designs.size,60);
});
test('no data yields no invented rows, chart or values, and markup is escaped',()=>{
 for(const template of ['institutional','akd','volume'] as Template[]){const svg=cardSvg({template,headline:'Verili haber',body:'Sadece kaynakta bulunan bilgi.'});assert(!svg.includes('125 milyon'));assert(!svg.includes('Alfa Yatırım'));}
 const svg=cardSvg({template:'akd',headline:'A < B',body:'C & D',card_data:{buy:[{label:'<script>',value:'1 & 2'}]}});
 assert(svg.includes('&lt;script&gt;'));assert(!svg.includes('<script>'));assert(svg.includes('1 &amp; 2'));
 assert(cardDataFields(data).length>5);
});
test('five long institution names fit every AKD redesign without truncating amounts',()=>{
 const rows=Array.from({length:5},(_,i)=>({label:'Uzun Unvanlı Yatırım Menkul Değerler '+String(i+1),value:'1.234.567.890 adet'}));
 for(const layout of CARD_LAYOUTS){const svg=cardSvg({template:'akd',headline:'ABCD aracı kurum dağılımı',body:'Alıcı ve satıcı kurumlar kaynak verilerine göre gösteriliyor.',card_data:{buy:rows,sell:rows}},[],'',false,'navy',layout);assert(svg.includes('1.234.567.890 adet'));}
});
