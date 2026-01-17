from django.db import models


class Fournisseur(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.nom


class DemandeAchat(models.Model):
    STATUTS_DA = [
        ('BROUILLON', 'Brouillon'),
        ('EN_ATTENTE', 'En attente validation'),
        ('VALIDE', 'Validée'),
        ('REJETEE', 'Rejetée'),
    ]

    reference = models.CharField(max_length=50, unique=True)
    date_creation = models.DateField(auto_now_add=True)
    service_demandeur = models.CharField(max_length=100)
    objet = models.CharField(max_length=255, blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUTS_DA, default='BROUILLON')

    def __str__(self):
        return f"DA {self.reference} ({self.statut})"


class LigneDemandeAchat(models.Model):
    demande = models.ForeignKey(DemandeAchat, related_name='lignes', on_delete=models.CASCADE)
    article = models.CharField(max_length=100)
    quantite = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.article} x {self.quantite} pour {self.demande.reference}"


class BonCommande(models.Model):
    STATUTS_BC = [
        ('ENVOYE', 'Envoyé au fournisseur'),
        ('CONFIRME', 'Confirmé'),
        ('CLOTURE', 'Clôturé'),
    ]

    numero = models.CharField(max_length=50, unique=True)
    demande_achat = models.ForeignKey(DemandeAchat, on_delete=models.SET_NULL, null=True, blank=True)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT)
    date_emission = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUTS_BC, default='ENVOYE')

    def __str__(self):
        return f"BC {self.numero} - {self.fournisseur.nom}"


class Reception(models.Model):
    bon_commande = models.ForeignKey(BonCommande, on_delete=models.PROTECT)
    date_reception = models.DateField(auto_now_add=True)
    quantites_conformes = models.BooleanField(default=True)

    def __str__(self):
        return f"Réception de {self.bon_commande.numero} le {self.date_reception}"


class LitigeReception(models.Model):
    reception = models.ForeignKey(Reception, on_delete=models.CASCADE)
    description = models.TextField()
    date_creation = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Litige sur {self.reception.bon_commande.numero}"


class ControleQualite(models.Model):
    reception = models.OneToOneField(Reception, on_delete=models.CASCADE)
    qualite_conforme = models.BooleanField(default=True)
    commentaire = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"QC {self.reception.bon_commande.numero} - {'OK' if self.qualite_conforme else 'NON CONFORME'}"
