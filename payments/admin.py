from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Wallet, Transaction

@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('user_display', 'balance', 'currency')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__profile__full_name')

    def user_display(self, obj):
        try:
            full_name = obj.user.profile.full_name
            if full_name:
                return f"{full_name} ({obj.user.email})"
        except Exception:
            pass
        return obj.user.email
    user_display.short_description = 'User'

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('id', 'user_display', 'amount', 'type', 'status')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('id', 'wallet__user__email', 'wallet__user__profile__full_name')

    def user_display(self, obj):
        try:
            user = obj.wallet.user
            full_name = user.profile.full_name
            if full_name:
                return f"{full_name} ({user.email})"
            return user.email
        except Exception:
            return "—"
    user_display.short_description = 'User'
