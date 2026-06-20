import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from courier.views import DeliveryViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(role='passenger').first()
if not user:
    user = User.objects.create(email='test_passenger@test.com', role='passenger')

factory = APIRequestFactory()
request = factory.get('/v1/deliveries/estimate/', {
    'pickup_lat': '5.6037',
    'pickup_lng': '-0.1870',
    'dropoff_lat': '5.6337',
    'dropoff_lng': '-0.2170',
    'item_category': 'PACKAGE',
    'weight': '2.0'
})

view = DeliveryViewSet.as_view({'get': 'estimate'})
force_authenticate(request, user=user)
response = view(request)
print("STATUS:", response.status_code)
print("DATA:", response.data)
