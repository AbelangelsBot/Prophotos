from django.urls import path
from . import views

urlpatterns = [
    # Health & Status
    path('check-health/', views.check_health, name='check_health'),

    # Scan operations
    path('scan-image/', views.scan_image, name='scan_image'),
    path('scan-multiple/', views.scan_multiple, name='scan_multiple'),
    path('scan-all-images/', views.scan_all_images, name='scan_all_images'),
    path('scan-folder/', views.scan_folder, name='scan_folder'),

    # Search & Details
    path('search-face/', views.search_face, name='search_face'),
    path('image-details/', views.get_image_details, name='get_image_details'),

    # Face tagging & management
    path('face/tag/', views.tag_face, name='tag_face'),
    path('face/tag-with-similarity/', views.tag_face_with_similarity, name='tag_face_with_similarity'),
    path('face/delete/', views.delete_face, name='delete_face'),
    path('face/image/', views.get_face_image, name='get_face_image'),
    path('faces/untagged/', views.get_untagged_faces, name='get_untagged_faces'),

    # Persons
    path('persons/', views.list_persons, name='list_persons'),
    path('persons/faces-multiple/', views.get_multiple_persons_faces, name='get_multiple_persons_faces'),
    path('person/faces/', views.get_person_faces, name='get_person_faces'),

    # Tests
    path('test-vectorize/', views.test_vectorize, name='test_vectorize'),
    path('test-compare-faces/', views.test_compare_faces, name='test_compare_faces'),

    # Delete (used by backend-files)
    path('delete-image/', views.delete_image, name='delete_image'),
    path('delete-multiple/', views.delete_multiple_images, name='delete_multiple_images'),
]
