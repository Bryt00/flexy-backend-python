from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    BlogPostViewSet, CityViewSet, TestimonialViewSet, 
    FAQItemViewSet, JobOpeningViewSet, ContactInquiryViewSet,
    LegalDocumentViewSet
)

router = DefaultRouter()
router.register(r'blogs', BlogPostViewSet, basename='blog')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')
router.register(r'faqs', FAQItemViewSet, basename='faq')
router.register(r'jobs', JobOpeningViewSet, basename='job')
router.register(r'inquiries', ContactInquiryViewSet, basename='inquiry')
router.register(r'legal-documents', LegalDocumentViewSet, basename='legal-document')

urlpatterns = [
    path('', include(router.urls)),
]
