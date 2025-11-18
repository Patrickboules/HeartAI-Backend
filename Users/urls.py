from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import *

urlpatterns = [
    path('patients/create/', create_Patient, name='create_patient'),
    path('patients/login/',Patient_Login,name='Patient_Login'),
    path('doctors/list/', get_Doctors_list, name='get_doctors_list'),  
  
    path('doctors/create/', create_Doctor, name='create_doctor'),
    path('doctors/login/',Doctor_Login,name = 'doctor_login'),

    
    path('assignment-requests/create/', create_request, name='create_assignment_request'),
    path('assignment-requests/list/', pending_requests_list, name='list_pending_requests'),
    path('assignment-requests/respond/', respond_request, name='respond_to_request'),
    path('remove/', remove_patient_assignment, name='remove'),
    path('patients/list/', get_Patients_list, name='get_patients_list'), 

    path('auth/', get_auth, name='auth'),
    path('callback/', callback, name='callback'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

