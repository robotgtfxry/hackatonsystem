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

    @staticmethod
    def name_taken(name, hackathon):
        return Team.objects.filter(hackathon=hackathon, name__iexact=name.strip()).exists()

    @classmethod
    def create_with_captain(cls, name, hackathon, user, description=''):
        """Tworzy zespół i wpis kapitana (jedyny członek z kontem)."""
        team = cls.objects.create(name=name.strip(), hackathon=hackathon, captain=user,
                                  description=description)
        TeamMember.objects.create(
            team=team, user=user, role='captain',
            first_name=user.first_name or user.username,
            last_name=user.last_name,
            email=user.email,
        )
        return team


class TeamMember(models.Model):
    """Członek zespołu. Konto (user) ma tylko kapitan - pozostałych wpisuje kapitan."""
    ROLE_CHOICES = [
        ('captain', 'Kapitan'),
        ('member', 'Członek'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships',
                             null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name='Imię')
    last_name = models.CharField(max_length=100, verbose_name='Nazwisko')
    email = models.EmailField(blank=True, verbose_name='Email')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.team.name} ({self.get_role_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        ordering = ['role', 'joined_at']  # kapitan pierwszy ('captain' < 'member')
