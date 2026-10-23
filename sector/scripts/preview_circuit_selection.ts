// Offline public-cache reconstruction, never a production delivery or original failure snapshot.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import twitter from 'twitter-text';
import {report} from '../src/kap/reports';
import {draftCards} from '../src/card-pages';
import {postText} from '../src/editorial';
import {png} from './render_local';
const fixture=JSON.parse(await readFile('test/fixtures/circuit-report-2026-10-23.json','utf8'));
const out='reports/circuit-selection-preview';await mkdir(out,{recursive:true});
const {draft}=report('circuit',fixture.disclosures.map((disclosure:any)=>({disclosure})),fixture.indices,fixture.at,'Rapor kayıtlı KAP bildirimleriyle sınırlıdır.');
await writeFile(out+'/draft.json',JSON.stringify({provenance:fixture.provenance,...draft},null,2)+'\n');await writeFile(out+'/tweet.txt',postText(draft)+'\n');
const svgs=draftCards(draft),pages=[];
for(let i=0;i<svgs.length;i++){const svg=svgs[i],image=await png(svg),name='devre-kesici-'+(i+1);await writeFile(out+'/'+name+'.svg',svg);await writeFile(out+'/'+name+'.png',image);pages.push({file:name+'.png',rows:(svg.match(/data-report-row=/g)??[]).length,bytes:image.length,sha256:createHash('sha256').update(image).digest('hex')});}
const selection=draft.card_data!.report!.circuit!;
await writeFile(out+'/summary.json',JSON.stringify({provenance:fixture.provenance,total_events:selection.total_events,total_tickers:selection.total_tickers,selected:selection.selected_tickers,omitted:selection.omitted,tweet_weighted_length:twitter.parseTweet(postText(draft)).weightedLength,tweet_style:selection.tweet_style,pages},null,2)+'\n');
console.log(JSON.stringify({out,events:selection.total_events,total:selection.total_tickers,shown:selection.selected_tickers.length,omitted:selection.omitted,tweet_length:twitter.parseTweet(postText(draft)).weightedLength,pages:pages.length}));
