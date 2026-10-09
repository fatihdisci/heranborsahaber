import re
from .normalizer import norm

REASONING='high'
MODEL='gpt-6-luna'; PROVIDER='openai-codex'; TRANSPORT='codex_responses'
class ValidationError(ValueError): pass

def complete_source_sentence(text,passage):
    """Reject clipped negations, conditions and mid-sentence attribution."""
    needle=norm(text)
    for line in passage.splitlines():
        line=norm(line);start=line.find(needle)
        while start>=0:
            end=start+len(needle);before=line[:start].rstrip();after=line[end:].lstrip()
            begins=not before or start>0 and line[start-1].isspace() and before.rstrip('"”’').endswith(('.', '!', '?'))
            finishes=not after or needle.rstrip('"”’').endswith(('.', '!', '?')) and end<len(line) and line[end].isspace()
            if begins and finishes:return True
            start=line.find(needle,start+1)
    return False

def numeric_value(raw):
    from decimal import Decimal,InvalidOperation
    raw=raw.casefold().strip().removeprefix('yüzde').strip().lstrip('%').strip()
    # A sourced lower-bound phrase still has a numeric floor. The verbatim
    # fact sentence retains "üzerinde" so the draft cannot turn it into an
    # exact amount; this parser only checks the model's numeric floor.
    raw=re.sub(r"\s+tl(?:['’]nin)?\s+üzerinde$",'',raw)
    scales={'bin':1000,'milyon':1000000,'milyar':1000000000,'trilyon':1000000000000}
    tokens=re.findall(r'[+-]?\d+(?:[.,]\d+)*|bin|milyon|milyar|trilyon',raw)
    if ''.join(tokens)!=re.sub(r'\s+','',raw):raise InvalidOperation('unsupported numeric expression')
    if not tokens:raise InvalidOperation('empty numeric expression')
    total=Decimal(0);current=None
    for token in tokens:
        if token in scales:
            if current is None:raise InvalidOperation('scale without number')
            total+=current*scales[token];current=None
        else:
            if current is not None:raise InvalidOperation('adjacent numbers without scale')
            if ',' in token:token=token.replace('.','').replace(',','.')
            elif re.fullmatch(r'[+-]?\d{1,3}(?:\.\d{3})+',token):token=token.replace('.','')
            current=Decimal(token)
    return total+(current if current is not None else 0)

def validate_result(result,job,evidence):
    manual=job.get('manual_attribution')
    strict_article=job.get('content_contract')=='article-v2'
    expected={'schema_version','event_id','event_version','relevance_reason','priority','verification_state','facts','ambiguities','headline','proposed_body','verified_tags','image_candidates'}
    if not isinstance(result,dict) or set(result)!=expected: raise ValidationError('schema_keys')
    if type(result['event_version']) is not int or not isinstance(result['relevance_reason'],str) or len(result['relevance_reason'])>600:raise ValidationError('schema_types')
    if not isinstance(result['ambiguities'],list) or not isinstance(result['image_candidates'],list) or not all(isinstance(c,dict) for c in result['image_candidates']):raise ValidationError('schema_arrays')
    if result['schema_version']!='habnews-v1' or result['event_id']!=job['event_id'] or result['event_version']!=job['event_version']: raise ValidationError('job_identity')
    if result['priority'] not in ('P0','P1','P2'): raise ValidationError('priority')
    if result['verification_state'] not in ('official_primary','corroborated_independent','attributed_single_source','unverified','conflicting'): raise ValidationError('verification_state')
    body=result['proposed_body']; headline=result['headline']
    if not isinstance(body,str) or len(body)>3200 or not body or not isinstance(headline,str) or len(headline)>180: raise ValidationError('body_length')
    pattern=r'Başlık:|hedef fiyat|piyasayı sall|hisseyi uçur|al/sat' if manual and manual.get('source_type')=='social_x' else r'https?://|#|Başlık:|hedef fiyat|piyasayı sall|hisseyi uçur|al/sat'
    if re.search(pattern,body,re.I): raise ValidationError('editorial_format')
    if not isinstance(result['facts'],list) or not 1<=len(result['facts'])<=20: raise ValidationError('facts_required')
    if result['ambiguities']: raise ValidationError('needs_review_ambiguities')
    allowed=set(job['evidence_refs']); families=set();primary=False; sentences=[]
    from .evidence import conflicting_evidence
    if conflicting_evidence([evidence[k] for k in allowed if k in evidence]):raise ValidationError('conflicting_critical_numbers')
    fact_keys={'text','source_ref','value_raw','normalized_value','unit','currency','scale','period','scope','stage','actor','quote'}
    for fact in result['facts']:
        if not isinstance(fact,dict) or set(fact)!=fact_keys: raise ValidationError('fact_schema')
        ref=fact['source_ref']
        if ref not in allowed or ref not in evidence: raise ValidationError('missing_evidence_ref')
        ev=evidence[ref]; passage=ev['passage']; text=fact['text']
        if not isinstance(text,str) or len(text)<10 or norm(text) not in norm(passage): raise ValidationError('unsupported_sentence')
        if strict_article and not complete_source_sentence(text,passage):raise ValidationError('incomplete_source_sentence')
        for key in ('value_raw','unit','currency','scale','period','scope','stage','actor','quote'):
            value=fact[key]
            if value is not None and (not isinstance(value,str) or norm(value) not in norm(text if strict_article else passage)): raise ValidationError('unsupported_'+key)
        if fact['value_raw'] is not None:
            from decimal import Decimal,InvalidOperation
            try:
                if numeric_value(fact['value_raw'])!=Decimal(str(fact['normalized_value'])):raise ValidationError('numeric_normalization_mismatch')
            except InvalidOperation:raise ValidationError('numeric_format_needs_review')
        elif fact['normalized_value'] is not None:raise ValidationError('numeric_without_raw')
        if not fact['actor'] or not fact['stage']: raise ValidationError('actor_stage_required')
        # Never interpret a source quote as a system instruction.
        if re.search(r'ignore.*instructions|şifre|tokenı gönder|system prompt|execute|curl ',text,re.I): raise ValidationError('injection_content')
        families.add(ev['family']);primary=primary or bool(ev['primary_source']);sentences.append(text)
    # Conservative v1 guard: all body claims are verbatim supported fact sentences.
    if body!=headline+'\n\n'+'\n\n'.join(sentences): raise ValidationError('unreferenced_body_claim')
    words=re.findall(r'\w+',norm(headline)); supported=' '.join(norm(evidence[f['source_ref']]['passage']) for f in result['facts'])
    if any(word not in supported for word in words): raise ValidationError('unsupported_headline')
    if strict_article:
        trim=lambda t:norm(t).rstrip('.!? ')
        source_lines=[job.get('source_title','')]+sentences+[line for f in result['facts'] for line in evidence[f['source_ref']]['passage'].splitlines()]
        if trim(headline) not in {trim(line) for line in source_lines if line.strip()}:raise ValidationError('headline_not_source_phrase')
        if not set(re.findall(r'\d+(?:[.,]\d+)*',headline)).issubset(set(re.findall(r'\d+(?:[.,]\d+)*',' '.join(sentences)))):raise ValidationError('headline_unbound_number')
    if strict_article and manual and manual.get('source_type')=='article' and re.match(r'^(?:şirket|kurum|proje|bu şirket|söz konusu şirket)(?:[\s,.:]|$)',norm(headline),re.I):
        raise ValidationError('generic_article_headline')
    if result['verification_state']=='official_primary' and not primary: raise ValidationError('not_primary')
    if result['verification_state']=='corroborated_independent' and len(families)<2: raise ValidationError('same_wire_not_independent')
    attributed=bool(manual) and result['verification_state']=='attributed_single_source'
    if attributed:
        if any(evidence[f['source_ref']]['url']!=manual['url'] for f in result['facts']):raise ValidationError('manual_source_mismatch')
        if manual['source_type']=='social_x':
            from .social import ACCOUNTS
            from urllib.parse import urlsplit
            account=manual.get('account');link=urlsplit(manual['url'])
            if account not in ACCOUNTS or manual['owner']!='X · @'+account or link.scheme!='https' or link.hostname!='x.com' or not re.fullmatch('/'+account+r'/status/\d{15,22}',link.path):raise ValidationError('manual_account_mismatch')
            if any(evidence[f['source_ref']]['family']!='social:'+account for f in result['facts']):raise ValidationError('manual_account_evidence_mismatch')
        elif manual['source_type']!='article':raise ValidationError('manual_source_type')
    if result['verification_state'] not in ('official_primary','corroborated_independent') and not attributed: raise ValidationError('verification_pending')
    # Model cannot authorize tags, media licensing, priority escalation or publishing.
    if result['verified_tags']: raise ValidationError('unconfigured_tag_mapping')
    if len(result['image_candidates'])>3: raise ValidationError('image_candidate_limit')
    if manual:
        if manual['source_type']=='social_x':
            from .social import ACCOUNTS
            text=ACCOUNTS[manual['account']]+', X hesabında şu ifadeleri paylaştı:\n\n'+'\n\n'.join('“'+s+'”' for s in sentences)
        else:
            # A source sentence may serve as both headline and fact for evidence
            # binding; show that information only once in the delivered draft.
            trim=lambda value:norm(value).rstrip('.!? ')
            displayed=[sentence for sentence in sentences if trim(sentence)!=trim(headline)] if strict_article else sentences
            text=headline+('\n\n'+'\n\n'.join(displayed) if displayed else '')
            if attributed:text+='\n\nKaynak: '+manual['owner']
        from .tweet_style import decorate
        text=decorate(text,body+' '+job.get('source_title',''))
        if len(text)>(380 if strict_article else 550):raise ValidationError('tweet_too_long')
        return text
    from .tweet_style import decorate
    return decorate(body,body)

def lock_metadata(metadata):
    if metadata.get('requested_model')!=MODEL or metadata.get('provider')!=PROVIDER or metadata.get('transport')!=TRANSPORT: raise ValidationError('model_transport_lock')
    reported=metadata.get('server_model')
    if reported is not None and reported!=MODEL: raise ValidationError('effective_model_mismatch')
    if metadata.get('auth_source')!='habnews_own_oauth' or metadata.get('speed')!='standard': raise ValidationError('auth_speed_lock')
