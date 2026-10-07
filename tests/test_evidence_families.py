from habnews.evidence import source_family,evidence_excerpt
import pytest
S={'priority':'B','source_family':'publisher-one'}

def test_syndicated_copies_one_family():
    assert source_family(S,'Reuters haberine göre karar...')=='wire:reuters'
    assert source_family(S|{'source_family':'two'},'REUTERS aktardı...')=='wire:reuters'
    assert source_family(S,'Anadolu Ajansı muhabirine...')=='wire:aa'

def test_identical_unattributed_copy_not_independent():
    text='TCMB faiz kararına ilişkin açıklama yayımladı. '*15
    assert source_family(S,text,[{'family':'other-publisher','passage':text}])=='other-publisher'

def test_evidence_whole_paragraph_retention():
    text='Tam kaynaklı açıklama cümlesi. '*10+'\n'+'Ek paragraf. '*100
    excerpt=evidence_excerpt(text,400);assert excerpt==text.split('\n')[0]
    with pytest.raises(ValueError):evidence_excerpt('x'*3000)

def test_critical_conflict_no_averaging():
    from habnews.evidence import conflicting_evidence
    assert conflicting_evidence([{'passage':'TCMB politika faizini yüzde 40 olarak belirledi.'},{'passage':'TCMB politika faizini yüzde 39 olarak belirledi.'}])=='policy_rate'

def test_monthly_annual_distinct():
    from habnews.evidence import conflicting_evidence
    assert not conflicting_evidence([{'passage':'Aylık TÜFE yüzde 2,1 oldu.'},{'passage':'Yıllık TÜFE yüzde 34,2 oldu.'}])
