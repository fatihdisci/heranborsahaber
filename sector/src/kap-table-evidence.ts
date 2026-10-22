import type {Document} from './types';
// KAP renders units in column headings, not in each cell. Preserve every
// heading and row together; do not apply a table's currency to unrelated text.
export function withKapTableEvidence(documents:Document[]):Document[] {
 return documents.map(doc=>{
  if(doc.source_id!=='kap'||!doc.official)return doc;
  const extra:{id:string;text:string}[]=[];
  for(const p of doc.passages){
   if(!/^(?:page\d+_)?table\d+$/.test(p.id))continue;
   let rows:unknown;try{rows=JSON.parse(p.text);}catch{continue;}
   if(!Array.isArray(rows)||rows.length<2||!rows.every(r=>Array.isArray(r)&&r.every(c=>typeof c==='string')))continue;
   const cells=(rows as string[][]).map(row=>row.map(c=>{
    c=c.replace(/[|\s]+$/g,'').trim();
    // PDF line wrapping may split decimal digits, but separate numbers must
    // never be concatenated. Keep the original table as verbatim evidence.
    if(/^[-+]?\d[\d.,\s]*$/.test(c))c=c.replace(/(?<=[.,])[\t ]*[\r\n]+[\t ]*(?=\d)/g,'');
    return c.replace(/\s+/g,' ');
   }));
   const header=cells[0];if(header.length<2||header.length>30||!header.some(c=>/\((?:TL|USD|EUR|%)(?:\/Adet)?\)/i.test(c)))continue;
   // Only share-quantity PDFs need this new annotation. Expanding every
   // financial-report table would inflate unrelated model evidence payloads.
   if(p.id.startsWith('page')&&(!header.some(c=>/pay/iu.test(c))||!header.some(c=>/nominal/iu.test(c))))continue;
   for(let i=1;i<cells.length;i++){
    if(cells[i].length!==header.length)continue;
    const id=p.id+'row'+i;if(doc.passages.some(p=>p.id===id))continue;
    const text=header.map((h,j)=>{
     const value=cells[i][j],unit=h.match(/\((TL|USD|EUR|%)(?:\/Adet)?\)/i)?.[1];
     const annotated=unit&&/^[-+]?\d+(?:[.,]\d+)*$/.test(value)?(unit==='%'?'%'+value:value+' '+unit.toUpperCase()):value;
     return `${h}: ${annotated||'—'}`;
    }).join(' | ');
    extra.push({id,text});
   }
  }
  return extra.length?{...doc,body:doc.body+'\n\n'+extra.map(p=>p.text).join('\n\n'),passages:[...doc.passages,...extra]}:doc;
 });
}
