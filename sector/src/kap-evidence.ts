import {withKapTableEvidence} from './kap-table-evidence';
import {KapClient} from './kap/client';
import {ORIGIN,type Disclosure,fullText} from './kap/parser';
import {pdfBytes,boundedBytes} from './pdf-transport';
import type {Document} from './types';
export interface PdfResult {body:string;passages:{id:string;text:string}[];images:string[];coverage:{complete:boolean;page_count:number;pages:unknown[]};}
export async function kapDocuments(id:number,extract:(bytes:Uint8Array,timeout:number)=>Promise<PdfResult>,request:typeof fetch=fetch):Promise<Document[]> {
 const deadline=Date.now()+180_000;
 const page=await new KapClient(request).fullText(id);
 return completeKapDocuments(page,async url=>{
  if(!new RegExp('^https://www\\.kap\\.org\\.tr/tr/api/file/download/[a-f0-9]{32}$','i').test(url))throw Error('kap_attachment_origin');
  const remaining=deadline-Date.now();if(remaining<1000)throw Error('kap_evidence_timeout');
  const r=await request(url,{headers:{Accept:'application/pdf,application/octet-stream'},redirect:'manual',signal:AbortSignal.timeout(Math.min(20_000,remaining))});
  if(!r.ok){await r.body?.cancel();throw Error('kap_attachment_unavailable');}
  const bytes=pdfBytes(await boundedBytes(r));return extract(bytes,Math.max(1000,deadline-Date.now()));
 });
}
export async function completeKapDocuments(page:ReturnType<typeof fullText>,load:(url:string)=>Promise<PdfResult>):Promise<Document[]> {
 const d=page.disclosure;
 if(page.status!=='available'||!page.text?.trim())throw Error('kap_full_text_unavailable');
 if(page.attachmentStatus!=='links_available')throw Error('kap_attachments_incomplete');
 const attachments=page.attachments.filter(a=>a.url.includes('/api/file/download/'));
 if(attachments.length<page.expectedAttachments||attachments.length>20)throw Error('kap_attachments_incomplete');
 const title=[d.company,d.title].filter(Boolean).join(' — ');
 const paragraphs=page.text.split(/\n\s*\n/).filter(Boolean).map((text,i)=>({id:`body${i+1}`,text}));
 const passages=[{id:'metadata',text:[d.company,d.title,d.summary,d.publishedAt,d.subjectCodes.length?'Asıl hisse kodu: '+d.subjectCodes.join(', '):''].filter(Boolean).join('\n')},...paragraphs,...page.tables.map((rows,i)=>({id:`table${i+1}`,text:JSON.stringify(rows)}))];
 const main:Document={source_id:'kap',source_name:'KAP',family:'kap',official:true,url:d.url,title,body:passages.map(p=>p.text).join('\n\n'),passages,published_at:d.publishedAt,language:'tr',equity_codes:d.subjectCodes};
 const docs=[main];
 for(const a of attachments){
  const pdf=await load(a.url);
  if(!pdf.coverage.complete||pdf.coverage.pages.length!==pdf.coverage.page_count||!pdf.body.trim())throw Error('kap_attachment_incomplete');
  docs.push({...main,url:a.url,title:`${d.company??'KAP'} — ${a.label}`,body:pdf.body,passages:pdf.passages,images:pdf.images,coverage:pdf.coverage});
 }
 const prepared=withKapTableEvidence(docs);
 if(prepared.reduce((n,d)=>n+d.body.length,0)>1_000_000||docs.reduce((n,d)=>n+(d.images?.length??0),0)>20)throw Error('kap_evidence_limit');
 return prepared;
}
