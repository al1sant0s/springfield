from django.test import TestCase, Client
from django.urls import reverse
from django.utils.crypto import get_random_string
from connect.models import DeviceToken
from mh.models import LandToken
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


    def get_device_token(self):
        return DeviceToken.objects.get(advertising_id=uuid.uuid5(uuid.NAMESPACE_OID, str(self.advertising_id)))


    def update_device_token(self, **kwargs):
        token = self.get_device_token()

        for key, value in kwargs.items():
            setattr(token, key, value)

        token.save(update_fields = kwargs.keys())


    def authenticate_device(self, initial_dict = dict()):
        json_dict = {"advertisingId": str(self.advertising_id)}
        json_dict.update(initial_dict)
        json_data = json.dumps(json_dict)
        query_params = {
            "sig": f"{(base64.b64encode(json_data.encode())).decode()}.{get_random_string(16)}",
            "authenticator_login_type": self.authenticator_login_type
        }
        return Client().get(reverse("connect:auth", args=(self.device_id,)), query_params=query_params)


    def authenticate_token(self):
        self.client = Client()
        self.client.get(reverse("connect:tokeninfo", args=(self.get_device_token().device_id,)))
        self.client.post(
            reverse("mh:userstats"),
            headers={
                "currentClientSessionId": str(self.current_client_session_id)
            },
            query_params={
                "device_id": str(self.device_id)
            }
        )


class ConnectViewsTests(TestCase):

    def test_anonymous_connection(self):
        """
        The first connection should receive a sig parameter from URL
        and use the data to create a new User and DeviceToken entries
        in the database.
        """

        device = TestDevice()
        response = device.authenticate_device()
        self.assertEqual(response.status_code, 200, "Device authentication failed")

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("code", response_data)
        self.assertIn("lnglv_token", response_data)


    def test_login_logout_user(self):
        """
        User insert code and confirm their email.
        After a successful login, user requests to be logged out.
        """

        # Perform user first connection.
        device = TestDevice()
        response = device.authenticate_device()
        token = device.get_device_token()
        self.assertEqual(response.status_code, 200, "Device authentication failed")

        # Perform user register connection: request from game login screen.
        email = "testmail@django.com"

        code = get_auth_code(email, use_tsto_api=False).code
        device.authenticator_login_type = "mobile_ea_account" # Switch to registered user.

        # User inserts wrong code.
        response = device.authenticate_device(initial_dict={"email": email , "cred": "0"})
        self.assertEqual(response.status_code, 404, "It should return 404 for wrong credential")

        # User inserts right code.
        response = device.authenticate_device(initial_dict={"email": email , "cred": code})
        self.assertEqual(response.status_code, 200, "It should return 200 for right credential")
        token.refresh_from_db()

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("code", response_data)
        self.assertIn("lnglv_token", response_data)
        self.assertTrue(token.login_status, "Login have failed")

        # User requests a logout.
        response = self.client.get(
            reverse("connect:token", args=(device.device_id,)),
            query_params={"authenticator_type": "NUCLEUS", "grant_type": "remove_authenticator"}
        )
        self.assertEqual(response.status_code, 200, "Token view failed")
        token.refresh_from_db()

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("access_token", response_data)
        self.assertIn("token_type", response_data)
        self.assertIn("expires_in", response_data)
        self.assertIn("refresh_token", response_data)
        self.assertIn("refresh_token_expires_in", response_data)
        self.assertIn("id_token", response_data)
        self.assertFalse(token.login_status, "Logout have failed")


    def test_tokeninfo(self):

        # Perform user first connection.
        device = TestDevice()
        response = device.authenticate_device()
        token = device.get_device_token()
        self.assertEqual(response.status_code, 200, "Device authentication failed")

        response = self.client.get(reverse("connect:tokeninfo", args=(device.device_id,)))
        self.assertEqual(response.status_code, 200, "Tokeninfo view failed")

        # Make sure a land token was made for the user.
        self.assertTrue(LandToken.objects.filter(user=token.user).exists(), "LandToken should exist for the user")

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("client_id", response_data)
        self.assertIn("scope", response_data)
        self.assertIn("expires_in", response_data)
        self.assertIn("pid_id", response_data)
        self.assertIn("pid_type", response_data)
        self.assertIn("user_id", response_data)
        self.assertIn("persona_id", response_data)
        self.assertIn("authenticators", response_data)
        self.assertIn("is_underage", response_data)
        self.assertIn("stopProcess", response_data)
        self.assertIn("telemetry_id", response_data)
