from django.contrib import admin
from .models import TelegramProfile

@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    pass