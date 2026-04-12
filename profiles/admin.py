from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Profile, DriverVerification

@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ('user', 'full_name', 'phone_number', 'rating')

@admin.register(DriverVerification)
class DriverVerificationAdmin(ModelAdmin):
    list_display = ('driver', 'license_number', 'is_verified')
