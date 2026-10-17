import copy
from habnews.quality import CASES,case_input,evaluate


def test_reference_corpus_passes_without_model_calls():
 report=evaluate()
 assert report['passed']==report['total']==10
 assert report['live_calls_made']==0 and report['mode']=='reference_drafts'
 assert any(c['characters_saved']>0 for c in report['cases'])
 assert all(c['unsupported_numbers']==[] for c in report['cases'])


def test_recorded_output_mutation_fails_and_is_comparable():
 outputs={c['id']:{'result':case_input(c)[1],'run_metadata':{'turns':1}} for c in CASES}
 changed=outputs['current-account']['result']
 changed['facts'][0]['text']=changed['facts'][0]['text'].replace('42,1','99,9')
 changed['proposed_body']=changed['headline']+'\n\n'+changed['facts'][0]['text']
 report=evaluate(outputs,evaluate())
 bad=next(r for r in report['cases'] if r['id']=='current-account')
 assert not bad['passed'] and bad['error']=='unsupported_sentence'
 assert len(report['comparison'])==10
 assert report['mode']=='recorded_model_outputs'


def test_missing_model_cases_are_not_counted_as_success():
 report=evaluate({})
 assert report['passed']==0


def test_operational_counts_are_local_and_do_not_claim_quality(db):
 from habnews.quality import operational_metrics
 db.audit('draft_edited','x',{'model_calls':0});db.audit('feed_duplicate_grouped','y')
 report=operational_metrics(db)
 assert report['edits_without_model']==1 and report['grouped_duplicate_cards']==1
 assert report['known_local_model_calls']==0 and report['uncertain_local_calls']==0
