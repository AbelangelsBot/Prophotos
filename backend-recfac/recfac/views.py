import os
import json
import requests
import numpy as np
from pathlib import Path
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.core.cache import cache

from .models import Image, Face, Person
from utils import calculate_file_hash, get_image_dimensions
from .utils import (
    verify_admin_token,
    verify_user_token,
    verify_admin_token_from_query,
    parse_json_body,
    validate_path_security,
    is_image_file,
    get_or_create_image_record,
    create_faces_from_gpu_result,
    mark_image_as_scanned,
    parse_pagination_params,
    paginate_response,
    check_rate_limit,
    IMAGE_EXTENSIONS,
)


ROOT_DIR = settings.FILES_ROOT_DIR
GPU_WORKER_URL = settings.GPU_WORKER_URL
GPU_WORKER_TOKEN = settings.GPU_WORKER_TOKEN


def _gpu_headers():
    """Retourne les headers d'authentification pour le GPU worker."""
    if GPU_WORKER_TOKEN:
        return {"X-Token": GPU_WORKER_TOKEN}
    return {}


def _vectorize_image(image_file, max_faces=0):
    """
    Vectorise une image en appelant le GPU worker.

    Args:
        image_file: Fichier image (UploadedFile Django)
        max_faces: Nombre maximum de visages à détecter (0 = tous)

    Returns:
        tuple: (success: bool, result: dict or error_message: str)

    Result format si succès:
        {
            "faces_found": int,
            "model": str,
            "results": [
                {
                    "bbox": [x1, y1, x2, y2],
                    "det_score": float,
                    "dim": int,
                    "embedding": [float...]
                }
            ]
        }
    """
    if not GPU_WORKER_URL:
        return False, "GPU_WORKER_URL not configured"

    try:
        files = {'image': (image_file.name, image_file.file, image_file.content_type)}
        params = {}
        if max_faces > 0:
            params['max_faces'] = max_faces

        resp = requests.post(
            f"{GPU_WORKER_URL}/embed_faces",
            headers=_gpu_headers(),
            files=files,
            params=params,
            timeout=60,
        )

        if not resp.ok:
            return False, f"GPU worker failed with status {resp.status_code}"

        gpu_result = resp.json()
        return True, gpu_result

    except requests.RequestException as exc:
        return False, f"GPU worker error: {str(exc)}"
    except ValueError as e:
        return False, f"Invalid GPU response: {str(e)}"


def _calculate_cosine_similarity(embedding1, embedding2):
    """
    Calcule la similarité cosine entre deux embeddings.

    Args:
        embedding1: Liste ou array numpy de floats (embedding normalisé)
        embedding2: Liste ou array numpy de floats (embedding normalisé)

    Returns:
        float: Similarité cosine (0-1, où 1 = identique)
    """
    emb1 = np.array(embedding1, dtype=np.float32)
    emb2 = np.array(embedding2, dtype=np.float32)

    # Produit scalaire (embeddings déjà normalisés par le GPU worker)
    similarity = float(np.dot(emb1, emb2))
    return similarity


def _calculate_cosine_distance(embedding1, embedding2):
    """
    Calcule la distance cosine entre deux embeddings.

    Args:
        embedding1: Liste ou array numpy de floats (embedding normalisé)
        embedding2: Liste ou array numpy de floats (embedding normalisé)

    Returns:
        float: Distance cosine (0-2, où 0 = identique)
    """
    similarity = _calculate_cosine_similarity(embedding1, embedding2)
    distance = 1.0 - similarity
    return distance


def _interpret_similarity(similarity):
    """
    Interprète un score de similarité.

    Args:
        similarity: float (0-1)

    Returns:
        str: Statut du match
    """
    if similarity >= 0.6:
        return "Match probable (même personne)"
    elif similarity >= 0.4:
        return "Incertain"
    else:
        return "Personnes différentes"


def _normalize_person_name(name):
    """
    Normalise un nom de personne pour éviter les doublons.
    - Supprime les espaces au début et à la fin
    - Normalise les espaces multiples en un seul espace
    - Met en forme: première lettre de chaque mot en majuscule

    Returns:
        str: Nom normalisé ou None si vide
    """
    if not name:
        return None

    # Supprimer espaces début/fin et normaliser espaces multiples
    normalized = " ".join(name.strip().split())

    # Si vide après normalisation
    if not normalized:
        return None

    # Mettre en forme: première lettre de chaque mot en majuscule
    # Ex: "john doe" -> "John Doe", "JOHN DOE" -> "John Doe"
    normalized = normalized.title()

    return normalized


def _update_person_average_embedding(person_name):
    """
    Calcule et met à jour l'embedding moyen d'une personne.
    Moyenne tous les embeddings des visages taggés avec cette personne,
    puis normalise le résultat.
    """
    # Récupérer tous les visages de cette personne
    faces = Face.objects.filter(person_name=person_name)

    if not faces.exists():
        return None

    # Extraire tous les embeddings
    embeddings = []
    for face in faces:
        emb = np.array(face.embedding, dtype=np.float32)
        embeddings.append(emb)

    # Calculer la moyenne
    embeddings_array = np.array(embeddings)
    average_emb = np.mean(embeddings_array, axis=0)

    # Normaliser l'embedding moyen
    norm = np.linalg.norm(average_emb)
    if norm > 1e-12:
        average_emb = average_emb / norm

    # Créer ou mettre à jour l'objet Person
    person, created = Person.objects.get_or_create(
        name=person_name,
        defaults={'reference_face': faces.first()}
    )

    person.average_embedding = average_emb.tolist()
    if not person.reference_face:
        person.reference_face = faces.first()
    person.save()

    return person


@csrf_exempt
def check_health(request):
    """
    Vérifie l'état du service recfac et du GPU worker.
    GET /recfac/check-health/
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    gpu_ok = False
    gpu_detail = {}

    if GPU_WORKER_URL:
        try:
            resp = requests.get(
                f"{GPU_WORKER_URL}/health",
                headers=_gpu_headers(),
                timeout=3,
            )
            gpu_ok = resp.ok
            try:
                gpu_detail = resp.json()
            except ValueError:
                gpu_detail = {
                    "status_code": resp.status_code,
                    "body": resp.text[:200],
                }
        except requests.RequestException as exc:
            gpu_detail = {"error": "GPU worker unreachable"}
    else:
        gpu_detail = {"error": "GPU_WORKER_URL not set"}

    # Réponse basique pour tout le monde
    response = {
        "service": "recfac",
        "ok": True,
        "gpu_worker_ok": gpu_ok,
    }

    # Détails supplémentaires seulement pour les admins
    success, _ = verify_admin_token(request)
    if success:
        response["gpu_worker"] = gpu_detail
        response["images_count"] = Image.objects.count()
        response["faces_count"] = Face.objects.count()
        response["persons_count"] = Person.objects.count()

    return JsonResponse(response)


@csrf_exempt
def scan_image(request):
    """
    Scan une image pour détecter les visages et extraire les embeddings.
    POST /recfac/scan-image/
    Body JSON: {"path": "relative/path/to/image.jpg"}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    relative_path = data.get("path", "")
    if not relative_path:
        return JsonResponse({"error": "Path is required."}, status=400)

    # Valider et construire le chemin
    is_valid, path_result = validate_path_security(relative_path)
    if not is_valid:
        return JsonResponse({"error": path_result}, status=400)
    file_path = path_result

    if not file_path.exists() or not file_path.is_file():
        return JsonResponse({"error": "File not found."}, status=404)

    # Vérifier que c'est une image
    if not is_image_file(file_path):
        return JsonResponse({"error": "Not an image file."}, status=400)

    # Récupérer ou créer l'enregistrement image
    image, created, error = get_or_create_image_record(file_path, relative_path)
    if error:
        return JsonResponse({"error": error}, status=500)

    # Si déjà scannée, retourner les résultats existants
    if image.scanned:
        return JsonResponse({
            "image_id": str(image.id),
            "already_scanned": True,
            "faces_count": image.faces_count,
            "scan_date": image.scan_date.isoformat() if image.scan_date else None,
        })

    # Vérifier que le GPU worker est configuré
    if not GPU_WORKER_URL:
        return JsonResponse({"error": "GPU_WORKER_URL not configured."}, status=503)

    # Appeler le GPU worker pour extraire les embeddings
    try:
        with open(file_path, 'rb') as f:
            files = {'image': (file_path.name, f, 'image/jpeg')}
            resp = requests.post(
                f"{GPU_WORKER_URL}/embed_faces",
                headers=_gpu_headers(),
                files=files,
                timeout=60,
            )
    except requests.RequestException as exc:
        return JsonResponse({"error": f"GPU worker error: {str(exc)}"}, status=502)

    if not resp.ok:
        try:
            detail = resp.json()
        except ValueError:
            detail = {"status_code": resp.status_code, "body": resp.text[:200]}
        return JsonResponse({"error": "GPU worker failed", "detail": detail}, status=resp.status_code)

    # Parser la réponse du GPU worker
    try:
        gpu_result = resp.json()
        faces_data = gpu_result.get("results", [])
    except ValueError:
        return JsonResponse({"error": "Invalid response from GPU worker."}, status=502)

    # Sauvegarder les faces détectées
    faces_created = create_faces_from_gpu_result(image, faces_data)

    # Marquer l'image comme scannée
    mark_image_as_scanned(image, len(faces_created))

    return JsonResponse({
        "image_id": str(image.id),
        "faces_count": len(faces_created),
        "faces": faces_created,
        "scan_date": image.scan_date.isoformat(),
    })


@csrf_exempt
def scan_multiple(request):
    """
    Scan plusieurs images pour détecter les visages.
    POST /recfac/scan-multiple/
    Body JSON: {"paths": ["path1.jpg", "path2.jpg", ...]}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    paths = data.get("paths", [])
    if not paths or not isinstance(paths, list):
        return JsonResponse({"error": "List of paths required."}, status=400)

    # Vérifier que le GPU worker est configuré
    if not GPU_WORKER_URL:
        return JsonResponse({"error": "GPU_WORKER_URL not configured."}, status=503)

    results = {
        "scanned": [],
        "already_scanned": [],
        "errors": [],
        "total_faces": 0
    }

    for relative_path in paths:
        if not relative_path:
            continue

        # Valider et construire le chemin
        is_valid, path_result = validate_path_security(relative_path)
        if not is_valid:
            results["errors"].append({"path": relative_path, "error": "Invalid path"})
            continue
        file_path = path_result

        if not file_path.exists() or not file_path.is_file():
            results["errors"].append({"path": relative_path, "error": "File not found"})
            continue

        # Vérifier que c'est une image
        if not is_image_file(file_path):
            results["errors"].append({"path": relative_path, "error": "Not an image file"})
            continue

        try:
            # Récupérer ou créer l'enregistrement image
            image, created, error = get_or_create_image_record(file_path, relative_path)
            if error:
                results["errors"].append({"path": relative_path, "error": error})
                continue

            # Si déjà scannée, skip
            if image.scanned:
                results["already_scanned"].append({
                    "path": relative_path,
                    "faces_count": image.faces_count
                })
                results["total_faces"] += image.faces_count
                continue

            # Appeler le GPU worker
            with open(file_path, 'rb') as f:
                files = {'image': (file_path.name, f, 'image/jpeg')}
                resp = requests.post(
                    f"{GPU_WORKER_URL}/embed_faces",
                    headers=_gpu_headers(),
                    files=files,
                    timeout=60,
                )

            if not resp.ok:
                results["errors"].append({"path": relative_path, "error": f"GPU worker failed: {resp.status_code}"})
                continue

            # Parser la réponse
            gpu_result = resp.json()
            faces_data = gpu_result.get("results", [])

            # Sauvegarder les faces
            faces_created = create_faces_from_gpu_result(image, faces_data)

            # Marquer comme scanné
            mark_image_as_scanned(image, len(faces_created))

            results["scanned"].append({
                "path": relative_path,
                "faces_count": len(faces_created)
            })
            results["total_faces"] += len(faces_created)

        except requests.RequestException as exc:
            results["errors"].append({"path": relative_path, "error": f"GPU worker error: {str(exc)}"})
        except Exception as e:
            results["errors"].append({"path": relative_path, "error": str(e)})

    return JsonResponse({
        "message": f"{len(results['scanned'])} image(s) scannée(s)",
        "scanned_count": len(results["scanned"]),
        "already_scanned_count": len(results["already_scanned"]),
        "errors_count": len(results["errors"]),
        "total_faces": results["total_faces"],
        "details": results
    })


@csrf_exempt
def search_face(request):
    """
    Recherche des visages similaires à partir d'une image uploadée ou d'un face_id.
    POST /recfac/search-face/
    Body: multipart/form-data avec "image" OU JSON avec {"face_id": "uuid"}
    Query params: ?threshold=0.6 (similarité minimale, défaut 0.6)
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token
    success, result = verify_user_token(request)
    if not success:
        return result

    try:
        threshold = float(request.GET.get('threshold', '0.6'))
    except (ValueError, TypeError):
        threshold = 0.6
    threshold = max(0.0, min(1.0, threshold))

    query_embedding = None

    # Cas 1: Recherche par face_id
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            face_id = data.get('face_id')
            if not face_id:
                return JsonResponse({"error": "face_id required in JSON body."}, status=400)

            try:
                face = Face.objects.get(id=face_id)
                query_embedding = np.array(face.embedding, dtype=np.float32)
            except Face.DoesNotExist:
                return JsonResponse({"error": "Face not found."}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)

    # Cas 2: Recherche par upload d'image
    elif 'image' in request.FILES:
        uploaded_file = request.FILES['image']

        # Utiliser la fonction helper pour vectoriser
        success, result = _vectorize_image(uploaded_file, max_faces=1)
        if not success:
            return JsonResponse({"error": result}, status=502)

        faces_data = result.get("results", [])
        if not faces_data:
            return JsonResponse({"error": "No face detected in uploaded image."}, status=400)

        query_embedding = faces_data[0]['embedding']
    else:
        return JsonResponse({"error": "Provide either 'image' file or JSON with 'face_id'."}, status=400)

    # Limiter le nombre de résultats
    try:
        max_results = int(request.GET.get('limit', '50'))
    except (ValueError, TypeError):
        max_results = 50
    max_results = max(1, min(200, max_results))
    query_emb = np.array(query_embedding, dtype=np.float32)

    # 1. Comparer avec les embeddings moyens des personnes (plus rapide, moins d'entrées)
    persons_matches = []
    all_persons = Person.objects.exclude(average_embedding__isnull=True).only('name', 'average_embedding')

    for person in all_persons:
        similarity = float(np.dot(query_emb, np.array(person.average_embedding, dtype=np.float32)))
        if similarity >= threshold:
            persons_matches.append({
                "person_name": person.name,
                "similarity": round(similarity, 4),
                "match_type": "person_average",
            })

    # 2. Recherche vectorisée sur les visages (batch processing)
    # Charger seulement les champs nécessaires
    faces_data = list(
        Face.objects
        .select_related('image')
        .only('id', 'embedding', 'person_name', 'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2',
              'image__id', 'image__path')
        .all()
    )

    if faces_data:
        # Créer une matrice de tous les embeddings pour calcul vectorisé
        embeddings_matrix = np.array([f.embedding for f in faces_data], dtype=np.float32)

        # Calcul de similarité vectorisé (produit scalaire avec embeddings normalisés)
        similarities = np.dot(embeddings_matrix, query_emb)

        # Filtrer par threshold et créer les résultats
        similar_faces = []
        for i, sim in enumerate(similarities):
            if sim >= threshold:
                face = faces_data[i]
                similar_faces.append({
                    "face_id": str(face.id),
                    "image_id": str(face.image.id),
                    "image_path": face.image.path,
                    "similarity": round(float(sim), 4),
                    "bbox": [face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2],
                    "person_name": face.person_name,
                    "match_type": "face",
                })

        # Trier et limiter
        similar_faces.sort(key=lambda x: x['similarity'], reverse=True)
        similar_faces = similar_faces[:max_results]
    else:
        similar_faces = []

    persons_matches.sort(key=lambda x: x['similarity'], reverse=True)

    return JsonResponse({
        "count": len(similar_faces),
        "threshold": threshold,
        "results": similar_faces,
        "persons_matches": persons_matches,
    })


@csrf_exempt
def tag_face(request):
    """
    Tagger un visage avec le nom d'une personne.
    POST /recfac/face/tag/
    Body JSON: {"face_id": "uuid", "person_name": "John Doe"}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    face_id = data.get("face_id")
    person_name = _normalize_person_name(data.get("person_name", ""))

    if not face_id:
        return JsonResponse({"error": "face_id required."}, status=400)

    try:
        face = Face.objects.get(id=face_id)
    except Face.DoesNotExist:
        return JsonResponse({"error": "Face not found."}, status=404)

    # Sauvegarder l'ancien nom pour recalculer les embeddings moyens
    old_person_name = face.person_name

    # Mettre à jour le nom (déjà normalisé)
    face.person_name = person_name
    face.save()

    # Recalculer l'embedding moyen pour la nouvelle personne (si taggée)
    if person_name:
        _update_person_average_embedding(person_name)

    # Recalculer l'embedding moyen pour l'ancienne personne (si elle en avait une)
    if old_person_name and old_person_name != person_name:
        _update_person_average_embedding(old_person_name)

    # Invalider le cache des personnes
    _invalidate_persons_cache()

    return JsonResponse({
        "face_id": str(face.id),
        "person_name": face.person_name,
        "updated": True,
    })


@csrf_exempt
def tag_face_with_similarity(request):
    """
    Tagger un visage et tous les visages similaires avec le nom d'une personne.
    POST /recfac/face/tag-with-similarity/
    Body JSON: {"face_id": "uuid", "person_name": "John Doe", "similarity_threshold": 0.6}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    face_id = data.get("face_id")
    person_name = _normalize_person_name(data.get("person_name", ""))
    try:
        similarity_threshold = float(data.get("similarity_threshold", 0.6))
    except (ValueError, TypeError):
        similarity_threshold = 0.6
    similarity_threshold = max(0.0, min(1.0, similarity_threshold))

    if not face_id:
        return JsonResponse({"error": "face_id required."}, status=400)

    if not person_name:
        return JsonResponse({"error": "person_name required."}, status=400)

    try:
        reference_face = Face.objects.get(id=face_id)
    except Face.DoesNotExist:
        return JsonResponse({"error": "Face not found."}, status=404)

    # Obtenir l'embedding du visage de référence
    reference_embedding = np.array(reference_face.embedding, dtype=np.float32)

    # Transaction atomique pour garantir la cohérence des données
    with transaction.atomic():
        # Tagger le visage de référence
        reference_face.person_name = person_name
        reference_face.save()
        tagged_faces_ids = [str(reference_face.id)]

        # Charger tous les autres visages avec leurs images (optimisé)
        all_faces = list(
            Face.objects.exclude(id=face_id)
            .select_related('image')
            .only('id', 'embedding', 'person_name', 'image__path')
        )

        if not all_faces:
            # Pas d'autres visages à comparer
            tagged_faces = []
        else:
            # Calcul vectorisé des similarités avec numpy
            embeddings_matrix = np.array([f.embedding for f in all_faces], dtype=np.float32)
            # Normaliser l'embedding de référence
            ref_norm = reference_embedding / (np.linalg.norm(reference_embedding) + 1e-10)
            # Produit scalaire = similarité cosinus
            similarities = np.dot(embeddings_matrix, ref_norm)

            # Trouver les indices des visages similaires
            similar_mask = similarities >= similarity_threshold
            similar_indices = np.where(similar_mask)[0]

            # Préparer les visages à mettre à jour
            faces_to_update = []
            tagged_faces = []

            for idx in similar_indices:
                face = all_faces[idx]
                similarity = float(similarities[idx])
                face.person_name = person_name
                faces_to_update.append(face)
                tagged_faces.append({
                    "face_id": str(face.id),
                    "similarity": similarity,
                    "image_path": face.image.path,
                })
                tagged_faces_ids.append(str(face.id))

            # Mise à jour en batch
            if faces_to_update:
                Face.objects.bulk_update(faces_to_update, ['person_name'])

        # Recalculer l'embedding moyen pour cette personne
        _update_person_average_embedding(person_name)

    # Invalider le cache des personnes (hors transaction)
    _invalidate_persons_cache()

    return JsonResponse({
        "reference_face_id": str(reference_face.id),
        "person_name": person_name,
        "similar_faces_tagged": len(tagged_faces),
        "total_faces_tagged": len(tagged_faces_ids),
        "tagged_faces": tagged_faces,
        "similarity_threshold": similarity_threshold,
    })


PERSONS_CACHE_KEY = 'recfac_persons_list'
PERSONS_CACHE_TIMEOUT = 60  # 1 minute cache


def _invalidate_persons_cache():
    """Invalide le cache des personnes après modification."""
    cache.delete(PERSONS_CACHE_KEY)


@csrf_exempt
def list_persons(request):
    """
    Liste toutes les personnes (person_name uniques).
    GET /recfac/persons/
    Requiert authentification utilisateur.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token utilisateur
    success, result = verify_user_token(request)
    if not success:
        return result

    # Essayer de récupérer depuis le cache
    cached_result = cache.get(PERSONS_CACHE_KEY)
    if cached_result is not None:
        return JsonResponse(cached_result)

    # Récupérer les person_name uniques avec comptage en une seule query
    from django.db.models import Count

    persons = (
        Face.objects
        .filter(person_name__isnull=False)
        .exclude(person_name='')
        .values('person_name')
        .annotate(faces_count=Count('id'))
        .order_by('person_name')
    )

    # Conversion directe en liste (les noms sont déjà normalisés à la sauvegarde)
    persons_list = [
        {"name": p['person_name'], "faces_count": p['faces_count']}
        for p in persons
        if p['person_name'].strip()  # Filtre sécurité
    ]

    result = {
        "count": len(persons_list),
        "persons": persons_list,
    }

    # Mettre en cache
    cache.set(PERSONS_CACHE_KEY, result, PERSONS_CACHE_TIMEOUT)

    return JsonResponse(result)


@csrf_exempt
def get_multiple_persons_faces(request):
    """
    Retourne les faces de plusieurs personnes.
    POST /recfac/persons/faces-multiple/
    Body JSON: {"names": ["John Doe", "Jane Doe"], "mode": "union"}

    Modes:
    - "union" (default): retourne les images contenant AU MOINS UNE des personnes
    - "intersection": retourne les images contenant TOUTES les personnes

    Requiert authentification utilisateur.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token utilisateur
    success, result = verify_user_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    names = data.get("names", [])
    mode = data.get("mode", "union")  # "union" ou "intersection"

    if not names or not isinstance(names, list):
        return JsonResponse({"error": "List of names required."}, status=400)

    if mode not in ["union", "intersection"]:
        return JsonResponse({"error": "mode must be 'union' or 'intersection'."}, status=400)

    # Nettoyer les noms
    clean_names = [n.strip() for n in names if n and n.strip()]
    if not clean_names:
        return JsonResponse({"error": "At least one valid name required."}, status=400)

    if mode == "union":
        # Union: images contenant AU MOINS UNE des personnes
        # Récupérer tous les chemins d'images uniques
        image_paths = set()
        persons_found = {}

        for name in clean_names:
            faces = Face.objects.filter(person_name__iexact=name).select_related('image')
            paths_for_person = set()
            for face in faces:
                image_paths.add(face.image.path)
                paths_for_person.add(face.image.path)
            persons_found[name] = len(paths_for_person)

        return JsonResponse({
            "mode": "union",
            "names": clean_names,
            "persons_found": persons_found,
            "images_count": len(image_paths),
            "image_paths": list(image_paths),
        })

    else:
        # Intersection: images contenant TOUTES les personnes
        # Pour chaque personne, récupérer l'ensemble des chemins d'images
        path_sets = []
        persons_found = {}

        for name in clean_names:
            faces = Face.objects.filter(person_name__iexact=name).select_related('image')
            paths_for_person = set(face.image.path for face in faces)
            path_sets.append(paths_for_person)
            persons_found[name] = len(paths_for_person)

        # Intersection de tous les ensembles
        if path_sets:
            common_paths = path_sets[0]
            for s in path_sets[1:]:
                common_paths = common_paths.intersection(s)
        else:
            common_paths = set()

        return JsonResponse({
            "mode": "intersection",
            "names": clean_names,
            "persons_found": persons_found,
            "images_count": len(common_paths),
            "image_paths": list(common_paths),
        })


@csrf_exempt
def get_person_faces(request):
    """
    Retourne toutes les faces d'une personne.
    GET /recfac/person/faces/?name=John%20Doe
    Requiert authentification utilisateur.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token utilisateur
    success, result = verify_user_token(request)
    if not success:
        return result

    person_name = request.GET.get('name', '').strip()
    if not person_name:
        return JsonResponse({"error": "name parameter required."}, status=400)

    # Utiliser une recherche case-insensitive pour plus de flexibilité
    faces = Face.objects.filter(person_name__iexact=person_name).select_related('image')

    faces_list = []
    for face in faces:
        faces_list.append({
            "face_id": str(face.id),
            "image_id": str(face.image.id),
            "image_path": face.image.path,
            "bbox": [face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2],
            "det_score": face.det_score,
        })

    return JsonResponse({
        "person_name": person_name,
        "faces_count": len(faces_list),
        "faces": faces_list,
    })


@csrf_exempt
def get_image_details(request):
    """
    Retourne les détails enrichis d'une image avec informations recfac.
    GET /recfac/image-details/?path=relative/path/to/image.jpg
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token
    success, result = verify_user_token(request)
    if not success:
        return result

    relative_path = request.GET.get('path', '').strip()
    if not relative_path:
        return JsonResponse({"error": "path parameter required."}, status=400)

    # Chercher l'image dans la DB par path
    try:
        image = Image.objects.get(path=relative_path)
    except Image.DoesNotExist:
        return JsonResponse({
            "path": relative_path,
            "scanned": False,
            "exists_in_db": False,
        })

    # Récupérer les visages de cette image (une seule query)
    faces = list(image.faces.all())

    # Compter les personnes uniques avec une seule query annotée
    from django.db.models import Count
    persons_in_image = (
        image.faces
        .filter(person_name__isnull=False)
        .exclude(person_name='')
        .values('person_name')
        .annotate(faces_count=Count('id'))
        .order_by('person_name')
    )
    persons_list = [
        {"name": p['person_name'], "faces_count": p['faces_count']}
        for p in persons_in_image
    ]

    # Détails des visages (déjà chargés en mémoire)
    faces_list = [
        {
            "face_id": str(face.id),
            "bbox": [face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2],
            "det_score": face.det_score,
            "person_name": face.person_name,
        }
        for face in faces
    ]

    return JsonResponse({
        "image_id": str(image.id),
        "path": image.path,
        "filename": image.filename,
        "file_size": image.file_size,
        "width": image.width,
        "height": image.height,
        "scanned": image.scanned,
        "scan_date": image.scan_date.isoformat() if image.scan_date else None,
        "faces_count": image.faces_count,
        "persons_count": len(persons_list),
        "persons": persons_list,
        "faces": faces_list,
        "exists_in_db": True,
    })


@csrf_exempt
def get_untagged_faces(request):
    """
    Récupère les visages non taggés avec pagination.
    GET /recfac/faces/untagged/?page=1&limit=20
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Pagination
    page, limit, offset = parse_pagination_params(request)

    # Récupérer les visages non taggés
    untagged_faces = Face.objects.filter(
        Q(person_name__isnull=True) | Q(person_name='')
    ).select_related('image').order_by('-image__scan_date', 'id')

    total_count = untagged_faces.count()
    faces_page = untagged_faces[offset:offset + limit]

    faces_list = []
    for face in faces_page:
        # Générer le thumbnail du visage (crop de l'image)
        face_data = {
            "face_id": str(face.id),
            "bbox": [face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2],
            "det_score": face.det_score,
            "image_path": face.image.path if face.image else None,
            "image_id": str(face.image.id) if face.image else None,
            "scan_date": face.image.scan_date.isoformat() if face.image and face.image.scan_date else None,
        }
        faces_list.append(face_data)

    pagination = paginate_response(total_count, page, limit)
    return JsonResponse({
        **pagination,
        "faces": faces_list,
    })


@csrf_exempt
def delete_face(request):
    """
    Supprime un visage de la base de données.
    DELETE /recfac/face/delete/
    Body JSON: {"face_id": "uuid"}
    """
    if request.method != "DELETE" and request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    face_id = data.get("face_id")
    if not face_id:
        return JsonResponse({"error": "face_id required."}, status=400)

    try:
        face = Face.objects.get(id=face_id)
    except Face.DoesNotExist:
        return JsonResponse({"error": "Face not found."}, status=404)

    # Sauvegarder les infos pour la réponse
    image = face.image
    person_name = face.person_name

    # Supprimer le visage
    face.delete()

    # Mettre à jour le compteur de visages de l'image
    if image:
        image.faces_count = image.faces.count()
        image.save()

    # Recalculer l'embedding moyen de la personne si elle était taggée
    if person_name:
        _update_person_average_embedding(person_name)

    return JsonResponse({
        "success": True,
        "deleted_face_id": face_id,
        "image_path": image.path if image else None,
    })


@csrf_exempt
def get_face_image(request):
    """
    Récupère l'image croppée d'un visage (thumbnail).
    GET /recfac/face/image/?face_id=uuid
    Retourne l'image en base64.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token
    success, result = verify_user_token(request)
    if not success:
        return result

    face_id = request.GET.get('face_id')
    if not face_id:
        return JsonResponse({"error": "face_id required."}, status=400)

    try:
        face = Face.objects.select_related('image').get(id=face_id)
    except Face.DoesNotExist:
        return JsonResponse({"error": "Face not found."}, status=404)

    if not face.image:
        return JsonResponse({"error": "Image not found for this face."}, status=404)

    # Charger l'image originale
    image_path = os.path.join(ROOT_DIR, face.image.path)
    if not os.path.exists(image_path):
        return JsonResponse({"error": "Image file not found."}, status=404)

    try:
        from PIL import Image as PILImage
        import base64
        from io import BytesIO

        img = PILImage.open(image_path)

        # Crop le visage avec une marge de 20%
        bbox = [face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2]
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        margin = 0.2

        crop_x1 = max(0, int(bbox[0] - width * margin))
        crop_y1 = max(0, int(bbox[1] - height * margin))
        crop_x2 = min(img.width, int(bbox[2] + width * margin))
        crop_y2 = min(img.height, int(bbox[3] + height * margin))

        face_crop = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))

        # Redimensionner à une taille raisonnable (150x150 max)
        max_size = 150
        face_crop.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)

        # Convertir en base64
        buffer = BytesIO()
        face_crop.save(buffer, format='JPEG', quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return JsonResponse({
            "face_id": str(face.id),
            "image": f"data:image/jpeg;base64,{img_base64}",
            "bbox": bbox,
            "image_path": face.image.path,
        })

    except Exception as e:
        return JsonResponse({"error": f"Error processing image: {str(e)}"}, status=500)


@csrf_exempt
def test_vectorize(request):
    """
    Test endpoint pour vectorisation d'image sans sauvegarde en base.
    POST /recfac/test-vectorize/
    Body: multipart/form-data avec "image"
    Retourne les faces détectées avec bboxes et embeddings pour affichage test.

    Rate limited: 10 requêtes par minute par IP.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Rate limiting pour éviter l'abus des ressources GPU
    is_allowed, error_response = check_rate_limit(request)
    if not is_allowed:
        return error_response

    if 'image' not in request.FILES:
        return JsonResponse({"error": "Image file required."}, status=400)

    uploaded_file = request.FILES['image']

    # Utiliser la fonction helper pour vectoriser
    success, result = _vectorize_image(uploaded_file)

    if not success:
        return JsonResponse({"error": result}, status=502)

    # Retourner les résultats bruts pour affichage test
    return JsonResponse({
        "faces_found": result.get("faces_found", 0),
        "model": result.get("model", "unknown"),
        "results": result.get("results", []),
    })


@csrf_exempt
def recalculate_persons_embeddings(request):
    """
    Recalcule les embeddings moyens de toutes les personnes.
    POST /recfac/recalculate-persons-embeddings/
    Utile après avoir importé/modifié beaucoup de faces.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Récupérer tous les noms de personnes uniques
    person_names = Face.objects.filter(person_name__isnull=False).values_list('person_name', flat=True).distinct()

    updated_count = 0
    for person_name in person_names:
        person = _update_person_average_embedding(person_name)
        if person:
            updated_count += 1

    return JsonResponse({
        "updated_count": updated_count,
        "message": f"{updated_count} personne(s) mise(s) à jour avec succès",
    })


@csrf_exempt
def scan_all_images(request):
    """
    Scan toutes les images du répertoire root pour détecter les visages.
    GET /recfac/scan-all-images/?token=xxx
    Streaming: Retourne des messages de progression en temps réel via Server-Sent Events.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed. Use GET for SSE."}, status=405)

    # Vérification du token (admin seulement) - récupéré depuis query params pour EventSource
    success, result = verify_admin_token_from_query(request)
    if not success:
        return result

    # Fonction generator pour le streaming
    def scan_progress():
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from io import BytesIO

        # Récupérer toutes les images du répertoire
        root = Path(ROOT_DIR).resolve()

        # Compter d'abord le total
        all_image_files = []
        for ext in IMAGE_EXTENSIONS:
            all_image_files.extend(list(root.rglob(f"*{ext}")))
            all_image_files.extend(list(root.rglob(f"*{ext.upper()}")))

        total = len(all_image_files)

        yield f"data: {json.dumps({'status': 'started', 'total': total})}\n\n"

        processed = 0
        success_count = 0
        error_count = 0
        already_scanned_count = 0
        errors = []

        for file_path in all_image_files:
            processed += 1

            try:
                # Calculer le chemin relatif
                relative_path = str(file_path.relative_to(root))

                # Calculer le hash du fichier
                file_hash = calculate_file_hash(file_path)
                file_size = file_path.stat().st_size
                width, height = get_image_dimensions(file_path)

                # Chercher ou créer l'image dans la DB
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

                # Si l'image existe mais le chemin a changé, mettre à jour
                if not created and image.path != relative_path:
                    image.path = relative_path
                    image.filename = file_path.name
                    image.save()

                # Si déjà scannée, skip
                if image.scanned:
                    already_scanned_count += 1
                    yield f"data: {json.dumps({'status': 'progress', 'processed': processed, 'total': total, 'current': relative_path, 'result': 'already_scanned'})}\n\n"
                    continue

                # Appeler le GPU worker
                with open(file_path, 'rb') as f:
                    files = {'image': (file_path.name, f, 'image/jpeg')}
                    resp = requests.post(
                        f"{GPU_WORKER_URL}/embed_faces",
                        headers=_gpu_headers(),
                        files=files,
                        timeout=60,
                    )

                if not resp.ok:
                    error_count += 1
                    error_msg = f"GPU worker failed with status {resp.status_code}"
                    errors.append({'file': relative_path, 'error': error_msg})
                    yield f"data: {json.dumps({'status': 'progress', 'processed': processed, 'total': total, 'current': relative_path, 'result': 'error', 'error': error_msg})}\n\n"
                    continue

                gpu_result = resp.json()
                faces_data = gpu_result.get("results", [])

                # Sauvegarder les faces détectées
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

                # Marquer l'image comme scannée
                image.scanned = True
                image.scan_date = datetime.now()
                image.faces_count = len(faces_created)
                image.save()

                success_count += 1
                yield f"data: {json.dumps({'status': 'progress', 'processed': processed, 'total': total, 'current': relative_path, 'result': 'success', 'faces_count': len(faces_created)})}\n\n"

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                errors.append({'file': str(file_path), 'error': error_msg})
                yield f"data: {json.dumps({'status': 'progress', 'processed': processed, 'total': total, 'current': str(file_path), 'result': 'error', 'error': error_msg})}\n\n"

        # Envoyer le résumé final
        yield f"data: {json.dumps({'status': 'completed', 'total': total, 'success': success_count, 'errors': error_count, 'already_scanned': already_scanned_count, 'error_details': errors})}\n\n"

    # Retourner une réponse en streaming
    from django.http import StreamingHttpResponse
    response = StreamingHttpResponse(scan_progress(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
def scan_folder(request):
    """
    Scan toutes les images d'un dossier spécifique pour détecter les visages.
    GET /recfac/scan-folder/?token=xxx&folder_path=relative/path
    Streaming: Retourne des messages de progression en temps réel via Server-Sent Events.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed. Use GET for SSE."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token_from_query(request)
    if not success:
        return result

    # Récupérer le chemin du dossier
    folder_path = request.GET.get("folder_path", "").strip()

    # Fonction generator pour le streaming
    def scan_progress():
        root = Path(ROOT_DIR).resolve()

        # Construire le chemin du dossier à scanner
        if folder_path:
            target_folder = (root / folder_path).resolve()
            # Vérification de sécurité: le dossier doit être dans root
            try:
                target_folder.relative_to(root)
            except ValueError:
                data = {'status': 'error', 'message': 'Invalid folder path'}
                yield f"data: {json.dumps(data)}\n\n"
                return
        else:
            target_folder = root

        if not target_folder.exists() or not target_folder.is_dir():
            data = {'status': 'error', 'message': 'Folder does not exist'}
            yield f"data: {json.dumps(data)}\n\n"
            return

        # Compter d'abord le total (seulement dans ce dossier, pas récursif)
        all_image_files = []
        for ext in IMAGE_EXTENSIONS:
            all_image_files.extend(list(target_folder.glob(f"*{ext}")))
            all_image_files.extend(list(target_folder.glob(f"*{ext.upper()}")))

        # Filtrer pour ne garder que les fichiers (pas les dossiers)
        all_image_files = [f for f in all_image_files if f.is_file()]

        total = len(all_image_files)

        data = {'status': 'started', 'total': total, 'folder': folder_path or '/'}
        yield f"data: {json.dumps(data)}\n\n"

        processed = 0
        success_count = 0
        error_count = 0
        already_scanned_count = 0
        errors = []
        total_faces = 0

        for file_path in all_image_files:
            processed += 1

            try:
                # Calculer le chemin relatif
                relative_path = str(file_path.relative_to(root))

                # Calculer le hash du fichier
                file_hash = calculate_file_hash(file_path)
                file_size = file_path.stat().st_size
                width, height = get_image_dimensions(file_path)

                # Chercher ou créer l'image dans la DB
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

                # Si l'image existe mais le chemin a changé, mettre à jour
                if not created and image.path != relative_path:
                    image.path = relative_path
                    image.filename = file_path.name
                    image.save()

                # Si déjà scannée, skip
                if image.scanned:
                    already_scanned_count += 1
                    data = {'status': 'progress', 'processed': processed, 'total': total, 'total_faces': total_faces, 'errors': error_count, 'current_image': relative_path, 'result': 'already_scanned'}
                    yield f"data: {json.dumps(data)}\n\n"
                    continue

                # Appeler le GPU worker
                with open(file_path, 'rb') as f:
                    files = {'image': (file_path.name, f, 'image/jpeg')}
                    resp = requests.post(
                        f"{GPU_WORKER_URL}/embed_faces",
                        headers=_gpu_headers(),
                        files=files,
                        timeout=60,
                    )

                if not resp.ok:
                    error_count += 1
                    error_msg = f"GPU worker failed with status {resp.status_code}"
                    errors.append({'file': relative_path, 'error': error_msg})
                    data = {'status': 'progress', 'processed': processed, 'total': total, 'total_faces': total_faces, 'errors': error_count, 'current_image': relative_path, 'result': 'error', 'error': error_msg}
                    yield f"data: {json.dumps(data)}\n\n"
                    continue

                gpu_result = resp.json()
                faces_data = gpu_result.get("results", [])

                # Sauvegarder les faces détectées
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
                    faces_created.append(face)

                total_faces += len(faces_created)

                # Marquer l'image comme scannée
                image.scanned = True
                image.scan_date = datetime.now()
                image.faces_count = len(faces_created)
                image.save()

                success_count += 1
                data = {'status': 'progress', 'processed': processed, 'total': total, 'total_faces': total_faces, 'errors': error_count, 'current_image': relative_path, 'result': 'success', 'faces_count': len(faces_created)}
                yield f"data: {json.dumps(data)}\n\n"

            except Exception as e:
                error_count += 1
                error_msg = str(e)
                errors.append({'file': str(file_path), 'error': error_msg})
                data = {'status': 'progress', 'processed': processed, 'total': total, 'total_faces': total_faces, 'errors': error_count, 'current_image': str(file_path), 'result': 'error', 'error': error_msg}
                yield f"data: {json.dumps(data)}\n\n"

        # Envoyer le résumé final
        data = {'status': 'completed', 'total': total, 'success': success_count, 'errors': error_count, 'already_scanned': already_scanned_count, 'total_faces': total_faces, 'error_details': errors}
        yield f"data: {json.dumps(data)}\n\n"

    # Retourner une réponse en streaming
    from django.http import StreamingHttpResponse
    response = StreamingHttpResponse(scan_progress(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
def delete_image(request):
    """
    Supprime les données recfac d'une image (faces, tags, etc.).
    Appelé par le service files lors de la suppression d'un fichier.
    POST /recfac/delete-image/
    Body JSON: {"path": "relative/path/to/image.jpg"}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    relative_path = data.get("path", "")
    if not relative_path:
        return JsonResponse({"error": "Path is required."}, status=400)

    # Chercher l'image dans la DB par path
    try:
        image = Image.objects.get(path=relative_path)
    except Image.DoesNotExist:
        return JsonResponse({
            "path": relative_path,
            "deleted": False,
            "message": "Image not found in recfac database",
        })

    # Récupérer les personnes affectées avant suppression
    affected_persons = list(
        image.faces.filter(person_name__isnull=False)
        .exclude(person_name='')
        .values_list('person_name', flat=True)
        .distinct()
    )

    faces_count = image.faces_count
    image_id = str(image.id)

    # Supprimer l'image (CASCADE supprimera automatiquement les faces)
    image.delete()

    # Recalculer les embeddings moyens pour les personnes affectées
    persons_updated = []
    for person_name in affected_persons:
        # Vérifier s'il reste des faces pour cette personne
        remaining_faces = Face.objects.filter(person_name=person_name).count()
        if remaining_faces > 0:
            _update_person_average_embedding(person_name)
            persons_updated.append({"name": person_name, "remaining_faces": remaining_faces})
        else:
            # Supprimer la personne si elle n'a plus de faces
            Person.objects.filter(name=person_name).delete()
            persons_updated.append({"name": person_name, "deleted": True})

    return JsonResponse({
        "path": relative_path,
        "image_id": image_id,
        "deleted": True,
        "faces_deleted": faces_count,
        "persons_affected": persons_updated,
    })


@csrf_exempt
def delete_multiple_images(request):
    """
    Supprime les données recfac de plusieurs images.
    POST /recfac/delete-multiple/
    Body JSON: {"paths": ["path1.jpg", "path2.jpg", ...]}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token (admin seulement)
    success, result = verify_admin_token(request)
    if not success:
        return result

    # Parser le body JSON
    success, data = parse_json_body(request)
    if not success:
        return data

    paths = data.get("paths", [])
    if not paths or not isinstance(paths, list):
        return JsonResponse({"error": "List of paths required."}, status=400)

    results = {
        "deleted": [],
        "not_found": [],
        "total_faces_deleted": 0,
    }

    all_affected_persons = set()

    for relative_path in paths:
        if not relative_path:
            continue

        try:
            image = Image.objects.get(path=relative_path)

            # Récupérer les personnes affectées
            affected_persons = list(
                image.faces.filter(person_name__isnull=False)
                .exclude(person_name='')
                .values_list('person_name', flat=True)
                .distinct()
            )
            all_affected_persons.update(affected_persons)

            faces_count = image.faces_count
            results["total_faces_deleted"] += faces_count

            # Supprimer l'image
            image.delete()
            results["deleted"].append({
                "path": relative_path,
                "faces_deleted": faces_count,
            })

        except Image.DoesNotExist:
            results["not_found"].append(relative_path)

    # Recalculer les embeddings moyens pour toutes les personnes affectées
    persons_updated = []
    for person_name in all_affected_persons:
        remaining_faces = Face.objects.filter(person_name=person_name).count()
        if remaining_faces > 0:
            _update_person_average_embedding(person_name)
            persons_updated.append({"name": person_name, "remaining_faces": remaining_faces})
        else:
            Person.objects.filter(name=person_name).delete()
            persons_updated.append({"name": person_name, "deleted": True})

    return JsonResponse({
        "message": f"{len(results['deleted'])} image(s) supprimée(s) de recfac",
        "deleted_count": len(results["deleted"]),
        "not_found_count": len(results["not_found"]),
        "total_faces_deleted": results["total_faces_deleted"],
        "persons_affected": persons_updated,
        "details": results,
    })


@csrf_exempt
def test_compare_faces(request):
    """
    Test endpoint pour comparer deux visages (similarité/distance).
    POST /recfac/test-compare-faces/
    Body: multipart/form-data avec "image1" et "image2"
    Retourne la similarité entre les deux premiers visages détectés.

    Rate limited: 10 requêtes par minute par IP.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Rate limiting pour éviter l'abus des ressources GPU
    is_allowed, error_response = check_rate_limit(request)
    if not is_allowed:
        return error_response

    if 'image1' not in request.FILES or 'image2' not in request.FILES:
        return JsonResponse({"error": "Two images required (image1 and image2)."}, status=400)

    image1 = request.FILES['image1']
    image2 = request.FILES['image2']

    # Vectoriser les deux images
    success1, result1 = _vectorize_image(image1, max_faces=1)
    if not success1:
        return JsonResponse({"error": f"Image 1: {result1}"}, status=400)

    # Reset file pointer pour image2
    image2.seek(0)
    success2, result2 = _vectorize_image(image2, max_faces=1)
    if not success2:
        return JsonResponse({"error": f"Image 2: {result2}"}, status=400)

    # Vérifier qu'on a détecté des visages
    faces1 = result1.get("results", [])
    faces2 = result2.get("results", [])

    if not faces1:
        return JsonResponse({"error": "Image 1: No face detected"}, status=400)
    if not faces2:
        return JsonResponse({"error": "Image 2: No face detected"}, status=400)

    face1 = faces1[0]
    face2 = faces2[0]

    # Utiliser les fonctions helpers pour calculer similarité et distance
    similarity = _calculate_cosine_similarity(face1['embedding'], face2['embedding'])
    distance = _calculate_cosine_distance(face1['embedding'], face2['embedding'])
    match_status = _interpret_similarity(similarity)

    return JsonResponse({
        "similarity": round(similarity, 4),
        "distance": round(distance, 4),
        "match_status": match_status,
        "face1": {
            "bbox": face1['bbox'],
            "det_score": face1['det_score'],
            "dim": face1['dim'],
        },
        "face2": {
            "bbox": face2['bbox'],
            "det_score": face2['det_score'],
            "dim": face2['dim'],
        },
    })
