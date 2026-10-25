"""Synthetic regression for the user's exact wording and safe category scope."""
import pytest
from app.business_search import matches,resolution
from app.connectors import build_query
from app.domain import CampaignInput

@pytest.mark.parametrize('term',["Structure d'accueil pour enfants","Structures d’accueil pour enfants",'Crèche','Garderie','jardin d’enfants'])
def test_childcare_french_labels_are_recognized(term):
    assert resolution(term)['method']=='explicit_osm_categories'
    assert matches(term,{'amenity':'childcare' if term=='Crèche' else 'kindergarten'})

def test_childcare_boundaries_and_narrow_creche():
    term="Structure d'accueil pour enfants"
    assert matches(term,{'amenity':'childcare','name':'Different wording'})
    assert matches(term,{'amenity':'kindergarten','name':'Preschool'})
    assert matches(term,{'amenity':'social_facility','social_facility':'day_care','social_facility:for':'child;disabled'})
    assert not matches(term,{'amenity':'school'})
    assert not matches(term,{'amenity':'social_facility','social_facility':'day_care','social_facility:for':'senior'})
    assert not matches(term,{'amenity':'social_facility','social_facility':'group_home','social_facility:for':'child'})
    assert not matches('crèche',{'amenity':'kindergarten'})
    assert resolution('métier inconnu')['method']=='literal_name_or_tag_value'

def test_overpass_childcare_is_category_union_inside_same_municipality():
    q=build_query(CampaignInput(name='Morges',city='Morges',sectors=["Structure d'accueil pour enfants"]).model_dump())
    assert '"amenity"="childcare"' in q and '"amenity"="kindergarten"' in q
    assert '"social_facility"="day_care"' in q
    assert '"admin_level"="8"' in q and 'Morges' in q
    assert "Structure" not in q
