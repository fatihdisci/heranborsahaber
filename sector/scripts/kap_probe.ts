// Read-only official-source contract check. Does not write a collector DB or any notification.
import {writeFile} from 'node:fs/promises';
import {KapClient} from '../src/kap/client';
import {parseDisclosure,fullText} from '../src/kap/parser';
const source=new KapClient();
const listing=await source.listing(),indices=await source.indices();
const raw=JSON.parse(await source.read('/tr/api/disclosure/list/light','application/json')) as {disclosureIndex:number;subject:string}[];
const selectors={circuit:/Devre Kesici/i,fund:/Portföy Dağılım/i,buyback:/Geri Al/i,company:/Özel Durum/i,financial:/Finansal/i};
const samples=[];
for(const [kind,pattern] of Object.entries(selectors)){
 const candidate=raw.find(r=>pattern.test(r.subject));if(!candidate){samples.push({kind,status:'no_current_example'});continue;}
 const id=candidate.disclosureIndex,html=await source.read(`/tr/Bildirim/${id}`,'text/html'),d=parseDisclosure(html,id),body=fullText(html,id);
 samples.push({kind,status:'verified',id,url:d.url,title:d.title,publishedAt:d.publishedAt,issuerCode:d.issuerCode,relatedCodes:d.relatedCodes,subjectCodes:d.subjectCodes,isFund:d.isFund,htmlBytes:Buffer.byteLength(html),bodyStatus:body.status,bodyCharacters:body.text?.length??0,tableCount:body.tables.length,expectedAttachments:d.attachmentCount,attachmentStatus:body.attachmentStatus,transactionDates:body.transactionDates,boardDecisionDates:body.boardDecisionDates});
}
const report={checkedAt:new Date().toISOString(),discovery:{url:'https://www.kap.org.tr/tr/api/disclosure/list/light',count:listing.length,min:listing[0].id,max:listing.at(-1)!.id},indices:{source:indices.source,checkedAt:indices.checkedAt,bist30:indices.bist30.length,bist100:indices.bist100.length,subset:true},samples,deliveryPerformed:false};
await writeFile('reports/kap-contract.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
