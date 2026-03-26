import uuid
from django.db import models
from hackathon.models import Hackathon
from projects.models import Project


class Criterion(models.Model):
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE, related_name='criteria')
    name = models.CharField(max_length=200, verbose_name='Nazwa kryterium')
    description = models.TextField(blank=True, verbose_name='Opis')
    max_points = models.PositiveIntegerField(default=10, verbose_name='Max punktów')
    weight = models.FloatField(default=1.0, verbose_name='Waga')

    @property
    def points_range(self):
        return range(1, self.max_points + 1)

    def __str__(self):
        return f"{self.name} (max {self.max_points})"

    class Meta:
        verbose_name_plural = 'Criteria'


class JuryMember(models.Model):
    """Członek jury — admin dodaje, identyfikowany po QR."""
    name = models.CharField(max_length=200, verbose_name='Imię i nazwisko')
    email = models.EmailField(unique=True, verbose_name='Email')
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name='Token QR')
    is_active = models.BooleanField(default=True, verbose_name='Aktywny')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Członek jury (QR)'
        verbose_name_plural = 'Członkowie jury (QR)'


class JurySession(models.Model):
    """
    Sesja parowania: juror otwiera /judging/vote/ → dostaje kod sesji (QR na ekranie).
    Admin skanuje ten QR i przypisuje do konkretnego JuryMember.
    """
    code = models.UUIDField(default=uuid.uuid4, unique=True)
    jury_member = models.ForeignKey(
        JuryMember, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sessions', verbose_name='Przypisany juror'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.jury_member:
            return f"Sesja: {self.jury_member.name}"
        return f"Sesja (nieparowana): {self.code}"


class Vote(models.Model):
    """Głos jury na projekt per kryterium."""
    jury_member = models.ForeignKey(JuryMember, on_delete=models.CASCADE, related_name='votes')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='votes')
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, related_name='votes')
    score = models.PositiveIntegerField(verbose_name='Ocena')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['jury_member', 'project', 'criterion']
        verbose_name = 'Głos'
        verbose_name_plural = 'Głosy'

    def __str__(self):
        return f"{self.jury_member.name} -> {self.project.title} [{self.criterion.name}]: {self.score}"
