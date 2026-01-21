from django.db import models


class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    token = models.CharField(max_length=500, blank=True, null=True)
    last_login = models.DateTimeField(null=True, blank=True)
    admin = models.BooleanField(default=False)

    verifie = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    link_verification = models.CharField(max_length=255, null=True, blank=True)
    # Date de creation du token de verification (pour expiration)
    verification_token_created_at = models.DateTimeField(null=True, blank=True)


class LoginAttempt(models.Model):
    """
    Tracking des tentatives de connexion pour protection anti-bruteforce.
    """
    ip_address = models.GenericIPAddressField()
    email = models.EmailField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['ip_address', 'attempted_at']),
            models.Index(fields=['email', 'attempted_at']),
        ]

    @classmethod
    def get_recent_failures(cls, ip_address, email=None, minutes=15):
        """
        Retourne le nombre de tentatives echouees recentes pour une IP ou email.
        """
        from django.utils.timezone import now
        from datetime import timedelta

        cutoff = now() - timedelta(minutes=minutes)
        query = cls.objects.filter(
            ip_address=ip_address,
            attempted_at__gte=cutoff,
            successful=False
        )

        # Aussi verifier par email si fourni
        if email:
            from django.db.models import Q
            query = cls.objects.filter(
                Q(ip_address=ip_address) | Q(email=email),
                attempted_at__gte=cutoff,
                successful=False
            )

        return query.count()

    @classmethod
    def record_attempt(cls, ip_address, email=None, successful=False):
        """
        Enregistre une tentative de connexion.
        """
        cls.objects.create(
            ip_address=ip_address,
            email=email,
            successful=successful
        )

    @classmethod
    def clear_old_attempts(cls, hours=24):
        """
        Nettoie les anciennes tentatives (a appeler periodiquement).
        """
        from django.utils.timezone import now
        from datetime import timedelta

        cutoff = now() - timedelta(hours=hours)
        cls.objects.filter(attempted_at__lt=cutoff).delete()
