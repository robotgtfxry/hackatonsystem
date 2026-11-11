from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Team, TeamMember
from .forms import TeamForm, MemberForm, member_formset
from hackathon.models import Hackathon


@login_required
def team_list(request):
    teams = Team.objects.all().select_related('hackathon', 'captain')
    return render(request, 'teams/list.html', {'teams': teams})


@login_required
def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    members = team.members.all()
    is_captain = team.captain == request.user
    has_project = hasattr(team, 'project')
    return render(request, 'teams/detail.html', {
        'team': team,
        'members': members,
        'is_captain': is_captain,
        'can_add': is_captain and members.count() < team.hackathon.max_team_size,
        'has_project': has_project,
    })


@login_required
def team_create(request):
    hackathon = Hackathon.current()
    max_members = max(hackathon.max_team_size - 1, 0)  # bez kapitana

    if request.method == 'POST':
        form = TeamForm(request.POST, hackathon=hackathon)
        formset = member_formset(max_members, request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                team = Team.create_with_captain(
                    form.cleaned_data['name'], hackathon, request.user,
                    description=form.cleaned_data['description'],
                )
                for data in formset.cleaned_data:
                    if data:  # pomijamy puste wiersze
                        TeamMember.objects.create(team=team, role='member', **data)
            messages.success(request, f'Zespół "{team.name}" został utworzony!')
            return redirect('teams:detail', pk=team.pk)
    else:
        form = TeamForm(hackathon=hackathon)
        formset = member_formset(max_members)
    return render(request, 'teams/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Utwórz zespół',
    })


def _captain_team_or_redirect(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if team.captain != request.user:
        messages.error(request, 'Tylko kapitan może zarządzać członkami zespołu.')
        return team, redirect('teams:detail', pk=pk)
    return team, None


@login_required
def add_member(request, pk):
    team, denied = _captain_team_or_redirect(request, pk)
    if denied:
        return denied

    if team.members.count() >= team.hackathon.max_team_size:
        messages.error(request, 'Zespół osiągnął maksymalną wielkość.')
        return redirect('teams:detail', pk=pk)

    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.team = team
            member.role = 'member'
            member.save()
            messages.success(request, f'{member.full_name} dodany do zespołu!')
            return redirect('teams:detail', pk=pk)
    else:
        form = MemberForm()
    return render(request, 'teams/member_form.html', {
        'form': form, 'team': team, 'title': f'Dodaj członka do: {team.name}', 'submit': 'Dodaj',
    })


@login_required
def edit_member(request, pk, member_id):
    team, denied = _captain_team_or_redirect(request, pk)
    if denied:
        return denied

    member = get_object_or_404(TeamMember, team=team, pk=member_id)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dane członka zaktualizowane.')
            return redirect('teams:detail', pk=pk)
    else:
        form = MemberForm(instance=member)
    return render(request, 'teams/member_form.html', {
        'form': form, 'team': team, 'title': f'Edytuj członka: {member.full_name}', 'submit': 'Zapisz',
    })


@login_required
def remove_member(request, pk, member_id):
    team, denied = _captain_team_or_redirect(request, pk)
    if denied:
        return denied
    if request.method != 'POST':
        return redirect('teams:detail', pk=pk)

    member = get_object_or_404(TeamMember, team=team, pk=member_id)
    if member.role == 'captain':
        messages.error(request, 'Nie można usunąć kapitana z zespołu.')
        return redirect('teams:detail', pk=pk)

    member.delete()
    messages.success(request, 'Członek usunięty z zespołu.')
    return redirect('teams:detail', pk=pk)
