from django.http import HttpResponse
from django.test import TestCase

from connect.tests import TestDevice
from friends.models import FriendInvitation
from friends.views import send_friend_request, cancel_friend_request, accept_friend_request, remove_friend

# Create your tests here.
#
class TestFriendsManagement(TestCase):

    def test_friends_functions(self):

        device_01 = TestDevice()
        device_01.authenticate_device()
        device_01.authenticate_token()
        token_01 = device_01.get_device_token()

        device_02 = TestDevice()
        device_02.authenticate_device()
        device_02.authenticate_token()
        token_02 = device_02.get_device_token()

        success_status_code = 204
        success_response = HttpResponse(status=success_status_code)

        # Sending a friend request to yourself is not allowed.
        self.assertEqual(send_friend_request(token_01.user, token_01.user, success_response).status_code, 403)

        # Send a friend request for the first time.
        self.assertEqual(send_friend_request(token_01.user, token_02.user, success_response).status_code, success_status_code)

        # Verify the friend request really exists.
        self.assertTrue(FriendInvitation.objects.filter(from_user=token_01.user, to_user=token_02.user).exists())

        # Send another friend request when one already exists.
        self.assertEqual(send_friend_request(token_01.user, token_02.user, success_response).status_code, 409)

        # Also from the other side.
        self.assertEqual(send_friend_request(token_02.user, token_01.user, success_response).status_code, 409)

        # Cancel or reject friend request.
        self.assertEqual(cancel_friend_request(token_01.user, token_02.user, success_response).status_code, success_status_code)

        # Verify the friend request does not exist anymore.
        self.assertFalse(FriendInvitation.objects.filter(from_user=token_01.user, to_user=token_02.user).exists())

        # Send a friend request for the second time.
        self.assertEqual(send_friend_request(token_01.user, token_02.user, success_response).status_code, success_status_code)

        # Trying to accept a friend request on behalf of the other user is not allowed.
        self.assertEqual(accept_friend_request(token_02.user, token_01.user, success_response).status_code, 404)

        # Accept friend request.
        self.assertEqual(accept_friend_request(token_01.user, token_02.user, success_response).status_code, success_status_code)

        # Verify users are now friends.
        self.assertTrue(token_01.user.friends.filter(pk=token_02.user.pk).exists())
        self.assertTrue(token_02.user.friends.filter(pk=token_01.user.pk).exists())

        # Remove the friendship.
        self.assertEqual(remove_friend(token_02.user, token_01.user, success_response).status_code, success_status_code)
