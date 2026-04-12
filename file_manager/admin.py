from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import FileMetadata

@admin.register(FileMetadata)
class FileMetadataAdmin(ModelAdmin):
    list_display = ('file_name', 'content_type', 'file_size')
