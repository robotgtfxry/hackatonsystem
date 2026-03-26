from django import forms
from .models import Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class AddMemberForm(forms.Form):
    username = forms.CharField(max_length=150, label='Nazwa użytkownika',
                               widget=forms.TextInput(attrs={'class': 'form-control'}))
