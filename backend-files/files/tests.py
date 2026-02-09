"""
Tests automatisés pour le microservice files.
Couvre: listage, upload, suppression, compression d'images, sécurité des chemins.
"""
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase, Client, override_settings
from PIL import Image

# Mock user for token generation
class MockUser:
    def __init__(self, user_id, username, admin=False):
        self.id = user_id
        self.username = username
        self.admin = admin


def create_test_image(width=100, height=100, color='red'):
    """Crée une image de test en mémoire."""
    img = Image.new('RGB', (width, height), color=color)
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer


class HelloEndpointTestCase(TestCase):
    """Tests pour l'endpoint /files/hello/"""

    def setUp(self):
        self.client = Client()

    def test_hello_get(self):
        """GET /files/hello/ doit retourner un message de disponibilite."""
        response = self.client.get("/files/hello/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("Files", data["message"])

    def test_hello_post_not_allowed(self):
        """POST /files/hello/ doit retourner 405."""
        response = self.client.post("/files/hello/")
        self.assertEqual(response.status_code, 405)


class PathSecurityTestCase(TestCase):
    """Tests pour la sécurité des chemins (path traversal)."""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        # Créer un fichier test
        test_file = Path(self.temp_dir) / "test.jpg"
        img = Image.new('RGB', (10, 10), color='blue')
        img.save(test_file, format='JPEG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_path_traversal_blocked(self):
        """Les tentatives de path traversal doivent etre bloquees."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "\\windows\\system32",
            "folder/../../../etc/passwd",
        ]
        for path in malicious_paths:
            response = self.client.get(f"/files/?path={path}")
            self.assertIn(response.status_code, [400, 404],
                f"Path {path} should be rejected")

    def test_valid_path_allowed(self):
        """Les chemins valides dans ROOT_DIR doivent etre acceptes."""
        response = self.client.get("/files/?path=")
        self.assertEqual(response.status_code, 200)


class GetFilesTestCase(TestCase):
    """Tests pour l'endpoint GET /files/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        # Créer structure de test
        (Path(self.temp_dir) / "subfolder").mkdir()
        img = Image.new('RGB', (50, 50), color='green')
        img.save(Path(self.temp_dir) / "image1.jpg", format='JPEG')
        img.save(Path(self.temp_dir) / "image2.png", format='PNG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_get_files_root(self):
        """GET /files/ sans path retourne le contenu de la racine."""
        response = self.client.get("/files/?path=")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        # Doit contenir subfolder et les 2 images
        names = [item["Name"] for item in data]
        self.assertIn("subfolder", names)

    def test_get_files_nonexistent_directory(self):
        """GET /files/ avec chemin inexistant retourne 404."""
        response = self.client.get("/files/?path=nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_get_files_returns_null_thumbnails(self):
        """GET /files/ retourne Img: null pour les images (thumbnails via /files/thumbnail/)."""
        response = self.client.get("/files/?path=")
        data = response.json()
        images = [item for item in data if not item["isDirectory"]]
        self.assertTrue(len(images) > 0)
        for img in images:
            self.assertIsNone(img.get("Img"))


class GetThumbnailTestCase(TestCase):
    """Tests pour l'endpoint GET /files/thumbnail/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        img = Image.new('RGB', (500, 500), color='green')
        img.save(Path(self.temp_dir) / "thumb_test.jpg", format='JPEG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_thumbnail_no_path(self):
        """GET /files/thumbnail/ sans path retourne 400."""
        response = self.client.get("/files/thumbnail/")
        self.assertEqual(response.status_code, 400)

    def test_thumbnail_nonexistent(self):
        """GET /files/thumbnail/ fichier inexistant retourne 404."""
        response = self.client.get("/files/thumbnail/?path=nonexistent.jpg")
        self.assertEqual(response.status_code, 404)

    def test_thumbnail_guest(self):
        """GET /files/thumbnail/ sans token retourne JPEG (guest/blurred)."""
        response = self.client.get("/files/thumbnail/?path=thumb_test.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    @patch('files.views.verify_token')
    def test_thumbnail_authenticated_via_query(self, mock_verify):
        """GET /files/thumbnail/?token=xxx retourne JPEG (full quality)."""
        mock_verify.return_value = {"user_id": 1}
        response = self.client.get("/files/thumbnail/?path=thumb_test.jpg&token=test_token")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertIn("ETag", response)
        self.assertIn("Cache-Control", response)

    @patch('files.views.verify_token')
    def test_thumbnail_etag_304(self, mock_verify):
        """Deuxieme requete avec ETag retourne 304 Not Modified."""
        mock_verify.return_value = {"user_id": 1}
        r1 = self.client.get("/files/thumbnail/?path=thumb_test.jpg&token=test_token")
        etag = r1["ETag"]
        r2 = self.client.get(
            "/files/thumbnail/?path=thumb_test.jpg&token=test_token",
            HTTP_IF_NONE_MATCH=etag,
        )
        self.assertEqual(r2.status_code, 304)

    def test_thumbnail_path_traversal(self):
        """Path traversal doit etre bloque."""
        response = self.client.get("/files/thumbnail/?path=../../etc/passwd")
        self.assertIn(response.status_code, [400, 404])

    def test_thumbnail_post_not_allowed(self):
        """POST /files/thumbnail/ doit retourner 405."""
        response = self.client.post("/files/thumbnail/")
        self.assertEqual(response.status_code, 405)


class AddFilesTestCase(TestCase):
    """Tests pour l'endpoint POST /files/add/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_add_files_no_token(self):
        """Upload sans token doit echouer."""
        response = self.client.post("/files/add/")
        self.assertEqual(response.status_code, 401)

    @patch('files.views.verify_token')
    @patch('files.views.scan_image_async')
    def test_add_files_non_admin(self, mock_scan, mock_verify):
        """Upload avec token non-admin doit echouer."""
        mock_verify.return_value = {"admin": False, "user_id": 1}

        img = create_test_image()
        response = self.client.post(
            "/files/add/",
            {"path": "", "files": img},
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 403)

    @patch('files.views.verify_token')
    @patch('files.views.scan_image_async')
    def test_add_files_admin_success(self, mock_scan, mock_verify):
        """Upload avec token admin doit reussir."""
        mock_verify.return_value = {"admin": True, "user_id": 1}

        img = create_test_image()
        from django.core.files.uploadedfile import SimpleUploadedFile
        uploaded = SimpleUploadedFile("test.jpg", img.read(), content_type="image/jpeg")

        response = self.client.post(
            "/files/add/",
            {"path": "", "files": uploaded},
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue((Path(self.temp_dir) / "test.jpg").exists())


class AddFolderTestCase(TestCase):
    """Tests pour l'endpoint POST /files/folder/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_add_folder_no_token(self):
        """Creation de dossier sans token doit echouer."""
        response = self.client.post(
            "/files/folder/",
            json.dumps({"folder_name": "newfolder"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    @patch('files.views.verify_token')
    def test_add_folder_success(self, mock_verify):
        """Creation de dossier avec token admin doit reussir."""
        mock_verify.return_value = {"admin": True, "user_id": 1}

        response = self.client.post(
            "/files/folder/",
            json.dumps({"path": "", "folder_name": "newfolder"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue((Path(self.temp_dir) / "newfolder").is_dir())

    @patch('files.views.verify_token')
    def test_add_folder_duplicate(self, mock_verify):
        """Creation de dossier existant doit echouer."""
        mock_verify.return_value = {"admin": True, "user_id": 1}
        (Path(self.temp_dir) / "existing").mkdir()

        response = self.client.post(
            "/files/folder/",
            json.dumps({"path": "", "folder_name": "existing"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 409)


class DeleteItemTestCase(TestCase):
    """Tests pour l'endpoint POST /files/delete/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        # Créer fichiers de test
        img = Image.new('RGB', (10, 10), color='red')
        img.save(Path(self.temp_dir) / "to_delete.jpg", format='JPEG')
        (Path(self.temp_dir) / "folder_to_delete").mkdir()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_delete_no_token(self):
        """Suppression sans token doit echouer."""
        response = self.client.post(
            "/files/delete/",
            json.dumps({"path": "to_delete.jpg"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    @patch('files.views.verify_token')
    @patch('files.views.delete_image_from_recfac_async')
    def test_delete_file_success(self, mock_recfac, mock_verify):
        """Suppression de fichier avec token admin doit reussir."""
        mock_verify.return_value = {"admin": True, "user_id": 1}

        response = self.client.post(
            "/files/delete/",
            json.dumps({"path": "to_delete.jpg"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse((Path(self.temp_dir) / "to_delete.jpg").exists())

    @patch('files.views.verify_token')
    def test_delete_folder_success(self, mock_verify):
        """Suppression de dossier avec token admin doit reussir."""
        mock_verify.return_value = {"admin": True, "user_id": 1}

        response = self.client.post(
            "/files/delete/",
            json.dumps({"path": "folder_to_delete"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse((Path(self.temp_dir) / "folder_to_delete").exists())

    @patch('files.views.verify_token')
    def test_delete_root_blocked(self, mock_verify):
        """Suppression de la racine doit etre interdite."""
        mock_verify.return_value = {"admin": True, "user_id": 1}

        response = self.client.post(
            "/files/delete/",
            json.dumps({"path": ""}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 400)


class DeleteMultipleTestCase(TestCase):
    """Tests pour l'endpoint POST /files/delete-multiple/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        # Créer fichiers de test
        img = Image.new('RGB', (10, 10), color='red')
        for i in range(3):
            img.save(Path(self.temp_dir) / f"file{i}.jpg", format='JPEG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    @patch('files.views.verify_token')
    @patch('files.views.delete_multiple_from_recfac_async')
    def test_delete_multiple_success(self, mock_recfac, mock_verify):
        """Suppression multiple avec token admin doit reussir."""
        mock_verify.return_value = {"admin": True, "user_id": 1}

        response = self.client.post(
            "/files/delete-multiple/",
            json.dumps({"paths": ["file0.jpg", "file1.jpg"]}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["deleted_count"], 2)
        self.assertFalse((Path(self.temp_dir) / "file0.jpg").exists())
        self.assertFalse((Path(self.temp_dir) / "file1.jpg").exists())
        self.assertTrue((Path(self.temp_dir) / "file2.jpg").exists())


class GetImageInfoTestCase(TestCase):
    """Tests pour l'endpoint GET /files/image/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        # Créer image de test
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(Path(self.temp_dir) / "info_test.jpg", format='JPEG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_get_image_info_no_path(self):
        """GET /files/image/ sans path doit echouer."""
        response = self.client.get("/files/image/")
        self.assertEqual(response.status_code, 400)

    def test_get_image_info_nonexistent(self):
        """GET /files/image/ avec chemin inexistant doit retourner 404."""
        response = self.client.get("/files/image/?path=nonexistent.jpg")
        self.assertEqual(response.status_code, 404)

    def test_get_image_info_guest(self):
        """GET /files/image/ sans token retourne image protegee."""
        response = self.client.get("/files/image/?path=info_test.jpg")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["Name"], "info_test.jpg")
        self.assertIn("Img", data)

    @patch('files.views.verify_token')
    def test_get_image_info_authenticated(self, mock_verify):
        """GET /files/image/ avec token retourne image complete."""
        mock_verify.return_value = {"user_id": 1}

        response = self.client.get(
            "/files/image/?path=info_test.jpg",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["Name"], "info_test.jpg")
        self.assertIn("token info", data)
        self.assertEqual(data["token info"], "Token valide")


class DownloadImageTestCase(TestCase):
    """Tests pour l'endpoint GET /files/image/download/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        img = Image.new('RGB', (50, 50), color='green')
        img.save(Path(self.temp_dir) / "download.jpg", format='JPEG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_download_no_token(self):
        """Telechargement sans token doit echouer."""
        response = self.client.get("/files/image/download/?path=download.jpg")
        self.assertEqual(response.status_code, 401)

    @patch('files.views.verify_token')
    def test_download_success(self, mock_verify):
        """Telechargement avec token valide doit reussir."""
        mock_verify.return_value = {"user_id": 1}

        response = self.client.get(
            "/files/image/download/?path=download.jpg",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="download.jpg"')


class ImagesBatchTestCase(TestCase):
    """Tests pour l'endpoint POST /files/images-batch/"""

    def setUp(self):
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()
        self.patcher = patch('files.views.ROOT_DIR', self.temp_dir)
        self.patcher.start()

        # Créer plusieurs images de test
        for i in range(5):
            img = Image.new('RGB', (100, 100), color='yellow')
            img.save(Path(self.temp_dir) / f"batch{i}.jpg", format='JPEG')

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir)

    def test_batch_no_token(self):
        """Batch sans token doit echouer."""
        response = self.client.post(
            "/files/images-batch/",
            json.dumps({"paths": ["batch0.jpg"]}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    @patch('files.views.verify_token')
    def test_batch_success(self, mock_verify):
        """Batch avec token valide doit reussir."""
        mock_verify.return_value = {"user_id": 1}

        response = self.client.post(
            "/files/images-batch/",
            json.dumps({"paths": ["batch0.jpg", "batch1.jpg", "batch2.jpg"]}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        success_count = sum(1 for r in data["results"] if r.get("success"))
        self.assertEqual(success_count, 3)

    @patch('files.views.verify_token')
    def test_batch_max_limit(self, mock_verify):
        """Batch avec plus de 100 chemins doit echouer."""
        mock_verify.return_value = {"user_id": 1}

        paths = [f"file{i}.jpg" for i in range(101)]
        response = self.client.post(
            "/files/images-batch/",
            json.dumps({"paths": paths}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 400)

    @patch('files.views.verify_token')
    def test_batch_mixed_results(self, mock_verify):
        """Batch avec certains fichiers manquants."""
        mock_verify.return_value = {"user_id": 1}

        response = self.client.post(
            "/files/images-batch/",
            json.dumps({"paths": ["batch0.jpg", "nonexistent.jpg"]}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test_token"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = {r["path"]: r for r in data["results"]}
        self.assertTrue(results["batch0.jpg"]["success"])
        self.assertFalse(results["nonexistent.jpg"]["success"])


class ImageCompressionTestCase(TestCase):
    """Tests pour les fonctions de compression d'images."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = Path(self.temp_dir) / "compress_test.jpg"
        img = Image.new('RGB', (1000, 1000), color='purple')
        img.save(self.test_image_path, format='JPEG')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_compress_and_encode_image(self):
        """compress_and_encode_image doit retourner une image base64."""
        from files.views import _compress_image_internal
        result = _compress_image_internal(str(self.test_image_path), (300, 300), 65)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("data:image/jpeg;base64,"))

    def test_compress_image_guest(self):
        """compress_and_encode_image_guest doit retourner une image flouee."""
        from files.views import _compress_image_guest_internal
        result = _compress_image_guest_internal(str(self.test_image_path))
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("data:image/jpeg;base64,"))

    def test_generate_protected_image(self):
        """generate_protected_image doit retourner une image avec watermark."""
        from files.views import generate_protected_image
        result = generate_protected_image(str(self.test_image_path))
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("data:image/jpeg;base64,"))