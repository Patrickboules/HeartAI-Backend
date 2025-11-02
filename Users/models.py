from django.db import models
from django.contrib.auth.hashers import make_password


class Doctor(models.Model):
    first_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    full_name = models.CharField(max_length=200,null=True)
    email = models.EmailField(unique = True,primary_key = True)
    password = models.CharField(max_length=128,null=True)
    specialization = models.CharField(max_length = 100,null=True)
    description = models.TextField(blank=True)
    auth_method = models.CharField(
    max_length=10, 
    choices=[('manual', 'Manual'), ('google', 'Google')], 
    default='manual'
)

class Patient(models.Model):
    first_name = models.CharField(max_length = 100) 
    last_name = models.CharField(max_length = 100)
    full_name = models.CharField(max_length=200,null=True)
    email = models.EmailField(unique = True,primary_key= True)
    password = models.CharField(max_length=128,null=True)
    doctor = models.ForeignKey(
        Doctor,
        on_delete =models.CASCADE,
        related_name = 'patients',
        blank=True,
        null=True
        )
    auth_method = models.CharField(
    max_length=10, 
    choices=[('manual', 'Manual'), ('google', 'Google')], 
    default='manual'
)
    
class AssignmentRequest(models.Model):
    STATUS_CHOICES = (('pending','Pending'),('accepted','Accepted'),('rejected','Rejected'))

    status = models.CharField(choices=STATUS_CHOICES,default='pending')
    patient = models.ForeignKey(Patient,on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  


class UserCredentials(models.Model):
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name='credentials')
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)  
    token_uri = models.URLField()
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    scopes = models.JSONField()  
    expires_at = models.DateTimeField()  
    created_at = models.DateTimeField(auto_now_add=True)