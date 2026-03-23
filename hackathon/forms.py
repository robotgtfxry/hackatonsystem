from django import forms
from django.contrib.auth.models import User
from .models import Hackathon


class HackathonForm(forms.ModelForm):
    class Meta:
        model = Hackathon
        fields = ['name', 'description', 'date_start', 'date_end', 'submit_deadline', 'status', 'max_team_size']
        widgets = {
            'date_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'date_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'submit_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'


class CreateJuryForm(forms.Form):
    username = forms.CharField(max_length=150, label='Nazwa użytkownika')
    first_name = forms.CharField(max_length=30, label='Imię')
    last_name = forms.CharField(max_length=30, label='Nazwisko')
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Hasło')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Użytkownik o tej nazwie już istnieje.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Użytkownik z tym emailem już istnieje.')
        return email
