from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from .models import Doctor,Patient,AssignmentRequest

@api_view(['POST'])
def create_Doctor(request):
    data = request.data
    required_fields = ['first_name', 'last_name', 'password','email','specialization','description']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return Response(
            {"error": f"Missing fields: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        doctor = Doctor.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            full_name = f"{data['first_name']} {data['last_name']}", 
            password = make_password(data['password']),
            email=data['email'],
            specialization = data['specialization'],
            description = data['description']
        )

        return Response(
            {
                "message": "Doctor created successfully"
            },
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
def get_Doctors_list(request):
    try:
        doctors = Doctor.objects.values('full_name','email','specialization','description')
        doctors_Dict = [{"full_name": doctor['full_name'],
                        "email":doctor['email'],
                        "specialization":doctor['specialization'],
                        "description":doctor['description']
                        } for doctor in doctors]
        return Response(doctors_Dict)
    except Exception as e:
        return Response({'error':e})

@api_view(['POST'])
def create_Patient(request):
    data = request.data

    required_fields = ['first_name', 'last_name', 'email','password']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return Response(
            {"error": f"Missing fields: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        doctor_email = data.get('doctor')
        if doctor_email:
            doctor_chosen =  get_object_or_404(Doctor,email = doctor_email)
        else:
            doctor_chosen = None

        patient = Patient.objects.create(
            first_name = data['first_name'],
            last_name = data['last_name'],
            full_name = f"{data['first_name']} {data['last_name']}", 
            email = data['email'],
            password = make_password(data['password']),
            doctor = doctor_chosen
            )

        return Response(
            {
                "message": "Patient created successfully"
            },
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
def get_Patients_list(request):
    doctor_email = request.query_params.get('doctor')
    doctor_request = get_object_or_404(Doctor,email = doctor_email)
    patient_list = Patient.objects.filter(doctor = doctor_request).values('full_name','email')
    patient_list = [{'full_name':patient['full_name'],'email':patient['email']} for patient in patient_list]

    return Response(patient_list)

@api_view(['PUT'])
def remove_patient(request):
    patient_email = request.query_params.get('patient_email')
    if not patient_email:
        return Response(
            {"error": "Patient Username is missing"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        patient_targeted = get_object_or_404(Patient,email = patient_email)
        patient_targeted.doctor = None
        patient_targeted.save()

        return Response(
            {
                "message": "Patient Removed successfully",
            },
            status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def create_request(request):
    patient_email = request.data.get('patient_email')
    doctor_email = request.data.get('doctor_email')

    if not patient_email or not doctor_email:
        return Response(
            {"error": "There are missing parameters"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        patient_targeted = get_object_or_404(Patient,email = patient_email)
        doctor_targeted = get_object_or_404(Doctor,email = doctor_email)
        AssignmentRequest.objects.create(
            patient = patient_targeted,
            doctor = doctor_targeted,
        )
        return Response(
            {"message": "Request sent successfully."},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['GET'])
def pending_requests_list(request):
    doctor_email = request.query_params.get('doctor_email')
    doctor_intended = get_object_or_404(Doctor,email = doctor_email)

    pending_list = AssignmentRequest.objects.filter(
        doctor = doctor_intended,
        status = 'pending').values('id','patient__full_name')
    pending_list = [{'id':req['id'],'patient_name':req['patient__full_name']} for req in pending_list]

    return Response(pending_list)

@api_view(['PUT'])
def respond_request(request):
    request_id = request.data.get('request_id')
    action = request.data.get('action')

    if not request_id or action not in ['accept', 'reject']:
        return Response(
            {"error": "Both 'request_id' and 'action' (accept/reject) are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        assignment_request = get_object_or_404(AssignmentRequest, id=request_id)

        if assignment_request.status != 'pending':
            return Response(
                {"error": "This request has already been processed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action == 'accept':
            patient = assignment_request.patient
            patient.doctor = assignment_request.doctor
            patient.save()

            assignment_request.status = 'accepted'
            assignment_request.save()

            return Response(
                {"message": "Request accepted. Patient assigned to the doctor."},
                status=status.HTTP_200_OK
            )
        elif action == 'reject':
            assignment_request.status = 'rejected'
            assignment_request.save()

            return Response(
                {"message": "Request rejected."},
                status=status.HTTP_200_OK
            )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    