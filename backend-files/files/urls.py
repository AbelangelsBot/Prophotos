from django.urls import path
from . import views

urlpatterns = [
    path('hello/', views.hello, name='hello'),
    path('', views.get_files, name='get_files'),
    path('image/', views.get_image_info, name='get_image_info'),
    path('image/download/', views.download_image, name='download_image'),
    path('add/', views.add_files, name='add_files'),
    path('folder/', views.add_folder, name='add_folder'),
]
