from django.db import models
from imageapp.models import User
from django.utils.timezone import now
# Create your models here.
class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=255)
    subscription_id = models.CharField(max_length=255, unique=True)
    product_name = models.CharField(max_length=255)
    price = models.IntegerField()
    interval = models.CharField(max_length=50, default="month")
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_canceled = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    
    @property
    def is_active(self):
        if self.end_date:
            if now() < self.end_date:
                return True
            else:
                return False
        else:
            return True
    
    @property
    def tier(self):
        tier_mapping = {
            'Lite': 1,
            'Pro': 2,
            'Volume': 3,
        }
        tier = tier_mapping.get(self.product_name, None)
        return tier
    
    def __str__(self):
        return f"{self.user.username} - {self.product_name} - Active: {self.is_active}"