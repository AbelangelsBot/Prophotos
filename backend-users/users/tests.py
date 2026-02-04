"""
Tests automatisés pour le microservice users.
Couvre: authentification, tokens, validation, anti-bruteforce.
"""
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now

from .models import User, LoginAttempt
from utils import generate_token, verify_token


class UtilsTokenTestCase(TestCase):
    """Tests pour les fonctions utilitaires de tokens."""

    def setUp(self):
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password=make_password("password123"),
            admin=False,
            verifie=True,
        )
        self.admin_user = User.objects.create(
            username="adminuser",
            email="admin@example.com",
            password=make_password("adminpass123"),
            admin=True,
            verifie=True,
        )

    def test_generate_token_returns_string(self):
        """generate_token doit retourner une chaine JWT."""
        token = generate_token(self.user)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 50)

    def test_verify_token_valid(self):
        """verify_token doit decoder un token valide."""
        token = generate_token(self.user)
        payload = verify_token(token)
        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["username"], self.user.username)
        self.assertFalse(payload["admin"])

    def test_verify_token_admin_flag(self):
        """Le token admin doit contenir admin=True."""
        token = generate_token(self.admin_user)
        payload = verify_token(token)
        self.assertTrue(payload["admin"])

    def test_verify_token_invalid(self):
        """verify_token doit lever une exception pour un token invalide."""
        with self.assertRaises(Exception) as context:
            verify_token("invalid.token.here")
        self.assertIn("invalide", str(context.exception).lower())


class HelloEndpointTestCase(TestCase):
    """Tests pour l'endpoint /users/hello/"""

    def setUp(self):
        self.client = Client()

    def test_hello_get(self):
        """GET /users/hello/ doit retourner un message de disponibilite."""
        response = self.client.get("/users/hello/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)

    def test_hello_post_not_allowed(self):
        """POST /users/hello/ doit retourner 405."""
        response = self.client.post("/users/hello/")
        self.assertEqual(response.status_code, 405)


class GetUsersEndpointTestCase(TestCase):
    """Tests pour l'endpoint GET /users/"""

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create(
            username="admin",
            email="admin@test.com",
            password=make_password("adminpass"),
            admin=True,
            verifie=True,
        )
        self.normal_user = User.objects.create(
            username="normal",
            email="normal@test.com",
            password=make_password("normalpass"),
            admin=False,
            verifie=True,
        )

    def test_get_users_without_token(self):
        """GET /users/ sans token doit retourner 401."""
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_get_users_with_invalid_token(self):
        """GET /users/ avec token invalide doit retourner 401."""
        response = self.client.get(
            "/users/",
            HTTP_AUTHORIZATION="Bearer invalid.token.here"
        )
        self.assertEqual(response.status_code, 401)

    def test_get_users_non_admin(self):
        """GET /users/ avec token non-admin doit retourner 403."""
        token = generate_token(self.normal_user)
        response = self.client.get(
            "/users/",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 403)

    def test_get_users_admin_success(self):
        """GET /users/ avec token admin doit retourner la liste."""
        token = generate_token(self.admin_user)
        response = self.client.get(
            "/users/",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)


class GetCurrentUserTestCase(TestCase):
    """Tests pour l'endpoint GET /users/me/"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="currentuser",
            email="current@test.com",
            password=make_password("password123"),
            admin=False,
            verifie=True,
        )

    def test_get_current_user_success(self):
        """GET /users/me/ avec token valide retourne les infos user."""
        token = generate_token(self.user)
        response = self.client.get(
            "/users/me/",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "currentuser")

    def test_get_current_user_no_token(self):
        """GET /users/me/ sans token retourne 401."""
        response = self.client.get("/users/me/")
        self.assertEqual(response.status_code, 401)


class VerifyTokenEndpointTestCase(TestCase):
    """Tests pour l'endpoint /users/verify-token/"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="verifyuser",
            email="verify@test.com",
            password=make_password("password123"),
            admin=False,
            verifie=True,
        )

    def test_verify_token_valid(self):
        """Verification d'un token valide."""
        token = generate_token(self.user)
        response = self.client.get(
            "/users/verify-token/",
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("user", data)


class CreateUserTestCase(TestCase):
    """Tests pour l'endpoint POST /users/create/"""

    def setUp(self):
        self.client = Client()

    @patch('users.views.send_mail')
    def test_create_user_success(self, mock_mail):
        """Creation d'utilisateur avec donnees valides."""
        mock_mail.return_value = 1
        response = self.client.post(
            "/users/create/",
            data=json.dumps({
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_create_user_missing_fields(self):
        """Creation sans champs requis doit echouer."""
        response = self.client.post(
            "/users/create/",
            data=json.dumps({"username": "onlyuser"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_create_user_short_password(self):
        """Mot de passe trop court doit etre rejete."""
        response = self.client.post(
            "/users/create/",
            data=json.dumps({
                "username": "shortpass",
                "email": "short@test.com",
                "password": "123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_create_user_invalid_email(self):
        """Email invalide doit etre rejete."""
        response = self.client.post(
            "/users/create/",
            data=json.dumps({
                "username": "bademail",
                "email": "notanemail",
                "password": "password123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch('users.views.send_mail')
    def test_create_user_duplicate_username(self, mock_mail):
        """Username duplique doit etre rejete."""
        mock_mail.return_value = 1
        User.objects.create(
            username="duplicate",
            email="first@test.com",
            password=make_password("password123")
        )
        response = self.client.post(
            "/users/create/",
            data=json.dumps({
                "username": "duplicate",
                "email": "second@test.com",
                "password": "password123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


class LoginTestCase(TestCase):
    """Tests pour l'endpoint POST /users/login/"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="loginuser",
            email="login@test.com",
            password=make_password("password123"),
            admin=False,
            verifie=True,
        )
        self.unverified_user = User.objects.create(
            username="unverified",
            email="unverified@test.com",
            password=make_password("password123"),
            admin=False,
            verifie=False,
        )

    def test_login_success(self):
        """Login avec identifiants corrects."""
        response = self.client.post(
            "/users/login/",
            data=json.dumps({
                "email": "login@test.com",
                "password": "password123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)

    def test_login_wrong_password(self):
        """Login avec mauvais mot de passe."""
        response = self.client.post(
            "/users/login/",
            data=json.dumps({
                "email": "login@test.com",
                "password": "wrongpassword"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_user(self):
        """Login avec email inexistant."""
        response = self.client.post(
            "/users/login/",
            data=json.dumps({
                "email": "noone@test.com",
                "password": "password123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_unverified_user(self):
        """Login avec compte non verifie."""
        response = self.client.post(
            "/users/login/",
            data=json.dumps({
                "email": "unverified@test.com",
                "password": "password123"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("not_verified", response.json().get("code", ""))


class AntiBruteforceTestCase(TestCase):
    """Tests pour la protection anti-bruteforce."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username="bruteuser",
            email="brute@test.com",
            password=make_password("password123"),
            admin=False,
            verifie=True,
        )

    def test_bruteforce_lockout(self):
        """Apres 5 echecs, le compte doit etre bloque."""
        for i in range(5):
            self.client.post(
                "/users/login/",
                data=json.dumps({
                    "email": "brute@test.com",
                    "password": "wrongpassword"
                }),
                content_type="application/json"
            )

        # La 6eme tentative doit etre bloquee
        response = self.client.post(
            "/users/login/",
            data=json.dumps({
                "email": "brute@test.com",
                "password": "password123"  # Meme le bon mot de passe
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn("too_many_attempts", response.json().get("code", ""))


class UserVerificationTestCase(TestCase):
    """Tests pour la verification de compte."""

    def setUp(self):
        self.client = Client()
        self.unverified_user = User.objects.create(
            username="toverify",
            email="toverify@test.com",
            password=make_password("password123"),
            admin=False,
            verifie=False,
            link_verification="valid_token_123",
            verification_token_created_at=now(),
        )

    @patch('users.views.send_mail')
    def test_verify_user_success(self, mock_mail):
        """Verification avec token valide."""
        mock_mail.return_value = 1
        response = self.client.get("/users/verify/valid_token_123/")
        self.assertEqual(response.status_code, 200)
        self.unverified_user.refresh_from_db()
        self.assertTrue(self.unverified_user.verifie)

    def test_verify_invalid_token(self):
        """Verification avec token invalide."""
        response = self.client.get("/users/verify/invalid_token/")
        self.assertEqual(response.status_code, 400)

    def test_verify_expired_token(self):
        """Verification avec token expire."""
        self.unverified_user.verification_token_created_at = now() - timedelta(hours=49)
        self.unverified_user.save()
        response = self.client.get("/users/verify/valid_token_123/")
        self.assertEqual(response.status_code, 410)
        self.assertIn("token_expired", response.json().get("code", ""))