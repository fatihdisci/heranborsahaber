import type {Document,Draft} from './types';
// Repair only a locator, never the quotation or claim. The verbatim quotation
// must already exist in the SAME document; the semantic audit still runs next.
export function repairEvidenceReferences(value:Draft,documents:Document[]):Draft {
 if(!value||!Array.isArray(value.claims))return value;
 return {...value,claims:value.claims.map(claim=>!claim||!Array.isArray(claim.evidence)?claim:{...claim,evidence:claim.evidence.map(e=>{
  if(!e||typeof e.quote!=='string'||e.quote.length<20)return e;
  const doc=documents[e.document];if(!doc||doc.passages.find(p=>p.id===e.passage)?.text.includes(e.quote))return e;
  const match=doc.passages.filter(p=>p.text.includes(e.quote)).sort((a,b)=>a.text.length-b.text.length)[0];
  return match?{...e,passage:match.id}:e;
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
