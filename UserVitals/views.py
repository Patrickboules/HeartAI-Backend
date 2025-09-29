import datetime
import time
import requests

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from rest_framework.decorators import api_view 
from rest_framework.response import Response

from django.conf import settings
from django.shortcuts import get_object_or_404

from Users.models import Patient
from .models import UserCredentials,UserVitals,UserBPM


@api_view(['GET'])
def get_auth(request):
    user_email = request.query_params.get('email')
    user_password = request.query_params.get('password')


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
        patient_intended, created = Patient.objects.get_or_create(email=user_email)
        if user_password:
            patient_intended.set_password(user_password)
            patient_intended.save()

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

        patient_intended,created = Patient.objects.get_or_create(email = user_email,defaults={'first_name':'Unknown'})

        UserCredentials.objects.update_or_create(
            patient = patient_intended,
             defaults={
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expires_at': credentials.expiry    }
        )

        return Response({
            'message': 'Authentication successful',
            'email': user_email,
            'token': credentials.token,
        })

    except Exception as e:
        # Handle errors during token exchange
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def fetch_data(request):
    user_email = request.query_params.get('email')
    patient_intended = get_object_or_404(Patient,email = user_email)

    try:
        credentials = patient_intended.credentials
        user_credentials = Credentials(
            token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )

        service = build('fitness', 'v3', credentials=user_credentials)

        now = int(time.time() * 1000)
        start_time = now - (24 * 60 * 60 * 1000)
        dataset_id = f"{start_time}-{now}"

        health_data = {}

        activity_data = fetch_activity_data(service, dataset_id)

        blood_pressure_data = fetch_blood_pressure_data(service, dataset_id)

        heart_rate_data = fetch_heart_rate_data(service, dataset_id)

        oxygen_saturation_data = fetch_oxygen_saturation_data(service, dataset_id)

        UserVitals.objects.update_or_create(
            patient = patient_intended,
            defaults={
            'steps': activity_data['step_count'],
            'calories': activity_data['calories'],
            'systolic_blood_pressure': blood_pressure_data['systolic'],
            'diastolic_blood_pressure': blood_pressure_data['diastolic'],
            'heart_rate' : heart_rate_data,
            'oxygen_sat' : oxygen_saturation_data
            }
        )

        UserBPM.objects.create(
            patient = patient_intended,
            heart_rate = heart_rate_data
        )
        

        return Response(health_data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    
def fetch_activity_data(service, dataset_id):
    step_count_data = service.users().dataSources().datasets().get(
        userId='me',
        dataSourceId='derived:com.google.step_count.delta:com.google.android.gms:estimated_steps',
        datasetId=dataset_id
    ).execute()

    calories_data = service.users().dataSources().datasets().get(
        userId='me',
        dataSourceId='derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended',
        datasetId=dataset_id
    ).execute()

    total_steps = 0
    for point in step_count_data.get('point', []):
        value = point.get('value', [{}])[0]
        total_steps += value.get('intVal', 0)

    total_calories = 0.0
    for point in calories_data.get('point', []):
        value = point.get('value', [{}])[0]
        total_calories += value.get('fpVal', 0.0)

    return {
        'step_count': step_count_data,
        'calories': calories_data,
    }

def fetch_blood_pressure_data(service, dataset_id):
    blood_pressure_data = service.users().dataSources().datasets().get(
        userId='me',
        dataSourceId='derived:com.google.blood_pressure:com.google.android.gms:merged',
        datasetId=dataset_id
    ).execute()

    points = blood_pressure_data.get('point', [])
    if not points:
        return {'systolic': None, 'diastolic': None}

    point = points[-1]
    values = point.get('value', [])

    systolic = values[0].get('fpVal') 
    diastolic = values[1].get('fpVal') 
    return {
        'systolic': systolic,
        'diastolic': diastolic
    }

def fetch_heart_rate_data(service, dataset_id):
    heart_rate_data = service.users().dataSources().datasets().get(
        userId='me',
        dataSourceId='derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm',
        datasetId=dataset_id
    ).execute()

    points = heart_rate_data.get('point', [])
    if not points:
        return None 
    
    total_bpm = 0.0
    count = 0
    for point in points:
        value = point.get('value', [{}])[0]
        bpm = value.get('fpVal')
        if bpm is not None:
            total_bpm += bpm
            count += 1

def fetch_oxygen_saturation_data(service, dataset_id):
    oxygen_saturation_data = service.users().dataSources().datasets().get(
        userId='me',
        dataSourceId='derived:com.google.oxygen_saturation:com.google.android.gms:merged',
        datasetId=dataset_id
    ).execute()

    points = oxygen_saturation_data.get('point', [])
    if not points:
        return None 

    latest_point = points[-1]
    values = latest_point.get('value', [])

    oxygen_saturation = None
    if values:
        oxygen_saturation = values[0].get('fpVal')

    return oxygen_saturation

@api_view(['GET'])
def Ai_pred(request):
    user_email = request.query_params.get('email')
    patient_intended = get_object_or_404(Patient,email = user_email)

    bpm_readings = UserBPM.objects.filter(patient = patient_intended).values('heart_rate')
    bpm_readings = list(bpm_readings)

    api_url = "https://sharafo-InnovatorsHeartAI.hf.space/predict"

    data ={
        'heartbeat':[bpm_readings]
    }

    response = requests.post(
            api_url, 
            json=data, 
            timeout=10
        )
    prediction = response.json()

    return Response(prediction)
