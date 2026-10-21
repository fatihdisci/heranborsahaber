import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {awaitActivation} from '../scripts/startup_gate';
test('a staged startup cannot consume work before activation; stop aborts the gate',async()=>{
 const root=await mkdtemp(join(tmpdir(),'sector-startup-')),release='a'.repeat(32);let waits=0;
 try{
  assert.equal(await awaitActivation(root,release,()=>false,async()=>{waits++;if(waits===3){await mkdir(`${root}/releases/${release}`,{recursive:true});await writeFile(`${root}/releases/${release}/active`,'');}}),true);
  assert.equal(waits,3);
  let stopping=false;assert.equal(await awaitActivation(root,'b'.repeat(32),()=>stopping,async()=>{stopping=true;}),false);
  await assert.rejects(()=>awaitActivation(root,'../other',()=>false),/invalid_release_id/);
  assert.equal(await awaitActivation(root,undefined,()=>false),true);
 }finally{await rm(root,{recursive:true,force:true});}
});
