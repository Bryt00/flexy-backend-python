import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_login_payload_parity(api_client, test_user):
    url = reverse('login')
    data = {
        "email": test_user.email,
        "password": "password123"
    }
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == 200
    # Mandatory parity keys for mobile apps
    assert 'token' in response.data
    assert 'refresh_token' in response.data
    assert 'user' in response.data
    assert response.data['user']['email'] == test_user.email

@pytest.mark.django_db
def test_login_invalid_credentials(api_client, test_user):
    url = reverse('login')
    data = {
        "email": test_user.email,
        "password": "wrongpassword"
    }
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == 401
    assert 'error' in response.data
