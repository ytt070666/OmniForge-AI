"""Reference model copied into a real Django app during the Django lab."""

DJANGO_MODEL_EXAMPLE = r'''
from django.db import models

class Incident(models.Model):
    title = models.CharField(max_length=240)
    severity = models.CharField(max_length=16)
    status = models.CharField(max_length=32, default="open")
    asset_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: {self.title}"
'''
