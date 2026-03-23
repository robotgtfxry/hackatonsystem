from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Team, TeamMember, InviteLink
from .forms import TeamForm, AddMemberForm


@login_required
def team_list(request):
    teams = Team.objects.all().select_related('hackathon', 'captain')
    return render(request, 'teams/list.html', {'teams': teams})


@login_required
def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    members = team.members.all().select_related('user')
    is_captain = team.captain == request.user
    is_member = team.members.filter(user=request.user).exists()
    has_project = hasattr(team, 'project')
    return render(request, 'teams/detail.html', {
        'team': team,
        'members': members,
        'is_captain': is_captain,
        'is_member': is_member,
        'has_project': has_project,
    })


@login_required
def team_create(request):
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.captain = request.user
            team.save()
            TeamMember.objects.create(team=team, user=request.user, role='captain')
            messages.success(request, f'Zespół "{team.name}" został utworzony!')
            return redirect('teams:detail', pk=team.pk)
    else:
        form = TeamForm()
    return render(request, 'teams/form.html', {'form': form, 'title': 'Utwórz zespół'})


@login_required
def add_member(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if team.captain != request.user:
        messages.error(request, 'Tylko kapitan może dodawać członków.')
        return redirect('teams:detail', pk=pk)

    if request.method == 'POST':
        form = AddMemberForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, f'Użytkownik "{username}" nie istnieje.')
                return redirect('teams:add_member', pk=pk)

            if team.members.filter(user=user).exists():
                messages.warning(request, f'{username} jest już w zespole.')
                return redirect('teams:detail', pk=pk)

            if team.members.count() >= team.hackathon.max_team_size:
                messages.error(request, 'Zespół osiągnął maksymalną wielkość.')
                return redirect('teams:detail', pk=pk)

            TeamMember.objects.create(team=team, user=user, role='member')
            messages.success(request, f'{username} dodany do zespołu!')
            return redirect('teams:detail', pk=pk)
    else:
        form = AddMemberForm()
    return render(request, 'teams/add_member.html', {'form': form, 'team': team})


@login_required
def remove_member(request, pk, user_id):
    team = get_object_or_404(Team, pk=pk)
    if team.captain != request.user:
        messages.error(request, 'Tylko kapitan może usuwać członków.')
        return redirect('teams:detail', pk=pk)

    member = get_object_or_404(TeamMember, team=team, user_id=user_id)
    if member.role == 'captain':
        messages.error(request, 'Nie można usunąć kapitana z zespołu.')
        return redirect('teams:detail', pk=pk)

    member.delete()
    messages.success(request, 'Członek usunięty z zespołu.')
    return redirect('teams:detail', pk=pk)


@login_required
def generate_invite(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if team.captain != request.user:
        messages.error(request, 'Tylko kapitan może generować linki zaproszeniowe.')
        return redirect('teams:detail', pk=pk)

    uses = int(request.POST.get('uses', 1))
    invite = InviteLink.objects.create(team=team, created_by=request.user, uses_left=uses)
    invite_url = request.build_absolute_uri(f'/teams/join/{invite.token}/')
    messages.success(request, f'Link zaproszeniowy wygenerowany!')
    return render(request, 'teams/invite_generated.html', {
        'team': team,
        'invite': invite,
        'invite_url': invite_url,
    })


@login_required
def join_team(request, token):
    invite = get_object_or_404(InviteLink, token=token)

    if not invite.is_active or invite.uses_left <= 0:
        messages.error(request, 'Ten link zaproszeniowy jest nieaktywny lub wyczerpany.')
        return redirect('teams:list')

    team = invite.team

    if team.members.filter(user=request.user).exists():
        messages.warning(request, 'Już jesteś w tym zespole.')
        return redirect('teams:detail', pk=team.pk)

    if team.members.count() >= team.hackathon.max_team_size:
        messages.error(request, 'Zespół osiągnął maksymalną wielkość.')
        return redirect('teams:list')

    if request.method == 'POST':
        TeamMember.objects.create(team=team, user=request.user, role='member')
        invite.uses_left -= 1
        if invite.uses_left <= 0:
            invite.is_active = False
        invite.save()
        messages.success(request, f'Dołączyłeś do zespołu "{team.name}"!')
        return redirect('teams:detail', pk=team.pk)

    return render(request, 'teams/join_confirm.html', {'team': team, 'invite': invite})
