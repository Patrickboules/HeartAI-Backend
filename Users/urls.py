from django.urls import path
from .views import *

urlpatterns = [
    path('doctors/create/', create_Doctor, name='create_doctor'),  
    path('doctors/list/', get_Doctors_list, name='get_doctors_list'),  

    path('patients/create/', create_Patient, name='create_patient'),  
    path('patients/list/', get_Patients_list, name='get_patients_list'),  
    path('remove/', remove, name='remove'),
    

    path('assignment-requests/create/', create_request, name='create_assignment_request'),
    path('assignment-requests/list/', pending_requests_list, name='list_pending_requests'),
    path('assignment-requests/respond/', respond_request, name='respond_to_request'),  
]

"Login"