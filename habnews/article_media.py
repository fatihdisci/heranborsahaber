"""Publisher-selected article pictures for the owner's private review, not a reuse license."""
import hashlib,io,json,time,warnings
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image,ImageOps
from .network import Fetcher,host_ok

# Exact publisher/CDN origins observed in real article metadata. Never extend this
# list using a hostname supplied by a page, a model, or a Telegram callback.
ARTICLE_HOSTS={
    'foreks':('www.foreks.com','foreks.com'),
    'bloomberght':('www.bloomberght.com','bloomberght.com'),
    'haberturk':('www.haberturk.com','haberturk.com'),
    'sozcu':('www.sozcu.com.tr','sozcu.com.tr'),
    'tcmb':('www.tcmb.gov.tr','tcmb.gov.tr'),
    'dunya':('www.dunya.com','dunya.com'),
    'ekonomim':('www.ekonomim.com','ekonomim.com'),
    'cnbce':('www.cnbce.com',),
    'ntvpara':('www.ntv.com.tr',),
    'trt-ekonomi':('www.trthaber.com',),
    'aa-ekonomi':('www.aa.com.tr',),
    'euronews-tr':('tr.euronews.com',),
}
ARTICLE_MEDIA_HOSTS={
    'foreks':('news-files.foreks.com',),
    'bloomberght':('geoim.bloomberght.com',),
    'haberturk':('im.haberturk.com',),
    'sozcu':('sozcu01.sozcucdn.com',),
    'tcmb':('www.tcmb.gov.tr','tcmb.gov.tr'),
    'dunya':('image.dunya.com',),
    'ekonomim':('img.ekonomim.com',),
    'cnbce':('img.cnbce.com',),
    'ntvpara':('images.ntv.com.tr',),
    'trt-ekonomi':('trthaberstatic.cdn.wp.trt.com.tr',),
    'aa-ekonomi':('web-cdnprod.aa.com.tr',),
    'euronews-tr':('images.euronews.com',),
}

def allowed_media(sid):return set(ARTICLE_HOSTS.get(sid,()))|set(ARTICLE_MEDIA_HOSTS.get(sid,()))

def media_hosts(sources):
    return {h for s in sources if s['enabled'] for h in allowed_media(s['stable_id'])}

def private_preview(record):
    """A source-bound private preview is deliberately never verified_reusable."""
    if not isinstance(record,dict):return False
    sid=record.get('source_id')
    try:
        page=urlsplit(record.get('landing_page_url',''));asset=urlsplit(record.get('original_asset_url',''))
        return (record.get('delivery_scope')=='private_source_preview' and record.get('rights_status')=='unknown'
            and record.get('restrictions')==['publication_rights_unverified']
            and page.scheme==asset.scheme=='https' and page.username is None and page.password is None and asset.username is None and asset.password is None
            and page.port in (None,443) and asset.port in (None,443)
            and host_ok(page.hostname,ARTICLE_HOSTS.get(sid,()))
            and host_ok(asset.hostname,allowed_media(sid))
            and len(record.get('article_digest',''))==64 and len(record.get('sha256',''))==64
            and bool(record.get('publisher')) and bool(record.get('attribution_text')))
    except (TypeError,ValueError):return False

def article_photo(document,source,directory,guard=lambda:None):
    """Try at most three page-owned candidates, without unrelated image search."""
    sid=source['stable_id'];page=document.get('source_url','')
    if not host_ok(urlsplit(page).hostname,ARTICLE_HOSTS.get(sid,())):return None
    if not source.get('enabled'):return None
    allowed=allowed_media(sid);deadline=time.monotonic()+20
    text=(document['title']+'\n\n' if document['title'] else '')+document['body']
    article_digest=hashlib.sha256(text.encode()).hexdigest()
    candidates=document.get('image_candidates') or ([{'url':document['image_url'],'method':'og:image'}] if document.get('image_url') else [])
    for candidate in candidates[:3]:
        guard()
        remaining=deadline-time.monotonic()
        if remaining<1:break
        asset=candidate['url']
        if not host_ok(urlsplit(asset).hostname,allowed):continue
        try:
            raw,headers,final,_=Fetcher(allowed,guard,timeout=min(6,remaining),max_bytes=10_000_000).get(asset)
            if len(raw)>10_000_000:raise ValueError('article_image_size')
            mime=headers.get('content-type','').split(';')[0].lower()
            if mime not in ('image/jpeg','image/png','image/webp'):raise ValueError('article_image_mime')
            magic=(raw.startswith(b'\xff\xd8\xff') or raw.startswith(b'\x89PNG\r\n\x1a\n') or raw[:4]==b'RIFF' and raw[8:12]==b'WEBP')
            if not magic:raise ValueError('article_image_magic')
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                im=Image.open(io.BytesIO(raw))
                if min(im.size)<240 or max(im.size)/min(im.size)>4 or im.width*im.height>25_000_000 or getattr(im,'n_frames',1)!=1:raise ValueError('article_image_dimensions')
                im.verify();im=Image.open(io.BytesIO(raw));im.load()
            original_size=list(im.size)
            im=ImageOps.exif_transpose(im)
            # Convert formats Telegram sometimes rejects; preserve the whole picture
            # and watermark, strip metadata, and stay inside its photo limits.
            im.thumbnail((2560,2560),Image.Resampling.LANCZOS)
            if im.mode in ('RGBA','LA') or 'transparency' in im.info:
                rgba=im.convert('RGBA');rgb=Image.new('RGB',im.size,'white');rgb.paste(rgba,mask=rgba.getchannel('A'));im=rgb
            else:im=im.convert('RGB')
            buf=io.BytesIO();im.save(buf,format='JPEG',quality=92,optimize=True);blob=buf.getvalue()
            if len(blob)>10_000_000 or sum(im.size)>10000:raise ValueError('telegram_photo_limits')
            guard();sha=hashlib.sha256(blob).hexdigest();now=time.time()
            record={'landing_page_url':page,'original_asset_url':final,'publisher':source['owner'],'creator':'not specified',
                'license_name':'not established','license_version':None,'license_url':page,
                'rights_evidence':'Publisher-selected article image; public availability does not establish republication permission.',
                'attribution_text':'Haber görseli: '+source['owner'],'restrictions':['publication_rights_unverified'],
                'retrieved_at':now,'photographed_at':None,'subject_match':False,'event_match':False,
                'archive_or_current':'unknown','confidence_reason':'Selected by the publisher for this exact article; identities and capture date not independently verified.',
                'rights_status':'unknown','delivery_scope':'private_source_preview','source_id':sid,
                'article_digest':article_digest,'selection_method':candidate.get('method','article'),
                'sha256':sha,'original_sha256':hashlib.sha256(raw).hexdigest(),'mime':'image/jpeg','source_mime':mime,
                'dimensions':list(im.size),'original_dimensions':original_size,'stored_at':now}
            if not private_preview(record):raise ValueError('article_media_binding')
            root=Path(directory).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=True)
            key=hashlib.sha256((page+article_digest).encode()).hexdigest()[:16]
            path=root/('article-'+key+'-'+sha+'.jpg');temp=path.with_suffix('.tmp')
            temp.write_bytes(blob);temp.chmod(0o600);temp.replace(path)
            sidecar=path.with_suffix('.json');sidecar.write_text(json.dumps(record,ensure_ascii=False,indent=2));sidecar.chmod(0o600)
            return {'version':1,'path':str(path),'provenance':record}
        except RuntimeError as exc:
            if str(exc)=='paused':raise
        except (OSError,ValueError,KeyError,Image.DecompressionBombError,Image.DecompressionBombWarning):pass
    return None
