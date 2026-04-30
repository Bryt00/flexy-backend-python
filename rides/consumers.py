import json
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from channels.generic.websocket import AsyncWebsocketConsumer


class RideConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            # Reject without accepting (HTTP 403 at handshake level)
            await self.close()
            return

        self.ride_id = self.scope['url_route']['kwargs'].get('ride_id')
        if self.ride_id:
            self.room_group_name = f'ride_{self.ride_id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            # Discovery stream: accept first, then close if not eligible
            # (Channels requires accept() before close() with a custom code)
            is_eligible = await self.check_eligible_driver()
            if not is_eligible:
                # Accept then immediately close with 4003
                await self.accept()
                await self.close(code=4003)
                return

            self.room_group_name = 'discovery_rides'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            
            # Join individual discovery group for targeted radius dispatch
            self.individual_group_name = f'driver_discovery_{self.user.id}'
            await self.channel_layer.group_add(self.individual_group_name, self.channel_name)
            
            await self.accept()

    async def check_eligible_driver(self):
        """
        Allow any verified driver into the discovery stream.
        Subscription enforcement is handled by the Online/Offline toggle on the app side.
        """
        from asgiref.sync import sync_to_async
        from profiles.models import DriverVerification

        @sync_to_async
        def get_eligibility(user):
            try:
                verification = DriverVerification.objects.get(driver__user=user)
                return verification.is_verified
            except DriverVerification.DoesNotExist:
                return False
            except Exception as e:
                print(f"RideConsumer: eligibility check error: {e}")
                return False

        return await get_eligibility(self.user)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if hasattr(self, 'individual_group_name'):
            await self.channel_layer.group_discard(self.individual_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        event_type = text_data_json.get('type')
        data = text_data_json.get('data')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ride_update',
                'event_type': event_type,
                'data': data,
                'sender_id': self.user.id
            }
        )

    async def ride_update(self, event):
        # Prevent echo: don't send back to the user who originated the message
        if event.get('sender_id') == self.user.id:
            return

        await self.send(text_data=json.dumps({
            'type': event['event_type'],
            'data': event['data']
        }, cls=DjangoJSONEncoder))

class GlobalRideConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'global_rides'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def broadcast_location(self, event):
        await self.send(text_data=json.dumps(event['data'], cls=DjangoJSONEncoder))

from asgiref.sync import sync_to_async
from .models import ChatMessage, Ride
from .crypto_utils import ChatEncryption
from .serializers import ChatMessageSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'chat_{self.ride_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        # Push any pending messages for this ride that weren't sent by this user
        # Once pushed, they should ideally be deleted, but we wait for 'chat_ack' 
        # to ensure they actually reached the device.
        await self.send_pending_messages()

    @sync_to_async
    def get_pending_messages(self):
        return list(ChatMessage.objects.filter(ride_id=self.ride_id).exclude(sender=self.user).select_related('ride', 'sender'))

    async def send_pending_messages(self):
        pending = await self.get_pending_messages()
        for msg in pending:
            # Decrypt the temporary storage content for transmission
            msg.content = ChatEncryption.decrypt(msg.content)
            serializer = ChatMessageSerializer(msg)
            await self.send(text_data=json.dumps({
                'type': 'chat',
                'data': serializer.data
            }, cls=DjangoJSONEncoder))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            event_type = data.get('type')
            
            if event_type == 'chat':
                payload = data.get('data')
                if payload:
                    await self.handle_chat_message(payload)
        except Exception as e:
            print(f"Error in chat receive: {e}")

    async def handle_chat_message(self, data):
        content = data.get('content')
        if not content:
            return

        # 1. Encrypt for temporary storage
        encrypted_content = ChatEncryption.encrypt(content)
        
        # 2. Save to DB (persists until ride completion)
        message = await self.save_message(encrypted_content)
        
        # 3. Broadcast to room
        message_data = await self.prepare_broadcast_data(message, content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_broadcast',
                'data': message_data
            }
        )

    @sync_to_async
    def save_message(self, encrypted_content):
        return ChatMessage.objects.create(
            ride_id=self.ride_id,
            sender=self.user,
            content=encrypted_content
        )
    
    @sync_to_async
    def prepare_broadcast_data(self, message, raw_content):
        # Temporarily restore raw content for the serializer
        message.content = raw_content
        return ChatMessageSerializer(message).data

    async def chat_broadcast(self, event):
        # This is called for each client in the room
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'data': event['data']
        }, cls=DjangoJSONEncoder))

class AdminHeatmapConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        
        self.room_group_name = 'admin_heatmap'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def heatmap_update(self, event):
        # Transmits the list of dictionaries directly
        await self.send(text_data=json.dumps({
            'type': 'heatmap_refresh',
            'data': event['data']
        }, cls=DjangoJSONEncoder))
