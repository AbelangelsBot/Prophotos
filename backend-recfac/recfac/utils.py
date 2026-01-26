"""
Fonctions utilitaires pour le module recfac.
Regroupe les patterns de code repetitifs pour eviter la duplication.
"""
import json
import threading
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from django.http import JsonResponse
from django.conf import settings

from utils import verify_token, calculate_file_hash, get_image_dimensions
from .models import Image, Face


ROOT_DIR = settings.FILES_ROOT_DIR

# Extensions d'images supportees
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']


# =============================================================================
# Rate Limiting
# =============================================================================

# Configuration du rate limiting
RATE_LIMIT_MAX_REQUESTS = 10  # Nombre max de requetes
RATE_LIMIT_WINDOW_SECONDS = 60  # Fenetre de temps en secondes

# Stockage en memoire pour le rate limiting (thread-safe)
_rate_limit_lock = threading.Lock()
_rate_limit_data = defaultdict(list)  # ip -> list of timestamps


def get_client_ip(request):
    """
    Recupere l'adresse IP du client (gere les proxies).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


def check_rate_limit(request, max_requests=RATE_LIMIT_MAX_REQUESTS, window_seconds=RATE_LIMIT_WINDOW_SECONDS):
    """
    Verifie si une requete depasse la limite de taux.

    Args:
        request: La requete Django
        max_requests: Nombre max de requetes dans la fenetre
        window_seconds: Taille de la fenetre en secondes

    Returns:
        (is_allowed, error_response_or_none)
        - Si autorise: (True, None)
        - Si bloque: (False, JsonResponse avec erreur 429)
    """
    ip = get_client_ip(request)
    now = datetime.now().timestamp()
    window_start = now - window_seconds

    with _rate_limit_lock:
        # Nettoyer les anciennes entrees
        _rate_limit_data[ip] = [ts for ts in _rate_limit_data[ip] if ts > window_start]

        # Verifier la limite
        if len(_rate_limit_data[ip]) >= max_requests:
            # Calculer le temps restant avant reset
            oldest_request = min(_rate_limit_data[ip]) if _rate_limit_data[ip] else now
            retry_after = int(oldest_request + window_seconds - now) + 1

            return False, JsonResponse({
                "error": f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
                "retry_after_seconds": retry_after,
            }, status=429)

        # Ajouter la requete actuelle
        _rate_limit_data[ip].append(now)

    return True, None


def cleanup_rate_limit_data():
    """
    Nettoie les donnees de rate limiting perimees.
    Peut etre appele periodiquement pour liberer la memoire.
    """
    now = datetime.now().timestamp()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    with _rate_limit_lock:
        ips_to_remove = []
        for ip, timestamps in _rate_limit_data.items():
            _rate_limit_data[ip] = [ts for ts in timestamps if ts > window_start]
            if not _rate_limit_data[ip]:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del _rate_limit_data[ip]


# =============================================================================
# Decorateurs et helpers d'authentification
# =============================================================================

def require_token(admin_only=False):
    """
    Decorateur pour verifier le token d'authentification.

    Args:
        admin_only: Si True, verifie aussi que l'utilisateur est admin

    Returns:
        Le payload du token si valide, ou une JsonResponse d'erreur
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Token manquant."}, status=401)

            token = auth_header.split(" ")[1]
            try:
                payload = verify_token(token)
                if admin_only and not payload.get("admin"):
                    return JsonResponse({"error": "Admin access required."}, status=403)
                # Ajouter le payload a la request pour usage ulterieur
                request.token_payload = payload
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=401)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def verify_admin_token(request):
    """
    Verifie le token admin et retourne (success, payload_or_error_response).

    Usage:
        success, result = verify_admin_token(request)
        if not success:
            return result  # C'est une JsonResponse d'erreur
        payload = result
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        if not payload.get("admin"):
            return False, JsonResponse({"error": "Admin access required."}, status=403)
        return True, payload
    except Exception as e:
        return False, JsonResponse({"error": str(e)}, status=401)


def verify_user_token(request):
    """
    Verifie le token utilisateur (sans verif admin) et retourne (success, payload_or_error_response).
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


def verify_admin_token_from_query(request):
    """
    Verifie le token admin depuis les query params (pour SSE/EventSource).
    """
    token = request.GET.get("token", "")
    if not token:
        return False, JsonResponse({"error": "Token manquant."}, status=401)

    try:
        payload = verify_token(token)
        if not payload.get("admin"):
            return False, JsonResponse({"error": "Admin access required."}, status=403)
        return True, payload
    except Exception as e:
        return False, JsonResponse({"error": str(e)}, status=401)


# =============================================================================
# Helpers pour parsing des requetes
# =============================================================================

def parse_json_body(request):
    """
    Parse le body JSON de la requete.

    Returns:
        (success, data_or_error_response)
    """
    try:
        data = json.loads(request.body)
        return True, data
    except json.JSONDecodeError:
        return False, JsonResponse({"error": "Invalid JSON."}, status=400)


def check_method(request, allowed_methods):
    """
    Verifie que la methode HTTP est autorisee.

    Args:
        request: La requete Django
        allowed_methods: Liste ou string des methodes autorisees (ex: "GET" ou ["GET", "POST"])

    Returns:
        JsonResponse d'erreur si methode non autorisee, None sinon
    """
    if isinstance(allowed_methods, str):
        allowed_methods = [allowed_methods]

    if request.method not in allowed_methods:
        return JsonResponse({"error": "Method not allowed."}, status=405)
    return None


# =============================================================================
# Helpers pour les chemins de fichiers
# =============================================================================

def validate_path_security(relative_path):
    """
    Valide qu'un chemin relatif est securise (reste dans ROOT_DIR).

    Args:
        relative_path: Chemin relatif a valider

    Returns:
        (is_valid, file_path_or_error_message)
        - Si valide: (True, Path object absolu)
        - Si invalide: (False, message d'erreur string)
    """
    root = Path(ROOT_DIR).resolve()
    file_path = (root / str(relative_path).lstrip("/\\")).resolve()

    try:
        if not file_path.is_relative_to(root):
            return False, "Invalid path."
    except AttributeError:
        # Fallback pour anciennes versions Python
        if str(file_path).find(str(root)) != 0:
            return False, "Invalid path."

    return True, file_path


def is_image_file(file_path):
    """
    Verifie si un fichier est une image supportee.

    Args:
        file_path: Path object ou string

    Returns:
        bool
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
    return file_path.suffix.lower() in IMAGE_EXTENSIONS


# =============================================================================
# Helpers pour la gestion des images en DB
# =============================================================================

def get_or_create_image_record(file_path, relative_path):
    """
    Recupere ou cree un enregistrement Image dans la DB.
    Met a jour le chemin si l'image existe deja avec un chemin different.

    Args:
        file_path: Path object absolu vers le fichier
        relative_path: Chemin relatif a stocker en DB

    Returns:
        (image, created, error_message)
        - Si succes: (Image instance, bool created, None)
        - Si erreur: (None, False, error message string)
    """
    try:
        file_hash = calculate_file_hash(file_path)
        file_size = file_path.stat().st_size
        width, height = get_image_dimensions(file_path)

        image, created = Image.objects.get_or_create(
            file_hash=file_hash,
            defaults={
                'path': relative_path,
                'filename': file_path.name,
                'file_size': file_size,
                'width': width,
                'height': height,
            }
        )

        # Si l'image existe mais le chemin a change, mettre a jour
        if not created and image.path != relative_path:
            image.path = relative_path
            image.filename = file_path.name
            image.save()

        return image, created, None

    except Exception as e:
        return None, False, f"Error reading file: {str(e)}"


def create_faces_from_gpu_result(image, faces_data):
    """
    Cree les enregistrements Face a partir des resultats du GPU worker.

    Args:
        image: Instance Image
        faces_data: Liste des faces depuis le GPU worker

    Returns:
        Liste des Face IDs crees (strings)
    """
    faces_created = []
    for face_data in faces_data:
        face = Face.objects.create(
            image=image,
            bbox_x1=face_data['bbox'][0],
            bbox_y1=face_data['bbox'][1],
            bbox_x2=face_data['bbox'][2],
            bbox_y2=face_data['bbox'][3],
            det_score=face_data['det_score'],
            embedding=face_data['embedding'],
        )
        faces_created.append(str(face.id))
    return faces_created


def mark_image_as_scanned(image, faces_count):
    """
    Marque une image comme scannee avec la date actuelle.

    Args:
        image: Instance Image
        faces_count: Nombre de visages detectes
    """
    image.scanned = True
    image.scan_date = datetime.now()
    image.faces_count = faces_count
    image.save()


# =============================================================================
# Helpers pour la pagination
# =============================================================================

def parse_pagination_params(request, default_limit=20, max_limit=100):
    """
    Parse les parametres de pagination depuis la requete.

    Args:
        request: La requete Django
        default_limit: Limite par defaut
        max_limit: Limite maximum autorisee

    Returns:
        (page, limit, offset)
    """
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', default_limit))
    except ValueError:
        page = 1
        limit = default_limit

    if page < 1:
        page = 1
    if limit < 1 or limit > max_limit:
        limit = default_limit

    offset = (page - 1) * limit
    return page, limit, offset


def paginate_response(total_count, page, limit):
    """
    Calcule les metadonnees de pagination pour une reponse.

    Returns:
        dict avec total_count, page, limit, total_pages
    """
    return {
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
    }