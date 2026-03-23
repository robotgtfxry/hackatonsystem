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
