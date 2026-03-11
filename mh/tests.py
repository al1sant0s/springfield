from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from connect.models import DeviceToken, UserId
from connect.tests import TestDevice
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
        device.auth_device()
        token = device.get_device_token()

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

        # Post town.
        compressed_body = gzip.compress(land_data.SerializeToString())
        response = self.client.post(
            reverse("mh:protoland", args=(token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={"currentClientSessionId": str(device.current_client_session_id), "Content-Encoding": "gzip"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ET.tostring(ET.Element("WholeLandUpdateResponse")))


        # Get town again.
        response = self.client.get(reverse("mh:protoland", args=(token.user.mayhem_id.int,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, land_data.SerializeToString())


        # Attempt to post to other user's town by giving their mayhem id.
        new_device = TestDevice()
        new_device.auth_device()
        new_token = new_device.get_device_token()

        compressed_body = gzip.compress(land_data.SerializeToString())
        response = self.client.post(
            reverse("mh:protoland", args=(new_token.user.mayhem_id.int,)),
            data=compressed_body,
            content_type="application/x-protobuf",
            headers={"currentClientSessionId": str(device.current_client_session_id), "Content-Encoding": "gzip"}
        )
        self.assertEqual(response.status_code, 400)

