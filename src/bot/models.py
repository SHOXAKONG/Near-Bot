from django.db import models


class TelegramProfile(models.Model):
    tg_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    step = models.CharField(max_length=100, default='default')
    language = models.CharField(max_length=2, default='uz')
    temp_data = models.JSONField(default=dict, null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    near_user_id = models.IntegerField(null=True, blank=True, verbose_name="Near loyihasi User IDsi")

    def __str__(self):
        if self.near_user_id:
            return f"Near User ID: {self.near_user_id} (TG ID: {self.tg_id})"
        return f"TG Profile: {self.tg_id}"

    class Meta:
        verbose_name = "Telegram Profile"
        verbose_name_plural = "Telegram Profiles"
