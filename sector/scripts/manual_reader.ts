import {withMarketTiming} from '../src/market-timing';
import {ensureManualStatus,manualStatusId} from '../src/manual-status';
import registry from '../sources.json';
import {readDocument} from '../src/article';
import {safeUrl} from '../src/network';
import {kapDocuments} from '../src/kap-evidence';
import {readPdf} from './pdf_reader';
import {pdfBytes,boundedBytes} from '../src/pdf-transport';
import {telegram,sendDraft} from '../src/telegram';
import {enqueueEvidence} from '../src/ingest';
import {readImage,type ImageEvidence} from './image_reader';
import {withMarketText,marketSelection,selectMarketDocument} from '../src/market-input';
import type {Env,Document,Source} from '../src/types';
async function telegramFile(env:Env,file:{file_id:string;file_size?:number}):Promise<Uint8Array>{
 if(!file?.file_id||(file.file_size!==undefined&&(!Number.isSafeInteger(file.file_size)||file.file_size<0||file.file_size>20_000_000)))throw Error('manual_file_size_limit');
 const result=await telegram(env,'getFile',new URLSearchParams({file_id:file.file_id}));
 const path=String(result.file_path??'');if(!/^[a-zA-Z0-9_./-]+$/.test(path)||path.split('/').includes('..')||path.startsWith('/'))throw Error('telegram_file_path');
 const r=await fetch(`https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${path}`,{redirect:'manual',signal:AbortSignal.timeout(20_000)});
 if(!r.ok){await r.body?.cancel();throw Error('telegram_file_unavailable');}
 return boundedBytes(r);
}
export async function manualDocuments(env:Env,kind:string,input:string,messageId:number,extractImage:(bytes:Uint8Array)=>Promise<ImageEvidence>=readImage):Promise<Document[]> {
 const value=JSON.parse(input) as {url?:string;text:string;submitted_at?:number;origin_bot?:string;focus?:'buy'|'sell'|'both';draft_id?:string;image?:{file_id:string;file_size?:number};document?:{file_id:string;file_name?:string;file_size?:number}};
 if(kind==='url'){
  const u=new URL(value.url!);const kap=u.hostname==='www.kap.org.tr'&&u.pathname.match(/^\/tr\/Bildirim\/(\d+)$/);
  if(kap)return kapDocuments(Number(kap[1]),readPdf);
  const source=(registry as Source[]).find(s=>s.allowed_hosts.includes(u.hostname)&&s.method!=='reference');if(!source)throw Error('manual_source_unsupported');
  const url=safeUrl(u.href,source.allowed_hosts);return [await readDocument({url,title:'',summary:'',published_at:null},source)];
 }
 const sourceUrl=`https://t.me/habernewssbot?start=source_${messageId}`;
 const base={source_id:'manual-input',source_name:'Gönderdiğin belge',family:'owner-submitted',official:false,url:sourceUrl,published_at:null,language:'tr'};
 const selection=(d:Document):Document=>selectMarketDocument(d,value.focus&&['buy','sell','both'].includes(value.focus)?value.focus:undefined);
 if(kind==='market_reuse'){
  const row=await env.DB.prepare('SELECT documents FROM drafts WHERE id=?').bind(value.draft_id).first<{documents:string}>();
  const docs=row?JSON.parse(row.documents) as Document[]:[];
  if(!docs.length||!docs.some(d=>d.market_data||withMarketText(d).market_data))throw Error('manual_market_source_missing');
  return docs.map(d=>selection({...withMarketText(d),url:sourceUrl}));
 }
 if(kind==='image'){
  const evidence=await extractImage(await telegramFile(env,value.image!));
  const caption=marketSelection(value.text)?'':value.text.trim();
  const captionDoc=caption?withMarketText({...base,title:caption.split('\n')[0],body:caption,passages:[{id:'provided_caption',text:caption}]}):undefined;
  const d:Document={...base,...evidence,title:evidence.market_data?.broker?evidence.market_data.broker+' kurum analizi':evidence.market_data?.ticker?evidence.market_data.ticker+' aracı kurum dağılımı':'İlettiğin görsel',source_name:value.origin_bot?'İlettiğin @'+value.origin_bot+' görseli':'İlettiğin görsel',
   ...(evidence.market_data?.ticker?{equity_codes:[evidence.market_data.ticker]}:evidence.market_data?.tickers?{equity_codes:evidence.market_data.tickers}:{}),body:[evidence.body,captionDoc?.market_data?'':caption].filter(Boolean).join('\n\n'),passages:[...evidence.passages,...(caption&&!captionDoc?.market_data?[{id:'provided_caption',text:caption}]:[])]};
  const docs=[selection(d),...(captionDoc?.market_data?[selection(captionDoc)]:[])];const sourceText=docs.flatMap(d=>[d.body,...d.passages.map(p=>p.text)]).join('\n');return docs.map(d=>withMarketTiming(d,value.submitted_at,sourceText));
 }
 if(kind==='pdf'){
  if(!value.document?.file_id||(value.document.file_size??0)>20_000_000)throw Error('pdf_size_limit');
  const pdf=await readPdf(pdfBytes(await telegramFile(env,value.document)));
  return [{...base,title:value.document.file_name??'Gönderilen PDF',...pdf}];
 }
 if(kind==='text'){
  const text=value.text.trim();if(text.length<100||text.length>100_000)throw Error('manual_text_length');
  return [withMarketTiming(selection(withMarketText({...base,source_name:value.origin_bot?'İlettiğin @'+value.origin_bot+' metni':'Gönderdiğin metin',title:text.split('\n')[0].slice(0,180),body:text,passages:[{id:'provided_text',text}]})),value.submitted_at)];
 }
 throw Error('manual_kind');
}
export async function runManual(env:Env):Promise<void> {
 const now=Math.floor(Date.now()/1000);
 const active=await env.DB.prepare("SELECT update_id,message_id FROM manual_requests WHERE state IN ('queued','reading','model_queued') ORDER BY created_at LIMIT 10").all<{update_id:number;message_id:number}>();
 for(const r of active.results??[])await ensureManualStatus(env,r.update_id,r.message_id);
 // The model's output is still subject to all source and uncertainty checks.
 const pending=await env.DB.prepare("SELECT update_id,job_id,message_id FROM manual_requests WHERE state='model_queued'").all<{update_id:number;job_id:string;message_id:number}>();
 for(const row of pending.results??[]){
  const j=await env.DB.prepare('SELECT state,error,result_draft FROM model_jobs WHERE id=?').bind(row.job_id).first<{state:string;error:string|null;result_draft:string|null}>();
  const d=j?.result_draft?await env.DB.prepare('SELECT id,revision,content,documents,media_key,verification,state,delivery_state,message_id FROM drafts WHERE id=?').bind(j.result_draft).first<{id:string;revision:number;content:string;documents:string;media_key:string;verification:string;state:string;delivery_state:string;message_id:number}>():null;
  if(d?.delivery_state==='sent'){
   const statusId=await manualStatusId(env,row.update_id);
   // Reusing an already prepared URL still completes this request's own status.
   if(statusId&&statusId!==d.message_id){
    const image=await env.MEDIA.get(d.media_key);if(!image)throw Error('draft_media_missing');
    await sendDraft(env,d.id,d.revision,JSON.parse(d.content),JSON.parse(d.documents),new Uint8Array(await image.arrayBuffer()),d.verification,statusId);
   }
   await env.DB.prepare("UPDATE manual_requests SET state='complete' WHERE update_id=?").bind(row.update_id).run();
  }
  else if(j?.state==='needs_review'||j?.state==='expired'||d?.state==='needs_review'||['uncertain','failed','suppressed'].includes(d?.delivery_state??''))await env.DB.prepare("UPDATE manual_requests SET state='needs_review',error=? WHERE update_id=?").bind(d?.delivery_state==='uncertain'?'delivery_uncertain':d?.delivery_state==='failed'?'delivery_failed':d?.delivery_state==='suppressed'?'delivery_suppressed':j?.error??'draft_review_required',row.update_id).run();
 }
 const failed=await env.DB.prepare("SELECT update_id,message_id,error FROM manual_requests WHERE state='needs_review' AND notified=0 LIMIT 1").first<{update_id:number;message_id:number;error:string}>();
 if(failed&&env.MODE==='telegram_review'){
  // Claim before sending an error reply; never flood on a delivery timeout.
  await env.DB.prepare('UPDATE manual_requests SET notified=1 WHERE update_id=?').bind(failed.update_id).run();
  const text=failed.error==='delivery_uncertain'?'Tweet ve görsel hazır; teslimatın sonucu belirsiz. Aynı içerik otomatik olarak tekrar gönderilmeyecek.':failed.error==='delivery_failed'?'Tweet ve görsel hazır ancak Telegram teslimatı başarısız oldu. Yeniden AI kullanılmadı.':failed.error==='delivery_suppressed'?'Bu içerik güncel gönderim tercihlerine göre kapatıldı.':failed.error==='model_retry_unavailable'?'Bu içerik için yeniden deneme sınırına ulaşıldı veya mevcut hata güvenli biçimde yeniden denenemiyor. Hazır içerik varsa tekrar oluşturulmaz.':/subscription|hermes|quota|lease_expired/.test(failed.error)?'Kaynağın alındı ancak içerik hazırlama hizmeti şu anda yanıt veremedi. Aynı içeriği yeniden gönderebilirsin.':failed.error.startsWith('image_')?'Görseldeki tabloyu veya metni eksiksiz okuyamadım. Kurum ya da sayı tahmin etmedim. Daha net görseli veya botun metin çıktısını iletebilirsin.':failed.error==='manual_market_focus_unsupported'?'Takas/saklama dağılımından alım-satım sonucu çıkarılamaz. Alım-satım için kurum analizi veya AKD çıktısını iletebilirsin.':failed.error==='manual_source_unsupported'?'Bu siteyi henüz okuyamıyorum. Haberi PDF olarak veya metniyle buraya gönderebilirsin.':'Bu içeriğin tamamını güvenilir biçimde okuyup doğrulayamadım; eksik bilgiden tweet üretmedim. Farklı bir PDF veya tam haber metnini gönderebilirsin.';
  const statusId=await manualStatusId(env,failed.update_id);
  await telegram(env,statusId?'editMessageText':'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text,...(statusId?{message_id:String(statusId)}:{reply_parameters:JSON.stringify({message_id:failed.message_id,allow_sending_without_reply:true})})}));
 }
 const busy=await env.DB.prepare("SELECT COUNT(*) AS n FROM model_jobs WHERE state IN ('queued','leased')").first<{n:number}>();if((busy?.n??0)>=5)return;
 await env.DB.prepare("UPDATE manual_requests SET state='queued' WHERE state='reading' AND lease_until<?").bind(now).run();
 const row=await env.DB.prepare("SELECT * FROM manual_requests WHERE state='queued' AND lease_until<=? ORDER BY created_at LIMIT 1").bind(now).first<{update_id:number;message_id:number;kind:string;input:string;attempts:number}>();if(!row)return;
 const claimed=await env.DB.prepare("UPDATE manual_requests SET state='reading',lease_until=?,attempts=attempts+1 WHERE update_id=? AND state='queued'").bind(now+300,row.update_id).run();if(!claimed.meta.changes)return;
 try{
  const docs=await manualDocuments(env,row.kind,row.input,row.message_id),job=await enqueueEvidence(env,docs,'manual');
  await env.DB.prepare("UPDATE manual_requests SET state='model_queued',job_id=?,lease_until=0,error=NULL WHERE update_id=?").bind(job,row.update_id).run();
 }catch(e){const error=e instanceof Error&&/^[a-z_]{3,70}$/.test(e.message)?e.message:'manual_read_failed';
  const permanent=/unsupported|limit|invalid|model_retry_unavailable|manual_market_row_incomplete|image_market_/.test(error)||row.attempts>=2;
  await env.DB.prepare('UPDATE manual_requests SET state=?,lease_until=?,error=? WHERE update_id=?').bind(permanent?'needs_review':'queued',now+60,error,row.update_id).run();
 }
}
