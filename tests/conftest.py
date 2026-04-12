import pytest
from rest_framework.test import APIClient
from core_auth.models import User
from factory.django import DjangoModelFactory
import factory

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'password123')

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    return UserFactory()
