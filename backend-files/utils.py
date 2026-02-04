"""
Fonctions utilitaires pour le module files.
Regroupe les patterns de code repetitifs pour eviter la duplication.
"""
import jwt
import json
import os
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse


logger = logging.getLogger(__name__)

# Extensions d'images supportées
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Root directory pour les fichiers
ROOT_DIR = os.environ.get("FILES_ROOT_DIR")


# =============================================================================
# Token Generation & Verification
# =============================================================================

def generate_token(user):
    """Génère un token JWT pour un utilisateur."""
    payload = {
        'user_id': user.id,
        'username': getattr(user, 'username', ''),
        'admin': getattr(user, 'admin', False),
        'exp': datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRATION_HOURS),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def verify_token(token):
    """Vérifie et décode un token JWT."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Le token a expiré.")
    except jwt.InvalidTokenError:
        raise Exception("Le token est invalide.")


# =============================================================================
# Request Authentication Helpers
# =============================================================================

def verify_admin_token(request):
    """
    Vérifie le token admin depuis le header Authorization.

    Returns:
        (success, payload_or_error_response)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        if not payload.get("admin"):
            return False, JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)
        return True, payload
    except Exception as e:
        return False, JsonResponse({"error": str(e)}, status=401)


def verify_user_token(request):
    """
    Vérifie le token utilisateur depuis le header Authorization.

    Returns:
        (success, payload_or_error_response)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        return True, payload
    except Exception as e:
        return False, JsonResponse({"error": str(e)}, status=401)


def extract_token(request):
    """
    Extrait le token du header Authorization sans le vérifier.

    Returns:
        token string ou None
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None


def is_authenticated(request):
    """
    Vérifie si l'utilisateur est authentifié (sans bloquer).

    Returns:
        bool
    """
    token = extract_token(request)
    if not token:
        return False
    try:
        verify_token(token)
        return True
    except Exception:
        return False


# =============================================================================
# Request Parsing Helpers
# =============================================================================

def parse_json_body(request):
    """
    Parse le body JSON de la requête.

    Returns:
        (success, data_or_error_response)
    """
    try:
        data = json.loads(request.body.decode() if hasattr(request.body, 'decode') else request.body)
        return True, data
    except json.JSONDecodeError:
        return False, JsonResponse({"error": "JSON invalide."}, status=400)


def parse_json_or_post(request):
    """
    Parse le body JSON ou les données POST selon le content-type.

    Returns:
        (success, data_or_error_response)
    """
    if request.content_type and 'application/json' in request.content_type.lower():
        try:
            data = json.loads(request.body.decode() or '{}')
            return True, data
        except json.JSONDecodeError:
            return False, JsonResponse({"error": "JSON invalide."}, status=400)
    else:
        return True, request.POST


def check_method(request, allowed_methods):
    """
    Vérifie que la méthode HTTP est autorisée.

    Returns:
        JsonResponse d'erreur si méthode non autorisée, None sinon
    """
    if isinstance(allowed_methods, str):
        allowed_methods = [allowed_methods]

    if request.method not in allowed_methods:
        return JsonResponse({"error": "Method not allowed."}, status=405)
    return None


# =============================================================================
# Path Security Helpers
# =============================================================================

def get_root_path():
    """Retourne le chemin root résolu."""
    return Path(ROOT_DIR).resolve()


def validate_path_security(relative_path, root=None):
    """
    Valide qu'un chemin relatif est sécurisé (reste dans ROOT_DIR).

    Args:
        relative_path: Chemin relatif à valider
        root: Path root optionnel (utilise ROOT_DIR par défaut)

    Returns:
        (is_valid, resolved_path_or_error_message)
    """
    if root is None:
        root = get_root_path()

    full_path = (root / str(relative_path).lstrip("/\\")).resolve()

    try:
        if not full_path.is_relative_to(root):
            return False, "Invalid path."
    except AttributeError:
        # Fallback pour anciennes versions Python
        if str(full_path).find(str(root)) != 0:
            return False, "Invalid path."

    return True, full_path


def is_image_file(file_path):
    """
    Vérifie si un fichier est une image supportée.

    Args:
        file_path: Path object ou string

    Returns:
        bool
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
    return file_path.suffix.lower() in IMAGE_EXTENSIONS


def collect_image_paths(directory, root=None):
    """
    Collecte tous les chemins d'images dans un répertoire (récursif).

    Args:
        directory: Path du répertoire à scanner
        root: Path root pour calculer les chemins relatifs

    Returns:
        Liste de chemins relatifs (strings)
    """
    if root is None:
        root = get_root_path()

    image_paths = []
    for ext in IMAGE_EXTENSIONS:
        image_paths.extend([
            str(f.relative_to(root)) for f in directory.rglob(f"*{ext}")
        ])
        image_paths.extend([
            str(f.relative_to(root)) for f in directory.rglob(f"*{ext.upper()}")
        ])
    return image_paths


# =============================================================================
# Async Thread Helpers
# =============================================================================

def spawn_async_task(target, args, task_name="async_task"):
    """
    Lance une tâche en arrière-plan dans un thread daemon.

    Args:
        target: Fonction à exécuter
        args: Tuple d'arguments pour la fonction
        task_name: Nom pour le logging
    """
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    logger.info(f"Tâche {task_name} lancée en arrière-plan")
