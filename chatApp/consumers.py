import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message, MessageReceipt, UserStatus

class ChatConsumer(AsyncJsonWebsocketConsumer):
    
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        # 1. Join a global presence group to manage online/offline status
        self.presence_group = "presence_global"
        await self.channel_layer.group_add(self.presence_group, self.channel_name)
        await self.update_user_status(True)
        await self.broadcast_presence_change(True)

        # 2. Join rooms the user belongs to dynamically
        self.user_rooms = await self.get_user_rooms()
        for room_id in self.user_rooms:
            await self.channel_layer.group_add(f"chat_{room_id}", self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Remove from groups and mark offline
        await self.update_user_status(False)
        await self.broadcast_presence_change(False)
        
        await self.channel_layer.group_discard(self.presence_group, self.channel_name)
        for room_id in self.user_rooms:
            await self.channel_layer.group_discard(f"chat_{room_id}", self.channel_name)

    async def receive_json(self, content):
        """Routes incoming messages from the frontend client based on 'action'"""
        action = content.get("action")
        room_id = content.get("room_id")

        if action == "send_message":
            msg_text = content.get("message")
            msg_data = await self.save_message(room_id, msg_text)
            
            # Broadcast message to everyone in the room channel
            await self.channel_layer.group_send(
                f"chat_{room_id}",
                {"type": "chat_message", "data": msg_data}
            )

        elif action == "read_receipt":
            message_id = content.get("message_id")
            receipt_data = await self.mark_as_read(message_id)
            
            # Broadcast read notification to the room
            await self.channel_layer.group_send(
                f"chat_{room_id}",
                {"type": "read_notification", "data": receipt_data}
            )

        elif action == "typing_status":
            is_typing = content.get("is_typing")
            await self.channel_layer.group_send(
                f"chat_{room_id}",
                {
                    "type": "typing_notification",
                    "data": {"user": self.user.username, "is_typing": is_typing, "room_id": room_id}
                }
            )

    # --- Channel Event Handlers (Broadcasting to Client Frontend) ---

    async def chat_message(self, event):
        await self.send_json({"action": "new_message", "data": event["data"]})

    async def read_notification(self, event):
        await self.send_json({"action": "message_read", "data": event["data"]})

    async def typing_notification(self, event):
        await self.send_json({"action": "user_typing", "data": event["data"]})

    async def presence_notification(self, event):
        await self.send_json({"action": "presence_change", "data": event["data"]})

    # --- Database Helpers (Async Wrapper Queries) ---

    @database_sync_to_async
    def get_user_rooms(self):
        return list(self.user.chat_rooms.values_list('id', flat=True))

    @database_sync_to_async
    def update_user_status(self, status):
        UserStatus.objects.update_or_create(user=self.user, defaults={'is_online': status})

    @database_sync_to_async
    def save_message(self, room_id, text):
        room = ChatRoom.objects.get(id=room_id)
        msg = Message.objects.create(room=room, sender=self.user, text=text)
        
        # Auto-create unread receipts for all other members in the room
        for member in room.members.exclude(id=self.user.id):
            MessageReceipt.objects.create(message=msg, user=member)
            
        return {"id": msg.id, "room_id": room_id, "sender": self.user.username, "text": msg.text, "timestamp": str(msg.timestamp)}

    @database_sync_to_async
    def mark_as_read(self, message_id):
        receipt = MessageReceipt.objects.get(message_id=message_id, user=self.user)
        receipt.is_read = True
        receipt.read_at = timezone.now()
        receipt.save()
        return {"message_id": message_id, "user": self.user.username, "read_at": str(receipt.read_at)}

    async def broadcast_presence_change(self, is_online):
        await self.channel_layer.group_send(
            self.presence_group,
            {
                "type": "presence_notification",
                "data": {"user": self.user.username, "is_online": is_online, "last_seen": str(timezone.now())}
            }
        )
