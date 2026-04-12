import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer

class RideConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs'].get('ride_id')
        if self.ride_id:
            self.room_group_name = f'ride_{self.ride_id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        else:
            self.room_group_name = 'discovery_rides'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        event_type = text_data_json.get('type')
        data = text_data_json.get('data')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ride_update',
                'event_type': event_type,
                'data': data
            }
        )

    async def ride_update(self, event):
        await self.send(text_data=json.dumps({
            'type': event['event_type'],
            'data': event['data']
        }))

class GlobalRideConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'global_rides'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def broadcast_location(self, event):
        await self.send(text_data=json.dumps(event['data']))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'chat_{self.ride_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        sender_id = self.scope['user'].id if self.scope['user'].is_authenticated else None

        # Logic to save message to DB would go here (ideally via sync_to_async)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': str(sender_id) if sender_id else None,
                'timestamp': str(timezone.now())
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
