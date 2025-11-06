from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from .models import Doctor,Patient,AssignmentRequest,UserCredentials
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response

from google_auth_oauthlib.flow import Flow
import requests


@api_view(['POST'])
@permission_classes([AllowAny])
def create_Doctor(request):
    data = request.data
    required_fields = ['first_name', 'last_name','email','specialization','description','password']
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
@permission_classes([IsAuthenticated])
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
        return Response({'error':str(e)})

@api_view(['POST'])
@permission_classes([AllowAny])
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
        if Patient.objects.filter(email = data['email']).exists():
            return Response(
            {"error": f"User Already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

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
            doctor = doctor_chosen,
            auth_method = 'manual'
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
@permission_classes([IsAuthenticated])
def get_Patients_list(request):
    doctor_email = request.query_params.get('doctor')
    doctor_request = get_object_or_404(Doctor,email = doctor_email)
    patient_list = Patient.objects.filter(doctor = doctor_request).values('full_name','email')
    patient_list = [{'full_name':patient['full_name'],'email':patient['email']} for patient in patient_list]

    return Response(patient_list)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def remove_patient_assignment(request):
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
def pending_requests_list(request):
    doctor_email = request.query_params.get('doctor_email')
    doctor_intended = get_object_or_404(Doctor,email = doctor_email)

    pending_list = AssignmentRequest.objects.filter(
        doctor = doctor_intended,
        status = 'pending').values('id','patient__full_name')
    pending_list = [{'id':req['id'],'patient_name':req['patient__full_name']} for req in pending_list]

    return Response(pending_list)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
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
    
@api_view(['GET'])
@permission_classes([AllowAny])
def get_auth(request):
    user_email = request.query_params.get('email')

    flow = Flow.from_client_secrets_file(
        settings.CLIENT_SECRETS_FILE,
        scopes=settings.GOOGLE_FIT_SCOPES,
        redirect_uri=settings.GOOGLE_FIT_REDIRECT_URI
    )
    
    extra_params = {
        'access_type': 'offline',
        'include_granted_scopes': 'true',
    }
    if user_email:
        extra_params['login_hint'] = user_email

    authorization_url, state = flow.authorization_url(
        **extra_params
    )

    request.session['oauth_state'] = state
    return Response({'authorization_url': authorization_url})

@api_view(['GET'])
def callback(request):

    state = request.GET.get('state')
    authorization_code = request.GET.get('code')

    if not state or not authorization_code:
        return Response({'error': 'Invalid state parameter'}, status=400)
    
    try:
        flow = Flow.from_client_secrets_file(
            settings.CLIENT_SECRETS_FILE,
            scopes=settings.GOOGLE_FIT_SCOPES,
            redirect_uri=settings.GOOGLE_FIT_REDIRECT_URI
        )

        flow.fetch_token(code=authorization_code)
        credentials = flow.credentials

        response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        response.raise_for_status()
        user_info = response.json()

        user_email = user_info.get('email')
        given_name = user_info.get('given_name', 'User')
        family_name = user_info.get('family_name', '')

        patient_intended,created = Patient.objects.get_or_create(
            email = user_email,
            defaults = {
            'first_name': given_name,  # Corrected key
            'last_name': family_name,  # Corrected key
            'full_name': f"{given_name} {family_name}".strip(), # Corrected key
            'auth_method': 'google',   # Corrected key
            'password': make_password(None)
            }
        )

        if not created and patient_intended.auth_method != 'google':
            patient_intended.auth_method = 'google'
            patient_intended.save()

        UserCredentials.objects.update_or_create(
            patient = patient_intended,
             defaults={
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expires_at': credentials.expiry 
        }
        )

        return Response({
            'message': 'Authentication successful',
            'email': user_email,
            'token': credentials.token,
        })

    except Exception as e:
        # Handle errors during token exchange
        return Response({'error': str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def Login(request):
    data = request.data

    user_email = data['email']
    provided_password = data['password']

    if not user_email or not provided_password:
        return Response({"error": "No Email or password provided"},status=400)
    
    try:
        patient_intended = Patient.objects.get(email=user_email)
        if patient_intended.auth_method == 'manual':
            if not check_password(provided_password,patient_intended.password):
                return Response(
                    {"error": "Invalid credentials"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                    )
            else:
                return Response({
                "message": "Login successful",
                "email": patient_intended.email,
                "full_name": patient_intended.full_name
            }
            , status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Please sign in with Google"}, 
                status=status.HTTP_400_BAD_REQUEST
                )
        
    
    except Patient.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=401)
    
    




    