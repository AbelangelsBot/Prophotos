"""
Django management command pour normaliser tous les person_name existants.
Usage: python manage.py normalize_person_names
"""
from django.core.management.base import BaseCommand
from recfac.models import Face
from django.db import transaction


def normalize_person_name(name):
    """
    Normalise un nom de personne.
    """
    if not name:
        return None

    # Supprimer espaces début/fin et normaliser espaces multiples
    normalized = " ".join(name.strip().split())

    if not normalized:
        return None

    # Mettre en forme: première lettre de chaque mot en majuscule
    normalized = normalized.title()

    return normalized


class Command(BaseCommand):
    help = 'Normalise tous les person_name dans la base de données pour éviter les doublons'

    def handle(self, *args, **options):
        self.stdout.write('Démarrage de la normalisation des noms...')

        # Récupérer tous les visages avec un person_name
        faces_with_names = Face.objects.filter(person_name__isnull=False).exclude(person_name='')

        total = faces_with_names.count()
        updated = 0

        self.stdout.write(f'Trouvé {total} visage(s) avec un nom.')

        with transaction.atomic():
            for face in faces_with_names:
                original_name = face.person_name
                normalized_name = normalize_person_name(original_name)

                if normalized_name != original_name:
                    face.person_name = normalized_name
                    face.save()
                    updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  Normalisé: "{original_name}" -> "{normalized_name}"')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'\nTerminé! {updated}/{total} nom(s) normalisé(s).')
        )
