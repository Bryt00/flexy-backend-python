from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Wallet, Transaction

@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('user', 'balance', 'currency')
    list_filter = ('created_at', 'updated_at')

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('id', 'amount', 'type', 'status')
    list_filter = ('type', 'status', 'created_at')
