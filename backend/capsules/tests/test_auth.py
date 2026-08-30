from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from capsules.models import Capsule

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.token = Token.objects.create(user=self.user)

    def test_register_user(self):
        response = self.client.post('/api/auth/register', {'username': 'newuser', 'password': 'newpassword'})
        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.data)

    def test_login_user(self):
        response = self.client.post('/api/auth/login', {'username': 'testuser', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    def test_invalid_login(self):
        response = self.client.post('/api/auth/login', {'username': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 401)
