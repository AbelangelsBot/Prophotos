from django.db import models


class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    token = models.CharField(max_length=500, blank=True, null=True)
    last_login = models.DateTimeField(null=True, blank=True)

    verifie = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    link_verification = models.CharField(max_length=255, null=True, blank=True)

