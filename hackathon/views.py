from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Hackathon
from .forms import HackathonForm, CreateJuryForm
from accounts.models import UserProfile
from judging.models import Criterion, JuryAssignment
from django.contrib.auth.models import User


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            messages.error(request, 'Brak uprawnień administratora.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def hackathon_list(request):
    hackathons = Hackathon.objects.all()
    return render(request, 'hackathon/list.html', {'hackathons': hackathons})


def hackathon_detail(request, pk):
    hackathon = get_object_or_404(Hackathon, pk=pk)
    teams = hackathon.teams.all()
    return render(request, 'hackathon/detail.html', {'hackathon': hackathon, 'teams': teams})


@admin_required
def hackathon_create(request):
    if request.method == 'POST':
        form = HackathonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hackathon został utworzony!')
            return redirect('hackathon:list')
    else:
        form = HackathonForm()
    return render(request, 'hackathon/form.html', {'form': form, 'title': 'Nowy hackathon'})


@admin_required
def hackathon_edit(request, pk):
    hackathon = get_object_or_404(Hackathon, pk=pk)
    if request.method == 'POST':
        form = HackathonForm(request.POST, instance=hackathon)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hackathon zaktualizowany!')
            return redirect('hackathon:detail', pk=pk)
    else:
        form = HackathonForm(instance=hackathon)
    return render(request, 'hackathon/form.html', {'form': form, 'title': 'Edytuj hackathon'})


@admin_required
def manage_jury(request, pk):
    hackathon = get_object_or_404(Hackathon, pk=pk)
    jury_profiles = UserProfile.objects.filter(role='jury')
    assigned = JuryAssignment.objects.filter(hackathon=hackathon).values_list('jury_id', flat=True)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('jury_ids')
        JuryAssignment.objects.filter(hackathon=hackathon).delete()
        for uid in selected_ids:
            JuryAssignment.objects.create(jury_id=uid, hackathon=hackathon)
        messages.success(request, 'Jury zaktualizowane!')
        return redirect('hackathon:detail', pk=pk)

    return render(request, 'hackathon/manage_jury.html', {
        'hackathon': hackathon,
        'jury_profiles': jury_profiles,
        'assigned': list(assigned),
    })


@admin_required
def manage_criteria(request, pk):
    hackathon = get_object_or_404(Hackathon, pk=pk)
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
            return redirect('hackathon:manage_criteria', pk=pk)

    return render(request, 'hackathon/manage_criteria.html', {
        'hackathon': hackathon,
        'criteria': criteria,
    })


@admin_required
def delete_criterion(request, pk, criterion_pk):
    criterion = get_object_or_404(Criterion, pk=criterion_pk, hackathon_id=pk)
    criterion.delete()
    messages.success(request, 'Kryterium usunięte.')
    return redirect('hackathon:manage_criteria', pk=pk)


@admin_required
def admin_panel(request):
    hackathons = Hackathon.objects.all()
    users = User.objects.all().select_related('profile')
    return render(request, 'hackathon/admin_panel.html', {'hackathons': hackathons, 'users': users})


@admin_required
def create_jury(request):
    if request.method == 'POST':
        form = CreateJuryForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            user.profile.role = 'jury'
            user.profile.save()
            messages.success(request, f'Konto jury "{user.get_full_name()}" zostało utworzone!')
            return redirect('hackathon:admin_panel')
    else:
        form = CreateJuryForm()
    return render(request, 'hackathon/create_jury.html', {'form': form})


@admin_required
def change_user_role(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        new_role = request.POST.get('role')
        if new_role in ['participant', 'jury', 'admin']:
            target_user.profile.role = new_role
            target_user.profile.save()
            messages.success(request, f'Rola użytkownika {target_user.username} zmieniona na {new_role}.')
    return redirect('hackathon:admin_panel')
