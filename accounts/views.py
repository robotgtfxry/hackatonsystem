from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .forms import RegisterForm, UserUpdateForm
from teams.models import Team, TeamMember


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                team = Team.create_with_captain(form.cleaned_data['team_name'], form.hackathon, user)
            login(request, user)
            messages.success(request, f'Konto i zespół "{team.name}" zostały utworzone! Dodaj teraz członków zespołu.')
            return redirect('teams:detail', pk=team.pk)
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard(request):
    profile = request.user.profile
    context = {'profile': profile}

    if profile.is_participant:
        memberships = TeamMember.objects.filter(user=request.user).select_related('team', 'team__hackathon')
        context['memberships'] = memberships
    elif profile.is_admin:
        from hackathon.models import Hackathon
        context['hackathon'] = Hackathon.objects.first()

    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil zaktualizowany!')
            return redirect('accounts:profile')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})
