from django import forms
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
