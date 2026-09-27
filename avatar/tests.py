import io
import uuid
import xml.etree.ElementTree as ET
from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from connect.models import DeviceToken, UserId


def create_test_image():
    buf = io.BytesIO()
    Image.new("RGBA", (32, 32), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


class AvatarViewsTests(TestCase):
    def setUp(self):
        self.user_with_avatar = UserId.objects.create(
            username="avatar_user",
            email="avatar_user@example.com",
            avatar=SimpleUploadedFile(
                "custom_avatar.png", create_test_image(), content_type="image/png"
            ),
        )
        self.user_without_avatar = UserId.objects.create(
            username="no_avatar_user",
            email="no_avatar_user@example.com",
        )
        DeviceToken.objects.create(
            advertising_id=uuid.uuid4(),
            user=self.user_with_avatar,
            access_token="test_access_token_123",
        )

    def tearDown(self):
        if self.user_with_avatar.avatar:
            self.user_with_avatar.avatar.delete(save=False)

    def test_get_avatars_with_custom_avatar(self):
        url = reverse("avatar:get_avatars", args=(self.user_with_avatar.user_id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        root = ET.fromstring(response.content)
        user_elem = root.find("user")
        self.assertIsNotNone(user_elem)
        self.assertEqual(
            user_elem.find("userId").text, str(self.user_with_avatar.user_id)
        )

        avatar_elem = user_elem.find("avatar")
        self.assertIsNotNone(avatar_elem)
        link = avatar_elem.find("link").text
        self.assertTrue(link.startswith("http"))
        self.assertIn("custom_avatar", link)

    def test_get_avatars_without_custom_avatar(self):
        url = reverse("avatar:get_avatars", args=(self.user_without_avatar.user_id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        root = ET.fromstring(response.content)
        user_elem = root.find("user")
        self.assertIsNotNone(user_elem)

        avatar_elem = user_elem.find("avatar")
        self.assertIsNotNone(avatar_elem)
        link = avatar_elem.find("link").text or ""
        self.assertEqual(link, "")

    def test_get_avatars_lookup_by_persona_id(self):
        url = reverse("avatar:get_avatars", args=(self.user_with_avatar.persona_id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        root = ET.fromstring(response.content)
        avatar_elem = root.find("user/avatar")
        link = avatar_elem.find("link").text
        self.assertTrue(link.startswith("http"))

    def test_get_avatars_multiple_and_trailing_semicolon(self):
        users_ids = (
            f"{self.user_with_avatar.user_id};{self.user_without_avatar.user_id};"
        )
        url = reverse("avatar:get_avatars", args=(users_ids,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        root = ET.fromstring(response.content)
        users = root.findall("user")
        self.assertEqual(len(users), 2)

    def test_get_avatar_authenticated(self):
        url = reverse("avatar:get_avatar")
        response = self.client.get(url, headers={"AuthToken": "test_access_token_123"})
        self.assertEqual(response.status_code, 200)

        root = ET.fromstring(response.content)
        user_elem = root.find("user")
        self.assertEqual(
            user_elem.find("userId").text, str(self.user_with_avatar.user_id)
        )

    def test_get_avatar_unauthenticated(self):
        url = reverse("avatar:get_avatar")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
