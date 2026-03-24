from django.db import models


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


class HackathonStatus(models.Model):
    """Singleton — globalny status hackatonu."""
    STATUS_CHOICES = [
        ('in_progress', 'W trakcie'),
        ('submissions_closed', 'Zgłoszenia zamknięte'),
        ('jury_review', 'Ocenianie jury'),
        ('results_announced', 'Wyniki ogłoszone'),
    ]

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='in_progress', verbose_name='Status globalny')
    active_hackathon = models.ForeignKey(
        Hackathon, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Aktywny hackathon', related_name='global_status'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Status hackatonu'
        verbose_name_plural = 'Status hackatonu'

    def __str__(self):
        return self.get_status_display()

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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
