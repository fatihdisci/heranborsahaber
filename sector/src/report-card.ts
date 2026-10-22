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
 // The header scales with canvas width; only table density changes with count.
 const cols=g.rows.length>45?3:g.rows.length>15?2:1,per=Math.ceil(g.rows.length/cols),width=cols*1060+120,scale=width/2200;
 const rowHeight=g.rows.length>100?52:g.rows.length>45?58:64,headerHeight=420*scale,top=headerHeight+105,height=Math.ceil(Math.max(1100,top+per*rowHeight+150));
 const t=(s:string,x:number,y:number,size:number,color=COLORS.navy,anchor='start')=>`<text x="${x}" y="${y}" text-anchor="${anchor}" font-size="${size}" fill="${color}">${esc(s)}</text>`;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#FFFFFF"/><g font-family="Noto Sans, sans-serif"><g transform="scale(${scale})"><image href="${PROFILE_DATA}" x="60" y="42" width="100" height="100"/><g font-weight="700">`+t('ENDEKS HABER',190,116,58)+t('PAY GERİ ALIMLARI',60,260,96)+'</g>'+t(g.day+' • '+g.time+' itibarıyla',60,314,34);
 const metrics=[['HİSSE',String(g.companies)],['TOPLAM LOT',g.lots],['TOPLAM TUTAR'+(g.missing?' (KISMİ)':''),g.amount+' TL']];
 metrics.forEach(([label,value],i)=>{const x=60+i*2080/3;svg+=t(label,x,375,25)+t(value,x,426,40);});
 svg+='</g>';
 const font=g.rows.length>100?26:28;
 for(let c=0;c<cols;c++){const x=60+c*1060,y=headerHeight+55;svg+=`<g font-weight="700">`+t('HİSSE',x,y,24)+t('LOT',x+420,y,24,COLORS.navy,'end')+t('ORT. FİYAT (TL)',x+690,y,24,COLORS.navy,'end')+t('TUTAR (TL)',x+1000,y,24,COLORS.navy,'end')+'</g>';}
 g.rows.forEach((r,i)=>{const c=Math.floor(i/Math.max(1,per)),line=i%Math.max(1,per),x=60+c*1060,y=top+line*rowHeight;svg+=`<rect x="${x-12}" y="${y-35}" width="1030" height="${rowHeight-4}" fill="${COLORS.navy}" opacity="${line%2?'.025':'.065'}"/>`+t('#'+r.ticker,x,y,font+2)+t(r.lots,x+420,y,font,COLORS.navy,'end')+t(r.price,x+690,y,font,COLORS.navy,'end')+t(r.amount,x+1000,y,font,COLORS.navy,'end');});
 if(!g.rows.length)svg+=t('Doğrulanmış günlük işlem satırı yok.',60,top,32);
 svg+=t('Yalnız KAP pay geri alımı bildirimleri esas alınmıştır. Farklılık gösterebilir.',60,height-82,24)+t(g.missing?'Eksik fiyatlar — ile gösterilir. Toplam tutar kısmi olabilir.':'Ortalama fiyat lot ağırlıklıdır. Tutar işlem satırlarından hesaplanmıştır.',60,height-40,24);
 return svg+'</g></svg>';
}
