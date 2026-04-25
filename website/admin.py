from django.contrib import admin
from .models import BlogPost, ContactInquiry, City, Testimonial, FAQItem, JobOpening

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_name', 'category', 'is_published', 'published_at', 'created_at')
    list_filter = ('is_published', 'category', 'created_at')
    search_fields = ('title', 'author_name', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'rating', 'created_at')
    list_filter = ('role', 'rating')
    search_fields = ('name', 'quote')


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'category', 'is_resolved', 'created_at')
    list_filter = ('category', 'is_resolved', 'created_at')
    search_fields = ('name', 'email', 'message')
    list_editable = ('is_resolved',)
    date_hierarchy = 'created_at'

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'is_active', 'driver_count')
    list_filter = ('is_active', 'region')
    search_fields = ('name', 'region')
    list_editable = ('is_active', 'driver_count')

@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'order', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('question', 'answer')
    list_editable = ('order', 'is_active')

@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'location', 'job_type', 'is_active', 'created_at')
    list_filter = ('department', 'job_type', 'is_active')
    search_fields = ('title', 'description')
    list_editable = ('is_active',)
