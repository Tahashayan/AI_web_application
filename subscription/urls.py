from django.urls import path
from .views import *

urlpatterns = [
    path('', subscription_view, name="subscription"),
    path('create/', create_subscription, name='create_subscription'),
    path('my_sub/', my_sub_view, name='my_sub'),
    path('cancel/<subscription_id>', cancel_subscription, name='cancel_subscription'),
]
