from django.db import models
from django.http import Http404


class Hackathon(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planowany'),
        ('active', 'Aktywny'),
        ('judging', 'Ocenianie'),
        ('finished', 'Zakończony'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nazwa')
    description = models.TextField(verbose_name='Opis')
    date_start = models.DateTimeField(verbose_name='Data rozpoczęcia')
    date_end = models.DateTimeField(verbose_name='Data zakończenia')
    submit_deadline = models.DateTimeField(verbose_name='Deadline oddania projektów')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name='Status')
    max_team_size = models.PositiveIntegerField(default=5, verbose_name='Max wielkość zespołu')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-date_start']

    @classmethod
    def current(cls):
        h = cls.objects.first()
        if not h:
            raise Http404("Brak hackathonu. Utwórz hackathon w panelu admina.")
        return h


class PresentationSession(models.Model):
    """Sesja prezentacji — admin kontroluje aktualny projekt."""
    hackathon = models.OneToOneField(Hackathon, on_delete=models.CASCADE, related_name='presentation')
    current_project = models.ForeignKey(
        'projects.Project', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Aktualny projekt', related_name='+'
    )
    project_order = models.JSONField(default=list, blank=True, verbose_name='Kolejność projektów (lista ID)')
    current_index = models.IntegerField(default=0, verbose_name='Aktualny indeks')

    def __str__(self):
        return f"Prezentacja: {self.hackathon.name}"
