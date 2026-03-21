from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from connect.models import DeviceToken, UserId
from connect.tests import TestDevice
from mh.models import LandToken
from protofiles import *

import xml.etree.ElementTree as ET
import uuid
import gzip
import tempfile

# Create your tests here.

class GetCurrentTimeViewTests(TestCase):

    def test_epoch_time(self):
        """
        View should return a basic xml response with a similar format.

        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Time>
            <epochMilliseconds>
                1728425827965
            </epochMilliseconds>
        </Time>

        """

        response = self.client.get(reverse("mh:time"))
        self.assertEqual(response.status_code, 200)

        root = ET.fromstring(response.content)
        self.assertEqual(root.tag, "Time")
        self.assertEqual(root[0].tag, "epochMilliseconds")
        self.assertEqual(root[0].text.isnumeric(), True)


class UserStatsViewTests(TestCase):

    def test_view(self):

        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()

        token = device.get_device_token()

        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("mh:userstats"),
            headers={
                "currentClientSessionId": str(device.current_client_session_id)
            },
            query_params={
                "device_id": str(device.device_id)
            }
        )
        self.assertEqual(response.status_code, 409)


class FriendDataViewTests(TestCase):

    def test_debug_mayhem_id(self):

        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()

        token = device.get_device_token()

        response = self.client.get(
            reverse("mh:friendData"),
            headers={"currentClientSessionId": str(token.current_client_session_id)},
            query_params={"debug_mayhem_id": str(token.user.mayhem_id.int)}
        )
        self.assertEqual(response.status_code, 200)

        friend_data_response = GetFriendData_pb2.GetFriendDataResponse()
        friend_data_response.ParseFromString(response.content)


    def test_origin(self):

        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()

        token = device.get_device_token()

        response = self.client.get(reverse("mh:friendDataOrigin"), headers={"currentClientSessionId": str(token.current_client_session_id)})
        self.assertEqual(response.status_code, 200)

        friend_data_response = GetFriendData_pb2.GetFriendDataResponse()
        friend_data_response.ParseFromString(response.content)


class ProtolandViewTests(TestCase):

    def test_load_save_town(self):
        """
        Make a new user and request their town.
        Parse the response to be sure it is valid.
        Submit the town back to be saved and request it again.
        Match both towns.
        Finally, attempt to save over another user's town and fail.
        """

        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()

        token = device.get_device_token()
        land_token = LandToken.objects.filter(user=token.user).first()

        # Set towns dir to temp directory.
        cache.set("towns_dir", tempfile.TemporaryDirectory().name)

        # Get town.
        response = self.client.get(reverse("mh:protoland", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)

        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(response.content)
        self.assertEqual(land_data.friendData.dataVersion, 72)
        self.assertIn("hasLemonTree", land_data.friendData)
        self.assertIn("language", land_data.friendData)
        self.assertIn("level", land_data.friendData)
        self.assertIn("name", land_data.friendData)
        self.assertIn("rating", land_data.friendData)

        # Change some data and post town.
        land_data.friendData.dataVersion = 123
        compressed_body = gzip.compress(land_data.SerializeToString())
        response = self.client.post(
            reverse("mh:protoland", args=(token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={
                "Land-Update-Token": str(land_token.land_token),
                "currentClientSessionId": str(device.current_client_session_id),
                "Content-Encoding": "gzip"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ET.tostring(ET.Element("WholeLandUpdateResponse")))


        # Get town again.
        response = self.client.get(reverse("mh:protoland", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, land_data.SerializeToString())


        # Attempt to post to other user's town by giving their mayhem id.
        new_device = TestDevice()
        new_device.authenticate_device()
        new_token = new_device.get_device_token()

        compressed_body = gzip.compress(land_data.SerializeToString())
        response = self.client.post(
            reverse("mh:protoland", args=(new_token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={
                "Land-Update-Token": str(land_token.land_token),
                "currentClientSessionId": str(device.current_client_session_id),
                "Content-Encoding": "gzip"
            }
        )
        self.assertEqual(response.status_code, 400)


    def test_load_premium_currency(self):

        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()

        token = device.get_device_token()

        # Get donuts balance.
        response = self.client.get(
            reverse("mh:protocurrency", args=(token.user.mayhem_id.int,)),
            headers={"currentClientSessionId": str(device.current_client_session_id)}
        )
        self.assertEqual(response.status_code, 200)

        protocurrency_response = PurchaseData_pb2.CurrencyData()
        protocurrency_response.ParseFromString(response.content)
        self.assertEqual(token.user.donuts_balance, protocurrency_response.vcBalance )


        # Update donuts and check donuts balance again.
        token.user.donuts_balance = 123
        token.user.save()
        response = self.client.get(
            reverse("mh:protocurrency", args=(token.user.mayhem_id.int,)),
            headers={"currentClientSessionId": str(device.current_client_session_id)}
        )
        self.assertEqual(response.status_code, 200)

        protocurrency_response = PurchaseData_pb2.CurrencyData()
        protocurrency_response.ParseFromString(response.content)
        self.assertEqual(token.user.donuts_balance, protocurrency_response.vcBalance )


    def test_update_premium_currency(self):

        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()

        token = device.get_device_token()
        token.user.donuts_balance = 500
        token.user.save()

        land_token = LandToken.objects.filter(user=token.user).first()

        # Make some events up.
        currency_deltas = [
            LandData_pb2.ExtraLandMessage.CurrencyDelta(id=1, reason="Purchased donuts.", amount=50),
            LandData_pb2.ExtraLandMessage.CurrencyDelta(id=2, reason="Purchased character.", amount=-25),
            LandData_pb2.ExtraLandMessage.CurrencyDelta(id=3, reason="Level up!", amount=2)
        ]

        extraland_request = LandData_pb2.ExtraLandMessage(currencyDelta=currency_deltas)
        extraland_response = LandData_pb2.ExtraLandResponse(processedCurrencyDelta=currency_deltas)

        # Post the previous events.
        compressed_body = gzip.compress(extraland_request.SerializeToString())
        response = self.client.post(
            reverse("mh:extraLandUpdate", args=(token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={
                "Land-Update-Token": str(land_token.land_token),
                "currentClientSessionId": str(device.current_client_session_id),
                "Content-Encoding": "gzip"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, extraland_response.SerializeToString())
        token.user.refresh_from_db()


        # Request currency info and compare directly with the database.
        response = self.client.get(
            reverse("mh:protocurrency", args=(token.user.mayhem_id.int,)),
            headers={"currentClientSessionId": str(device.current_client_session_id)}
        )
        self.assertEqual(response.status_code, 200)

        protocurrency_response = PurchaseData_pb2.CurrencyData()
        protocurrency_response.ParseFromString(response.content)
        self.assertEqual(token.user.donuts_balance, protocurrency_response.vcBalance)


        # Test if user can override currency from another user.
        new_device = TestDevice()
        new_device.authenticate_device()
        new_device.authenticate_token()

        new_token = new_device.get_device_token()

        compressed_body = gzip.compress(extraland_request.SerializeToString())
        response = self.client.post(
            reverse("mh:extraLandUpdate", args=(new_token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={
                "Land-Update-Token": str(land_token.land_token),
                "currentClientSessionId": str(device.current_client_session_id),
                "Content-Encoding": "gzip"
            }
        )
        self.assertEqual(response.status_code, 400)
