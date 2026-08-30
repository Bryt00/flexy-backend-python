from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiResponse, inline_serializer
from rest_framework import serializers as drf_serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at')


@extend_schema_view(
    list=extend_schema(tags=['Notifications'], summary='List all notifications', description='Returns all notifications for the authenticated user.'),
    retrieve=extend_schema(tags=['Notifications'], summary='Get notification details', description='Returns details of a specific notification by ID.'),
    create=extend_schema(tags=['Notifications'], summary='Create a notification', description='Creates a new notification record.'),
    update=extend_schema(tags=['Notifications'], summary='Update a notification', description='Updates a notification record.'),
    partial_update=extend_schema(tags=['Notifications'], summary='Partially update a notification', description='Partially updates a notification record.'),
    destroy=extend_schema(tags=['Notifications'], summary='Delete a notification', description='Deletes a single notification by ID.'),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """In-app notification inbox management."""
    queryset = Notification.objects.all() # Added for drf-spectacular metadata
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @extend_schema(
        tags=['Notifications'],
        summary='Get my notifications inbox',
        description=(
            'Returns the user\'s notification inbox with unread count.\n\n'
            'Supports pagination parameters `limit` and `offset`.'
        ),
        parameters=[
            OpenApiParameter(name='limit', type=int, location='query', required=False, description='Max notifications to return.'),
            OpenApiParameter(name='offset', type=int, location='query', required=False, description='Pagination offset.'),
        ],
        responses={
            200: inline_serializer(
                name='NotificationInboxResponse',
                fields={
                    'notifications': NotificationSerializer(many=True),
                    'unread_count': drf_serializers.IntegerField(help_text='Count of unread notifications.'),
                }
            ),
        },
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        queryset = self.get_queryset()
        
        limit = request.query_params.get('limit')
        offset = request.query_params.get('offset')
        
        try:
            if offset is not None:
                offset = int(offset)
                queryset = queryset[offset:]
            if limit is not None:
                limit = int(limit)
                queryset = queryset[:limit]
        except ValueError:
            pass

        serializer = self.get_serializer(queryset, many=True)
        unread_count = self.get_queryset().filter(is_read=False).count()
        
        return Response({
            "notifications": serializer.data,
            "unread_count": unread_count
        })

    @extend_schema(
        tags=['Notifications'],
        summary='Mark all notifications as read',
        description='Sets `is_read=True` on all unread notifications for the authenticated user.',
        request=None,
        responses={
            200: inline_serializer(
                name='ReadAllNotificationsResponse',
                fields={'status': drf_serializers.CharField(default='success')},
            ),
        },
    )
    @action(detail=False, methods=['post'])
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"status": "success"})

    @extend_schema(
        tags=['Notifications'],
        summary='Delete all notifications',
        description='Clears the user\'s notification inbox completely.',
        request=None,
        responses={204: OpenApiResponse(description='All notifications deleted.')},
    )
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        self.get_queryset().delete()
        return Response({"status": "success"}, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=['Notifications'],
        summary='Mark single notification as read',
        description='Marks a specific notification as read by setting `is_read=True`.',
        request=None,
        responses={200: NotificationSerializer},
    )
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(self.get_serializer(notification).data)

class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = __import__('notification').models.FCMDevice
        fields = ['registration_id', 'device_id', 'app_type']

class RegisterFCMTokenView(APIView):
    """Registers Firebase Cloud Messaging (FCM) tokens for push notifications."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Notifications'],
        summary='Register FCM device token',
        description=(
            'Registers or updates a Firebase Cloud Messaging push token for the user\'s device.\n\n'
            '**App types:** `PASSENGER` (default), `DRIVER`\n\n'
            'Triggers an automatic welcome push notification if this is a brand new user\'s first device.'
        ),
        request=FCMDeviceSerializer,
        responses={
            200: inline_serializer(
                name='RegisterFCMTokenResponse',
                fields={
                    'status': drf_serializers.CharField(default='success'),
                    'message': drf_serializers.CharField(),
                }
            ),
            400: OpenApiResponse(description='Missing registration_id or device_id.'),
        },
    )
    def post(self, request):
        registration_id = request.data.get('registration_id')
        device_id = request.data.get('device_id')
        app_type = request.data.get('app_type', 'PASSENGER')
        
        if not registration_id or not device_id:
            return Response({"error": "registration_id and device_id are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        device, created = __import__('notification').models.FCMDevice.objects.update_or_create(
            device_id=device_id,
            defaults={'user': request.user, 'registration_id': registration_id, 'app_type': app_type}
        )
        
        # Send a welcome push if this is their first registered device 
        # (we use the Notification model to check if we've already welcomed them)
        if created:
            from django.utils import timezone
            from datetime import timedelta
            from .models import Notification
            from .utils import send_notification
            from core_settings.models import SiteSetting
            
            # Check if this is the only registered device for this user
            FCMDevice = __import__('notification').models.FCMDevice
            device_count = FCMDevice.objects.filter(user=request.user).count()
            
            # Welcome push is only sent for brand new users (account created in the last 24 hours)
            is_new_user = (timezone.now() - request.user.created_at) < timedelta(hours=24)
            
            # Check if they have already received a welcome message
            has_welcomed = Notification.objects.filter(user=request.user, title__icontains="Welcome").exists()
            if device_count == 1 and is_new_user and not has_welcomed:
                # Safely extract the first name from the user's profile
                first_name = "there"
                try:
                    if hasattr(request.user, 'profile') and request.user.profile.full_name:
                        first_name = request.user.profile.full_name.split()[0]
                except Exception:
                    pass
                
                title_setting = SiteSetting.objects.filter(key="WELCOME_PUSH_TITLE").first()
                body_setting = SiteSetting.objects.filter(key="WELCOME_PUSH_BODY").first()
                
                title = title_setting.value if title_setting else "🎉 Welcome to FlexyRide!"
                body_template = body_setting.value if body_setting else "Hi {first_name}! We're thrilled to have you on board. Enjoy your rides!"
                body = body_template.replace("{first_name}", first_name)
                
                send_notification(request.user, title, body, type='PUSH')
        
        return Response({"status": "success", "message": f"FCM token registered for {app_type}"})
