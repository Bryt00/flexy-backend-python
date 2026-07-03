from django.contrib import admin
from django import forms
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminPasswordWidget
from .models import User, DeletionRequest

class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=UnfoldAdminPasswordWidget(attrs={'autocomplete': 'new-password'}),
        label="Password",
        required=True,
        help_text="Enter a secure password for the new user."
    )

    class Meta:
        model = User
        fields = ("email", "role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    password = forms.CharField(
        widget=UnfoldAdminPasswordWidget(attrs={'autocomplete': 'new-password'}),
        label="Change Password",
        required=False,
        help_text="Leave blank if you do not want to change the password."
    )

    class Meta:
        model = User
        fields = ("email", "role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

@admin.register(User)
class UserAdmin(ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    
    list_per_page = 20
    list_display = ('email', 'full_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at', 'updated_at')
    search_fields = ('email',)
    
    def full_name(self, obj):
        try:
            return obj.profile.full_name or "—"
        except Exception:
            return "—"
    full_name.short_description = 'Full Name'
    
    fieldsets = (
        (None, {"fields": ("email", "password", "role", "is_active")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    readonly_fields = ('created_at', 'last_login')

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        else:
            defaults['form'] = self.form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

@admin.register(DeletionRequest)
class DeletionRequestAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('user', 'status', 'requested_at', 'processed_at')
    list_filter = ('status', 'requested_at', 'processed_at')
    search_fields = ('user__email',)
    list_editable = ('status',)

