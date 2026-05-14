from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from subscription.models import Subscription
# Create your models here.

class ImageTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    original_image = models.ImageField(upload_to='uploads/')
    bg_removed_image = models.URLField(max_length=500, blank=True, null=True)
    enhanced_image = models.URLField(max_length=500, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.user:
            return f"Task {self.id} by {self.user.username}"
        return f"Task {self.id} by Guest"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credits_remaining = models.IntegerField(default=5)
    total_images_processed = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} Profile"
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        
class SystemLog(models.Model):
    task = models.ForeignKey(ImageTask, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='FAILED')
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Log {self.id} - {self.status}"
    