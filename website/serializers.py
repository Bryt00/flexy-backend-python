from rest_framework import serializers
from .models import BlogPost, City, Testimonial, FAQItem, JobOpening, ContactInquiry

class BlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = '__all__'

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'

class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'

class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = '__all__'

class JobOpeningSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOpening
        fields = '__all__'

class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = '__all__'
