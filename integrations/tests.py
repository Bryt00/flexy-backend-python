import hmac
import hashlib
import time
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import APIKey, AVAILABLE_SCOPES, DEFAULT_SCOPES
from .webhooks import WebhookService

User = get_user_model()

class APIKeyIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='dev_partner@flexyride.com',
            password='TestPassword123!',
            role='partner'
        )
        self.client.force_authenticate(user=self.user)

    def test_key_generation_and_fast_sha256_verification(self):
        raw_key, api_key = APIKey.generate_key(
            name="Logistics Engine Key",
            user=self.user,
            environment="LIVE",
            scopes=["deliveries:create", "deliveries:read"]
        )
        self.assertTrue(raw_key.startswith("fx_live_"))
        self.assertTrue(api_key.hashed_key.startswith("sha256$"))
        self.assertTrue(api_key.verify_key(raw_key))
        self.assertFalse(api_key.verify_key("fx_live_invalid_secret_value"))

    def test_sandbox_key_generation_prefix(self):
        raw_key, api_key = APIKey.generate_key(
            name="Sandbox Testing Key",
            user=self.user,
            environment="SANDBOX"
        )
        self.assertTrue(raw_key.startswith("fx_test_"))
        self.assertEqual(api_key.environment, "SANDBOX")
        self.assertTrue(api_key.verify_key(raw_key))

    def test_legacy_pbkdf2_compatibility(self):
        from django.contrib.auth.hashers import make_password
        prefix = "legacy88"
        raw_key = f"fx_{prefix}_supersecret"
        legacy_hash = make_password(raw_key)

        legacy_key = APIKey.objects.create(
            name="Legacy Partner",
            user=self.user,
            prefix=prefix,
            hashed_key=legacy_hash
        )
        self.assertTrue(legacy_key.verify_key(raw_key))
        self.assertFalse(legacy_key.verify_key("fx_legacy88_wrongsecret"))

    def test_scope_validation(self):
        raw_key, api_key = APIKey.generate_key(
            name="Scoped Key",
            user=self.user,
            scopes=["deliveries:create", "deliveries:read"]
        )
        self.assertTrue(api_key.has_scope("deliveries:create"))
        self.assertTrue(api_key.has_scope("deliveries:read"))
        self.assertFalse(api_key.has_scope("rides:create"))

        # Test wildcard scope
        api_key.scopes = ["*"]
        api_key.save()
        self.assertTrue(api_key.has_scope("rides:create"))
        self.assertTrue(api_key.has_scope("deliveries:cancel"))

    def test_ip_whitelist_validation(self):
        raw_key, api_key = APIKey.generate_key(
            name="IP Locked Key",
            user=self.user,
            allowed_ips=["192.168.1.0/24", "10.0.0.5"]
        )
        self.assertTrue(api_key.is_ip_allowed("192.168.1.42"))
        self.assertTrue(api_key.is_ip_allowed("10.0.0.5"))
        self.assertFalse(api_key.is_ip_allowed("10.0.0.6"))
        self.assertFalse(api_key.is_ip_allowed("203.0.113.1"))

    def test_key_rotation(self):
        raw_key, api_key = APIKey.generate_key(
            name="Rotating Service",
            user=self.user
        )
        old_prefix = api_key.prefix
        new_raw_key = api_key.rotate_secret()
        api_key.refresh_from_db()

        self.assertNotEqual(old_prefix, api_key.prefix)
        self.assertTrue(api_key.verify_key(new_raw_key))
        self.assertFalse(api_key.verify_key(raw_key))

    def test_webhook_signature_generation(self):
        secret = "whsec_supersecretkey12345"
        payload = b'{"event":"delivery.completed","data":{"id":"123"}}'
        ts = int(time.time())
        sig_header = WebhookService.generate_signature(payload, secret, ts)

        self.assertTrue(sig_header.startswith(f"t={ts},v1="))
        v1_sig = sig_header.split("v1=")[1]

        expected_signed = f"t={ts}.".encode('utf-8') + payload
        expected_sig = hmac.new(secret.encode('utf-8'), expected_signed, hashlib.sha256).hexdigest()
        self.assertEqual(v1_sig, expected_sig)

    def test_api_endpoints_crud_and_rotation(self):
        # 1. Create key
        create_res = self.client.post('/v1/integrations/keys/', {
            "name": "Food Partner API",
            "environment": "LIVE",
            "scopes": ["deliveries:create", "deliveries:read"],
            "webhook_url": "https://example.com/webhook"
        }, format='json')
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertIn("raw_key", create_res.data)
        key_id = create_res.data["id"]

        # 2. List keys
        list_res = self.client.get('/v1/integrations/keys/')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        keys_list = list_res.data.get('results', list_res.data) if isinstance(list_res.data, dict) else list_res.data
        self.assertGreaterEqual(len(keys_list), 1)

        # 3. Rotate key
        rotate_res = self.client.post(f'/v1/integrations/keys/{key_id}/rotate/')
        self.assertEqual(rotate_res.status_code, status.HTTP_200_OK)
        self.assertIn("raw_key", rotate_res.data)

        # 4. Delete / Revoke key
        del_res = self.client.delete(f'/v1/integrations/keys/{key_id}/')
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

        revoked_key = APIKey.objects.get(id=key_id)
        self.assertFalse(revoked_key.is_active)

    def test_authentication_with_api_key_header(self):
        raw_key, api_key = APIKey.generate_key(
            name="Direct Auth Key",
            user=self.user,
            scopes=["settings:read"]
        )

        unauthed_client = APIClient()
        # Request with X-Api-Key
        response = unauthed_client.get('/v1/settings/vehicle-categories/', HTTP_X_API_KEY=raw_key)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_204_NO_CONTENT])
