"""
Tests automatisés pour le microservice recfac.
Couvre: scan d'images, tagging, recherche de visages, gestion des personnes.
"""
import json
import os
import tempfile
import shutil
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase, Client
from django.conf import settings
from PIL import Image as PILImage
import numpy as np

from .models import Image, Face, Person


def create_test_image(width=100, height=100, color='red'):
    """Crée une image de test en mémoire."""
    img = PILImage.new('RGB', (width, height), color=color)
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer


def create_mock_embedding(dim=512):
    """Crée un embedding de test normalisé."""
    emb = np.random.randn(dim).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    return emb.tolist()


class CheckHealthTestCase(TestCase):
    """Tests pour l'endpoint GET /recfac/check-health/"""

    def setUp(self):
        self.client = Client()

    def test_health_check_get(self):
        """GET /recfac/check-health/ doit retourner le statut du service."""
        response = self.client.get("/recfac/check-health/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["service"], "recfac")
        self.assertTrue(data["ok"])
        self.assertIn("images_count", data)
        self.assertIn("faces_count", data)

    def test_health_check_post_not_allowed(self):
        """POST /recfac/check-health/ doit retourner 405."""
        response = self.client.post("/recfac/check-health/")
        self.assertEqual(response.status_code, 405)


class ScanImageTestCase(TestCase):
    """Tests pour l'endpoint POST /recfac/scan-image/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        # Créer une image de test
        img = PILImage.new('RGB', (100, 100), color='blue')
        img.save(Path(self.temp_dir) / "test_image.jpg", format='JPEG')

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_scan_image_no_token(self):
        """Scan sans token doit echouer."""
        response = self.client.post(
            "/recfac/scan-image/",
            json.dumps({"path": "test_image.jpg"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_admin_token')
    def test_scan_image_missing_path(self, mock_verify):
        """Scan sans chemin doit echouer."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.post(
            "/recfac/scan-image/",
            json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 400)

    @patch('recfac.views.verify_admin_token')
    def test_scan_image_invalid_path(self, mock_verify):
        """Scan avec chemin invalide doit echouer."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.post(
            "/recfac/scan-image/",
            json.dumps({"path": "../../../etc/passwd"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 400)


class ListPersonsTestCase(TestCase):
    """Tests pour l'endpoint GET /recfac/persons/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        # Créer des données de test
        self.image = Image.objects.create(
            path="test.jpg",
            filename="test.jpg",
            file_hash="abc123",
            file_size=1000,
            width=100,
            height=100,
            scanned=True,
            faces_count=3,
        )

        # Créer des faces avec différentes personnes
        for i, name in enumerate(["John Doe", "John Doe", "Jane Smith"]):
            Face.objects.create(
                image=self.image,
                bbox_x1=0, bbox_y1=0, bbox_x2=50, bbox_y2=50,
                det_score=0.99,
                embedding=create_mock_embedding(),
                person_name=name,
            )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_list_persons_no_token(self):
        """Liste sans token doit echouer."""
        response = self.client.get("/recfac/persons/")
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_user_token')
    def test_list_persons_success(self, mock_verify):
        """Liste des personnes doit retourner les noms uniques."""
        mock_verify.return_value = (True, {"user_id": 1})

        response = self.client.get(
            "/recfac/persons/",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)  # John Doe et Jane Smith

        names = [p["name"] for p in data["persons"]]
        self.assertIn("John Doe", names)
        self.assertIn("Jane Smith", names)


class TagFaceTestCase(TestCase):
    """Tests pour l'endpoint POST /recfac/face/tag/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        self.image = Image.objects.create(
            path="test.jpg",
            filename="test.jpg",
            file_hash="abc123",
            file_size=1000,
            width=100,
            height=100,
            scanned=True,
        )

        self.face = Face.objects.create(
            image=self.image,
            bbox_x1=0, bbox_y1=0, bbox_x2=50, bbox_y2=50,
            det_score=0.99,
            embedding=create_mock_embedding(),
        )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_tag_face_no_token(self):
        """Tagging sans token doit echouer."""
        response = self.client.post(
            "/recfac/face/tag/",
            json.dumps({"face_id": str(self.face.id), "person_name": "Test"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_admin_token')
    def test_tag_face_success(self, mock_verify):
        """Tagging avec token admin doit reussir."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.post(
            "/recfac/face/tag/",
            json.dumps({"face_id": str(self.face.id), "person_name": "John Doe"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["person_name"], "John Doe")
        self.assertTrue(data["updated"])

        # Vérifier en DB
        self.face.refresh_from_db()
        self.assertEqual(self.face.person_name, "John Doe")

    @patch('recfac.views.verify_admin_token')
    def test_tag_face_normalizes_name(self, mock_verify):
        """Le nom doit etre normalise."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.post(
            "/recfac/face/tag/",
            json.dumps({"face_id": str(self.face.id), "person_name": "  john   doe  "}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)

        self.face.refresh_from_db()
        self.assertEqual(self.face.person_name, "John Doe")  # Normalisé

    @patch('recfac.views.verify_admin_token')
    def test_tag_face_not_found(self, mock_verify):
        """Tagging d'un visage inexistant doit echouer."""
        mock_verify.return_value = (True, {"admin": True})

        fake_uuid = str(uuid.uuid4())
        response = self.client.post(
            "/recfac/face/tag/",
            json.dumps({"face_id": fake_uuid, "person_name": "Test"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 404)


class GetPersonFacesTestCase(TestCase):
    """Tests pour l'endpoint GET /recfac/person/faces/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        self.image = Image.objects.create(
            path="test.jpg",
            filename="test.jpg",
            file_hash="abc123",
            file_size=1000,
            width=100,
            height=100,
            scanned=True,
        )

        # Créer des faces pour John Doe
        for i in range(3):
            Face.objects.create(
                image=self.image,
                bbox_x1=i*10, bbox_y1=0, bbox_x2=i*10+50, bbox_y2=50,
                det_score=0.95,
                embedding=create_mock_embedding(),
                person_name="John Doe",
            )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_get_person_faces_no_token(self):
        """Requete sans token doit echouer."""
        response = self.client.get("/recfac/person/faces/?name=John%20Doe")
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_user_token')
    def test_get_person_faces_missing_name(self, mock_verify):
        """Requete sans nom doit echouer."""
        mock_verify.return_value = (True, {"user_id": 1})

        response = self.client.get(
            "/recfac/person/faces/",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 400)

    @patch('recfac.views.verify_user_token')
    def test_get_person_faces_success(self, mock_verify):
        """Requete valide doit retourner les faces."""
        mock_verify.return_value = (True, {"user_id": 1})

        response = self.client.get(
            "/recfac/person/faces/?name=John%20Doe",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["person_name"], "John Doe")
        self.assertEqual(data["faces_count"], 3)
        self.assertEqual(len(data["faces"]), 3)


class GetImageDetailsTestCase(TestCase):
    """Tests pour l'endpoint GET /recfac/image-details/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        self.image = Image.objects.create(
            path="folder/image.jpg",
            filename="image.jpg",
            file_hash="xyz789",
            file_size=5000,
            width=800,
            height=600,
            scanned=True,
            faces_count=2,
        )

        Face.objects.create(
            image=self.image,
            bbox_x1=100, bbox_y1=100, bbox_x2=200, bbox_y2=200,
            det_score=0.98,
            embedding=create_mock_embedding(),
            person_name="Alice",
        )
        Face.objects.create(
            image=self.image,
            bbox_x1=300, bbox_y1=100, bbox_x2=400, bbox_y2=200,
            det_score=0.95,
            embedding=create_mock_embedding(),
        )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_get_image_details_no_token(self):
        """Requete sans token doit echouer."""
        response = self.client.get("/recfac/image-details/?path=folder/image.jpg")
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_user_token')
    def test_get_image_details_success(self, mock_verify):
        """Requete valide doit retourner les details."""
        mock_verify.return_value = (True, {"user_id": 1})

        response = self.client.get(
            "/recfac/image-details/?path=folder/image.jpg",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["exists_in_db"])
        self.assertTrue(data["scanned"])
        self.assertEqual(data["faces_count"], 2)
        self.assertEqual(data["persons_count"], 1)  # Seulement Alice est taggée

    @patch('recfac.views.verify_user_token')
    def test_get_image_details_not_found(self, mock_verify):
        """Image non trouvee retourne exists_in_db=False."""
        mock_verify.return_value = (True, {"user_id": 1})

        response = self.client.get(
            "/recfac/image-details/?path=nonexistent.jpg",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["exists_in_db"])


class GetUntaggedFacesTestCase(TestCase):
    """Tests pour l'endpoint GET /recfac/faces/untagged/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        self.image = Image.objects.create(
            path="test.jpg",
            filename="test.jpg",
            file_hash="abc123",
            file_size=1000,
            width=100,
            height=100,
            scanned=True,
        )

        # Créer des faces: 2 non taggées, 1 taggée
        Face.objects.create(
            image=self.image,
            bbox_x1=0, bbox_y1=0, bbox_x2=50, bbox_y2=50,
            det_score=0.99,
            embedding=create_mock_embedding(),
        )
        Face.objects.create(
            image=self.image,
            bbox_x1=50, bbox_y1=0, bbox_x2=100, bbox_y2=50,
            det_score=0.97,
            embedding=create_mock_embedding(),
        )
        Face.objects.create(
            image=self.image,
            bbox_x1=0, bbox_y1=50, bbox_x2=50, bbox_y2=100,
            det_score=0.95,
            embedding=create_mock_embedding(),
            person_name="Tagged Person",
        )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_untagged_no_token(self):
        """Requete sans token doit echouer."""
        response = self.client.get("/recfac/faces/untagged/")
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_admin_token')
    def test_untagged_success(self, mock_verify):
        """Requete valide retourne les faces non taggees."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.get(
            "/recfac/faces/untagged/",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)  # Seulement 2 non taggées

    @patch('recfac.views.verify_admin_token')
    def test_untagged_pagination(self, mock_verify):
        """La pagination doit fonctionner."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.get(
            "/recfac/faces/untagged/?page=1&limit=1",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["faces"]), 1)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 1)


class DeleteFaceTestCase(TestCase):
    """Tests pour l'endpoint DELETE /recfac/face/delete/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        self.image = Image.objects.create(
            path="test.jpg",
            filename="test.jpg",
            file_hash="abc123",
            file_size=1000,
            width=100,
            height=100,
            scanned=True,
            faces_count=1,
        )

        self.face = Face.objects.create(
            image=self.image,
            bbox_x1=0, bbox_y1=0, bbox_x2=50, bbox_y2=50,
            det_score=0.99,
            embedding=create_mock_embedding(),
        )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    def test_delete_face_no_token(self):
        """Suppression sans token doit echouer."""
        response = self.client.delete(
            "/recfac/face/delete/",
            json.dumps({"face_id": str(self.face.id)}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    @patch('recfac.views.verify_admin_token')
    def test_delete_face_success(self, mock_verify):
        """Suppression avec token admin doit reussir."""
        mock_verify.return_value = (True, {"admin": True})
        face_id = str(self.face.id)

        response = self.client.delete(
            "/recfac/face/delete/",
            json.dumps({"face_id": face_id}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["deleted_face_id"], face_id)

        # Vérifier que la face est supprimée
        self.assertFalse(Face.objects.filter(id=face_id).exists())


class DeleteImageTestCase(TestCase):
    """Tests pour l'endpoint POST /recfac/delete-image/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher_root = patch.object(settings, 'FILES_ROOT_DIR', self.temp_dir)
        self.patcher_root.start()

        self.image = Image.objects.create(
            path="to_delete.jpg",
            filename="to_delete.jpg",
            file_hash="del123",
            file_size=1000,
            width=100,
            height=100,
            scanned=True,
            faces_count=2,
        )

        Face.objects.create(
            image=self.image,
            bbox_x1=0, bbox_y1=0, bbox_x2=50, bbox_y2=50,
            det_score=0.99,
            embedding=create_mock_embedding(),
            person_name="Test Person",
        )

    def tearDown(self):
        self.patcher_root.stop()
        shutil.rmtree(self.temp_dir)

    @patch('recfac.views.verify_admin_token')
    def test_delete_image_success(self, mock_verify):
        """Suppression d'image doit supprimer l'image et ses faces."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.post(
            "/recfac/delete-image/",
            json.dumps({"path": "to_delete.jpg"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["deleted"])

        # Vérifier que l'image est supprimée
        self.assertFalse(Image.objects.filter(path="to_delete.jpg").exists())

    @patch('recfac.views.verify_admin_token')
    def test_delete_image_not_found(self, mock_verify):
        """Suppression d'image inexistante retourne deleted=False."""
        mock_verify.return_value = (True, {"admin": True})

        response = self.client.post(
            "/recfac/delete-image/",
            json.dumps({"path": "nonexistent.jpg"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["deleted"])


class CosineSimilarityTestCase(TestCase):
    """Tests pour les fonctions de calcul de similarite."""

    def test_cosine_similarity_identical(self):
        """Embeddings identiques doivent avoir similarite ~1."""
        from recfac.views import _calculate_cosine_similarity
        emb = create_mock_embedding()
        similarity = _calculate_cosine_similarity(emb, emb)
        self.assertAlmostEqual(similarity, 1.0, places=5)

    def test_cosine_similarity_different(self):
        """Embeddings differents doivent avoir similarite < 1."""
        from recfac.views import _calculate_cosine_similarity
        emb1 = create_mock_embedding()
        emb2 = create_mock_embedding()
        similarity = _calculate_cosine_similarity(emb1, emb2)
        self.assertLess(similarity, 1.0)

    def test_cosine_distance(self):
        """Distance = 1 - similarite."""
        from recfac.views import _calculate_cosine_distance
        emb = create_mock_embedding()
        distance = _calculate_cosine_distance(emb, emb)
        self.assertAlmostEqual(distance, 0.0, places=5)


class NormalizePersonNameTestCase(TestCase):
    """Tests pour la normalisation des noms."""

    def test_normalize_basic(self):
        """Normalisation basique."""
        from recfac.views import _normalize_person_name
        self.assertEqual(_normalize_person_name("john doe"), "John Doe")
        self.assertEqual(_normalize_person_name("JOHN DOE"), "John Doe")
        self.assertEqual(_normalize_person_name("  john   doe  "), "John Doe")

    def test_normalize_empty(self):
        """Noms vides retournent None."""
        from recfac.views import _normalize_person_name
        self.assertIsNone(_normalize_person_name(""))
        self.assertIsNone(_normalize_person_name("   "))
        self.assertIsNone(_normalize_person_name(None))


class InterpretSimilarityTestCase(TestCase):
    """Tests pour l'interpretation des scores de similarite."""

    def test_high_similarity(self):
        """Haute similarite = match probable."""
        from recfac.views import _interpret_similarity
        result = _interpret_similarity(0.7)
        self.assertIn("Match", result)

    def test_low_similarity(self):
        """Basse similarite = personnes differentes."""
        from recfac.views import _interpret_similarity
        result = _interpret_similarity(0.2)
        self.assertIn("diff", result.lower())

    def test_medium_similarity(self):
        """Similarite moyenne = incertain."""
        from recfac.views import _interpret_similarity
        result = _interpret_similarity(0.5)
        self.assertIn("ncertain", result)


class TestRateLimitTestCase(TestCase):
    """Tests pour le rate limiting sur les endpoints de test."""

    def setUp(self):
        self.client = Client()

    @patch('recfac.views.check_rate_limit')
    def test_rate_limit_allowed(self, mock_rate_limit):
        """Requete autorisee par rate limit."""
        mock_rate_limit.return_value = (True, None)

        img = create_test_image()
        from django.core.files.uploadedfile import SimpleUploadedFile
        uploaded = SimpleUploadedFile("test.jpg", img.read(), content_type="image/jpeg")

        # Simuler qu'il n'y a pas de GPU worker configuré
        with patch.object(settings, 'GPU_WORKER_URL', ''):
            response = self.client.post(
                "/recfac/test-vectorize/",
                {"image": uploaded}
            )
            # Sans GPU worker, on attend une erreur 502
            self.assertIn(response.status_code, [400, 502])

    @patch('recfac.views.check_rate_limit')
    def test_rate_limit_blocked(self, mock_rate_limit):
        """Requete bloquee par rate limit retourne 429."""
        from django.http import JsonResponse
        mock_rate_limit.return_value = (False, JsonResponse({"error": "Rate limit exceeded"}, status=429))

        img = create_test_image()
        from django.core.files.uploadedfile import SimpleUploadedFile
        uploaded = SimpleUploadedFile("test.jpg", img.read(), content_type="image/jpeg")

        response = self.client.post(
            "/recfac/test-vectorize/",
            {"image": uploaded}
        )
        self.assertEqual(response.status_code, 429)