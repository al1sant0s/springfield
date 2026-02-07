from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)



class UploadTownForm(forms.Form):
    prefix = "town"
    town_file = forms.FileField(label="Town file")


class EditCurrenciesForm(forms.Form):
    prefix = "currency"
    money = forms.IntegerField(initial=0, min_value=0)
    donuts = forms.IntegerField(initial=0, min_value=0)


class RequestUserForm(forms.Form):
    email = forms.EmailField()


class AuthCodeForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput)
    code = forms.CharField(min_length=6, max_length=6)


class ResetPasswordForm(forms.Form):
    username = forms.CharField(min_length=5, max_length=12, empty_value=".null")
    password = forms.CharField(label="Password", widget=forms.PasswordInput, min_length=8)
    same_password = forms.CharField(label="Password", widget=forms.PasswordInput, min_length=8)


class UserProfileForm(forms.Form):
    profile_avatar = forms.ImageField(label="Avatar Picture", required=False)
    profile_username = forms.CharField(
        label="Username",
        label_suffix="",
        min_length=5,
        max_length=12,
        empty_value=".null",
    )


class SearchUserForm(forms.Form):
    search_text = forms.CharField(label="Search user")



class CheckBoxForm(forms.Form):
    checkbox = forms.BooleanField(label="")
