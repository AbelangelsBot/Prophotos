from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
import os
import base64
from PIL import Image
from io import BytesIO
from utils import verify_token
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


ROOT_DIR = os.environ.get("FILES_ROOT_DIR")


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
