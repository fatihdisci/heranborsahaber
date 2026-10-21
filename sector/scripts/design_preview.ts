import {writeFile,mkdir,readFile} from 'node:fs/promises';
import {cardSvg} from '../src/card';
import {png} from './render_local';
import type {Template} from '../src/types';
await mkdir('outputs',{recursive:true});
// Existing source-checked local examples, never published by this preview script.
const samples=JSON.parse(await readFile('outputs/foreks.result.json','utf8'));
const d=samples.draft;
for(const template of ['breaking','economic_data','company','global','info'] as Template[]){await writeFile(`outputs/updated-${template}.png`,await png(cardSvg({headline:d.card_headline,body:d.card_body,template},[],'',false)));}
console.log(JSON.stringify({headline:d.card_headline,body:d.card_body}));
