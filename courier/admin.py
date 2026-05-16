from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Delivery

@admin.register(Delivery)
class DeliveryAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ('id', 'status', 'item_category')
