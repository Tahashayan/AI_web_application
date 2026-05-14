from django import forms
from .models import ImageTask

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = ImageTask
        fields = ['original_image']
        widgets = {
            'original_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }
        
        