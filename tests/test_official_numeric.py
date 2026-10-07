from habnews.official import parse_tcmb_home
from habnews.schema import ValidationError
import pytest

@pytest.mark.parametrize('year',['2026','2027'])
def test_dynamic_official_year_date_precision(year):
    html=f'<a class="tab-content-box" href="/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/{year}/DUY{year}-1"><p class="tab-content-text">Faiz kararı</p><div class="tab-content-date-day">01</div><div class="tab-content-date-month">01</div></a>'
    item=parse_tcmb_home(html.encode(),'tcmb')[0];assert item['time_precision']=='date';assert year in item['url']

def test_changed_dom_is_failure_not_no_news():
    with pytest.raises(ValueError):parse_tcmb_home(b'<html>No matching cards</html>','tcmb')

def test_normalized_number_must_match_raw(prepared):
    db,a,j,r,m=prepared;r['facts'][0]['normalized_value']=4000
    with pytest.raises(ValidationError,match='normalization'):a.create(j,r,m)
