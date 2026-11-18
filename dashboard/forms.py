import re

from django import forms
from hcaptcha.fields import hCaptchaField

from connect.models import UserId
from mh.views import load_town, save_town
from protofiles import GetFriendData_pb2, LandData_pb2

# Helper for editing other types of currencies in the town file.
SPENDABLES = {
    "FreeLandTokenCurrency": 194006,
}


class UploadTownForm(forms.ModelForm):
    town = forms.FileField(required=True, widget=forms.FileInput)

    class Meta:
        model = UserId
        fields = ["town"]

    def save(self, commit=True):
        if commit:
            save_town(self.instance, self.cleaned_data["town"].read())
        return self.instance


class EditCurrenciesForm(forms.ModelForm):
    money = forms.IntegerField(initial=0, min_value=0, max_value=4294967295)
    free_land_tokens = forms.IntegerField(initial=0, min_value=0, max_value=1024)
    donuts_balance = forms.IntegerField(min_value=0, max_value=99999, label="Donuts")

    class Meta:
        model = UserId
        fields = ["donuts_balance"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.land_data = LandData_pb2.LandMessage()
        self.land_data.ParseFromString(load_town(self.instance))
        self.spendables = {
            spendable.type: spendable
            for spendable in self.land_data.spendablesData.spendable
        }
        free_land_token = self.spendables.get(SPENDABLES["FreeLandTokenCurrency"])
        self.initial["money"] = self.land_data.userData.money
        self.initial["free_land_tokens"] = (
            free_land_token.amount if free_land_token else 0
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            if "money" in self.changed_data:
                self.land_data.userData.money = self.cleaned_data["money"]

            if "free_land_tokens" in self.changed_data:
                token_type = SPENDABLES["FreeLandTokenCurrency"]
                amount = self.cleaned_data["free_land_tokens"]
                if token_type in self.spendables:
                    self.spendables[token_type].amount = amount
                else:
                    self.land_data.spendablesData.spendable.add(
                        type=token_type, amount=amount
                    )

            if "money" in self.changed_data or "free_land_tokens" in self.changed_data:
                save_town(user, self.land_data.SerializeToString())

            if "donuts_balance" in self.changed_data:
                user.save(update_fields=["donuts_balance"])

        return user


class RequestUserForm(forms.Form):
    email = forms.EmailField()


class AuthCodeForm(forms.Form):
    code = forms.CharField(min_length=5, max_length=6)


class UsernameModelForm(forms.ModelForm):
    def clean_username(self):
        # Default usernames of non-registered users (u + 13 digit persona_id + 00) are reserved,
        # so a user can never take the username of a user about to be created.
        username = self.cleaned_data["username"]
        if (
            re.match(r"^u\d{13}00$", username, re.IGNORECASE)
            and username.lower() != f"u{self.instance.persona_id}00"
        ) or UserId.objects.filter(username__iexact=username).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def update_friend_data_username(self):
        if "username" in self.changed_data and self.instance.friend_data:
            friend_data_pair = (
                GetFriendData_pb2.GetFriendDataResponse.FriendDataPair.FromString(
                    bytes(self.instance.friend_data)
                )
            )
            friend_data_pair.friendData.name = self.instance.username
            self.instance.friend_data = friend_data_pair.SerializeToString()


class ResetPasswordForm(UsernameModelForm):
    password = forms.CharField(
        label="Password", widget=forms.PasswordInput, min_length=8
    )
    same_password = forms.CharField(
        label="Password", widget=forms.PasswordInput, min_length=8
    )

    class Meta:
        model = UserId
        fields = ["username"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        same_password = cleaned_data.get("same_password")

        if password and same_password and password != same_password:
            self.add_error("same_password", "The passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        self.update_friend_data_username()
        if commit:
            user.save(update_fields=["username", "password", "friend_data"])
        return user


class UserProfileForm(UsernameModelForm):
    class Meta:
        model = UserId
        fields = ["avatar", "username"]
        widgets = {"avatar": forms.FileInput}
        labels = {"avatar": False}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label_suffix = ""

    def save(self, commit=True):
        user = super().save(commit=False)
        self.update_friend_data_username()
        if commit:
            user.save()
        return user


class SearchUserForm(forms.Form):
    search_text = forms.CharField(min_length=5, label="Search user")


class DeleteUserForm(forms.Form):
    code = forms.CharField(min_length=5, max_length=6)
    hcaptcha = hCaptchaField(label="")
