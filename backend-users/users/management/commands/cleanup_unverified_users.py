"""
Commande Django pour supprimer les utilisateurs non verifies apres 72 heures.

Usage:
    python manage.py cleanup_unverified_users
    python manage.py cleanup_unverified_users --hours=48  # Personnaliser le delai
    python manage.py cleanup_unverified_users --dry-run   # Voir ce qui serait supprime
"""

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from users.models import User, LoginAttempt


class Command(BaseCommand):
    help = 'Supprime les utilisateurs non verifies apres un certain delai (defaut: 72h)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=72,
            help='Nombre d\'heures apres lesquelles supprimer les comptes non verifies (defaut: 72)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les utilisateurs qui seraient supprimes sans les supprimer'
        )
        parser.add_argument(
            '--cleanup-attempts',
            action='store_true',
            help='Nettoie aussi les anciennes tentatives de connexion (> 24h)'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        cleanup_attempts = options['cleanup_attempts']

        cutoff_date = now() - timedelta(hours=hours)

        # Trouver les utilisateurs non verifies crees avant la date limite
        unverified_users = User.objects.filter(
            verifie=False,
            created_at__lt=cutoff_date
        )

        count = unverified_users.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'Aucun utilisateur non verifie de plus de {hours}h a supprimer.')
            )
        else:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] {count} utilisateur(s) seraient supprimes:')
                )
                for user in unverified_users:
                    age = now() - user.created_at
                    self.stdout.write(f'  - {user.username} ({user.email}) - cree il y a {age.days}j {age.seconds // 3600}h')
            else:
                # Supprimer les utilisateurs
                usernames = list(unverified_users.values_list('username', flat=True))
                deleted_count, _ = unverified_users.delete()

                self.stdout.write(
                    self.style.SUCCESS(f'{deleted_count} utilisateur(s) non verifie(s) supprime(s):')
                )
                for username in usernames:
                    self.stdout.write(f'  - {username}')

        # Nettoyage des tentatives de connexion
        if cleanup_attempts:
            attempts_cutoff = now() - timedelta(hours=24)
            old_attempts = LoginAttempt.objects.filter(attempted_at__lt=attempts_cutoff)
            attempts_count = old_attempts.count()

            if attempts_count > 0:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'[DRY RUN] {attempts_count} tentatives de connexion seraient supprimees')
                    )
                else:
                    old_attempts.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'{attempts_count} anciennes tentatives de connexion supprimees')
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Aucune ancienne tentative de connexion a nettoyer')
                )
