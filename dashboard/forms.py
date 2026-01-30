from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email:")
    password = forms.CharField(label="Password:", widget=forms.PasswordInput)



class DashForm(forms.Form):
    town_file = forms.FileField(label="Town file")
