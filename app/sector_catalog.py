"""French activity picker. Keywords suggest categories, never become query filters."""
from app.business_search import norm
ROWS=[
 ('restaurant','Restaurant','restauration,repas,bistrot,brasserie'),('bakery','Boulangerie','bakery,pain,viennoiserie,tea-room,tea room,tearoom'),('cafe','Café','cafe,coffee,salon de thé,tea-room'),
 ('creche','Crèche','enfants,enfant,UAPE,garderie,accueil parascolaire,périscolaire,nurserie,petite enfance'),('kindergarten','Jardin d’enfants','préscolaire,école enfantine,enfants'),
 ('hairdresser','Coiffure','hairdresser,coiffeur,coiffeuse,salon,cheveux,barbier'),('car_repair','Garage automobile','garage,car repair,car_repair,mécanique,automobile,garagiste'),('dentist','Dentiste','dentist,dentaire,cabinet dentaire'),('plumber','Plomberie','plumber,plombier,sanitaire,tuyaux'),('electrician','Électricité','electrician,électricien,électrique'),
 ('florist','Fleuriste','fleurs,bouquets'),('butcher','Boucherie','boucher,viande'),('pharmacy','Pharmacie','médicaments,santé'),('lawyer','Avocat','avocate,juridique,droit,étude'),('accountant','Fiduciaire','comptable,comptabilité,fiscalité'),('hotel','Hôtel','hotel,hébergement'),('fitness_centre','Salle de sport','fitness,musculation,gym,sport'),('carpenter','Menuiserie','menuisier,charpentier,bois'),('painter','Peinture','peintre,rénovation'),('estate_agent','Agence immobilière','immobilier,courtage,logement'),('optician','Opticien','lunettes,optique'),('veterinary','Vétérinaire','animaux,vétérinaire'),
 ('beauty','Institut de beauté','esthétique,ongles,manucure'),('massage','Massage','bien-être,massages'),('physiotherapist','Physiothérapie','physio,rééducation'),('doctors','Cabinet médical','médecin,docteur,santé'),('psychotherapist','Psychothérapie','psychologue,thérapie'),('architect','Architecture','architecte,construction'),('insurance','Assurances','assurance,courtier'),('it','Services informatiques','informatique,IT,ordinateur'),('travel_agency','Agence de voyages','voyage,tourisme'),('clothes','Boutique de vêtements','mode,habits,textile'),('shoes','Magasin de chaussures','chaussures'),('jewelry','Bijouterie','bijoux,horlogerie'),('books','Librairie','livres'),('sports','Magasin de sport','sport,cycles'),('bicycle','Magasin de vélos','vélo,cycle,bicyclette'),('furniture','Ameublement','meuble,mobilier,décoration'),('hardware','Quincaillerie','bricolage,outillage'),('pet','Animalerie','animaux,alimentation animale'),('laundry','Blanchisserie','laverie,pressing,linge'),('tailor','Couture','couturier,retouche'),('shoemaker','Cordonnerie','cordonnier,réparation chaussures'),('locksmith','Serrurerie','serrurier,clé'),('plasterer','Plâtrerie','plâtrier,isolation'),('roofer','Toiture','couvreur,toit'),('gardener','Paysagiste','jardinier,jardin,paysagisme'),('cleaning','Nettoyage','ménage,conciergerie'),('photographer','Photographie','photographe,photo'),('catering','Traiteur','événementiel,banquet,repas'),('driving_school','Auto-école','permis,conduite'),('language_school','École de langues','langues,cours'),('music_school','École de musique','musique,cours,instruments'),('fast_food','Restauration rapide','snack,kebab,takeaway,pizza à emporter'),('confectionery','Confiserie','chocolat,bonbons'),('pastry','Pâtisserie','pâtisserie,gâteaux'),('supermarket','Supermarché','épicerie,alimentation'),('wine','Caviste','vin,vins'),('bar','Bar','pub,boissons'),('events_venue','Lieu événementiel','salle,réception,mariage')]
TAGS={k:('shop',k) for k in ['florist','butcher','beauty','massage','clothes','shoes','jewelry','books','sports','bicycle','furniture','hardware','pet','laundry','travel_agency','confectionery','pastry','supermarket','wine']}
TAGS.update({k:('office',k) for k in ['lawyer','accountant','estate_agent','architect','insurance','it']})
TAGS.update({k:('craft',k) for k in ['carpenter','painter','tailor','shoemaker','locksmith','plasterer','roofer','gardener','cleaning','photographer','catering']})
TAGS.update({k:('amenity',k) for k in ['kindergarten','pharmacy','veterinary','doctors','driving_school','language_school','music_school','fast_food','bar','events_venue']})
TAGS.update({'hotel':('tourism','hotel'),'fitness_centre':('leisure','fitness_centre'),'physiotherapist':('healthcare','physiotherapist'),'psychotherapist':('healthcare','psychotherapist')})
CATALOG=[{'id':k,'label':label,'keywords':[x.strip() for x in words.split(',')]} for k,label,words in ROWS]
def selected_id(value):
    needle=norm(value)
    for item in CATALOG:
        if needle in (norm(item['id']),norm(item['label'])):return item['id']
    return value

def sector_label(value):
    key=selected_id(value)
    if '=' in key:
        tag,value=key.split('=',1)
        for item in CATALOG:
            if TAGS.get(item['id'])==(tag,value):return item['label']
    return next((x['label'] for x in CATALOG if x['id']==key),value)
def suggest(text):
    q=norm(text);ranked=[]
    for item in CATALOG:
        fields=[norm(item['label']),norm(item['id']),*[norm(v) for v in item['keywords']]]
        rank=0 if not q else 100 if q==fields[0] else 90 if q in fields[2:] else 70 if fields[0].startswith(q) else 50 if any(q in f for f in fields) else 0
        if rank or not q:ranked.append((rank,item))
    return [v for _,v in sorted(ranked,key=lambda row:-row[0])[:12]]
