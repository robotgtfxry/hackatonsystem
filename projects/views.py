from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Project, ProjectFile
from .forms import ProjectForm, ProjectFileForm
from teams.models import Team


def _is_admin_or_jury(request):
    """Sprawdź czy użytkownik to admin, albo czy to sesja jury."""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.is_admin:
        return True
    if request.session.get('jury_session'):
        return True
    return False


def project_list(request):
    if not _is_admin_or_jury(request):
        messages.error(request, 'Projekty są dostępne tylko dla admina i jury.')
        return redirect('home')
    projects = Project.objects.filter(status='submitted').select_related('team', 'team__hackathon')
    return render(request, 'projects/list.html', {'projects': projects})


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    is_team_member = (
        request.user.is_authenticated and project.team.captain == request.user
    )
    # Kapitan widzi swój projekt; pozostałe projekty tylko admin i jury
    if not (is_team_member or _is_admin_or_jury(request)):
        messages.error(request, 'Projekty są dostępne tylko dla admina i jury.')
        return redirect('home')
    files = project.files.all()
    return render(request, 'projects/detail.html', {
        'project': project,
        'files': files,
        'is_team_member': is_team_member,
    })


@login_required
def project_submit(request, team_pk):
    team = get_object_or_404(Team, pk=team_pk)

    if team.captain != request.user:
        messages.error(request, 'Tylko kapitan zespołu może to zrobić.')
        return redirect('teams:detail', pk=team_pk)

    hackathon = team.hackathon
    if hackathon.status != 'active':
        messages.error(request, 'Zgłoszenia są zamknięte. Status: ' + hackathon.get_status_display())
        return redirect('teams:detail', pk=team_pk)

    if hasattr(team, 'project'):
        return redirect('projects:edit', pk=team.project.pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.team = team
            project.status = 'submitted'
            project.save()
            messages.success(request, 'Projekt został oddany!')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/form.html', {'form': form, 'team': team, 'title': 'Oddaj projekt'})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if project.team.captain != request.user:
        messages.error(request, 'Tylko kapitan zespołu może to zrobić.')
        return redirect('projects:detail', pk=pk)

    deadline = project.team.hackathon.submit_deadline
    if deadline and timezone.now() > deadline:
        messages.error(request, 'Deadline na oddanie projektu minął!')
        return redirect('projects:detail', pk=pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Projekt zaktualizowany!')
            return redirect('projects:detail', pk=pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/form.html', {'form': form, 'team': project.team, 'title': 'Edytuj projekt'})


@login_required
def upload_file(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if project.team.captain != request.user:
        messages.error(request, 'Tylko kapitan zespołu może to zrobić.')
        return redirect('projects:detail', pk=pk)

    if request.method == 'POST':
        form = ProjectFileForm(request.POST, request.FILES)
        if form.is_valid():
            pf = form.save(commit=False)
            pf.project = project
            pf.save()
            messages.success(request, 'Plik dodany!')
            return redirect('projects:detail', pk=pk)
    else:
        form = ProjectFileForm()
    return render(request, 'projects/upload_file.html', {'form': form, 'project': project})
