import hashlib, io, json, time, warnings
from pathlib import Path
from PIL import Image
from .network import Fetcher

Image.MAX_IMAGE_PIXELS=25_000_000
FIELDS={'landing_page_url','original_asset_url','publisher','creator','license_name','license_version','license_url','rights_evidence','attribution_text','restrictions','retrieved_at','photographed_at','subject_match','event_match','archive_or_current','confidence_reason','rights_status'}

def reusable(record):
    if not isinstance(record,dict):return False
    if any(not isinstance(record.get(k),str) or not record[k] for k in ('landing_page_url','original_asset_url','publisher','creator','license_name','license_url','rights_evidence','attribution_text')):return False
    official=(record.get('publisher')=='TCMB' and record.get('license_name')=='TCMB official Flickr reuse'
        and record.get('license_url')=='https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Sosyal+Medya'
        and record.get('landing_page_url')=='https://www.flickr.com/photos/merkez_bankasi/55462088240/'
        and record.get('original_asset_url')=='https://live.staticflickr.com/65535/55462088240_2fb7910355_b.jpg')
    return (FIELDS.issubset(record) and record['rights_status']=='verified_reusable' and record['subject_match'] is True
        and bool(record['rights_evidence']) and bool(record['creator']) and bool(record['attribution_text'])
        and (record['license_name'] in ('CC BY','CC BY-SA','CC0','Public domain') or official)
        and not record['restrictions'] and (record['event_match'] is True or record['archive_or_current']=='archive'))

def matched_official_archive(subject, directory, guard=lambda:None,article_body=''):
    """Institutional context from audited source metadata; never face identification."""
    import re
    named=bool(re.search(r'\b(?:Fatih|Yaşar Fatih) Karahan\b',subject,re.I))
    governed=bool(re.search(r'\bKarahan\b',subject,re.I) and (re.search(r'TCMB|Merkez Bankası',subject,re.I) or re.search(r'Fatih Karahan',article_body[:500],re.I)))
    institutional=bool(re.search(r'TCMB|Merkez Bankası',subject+' '+article_body[:500],re.I))
    if not (named or governed) or not institutional:return None
    policy='https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Sosyal+Medya'
    record={'landing_page_url':'https://www.flickr.com/photos/merkez_bankasi/55462088240/',
        'original_asset_url':'https://live.staticflickr.com/65535/55462088240_2fb7910355_b.jpg',
        'publisher':'TCMB','creator':'Türkiye Cumhuriyet Merkez Bankası',
        'license_name':'TCMB official Flickr reuse','license_version':None,'license_url':policy,
        'rights_evidence':'TCMB resmî Sosyal Medya sayfası, Flickr bölümü 2: kullanım için izin gerekmez.',
        'attribution_text':'TCMB — Enflasyon Raporu toplantısı, 13.08.2026',
        'restrictions':[],'retrieved_at':time.time(),'photographed_at':'2026-08-13',
        'subject_match':True,'event_match':False,'archive_or_current':'archive',
        'confidence_reason':'TCMB resmî hesabının başlığı ve tarihiyle doğrulanan kurumsal toplantı arşivi. Güncel haber olayının fotoğrafı değildir.',
        'subject_type':'institution','subject':'TCMB',
        'rights_status':'verified_reusable','expected_sha256':'a2aa71e58e0071352f641b68640c28d9e3e981c6896e75b32c5c15676cc7bec8'}
    path,provenance=store_image(record,directory,['live.staticflickr.com'],guard)
    return {'version':1,'path':str(path),'provenance':provenance}

def image_note(record):
    if record['rights_status']=='prohibited': return 'Görsel elendi.'
    prefix='Arşiv fotoğrafı; bu açıklamanın görüntüsü değil.\n' if record.get('archive_or_current')=='archive' else ''
    if not reusable(record): return prefix+'Hak veya kişi/olay eşleşmesi doğrulanmadı; dosya verilmiyor.\n'+record['landing_page_url']
    return prefix+record['attribution_text']+'\n'+record['landing_page_url']+'\n'+record['license_url']

def store_image(record,directory,allowed,guard=lambda:None):
    if not reusable(record): raise ValueError('image_rights_or_match_unverified')
    data,meta,_,_=Fetcher(allowed,guard,max_bytes=10_000_000).get(record['original_asset_url'])
    if not meta.get('content-type','').split(';')[0] in ('image/jpeg','image/png','image/webp'): raise ValueError('image_mime')
    if not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n') or data[:4]==b'RIFF' and data[8:12]==b'WEBP'): raise ValueError('image_magic')
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        im=Image.open(io.BytesIO(data)); im.verify()
        im=Image.open(io.BytesIO(data)); im.load()
    if min(im.size)<100 or sum(im.size)>10000 or max(im.size)/min(im.size)>20: raise ValueError('image_dimensions')
    sha=hashlib.sha256(data).hexdigest()
    if record.get('expected_sha256') and record['expected_sha256']!=sha:raise ValueError('curated_image_changed')
    root=Path(directory).resolve(); root.mkdir(mode=0o700,parents=True,exist_ok=True)
    path=root/(sha+'.'+{'JPEG':'jpg','PNG':'png','WEBP':'webp'}[im.format])
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_bytes(data);temp.chmod(0o600);temp.replace(path)
    # Original is preserved privately; no remote public URL. Provenance retains original SHA.
    phash=hashlib.sha256(im.convert('L').resize((8,8)).tobytes()).hexdigest()
    provenance=record|{'sha256':sha,'perceptual_digest':phash,'mime':meta['content-type'],'dimensions':list(im.size),'stored_at':time.time()}
    sidecar=path.with_suffix('.json');sidecar.write_text(json.dumps(provenance,ensure_ascii=False,indent=2));sidecar.chmod(0o600)
    attribution=path.with_suffix('.attribution.txt');attribution.write_text(record['attribution_text']+'\n'+record['license_url']);attribution.chmod(0o600)
    return path,provenance

class CommonsCandidates:
    """Free bounded discovery; extmetadata alone cannot verify subject/event matching."""
    def __init__(self,guard): self.guard=guard
    def search(self,query):
        from urllib.parse import urlencode
        from .normalizer import ROUTINE_KAP
        if ROUTINE_KAP.search(query): raise ValueError('scope_excluded_query')
        params={'action':'query','format':'json','generator':'search','gsrsearch':query,'gsrnamespace':6,'gsrlimit':3,'prop':'imageinfo','iiprop':'url|extmetadata'}
        raw,_,_,_=Fetcher(['commons.wikimedia.org'],self.guard).get('https://commons.wikimedia.org/w/api.php?'+urlencode(params))
        result=[]
        for page in json.loads(raw).get('query',{}).get('pages',{}).values():
            info=page.get('imageinfo',[{}])[0];ex=info.get('extmetadata',{})
            result.append({'landing_page_url':info.get('descriptionurl'),'original_asset_url':info.get('url'),'publisher':'Wikimedia Commons',
                'creator':ex.get('Artist',{}).get('value'),'license_name':ex.get('LicenseShortName',{}).get('value'),'license_version':None,
                'license_url':ex.get('LicenseUrl',{}).get('value'),'rights_evidence':ex.get('UsageTerms',{}).get('value'),'attribution_text':ex.get('Attribution',{}).get('value'),
                'restrictions':['Subject/event matching needs review'],'retrieved_at':time.time(),'photographed_at':None,'subject_match':False,'event_match':False,
                'archive_or_current':'unknown','confidence_reason':'Source-page candidate only','rights_status':'unknown'})
        return result
