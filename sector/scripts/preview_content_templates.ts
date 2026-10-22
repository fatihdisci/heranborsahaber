// Fictional offline fixtures only; nothing here is ingested or sent to Telegram.
import {mkdir,writeFile} from 'node:fs/promises';
import {cardSvg} from '../src/card';
import {png} from './render_local';
import type {CardData,Template} from '../src/types';
const out='reports/content-templates';await mkdir(out,{recursive:true});
const common={as_of:'22 Ekim 2026 / Seans kapanışı'};
const cases:{name:string;template:Template;headline:string;body:string;card_data?:CardData}[]=[
 {name:'haber',template:'news',headline:'Şirket yeni yatırım programını açıkladı',body:'Üretim kapasitesini artıracak yatırım için izin süreci ve finansman çalışmaları devam ediyor.'},
 {name:'devre-kesici',template:'circuit',headline:'ABCD payında devre kesici uygulandı',body:'İlgili payda tek fiyat emir toplama işlemi başladı.',card_data:{ticker:'ABCD',as_of:'22 Ekim 2026 / 14:32'}},
 {name:'kurum-alim-satim',template:'institutional',headline:'Kurumların en çok aldığı ve sattığı hisseler',body:'Kurumların gün sonu net işlem tutarlarına göre hazırlanan hisse dağılımı.',card_data:{...common,buy:[{label:'ABCD',value:'125.000.000 TL'},{label:'EFGH',value:'92.000.000 TL'},{label:'JKLM',value:'68.000.000 TL'},{label:'MNPR',value:'42.000.000 TL'}],sell:[{label:'STUV',value:'110.000.000 TL'},{label:'WXYZ',value:'83.000.000 TL'},{label:'BCDE',value:'61.000.000 TL'},{label:'FGHJ',value:'38.000.000 TL'}]}},
 {name:'hisse-akd',template:'akd',headline:'ABCD aracı kurum dağılımı',body:'Alıcı ve satıcı tarafındaki net pay miktarları kurum bazında gösteriliyor.',card_data:{...common,ticker:'ABCD',buy:[{label:'Alfa Yatırım',value:'1.250.000 adet'},{label:'Beta Menkul',value:'890.000 adet'},{label:'Gama Yatırım',value:'645.000 adet'}],sell:[{label:'Delta Menkul',value:'1.120.000 adet'},{label:'Epsilon Yatırım',value:'815.000 adet'},{label:'Zeta Menkul',value:'590.000 adet'}]}},
 {name:'hacim',template:'volume',headline:'ABCD işlem hacmi',body:'Günlük hacim ve karşılaştırma verileri aynı dönem kapsamındadır.',card_data:{...common,ticker:'ABCD',metrics:[{label:'GÜNLÜK İŞLEM HACMİ',value:'1,25 milyar TL'},{label:'Önceki seans',value:'980 milyon TL'},{label:'20 seans ortalaması',value:'1,08 milyar TL'}]}}
];
const items:string[]=[];
for(let i=0;i<cases.length*2;i++){
 const sample=cases[i%cases.length],theme=i<cases.length?'navy':'paper',layout=i<cases.length?'editorial':'frame',svg=cardSvg(sample,[],'',false,theme,layout),bytes=await png(svg);
 await writeFile(`${out}/${sample.name}-${theme}.png`,bytes);await writeFile(`${out}/${sample.name}-${theme}.svg`,svg.replace(/[ \t]+$/gm,''));
 const x=(i%3)*360,y=Math.floor(i/3)*470;
 items.push(`<image x="${x}" y="${y}" width="336" height="420" href="data:image/png;base64,${Buffer.from(bytes).toString('base64')}"/><text x="${x+4}" y="${y+445}" font-size="16" fill="#112333">${sample.name} / ${theme}</text>`);
}
await writeFile(`${out}/contact-sheet.png`,await png(`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1880"><rect width="1080" height="1880" fill="#E4E9EC"/><g font-family="Noto Sans">${items.join('')}</g></svg>`));
console.log('Five content families, ten actual PNGs; fictional offline data, no external effects.');
