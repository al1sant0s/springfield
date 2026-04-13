from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from connect.tests import TestDevice
from mh.models import LandToken
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
        device.authenticate_device()
        token = device.get_device_token()

        # Create user land token.
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

        self.assertTrue(token.user.landtoken.authorized)
        self.assertEqual(response.status_code, 409)


    def test_missing_currenct_client_session_id(self):
        device = TestDevice()
        device.authenticate_device()
        response = self.client.post(
            reverse("mh:userstats"),
            query_params={
                "device_id": str(device.device_id)
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_device_id(self):
        device = TestDevice()
        device.authenticate_device()
        response = self.client.post(
            reverse("mh:userstats"),
            headers={
                "currentClientSessionId": str(device.current_client_session_id)
            }
        )
        self.assertEqual(response.status_code, 400)


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
        land_token = token.user.landtoken

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


        # Change some data and post town with unauthorized land token.
        land_token.authorized = False
        land_token.save()
        land_token.refresh_from_db()
        land_data.friendData.dataVersion = 124
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

        # Get town again and make sure it was not saved yet.
        response = self.client.get(reverse("mh:protoland", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, land_data.SerializeToString(), msg_prefix="Unauthorized land token should not save town")
        self.assertTrue(cache.get(str(land_token.land_token)))

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

        # Get town again and make sure it was saved this time.
        response = self.client.get(reverse("mh:protoland", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, land_data.SerializeToString())
        self.assertFalse(cache.get(str(land_token.land_token)))

        # Remove town.
        token.user.refresh_from_db()
        token.user.town.delete()

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

        land_token = token.user.landtoken

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


class WholeLandTokenViewsTest(TestCase):

    def test_proto_whole_land_token(self):

        # Create user, device and land token.
        device = TestDevice()
        device.authenticate_device()
        token = device.get_device_token()

        # Check the token is unauthorized and not retrieved.
        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        self.assertEqual(response.status_code, 200)

        self.assertFalse(token.user.landtoken.authorized)
        self.assertFalse(token.user.landtoken.retrieved)

        # Retrieve the token and check it's retrieved and it cannot be retrieved again.
        response = self.client.get(reverse("mh:protoWholeLandToken", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)

        token.user.refresh_from_db()
        self.assertFalse(token.user.landtoken.authorized)
        self.assertTrue(token.user.landtoken.retrieved)

        # Try to retrieve it again should not be possible until calling tokeninfo again.
        response = self.client.get(reverse("mh:protoWholeLandToken", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("mh:protoWholeLandToken", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)

        # If an authorized token exists then the user may choose if they want to overwrite it
        # or switch to other device to save their progress first.
        device.authenticate_token()
        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        self.assertEqual(response.status_code, 200) 

        response = self.client.get(reverse("mh:protoWholeLandToken", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ET.tostring(ET.Element("error", attrib={"code": "409", "type": "RESOURCE_ALREADY_EXISTS"})))

        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("mh:protoWholeLandToken", args=(token.user.mayhem_id.int,)), query_params={"force": "1"})
        self.assertEqual(response.status_code, 200)

        token.refresh_from_db()
        self.assertFalse(token.user.landtoken.authorized)
        self.assertTrue(token.user.landtoken.retrieved)


    def test_check_token(self):

        # Create user, device and land token.
        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()
        token = device.get_device_token()

        # Check that a retrieved token cannot be retrieved again.
        self.assertTrue(token.user.landtoken.retrieved)
        response = self.client.get(reverse("mh:checkToken", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 403)

        # Unauthorize a previous authorized token.
        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        response = self.client.get(reverse("mh:checkToken", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)

        token.refresh_from_db()
        self.assertFalse(token.user.landtoken.authorized)

    def test_delete_token(self):

        # Create user, device and land token.
        device = TestDevice()
        device.authenticate_device()
        device.authenticate_token()
        token = device.get_device_token()

        # Call view with wrong body land token.
        delete_token_request = WholeLandTokenData_pb2.DeleteTokenRequest()
        delete_token_request.token = str(uuid.uuid4())

        response = self.client.post(
            reverse("mh:deleteToken",
            args=(token.user.mayhem_id.int,)),
            data=delete_token_request.SerializeToString(),
            content_type="application/x-protobuf"
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(LandToken.objects.filter(user=token.user).exists())

        # Call view with right land token and verify it deletes it.
        delete_token_request = WholeLandTokenData_pb2.DeleteTokenRequest()
        delete_token_request.token = str(token.user.landtoken.land_token)

        response = self.client.post(
            reverse("mh:deleteToken",
            args=(token.user.mayhem_id.int,)),
            data=delete_token_request.SerializeToString(),
            content_type="application/x-protobuf"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LandToken.objects.filter(user=token.user).exists())

        # Create new unauthorized land token and check the removal procedure.
        # The land token should be marked for removal but it should only be removed
        # once the user reach userstats.
        response = self.client.get(reverse("connect:tokeninfo", args=(token.device_id,)))
        self.assertEqual(response.status_code, 200)

        token.user.refresh_from_db()
        self.assertFalse(token.user.landtoken.remove)

        delete_token_request = WholeLandTokenData_pb2.DeleteTokenRequest()
        delete_token_request.token = str(token.user.landtoken.land_token)

        response = self.client.post(
            reverse("mh:deleteToken",
            args=(token.user.mayhem_id.int,)),
            data=delete_token_request.SerializeToString(),
            content_type="application/x-protobuf"
        )
        self.assertEqual(response.status_code, 200)

        # Marked for removal but it is not removed yet.
        token.user.refresh_from_db()
        self.assertTrue(token.user.landtoken.remove)
        self.assertTrue(LandToken.objects.filter(user=token.user).exists())

        response = self.client.post(
            reverse("mh:userstats"),
            headers={
                "currentClientSessionId": str(device.current_client_session_id)
            },
            query_params={
                "device_id": str(device.device_id)
            }
        )

        # Now the land token has been removed.
        self.assertFalse(LandToken.objects.filter(user=token.user).exists())
