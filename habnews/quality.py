"""Repeatable offline editorial evaluation, with optional recorded model outputs.

python -m habnews.quality --output reports/editorial-quality.json
python -m habnews.quality --results outputs.json --baseline previous.json

This measures contracts and observable text properties, not semantic truth or
human readability. The default uses reference drafts and makes zero model calls.
"""
import argparse,json,re
from pathlib import Path
from .editorial_prompt import EDITORIAL_VERSION
from .news_profiles import profile
from .schema import validate_delivery_result,ValidationError
from .rewriting import rewrite_sentence

CASES = [
    {'id':'rate','type':'rate','actor':'TCMB','stage':'belirlediğini',
     'sentence':'TCMB, politika faizini yüzde 40 olarak belirlediğini açıkladı.','keep':['%40','belirledi']},
    {'id':'inflation','type':'inflation','actor':'TÜİK','stage':'açıkladı',
     'sentence':'TÜİK, eylül ayında TÜFE artışının aylık yüzde 2,5 ve yıllık yüzde 30 olduğunu açıkladı.','keep':['eylül','aylık %2,5','yıllık %30']},
    {'id':'current-account','type':'current_account','actor':'Şimşek','stage':'bildirdi',
     'sentence':'Ağustos ayında 4,1 milyar dolar cari fazla verildiğini belirten Şimşek, yıllıklandırılmış cari açığın 42,1 milyar dolar gerçekleştiğini bildirdi.',
     'keep':['Ağustos','4,1','yıllıklandırılmış','42,1'], 'fixture':False,
     'url':'https://www.cnbce.com/haberler/hazine-ve-maliye-bakani-mehmet-simsek-cari-acigin-yonetilebilir-seviyelerde-kalmasini-ongoruyoruz-h39365',
     'owner':'CNBC-e','source_note':'13 Ekim 2026 tarihinde incelenmiş arşiv cümlesi; güncel haber iddiası değildir.'},
    {'id':'earnings','type':'earnings','actor':'Örnek Şirket','stage':'açıkladı',
     'sentence':'Örnek Şirket, 2026 ilk yarı net kârını 2 milyar TL, hasılatını 10 milyar TL olarak açıkladı.','keep':['2026 ilk yarı','net kârını 2 milyar TL','hasılatını 10 milyar TL']},
    {'id':'dividend','type':'dividend','actor':'Örnek Şirket','stage':'sunacağını',
     'sentence':'Örnek Şirket, pay başına brüt 2 TL temettü teklifini genel kurul onayına sunacağını açıkladı.','keep':['brüt 2 TL','teklifini','genel kurul onayına']},
    {'id':'investment','type':'company','actor':'Örnek Şirket','stage':'planladığını',
     'sentence':'Örnek Şirket, 10 milyon TL tutarında yatırım yapmayı planladığını açıkladı.','keep':['10 milyon TL','planlıyor']},
    {'id':'conditional-investment','type':'company','actor':'Örnek Şirket','stage':'planladığını',
     'sentence':'Örnek Şirket, izin alınması koşuluyla 10 milyon TL tutarında yatırım yapmayı planladığını açıkladı.','keep':['izin alınması koşuluyla','10 milyon TL','planladığını']},
    {'id':'denial','type':'claim','actor':'Örnek Şirket','stage':'yalanladı',
     'sentence':'Örnek Şirket, iflas başvurusunda bulunduğu iddiasını yalanladı.','keep':['iddiasını yalanladı']},
    {'id':'contract','type':'company','actor':'Örnek Şirket','stage':'imzaladığını',
     'sentence':'Örnek Şirket, 20 milyon dolar tutarında sözleşme imzaladığını bildirdi.','keep':['20 milyon dolar','imzaladı']},
    {'id':'percentage-points','type':'general','actor':'Örnek Kurum','stage':'açıkladı',
     'sentence':'Örnek Kurum, test göstergesindeki artışın yüzde 5 puan olduğunu açıkladı.','keep':['yüzde 5 puan']},
]


def case_input(case):
    sentence=case['sentence'];ref='evidence-'+case['id'];url=case.get('url','https://fixture.invalid/'+case['id'])
    fact=dict(text=sentence,source_ref=ref,actor=case['actor'],stage=case['stage'],value_raw=None,normalized_value=None,unit=None,currency=None,scale=None,period=None,scope=None,quote=None)
    job={'event_id':case['id'],'event_version':1,'evidence_refs':[ref], 'source_title':sentence.rstrip('.'),
         'content_contract':'article-v2','controlled_rewrite':True,
         'manual_attribution':{'source_type':'article','owner':case.get('owner','TEST'),'url':url}}
    result={'schema_version':'habnews-v1','event_id':case['id'],'event_version':1,'relevance_reason':'Offline editorial regression case',
            'priority':'P1','verification_state':'attributed_single_source','facts':[fact],'ambiguities':[],
            'headline':sentence.rstrip('.'),'proposed_body':sentence.rstrip('.')+'\n\n'+sentence,'verified_tags':[],'image_candidates':[]}
    evidence={ref:{'id':ref,'url':url,'passage':sentence,'family':'fixture','primary_source':False}}
    return job,result,evidence


def evaluate(results=None,baseline=None):
    rows=[]
    for case in CASES:
        job,result,evidence=case_input(case)
        record=(results or {}).get(case['id'])
        entry={'id':case['id'],'fixture':case.get('fixture',True),'type':profile(case['sentence'])['type'],'expected_type':case['type']}
        if 'url' in case:entry.update(source_url=case['url'],source_note=case['source_note'])
        if results is not None:
            if not isinstance(record,dict) or not isinstance(record.get('result'),dict):
                rows.append(entry|{'passed':False,'error':'missing_recorded_result'});continue
            result=record['result']
        try:
            canonical,text,changes=validate_delivery_result(result,job,evidence)
            missing=[marker for marker in case['keep'] if marker not in text]
            duplicates=sum(max(0,text.count(rewrite_sentence(f['text'],f['actor'],bool(f.get('quote'))).rstrip('.'))-1) for f in canonical['facts'])
            numbers=re.findall(r'\d+(?:[.,]\d+)*',text)
            source_numbers=re.findall(r'\d+(?:[.,]\d+)*',case['sentence'])
            new_numbers=sorted(set(numbers)-set(source_numbers))
            entry.update(passed=not missing and not duplicates and not new_numbers and entry['type']==case['type'],
                         text=text,characters=len(text),words=len(text.split()),tags=len(re.findall(r'#\w+',text)),
                         missing_markers=missing,repeated_fact_count=duplicates,unsupported_numbers=new_numbers,normalizations=changes)
            # A before/after display comparison uses exactly the same facts.
            try:
                _,before,_=validate_delivery_result(result,job|{'controlled_rewrite':False},evidence)
                entry['before_characters']=len(before);entry['characters_saved']=len(before)-len(text)
            except ValidationError:entry['before_characters']=None
            calls=record.get('run_metadata',{}).get('turns') if record else None
            entry['reported_model_calls']=calls if type(calls) is int and calls>=0 else None
        except (ValidationError,KeyError,TypeError,ValueError) as exc:
            entry.update(passed=False,error=str(exc) if isinstance(exc,ValidationError) else 'invalid_result_shape')
        rows.append(entry)
    report={'editorial_version':EDITORIAL_VERSION,'corpus_version':1,'mode':'recorded_model_outputs' if results is not None else 'reference_drafts',
            'live_calls_made':0,'cases':rows,'passed':sum(r['passed'] for r in rows),'total':len(rows),
            'human_review':'Readability and semantic faithfulness still require editorial review; these metrics are deterministic regression checks.'}
    if baseline:
        previous={r['id']:r for r in baseline.get('cases',[])}
        report['comparison']=[{'id':r['id'],'previous_passed':previous[r['id']].get('passed'),'current_passed':r['passed'],
                               'character_delta':r.get('characters',0)-previous[r['id']].get('characters',0)} for r in rows if r['id'] in previous]
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,help='JSON object mapping case id to result and optional run_metadata')
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=evaluate(json.loads(args.results.read_text()) if args.results else None,json.loads(args.baseline.read_text()) if args.baseline else None)
    raw=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(raw)
    else:print(raw,end='')
    raise SystemExit(0 if report['passed']==report['total'] else 1)



def operational_metrics(db, now=None):
    """Local seven-day counters, not a claim about account-wide model usage."""
    import time
    since=(time.time() if now is None else now)-7*86400
    drafts=db.conn.execute("SELECT count(*),coalesce(round(avg(length(body)),1),0) FROM habnews_draft WHERE created>? AND body<>''",(since,)).fetchone()
    calls=db.conn.execute("SELECT coalesce(sum(actual),0),coalesce(sum(CASE WHEN status='uncertain' THEN 1 ELSE 0 END),0) FROM habnews_budget WHERE created>? AND kind='llm'",(since,)).fetchone()
    counts={r['kind']:r['count'] for r in db.conn.execute("SELECT kind,count(*) AS count FROM habnews_audit WHERE created>? AND kind IN ('draft_edited','feed_duplicate_grouped','manual_format_repair','manual_stage_retry') GROUP BY kind",(since,))}
    failures=[dict(r) for r in db.conn.execute('SELECT stage,code,count(*) AS count FROM habnews_job_failure WHERE created>? GROUP BY stage,code',(since,))]
    return {'window_days':7,'drafts':drafts[0],'mean_characters':drafts[1],'known_local_model_calls':calls[0],'uncertain_local_calls':calls[1],
            'edits_without_model':counts.get('draft_edited',0),'grouped_duplicate_cards':counts.get('feed_duplicate_grouped',0),
            'format_repair_requests':counts.get('manual_format_repair',0),'manual_retries':counts.get('manual_stage_retry',0),'failures':failures}


if __name__=='__main__':main()
