from django.urls import path

from src.config import settings
from . import views

urlpatterns = [
    path(f'webhook/{settings.BOT_TOKEN}/', views.webhook_view, name='webhook'),
]
