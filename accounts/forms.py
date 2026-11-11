from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from hackathon.models import Hackathon
from teams.models import Team


class RegisterForm(UserCreationForm):
    """Rejestracja lidera zespołu - od razu z nazwą zespołu."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label='Imię')
    last_name = forms.CharField(max_length=30, required=True, label='Nazwisko')
    team_name = forms.CharField(max_length=200, required=True, label='Nazwa zespołu')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    field_order = ['team_name', 'username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hackathon = Hackathon.objects.first()
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_team_name(self):
        name = self.cleaned_data['team_name'].strip()
        if not self.hackathon:
            raise forms.ValidationError('Rejestracja jest niedostępna - brak hackathonu.')
        if Team.name_taken(name, self.hackathon):
            raise forms.ValidationError('Zespół o tej nazwie już istnieje.')
        return name


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
