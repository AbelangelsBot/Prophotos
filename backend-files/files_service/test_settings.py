"""
Settings de test - utilise SQLite en mémoire pour les tests.
"""
import tempfile
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

# Mode test
DEBUG = False
TESTING = True

# Créer un répertoire temporaire pour les fichiers de test
FILES_ROOT_DIR = tempfile.mkdtemp()