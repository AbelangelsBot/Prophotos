"""
Settings de test - utilise SQLite en mémoire pour les tests.
"""
from .settings import *

# Utiliser SQLite en mémoire pour les tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Désactiver les migrations pour accélérer les tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Réduire le hashing pour accélérer les tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Désactiver l'envoi d'emails pendant les tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Mode test
DEBUG = False
TESTING = True