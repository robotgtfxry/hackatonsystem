from django import forms
from .models import Team, TeamMember


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description']

    def __init__(self, *args, hackathon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hackathon = hackathon
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.hackathon and Team.name_taken(name, self.hackathon):
            raise forms.ValidationError('Zespół o tej nazwie już istnieje.')
        return name.strip()


class MemberForm(forms.ModelForm):
    """Dane członka zespołu wpisywane przez kapitana (członkowie nie mają kont)."""

    class Meta:
        model = TeamMember
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


def member_formset(max_members, data=None):
    """Formularze członków (bez kapitana) przy tworzeniu zespołu. Puste wiersze są pomijane."""
    MemberFormSet = forms.formset_factory(
        MemberForm, extra=max_members, max_num=max_members, validate_max=True,
    )
    return MemberFormSet(data, prefix='members')
