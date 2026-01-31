from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email:")
    password = forms.CharField(label="Password:", widget=forms.PasswordInput)



class UploadTownForm(forms.Form):
    prefix = "town"
    town_file = forms.FileField(label="Town file")


class EditCurrenciesForm(forms.Form):
    prefix = "currency"
    money = forms.IntegerField(min_value=0)
    donuts = forms.IntegerField(min_value=0)
