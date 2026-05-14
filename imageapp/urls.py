from django.urls import path
from . import views, api

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('history/', views.user_history, name='history'),
    path('logout/', views.logout_user, name='logout'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('api/v1/process/<str:action>/', api.api_process_image, name='api_process_image'),
    path('api/token/', views.get_api_token, name='get_api_token'),
]