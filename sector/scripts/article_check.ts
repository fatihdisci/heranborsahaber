import {readFile,mkdir,writeFile} from 'node:fs/promises';
import registry from '../sources.json';
import type {Source} from '../src/types';
import {parseFeed} from '../src/feed';
import {readPublic} from '../src/network';
import {readDocument} from '../src/article';
await mkdir('reports/articles',{recursive:true});const results=[];
for(const source of registry as Source[]){
 try {
  let xml:string;try{xml=await readFile(`reports/feeds/${source.id}.xml`,'utf8');}catch{xml=(await readPublic(source.url,source.allowed_hosts)).text;}
  const items=parseFeed(xml,source).filter(x=>!x.url.endsWith('.pdf'));
  if(!items.length)throw new Error('no_html_items');
  const doc=await readDocument(items[0],source);
  await writeFile(`reports/articles/${source.id}.json`,JSON.stringify(doc,null,2));
  results.push({id:source.id,status:'ok',title:doc.title,body_chars:doc.body.length,url:doc.url});
 }catch(e){results.push({id:source.id,status:'failed',error:e instanceof Error?e.message:'unknown'});}
 console.log(results.at(-1));
}
await writeFile('reports/article-check.json',JSON.stringify(results,null,2));
