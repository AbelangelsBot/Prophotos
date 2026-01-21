import jwt
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from pathlib import Path


def generate_token(user):
    """Génère un JWT token pour un utilisateur."""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'admin': getattr(user, 'admin', False),
        'exp': datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRATION_HOURS),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def verify_token(token):
    """Vérifie et décode un JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Le token a expiré.")
    except jwt.InvalidTokenError:
        raise Exception("Le token est invalide.")


def calculate_file_hash(file_path):
    """
    Calcule le hash SHA256 d'un fichier.
    Utilisé pour détecter les changements et identifier les fichiers.
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Lire par chunks pour ne pas saturer la RAM sur gros fichiers
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def get_image_dimensions(file_path):
    """
    Récupère les dimensions (largeur, hauteur) d'une image.
    """
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            return img.width, img.height
    except Exception:
        return None, None
