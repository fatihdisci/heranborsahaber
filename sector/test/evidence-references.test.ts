import test from 'node:test';
import assert from 'node:assert/strict';
import {repairEvidenceReferences,evidenceIssues} from '../src/evidence-references';
import type {Document,Draft} from '../src/types';
const text='Şirket transfer arabalarının üretimi için 765.000 Avro tutarında sözleşme imzaladı.';
const docs=[{body:text,passages:[{id:'body31',text},{id:'body32',text:'İngilizce çeviri bilgilendirme amaçlıdır.'},{id:'table2',text:text+' Teslimat planlanıyor.'}]}] as Document[];
function draft(passage='body32',quote=text){return {claims:[{text:'Sözleşme imzalandı.',evidence:[{document:0,passage,quote}]}]} as Draft;}
test('verbatim quote locator is repaired within same document before audit; facts never change',()=>{
 const original=draft(),fixed=repairEvidenceReferences(original,docs);
 assert.equal(fixed.claims[0].evidence[0].passage,'body31');
 assert.equal(fixed.claims[0].text,original.claims[0].text);
 assert.equal(fixed.claims[0].evidence[0].quote,text);
 assert.equal(original.claims[0].evidence[0].passage,'body32');
 assert.deepEqual(repairEvidenceReferences(fixed,docs),fixed);
});
test('fabricated quote, short fragment, and cross-document match cannot be silently repaired',()=>{
 for(const original of [draft('body32',text.replace('765.000','900.000')),draft('body32','Şirket')])assert.deepEqual(repairEvidenceReferences(original,docs),original);
 const original=draft();original.claims[0].evidence[0].document=1;
 assert.deepEqual(repairEvidenceReferences(original,[...docs,{body:'Other company',passages:[]} as unknown as Document]),original);
 const issues=evidenceIssues(draft('body31',text.replace('Avro','dolar')),docs);
 assert.equal(issues.length,1);assert(issues[0].includes('Gerçek pasaj: '+text));
});
test('PDF whitespace can be mapped back to the verbatim source without changing facts',()=>{
 const source='Şirket    765.000\n  Avro tutarında sözleşme imzaladı.';
 const quote='Şirket 765.000 Avro tutarında sözleşme imzaladı.';
 const documents=[{passages:[{id:'page1',text:source}]}] as Document[];
 const original=draft('page1',quote),fixed=repairEvidenceReferences(original,documents);
 assert.equal(fixed.claims[0].evidence[0].quote,source);assert.equal(fixed.claims[0].text,original.claims[0].text);
 assert.deepEqual(evidenceIssues(fixed,documents),[]);
 for(const changed of [quote.replace('765.000','900.000'),quote.replace('Avro','dolar')])assert.equal(repairEvidenceReferences(draft('page1',changed),documents).claims[0].evidence[0].quote,changed);
 const ambiguous=[{passages:[{id:'a',text:source},{id:'b',text:source}]}] as Document[];
 assert.deepEqual(repairEvidenceReferences(draft('missing',quote),ambiguous),draft('missing',quote));
});
