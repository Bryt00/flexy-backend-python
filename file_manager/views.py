import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.core.files.storage import default_storage
from .models import FileMetadata

from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiResponse, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import AllowAny

class FileUploadView(APIView):
    """File upload service for profile pictures, documents, and proofs."""
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        tags=['Files'],
        summary='Upload a file',
        description=(
            'Uploads a file to media storage and returns its absolute URL.\n\n'
            'Generates a unique UUID filename to prevent collisions. Stores file metadata '
            '(size, content type, original filename) in DB.'
        ),
        operation_id="upload_file",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'The file binary payload to upload.'
                    }
                },
                'required': ['file']
            }
        },
        responses={
            201: inline_serializer(
                name='FileUploadResponse',
                fields={
                    'id': drf_serializers.UUIDField(help_text='File metadata record ID.'),
                    'file_url': drf_serializers.URLField(help_text='Absolute public URL of the uploaded file.'),
                    'file_name': drf_serializers.CharField(help_text='Original filename.'),
                    'status': drf_serializers.CharField(default='success'),
                }
            ),
            400: OpenApiResponse(description='No file uploaded.'),
        }
    )
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique filename to prevent collisions
        file_extension = file_obj.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Save the file to storage
        path = default_storage.save(f'uploads/{unique_filename}', file_obj)
        file_url = request.build_absolute_uri(default_storage.url(path))

        # Create metadata Record
        metadata = FileMetadata.objects.create(
            uploader=request.user if request.user.is_authenticated else None,
            file_name=file_obj.name,
            file_url=file_url,
            file_size=file_obj.size,
            content_type=file_obj.content_type
        )

        return Response({
            'id': str(metadata.id),
            'file_url': file_url,
            'file_name': file_obj.name,
            'status': 'success'
        }, status=status.HTTP_201_CREATED)
