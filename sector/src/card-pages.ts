import {draftCard} from './card';
import {outputView} from './output-preferences';
import type {Draft} from './types';
import type {CardTheme} from './card-theme';
import type {CardLayout} from './card-layout';
export {cardSvg} from './card';
export const MAX_CARDS=4;
export const CARD_CAPACITY_MESSAGE='Seçilen veri okunaklı biçimde dört görsele sığmıyor. Hiçbir satır çıkarılmadı. Kapsamı daraltabilir veya ayrıca thread isteyebilirsin; otomatik thread oluşturulmadı.';
export function balancedPages<T>(rows:readonly T[],capacity:number,pages=Math.max(1,Math.ceil(rows.length/capacity))):T[][]{
 if(!Number.isInteger(capacity)||capacity<1||!Number.isInteger(pages)||pages<1||pages>MAX_CARDS||rows.length>capacity*pages)throw Error('multi_card_capacity_exceeded');
 let start=0;return Array.from({length:pages},(_,i)=>{const n=Math.ceil((rows.length-start)/(pages-i)),part=rows.slice(start,start+n);start+=n;return part;});
}
// The selected immutable source is partitioned, never summarized or truncated.
export function cardPageDrafts(input:Draft):Draft[]{
 const d=structuredClone(outputView(input)),data=d.card_data;if(!data)return [d];
 const fields:{rows:unknown[];capacity:number;set:(page:Draft,rows:any[])=>void}[]=[];
 const add=(rows:unknown[]|undefined,capacity:number,set:(p:Draft,r:any[])=>void)=>{if(rows)fields.push({rows,capacity,set});};
 if(data.report?.buyback)add(data.report.buyback.rows,60,(p,r)=>{p.card_data!.report!.buyback!.rows=r;p.card_data!.report!.buyback!.row_count=r.length;});
 else if(data.report?.general)add(data.report.general.rows,60,(p,r)=>{p.card_data!.report!.general!.rows=r;});
 else if(data.report)add(data.report.rows,15,(p,r)=>{p.card_data!.report!.rows=r;});
 else if(d.template==='circuit')add(data.tickers,36,(p,r)=>{p.card_data!.tickers=r;});
 else {
  const cap=d.template==='institutional'?10:5;
  for(const side of ['buy','sell','holdings'] as const)add(data[side],cap,(p,r)=>{p.card_data![side]=r;});
 }
 const count=Math.max(1,...fields.map(f=>Math.ceil(f.rows.length/f.capacity)));if(count>MAX_CARDS)throw Error('multi_card_capacity_exceeded');
 const parts=fields.map(f=>balancedPages(f.rows,f.capacity,count));
 return Array.from({length:count},(_,i)=>{const page=structuredClone(d);fields.forEach((f,j)=>f.set(page,parts[j][i]));return page;});
}
export function draftCards(d:Draft,theme?:CardTheme,layout:CardLayout='editorial'):string[]{
 const pages=cardPageDrafts(d);
 return pages.map((page,i)=>{
  let svg=draftCard(page,[],'',false,theme,layout);
  if(pages.length>1){const size=/width="(\d+)" height="(\d+)"/.exec(svg);if(!size)throw Error('card_dimensions_missing');const w=Number(size[1]),h=Number(size[2]);svg=svg.replace('</svg>',`<text x="${w-58}" y="${h-24}" text-anchor="end" font-family="Noto Sans" font-size="24" fill="#8095A4">${i+1}/${pages.length}</text></svg>`);}
  return svg;
 });
}
export function cardSvgs(d:Pick<Draft,'headline'|'body'|'template'|'card_data'|'output_preferences'>,theme?:CardTheme,layout:CardLayout='editorial'){
 return draftCards({...d,card_headline:d.headline,card_body:d.body} as Draft,theme,layout);
}
