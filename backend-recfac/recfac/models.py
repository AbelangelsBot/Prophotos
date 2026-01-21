import uuid
from django.db import models


class Image(models.Model):
    """
    Représente une image dans le système de fichiers.
    Utilise un UUID pour identifier de manière stable même si le chemin change.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Chemin relatif actuel (peut changer si fichier déplacé/renommé)
    path = models.CharField(max_length=1000, unique=True, db_index=True, help_text="Chemin relatif depuis FILES_ROOT_DIR")

    # Hash SHA256 du contenu du fichier (pour détecter les changements/renommages)
    file_hash = models.CharField(max_length=64, db_index=True, help_text="SHA256 hash du fichier")

    # Métadonnées du fichier
    filename = models.CharField(max_length=255, help_text="Nom du fichier")
    file_size = models.BigIntegerField(help_text="Taille en octets")
    width = models.IntegerField(null=True, blank=True, help_text="Largeur en pixels")
    height = models.IntegerField(null=True, blank=True, help_text="Hauteur en pixels")

    # Statut de scan pour reconnaissance faciale
    scanned = models.BooleanField(default=False, db_index=True, help_text="Image scannée pour visages")
    scan_date = models.DateTimeField(null=True, blank=True, help_text="Date du dernier scan")
    faces_count = models.IntegerField(default=0, help_text="Nombre de visages détectés")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recfac_image'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.faces_count} visages)"


class Face(models.Model):
    """
    Représente un visage détecté dans une image.
    Stocke l'embedding vectoriel (512 dimensions) pour la reconnaissance faciale.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relation vers l'image (CASCADE: si image supprimée, faces aussi)
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name='faces')

    # Bounding box du visage dans l'image (coordonnées)
    bbox_x1 = models.FloatField(help_text="Coordonnée X1 du cadre")
    bbox_y1 = models.FloatField(help_text="Coordonnée Y1 du cadre")
    bbox_x2 = models.FloatField(help_text="Coordonnée X2 du cadre")
    bbox_y2 = models.FloatField(help_text="Coordonnée Y2 du cadre")
    det_score = models.FloatField(help_text="Score de confiance de détection (0-1)")

    # Vecteur d'embedding (512 floats normalisés pour InsightFace)
    # Stocké en JSON pour PostgreSQL standard
    # Format: liste de 512 floats entre -1 et 1
    embedding = models.JSONField(help_text="Vecteur d'embedding normalisé (512 dimensions)")

    # Tag manuel de la personne (pour identification)
    person_name = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="Nom de la personne (tag manuel)")

    # Clustering automatique (ID de cluster pour regrouper visages similaires)
    cluster_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="ID du cluster automatique")

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recfac_face'
        ordering = ['-det_score']

    def __str__(self):
        person = self.person_name or "Inconnu"
        return f"Visage de {person} dans {self.image.filename} (score: {self.det_score:.2f})"


class Person(models.Model):
    """
    Représente une personne identifiée (optionnel pour phase 2).
    Regroupe plusieurs faces sous un même nom.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Nom unique de la personne
    name = models.CharField(max_length=255, unique=True, help_text="Nom de la personne")

    # Visage de référence pour affichage (miniature)
    reference_face = models.ForeignKey(Face, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    # Embedding moyen normalisé de tous les visages de cette personne
    # Permet une meilleure reconnaissance même avec changements d'âge/apparence
    # Calculé comme la moyenne de tous les embeddings des faces taggées avec cette personne
    average_embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Vecteur d'embedding moyen normalisé (512 dimensions) calculé depuis tous les visages de la personne"
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recfac_person'
        ordering = ['name']

    def __str__(self):
        return self.name
