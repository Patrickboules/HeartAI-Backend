from django.db import models

class Doctor(models.Model):
    first_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    full_name = models.CharField(max_length=200,null=True)
    email = models.EmailField(unique = True,primary_key=True,default="Doctor Username Email")
    password = models.CharField(max_length=128,null=True)
    specialization = models.CharField(max_length = 100,null=True)
    description = models.TextField(blank=True)

class Patient(models.Model):
    first_name = models.CharField(max_length = 100) 
    last_name = models.CharField(max_length = 100)
    full_name = models.CharField(max_length=200,null=True)
    email = models.EmailField(unique = True,primary_key=True,default="Patient Email")
    password = models.CharField(max_length=128,null=True)
    doctor = models.ForeignKey(
        Doctor,
        on_delete =models.CASCADE,
        related_name = 'patients',
        blank=True,
        null=True
        )
    
class AssignmentRequest(models.Model):
    STATUS_CHOICES = (('pending','Pending'),('accepted','Accepted'),('rejected','Rejected'))

    status = models.CharField(choices=STATUS_CHOICES,default='pending')
    patient = models.ForeignKey(Patient,on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  