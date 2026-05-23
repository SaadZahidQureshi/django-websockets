from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ChatRoom, Message, MessageReceipt

@csrf_exempt
@login_required # Ensures only logged-in users like Alice/Bob can upload
def upload_attachment(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        room_id = request.POST.get('room_id')
        
        # Save placeholder message to history with the attachment file
        room = ChatRoom.objects.get(id=room_id)
        msg = Message.objects.create(
            room=room,
            sender=request.user,
            has_attachment=True,
            file_url=uploaded_file,
            file_type=uploaded_file.content_type
        )
        
        # Create unread receipts for others
        for member in room.members.exclude(id=request.user.id):
            MessageReceipt.objects.create(message=msg, user=member)

        # Return the saved attachment details back to the frontend client
        return JsonResponse({
            "status": "success",
            "message_id": msg.id,
            "file_url": msg.file_url.url,
            "file_type": msg.file_type
        })
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def get_chat_history(request, room_id):
    try:
        room = request.user.chat_rooms.get(id=room_id)
        # Fetch last 50 messages ordered by oldest first
        messages = room.messages.all().order_by('-timestamp')[:50][::-1] 
        
        history_data = []
        for msg in messages:
            history_data.append({
                "id": msg.id,
                "sender": msg.sender.username,
                "text": msg.text,
                "has_attachment": msg.has_attachment,
                "file_url": msg.file_url.url if msg.has_attachment else None,
                "file_type": msg.file_type,
                "timestamp": str(msg.timestamp)
            })
        return JsonResponse({"room_id": room_id, "messages": history_data})
    except ChatRoom.DoesNotExist:
        return JsonResponse({"error": "Unauthorized or Room matching query does not exist"}, status=403)
