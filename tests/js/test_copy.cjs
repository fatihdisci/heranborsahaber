// Run with node --test tests/js/test_copy.cjs; no browser or network needed.
const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const zlib=require('node:zlib');
const crypto=require('node:crypto');
const script=fs.readFileSync('docs/gpt/copy.js','utf8');
function context({denied=false,legacy=false}={}) {
 const elements=new Map();
 const doc={getElementById(id) {if(!elements.has(id))elements.set(id,{value:'',hidden:true,disabled:true,textContent:'',closest:()=>({open:false}),focus(){},select(){},setSelectionRange(){}});return elements.get(id);},
 execCommand(){if(denied)throw Error('SecurityError');return true;}};
 let copied;
 const ctx=vm.createContext({document:doc,navigator:{clipboard:{async writeText(text){if(denied)throw Error('NotAllowedError');copied=text;}}},
 window:{isSecureContext:!legacy,addEventListener(){}},location:{hash:'',pathname:'/gpt/'},history:{replaceState(){}},
 Blob,DecompressionStream,Uint8Array,TextEncoder,crypto:crypto.webcrypto,atob});
 vm.runInContext(script,ctx);
 return {ctx,elements,readCopied:()=>copied};
}
test('Unicode payload including emoji is verified and copied byte-for-byte',async()=>{
 const {ctx,readCopied}=context();
 const prompt='📢 Çok hisseli haber\nŞirket A: 510 milyon TL.\nŞirket B: 2,5 milyar TL.\nİzne tabidir. 🚨';
 const data={v:1,prompt,title:'Hisseler 📊',chars:[...prompt].length,sha256:crypto.createHash('sha256').update(prompt).digest('hex')};
 ctx.fragment='#v1.'+zlib.gzipSync(JSON.stringify(data)).toString('base64url');
 const result=await vm.runInContext('decodePayload(fragment)',ctx);
 assert.equal(result.prompt,prompt);
 ctx.document.getElementById('text').value=result.prompt;
 assert.equal(await vm.runInContext('copyPrompt()',ctx),true);
 assert.equal(readCopied(),prompt);
});
test('denied clipboard and throwing legacy copy leave text accessible',async()=>{
 const {ctx,elements}=context({denied:true});
 ctx.document.getElementById('text').value='Prompt ve haberin tüm metni.';
 assert.equal(await vm.runInContext('copyPrompt()',ctx),false);
 assert.equal(elements.get('text').value,'Prompt ve haberin tüm metni.');
 assert.match(elements.get('status').textContent,/Panoya erişilemedi/);
});
test('legacy user-gesture copy still works',async()=>{
 const {ctx}=context({legacy:true});
 assert.equal(await vm.runInContext('copyPrompt()',ctx),true);
});
test('corrupted export cannot be copied as verified content',async()=>{
 const {ctx}=context();
 const data={v:1,prompt:'Haber',title:'Başlık',chars:5,sha256:'0'.repeat(64)};
 ctx.fragment='#v1.'+zlib.gzipSync(JSON.stringify(data)).toString('base64url');
 await assert.rejects(vm.runInContext('decodePayload(fragment)',ctx),/doğrulanamadı/);
});
