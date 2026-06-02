from django.test import TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string
from connect.models import UserId, DeviceToken
from proxy.views import get_auth_code

from mh.models import LandToken

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
        self.token = None


    def register_device_token(self, email=None, is_registered=False, login_status=False):
        user = UserId(email=email, is_registered=is_registered)
        user.save()
        self.token = DeviceToken(
            advertising_id=self.advertising_id,
            user=user,
            device_id=self.device_id,
            device_id_cache=self.device_id,
            current_client_session_id=self.current_client_session_id,
            session_key=user.session_key,
            login_status=login_status
        )
        self.token.save()


class ConnectViewsTests(TestCase):

    def test_anonymous_connection(self):
        """
        The first connection should receive a sig parameter from URL
        and use the data to create a new User and DeviceToken entries
        in the database.
        """

        # Perform user first connection.
        device = TestDevice()
        json_dict = {"platform": "android", "advertisingId": str(device.advertising_id)}
        json_data = json.dumps(json_dict)
        query_params = {
            "sig": f"{(base64.b64encode(json_data.encode())).decode()}.{get_random_string(16)}",
            "authenticator_login_type": device.authenticator_login_type
        }
        response = self.client.get(reverse("connect:auth", args=(device.device_id,)), query_params=query_params)
        self.assertEqual(response.status_code, 200, "Device authentication failed")

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("code", response_data)
        self.assertIn("lnglv_token", response_data)


    def test_login_user(self):
        """
        User inserts code and confirms their email.
        """

        # Perform user first connection.
        device = TestDevice(authenticator_login_type="mobile_ea_account")
        token = DeviceToken(
            advertising_id=device.advertising_id,
            user = UserId(),
            device_id=device.device_id,
            device_id_cache=device.device_id
        )
        token.user.save()
        token.save()

        # Perform user register connection: request from game login screen.
        email = "testmail@django.com"
        code = get_auth_code(email, send_email=False).code

        # User inserts wrong code.
        json_dict = {"email": email , "cred": "0"}
        json_data = json.dumps(json_dict)
        query_params = {
            "sig": f"{(base64.b64encode(json_data.encode())).decode()}.{get_random_string(16)}",
            "authenticator_login_type": device.authenticator_login_type
        }

        response = self.client.get(reverse("connect:auth", args=(device.device_id,)), query_params=query_params)
        self.assertEqual(response.status_code, 404, "Device authentication failed")

        # User inserts right code.
        json_dict.update({"email": email , "cred": code})
        json_data = json.dumps(json_dict)
        query_params = {
            "sig": f"{(base64.b64encode(json_data.encode())).decode()}.{get_random_string(16)}",
            "authenticator_login_type": device.authenticator_login_type
        }

        response = self.client.get(reverse("connect:auth", args=(device.device_id,)), query_params=query_params)
        self.assertEqual(response.status_code, 200, "Device authentication failed")
        token.refresh_from_db()

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("code", response_data)
        self.assertIn("lnglv_token", response_data)
        self.assertTrue(token.login_status, "Login have failed")


    def test_logout_user(self):
        """
        After a successful login, user requests to be logged out.
        """

        # Register and login user.
        device = TestDevice(authenticator_login_type="mobile_ea_account")
        device.register_device_token(email="testmail@django.com", is_registered=True, login_status=True)

        # User requests a logout.
        # DeviceToken gets deleted.
        response = self.client.get(
            reverse("connect:token", args=(device.device_id,)),
            query_params={"authenticator_type": "NUCLEUS", "grant_type": "remove_authenticator"}
        )
        self.assertEqual(response.status_code, 200, "Token view failed")

        response_data = json.loads(response.content)
        self.assertEqual(type(response_data), dict)
        self.assertIn("access_token", response_data)
        self.assertIn("token_type", response_data)
        self.assertIn("expires_in", response_data)
        self.assertIn("refresh_token", response_data)
        self.assertIn("refresh_token_expires_in", response_data)
        self.assertIn("id_token", response_data)
        self.assertFalse(DeviceToken.objects.filter(advertising_id=device.advertising_id).exists())


    def test_tokeninfo(self):

        # Perform user first connection.
        device = TestDevice()
        device.register_device_token()

        response = self.client.get(reverse("connect:tokeninfo", args=(device.device_id,)))
        self.assertEqual(response.status_code, 200, "Tokeninfo view failed")

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


    def test_delete_land_token_marked_for_removal(self):
        """
        If a land token is marked for removal, it should be renewed in tokeninfo.
        """

        device = TestDevice()
        device.register_device_token()
        land_token = LandToken.objects.create(user=device.token.user, remove=True)

        response = self.client.get(reverse("connect:tokeninfo", args=(device.device_id,)))
        self.assertEqual(response.status_code, 200, "Tokeninfo view failed")
        self.assertNotEqual(LandToken.objects.get(user=device.token.user).land_token, land_token.land_token, "Land token was not renewed")
