// Offline, self-contained art kit. Never copy runtime data, credentials or bot code.
import {mkdir,copyFile,writeFile,readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {cardSvg} from '../src/card';
import {png} from './render_local';
import {CARD_LAYOUTS} from '../src/card-layout';
const out=process.argv[2]??'exports/ENDEKS-HABER-ChatGPT';
for(const dir of ['assets','src','runtime','examples'])await mkdir(`${out}/${dir}`,{recursive:true});
for(const file of ['card.ts','market-card.ts','brand.ts','card-layout.ts','card-theme.ts','types.ts'])await copyFile(`src/${file}`,`${out}/src/${file}`);
for(const file of ['NotoSans-Regular.ttf','NotoSans-Bold.ttf','OFL.txt','profile.svg','profile.png','banner.svg','banner.png'])await copyFile(`assets/${file}`,`${out}/assets/${file}`);
for(const file of ['index.mjs','index_bg.wasm','package.json'])await copyFile(`node_modules/@resvg/resvg-wasm/${file}`,`${out}/runtime/${file}`);
execFileSync('node_modules/.bin/esbuild',['src/card.ts','--bundle','--platform=node','--format=esm',`--outfile=${out}/runtime/cards.mjs`]);
await writeFile(`${out}/render.mjs`,String.raw`import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {cardSvg} from './runtime/cards.mjs';
import {initWasm,Resvg} from './runtime/index.mjs';
const base=new URL('./',import.meta.url),input=process.argv[2],output=process.argv[3]??'kart.png';
if(!input)throw Error('Usage: node render.mjs content.json kart.png');
const d=JSON.parse(await readFile(input,'utf8'));
const svg=cardSvg(d,[],'',false,d.theme??'navy',d.layout??'editorial');
await initWasm(await readFile(new URL('runtime/index_bg.wasm',base)));
const fonts=await Promise.all(['Regular','Bold'].map(n=>readFile(new URL('assets/NotoSans-'+n+'.ttf',base))));
const r=new Resvg(svg,{font:{fontBuffers:fonts,defaultFontFamily:'Noto Sans'}});
try{const image=r.render();try{await writeFile(output,image.asPng());await writeFile(output.replace(/\.png$/i,'')+'.svg',svg);}finally{image.free();}}finally{r.free();}
console.log(output);
`);
const samples:any[]=[];
for(const layout of CARD_LAYOUTS)for(const theme of ['navy','paper'])samples.push({name:`haber-${layout}-${theme}`,template:'news',headline:'Şirket yeni yatırım programını açıkladı',body:'Üretim kapasitesini artıracak yatırım için izin ve finansman çalışmaları sürüyor.',theme,layout});
for(const count of [2,24,120])samples.push({name:`devre-kesici-${count}`,template:'circuit',headline:'Devre kesici uygulandı',body:'Sürekli işleme ara verildi.',card_data:{tickers:Array.from({length:count},(_,i)=>'A'+String(i).padStart(4,'0'))}});
samples.push({name:'hisse-akd',template:'akd',headline:'ABCD aracı kurum dağılımı',body:'Net alıcı ve satıcı kurumların pay miktarları.',card_data:{ticker:'ABCD',buy:[{label:'Alfa Yatırım',value:'125.000 lot'}],sell:[{label:'Beta Menkul',value:'110.000 lot'}]}},
{name:'kurum',template:'institutional',headline:'Örnek Kurum üzerinden en çok alınan hisseler',body:'Alım tarafında öne çıkan hisseler.',card_data:{broker:'Örnek Kurum',buy:Array.from({length:10},(_,i)=>({label:'A'+String(i).padStart(4,'0'),value:`${10-i} milyon TL`}))}},
{name:'takas',template:'custody',headline:'ABCD takas dağılımı',body:'Kaynakta yer alan saklama kuruluşlarının payları.',card_data:{ticker:'ABCD',metrics:[{label:'Toplam takas',value:'100 milyon lot'}],holdings:[{label:'Alfa',value:'10 milyon lot / %10'}]}},
{name:'hacim',template:'volume',headline:'ABCD işlem hacmi',body:'Kaynakta açıklanan işlem hacmi.',card_data:{ticker:'ABCD',metrics:[{label:'İŞLEM HACMİ',value:'125 milyon TL'}]}});
for(const s of samples){const {name,...d}=s;await writeFile(`${out}/examples/${name}.json`,JSON.stringify(d,null,2));const svg=cardSvg(d,[],'',false,d.theme,d.layout);await writeFile(`${out}/examples/${name}.svg`,svg);await writeFile(`${out}/examples/${name}.png`,await png(svg));}
await copyFile('docs/chatgpt-kit-prompt.txt',`${out}/CHATGPT-PROMPT.txt`);
await copyFile('docs/chatgpt-kit-readme.txt',`${out}/ONCE-BUNU-OKU.txt`);
await writeFile(`${out}/THIRD-PARTY.txt`,'PNG renderer: @resvg/resvg-wasm 2.6.2, MPL-2.0, https://github.com/yisibl/resvg-js. Original unmodified runtime source is included. Noto Sans: SIL OFL, assets/OFL.txt.\n');
console.log(`Offline kit: ${out}; ${samples.length} rendered PNG examples. Examples are fictional, not current market data.`);
