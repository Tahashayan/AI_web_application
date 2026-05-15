from django.contrib import admin
from .models import Subscription
# Register your models here.
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    user = 'user__username'
    list_display = ['user', 'product_name', 'interval', 'start_date', 'end_date', 'is_active']
    list_filter = ['user', 'product_name', 'interval']
    search_fields = ['user']