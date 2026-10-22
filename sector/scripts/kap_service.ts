// Independent collector only: no bot credentials, Hermes, RSS worker or publication imports.
import {awaitActivation} from './startup_gate';
import {mkdir,readFile,chmod,open,writeFile,unlink} from 'node:fs/promises';
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
let lock:Awaited<ReturnType<typeof open>>|undefined;
try {
 if(!args.length){
  const path=join(dir,'service.lock');
  try{lock=await open(path,'wx',0o600);}catch(e){
   if((e as NodeJS.ErrnoException).code!=='EEXIST')throw e;
   const pid=Number(await readFile(path,'utf8'));try{process.kill(pid,0);throw Error('kap_service_already_running');}catch(e){if((e as NodeJS.ErrnoException).code!=='ESRCH')throw e;}
   await unlink(path);lock=await open(path,'wx',0o600);
  }
  await lock.writeFile(String(process.pid));
  await writeFile(join(dir,'service-ready.json'),JSON.stringify({pid:process.pid,release:process.env.SECTOR_RELEASE_ID??'',started_at:new Date().toISOString()}),{mode:0o600});
  if(!await awaitActivation(dir,process.env.SECTOR_RELEASE_ID,()=>stopping))stopping=true;
 }
 if(stopping){}
 else if(args.includes('--status'))console.log(JSON.stringify(store.health(),null,2));
 else if(args.includes('--preferences')){const path=option('--preferences');if(!path)throw new Error('kap_preferences_file');store.configure(JSON.parse(await readFile(path,'utf8')));console.log('KAP preferences validated and saved. Disabled circuit notifications are suppressed; source records are preserved.');}
 else if(args.includes('--full-text')){const id=Number(option('--full-text'));console.log(JSON.stringify(await source.fullText(id),null,2));}
 else if(args.includes('--once')){for(const job of ['discovery','indices','live','backfill','reconcile','groups'] as Job[])await collector.run(job);console.log(JSON.stringify(store.health(),null,2));}
 else {const loop=async(job:Job)=>{while(!stopping){await collector.run(job);await new Promise(r=>setTimeout(r,1000));}};await collector.run('discovery');await Promise.all((['discovery','indices','live','backfill','reconcile','groups'] as Job[]).map(loop));}
}finally{if(lock){await lock.close();await unlink(join(dir,'service.lock')).catch(()=>{});}store.close();}
