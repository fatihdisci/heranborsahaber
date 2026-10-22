import {COLORS,PROFILE_DATA} from './brand';
import type {Draft} from './types';
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
export function reportCard(d:Pick<Draft,'headline'|'body'|'card_data'>):string{
 const data=d.card_data!.report!,rows=data.rows.slice(0,30),cols=rows.length>15?2:1,height=Math.min(65,850/Math.ceil(Math.max(1,rows.length)/cols));
 const text=(s:string,x:number,y:number,size:number,color=COLORS.paper)=>`<text x="${x}" y="${y}" font-size="${size}" fill="${color}">${esc(s)}</text>`;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350"><rect width="1080" height="1350" fill="${COLORS.navy}"/><g font-family="Noto Sans, sans-serif"><image href="${PROFILE_DATA}" x="64" y="52" width="64" height="64"/>`+text('ENDEKS HABER',148,94,30)+text(d.headline.replace(/^📢\s*/,''),64,210,40)+text(d.body,64,263,26,COLORS.steel);
 for(let c=0;c<cols;c++){const x=64+c*500;svg+=text('HİSSE',x,310,20,COLORS.steel)+text(d.headline.includes('Devre')?'BİLDİRİM / ENDEKS':'ALIM MİKTARI',x+(cols===2?145:440),310,20,COLORS.steel);}
 rows.forEach((r,i)=>{const col=i%cols,line=Math.floor(i/cols),x=64+col*500,y=350+line*height;svg+=text(r.label,x,y,cols===2?25:31)+text(r.value,x+(cols===2?145:440),y,cols===2?20:30);});
 if(!rows.length)svg+=text('Doğrulanmış günlük işlem satırı yok.',64,380,32);
 if(data.rows.length>rows.length)svg+=text(`Diğer ${data.rows.length-rows.length} hisse rapor sayımına dahildir.`,64,1180,22,COLORS.steel);
 const words=data.footer.split(' '),lines:string[]=[];let line='';for(const w of words){if((line+' '+w).length>73){lines.push(line);line=w;}else line+=(line?' ':'')+w;}if(line)lines.push(line);
 lines.forEach((s,i)=>svg+=text(s,64,1260+i*30,21,COLORS.steel));return svg+'</g></svg>';
}
