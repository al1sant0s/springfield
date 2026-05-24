from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from connect.tests import TestDevice
from mh.models import LandToken
from mh.views import load_town
from protofiles import *

import xml.etree.ElementTree as ET
import uuid
import gzip

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

    def test_land_token_authorization(self):

        device = TestDevice()
        device.register_device_token()
        land_token = LandToken.objects.create(user=device.token.user, retrieved=True)

        response = self.client.post(
            reverse("mh:userstats"),
            headers={
                "currentClientSessionId": str(device.current_client_session_id)
            },
            query_params={
                "device_id": str(device.device_id)
            }
        )

        land_token.refresh_from_db()
        self.assertTrue(land_token.authorized)
        self.assertEqual(response.status_code, 409)


    def test_missing_currenct_client_session_id(self):
        device = TestDevice()
        response = self.client.post(
            reverse("mh:userstats"),
            query_params={
                "device_id": str(device.device_id)
            }
        )
        self.assertEqual(response.status_code, 400)


    def test_missing_device_id(self):
        device = TestDevice()
        response = self.client.post(
            reverse("mh:userstats"),
            headers={
                "currentClientSessionId": str(device.current_client_session_id)
            }
        )
        self.assertEqual(response.status_code, 400)


    def test_save_cached_town(self):
        """
        After sending a POST to protoland with an unauthorized land token,
        the cached town should be saved in mh/userstats.
        """
        device = TestDevice()
        device.register_device_token()
        land_token = LandToken.objects.create(user=device.token.user, retrieved=True, authorized=False)

        land_data = LandData_pb2.LandMessage()
        land_data.friendData.dataVersion = 123
        cache.set(str(land_token.land_token), land_data.SerializeToString(), timeout=300)

        # Call mh/userstats/ to authenticate and finally save the cached town.
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
        device.token.user.refresh_from_db()

        load_land_data = LandData_pb2.LandMessage()
        load_land_data.ParseFromString(load_town(device.token.user))
        self.assertEqual(load_land_data.friendData.dataVersion, land_data.friendData.dataVersion)

        # Remove town.
        device.token.user.town.delete()


    def test_delete_land_token_marked_for_removal(self):
        """
        If a land token is marked for removal, it should be deauthorized in userstats.
        """
        device = TestDevice()
        device.register_device_token()
        LandToken.objects.create(user=device.token.user, authorized=True, remove=True)

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
        land_token = LandToken.objects.get(user=device.token.user)
        self.assertFalse(land_token.authorized)
        self.assertTrue(land_token.remove)
        self.assertIsNone(cache.get(str(land_token.land_token)))


class FriendDataViewTests(TestCase):

    def test_debug_mayhem_id(self):
        device = TestDevice()
        device.register_device_token()
        response = self.client.get(
            reverse("mh:friendData"),
            headers={"currentClientSessionId": str(device.current_client_session_id)},
            query_params={"debug_mayhem_id": str(device.token.user.mayhem_id.int)}
        )
        self.assertEqual(response.status_code, 200)
        friend_data_response = GetFriendData_pb2.GetFriendDataResponse()
        friend_data_response.ParseFromString(response.content)


    def test_origin(self):
        device = TestDevice()
        device.register_device_token()
        response = self.client.get(reverse("mh:friendDataOrigin"), headers={"currentClientSessionId": str(device.current_client_session_id)})
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
        device.register_device_token()
        land_token = LandToken.objects.create(user=device.token.user, retrieved=True, authorized=True)

        # Get town.
        response = self.client.get(
            reverse("mh:protoland", args=(device.token.user.mayhem_id.int,)),
            headers={"Land-Update-Token": str(land_token.land_token)}
        )
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
            reverse("mh:protoland", args=(device.token.user.mayhem_id.int,)),
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
        response = self.client.get(
            reverse("mh:protoland", args=(device.token.user.mayhem_id.int,)),
            headers={"Land-Update-Token": str(land_token.land_token)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, land_data.SerializeToString())

        # Change some data and post town with unauthorized land token.
        land_token.authorized = False
        land_token.save()
        land_token.refresh_from_db()
        land_data.friendData.dataVersion = 124
        compressed_body = gzip.compress(land_data.SerializeToString())
        response = self.client.post(
            reverse("mh:protoland", args=(device.token.user.mayhem_id.int,)),
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

        # Get town again and make sure it was not saved yet.
        response = self.client.get(
            reverse("mh:protoland", args=(device.token.user.mayhem_id.int,)),
            headers={"Land-Update-Token": str(land_token.land_token)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, land_data.SerializeToString(), msg_prefix="Unauthorized land token should not save town")
        self.assertTrue(cache.get(str(land_token.land_token)))

        # Attempt to post to other user's town by giving their mayhem id.
        new_device = TestDevice()
        new_device.register_device_token()

        compressed_body = gzip.compress(land_data.SerializeToString())
        response = self.client.post(
            reverse("mh:protoland", args=(new_device.token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={
                "Land-Update-Token": str(land_token.land_token),
                "currentClientSessionId": str(new_device.current_client_session_id),
                "Content-Encoding": "gzip"
            }
        )
        self.assertEqual(response.status_code, 400)

        # Attempt to get town with unauthorized land token.
        land_token.authorized = False
        land_token.save()
        response = self.client.get(
            reverse("mh:protoland", args=(device.token.user.mayhem_id.int,)),
            headers={"Land-Update-Token": str(land_token.land_token)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ET.tostring(ET.Element("error", attrib={"code": "409", "type": "INVALID_VALUE", "severity": "DEBUG"})))

        # Remove town.
        device.token.user.town.delete()

    def test_load_premium_currency(self):

        device = TestDevice()
        device.register_device_token()

        # Get donuts balance.
        response = self.client.get(
            reverse("mh:protocurrency", args=(device.token.user.mayhem_id.int,)),
            headers={"currentClientSessionId": str(device.current_client_session_id)}
        )
        self.assertEqual(response.status_code, 200)

        protocurrency_response = PurchaseData_pb2.CurrencyData()
        protocurrency_response.ParseFromString(response.content)
        self.assertEqual(device.token.user.donuts_balance, protocurrency_response.vcBalance )

        # Update donuts and check donuts balance again.
        device.token.user.donuts_balance = 123
        device.token.user.save()
        response = self.client.get(
            reverse("mh:protocurrency", args=(device.token.user.mayhem_id.int,)),
            headers={"currentClientSessionId": str(device.current_client_session_id)}
        )
        self.assertEqual(response.status_code, 200)

        protocurrency_response = PurchaseData_pb2.CurrencyData()
        protocurrency_response.ParseFromString(response.content)
        self.assertEqual(device.token.user.donuts_balance, protocurrency_response.vcBalance)


    def test_update_premium_currency(self):

        initial_amount = 500
        deltas = [50, -25, 2]

        device = TestDevice()
        device.register_device_token()
        device.token.user.donuts_balance = initial_amount
        device.token.user.save()
        land_token = LandToken.objects.create(user=device.token.user, retrieved=True, authorized=True)

        # Make some events up.
        currency_deltas = [
            LandData_pb2.ExtraLandMessage.CurrencyDelta(id=1, reason="Purchased donuts.", amount=deltas[0]),
            LandData_pb2.ExtraLandMessage.CurrencyDelta(id=2, reason="Purchased character.", amount=deltas[1]),
            LandData_pb2.ExtraLandMessage.CurrencyDelta(id=3, reason="Level up!", amount=deltas[2])
        ]

        extraland_request = LandData_pb2.ExtraLandMessage(currencyDelta=currency_deltas)
        extraland_response = LandData_pb2.ExtraLandResponse(processedCurrencyDelta=currency_deltas)

        # Post the previous events.
        compressed_body = gzip.compress(extraland_request.SerializeToString())
        response = self.client.post(
            reverse("mh:extraLandUpdate", args=(device.token.user.mayhem_id.int,)),
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

        # Verify that donuts balance is up to date.
        device.token.user.refresh_from_db()
        self.assertEqual(device.token.user.donuts_balance, sum(deltas, initial_amount))

        # Test if user can override currency from another user.
        new_device = TestDevice()
        new_device.register_device_token()

        compressed_body = gzip.compress(extraland_request.SerializeToString())
        response = self.client.post(
            reverse("mh:extraLandUpdate", args=(new_device.token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={
                "Land-Update-Token": str(land_token.land_token),
                "currentClientSessionId": str(device.current_client_session_id),
                "Content-Encoding": "gzip"
            }
        )
        self.assertEqual(response.status_code, 400)


class WholeLandTokenViewsTest(TestCase):

    def test_proto_whole_land_token(self):

        # Create user and device.
        device = TestDevice()
        device.register_device_token()

        # Request a new land token.
        land_token = LandToken.objects.create(user=device.token.user)
        self.assertEqual(land_token.retrieved, False)
        self.assertEqual(land_token.authorized, False)
        self.assertEqual(land_token.remove, False)

        # Retrieve the land token.
        response = self.client.get(reverse("mh:protoWholeLandToken", args=(device.token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        land_token.refresh_from_db()
        self.assertTrue(land_token.retrieved)

        # Retrieving the land token should not be possible until calling tokeninfo again.
        response = self.client.get(reverse("mh:protoWholeLandToken", args=(device.token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 403)

        # Retrieve the land token again.
        land_token.retrieved = False
        land_token.save()
        response = self.client.get(reverse("mh:protoWholeLandToken", args=(device.token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        land_token.refresh_from_db()
        self.assertTrue(land_token.retrieved)

        # If an authorized land token exists then the user may choose if they want to overwrite it
        # or switch to other device to save their progress first.
        land_token.retrieved = False
        land_token.authorized = True
        land_token.save()

        response = self.client.get(reverse("mh:protoWholeLandToken", args=(device.token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ET.tostring(ET.Element("error", attrib={"code": "409", "type": "RESOURCE_ALREADY_EXISTS"})))

        response = self.client.get(reverse("mh:protoWholeLandToken", args=(device.token.user.mayhem_id.int,)), query_params={"force": "1"})
        self.assertEqual(response.status_code, 200)
        land_token.refresh_from_db()
        self.assertFalse(land_token.authorized)
        self.assertTrue(land_token.retrieved)


    def test_check_token(self):

        # Create user and device.
        device = TestDevice()
        device.register_device_token()
        land_token = LandToken.objects.create(user=device.token.user, retrieved=True, authorized=True)

        response = self.client.get(reverse("mh:checkToken", args=(device.token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 403)

        land_token.retrieved = False
        land_token.save()

        # Unauthorize a previous authorized token.
        response = self.client.get(reverse("mh:checkToken", args=(device.token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        land_token.refresh_from_db()
        self.assertFalse(land_token.authorized)

    def test_delete_token(self):

        # Create user and device.
        device = TestDevice()
        device.register_device_token()
        land_token = LandToken.objects.create(user=device.token.user, retrieved=True, authorized=False)

        # The land token should be marked for removal.
        delete_token_request = WholeLandTokenData_pb2.DeleteTokenRequest()
        delete_token_request.token = str(land_token.land_token)
        response = self.client.post(
            reverse("mh:deleteToken",
            args=(device.token.user.mayhem_id.int,)),
            data=delete_token_request.SerializeToString(),
            content_type="application/x-protobuf"
        )
        self.assertEqual(response.status_code, 200)
        land_token.refresh_from_db()
        self.assertTrue(land_token.remove)

        # The land token should be marked for removal and be deauthorized if authorized.
        land_token.authorized = True
        land_token.remove = False
        land_token.save()
        delete_token_request = WholeLandTokenData_pb2.DeleteTokenRequest()
        delete_token_request.token = str(land_token.land_token)
        response = self.client.post(
            reverse("mh:deleteToken",
            args=(device.token.user.mayhem_id.int,)),
            data=delete_token_request.SerializeToString(),
            content_type="application/x-protobuf"
        )
        self.assertEqual(response.status_code, 200)
        land_token.refresh_from_db()
        self.assertTrue(land_token.remove)
        self.assertFalse(land_token.authorized)

        # Call view with wrong body land token.
        land_token.authorized = True
        land_token.remove = False
        land_token.save()
        delete_token_request = WholeLandTokenData_pb2.DeleteTokenRequest()
        delete_token_request.token = str(uuid.uuid4())
        response = self.client.post(
            reverse("mh:deleteToken",
            args=(device.token.user.mayhem_id.int,)),
            data=delete_token_request.SerializeToString(),
            content_type="application/x-protobuf"
        )
        self.assertEqual(response.status_code, 404)
        land_token.refresh_from_db()
        self.assertFalse(land_token.remove)
        self.assertTrue(land_token.authorized)
