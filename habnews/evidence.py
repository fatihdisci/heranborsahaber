import re
from difflib import SequenceMatcher
from .normalizer import norm


def source_family(source,text,existing=()):
    lower=norm(text)
    if re.search(r'\breuters\b',lower):return 'wire:reuters'
    if re.search(r'anadolu ajansı|anadolu ajansi|\(aa\)|aa muhabiri',lower):return 'wire:aa'
    if source['priority']=='A':return source['source_family']
    for evidence in existing:
        if SequenceMatcher(None,norm(evidence['passage']),lower[:1600],autojunk=False).ratio()>=0.85:return evidence['family']
    return source['source_family']

def evidence_excerpt(text,limit=1600):
    # Whole paragraph boundary, no silent sentence truncation. A too-large first
    # paragraph is not usable under this conservative retention policy.
    paragraphs=[];size=0
    for paragraph in text.split('\n'):
        if size+len(paragraph)+1>limit:break
        paragraphs.append(paragraph);size+=len(paragraph)+1
    excerpt='\n'.join(paragraphs)
    if len(excerpt)<100:raise ValueError('bounded_evidence_needs_review')
    return excerpt


def critical_numbers(text):
    """Conservative exact contexts, not broad number averaging or fuzzy equivalence."""
    patterns={
        'policy_rate':r'politika faiz(?:i|ini|inin| oranı| oranını)[^.!?]{0,70}?yüzde\s+(\d+(?:[.,]\d+)?)',
        'cpi_monthly':r'(?:aylık\s+tüfe|tüfe[^.!?]{0,30}?aylık)[^.!?]{0,50}?yüzde\s+(\d+(?:[.,]\d+)?)',
        'cpi_annual':r'(?:yıllık\s+tüfe|tüfe[^.!?]{0,30}?yıllık)[^.!?]{0,50}?yüzde\s+(\d+(?:[.,]\d+)?)',
    }
    from decimal import Decimal
    return {kind:{str(Decimal(n.replace(',','.'))) for n in re.findall(pattern,norm(text),re.I)} for kind,pattern in patterns.items()}

def conflicting_evidence(evidence):
    for key in ('policy_rate','cpi_monthly','cpi_annual'):
        values=set()
        for entry in evidence:values.update(critical_numbers(entry['passage'])[key])
        if len(values)>1:return key
    return None
