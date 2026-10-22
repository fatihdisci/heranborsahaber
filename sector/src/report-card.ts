import {COLORS,PROFILE_DATA} from './brand';
import type {Draft} from './types';
const esc=(s:string)=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
export function reportCard(d:Pick<Draft,'headline'|'body'|'card_data'>):string{
 if(d.card_data!.report!.general)return generalCard(d.card_data!.report!.general!);
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

function generalCard(g:NonNullable<NonNullable<import('./types').CardData['report']>['general']>):string{
 // Keep readable native glyph sizes; grow the canvas instead of truncating rows.
 const cols=g.rows.length>45?3:g.rows.length>15?2:1,per=Math.ceil(g.rows.length/cols),width=cols*1060+120,height=Math.max(1100,560+per*64);
 const t=(s:string,x:number,y:number,size:number,color=COLORS.paper,anchor='start')=>`<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" fill="${color}">${esc(s)}</text>`;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="${COLORS.navy}"/><g font-family="Noto Sans, sans-serif"><image href="${PROFILE_DATA}" x="60" y="42" width="70" height="70"/>`+t('ENDEKS HABER',152,91,34)+t('PAY GERİ ALIMLARI',60,190,58)+t(g.day+' • '+g.time+' itibarıyla',60,240,28,COLORS.steel);
 const metrics=[['HİSSE',String(g.companies)],['TOPLAM LOT',g.lots],['TOPLAM TUTAR'+(g.missing?' (KISMİ)':''),g.amount+' TL']];
 metrics.forEach(([label,value],i)=>{const x=60+i*(width-120)/3;svg+=t(label,x,304,23,COLORS.steel)+t(value,x,353,36);});
 for(let c=0;c<cols;c++){const x=60+c*1060;svg+=t('HİSSE',x,423,24,COLORS.steel)+t('LOT',x+420,423,24,COLORS.steel,'end')+t('ORT. FİYAT (TL)',x+690,423,24,COLORS.steel,'end')+t('TUTAR (TL)',x+1000,423,24,COLORS.steel,'end');}
 g.rows.forEach((r,i)=>{const c=Math.floor(i/Math.max(1,per)),line=i%Math.max(1,per),x=60+c*1060,y=475+line*64;svg+=`<rect x="${x-12}" y="${y-38}" width="1030" height="60" fill="${COLORS.steel}" opacity="${line%2?'.04':'.1'}"/>`+t('#'+r.ticker,x,y,30)+t(r.lots,x+420,y,28,'#E4E9EC','end')+t(r.price,x+690,y,28,'#E4E9EC','end')+t(r.amount,x+1000,y,28,'#E4E9EC','end');});
 if(!g.rows.length)svg+=t('Doğrulanmış günlük işlem satırı yok.',60,490,32);
 svg+=t('Yalnız KAP pay geri alımı bildirimleri esas alınmıştır. Farklılık gösterebilir.',60,height-82,24,COLORS.steel)+t(g.missing?'Eksik fiyatlar — ile gösterilir. Toplam tutar kısmi olabilir.':'Ortalama fiyat lot ağırlıklıdır. Tutar işlem satırlarından hesaplanmıştır.',60,height-40,24,COLORS.steel);
 return svg+'</g></svg>';
}
