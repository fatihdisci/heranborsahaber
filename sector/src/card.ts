import {PROFILE_DATA} from './brand';
import type {Draft} from './types';
export const COLORS={navy:'#112333',paper:'#E4E9EC',steel:'#8095A4'};
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const measure=(s:string,size:number)=>[...s].reduce((n,c)=>n+(/[MW@%]/.test(c)?.94:/[ilıİ.,:;!' ]/.test(c)?.32:/[A-ZÇĞÖŞÜ0-9]/.test(c)?.69:.59),0)*size;
export function wrap(text:string,size:number,width:number):string[] {
 const words=text.trim().split(/\s+/).filter(Boolean);if(words.some(w=>measure(w,size)>width))throw new Error('card_word_overflow');
 // Balance all lines, not just the last one. Keep the original words and order.
 const greedy:string[]=[];let line='';
 for(const word of words){const next=line?line+' '+word:word;if(measure(next,size)>width&&line){greedy.push(line);line=word;}else line=next;}
 if(line)greedy.push(line);if(greedy.length<2||greedy.length>10)return greedy;
 const target=measure(words.join(' '),size)/greedy.length;
 const memo=new Map<string,{cost:number;lines:string[]}|null>();
 function solve(start:number,left:number):{cost:number;lines:string[]}|null {
  if(!left)return start===words.length?{cost:0,lines:[]}:null;
  const key=`${start}:${left}`;if(memo.has(key))return memo.get(key)!;
  let best:{cost:number;lines:string[]}|null=null;
  for(let end=start+1;end<=words.length-left+1;end++){
   const value=words.slice(start,end).join(' '),w=measure(value,size);if(w>width)break;
   const tail=solve(end,left-1);if(!tail)continue;
   const cost=(w-target)**2+(end-start===1&&words.length>greedy.length?width**2*.18:0)+tail.cost;
   if(!best||cost<best.cost)best={cost,lines:[value,...tail.lines]};
  }
  memo.set(key,best);return best;
 }
 return solve(0,greedy.length)?.lines??greedy;
}
export function draftCard(d:Draft,sources:string[]=[],date='',demo=false):string {return cardSvg({headline:d.card_headline,body:d.card_body,template:d.template},sources,date,demo);}
// Source access belongs to the Telegram button. Legacy arguments remain accepted.
export function cardSvg(d:Pick<Draft,'headline'|'body'|'template'>,_sources:string[]=[],_date='',_demo=false):string {
 const headline=d.headline.replace(/^(?:\p{Extended_Pictographic}\uFE0F?\s*)+/u,'').trim();
 if(!headline||!d.body.trim())throw new Error('card_content_empty');
 const dark=d.template!=='info'&&d.template!=='economic_data';
 const bg=dark?COLORS.navy:COLORS.paper,fg=dark?COLORS.paper:COLORS.navy;
 const bodySize=36,bodyLines=wrap(d.body,bodySize,848);
 if(bodyLines.length>6)throw new Error('card_content_overflow');
 const bodyHeight=Math.max(290,bodyLines.length*53+114),panelY=1350-bodyHeight;
 const top=d.template==='breaking'?310:270,bottom=panelY-90,available=bottom-top;
 const preferredLines=headline.length>80?5:headline.length>64?4:3;
 let size=108,lines:string[]=[];
 for(;size>=60;size-=2){
  try{lines=wrap(headline,size,920);}catch(e){if(size===60)throw e;continue;}
  if(lines.length<=(size===60?7:preferredLines)&&lines.length*size*1.14<=available)break;
 }
 if(size<60)throw new Error('card_content_overflow');
 const headlineY=top+Math.max(0,(available-lines.length*size*1.14)*.38)+size*.86;
 const text=(values:string[],x:number,y:number,fontSize:number,lineHeight:number,weight:number,color:string)=>values.map((v,i)=>`<text x="${x}" y="${Math.round(y+i*lineHeight)}" font-size="${fontSize}" font-weight="${weight}" fill="${color}">${esc(v)}</text>`).join('');
 // A geometric brand signature, never a chart or a fabricated illustration.
 const signature=`<path d="M815 30 H1060 V106 H891 V160 H1060 V290 H815 V214 H984 V160 H815 Z" fill="${COLORS.steel}" opacity=".10"/>`;
 const panelBg=dark?COLORS.paper:COLORS.navy,panelFg=dark?COLORS.navy:COLORS.paper;
 return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350" role="img" aria-labelledby="card-title">
 <title id="card-title">SECTOR HABER — ${esc(headline)}</title>
 <rect width="1080" height="1350" fill="${bg}"/>
 ${signature}
 <image x="76" y="66" width="80" height="80" xlink:href="${PROFILE_DATA}"/>
 <g font-family="Noto Sans">
 <text x="178" y="107" fill="${fg}" font-size="38" font-weight="700" letter-spacing="1">SECTOR</text>
 <text x="180" y="139" fill="${COLORS.steel}" font-size="22" font-weight="700" letter-spacing="7">HABER</text>
 <path d="M76 192 H1004" stroke="${COLORS.steel}" stroke-width="1" opacity=".45"/>
 <path d="M76 192 H156" stroke="${fg}" stroke-width="5"/>
 ${d.template==='breaking'?`<rect x="76" y="236" width="12" height="12" fill="${COLORS.steel}"/><text x="106" y="251" fill="${fg}" font-size="22" font-weight="700" letter-spacing="3">SON DAKİKA</text>`:''}
 ${text(lines,76,headlineY,size,size*1.14,700,fg)}
 <rect y="${panelY}" width="1080" height="${bodyHeight}" fill="${panelBg}"/>
 <path d="M76 ${panelY} H192" stroke="${COLORS.steel}" stroke-width="8"/>
 <path d="M76 ${panelY+64} V${panelY+bodyHeight-64}" stroke="${COLORS.steel}" stroke-width="2"/>
 ${text(bodyLines,112,panelY+88,bodySize,53,400,panelFg)}
 </g></svg>`;
}
