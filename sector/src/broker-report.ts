import type {Document,Draft} from './types';
export function brokerReport(documents:Document[]):{draft:Draft;documents:Document[]}{
 const doc=documents.find(d=>d.market_data?.kind==='broker_flow');if(!doc)throw Error('bot_query_reply_invalid');
 const passage=doc.passages.find(p=>p.id==='market_units');if(!passage)throw Error('bot_query_units_missing');
 const text=passage.text,buy: {label:string;value:string}[]=[],sell:typeof buy=[];let side:typeof buy|undefined;
 for(const line of text.split('\n')){
  if(/En Çok Net Alış Yapanlar/i.test(line)){side=buy;continue;}
  if(/En Çok Net Satış Yapanlar/i.test(line)){side=sell;continue;}
  const m=line.match(/^\s*(\d+)\.\s+(.+?)\s*→\s*([+-]?[\d.,]+\s+(?:milyon|milyar)\s+TL)\s*$/i);
  if(m&&side&&Number(m[1])<=5)side.push({label:m[2],value:m[3]});
 }
 if(buy.length!==5||sell.length!==5||buy.some(r=>r.value.startsWith('-'))||sell.some(r=>!r.value.startsWith('-')))throw Error('bot_query_table_incomplete');
 const heading='Aracı kurumların net işlem dağılımı';
 const body='Net alıcılar:\n'+buy.map(r=>r.label+': '+r.value).join('\n')+'\n\nNet satıcılar:\n'+sell.map(r=>r.label+': '+r.value).join('\n');
 const draft:Draft={headline:'📢 '+heading,body,hashtags:['Borsa','BIST'],category:'bist',importance:80,template:'broker_flow',card_headline:heading,card_body:'Kurumlar üzerinden gerçekleşen net işlemler',card_data:{buy,sell},claims:[{text:body,evidence:[{document:documents.indexOf(doc),passage:passage.id,quote:text}]}],entities:[],event_key:'broker-'+doc.url,uncertainties:[],source_notes:[]};
 return {draft,documents};
}
