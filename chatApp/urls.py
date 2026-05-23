from django.urls import path
from . import views  

urlpatterns = [
    path('upload_attachment/', views.upload_attachment, name='upload_attachment'),
    path('history/<int:room_id>/', views.get_chat_history, name='get_chat_history'),
]
