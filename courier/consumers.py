import json
from django.core.serializers.json import DjangoJSONEncoder
from channels.generic.websocket import AsyncWebsocketConsumer

class CourierConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.delivery_id = self.scope['url_route']['kwargs'].get('delivery_id')
        if self.delivery_id:
            # Group for a specific delivery tracking
            self.room_group_name = f'delivery_{self.delivery_id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Send initial state
            delivery_data = await self.get_serialized_delivery(self.delivery_id)
            if delivery_data:
                await self.send(text_data=json.dumps({
                    'type': 'status_update',
                    'data': delivery_data
                }, cls=DjangoJSONEncoder))
        else:
            # Discovery stream for available deliveries
            self.room_group_name = 'delivery_discovery'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

    from channels.db import database_sync_to_async

    @database_sync_to_async
    def get_serialized_delivery(self, delivery_id):
        try:
            from .models import Delivery
            from .serializers import DeliverySerializer
            delivery = Delivery.objects.select_related('passenger', 'driver').prefetch_related('proofs').get(id=delivery_id)
            return DeliverySerializer(delivery).data
        except Delivery.DoesNotExist:
            return None

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Handle incoming messages from the driver (location updates).
        """
        data = json.loads(text_data)
        message_type = data.get('type')
        payload = data.get('data')

        if message_type == 'location_update':
            # Broadcast location to everyone in the delivery group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'delivery_broadcast',
                    'message_type': 'location_update',
                    'data': payload,
                    'sender_id': self.user.id
                }
            )

    async def delivery_broadcast(self, event):
        """
        Called when someone sends a message to the group.
        """
        # Prevent echo
        if event.get('sender_id') == self.user.id:
            return

        await self.send(text_data=json.dumps({
            'type': event['message_type'],
            'data': event['data']
        }, cls=DjangoJSONEncoder))
