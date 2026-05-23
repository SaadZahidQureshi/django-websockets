from django.db import models
from django.contrib.auth.models import User

class ChatRoom(models.Model):
    ROOM_TYPES = (('p2p', 'One-to-One'), ('group', 'Group'))
    
    name = models.CharField(max_length=255, blank=True, null=True) # Used for group names
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='p2p')
    members = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField(blank=True, null=True) # Text can now be blank if sending a pure image
    
    # New Attachment Fields
    has_attachment = models.BooleanField(default=False)
    file_url = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True) # e.g., 'image/jpeg', 'application/pdf'
    
    timestamp = models.DateTimeField(auto_now_add=True)

class MessageReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('message', 'user')

class UserStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
