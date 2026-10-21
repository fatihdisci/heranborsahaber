import {mkdir,writeFile} from 'node:fs/promises';
import {cardSvg} from '../src/card';
import {CARD_LAYOUTS} from '../src/card-layout';
import {png} from './render_local';
const root=process.argv[2]??'outputs/layouts';await mkdir(root,{recursive:true});
const sample={headline:'Türkiye ve Japonya enerji iş birliğini güçlendiriyor',body:'İki ülke, enerji güvenliği ve yeni yatırımlar için ortak çalışma alanlarını genişletmeyi hedefliyor.',template:'company' as const};
let images='';
for(const [i,layout] of CARD_LAYOUTS.entries())for(const [j,theme] of (['navy','paper'] as const).entries()){
 const bytes=await png(cardSvg(sample,[],'',false,theme,layout));await writeFile(`${root}/${layout}-${theme}.png`,bytes);
 images+=`<image x="${(i%3)*360}" y="${(Math.floor(i/3)*2+j)*450}" width="360" height="450" href="data:image/png;base64,${Buffer.from(bytes).toString('base64')}"/>`;
}
await writeFile(`${root}/all.png`,await png(`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1800">${images}</svg>`));

let six='';
for(const [i,layout] of CARD_LAYOUTS.entries()){
 const theme=i%2?'paper':'navy',bytes=await png(cardSvg(sample,[],'',false,theme,layout));
 six+=`<image x="${(i%3)*360}" y="${Math.floor(i/3)*450}" width="360" height="450" href="data:image/png;base64,${Buffer.from(bytes).toString('base64')}"/>`;
}
await writeFile(`${root}/six.png`,await png(`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="900">${six}</svg>`));
