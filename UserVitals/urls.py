from django.urls import path
from .views import get_auth, callback, fetch_data,Ai_pred

urlpatterns = [
    path('health_data/', fetch_data, name='health_data'),
    path('AI/',Ai_pred,name = 'AI_prediction')
]