from django.test import TestCase, Client
from django.urls import reverse
from django.utils.crypto import get_random_string
from connect.models import DeviceToken
from proxy.views import get_auth_code

import base64
import json
import uuid


# Create your tests here.

class TestDevice():

    def __init__(self, authenticator_login_type = "mobile_anonymous"):
        self.advertising_id = uuid.uuid4()
        self.device_id = uuid.uuid4()
        self.current_client_session_id = uuid.uuid4()
        self.authenticator_login_type = authenticator_login_type


    def auth_device(self, initial_dict = dict()):
        json_dict = {"advertisingId": str(self.advertising_id)}
        json_dict.update(initial_dict)
        json_data = json.dumps(json_dict)
        query_params = {
            "sig": f"{(base64.b64encode(json_data.encode())).decode()}.{get_random_string(16)}",
            "authenticator_login_type": self.authenticator_login_type
        }

        response = Client().get(reverse("connect:auth", args=(self.device_id,)), query_params=query_params)

        # Write the rest of the fields to the token.
        self.update_device_token(current_client_session_id=self.current_client_session_id)
        return response


    def get_device_token(self):
        return DeviceToken.objects.get(advertising_id=uuid.uuid5(uuid.NAMESPACE_OID, str(self.advertising_id)))


    def update_device_token(self, **kwargs):
        token = self.get_device_token()

        for key, value in kwargs.items():
            setattr(token, key, value)

        token.save(update_fields = kwargs.keys())


class AuthViewTests(TestCase):

    def test_anonymous_connection(self):
        """
        The first connection should receive a sig parameter from URL
        and use the data to create a new User and DeviceToken entries
        in the database.
        """

        device = TestDevice()
        response = device.auth_device()
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("code", response_data)
        self.assertIn("lnglv_token", response_data)


    def test_register_user(self):
        """
        User insert code and confirm their email.
        """

        # Perform user first connection.
        device = TestDevice()
        response = device.auth_device()
        self.assertEqual(response.status_code, 200)

        # Perform user register connection: request from game login screen.
        email = "testmail@django.com"
        code = get_auth_code(email).code
        device.authenticator_login_type = "mobile_ea_account" # Switch to registered user.

        # User inserts wrong code.
        response = device.auth_device(initial_dict={"email": email , "cred": "0"})
        self.assertEqual(response.status_code, 404)

        # User inserts right code.
        response = device.auth_device(initial_dict={"email": email , "cred": code})
        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("code", response_data)
        self.assertIn("lnglv_token", response_data)
