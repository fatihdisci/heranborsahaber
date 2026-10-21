import {DatabaseSync} from 'node:sqlite';
import {readFile,writeFile,mkdir,unlink} from 'node:fs/promises';
import {join,resolve,sep} from 'node:path';
// The same repository/pipeline contract used by D1, backed by a separate local
// SQLite database when the always-on Mac is the runtime. Batches are atomic.
export async function localDatabase(path:string,schema:string):Promise<D1Database> {
 const sql=new DatabaseSync(path);sql.exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000; PRAGMA journal_mode=WAL;');
 const application=Number(sql.prepare('PRAGMA application_id').get()!.application_id);
 const tables=sql.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all();
 if(application!==0x53454354&&(application!==0||tables.length))throw new Error('database_namespace_mismatch');
 sql.exec('PRAGMA application_id=1397048148;');sql.exec(schema);
 class Statement {
  args:unknown[]=[];constructor(public text:string){}
  bind(...args:unknown[]){const s=new Statement(this.text);s.args=args;return s;}
  sync(){const r=sql.prepare(this.text).run(...this.args as never[]);return {success:true,meta:{changes:Number(r.changes),last_row_id:Number(r.lastInsertRowid)}};}
  run(){return Promise.resolve(this.sync());}
  first(column?:string){const row=sql.prepare(this.text).get(...this.args as never[]);return Promise.resolve(column?row?.[column]??null:row??null);}
  all(){return Promise.resolve({success:true,results:sql.prepare(this.text).all(...this.args as never[])});}
 }
 return {prepare:(text:string)=>new Statement(text),batch:(statements:Statement[])=>{sql.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.sync());sql.exec('COMMIT');return Promise.resolve(result);}catch(e){sql.exec('ROLLBACK');return Promise.reject(e);}}} as unknown as D1Database;
}
export async function localMedia(directory:string):Promise<R2Bucket> {
 await mkdir(directory,{recursive:true,mode:0o700});
 const path=(key:string)=>{const p=resolve(directory,key);if(!p.startsWith(resolve(directory)+sep))throw new Error('invalid_media_key');return p;};
 return {put:async(key:string,value:Uint8Array)=>{const p=path(key);await mkdir(resolve(p,'..'),{recursive:true,mode:0o700});await writeFile(p,value,{mode:0o600});return {};},get:async(key:string)=>{try{const data=await readFile(path(key));return {arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength)};}catch(e){if((e as NodeJS.ErrnoException).code==='ENOENT')return null;throw e;}},delete:async(key:string)=>{await unlink(path(key)).catch(e=>{if(e.code!=='ENOENT')throw e;});}} as unknown as R2Bucket;
}
