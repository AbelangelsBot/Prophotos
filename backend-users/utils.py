"""
Fonctions utilitaires pour le module users.
Regroupe les patterns de code repetitifs pour eviter la duplication.
"""
import jwt
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.http import JsonResponse


# =============================================================================
# Token Generation & Verification
# =============================================================================

def generate_token(user):
    """Génère un token JWT pour un utilisateur."""
    payload = {
        'user_id': user.id,
        'username': user.username,
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
        - Si succès: (True, payload dict)
        - Si erreur: (False, JsonResponse)
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
        data = json.loads(request.body)
        return True, data
    except json.JSONDecodeError:
        return False, JsonResponse({"error": "Données invalides."}, status=400)


def validate_required_fields(data, required_fields):
    """
    Valide que tous les champs requis sont présents et non-vides.

    Args:
        data: dict contenant les données
        required_fields: liste de noms de champs requis

    Returns:
        (is_valid, missing_field_or_none)
    """
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, field
    return True, None


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
# Token Expiration Helpers
# =============================================================================

def is_token_expired(created_at, expiry_hours):
    """
    Vérifie si un token de vérification a expiré.

    Args:
        created_at: datetime de création du token
        expiry_hours: nombre d'heures de validité

    Returns:
        bool
    """
    if not created_at:
        return True

    from django.utils.timezone import now
    token_age = now() - created_at
    max_age = timedelta(hours=expiry_hours)
    return token_age > max_age
