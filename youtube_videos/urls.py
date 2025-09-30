from .views import get_video,get_videos_list
from django.urls import path


urlpatterns = [
    path('video_list',get_videos_list,name = 'get_videos'),
    path('get_video',get_video,name ='get_vid')
]

