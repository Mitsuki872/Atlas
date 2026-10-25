"""Literal, explicit business matching; no invented semantic category inference."""
import re
import unicodedata
KEYS=('amenity','shop','craft','office','tourism','leisure','healthcare','industrial')
def norm(v):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(v)).lower() if not unicodedata.combining(c)).replace('_',' ').split())
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
    tag=tag_for(term)
    if tag:return tags.get(tag[0])==tag[1]
    value=norm(term)
    return bool(value) and any(value in norm(tags.get(k,'')) for k in ('name',*KEYS))
