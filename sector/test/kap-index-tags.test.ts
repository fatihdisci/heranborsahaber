import test from 'node:test';import assert from 'node:assert/strict';
import {kapIndexMembership,kapIndexHashtags} from '../src/kap/index-tags';
import {repairDraftStyle,styleIssues} from '../src/style';
import {postText} from '../src/editorial';
import type {Indices} from '../src/kap/parser';import type {Document,Draft} from '../src/types';
const now=Date.now(),pool=Array.from({length:98},(_,i)=>'A'+String(i).padStart(4,'0'));
const indices:Indices={bist30:['THYAO',...pool.slice(0,29)],bist100:['THYAO','CVKMD',...pool],checkedAt:new Date(now).toISOString(),source:'https://www.kap.org.tr/tr/Endeksler'};
const doc=(code:string,snapshot=indices):Document=>({source_id:'kap',source_name:'KAP',family:'kap',official:true,url:'https://www.kap.org.tr/tr/Bildirim/123',title:'Yeni İş İlişkisi',body:'Şirket sözleşme imzaladı.',passages:[],published_at:new Date(now).toISOString(),equity_codes:[code],index_membership:kapIndexMembership([code],snapshot,now)});
const draft={headline:'📢 Şirket sözleşme imzaladı',body:'Yeni iş anlaşması açıklandı.',card_headline:'Yeni iş anlaşması',card_body:'Sözleşme imzalandı.',hashtags:['#Borsa','#BIST','#BIST30','#BIST100'],template:'company'} as Draft;
test('verified BIST30 gets both tags, BIST100-only gets one and outside stocks get none',()=>{
 assert.deepEqual(kapIndexHashtags([doc('THYAO')],now),['#BIST30','#BIST100']);assert.deepEqual(kapIndexHashtags([doc('CVKMD')],now),['#BIST100']);assert.deepEqual(kapIndexHashtags([doc('KPEKS')],now),[]);
 const mixed=repairDraftStyle(draft,[doc('THYAO'),doc('CVKMD')]);assert.equal(mixed.hashtags.filter(t=>t==='#BIST100').length,1);assert.equal(mixed.hashtags.filter(t=>t==='#BIST30').length,1);
});
test('stale, future, malformed and unofficial lists do not create index membership',()=>{
 for(const bad of [{...indices,checkedAt:new Date(now-37*3600000).toISOString()},{...indices,checkedAt:'invalid'},{...indices,checkedAt:new Date(now+3600000).toISOString()},{...indices,source:'https://example.com'},{...indices,bist30:indices.bist30.slice(1)}])assert.equal(kapIndexMembership(['THYAO'],bad,now),undefined);
 assert.deepEqual(kapIndexHashtags([{...doc('THYAO'),official:false}],now),[]);assert.deepEqual(kapIndexHashtags([{...doc('THYAO'),source_id:'kap_pdf'}],now),[]);
 assert.deepEqual(kapIndexHashtags([{...doc('THYAO'),equity_codes:['CVKMD']}],now),[]);
 assert.deepEqual(kapIndexHashtags([{...doc('THYAO'),index_membership:undefined,index_tier:30}],now),[]);
 assert.deepEqual(kapIndexHashtags([doc('THYAO')],now+37*3600000),[]);
});
test('repair removes invented index tags and produces one source-backed hashtag line in caption/copy',()=>{
 const docs=[doc('CVKMD')],fixed=repairDraftStyle(draft,docs);assert(!fixed.hashtags.includes('#BIST30'));assert(fixed.hashtags.includes('#BIST100'));assert(styleIssues(draft,docs).includes('unverified_index_hashtag'));
 const text=postText(fixed);assert.equal((text.match(/#BIST100/g)??[]).length,1);assert(!text.includes('#BIST30'));assert(text.endsWith('#BIST100'));assert.deepEqual(repairDraftStyle(fixed,docs),fixed);
 const outside=repairDraftStyle(draft,[doc('KPEKS')]);assert(!outside.hashtags.some(t=>/^#BIST(?:30|100)$/.test(t)));assert(outside.hashtags.includes('#HalkaArz'));
});
