import {access} from 'node:fs/promises';
// A staged service reports local readiness before consuming updates or sending
// anything. The installer activates it only after a stable startup check.
export async function awaitActivation(root:string,release:string|undefined,stopping:()=>boolean,pause=(ms:number)=>new Promise<void>(r=>setTimeout(r,ms))):Promise<boolean>{
 if(!release)return !stopping();
 if(!/^[a-f0-9]{32}$/.test(release))throw Error('invalid_release_id');
 while(!stopping()){
  try{await access(`${root}/releases/${release}/active`);return true;}
  catch(e){if((e as NodeJS.ErrnoException).code!=='ENOENT')throw e;}
  await pause(200);
 }
 return false;
}
