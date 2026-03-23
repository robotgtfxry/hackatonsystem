from django import forms
from .models import Score


class ScoreForm(forms.Form):
    def __init__(self, *args, criteria=None, **kwargs):
        super().__init__(*args, **kwargs)
        if criteria:
            for criterion in criteria:
                self.fields[f'points_{criterion.pk}'] = forms.IntegerField(
                    min_value=0,
                    max_value=criterion.max_points,
                    label=f'{criterion.name} (max {criterion.max_points})',
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': criterion.max_points}),
                    required=True,
                )
                self.fields[f'comment_{criterion.pk}'] = forms.CharField(
                    required=False,
                    label=f'Komentarz do {criterion.name}',
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
                )
