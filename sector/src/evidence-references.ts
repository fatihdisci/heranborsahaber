import type {Document,Draft} from './types';
// Repair locators and PDF whitespace only, never a claim or factual token.
// Whitespace repairs must map to one unique source span in the SAME document.
function whitespaceSpan(text:string,quote:string):string|null {
 const normalized=quote.replace(/\s+/gu,' ').trim();if(normalized.length<20)return null;
 const chars:string[]=[],starts:number[]=[],ends:number[]=[];
 for(const match of text.matchAll(/\s+|[^\s]/gu)){chars.push(/\s/u.test(match[0])?' ':match[0]);starts.push(match.index!);ends.push(match.index!+match[0].length);}
 const flat=chars.join(''),at=flat.indexOf(normalized);
 if(at<0||flat.indexOf(normalized,at+1)>=0)return null;
 // Array offsets above use Unicode characters; UTF-16 indices need conversion.
 const first=[...flat.slice(0,at)].length,last=first+[...normalized].length-1;
 return text.slice(starts[first],ends[last]);
}
export function repairEvidenceReferences(value:Draft,documents:Document[]):Draft {
 if(!value||!Array.isArray(value.claims))return value;
 return {...value,claims:value.claims.map(claim=>!claim||!Array.isArray(claim.evidence)?claim:{...claim,evidence:claim.evidence.map(e=>{
  if(!e||typeof e.quote!=='string'||e.quote.length<20)return e;
  const doc=documents[e.document];if(!doc||doc.passages.find(p=>p.id===e.passage)?.text.includes(e.quote))return e;
  const match=doc.passages.filter(p=>p.text.includes(e.quote)).sort((a,b)=>a.text.length-b.text.length)[0];
  if(match)return {...e,passage:match.id};
  const candidates=doc.passages.flatMap(p=>{const quote=whitespaceSpan(p.text,e.quote);return quote?[{passage:p.id,quote}]:[];});
  // Prefer a single exact locator; otherwise require an unambiguous passage.
  const selected=candidates.find(c=>c.passage===e.passage)??(candidates.length===1?candidates[0]:null);
  return selected?{...e,...selected}:e;
 })})};
}
export function evidenceIssues(value:Draft,documents:Document[]):string[]{
 const issues:string[]=[];
 for(const [i,claim] of (Array.isArray(value?.claims)?value.claims:[]).entries()){
  for(const e of Array.isArray(claim?.evidence)?claim.evidence:[]){
   const p=documents[e?.document]?.passages.find(p=>p.id===e?.passage);
   if(!p||typeof e.quote!=='string'||e.quote.length<20||!p.text.includes(e.quote)){
    issues.push(`claims[${i}] evidence: document=${e?.document}, passage=${e?.passage}. Alıntı bu pasajda birebir bulunmuyor. Alıntıyı yeniden yazma; kaynak pasajdan aynen kopyala veya iddiayı çıkar. ${p?'Gerçek pasaj: '+p.text.slice(0,4000):'Var olan bir belge/pasaj kimliği kullan.'}`);
   }
  }
 }
 return issues.slice(0,10);
}
