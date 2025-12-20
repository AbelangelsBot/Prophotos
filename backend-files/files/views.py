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


ROOT_DIR = os.environ.get("FILES_ROOT_DIR")


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
                if item.is_file() and item.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
                    img = compress_and_encode_image(item, (256/2, 256/2), 20)

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
    incoming_files = request.FILES.getlist("files") or list(request.FILES.values())
    for file_obj in incoming_files:
        filename = Path(file_obj.name).name
        destination = target_dir / filename

        with open(destination, "wb+") as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)

        saved_files.append({"Name": filename, "Path": str(destination.relative_to(root))})

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

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"message": "Suppression effectuee."}, status=200)



def compress_and_encode_image(image_path, max_size=(500, 500), quality=70):
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
    try:
        with Image.open(image_path).convert("RGBA") as img:
            img = img.filter(ImageFilter.GaussianBlur(2))
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.5)

            watermark = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark)
            font_size = max(500, img.size[0] // 10)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            text = "ProPhotos"
            text_position = (img.size[0] // 4, img.size[1] // 2)
            draw.text(text_position, text, fill=(255, 255, 255, 200), font=font)

            watermarked = Image.alpha_composite(img, watermark)

            buffer = BytesIO()
            watermarked.convert("RGB").save(buffer, format="JPEG", quality=30)
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
