from django.db import models
from django.contrib.auth.models import User
from hackathon.models import Hackathon


class Team(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nazwa zespołu')
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE, related_name='teams')
    captain = models.ForeignKey(User, on_delete=models.CASCADE, related_name='captained_teams')
    description = models.TextField(blank=True, verbose_name='Opis')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['name', 'hackathon']


class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('captain', 'Kapitan'),
        ('member', 'Członek'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.get_role_display()})"

    class Meta:
        unique_together = ['team', 'user']
