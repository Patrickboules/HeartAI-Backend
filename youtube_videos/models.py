from django.db import models

class Videos(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link = models.URLField(unique=True)