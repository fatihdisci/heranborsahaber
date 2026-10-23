import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {PassThrough} from 'node:stream';
import {spawn} from 'node:child_process';
import {mkdtemp,mkdir,writeFile,utimes,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import type {ChildProcess} from 'node:child_process';
import {cleanupPdfArtifacts,collectProcessOutput,killProcessTree} from '../scripts/pdf_reader';

class FakeChild extends EventEmitter {
 stdout=new PassThrough();stderr=new PassThrough();kills=0;
 kill(){this.kills++;return true;}
}
const child=()=>new FakeChild() as unknown as ChildProcess&FakeChild;

test('PDF subprocess output limit kills the child tree and fails explicitly',async()=>{
 const c=child(),result=collectProcessOutput(c,1000,4);c.stdout.write('12345');
 await assert.rejects(result,/pdf_output_limit/);assert.equal(c.kills,1);
});
test('PDF subprocess timeout kills the child tree',async()=>{
 const c=child();await assert.rejects(collectProcessOutput(c,5,100),/pdf_timeout/);assert.equal(c.kills,1);
});
test('PDF subprocess spawn errors reject and normal completion preserves output',async()=>{
 const failed=child(),failure=collectProcessOutput(failed,1000,100);failed.emit('error',new Error('spawn failed'));await assert.rejects(failure,/spawn failed/);
 const ok=child(),complete=collectProcessOutput(ok,1000,100);ok.stdout.write('{"ok":true}');ok.stderr.write('diagnostic');ok.emit('close',0);assert.deepEqual(await complete,{code:0,output:'{"ok":true}',error:'diagnostic'});
});
test('PDF timeout cleanup terminates a detached process group',async()=>{
 const real=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{detached:process.platform!=='win32',stdio:'ignore'});
 await new Promise<void>((resolve,reject)=>{real.once('spawn',resolve);real.once('error',reject);});
 try{
  const closed=new Promise<[number|null,NodeJS.Signals|null]>(resolve=>real.once('close',(code,signal)=>resolve([code,signal])));
  killProcessTree(real);const [code,signal]=await Promise.race([closed,new Promise<never>((_,reject)=>setTimeout(()=>reject(Error('process_cleanup_timeout')),3000))]);
  assert.equal(code,null);assert.equal(signal,'SIGKILL');
 }finally{if(real.exitCode===null)killProcessTree(real);}
});
test('PDF cleanup removes expired orphan images but preserves fresh and explicitly active files',async()=>{
 const root=await mkdtemp(join(tmpdir(),'pdf-clean-'));try{
  const orphan=join(root,'sha256','page-1.png'),active=join(root,'active.pdf'),oldActive=join(root,'queued','page-2.png');await mkdir(join(root,'sha256'));await mkdir(join(root,'queued'));await writeFile(orphan,'old');await writeFile(active,'current');await writeFile(oldActive,'active evidence');
  const old=new Date(Date.now()-48*3600_000);await utimes(orphan,old,old);await utimes(oldActive,old,old);
  assert.equal(await cleanupPdfArtifacts(root,Date.now(),24*3600_000,[oldActive]),1);
  await assert.rejects(readFile(orphan));assert.equal(await readFile(active,'utf8'),'current');assert.equal(await readFile(oldActive,'utf8'),'active evidence');
 }finally{await rm(root,{recursive:true,force:true});}
});
