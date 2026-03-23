from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from hackathon.models import Hackathon
from projects.models import Project


class Criterion(models.Model):
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE, related_name='criteria')
    name = models.CharField(max_length=200, verbose_name='Nazwa kryterium')
    description = models.TextField(blank=True, verbose_name='Opis')
    max_points = models.PositiveIntegerField(default=10, verbose_name='Max punktów')
    weight = models.FloatField(default=1.0, verbose_name='Waga')

    def __str__(self):
        return f"{self.name} (max {self.max_points})"

    class Meta:
        verbose_name_plural = 'Criteria'


class JuryAssignment(models.Model):
    jury = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jury_assignments')
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE, related_name='jury_assignments')

    def __str__(self):
        return f"{self.jury.username} -> {self.hackathon.name}"

    class Meta:
        unique_together = ['jury', 'hackathon']


class Score(models.Model):
    jury = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scores')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='scores')
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, related_name='scores')
    points = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='Punkty'
    )
    comment = models.TextField(blank=True, verbose_name='Komentarz')
    scored_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project.title} - {self.criterion.name}: {self.points}"

    class Meta:
        unique_together = ['jury', 'project', 'criterion']
