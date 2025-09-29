from django.db import models

class Videos(models.Model):
    title = models.CharField()
    description = models.TextField()
    link = models.URLField()