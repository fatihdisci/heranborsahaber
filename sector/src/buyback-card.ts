import {COLORS,PROFILE_DATA} from './brand';
import {reportTextWidth} from './report-text-metrics';
import type {BuybackTable} from './buyback-types';
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
export function buybackLayout(n:number){
 if(!Number.isInteger(n)||n<1||n>200)throw Error('buyback_card_capacity_exceeded');
 const cols=n>80?3:n>20?2:1,per=Math.ceil(n/cols),font=n>100?28:32,rowHeight=n>100?48:58;
 const width=120+cols*1100+(cols-1)*40,height=Math.max(800,450+per*rowHeight+70);
 if(width>4096||height>4096||width*height>16_000_000)throw Error('buyback_card_capacity_exceeded');
 return {width,height,cols,per,font,rowHeight};
}
export function buybackCard(table:BuybackTable):string{
 const {width,height,cols,per,font,rowHeight}=buybackLayout(table.rows.length);
 const t=(value:string,x:number,y:number,size:number,space:number,bold=false,end=false)=>{
  if(reportTextWidth(value,size,bold)>space-8)throw Error('buyback_cell_capacity_exceeded');
  return `<text x="${x}" y="${y}" font-size="${size}"${bold?' font-weight="700"':''}${end?' text-anchor="end"':''}>${esc(value)}</text>`;
 };
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#FFFFFF"/><g font-family="Noto Sans" fill="${COLORS.navy}"><image href="${PROFILE_DATA}" x="60" y="45" width="80" height="80"/>`;
 svg+=t('ENDEKS HABER',168,103,42,width-228,true)+t('PAY GERİ ALIMLARI',60,245,78,width-120,true)+t(table.day.split('-').reverse().join('.'),60,310,34,width-120);
 const columns=[{label:'HİSSE',offset:0,space:170,end:false},{label:'NOMİNAL PAY TUTARI',offset:490,space:320,end:true},{label:'ORT. FİYAT (TL)',offset:755,space:245,end:true},{label:'TOPLAM (TL)',offset:1100,space:325,end:true}];
 for(let c=0;c<cols;c++){const x=60+c*1140;for(const col of columns)svg+=t(col.label,x+col.offset,398,24,col.space,true,col.end);}
 table.rows.forEach((r,i)=>{const c=Math.floor(i/per),line=i%per,x=60+c*1140,y=450+line*rowHeight;
  svg+=`<g data-row="${i}" data-ticker="${r.ticker}"><rect x="${x-10}" y="${y-38}" width="1120" height="${rowHeight-4}" fill="${COLORS.paper}" opacity="${line%2?'.35':'.8'}"/>`;
  const values=['#'+r.ticker,r.nominal??'—',r.price??'—',r.amount??'—'];
  columns.forEach((col,j)=>svg+=t(values[j],x+col.offset,y,font,col.space,j===0,col.end));svg+='</g>';
 });return svg+'</g></svg>';
}
