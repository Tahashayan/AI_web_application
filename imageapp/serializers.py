from rest_framework import serializers
from .models import ImageTask

class ImageTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageTask
        fields = ['id', 'user', 'original_image', 'bg_removed_image', 'enhanced_image', 'uploaded_at']
        read_only_fields = ['id', 'user', 'bg_removed_image', 'enhanced_image', 'uploaded_at']
        