from django.db import models
from teams.models import Team


class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Szkic'),
        ('submitted', 'Oddany'),
    ]

    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='project')
    title = models.CharField(max_length=300, verbose_name='Tytuł')
    description = models.TextField(verbose_name='Opis projektu')
    technologies = models.CharField(max_length=500, verbose_name='Użyte technologie')
    repo_url = models.URLField(blank=True, verbose_name='Link do repozytorium')
    demo_url = models.URLField(blank=True, verbose_name='Link do demo')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='project_files/')
    description = models.CharField(max_length=300, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.title} - {self.file.name}"
