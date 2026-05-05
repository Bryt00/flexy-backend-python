from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    BlogPostViewSet, CityViewSet, TestimonialViewSet, 
    FAQItemViewSet, JobOpeningViewSet, ContactInquiryViewSet
)

router = DefaultRouter()
router.register(r'blogs', BlogPostViewSet, basename='blog')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')
router.register(r'faqs', FAQItemViewSet, basename='faq')
router.register(r'jobs', JobOpeningViewSet, basename='job')
router.register(r'inquiries', ContactInquiryViewSet, basename='inquiry')

urlpatterns = [
    path('', include(router.urls)),
]
