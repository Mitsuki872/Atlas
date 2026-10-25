"""Literal, explicit business matching; no invented semantic category inference."""
import re
import unicodedata
KEYS=('amenity','shop','craft','office','tourism','leisure','healthcare','industrial')
def norm(v):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(v)).lower() if not unicodedata.combining(c)).replace('_',' ').replace('’',' ').replace("'",' ').split())
ALIASES={
 'restaurant':('amenity','restaurant'),'restaurants':('amenity','restaurant'),
 'cafe':('amenity','cafe'),'cafes':('amenity','cafe'),
 'boulangerie':('shop','bakery'),'bakery':('shop','bakery'),
 'coiffeur':('shop','hairdresser'),'coiffure':('shop','hairdresser'),'hairdresser':('shop','hairdresser'),
 'garage':('shop','car_repair'),'garagiste':('shop','car_repair'),'car repair':('shop','car_repair'),
 'dentiste':('amenity','dentist'),'dentist':('amenity','dentist'),
 'plomberie':('craft','plumber'),'plombier':('craft','plumber'),'plumber':('craft','plumber'),
 'electricien':('craft','electrician'),'electrician':('craft','electrician'),
 'fleuriste':('shop','florist'),'boucherie':('shop','butcher'),'pharmacie':('amenity','pharmacy'),
 'avocat':('office','lawyer'),'fiduciaire':('office','accountant'),'comptable':('office','accountant'),
 'hotel':('tourism','hotel'),'fitness':('leisure','fitness_centre'),'salle de sport':('leisure','fitness_centre'),
 'menuisier':('craft','carpenter'),'menuiserie':('craft','carpenter'),'peintre':('craft','painter'),
 'immobilier':('office','estate_agent'),'opticien':('shop','optician'),'veterinaire':('amenity','veterinary')}
def tag_for(term):
    value=term.strip()
    if re.fullmatch(r'(?:'+ '|'.join(KEYS)+r')=[a-zA-Z0-9_:;-]+',value):return tuple(value.split('=',1))
    return ALIASES.get(norm(value))
def categories(tags):
    from app.domain import SECTORS
    known=[s for s,(k,v) in SECTORS.items() if tags.get(k)==v]
    return list(dict.fromkeys(known+[f'{k}={tags[k]}' for k in KEYS if tags.get(k) and tags[k] not in ('no','yes','vacant')]))
def matches(term,tags):
    rules=rules_for(term)
    if rules:return any(all(value in tags.get(key,'').split(';') for key,value in rule) for rule in rules)
    value=norm(term)
    return bool(value) and any(value in norm(tags.get(k,'')) for k in ('name',*KEYS))

# Explicit OR categories. Preschool facilities are included only for broad requests;
# a crèche request stays narrower. Generic schools / residential care are excluded.
CHILDCARE_TERMS=('structure d accueil pour enfants','structures d accueil pour enfants','structure d accueil pour enfant','accueil pour enfants','accueil des enfants','accueil d enfants','accueil de la petite enfance','structure d accueil de la petite enfance','structures d accueil de la petite enfance','accueil petite enfance','petite enfance','garderie','garderies')
CHILDCARE_RULES=[(('amenity','childcare'),),(('amenity','kindergarten'),),(('amenity','social_facility'),('social_facility','day_care'),('social_facility:for','child'))]

def rules_for(term):
    label=norm(term)
    if label in CHILDCARE_TERMS:return CHILDCARE_RULES
    if label in ('creche','creches','nurserie','nurseries','accueil de jour pour enfants'):return [CHILDCARE_RULES[0],CHILDCARE_RULES[2]]
    if label in ('jardin d enfants','jardins d enfants','prescolaire','ecole enfantine','ecoles enfantines'):return [CHILDCARE_RULES[1]]
    tag=tag_for(term)
    return [(tag,)] if tag else []

def resolution(term):
    rules=rules_for(term)
    return {'term':term,'method':'explicit_osm_categories' if rules else 'literal_name_or_tag_value','rules':[[{'key':k,'value':v} for k,v in rule] for rule in rules],
            'note':'Correspondances explicites ; une recherche large peut inclure le préscolaire, sans garantir une place disponible ni une activité actuelle.' if norm(term) in CHILDCARE_TERMS else 'Catégories OSM explicites.' if rules else 'Libellé sans catégorie connue : recherche littérale, pas de compréhension automatique de tous les métiers.'}
