from django.contrib import admin
from .models import Image, Face, Person


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'filename', 'path', 'scanned', 'faces_count', 'created_at')
    list_filter = ('scanned', 'created_at')
    search_fields = ('filename', 'path', 'file_hash')
    readonly_fields = ('id', 'file_hash', 'created_at', 'updated_at')


@admin.register(Face)
class FaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'person_name', 'det_score', 'cluster_id', 'created_at')
    list_filter = ('person_name', 'cluster_id', 'created_at')
    search_fields = ('person_name', 'image__filename')
    readonly_fields = ('id', 'created_at')


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'reference_face', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at')
