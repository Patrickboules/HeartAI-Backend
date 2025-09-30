from django.db import models

class Videos(models.Model):
    title = models.CharField(max_length=255)
    mini_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    link = models.URLField(unique=True)