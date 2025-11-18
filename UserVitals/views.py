import time
import requests

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from rest_framework.decorators import api_view,permission_classes
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from Users.models import Patient,Doctor
from .models import UserVitals,UserBPM


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_data(request):
    user = request.user
    
    if isinstance(user,Doctor):
        patient_email = request.query_params.get('email')
        try:
            patient_intended = Patient.objects.get(email = patient_email)
            if patient_intended.doctor != user:
                return Response(
                {
                    'error':"User Not Assigned to this Doctor"
                },
                status.HTTP_403_FORBIDDEN
            )
            else:
                user = patient_intended

        except:
            return Response(
                {
                    'error':"User Doesn't exist"
                },
                status.HTTP_401_UNAUTHORIZED
            )
            
    credentials = user.credentials

    user_credentials = Credentials(
            token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=credentials.scopes
        )
    try:
        
        service = build('fitness', 'v1', credentials=user_credentials)

        now = int(time.time() * 1000)
        start_time = now - (24 * 60 * 60 * 1000)
        dataset_id = f"{start_time}-{now}"

        activity_data = fetch_activity_data(service, dataset_id)

        blood_pressure_data = fetch_blood_pressure_data(service, dataset_id)

        heart_rate_data = fetch_heart_rate_data(service, dataset_id)

        oxygen_saturation_data = fetch_oxygen_saturation_data(service, dataset_id)

        UserVitals.objects.update_or_create(
            patient = user,
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
            patient = user,
            heart_rate = heart_rate_data
        )
        

        return Response(
            {
            'steps': activity_data['step_count'],
            'calories': activity_data['calories'],
            'systolic_blood_pressure': blood_pressure_data['systolic'],
            'diastolic_blood_pressure': blood_pressure_data['diastolic'],
            'heart_rate' : heart_rate_data,
            'oxygen_sat' : oxygen_saturation_data
            }
        )
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
        'step_count': total_steps,
        'calories': total_calories,
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
@permission_classes([IsAuthenticated])
def Ai_pred(request):
    user = request.user
    
    if isinstance(user,Doctor):
        patient_email = request.query_params.get('email')
        try:
            patient_intended = Patient.objects.get(email = patient_email)
            if patient_intended.doctor != user:
                return Response(
                {
                    'error':"User Not Assigned to this Doctor"
                },
                status.HTTP_403_FORBIDDEN
            )
            else:
                user = patient_intended

        except:
            return Response(
                {
                    'error':"User Doesn't exist"
                },
                status.HTTP_401_UNAUTHORIZED
            )

    bpm_readings = UserBPM.objects.filter(patient = user).values('heart_rate')
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
