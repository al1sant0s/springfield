from django.test import TestCase
from dashboard.forms import SearchUserForm, UserProfileForm
from connect.models import UserId


class DashboardFormsTests(TestCase):
    def test_search_user_form_min_length(self):
        # Query with fewer than 5 characters should be invalid
        form = SearchUserForm(data={"search_text": "abc"})
        self.assertFalse(form.is_valid())
        self.assertIn("search_text", form.errors)

    def test_search_user_form_max_length(self):
        # Query with more than 16 characters should be invalid
        form = SearchUserForm(data={"search_text": "a" * 17})
        self.assertFalse(form.is_valid())
        self.assertIn("search_text", form.errors)

    def test_search_user_form_valid(self):
        # Query between 5 and 16 characters should be valid
        form = SearchUserForm(data={"search_text": "springfield"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["search_text"], "springfield")

    def test_user_profile_form_username_length(self):
        user = UserId.objects.create(username="validuser", email="valid@example.com")

        # Too short (< 5)
        form = UserProfileForm(instance=user, data={"username": "abcd"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

        # 16 characters is allowed
        form = UserProfileForm(instance=user, data={"username": "a" * 16})
        self.assertTrue(form.is_valid())

        # Too long (> 16)
        form = UserProfileForm(instance=user, data={"username": "a" * 17})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_user_profile_form_username_characters(self):
        user = UserId.objects.create(username="validuser", email="valid2@example.com")

        # Invalid characters (e.g. spaces or special chars)
        form = UserProfileForm(instance=user, data={"username": "invalid user!"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_user_profile_form_renames_avatar(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from avatar.tests import create_test_image

        user = UserId.objects.create(username="validuser", email="valid3@example.com")
        form = UserProfileForm(
            instance=user,
            data={"username": user.username},
            files={
                "avatar": SimpleUploadedFile(
                    "my_original_photo.png",
                    create_test_image(),
                    content_type="image/png",
                )
            },
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["avatar"].name, f"{user.user_id}.png")
