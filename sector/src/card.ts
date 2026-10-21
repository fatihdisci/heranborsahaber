import {PROFILE_DATA} from './brand';
import type {Draft,Template} from './types';
export const COLORS={navy:'#112333',paper:'#E4E9EC',steel:'#8095A4'};
const labels:Record<Template,string>={breaking:'SON DAKİKA',economic_data:'EKONOMİK VERİ',company:'ŞİRKET HABERLERİ',global:'KÜRESEL GÜNDEM',info:'BİLGİ KARTI'};
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
// Deliberately conservative widths for bundled Noto Sans; never truncate a
// number or silently lose an overflow paragraph. Long content needs editing.
export function wrap(text:string,size:number,width:number):string[] {
 const measure=(s:string)=>[...s].reduce((n,c)=>n+(/[MW@%]/.test(c)?.94:/[ilıİ.,:;!' ]/.test(c)?.32:/[A-ZÇĞÖŞÜ0-9]/.test(c)?.69:.59),0)*size;
 const lines:string[]=[];let line='';
 for(const word of text.trim().split(/\s+/)) {
  if(measure(word)>width)throw new Error('card_word_overflow');
  const next=line?line+' '+word:word;
  if(measure(next)>width&&line){lines.push(line);line=word;}else line=next;
 }
 if(line)lines.push(line);return lines;
}
export function draftCard(d:Draft,sources:string[],date:string,demo=false):string {
 return cardSvg({headline:d.card_headline,body:d.card_body,template:d.template},sources,date,demo);
}
export function cardSvg(d:Pick<Draft,'headline'|'body'|'template'>,sources:string[],date:string,demo=false):string {
 const dark=['breaking','global'].includes(d.template),bg=dark?COLORS.navy:COLORS.paper,fg=dark?COLORS.paper:COLORS.navy;
 const headline=d.headline.replace(/^\p{Extended_Pictographic}\uFE0F?\s*/u,'');
 let size=d.template==='info'?66:d.template==='global'?72:76,lines=wrap(headline,size,920);
 while(lines.length>5&&size>52){size-=2;lines=wrap(headline,size,920);}
 if(lines.length>6)throw new Error('card_headline_overflow');
 const headlineBottom=368+lines.length*(size*1.18);
 const bodyLines=wrap(d.body,34,920),available=Math.floor((1100-headlineBottom-52)/48);
 if(bodyLines.length>available)throw new Error('card_body_overflow');
 const text=(values:string[],x:number,y:number,f:number,lineHeight:number,weight=400,color=fg)=>values.map((v,i)=>`<text x="${x}" y="${Math.round(y+i*lineHeight)}" font-size="${f}" font-weight="${weight}" fill="${color}">${esc(v)}</text>`).join('');
 const sourceLines=wrap('KAYNAK: '+[...new Set(sources)].join(' · '),22,920);
 if(sourceLines.length>2)throw new Error('card_sources_overflow');
 return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1350" viewBox="0 0 1080 1350">
 <rect width="1080" height="1350" fill="${bg}"/>
 ${d.template==='economic_data'?`<rect width="1048" height="174" fill="${COLORS.navy}"/>`:''}
 <rect x="1048" width="32" height="1350" fill="${COLORS.steel}"/>
 <image x="68" y="60" width="84" height="84" xlink:href="${PROFILE_DATA}"/>
 <g font-family="Noto Sans"><text x="174" y="116" fill="${d.template==='economic_data'?COLORS.paper:fg}" font-size="31" font-weight="700">SECTOR HABER</text>
 ${d.template==='breaking'?`<rect x="76" y="191" width="284" height="54" fill="${COLORS.paper}"/>`:''}
 <text x="${d.template==='breaking'?94:76}" y="228" fill="${d.template==='breaking'?COLORS.navy:COLORS.steel}" font-size="22" letter-spacing="3">${labels[d.template]}</text>
 <path d="M76 268 H996" stroke="${COLORS.steel}" stroke-width="2"/>
 ${text(lines,76,368,size,size*1.18,700)}
 <rect x="76" y="${headlineBottom+8}" width="76" height="5" fill="${COLORS.steel}"/>
 ${d.template==='global'?`<rect x="28" y="310" width="8" height="${headlineBottom-300}" fill="${COLORS.steel}"/>`:''}
 ${d.template==='economic_data'?`<rect x="54" y="${headlineBottom+36}" width="964" height="${bodyLines.length*48+48}" fill="${COLORS.navy}"/>`:''}
 ${d.template==='info'?`<rect x="54" y="${headlineBottom+36}" width="964" height="${bodyLines.length*48+48}" fill="none" stroke="${COLORS.steel}" stroke-width="2"/>`:''}
 ${text(bodyLines,76,headlineBottom+76,34,48,400,d.template==='economic_data'?COLORS.paper:fg)}
 <path d="M76 1162 H996" stroke="${COLORS.steel}" stroke-width="1"/>
 <g fill="${COLORS.steel}" font-size="22">${sourceLines.map((s,i)=>`<text x="76" y="${1206+i*30}">${esc(s)}</text>`).join('')}
 <text x="76" y="1290">${esc(date)}${demo?' · DENEME':''}</text><text x="996" y="1290" text-anchor="end">@sectorhaber</text></g></g></svg>`;
}
