from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from core_auth.cache_utils import conditional_api_response
from .models import BlogPost, City, Testimonial, FAQItem, JobOpening, ContactInquiry, LegalDocument
from .serializers import (
    BlogPostSerializer, CitySerializer, TestimonialSerializer, 
    FAQItemSerializer, JobOpeningSerializer, ContactInquirySerializer,
    LegalDocumentSerializer
)

class AdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all().order_by('-created_at')
    serializer_class = BlogPostSerializer
    permission_classes = [AdminOrReadOnly]

class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all().order_by('name')
    serializer_class = CitySerializer
    permission_classes = [AdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return conditional_api_response(request, queryset, self.serializer_class)

class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonial.objects.all().order_by('-created_at')
    serializer_class = TestimonialSerializer
    permission_classes = [AdminOrReadOnly]

class FAQItemViewSet(viewsets.ModelViewSet):
    queryset = FAQItem.objects.all().order_by('order', 'id')
    serializer_class = FAQItemSerializer
    permission_classes = [AdminOrReadOnly]

class JobOpeningViewSet(viewsets.ModelViewSet):
    queryset = JobOpening.objects.all().order_by('-created_at')
    serializer_class = JobOpeningSerializer
    permission_classes = [AdminOrReadOnly]

class ContactInquiryViewSet(viewsets.ModelViewSet):
    queryset = ContactInquiry.objects.all().order_by('-created_at')
    serializer_class = ContactInquirySerializer
    # Allow anyone to create, but only admins to view/update/delete
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

class LegalDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = LegalDocumentSerializer
    permission_classes = [AdminOrReadOnly]
    lookup_field = 'document_type'

    def get_queryset(self):
        queryset = LegalDocument.objects.all().order_by('-last_updated')
        doc_type = self.request.query_params.get('document_type', None)
        if doc_type is not None:
            queryset = queryset.filter(document_type=doc_type)
        return queryset

    def get_object(self):
        doc_type = self.kwargs.get('document_type')
        obj = LegalDocument.objects.filter(document_type=doc_type).order_by('-last_updated').first()
        if not obj:
            obj = LegalDocument.objects.filter(slug=doc_type).order_by('-last_updated').first()
        
        if not obj:
            defaults = {
                'privacy': ('Privacy Policy', 'FlexyRide Privacy Policy:\n\nWe respect your privacy and are committed to protecting your personal data. We collect location and account data to provide safe, reliable ride-hailing and logistics services.'),
                'terms': ('Terms of Service', 'FlexyRide Terms of Service:\n\nWelcome to FlexyRide. By using our services, you agree to these Terms of Service. Please review all terms before requesting rides or services.'),
                'cookies': ('Cookie Policy', 'FlexyRide Cookie Policy:\n\nWe use essential session tokens and cookies to secure your account and personalize your experience.'),
                'about': ('About Us', 'About FlexyRide:\n\nFlexyRide is Ghana\'s premier ride-hailing and delivery service offering fast, affordable, and safe mobility.'),
            }
            title, content = defaults.get(doc_type, (doc_type.replace('_', ' ').title(), 'Legal document content is currently being updated.'))
            obj, _ = LegalDocument.objects.get_or_create(
                document_type=doc_type,
                defaults={
                    'title': title,
                    'slug': doc_type,
                    'content': content
                }
            )
        self.check_object_permissions(self.request, obj)
        return obj

