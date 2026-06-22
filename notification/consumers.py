import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            print(f"NotificationConsumer: REJECTED - Anonymous user. Scope keys: {self.scope.keys()}")
            await self.close()
        else:
            self.user_id = self.scope['user'].id
            self.user_role = getattr(user, 'role', '')
            print(f"NotificationConsumer: Connection accepted for user {self.user_id} with role {self.user_role}")
            self.room_group_name = f'notifications_{self.user_id}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # Add staff members to global admin alerts channel group
            self.is_staff = self.user_role in ['support', 'finance', 'admin', 'super_admin']
            if self.is_staff:
                await self.channel_layer.group_add(
                    'admin_alerts',
                    self.channel_name
                )

            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        if getattr(self, 'is_staff', False):
            await self.channel_layer.group_discard(
                'admin_alerts',
                self.channel_name
            )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['notification']
        }))

    async def admin_alert(self, event):
        await self.send(text_data=json.dumps({
            'type': 'admin_alert',
            'data': event['data']
        }))
