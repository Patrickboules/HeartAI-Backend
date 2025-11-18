from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from .models import Doctor,Patient,AssignmentRequest,UserCredentials
from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from google_auth_oauthlib.flow import Flow
import requests


def gen_JWT(user):
    refresh = RefreshToken.for_user(user)
    return{
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }

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

    user = request.user
    if not isinstance(user, Doctor):
        return Response(
            {"error": "Only doctors can access patient lists"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    patient_list = Patient.objects.filter(doctor = user).values('full_name','email')
    patient_list = [{'full_name':patient['full_name'],'email':patient['email']} for patient in patient_list]

    return Response(patient_list,status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def remove_patient_assignment(request):
    user = request.user

    if not isinstance(user, Doctor):
        return Response(
            {"error": "Only doctors can remove patient assignments"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    patient_email = request.query_params.get('patient_email')
    if not patient_email:
        return Response(
            {"error": "Patient Username is missing"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        patient_targeted = get_object_or_404(Patient,email = patient_email)
        if patient_targeted.doctor != user:
            return Response(
                {"error": "You can only remove your own patients"},
                status=status.HTTP_403_FORBIDDEN
            )
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
    user = request.user
    doctor_email = request.data.get('doctor_email')

    if not isinstance(user,Patient):
        return Response(
            {'error': 'Only Patients can create Doctor Requests'},
            status=status.HTTP_403_FORBIDDEN
        )
    if not doctor_email:
        return Response(
            {"error": "There are missing parameters"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        doctor_targeted = get_object_or_404(Doctor,email = doctor_email)

        existing_request = AssignmentRequest.objects.filter(
            patient=user,
            doctor=doctor_targeted,
            status='pending'
        ).exists()
        
        if existing_request:
            return Response(
                {"error": "You already have a pending request to this doctor"},
                status=status.HTTP_400_BAD_REQUEST
            )

        AssignmentRequest.objects.create(
            patient = user,
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
    user = request.user
    if not isinstance(user,Doctor):
        return Response({'error':"Only Doctors can view pending requests"},
                        status=status.HTTP_403_FORBIDDEN)

    pending_list = AssignmentRequest.objects.filter(
        doctor = user,
        status = 'pending').values('id','patient__full_name','patient__email')
    
    pending_list = [
        {
            'id':req['id'],
            'patient_name':req['patient__full_name'],
            'patient_email':req['patient__email']
         } for req in pending_list]

    return Response(pending_list,status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def respond_request(request):
    user = request.user

    if not isinstance(user,Doctor):
        return Response(
            {'error':"Only Doctors can view pending requests"},
            status=status.HTTP_403_FORBIDDEN
        )

    request_id = request.data.get('request_id')
    action = request.data.get('action')

    if not request_id or action not in ['accept', 'reject']:
        return Response(
            {"error": "Both 'request_id' and 'action' (accept/reject) are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        assignment_request = get_object_or_404(AssignmentRequest, id=request_id)

        if assignment_request.doctor != user:
            return Response(
                {'error':'User not allowed to respond to this request'},
                status.HTTP_403_FORBIDDEN
            )

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
        else:
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
@permission_classes([AllowAny])
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
            'first_name': given_name,  
            'last_name': family_name, 
            'full_name': f"{given_name} {family_name}".strip(), 
            'auth_method': 'google', 
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

        token = gen_JWT(patient_intended)
        return Response({
            'message': 'Authentication successful',
            'email': user_email,
            'google_token': credentials.token,
            'refresh_token':token['refresh'],
            'access_token':token['access']
        })

    except Exception as e:
        # Handle errors during token exchange
        return Response({'error': str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def Patient_Login(request):
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
                token = gen_JWT(patient_intended)

                return Response(
                {
                "message": "Login successful",
                "email": patient_intended.email,
                "full_name": patient_intended.full_name,
                "access_token":token['access'],
                "refresh_token":token['refresh']

                }
            , status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Please sign in with Google"}, 
                status=status.HTTP_400_BAD_REQUEST
                )
        
    
    except Patient.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status.HTTP_401_UNAUTHORIZED)
    
    
@api_view(['POST'])
@permission_classes([AllowAny])
def Doctor_Login(request):
    data = request.data
    doctor_email = data['email']
    doctor_password = data['password']

    if not doctor_email or not doctor_password:
        return Response(
            {
                'error':'Missing Credentials'
            },
            status.HTTP_400_BAD_REQUEST
        )
    try:
        doctor_intended = Doctor.objects.get(email = doctor_email)

        if check_password(doctor_password, doctor_intended.password):
            user_token = gen_JWT(doctor_intended)
            return Response(
                    {
                        'Message':'Login was Succesful',
                        'Email':doctor_intended.email,
                        'Full Name': doctor_intended.full_name,
                        'Refresh_Token': user_token['refresh'],
                        'Access_Token': user_token['access']
                    },
                    
                    status.HTTP_200_OK
                )
        else:
            return Response(
                {'Error':'Invalid Credentials'},
                status.HTTP_401_UNAUTHORIZED
                )
    except Doctor.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status.HTTP_401_UNAUTHORIZED)



    