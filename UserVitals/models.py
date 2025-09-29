from django.db import models
from Users.models import Patient

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

class UserVitals(models.Model):
    patient = models.OneToOneField(Patient,on_delete=models.CASCADE,related_name='vitals')
    steps = models.IntegerField(null=True,blank=True)
    calories = models.FloatField(null=True,blank=True)
    systolic_blood_pressure = models.FloatField(null=True,blank=True)
    diastolic_blood_pressure = models.FloatField(null=True,blank=True)
    heart_rate = models.FloatField(null=True,blank=True)
    oxygen_sat = models.FloatField(null=True,blank=True)    


class UserBPM(models.Model):
    patient = models.ForeignKey(Patient,on_delete=models.CASCADE)
    heart_rate = models.FloatField(null=True,blank=True)


    



