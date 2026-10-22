// Offline visual fixtures. These illustrative figures never enter live queues.
import {mkdir,writeFile} from 'node:fs/promises';
import {cardSvg} from '../src/card';
import {CARD_LAYOUTS} from '../src/card-layout';
import {png} from './render_local';
import type {Template} from '../src/types';
const root='reports/endeks-previews';await mkdir(root,{recursive:true});
const examples:{name:string;headline:string;body:string;template:Template}[]=[
 {name:'breaking',headline:'TCMB politika faizi kararını açıkladı',body:'Kararın ayrıntıları ve para politikası değerlendirmesi resmî açıklamayla paylaşıldı.',template:'breaking'},
 {name:'circuit',headline:'ABCD payında devre kesici uygulandı',body:'İlgili payda tek fiyat emir toplama işlemi başladı.',template:'circuit'},
 {name:'kap',headline:'Örnek Sanayi yeni iş sözleşmesini duyurdu',body:'Üretim ve teslimat koşulları KAP açıklamasıyla yatırımcılara bildirildi.',template:'kap'},
 {name:'company',headline:'Örnek Holding finansal sonuçlarını açıkladı',body:'Döneme ilişkin gelir tablosu ve bilanço verileri yayımlandı.',template:'company'},
 {name:'market',headline:'BIST 100 günü %1,25 yükselişle tamamladı',body:'Endeks 10.250,35 puandan kapandı. İşlem hacmi 98,4 milyar TL oldu.',template:'market'},
 {name:'finance',headline:'Enflasyon verisinin ayrıntıları belli oldu',body:'Aylık ve yıllık değişimler resmî istatistik bülteninde paylaşıldı.',template:'finance'},
 {name:'info',headline:'Temettü verimi nasıl hesaplanır?',body:'Pay başına temettünün hisse fiyatına oranıdır. Nakit tutar ile oran farklı göstergelerdir.',template:'info'}
];
const thumbs:string[]=[];
for(let i=0;i<12;i++){
 const sample=examples[i%examples.length],theme=i<6?'navy':'paper',layout=CARD_LAYOUTS[i%6];
 const svg=cardSvg(sample,[],'',false,theme,layout),bytes=await png(svg),name=`${String(i+1).padStart(2,'0')}-${sample.name}-${layout}-${theme}`;
 await writeFile(`${root}/${name}.svg`,svg.replace(/[ \t]+$/gm,''));await writeFile(`${root}/${name}.png`,bytes);
 const x=(i%3)*360,y=Math.floor(i/3)*470;
 thumbs.push(`<image x="${x}" y="${y}" width="336" height="420" href="data:image/png;base64,${Buffer.from(bytes).toString('base64')}"/><text x="${x+8}" y="${y+445}" font-size="16" fill="#112333">${layout} / ${theme}</text>`);
}
await writeFile(`${root}/contact-sheet.png`,await png(`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1880"><rect width="1080" height="1880" fill="#E4E9EC"/><g font-family="Noto Sans">${thumbs.join('')}</g></svg>`));
console.log('12 PNG cards: all six layouts and both themes; seven content types. Offline illustrative fixtures.');
