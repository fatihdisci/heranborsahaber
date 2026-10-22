import {COLORS,PROFILE_DATA,BRAND_NAME,MARK_PATH} from './brand';
import {CARD_LAYOUTS,type CardLayout} from './card-layout';
import type {CardTheme} from './card-theme';
import type {Draft,CardRow} from './types';
type Box={x:number;y:number;width:number;height:number;size:number;min:number;weight:number;color:string;align?:'center'};
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
// Each content family owns its hierarchy. Layout changes alter frame, rail,
// header or alignment while retaining the same evidence and financial values.
export function marketCard(d:Pick<Draft,'headline'|'body'|'template'|'card_data'>,theme:CardTheme,layout:CardLayout,fit:(s:string,b:Box)=>string):string {
 if(d.template==='circuit')return circuitCard(theme,layout);
 const bg=COLORS[theme],fg=theme==='navy'?COLORS.paper:COLORS.navy,steel=COLORS.steel;
 const data=d.card_data,variant=CARD_LAYOUTS.indexOf(layout),left=layout==='rail'?122:76,width=1080-left-76;
 const rect=(x:number,y:number,w:number,h:number,fill:string,stroke?:string)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}"${stroke?` stroke="${stroke}" stroke-width="2"`:''}/>`;
 const text=(s:string,x:number,y:number,size:number,color=fg,weight=400,anchor='start')=>`<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(s)}</text>`;
 const rule=(y:number)=>`<path d="M${left} ${y} H1004" stroke="${steel}" stroke-width="1"/>`;
 const block=(s:string,x:number,y:number,w:number,h:number,size:number=40,color=fg,min=26,weight=400,align?:'center')=>fit(s,{x,y,width:w,height:h,size,min,weight,color,align});
 const labels:{[key:string]:string}={circuit:'DEVRE KESİCİ',institutional:'KURUM ALIM / SATIM',akd:'HİSSE / AKD',volume:'İŞLEM HACMİ',broker_flow:'ARACI KURUM / NET İŞLEM',custody:'TAKAS / SAKLAMA'};
 const inverse=layout==='brief'||layout==='masthead';
 let art=layout==='frame'?rect(34,34,1012,1282,'none',steel):layout==='rail'?rect(0,0,38,1350,fg)+rect(38,0,6,1350,steel):'';
 if(inverse)art+=rect(0,0,1080,180,fg);
 art+=`<image x="${left}" y="58" width="68" height="68" href="${PROFILE_DATA}"/>`+text('ENDEKS',left+90,88,30,inverse?bg:fg,700)+text('H A B E R',left+92,116,17,steel,700)+text(labels[d.template],1004,102,22,inverse?bg:steel,700,'end');
 art+=rule(182);
 if(data?.as_of)art+=text(data.as_of,left,222,24,steel);
 const centered=layout==='center',align=centered?'center' as const:undefined;
 const separateTicker=data?.ticker&&!d.headline.includes(data.ticker);
 if(d.template==='volume'){
  art+=block(d.headline,left,276,width,200,65,fg,42,700,align);
  if(separateTicker)art+=text(data!.ticker!,1004,505,32,steel,700,'end');
  const hero=data?.metrics?.[0];
  if(hero){art+=text(hero.label,left,557,27,steel,700)+block(hero.value,left,592,width,180,114,fg,60,700);}
  else art+=`<path d="${MARK_PATH}" transform="translate(380 500) scale(.75)" fill="${steel}" opacity=".20"/>`;
  let y=836;for(const row of data?.metrics?.slice(1,3)??[]){art+=rule(y-20)+text(row.label,left,y+16,27,steel)+text(row.value,1004,y+22,36,fg,700,'end');y+=110;}
  art+=rule(1110)+block(d.body,left,1150,width,150,32,fg,26);
 }else if(d.template==='custody'){
  art+=block(d.headline,left,268,width,155,61,fg,38,700,align);
  if(separateTicker)art+=text(data!.ticker!,1004,455,32,steel,700,'end');
  const hero=data?.metrics?.[0];
  if(hero)art+=text(hero.label,left,500,26,steel,700)+block(hero.value,left,530,width,120,78,fg,44,700);
  if(data?.holdings?.length){
   art+=rect(left,710,width,440,fg)+text('SAKLAMA KURULUŞLARI',left+28,755,25,bg,700);
   data.holdings.forEach((r,i)=>{const y=778+i*70;art+=block(r.label,left+28,y,width*.40,60,29,bg,20,700)+block(r.value,left+width*.45,y,width*.55-28,60,28,bg,18);});
   art+=block(d.body,left,1190,width,110,29,fg,22);
  }else art+=block(d.body,left,735,width,430,45,fg,28);
 }else if(['akd','broker_flow'].includes(d.template)&&(data?.buy?.length||data?.sell?.length)){
  art+=block(d.headline,left,268,width,155,61,fg,38,700,align);
  if(separateTicker)art+=text(data.ticker!,1004,446,32,steel,700,'end');
  const table=(title:string,rows:CardRow[]|undefined,y:number,invert:boolean)=>{
   if(!rows?.length)return '';
   const ink=invert?bg:fg;let svg=rect(left,y,width,310,invert?fg:bg,invert?undefined:steel)+text(title,left+28,y+46,25,invert?bg:steel,700);
   rows.forEach((row,i)=>{const top=y+69+i*46;svg+=block(row.label,left+28,top,width-360,46,30,ink,18,700)+block(row.value,1004-300,top,272,46,30,ink,18);});
   return svg;
  };
  art+=table(d.template==='broker_flow'?'NET ALICI KURUMLAR':'ALICI KURUMLAR',data.buy,480,layout!=='masthead')+table(d.template==='broker_flow'?'NET SATICI KURUMLAR':'SATICI KURUMLAR',data.sell,836,layout==='masthead');
  art+=block(d.body,left,1190,width,105,30,fg,22);
 }else{
  art+=block(d.headline,left,268,width,192,61,fg,38,700,align);
  if(data?.ticker)art+=text(data.ticker,1004,486,34,fg,700,'end');
  const gap=26,col=(width-gap)/2,start=535;
  const panel=(title:string,rows:CardRow[]|undefined,x:number,invert:boolean)=>{
   if(!rows?.length)return '';
   const ink=invert?bg:fg,paper=invert?fg:bg;
   let svg=rect(x,start,col,530,paper,invert?undefined:steel)+text(title,x+25,start+47,25,invert?bg:steel,700);
   for(let i=0;i<rows.length;i++){
    const y=start+82+i*85;
    svg+=block(rows[i].label,x+25,y,col-50,38,d.template==='akd'?28:35,ink,23,700);
    svg+=block(rows[i].value,x+25,y+40,col-50,38,30,ink,22);
   }
   return svg;
  };
  if(data?.buy?.length||data?.sell?.length){art+=panel(d.template==='akd'?'ALICI KURUMLAR':'EN ÇOK ALINAN',data.buy,left,layout!=='masthead');art+=panel(d.template==='akd'?'SATICI KURUMLAR':'EN ÇOK SATILAN',data.sell,left+col+gap,layout==='masthead');}
  else art+=block(d.body,left,586,width,420,48,fg,32);
  if(data?.buy?.length||data?.sell?.length)art+=rule(1120)+block(d.body,left,1160,width,150,31,fg,25);
 }
 // A visible footer mark differentiates frame variants without invented charts.
 art+=`<path d="M${left} 1308 H${left+56+variant*22}" stroke="${steel}" stroke-width="${layout==='brief'?7:3}"/>`;
 return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350" role="img"><title>${BRAND_NAME} — ${esc(d.headline)}</title>${rect(0,0,1080,1350,bg)}<g font-family="Noto Sans">${art}</g></svg>`;
}
// A circuit batch has one visual signal. Tickers and official facts belong in
// the caption, so neither model text nor card_data can leak onto this artwork.
function circuitCard(theme:CardTheme,layout:CardLayout):string {
 const bg=COLORS[theme],ink=theme==='navy'?COLORS.paper:COLORS.navy,steel=COLORS.steel;
 const centered=layout==='center',x=centered?540:layout==='rail'?130:80,anchor=centered?'middle':'start';
 const panel=layout==='brief'||layout==='masthead',fg=panel?bg:ink;
 const frame=layout==='frame'?`<rect x="32" y="32" width="1016" height="1286" fill="none" stroke="${steel}" stroke-width="2"/>`:layout==='rail'?`<rect width="24" height="1350" fill="${ink}"/><rect x="24" width="6" height="1350" fill="${steel}"/>`:'';
 const y=layout==='brief'?570:layout==='masthead'?620:centered?625:600;
 return `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" role="img"><title>${BRAND_NAME} — DEVRE KESİCİ</title>
 <rect width="1080" height="1350" fill="${bg}"/>${frame}
 <image x="80" y="66" width="76" height="76" href="${PROFILE_DATA}"/>
 <g font-family="Noto Sans"><text x="178" y="103" font-size="36" font-weight="700" fill="${ink}">ENDEKS</text><text x="180" y="136" font-size="20" font-weight="700" letter-spacing="6" fill="${steel}">HABER</text>
 <path d="M80 192 H1000" stroke="${steel}" stroke-width="1"/>
 ${panel?`<rect x="48" y="330" width="984" height="660" fill="${ink}"/>`:''}
 <path d="M${centered?474:x} ${y-200} h132" stroke="${steel}" stroke-width="12"/>
 <text x="${x}" y="${y}" font-size="184" font-weight="700" letter-spacing="-6" text-anchor="${anchor}" fill="${fg}">DEVRE</text>
 <text x="${x}" y="${y+205}" font-size="184" font-weight="700" letter-spacing="-6" text-anchor="${anchor}" fill="${fg}">KESİCİ</text>
 <path d="M80 1200 H1000" stroke="${steel}" stroke-width="1"/><path d="M80 1200 H${240+CARD_LAYOUTS.indexOf(layout)*28}" stroke="${ink}" stroke-width="6"/>
 </g></svg>`;
}
