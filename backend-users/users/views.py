import secrets
import jwt
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from .models import User, LoginAttempt
from .email_validator import validate_email
import json
from django.utils.timezone import now
from utils import generate_token, verify_token

# Configuration anti-bruteforce
MAX_LOGIN_ATTEMPTS = 5  # Nombre max de tentatives
LOCKOUT_DURATION_MINUTES = 15  # Duree de blocage

# Configuration expiration token verification
VERIFICATION_TOKEN_EXPIRY_HOURS = 48  # Token valide 48h


@csrf_exempt
def hello(request):
    if request.method == "GET":
        return JsonResponse({"message": "Users service available"}, status=200)
    return JsonResponse({"error": "Method not allowed."}, status=405)

@csrf_exempt
def get_users(request):
    """
    Liste les utilisateurs. Requiert un token admin.
    GET /users/
    """
    # Vérification du token admin
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
    try:
        payload = verify_token(token)
        if not payload.get("admin"):
            return JsonResponse({"error": "Accès réservé aux administrateurs."}, status=403)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=401)

    # Ne pas exposer les tokens - seulement les infos de base
    users = User.objects.all().values('id', 'username', 'email', 'admin', 'verifie', 'created_at')
    return JsonResponse(list(users), safe=False)

@csrf_exempt
def get_current_user(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Token manquant."}, status=401)

    token = auth_header.split(" ")[1]
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
            password = data.get('password')
            admin_requested = bool(data.get('admin_request'))

            if not username or not email_raw or not password:
                return JsonResponse({"error": "Tous les champs sont requis."}, status=400)

            # === VALIDATION DE L'EMAIL ===
            is_valid, error_msg = validate_email(email_raw)
            if not is_valid:
                return JsonResponse({"error": error_msg}, status=400)

            email = email_raw.strip().lower()

            # Validation du username (caracteres autorises)
            if not username.replace('_', '').replace('-', '').isalnum():
                return JsonResponse({
                    "error": "Le nom d'utilisateur ne peut contenir que des lettres, chiffres, tirets et underscores."
                }, status=400)

            if len(username) < 3:
                return JsonResponse({"error": "Le nom d'utilisateur doit faire au moins 3 caracteres."}, status=400)

            # Validation du mot de passe
            if len(password) < 8:
                return JsonResponse({"error": "Le mot de passe doit faire au moins 8 caracteres."}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({"error": "Le nom d'utilisateur est deja pris."}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({"error": "L'email est deja utilise."}, status=400)

            verification_token = secrets.token_urlsafe(32)

            user = User(
                username=username,
                email=email,
                password=make_password(password),
                verifie=False,
                created_at=now(),
                link_verification=verification_token,
                verification_token_created_at=now(),  # Pour l'expiration
                admin=admin_requested,
            )
            user.save()

            base_verify_url = settings.EMAIL_VERIFICATION_BASE
            verification_link = f"{base_verify_url}verify/{verification_token}/"

            send_mail(
                subject=f"Nouveau compte a valider [{username}] - ProPhotos",
                message=(
                    "Un nouvel utilisateur s'est inscrit.\n\n"
                    f"Nom d'utilisateur : {username}\n"
                    f"Email : {email}\n"
                    f"Demande admin : {'oui' if admin_requested else 'non'}\n"
                    f"Lien de verification (valide {VERIFICATION_TOKEN_EXPIRY_HOURS}h):\n"
                    f"{verification_link}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            return JsonResponse({"message": "Utilisateur cree, en attente de validation."}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Donnees invalides."}, status=400)

    return JsonResponse({"error": "Methode non autorisee."}, status=405)


@csrf_exempt
def user_verification(request, token):
    if request.method == 'GET':
        try:
            user = User.objects.filter(link_verification=token, verifie=False).first()
            if not user:
                return JsonResponse({"error": "Lien invalide ou utilisateur deja verifie."}, status=400)

            # === VERIFICATION EXPIRATION DU TOKEN ===
            if user.verification_token_created_at:
                token_age = now() - user.verification_token_created_at
                max_age = timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS)

                if token_age > max_age:
                    return JsonResponse({
                        "error": f"Le lien de verification a expire (valide {VERIFICATION_TOKEN_EXPIRY_HOURS}h). Demandez un nouveau lien.",
                        "code": "token_expired",
                        "email": user.email
                    }, status=410)

            user.verifie = True
            user.verified_at = now()
            user.link_verification = None
            user.verification_token_created_at = None
            user.save()

            send_mail(
                subject=f"Compte valide - ProPhotos",
                message="Votre compte ProPhotos a ete verifie.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return JsonResponse({"message": "Utilisateur verifie avec succes."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Methode non autorisee."}, status=405)


@csrf_exempt
def resend_verification(request):
    """
    Renvoie un nouveau lien de verification si l'ancien a expire.
    POST /users/resend-verification/
    Body: {"email": "user@example.com"}
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()

            if not email:
                return JsonResponse({"error": "Email requis."}, status=400)

            user = User.objects.filter(email=email, verifie=False).first()
            if not user:
                # Ne pas reveler si l'email existe ou non
                return JsonResponse({
                    "message": "Si cet email existe et n'est pas verifie, un nouveau lien a ete envoye."
                }, status=200)

            # Generer un nouveau token
            new_token = secrets.token_urlsafe(32)
            user.link_verification = new_token
            user.verification_token_created_at = now()
            user.save()

            # Envoyer le nouveau lien
            base_verify_url = settings.EMAIL_VERIFICATION_BASE
            verification_link = f"{base_verify_url}verify/{new_token}/"

            send_mail(
                subject=f"Nouveau lien de verification - ProPhotos",
                message=(
                    f"Bonjour {user.username},\n\n"
                    "Voici votre nouveau lien de verification:\n"
                    f"{verification_link}\n\n"
                    f"Ce lien est valide {VERIFICATION_TOKEN_EXPIRY_HOURS} heures.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            return JsonResponse({
                "message": "Si cet email existe et n'est pas verifie, un nouveau lien a ete envoye."
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Donnees invalides."}, status=400)

    return JsonResponse({"error": "Methode non autorisee."}, status=405)


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


@csrf_exempt
def login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({"error": "Email et mot de passe requis."}, status=400)

            # Normaliser l'email
            email = email.strip().lower()
            ip_address = get_client_ip(request)

            # === PROTECTION ANTI-BRUTEFORCE ===
            recent_failures = LoginAttempt.get_recent_failures(
                ip_address, email, minutes=LOCKOUT_DURATION_MINUTES
            )

            if recent_failures >= MAX_LOGIN_ATTEMPTS:
                # Calculer le temps restant avant deblocage
                remaining_minutes = LOCKOUT_DURATION_MINUTES
                return JsonResponse({
                    "error": f"Trop de tentatives echouees. Reessayez dans {remaining_minutes} minutes.",
                    "code": "too_many_attempts",
                    "retry_after_minutes": remaining_minutes
                }, status=429)

            # Verifier si l'utilisateur existe
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Enregistrer la tentative echouee
                LoginAttempt.record_attempt(ip_address, email, successful=False)
                return JsonResponse({"error": "Email ou mot de passe incorrect."}, status=401)

            # Verifier le mot de passe
            if not check_password(password, user.password):
                # Enregistrer la tentative echouee
                LoginAttempt.record_attempt(ip_address, email, successful=False)

                # Informer du nombre de tentatives restantes
                attempts_left = MAX_LOGIN_ATTEMPTS - recent_failures - 1
                if attempts_left <= 2 and attempts_left > 0:
                    return JsonResponse({
                        "error": f"Email ou mot de passe incorrect. {attempts_left} tentative(s) restante(s).",
                        "attempts_left": attempts_left
                    }, status=401)

                return JsonResponse({"error": "Email ou mot de passe incorrect."}, status=401)

            # Verifier si le compte est verifie
            if not user.verifie:
                return JsonResponse(
                    {"error": "Compte non verifie. Veuillez patienter la validation.", "code": "not_verified"},
                    status=403
                )

            # === CONNEXION REUSSIE ===
            # Enregistrer la tentative reussie (reset le compteur)
            LoginAttempt.record_attempt(ip_address, email, successful=True)

            token = generate_token(user)

            user.last_login = now()
            user.save()

            return JsonResponse({"message": "Connexion reussie.", "token": token, "admin": user.admin}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Donnees invalides."}, status=400)

    return JsonResponse({"error": "Methode non autorisee."}, status=405)
