// Independent collector only: no bot credentials, Hermes, RSS worker or publication imports.
import {mkdir,readFile,chmod} from 'node:fs/promises';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {KapStore,type Job} from '../src/kap/store';
import {KapClient} from '../src/kap/client';
import {KapCollector} from '../src/kap/collector';
const args=process.argv.slice(2),option=(name:string)=>{const i=args.indexOf(name);return i<0?null:args[i+1];};
const dir=join(homedir(),'Library/Application Support/sector-haber/kap');
await mkdir(dir,{recursive:true,mode:0o700});process.umask(0o077);
const dbPath=option('--db')??join(dir,'kap.sqlite'),store=new KapStore(dbPath),source=new KapClient(),collector=new KapCollector(store,source);
await chmod(dbPath,0o600);
let stopping=false;process.on('SIGTERM',()=>{stopping=true;});process.on('SIGINT',()=>{stopping=true;});
try {
 if(args.includes('--status'))console.log(JSON.stringify(store.health(),null,2));
 else if(args.includes('--preferences')){const path=option('--preferences');if(!path)throw new Error('kap_preferences_file');store.configure(JSON.parse(await readFile(path,'utf8')));console.log('KAP preferences validated and saved. Existing queued items are unchanged.');}
 else if(args.includes('--full-text')){const id=Number(option('--full-text'));console.log(JSON.stringify(await source.fullText(id),null,2));}
 else if(args.includes('--once')){for(const job of ['discovery','indices','live','backfill','reconcile','groups'] as Job[])await collector.run(job);console.log(JSON.stringify(store.health(),null,2));}
 else {const loop=async(job:Job)=>{while(!stopping){await collector.run(job);await new Promise(r=>setTimeout(r,1000));}};await collector.run('discovery');await Promise.all((['discovery','indices','live','backfill','reconcile','groups'] as Job[]).map(loop));}
}finally{store.close();}
