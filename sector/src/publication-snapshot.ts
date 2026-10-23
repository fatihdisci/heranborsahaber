import {readMedia,mediaSet,bytesHash} from './media-set';import {sha256} from './utils/text';
import type {Env} from './types';import {postText} from './editorial';
export async function preparePublication(env:Env,id:string,expectedRevision?:number){
 const row=await env.DB.prepare('SELECT revision,content,documents,media_key FROM drafts WHERE id=?').bind(id).first<{revision:number;content:string;documents:string;media_key:string}>();if(!row||expectedRevision!==undefined&&expectedRevision!==row.revision)throw Error('publication_snapshot_revision_mismatch');
 // A legacy manual declaration may outlive its original PNG. Preserve that
 // record with an unknown hash; an incomplete new media set must still fail.
 const available=row.media_key&&env.MEDIA&&(await mediaSet(env,row.media_key,row.content)||await env.MEDIA.get(row.media_key));
 const media=available?await readMedia(env,row.media_key,row.content):null,hashes=media?await Promise.all(media.images.map(bytesHash)):[];
 const hash=hashes.length>1?await sha256(JSON.stringify(hashes)):hashes[0]??null;
 const auditMedia=media&&media.images.length>1?JSON.stringify(media.set!.pages):row.media_key;
 const urls=(JSON.parse(row.documents) as {url:string;equity_codes?:string[]}[]).map(d=>({url:d.url,equity_codes:d.equity_codes??[]}));
 return {...row,media_key:auditMedia,text:postText(JSON.parse(row.content)),urls:JSON.stringify(urls),hash};
}
export function snapshotStatement(env:Env,id:string,method:'manual'|'api',at:number,snap:Awaited<ReturnType<typeof preparePublication>>,remoteUrl?:string){
 return env.DB.prepare(`INSERT OR IGNORE INTO publication_snapshots(id,draft_id,revision,published_at,method,text,content,source_urls,media_key,media_hash,remote_url,created_at) SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE ?='api' OR EXISTS(SELECT 1 FROM publication_marks WHERE draft_id=? AND state='published' AND published_at=?)`).bind(`${method}:${id}:${at}`,id,snap.revision,at,method,snap.text,snap.content,snap.urls,snap.media_key??'',snap.hash,remoteUrl??null,Date.now(),method,id,at);
}
export async function capturePublication(env:Env,id:string,method:'manual'|'api',at:number,remoteUrl?:string,expectedRevision?:number){
 const previous=await env.DB.prepare('SELECT id FROM publication_snapshots WHERE id=?').bind(`${method}:${id}:${at}`).first();if(previous)return;
 const snapshot=await preparePublication(env,id,expectedRevision);await snapshotStatement(env,id,method,at,snapshot,remoteUrl).run();
}
