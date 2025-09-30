from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view 
from rest_framework.response import Response
from rest_framework import status
from .models import Videos


@api_view(['GET'])
def get_videos_list(request):
    videos_list = Videos.objects.all().values('id','title','mini_')
    videos_list = list(videos_list)
    return Response(videos_list)

@api_view(['GET'])
def get_video(request):
    vid_id = request.query_params.get('id')
    video = get_object_or_404(Videos,id = vid_id)
    return Response(
        {
            'title':video.title,
            'description':video.description,
            'link':video.link
        },
                status=status.HTTP_200_OK
    )

