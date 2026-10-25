"""Five visible CRM states; opposition remains a separate persistent flag."""
STATUSES=['À contacter','Contacté','À relancer','Client','Écarté']
LEGACY={'Nouveau':'À contacter','À qualifier':'À contacter','Qualifié':'À contacter','À appeler':'À contacter','Appel planifié':'À contacter','Sans réponse':'À relancer','Intéressé':'Contacté','Rendez-vous convenu':'Contacté','Devis à préparer':'Contacté','Devis envoyé':'Contacté','Négociation':'Contacté','Refusé':'Écarté','Ne plus contacter':'Écarté','Archivé':'Écarté'}
def canonical_status(value):return LEGACY.get(value,value)
