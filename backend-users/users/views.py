import secrets
import jwt
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings

from .models import User
import json
from django.utils.timezone import now
from utils import generate_token, verify_token


@csrf_exempt
def hello(request):
    if request.method == "GET":
        return JsonResponse({"message": "Users service available"}, status=200)
    return JsonResponse({"error": "Method not allowed."}, status=405)

@csrf_exempt
def get_users(request):
    users = User.objects.all().values('id', 'username', 'email', 'token', 'admin')
    return JsonResponse(list(users), safe=False)

@csrf_exempt
def get_current_user(request):
    token = request.headers.get("Authorization", "").split(" ")[1]
    try:
        payload = verify_token(token)
        user = User.objects.get(id=payload["user_id"])
        return JsonResponse({"username": user.username, "admin": user.admin}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=401)

@csrf_exempt
def verify_token_session(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JsonResponse({"error": "Token manquant"}, status=401)

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user = User.objects.get(id=payload["user_id"])
        return JsonResponse({"message": "Token valide", "user": {"username": user.username, "admin": user.admin}}, status=200)
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Token expiré"}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "Token invalide"}, status=401)


@csrf_exempt
def create_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email_raw = data.get('email')
            email = email_raw.strip().lower() if email_raw else None
            password = data.get('password')
            admin_requested = bool(data.get('admin_request'))

            if not username or not email or not password:
                return JsonResponse({"error": "Tous les champs sont requis."}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "Le nom d'utilisateur est déjà pris."}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({"error": "L'email est déjà utilisé."}, status=400)

            verification_token = secrets.token_urlsafe(32)

            user = User(
                username=username,
                email=email,
                password=make_password(password),
                verifie=False,
                created_at=now(),
                link_verification=verification_token,
                admin=admin_requested,
            )
            user.save()

            base_verify_url = settings.EMAIL_VERIFICATION_BASE 
            verification_link = f"{base_verify_url}verify/{verification_token}/"

            send_mail(
                subject=f"Nouveau compte à valider [{username}] - ProPhotos",
                message=(
                    "Un nouvel utilisateur s'est inscrit.\n\n"
                    f"Nom d'utilisateur : {username}\n"
                    f"Email : {email}\n"
                    f"Demande admin : {'oui' if admin_requested else 'non'}\n"
                    "Lien de vérification :\n"
                    f"{verification_link}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            return JsonResponse({"message": "Utilisateur créé, en attente de validation."}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Données invalides."}, status=400)

    return JsonResponse({"error": "Méthode non autorisée."}, status=405)


@csrf_exempt
def user_verification(request, token):
    if request.method == 'GET':
        try:
            user = User.objects.filter(link_verification=token, verifie=False).first()
            if not user:
                return JsonResponse({"error": "Lien invalide ou utilisateur déjà vérifié."}, status=400)

            user.verifie = True
            user.verified_at = now()
            user.link_verification = None
            user.save()

            send_mail(
                subject=f"Compte validé - ProPhotos",
                message="Votre compte ProPhotos a été vérifié.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return JsonResponse({"message": "Utilisateur vérifié avec succès."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Méthode non autorisée."}, status=405)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({"error": "Email et mot de passe requis."}, status=400)

            user = get_object_or_404(User, email=email)

            if not check_password(password, user.password):
                return JsonResponse({"error": "Email ou mot de passe incorrect."}, status=401)

            if not user.verifie:
                return JsonResponse(
                    {"error": "Compte non vérifié. Veuillez patienter la validation.", "code": "not_verified"},
                    status=403
                )

            token = generate_token(user)

            
            user.last_login = now()
            user.save()

            return JsonResponse({"message": "Connexion réussie.", "token": token, "admin": user.admin}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Données invalides."}, status=400)

    return JsonResponse({"error": "Méthode non autorisée."}, status=405)
