from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import BlogPost, City, Testimonial, FAQItem, JobOpening, ContactInquiry
from .serializers import (
    BlogPostSerializer, CitySerializer, TestimonialSerializer, 
    FAQItemSerializer, JobOpeningSerializer, ContactInquirySerializer
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
