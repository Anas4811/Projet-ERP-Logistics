from django.contrib import admin
from .models import (
    Fournisseur,
    DemandeAchat,
    LigneDemandeAchat,
    BonCommande,
    Reception,
    LitigeReception,
    ControleQualite,
)

admin.site.register(Fournisseur)
admin.site.register(DemandeAchat)
admin.site.register(LigneDemandeAchat)
admin.site.register(BonCommande)
admin.site.register(Reception)
admin.site.register(LitigeReception)
admin.site.register(ControleQualite)
