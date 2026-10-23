// Offline fixtures only. No database, model, Telegram or X connection.
import {mkdir,readFile,writeFile} from 'node:fs/promises';import {join,resolve} from 'node:path';import {createHash} from 'node:crypto';
import {draftCards} from '../src/card-pages';import {png} from './render_local';import type {Draft} from '../src/types';
const out=resolve(process.argv[2]??'reports/multi-card-preview');await mkdir(out,{recursive:true});
const raw=JSON.parse(await readFile('test/fixtures/is-buyback/2026-10-23.json','utf8'));
const base={headline:'📊 Kaynak verileri',body:'Kaynağın bütün satırları görsellerde.',card_headline:'Aracı kurum dağılımı',card_body:'Kaynakta yer alan veriler.',hashtags:[],claims:[],uncertainties:[]} as unknown as Draft;
const tableRows=(n:number)=>Array.from({length:n},(_,i)=>({label:'Kurum '+(i+1),value:`%20 · ${100000+i} lot · ${i%3?'4,70':'—'}`}));
const samples:{name:string;draft:Draft;rows:number;origin:string}[]=[
 {name:'geri-alim-54',rows:54,origin:'offline source fixture; not a production report',draft:{...base,template:'info',card_headline:'PAY GERİ ALIMLARI',card_data:{report:{rows:[],footer:'',buyback:{...raw,day:'2026-10-22'}}}}},
 {name:'devre-kesici-60',rows:60,origin:'synthetic daily event fixture',draft:{...base,template:'info',card_headline:'Devre kesici raporu',card_body:'84 bildirim · 60 farklı hisse',card_data:{report:{rows:Array.from({length:60},(_,i)=>({label:'#A'+String(i).padStart(4,'0'),value:(i<24?'2':'1')+' bildirim · BIST 100'})),footer:''}}}},
 {name:'devre-kesici-grup-120',rows:120,origin:'synthetic ticker fixture',draft:{...base,template:'circuit',card_data:{tickers:Array.from({length:120},(_,i)=>'A'+String(i).padStart(4,'0'))}}},
 {name:'akd-17',rows:34,origin:'synthetic numeric fixture',draft:{...base,template:'akd',card_data:{ticker:'ABCD',buy:tableRows(17),sell:tableRows(17)}}},
 {name:'takas-14',rows:14,origin:'synthetic custody fixture',draft:{...base,template:'custody',card_headline:'Takas dağılımı',card_data:{ticker:'ABCD',holdings:Array.from({length:14},(_,i)=>({label:'Saklama Kurumu '+(i+1),value:'123.000 lot · %5'}))}}}
];
const manifest=[];for(const s of samples){const svgs=draftCards(s.draft);for(let i=0;i<svgs.length;i++){const prefix=join(out,s.name+'-'+(i+1)),bytes=await png(svgs[i]);await writeFile(prefix+'.svg',svgs[i].replace(/^[ \t]+$/gm,''));await writeFile(prefix+'.png',bytes);manifest.push({sample:s.name,page:i+1,pages:svgs.length,source_rows:s.rows,origin:s.origin,file:prefix+'.png',sha256:createHash('sha256').update(bytes).digest('hex')});}}
await writeFile(join(out,'manifest.json'),JSON.stringify(manifest,null,2));console.log(JSON.stringify({samples:samples.length,images:manifest.length,output:out}));
