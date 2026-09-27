from google.protobuf.message import DecodeError
from django import forms
from django.core.files.base import ContentFile
from connect.models import UserId
from protofiles import LandData_pb2


class UploadTownForm(forms.ModelForm):
    town = forms.FileField(required=True, widget=forms.FileInput)

    class Meta:
        model = UserId
        fields = ["town"]

    def clean_town(self):
        data = self.cleaned_data["town"].read()
        land_data = LandData_pb2.LandMessage()

        try:
            land_data.ParseFromString(data)

        except DecodeError:
            try:
                land_data.ParseFromString(data[0x0C:])  # tstole.de backup offset

            except DecodeError:
                raise forms.ValidationError(
                    "Invalid town file. The uploaded file is corrupted or not a valid Springfield town file."
                )

        land_data.id = str(self.instance.mayhem_id.int)
        land_data.friendData.name = self.instance.username

        return ContentFile(
            land_data.SerializeToString(), name=f"{self.instance.mayhem_id.int}.pb"
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.events = bytes()
        if commit:
            user.save()
        return user


class EditCurrenciesForm(forms.ModelForm):
    money = forms.IntegerField(initial=0, min_value=0, max_value=4294967295)
    donuts_balance = forms.IntegerField(min_value=0, max_value=99999, label="Donuts")

    class Meta:
        model = UserId
        fields = ["donuts_balance"]


class RequestUserForm(forms.Form):
    email = forms.EmailField()


class AuthCodeForm(forms.Form):
    code = forms.CharField(min_length=5, max_length=6)


class ResetPasswordForm(forms.Form):
    username = forms.CharField(min_length=5, max_length=12)
    password = forms.CharField(
        label="Password", widget=forms.PasswordInput, min_length=8
    )
    same_password = forms.CharField(
        label="Password", widget=forms.PasswordInput, min_length=8
    )


class UserProfileForm(forms.ModelForm):
    username = forms.CharField(min_length=5, max_length=12, label_suffix="")

    class Meta:
        model = UserId
        fields = ["avatar", "username"]
        widgets = {"avatar": forms.FileInput}
        labels = {"avatar": False}


class SearchUserForm(forms.Form):
    search_text = forms.CharField(label="Search user")


class DeleteUserForm(forms.Form):
    code = forms.CharField(min_length=5, max_length=6)
