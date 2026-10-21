import {PROFILE_DATA} from './brand';
import type {Draft} from './types';
export const COLORS={navy:'#112333',paper:'#E4E9EC',steel:'#8095A4'};
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
export function wrap(text:string,size:number,width:number):string[] {
 const measure=(s:string)=>[...s].reduce((n,c)=>n+(/[MW@%]/.test(c)?.94:/[ilıİ.,:;!' ]/.test(c)?.32:/[A-ZÇĞÖŞÜ0-9]/.test(c)?.69:.59),0)*size;
 const lines:string[]=[];let line='';
 for(const word of text.trim().split(/\s+/)) {if(measure(word)>width)throw new Error('card_word_overflow');const next=line?line+' '+word:word;if(measure(next)>width&&line){lines.push(line);line=word;}else line=next;}
 if(line)lines.push(line);
 // Avoid an isolated final word without changing or dropping any source text.
 if(lines.length>1&&lines.at(-1)!.split(' ').length===1){const prev=lines.at(-2)!.split(' ');if(prev.length>2){const tail=prev.at(-1)!+' '+lines.at(-1)!;if(measure(tail)<=width){prev.pop();lines[lines.length-2]=prev.join(' ');lines[lines.length-1]=tail;}}}
 return lines;
}
export function draftCard(d:Draft,sources:string[]=[],date='',demo=false):string {return cardSvg({headline:d.card_headline,body:d.card_body,template:d.template},sources,date,demo);}
// Legacy arguments remain compatible; dates, source lists, handles and demo labels
// are deliberately absent from the artwork. Source access belongs to the button.
export function cardSvg(d:Pick<Draft,'headline'|'body'|'template'>,_sources:string[]=[],_date='',_demo=false):string {
 const dark=d.template==='breaking'||d.template==='global',bg=dark?COLORS.navy:COLORS.paper,fg=dark?COLORS.paper:COLORS.navy;
 const headline=d.headline.replace(/^(?:\p{Extended_Pictographic}\uFE0F?\s*)+/u,'').trim();
 let size=98,lines:string[]=[],bodyLines:string[]=[],bodySize=38,height=0;
 for(;size>=62;size-=2){lines=wrap(headline,size,880);bodyLines=wrap(d.body,bodySize,852);height=lines.length*size*1.14+56+bodyLines.length*bodySize*1.5;if(lines.length<=6&&bodyLines.length<=6&&height<=850)break;}
 if(size<62)throw new Error('card_content_overflow');
 const top=280+Math.max(0,(850-height)*.22),bodyY=top+lines.length*size*1.14+56;
 const text=(values:string[],x:number,y:number,fontSize:number,lineHeight:number,weight:number,color:string)=>values.map((v,i)=>`<text x="${x}" y="${Math.round(y+i*lineHeight)}" font-size="${fontSize}" font-weight="${weight}" fill="${color}">${esc(v)}</text>`).join('');
 return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350">
 <rect width="1080" height="1350" fill="${bg}"/>
 <image x="88" y="74" width="68" height="68" xlink:href="${PROFILE_DATA}"/>
 <g font-family="Noto Sans"><text x="178" y="119" fill="${fg}" font-size="28" font-weight="700" letter-spacing="2">SECTOR HABER</text>
 <path d="M88 182 H992" stroke="${COLORS.steel}" stroke-width="1" opacity=".5"/>
 ${d.template==='breaking'?`<text x="92" y="240" fill="${COLORS.steel}" font-size="21" font-weight="700" letter-spacing="3">SON DAKİKA</text>`:''}
 ${text(lines,88,top+size,size,size*1.14,700,fg)}
 <path d="M92 ${Math.round(bodyY-15)} H148" stroke="${COLORS.steel}" stroke-width="4"/>
 ${text(bodyLines,92,bodyY+bodySize,bodySize,bodySize*1.5,400,dark?COLORS.paper:COLORS.navy)}
 </g></svg>`;
}
