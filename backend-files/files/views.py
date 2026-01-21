from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
import os
import shutil
import base64
import json
from PIL import Image
from io import BytesIO
from utils import verify_token
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import threading
import requests
import logging

logger = logging.getLogger(__name__)


ROOT_DIR = os.environ.get("FILES_ROOT_DIR")
RECFAC_API_URL = os.environ.get("RECFAC_API_URL", "http://backend-recfac:8001")


def scan_image_async(image_path, token):
    """
    Appel asynchrone vers le service Recfac pour scanner une image.
    Cette fonction est appelée dans un thread séparé pour ne pas bloquer l'upload.
    """
    try:
        response = requests.post(
            f"{RECFAC_API_URL}/recfac/scan-image/",
            json={"path": image_path},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10  # Timeout court pour ne pas bloquer
        )

        if response.ok:
            logger.info(f"Image scannée avec succès: {image_path}")
        else:
            logger.warning(f"Échec du scan pour {image_path}: status={response.status_code}")

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout lors du scan de {image_path}")
    except requests.exceptions.ConnectionError:
        logger.warning(f"Service Recfac non disponible pour scanner {image_path}")
    except Exception as e:
        logger.error(f"Erreur lors du scan de {image_path}: {e}")


def delete_image_from_recfac_async(image_path, token):
    """
    Appel asynchrone vers le service Recfac pour supprimer les données d'une image.
    Cette fonction est appelée dans un thread séparé pour ne pas bloquer la suppression.
    """
    try:
        response = requests.post(
            f"{RECFAC_API_URL}/recfac/delete-image/",
            json={"path": image_path},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.ok:
            logger.info(f"Données recfac supprimées pour: {image_path}")
        else:
            logger.warning(f"Échec suppression recfac pour {image_path}: status={response.status_code}")

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout lors de la suppression recfac de {image_path}")
    except requests.exceptions.ConnectionError:
        logger.warning(f"Service Recfac non disponible pour supprimer {image_path}")
    except Exception as e:
        logger.error(f"Erreur lors de la suppression recfac de {image_path}: {e}")


def delete_multiple_from_recfac_async(paths, token):
    """
    Appel asynchrone vers le service Recfac pour supprimer les données de plusieurs images.
    Cette fonction est appelée dans un thread séparé pour ne pas bloquer la suppression.
    """
    try:
        response = requests.post(
            f"{RECFAC_API_URL}/recfac/delete-multiple/",
            json={"paths": paths},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30  # Timeout plus long pour les suppressions multiples
        )

        if response.ok:
            logger.info(f"Données recfac supprimées pour {len(paths)} fichier(s)")
        else:
            logger.warning(f"Échec suppression recfac multiple: status={response.status_code}")

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout lors de la suppression recfac de {len(paths)} fichier(s)")
    except requests.exceptions.ConnectionError:
        logger.warning(f"Service Recfac non disponible pour supprimer {len(paths)} fichier(s)")
    except Exception as e:
        logger.error(f"Erreur lors de la suppression recfac multiple: {e}")


@csrf_exempt
def hello(request):
    if request.method == "GET":
        return JsonResponse({"message": "Files service available"}, status=200)
    return JsonResponse({"error": "Method not allowed."}, status=405)


@csrf_exempt
def get_files(request):
    if request.method == "GET":
        # Default to current directory under root, not "/" which escapes join semantics
        relative_path = request.GET.get("path", "")

        root = Path(ROOT_DIR).resolve()
        # Prevent absolute path from overriding the root by stripping leading separators
        candidate = (root / str(relative_path).lstrip("/\\")).resolve()

        # Ensure requested path stays within ROOT_DIR
        try:
            if not candidate.is_relative_to(root):
                return JsonResponse({"error": "Invalid path."}, status=400)
        except AttributeError:
            # Fallback for older Python (not expected on 3.11)
            if str(candidate).find(str(root)) != 0:
                return JsonResponse({"error": "Invalid path."}, status=400)

        if not candidate.exists():
            return JsonResponse({"error": "Directory not found."}, status=404)

        try:
            content = []
            for item in candidate.iterdir():
                img = None
                if item.is_file() and item.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                    img = compress_and_encode_image(item, (300, 300), 55)

                content.append({
                    "Name": item.name,
                    "isDirectory": item.is_dir(),
                    "Path": str(item.relative_to(root)),
                    "Img": img,
                })

            return JsonResponse(content, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid HTTP method."}, status=405)


@csrf_exempt
def add_files(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method."}, status=405)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
    except Exception:
        return JsonResponse({"error": "Token invalide ou expiré."}, status=401)

    if not payload.get("admin"):
        return JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)

    relative_path = request.POST.get("path", "")
    root = Path(ROOT_DIR).resolve()
    target_dir = (root / str(relative_path).lstrip("/\\")).resolve()

    try:
        if not target_dir.is_relative_to(root):
            return JsonResponse({"error": "Invalid path."}, status=400)
    except AttributeError:
        if str(target_dir).find(str(root)) != 0:
            return JsonResponse({"error": "Invalid path."}, status=400)

    if not request.FILES:
        return JsonResponse({"error": "Aucun fichier fourni."}, status=400)

    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    incoming_files = request.FILES.getlist("files") or list(request.FILES.values())

    for file_obj in incoming_files:
        filename = Path(file_obj.name).name
        destination = target_dir / filename

        with open(destination, "wb+") as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)

        relative_path = str(destination.relative_to(root))
        saved_files.append({"Name": filename, "Path": relative_path})

        # Si c'est une image, lancer le scan en arrière-plan
        file_extension = destination.suffix.lower()
        if file_extension in image_extensions:
            thread = threading.Thread(
                target=scan_image_async,
                args=(relative_path, token)
            )
            thread.daemon = True
            thread.start()
            logger.info(f"Scan lancé en arrière-plan pour: {relative_path}")

    return JsonResponse({"message": "Fichiers ajoutés.", "files": saved_files}, status=201)

@csrf_exempt
def add_folder(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Token manquant.'}, status=401)

    token = auth_header.split(' ')[1]
    try:
        payload = verify_token(token)
    except Exception:
        return JsonResponse({'error': 'Token invalide ou expire.'}, status=401)

    if not payload.get('admin'):
        return JsonResponse({'error': 'Acces reserve aux administrateurs.'}, status=403)

    if request.content_type and 'application/json' in request.content_type.lower():
        try:
            data = json.loads(request.body.decode() or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON invalide.'}, status=400)
    else:
        data = request.POST

    relative_path = data.get('path', '')
    folder_name_raw = data.get('folder_name') or data.get('name') or ''
    folder_name = Path(str(folder_name_raw).strip()).name

    if not folder_name:
        return JsonResponse({'error': 'Nom de dossier requis.'}, status=400)

    root = Path(ROOT_DIR).resolve()
    target_dir = (root / str(relative_path).lstrip("/\\")).resolve()

    try:
        if not target_dir.is_relative_to(root):
            return JsonResponse({'error': 'Invalid path.'}, status=400)
    except AttributeError:
        if str(target_dir).find(str(root)) != 0:
            return JsonResponse({'error': 'Invalid path.'}, status=400)

    if not target_dir.exists():
        return JsonResponse({'error': 'Repertoire parent introuvable.'}, status=404)

    new_folder_path = (target_dir / folder_name).resolve()

    try:
        if not new_folder_path.is_relative_to(root):
            return JsonResponse({'error': 'Invalid path.'}, status=400)
    except AttributeError:
        if str(new_folder_path).find(str(root)) != 0:
            return JsonResponse({'error': 'Invalid path.'}, status=400)

    if new_folder_path.exists():
        return JsonResponse({'error': 'Un fichier ou dossier avec ce nom existe deja.'}, status=409)

    new_folder_path.mkdir(parents=True, exist_ok=False)

    return JsonResponse({
        'message': 'Dossier cree.',
        'path': str(new_folder_path.relative_to(root)),
    }, status=201)

@csrf_exempt
def delete_item(request):
    if request.method not in ("POST", "DELETE"):
        return JsonResponse({"error": "Methode non autorisee."}, status=405)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
    except Exception:
        return JsonResponse({"error": "Token invalide ou expire."}, status=401)

    if not payload.get("admin"):
        return JsonResponse({"error": "Acces reserve aux administrateurs."}, status=403)

    if request.content_type and "application/json" in request.content_type.lower():
        try:
            data = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "JSON invalide."}, status=400)
    else:
        data = request.POST

    relative_path = data.get("path", "")
    if not relative_path:
        return JsonResponse({"error": "Chemin requis."}, status=400)

    root = Path(ROOT_DIR).resolve()
    target = (root / str(relative_path).lstrip("/\\")).resolve()

    try:
        if not target.is_relative_to(root):
            return JsonResponse({"error": "Invalid path."}, status=400)
    except AttributeError:
        if str(target).find(str(root)) != 0:
            return JsonResponse({"error": "Invalid path."}, status=400)

    if target == root:
        return JsonResponse({"error": "Suppression de la racine interdite."}, status=400)

    if not target.exists():
        return JsonResponse({"error": "Fichier ou dossier introuvable."}, status=404)

    # Déterminer si c'est une image pour notifier recfac
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    is_image = target.is_file() and target.suffix.lower() in image_extensions
    is_directory = target.is_dir()

    # Pour les dossiers, collecter tous les chemins d'images avant suppression
    image_paths_to_delete = []
    if is_directory:
        for ext in image_extensions:
            image_paths_to_delete.extend([
                str(f.relative_to(root)) for f in target.rglob(f"*{ext}")
            ])
            image_paths_to_delete.extend([
                str(f.relative_to(root)) for f in target.rglob(f"*{ext.upper()}")
            ])

    try:
        if is_directory:
            shutil.rmtree(target)
        else:
            target.unlink()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    # Notifier recfac de la suppression (en arrière-plan)
    if is_image:
        thread = threading.Thread(
            target=delete_image_from_recfac_async,
            args=(relative_path, token)
        )
        thread.daemon = True
        thread.start()
        logger.info(f"Notification recfac lancée pour suppression: {relative_path}")
    elif is_directory and image_paths_to_delete:
        thread = threading.Thread(
            target=delete_multiple_from_recfac_async,
            args=(image_paths_to_delete, token)
        )
        thread.daemon = True
        thread.start()
        logger.info(f"Notification recfac lancée pour suppression dossier: {len(image_paths_to_delete)} image(s)")

    return JsonResponse({"message": "Suppression effectuee."}, status=200)


@csrf_exempt
def delete_multiple(request):
    """
    Supprime plusieurs fichiers/dossiers en une seule requête.
    POST /files/delete-multiple/
    Body: { "paths": ["path1", "path2", ...] }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Methode non autorisee."}, status=405)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
    except Exception:
        return JsonResponse({"error": "Token invalide ou expire."}, status=401)

    if not payload.get("admin"):
        return JsonResponse({"error": "Acces reserve aux administrateurs."}, status=403)

    try:
        data = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide."}, status=400)

    paths = data.get("paths", [])
    if not paths or not isinstance(paths, list):
        return JsonResponse({"error": "Liste de chemins requise."}, status=400)

    root = Path(ROOT_DIR).resolve()
    results = {"deleted": [], "errors": []}
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    all_image_paths_to_delete = []

    for relative_path in paths:
        if not relative_path:
            continue

        target = (root / str(relative_path).lstrip("/\\")).resolve()

        try:
            if not target.is_relative_to(root):
                results["errors"].append({"path": relative_path, "error": "Chemin invalide"})
                continue
        except AttributeError:
            if str(target).find(str(root)) != 0:
                results["errors"].append({"path": relative_path, "error": "Chemin invalide"})
                continue

        if target == root:
            results["errors"].append({"path": relative_path, "error": "Suppression de la racine interdite"})
            continue

        if not target.exists():
            results["errors"].append({"path": relative_path, "error": "Fichier introuvable"})
            continue

        # Collecter les chemins d'images avant suppression
        if target.is_file() and target.suffix.lower() in image_extensions:
            all_image_paths_to_delete.append(relative_path)
        elif target.is_dir():
            for ext in image_extensions:
                all_image_paths_to_delete.extend([
                    str(f.relative_to(root)) for f in target.rglob(f"*{ext}")
                ])
                all_image_paths_to_delete.extend([
                    str(f.relative_to(root)) for f in target.rglob(f"*{ext.upper()}")
                ])

        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            results["deleted"].append(relative_path)
        except Exception as e:
            results["errors"].append({"path": relative_path, "error": str(e)})

    # Notifier recfac de toutes les suppressions d'images (en arrière-plan)
    if all_image_paths_to_delete:
        thread = threading.Thread(
            target=delete_multiple_from_recfac_async,
            args=(all_image_paths_to_delete, token)
        )
        thread.daemon = True
        thread.start()
        logger.info(f"Notification recfac lancée pour suppression multiple: {len(all_image_paths_to_delete)} image(s)")

    return JsonResponse({
        "message": f"{len(results['deleted'])} fichier(s) supprimé(s)",
        "deleted_count": len(results["deleted"]),
        "errors_count": len(results["errors"]),
        "details": results
    }, status=200)


def compress_and_encode_image(image_path, max_size=(400, 400), quality=65):
    """
    Compresse et encode une image en base64.
    Parametres par defaut optimises pour un bon equilibre taille/qualite.
    """
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size)
            buffer = BytesIO()
            img.convert("RGB").save(buffer, format="JPEG", quality=quality)
            return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    except Exception:
        return None


@csrf_exempt
def get_image_info(request):
    if request.method == "GET":
        image_path = request.GET.get("path")
        if not image_path:
            return JsonResponse({"error": "Chemin d'image requis."}, status=400)

        root = Path(ROOT_DIR).resolve()
        full_path = (root / str(image_path).lstrip("/\\")).resolve()

        try:
            if not full_path.is_relative_to(root):
                return JsonResponse({"error": "Invalid path."}, status=400)
        except AttributeError:
            if str(full_path).find(str(root)) != 0:
                return JsonResponse({"error": "Invalid path."}, status=400)
        if not full_path.exists() or not full_path.is_file():
            return JsonResponse({"error": "Fichier non trouvé."}, status=404)

        file_info = full_path

        token = request.headers.get("Authorization", "").split(" ")[1] if "Authorization" in request.headers else None
        is_authenticated = False
        token_mess='token absent'
        if token:
            try:
                verify_token(token)
                is_authenticated = True
                token_mess='Token valide'

            except Exception:
                is_authenticated = False
                token_mess='Token invalide ou expire'

        try:
            if is_authenticated:
                with open(full_path, "rb") as image_file:
                    img_data = f"data:image/{file_info.suffix[1:]};base64,{base64.b64encode(image_file.read()).decode()}"
            else:
                img_data = generate_protected_image(str(full_path))

            return JsonResponse({
                "Name": file_info.name,
                "Path": str(file_info.relative_to(root)),
                "Size": f"{round(file_info.stat().st_size / 1024, 2)} KB",
                "Type": file_info.suffix,
                "Img": img_data,
                "token info": token_mess,
            })

        except Exception as e:
            return JsonResponse({"error": f"Erreur lors du traitement de l'image : {str(e)}"}, status=500)

    return JsonResponse({"error": "Méthode non autorisée."}, status=405)


def generate_protected_image(image_path):
    """
    Genere une image protegee pour les utilisateurs non connectes.
    - Blur fort (20) pour empecher la visualisation claire
    - Watermark "ProPhotos" au centre
    - Qualite reduite mais image plus grande pour un meilleur apercu
    """
    try:
        with Image.open(image_path).convert("RGBA") as img:
            # Redimensionner si trop grande (pour performance)
            max_size = 1200
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size))

            # Blur plus fort pour proteger l'image
            img = img.filter(ImageFilter.GaussianBlur(20))

            # Reduire la saturation des couleurs
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.4)

            # Ajouter un watermark
            watermark = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark)
            font_size = max(40, img.size[0] // 8)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            text = "ProPhotos"
            # Centrer le texte
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except AttributeError:
                # Fallback pour anciennes versions de Pillow
                text_width, text_height = draw.textsize(text, font=font)

            text_x = (img.size[0] - text_width) // 2
            text_y = (img.size[1] - text_height) // 2
            draw.text((text_x, text_y), text, fill=(255, 255, 255, 180), font=font)

            watermarked = Image.alpha_composite(img, watermark)

            buffer = BytesIO()
            watermarked.convert("RGB").save(buffer, format="JPEG", quality=50)
            return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    except Exception:
        return None


@csrf_exempt
def download_image(request):
    if request.method == "GET":
        token = request.headers.get("Authorization", "").split(" ")[1]
        try:
            verify_token(token)
        except Exception:
            return JsonResponse({"error": "Token invalide ou expiré."}, status=401)

        image_path = request.GET.get("path")
        if not image_path:
            return JsonResponse({"error": "Chemin d'image requis."}, status=400)

        root = Path(ROOT_DIR).resolve()
        full_path = (root / str(image_path).lstrip("/\\")).resolve()

        try:
            if not full_path.is_relative_to(root):
                return JsonResponse({"error": "Invalid path."}, status=400)
        except AttributeError:
            if str(full_path).find(str(root)) != 0:
                return JsonResponse({"error": "Invalid path."}, status=400)

        if not full_path.exists():
            return JsonResponse({"error": "Fichier non trouvé."}, status=404)

        return FileResponse(open(full_path, "rb"), as_attachment=True)

    return JsonResponse({"error": "Méthode non autorisée."}, status=405)


@csrf_exempt
def get_images_batch(request):
    """
    Retourne plusieurs images compressées en une seule requête.
    POST /files/images-batch/
    Body JSON: {"paths": ["path1.jpg", "path2.jpg", ...]}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Vérification du token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        verify_token(token)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=401)

    # Parser le body JSON
    try:
        data = json.loads(request.body)
        paths = data.get("paths", [])
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not isinstance(paths, list):
        return JsonResponse({"error": "paths must be a list."}, status=400)

    if len(paths) > 100:
        return JsonResponse({"error": "Maximum 100 paths per request."}, status=400)

    root = Path(ROOT_DIR).resolve()
    results = []

    for relative_path in paths:
        try:
            # Construire le chemin absolu et vérifier la sécurité
            full_path = (root / str(relative_path).lstrip("/\\")).resolve()

            # Vérifier que le chemin est dans le root
            try:
                if not full_path.is_relative_to(root):
                    results.append({
                        "path": relative_path,
                        "error": "Invalid path",
                        "success": False,
                    })
                    continue
            except AttributeError:
                if str(full_path).find(str(root)) != 0:
                    results.append({
                        "path": relative_path,
                        "error": "Invalid path",
                        "success": False,
                    })
                    continue

            # Vérifier que le fichier existe
            if not full_path.exists() or not full_path.is_file():
                results.append({
                    "path": relative_path,
                    "error": "File not found",
                    "success": False,
                })
                continue

            # Compresser et encoder l'image (meilleure qualite pour page Personnes)
            img_data = compress_and_encode_image(full_path, (350, 350), 60)

            if img_data:
                # Récupérer les métadonnées de base
                file_size = full_path.stat().st_size

                results.append({
                    "path": relative_path,
                    "name": full_path.name,
                    "img": img_data,
                    "size": file_size,
                    "success": True,
                })
            else:
                results.append({
                    "path": relative_path,
                    "error": "Failed to process image",
                    "success": False,
                })

        except Exception as e:
            results.append({
                "path": relative_path,
                "error": str(e),
                "success": False,
            })

    return JsonResponse({
        "count": len(results),
        "results": results,
    })
