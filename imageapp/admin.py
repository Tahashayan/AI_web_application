from django.contrib import admin
from .models import UserProfile, SystemLog
from subscription.models import Subscription

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'credits_remaining', 'total_images_processed')
    list_filter = ('user',)
    search_fields = ('user__username', 'user__email')
       
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(user__is_superuser = True) 

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'error_snippet', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('task', 'status', 'error_message', 'created_at')
    
    def error_snippet(self, obj):
        return obj.error_message[:50] + "..." if len(obj.error_message) > 50 else obj.error_message
    error_snippet.short_description = "Error Message"