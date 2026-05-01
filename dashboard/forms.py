from django import forms

from connect.models import UserId


class UploadTownForm(forms.ModelForm):
    class Meta:
        model = UserId
        fields = ["town"]
        widgets = {
            "town": forms.FileInput
        }


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
    username = forms.CharField(min_length=5, max_length=12, empty_value=".null")
    password = forms.CharField(label="Password", widget=forms.PasswordInput, min_length=8)
    same_password = forms.CharField(label="Password", widget=forms.PasswordInput, min_length=8)


class UserProfileForm(forms.ModelForm):
    username = forms.CharField(min_length=5, max_length=12, label_suffix="")
    class Meta:
        model = UserId
        fields = ["avatar", "username"]
        widgets = {
            "avatar": forms.FileInput
        }
        labels = {
            "avatar": False
        }


class SearchUserForm(forms.Form):
    search_text = forms.CharField(label="Search user")
