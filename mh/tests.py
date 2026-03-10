from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from connect.models import DeviceToken, UserId
from connect.tests import TestDevice
from protofiles import *

import xml.etree.ElementTree as ET
import uuid

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

    def test_retrieve_town(self):
        """
        Make a new user and request their town.
        Parse the response to be sure it is valid.
        """
        device = TestDevice()
        device.auth_device()
        token = device.get_device_token()

        response = self.client.get(reverse("mh:protoland", args=(token.user.mayhem_id.int,)), query_params={})
        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(response.content)
        self.assertEqual(land_data.friendData.dataVersion, 72)
        self.assertIn("hasLemonTree", land_data.friendData)
        self.assertIn("language", land_data.friendData)
        self.assertIn("level", land_data.friendData)
        self.assertIn("name", land_data.friendData)
        self.assertIn("rating", land_data.friendData)
