from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Hackathon
from .forms import HackathonForm
from judging.models import Criterion
from django.contrib.auth.models import User
from teams.models import Team
from projects.models import Project


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            messages.error(request, 'Brak uprawnień administratora.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def hackathon_detail(request):
    hackathon = Hackathon.current()
    teams = hackathon.teams.all()
    return render(request, 'hackathon/detail.html', {'hackathon': hackathon, 'teams': teams})


@admin_required
def hackathon_create(request):
    if Hackathon.objects.exists():
        messages.warning(request, 'Hackathon już istnieje. Edytuj istniejący.')
        return redirect('hackathon:detail')
    if request.method == 'POST':
        form = HackathonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hackathon został utworzony!')
            return redirect('hackathon:detail')
    else:
        form = HackathonForm()
    return render(request, 'hackathon/form.html', {'form': form, 'title': 'Nowy hackathon'})


@admin_required
def hackathon_edit(request):
    hackathon = Hackathon.current()
    if request.method == 'POST':
        form = HackathonForm(request.POST, instance=hackathon)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hackathon zaktualizowany!')
            return redirect('hackathon:detail')
    else:
        form = HackathonForm(instance=hackathon)
    return render(request, 'hackathon/form.html', {'form': form, 'title': 'Edytuj hackathon'})


@admin_required
def manage_criteria(request):
    hackathon = Hackathon.current()
    criteria = hackathon.criteria.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        max_points = request.POST.get('max_points', 10)
        weight = request.POST.get('weight', 1.0)
        description = request.POST.get('description', '')
        if name:
            Criterion.objects.create(
                hackathon=hackathon, name=name,
                max_points=max_points, weight=weight, description=description
            )
            messages.success(request, f'Dodano kryterium: {name}')
            return redirect('hackathon:manage_criteria')

    return render(request, 'hackathon/manage_criteria.html', {
        'hackathon': hackathon,
        'criteria': criteria,
    })


@admin_required
def delete_criterion(request, criterion_pk):
    hackathon = Hackathon.current()
    criterion = get_object_or_404(Criterion, pk=criterion_pk, hackathon=hackathon)
    criterion.delete()
    messages.success(request, 'Kryterium usunięte.')
    return redirect('hackathon:manage_criteria')


@admin_required
def admin_panel(request):
    hackathon = Hackathon.objects.first()
    users = User.objects.all().select_related('profile')
    teams = Team.objects.all().select_related('hackathon', 'captain')
    projects = Project.objects.all().select_related('team', 'team__hackathon')
    return render(request, 'hackathon/admin_panel.html', {
        'hackathon': hackathon,
        'users': users,
        'teams': teams,
        'projects': projects,
    })


@admin_required
def change_user_role(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        new_role = request.POST.get('role')
        if new_role in ['participant', 'admin']:
            target_user.profile.role = new_role
            target_user.profile.save()
            messages.success(request, f'Rola użytkownika {target_user.username} zmieniona na {new_role}.')
    return redirect('hackathon:admin_panel')


@admin_required
def delete_user(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, 'Nie możesz usunąć samego siebie.')
        return redirect('hackathon:admin_panel')
    if request.method == 'POST':
        username = target_user.username
        target_user.delete()
        messages.success(request, f'Użytkownik "{username}" został usunięty.')
    return redirect('hackathon:admin_panel')


@admin_required
def delete_team(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.method == 'POST':
        name = team.name
        team.delete()
        messages.success(request, f'Zespół "{name}" został usunięty.')
    return redirect('hackathon:admin_panel')


@admin_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == 'POST':
        title = project.title
        project.delete()
        messages.success(request, f'Projekt "{title}" został usunięty.')
    return redirect('hackathon:admin_panel')


@admin_required
def delete_hackathon(request):
    hackathon = Hackathon.current()
    if request.method == 'POST':
        name = hackathon.name
        hackathon.delete()
        messages.success(request, f'Hackathon "{name}" został usunięty.')
    return redirect('hackathon:admin_panel')
