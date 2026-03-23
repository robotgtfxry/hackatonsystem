from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Coalesce
from .models import JuryAssignment, Score, Criterion
from .forms import ScoreForm
from hackathon.models import Hackathon
from projects.models import Project


def jury_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_jury:
            messages.error(request, 'Dostęp tylko dla jury.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@jury_required
def jury_panel(request):
    assignments = JuryAssignment.objects.filter(jury=request.user).select_related('hackathon')
    return render(request, 'judging/jury_panel.html', {'assignments': assignments})


@jury_required
def jury_hackathon(request, hackathon_pk):
    hackathon = get_object_or_404(Hackathon, pk=hackathon_pk)
    if not JuryAssignment.objects.filter(jury=request.user, hackathon=hackathon).exists():
        messages.error(request, 'Nie jesteś przypisany do tego hackatonu jako jury.')
        return redirect('judging:panel')

    projects = Project.objects.filter(
        team__hackathon=hackathon, status='submitted'
    ).select_related('team')

    scored_projects = Score.objects.filter(
        jury=request.user, project__team__hackathon=hackathon
    ).values_list('project_id', flat=True).distinct()

    return render(request, 'judging/hackathon_projects.html', {
        'hackathon': hackathon,
        'projects': projects,
        'scored_projects': list(scored_projects),
    })


@jury_required
def score_project(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    hackathon = project.team.hackathon

    if not JuryAssignment.objects.filter(jury=request.user, hackathon=hackathon).exists():
        messages.error(request, 'Nie jesteś przypisany do tego hackatonu.')
        return redirect('judging:panel')

    criteria = hackathon.criteria.all()
    existing_scores = {s.criterion_id: s for s in Score.objects.filter(jury=request.user, project=project)}

    if request.method == 'POST':
        form = ScoreForm(request.POST, criteria=criteria)
        if form.is_valid():
            for criterion in criteria:
                points = form.cleaned_data[f'points_{criterion.pk}']
                comment = form.cleaned_data.get(f'comment_{criterion.pk}', '')
                Score.objects.update_or_create(
                    jury=request.user,
                    project=project,
                    criterion=criterion,
                    defaults={'points': points, 'comment': comment},
                )
            messages.success(request, f'Oceny dla "{project.title}" zapisane!')
            return redirect('judging:jury_hackathon', hackathon_pk=hackathon.pk)
    else:
        initial = {}
        for criterion in criteria:
            if criterion.pk in existing_scores:
                initial[f'points_{criterion.pk}'] = existing_scores[criterion.pk].points
                initial[f'comment_{criterion.pk}'] = existing_scores[criterion.pk].comment
        form = ScoreForm(initial=initial, criteria=criteria)

    return render(request, 'judging/score_project.html', {
        'project': project,
        'form': form,
        'hackathon': hackathon,
    })


def results(request, hackathon_pk):
    hackathon = get_object_or_404(Hackathon, pk=hackathon_pk)
    criteria = hackathon.criteria.all()
    projects = Project.objects.filter(
        team__hackathon=hackathon, status='submitted'
    ).select_related('team')

    rankings = []
    for project in projects:
        scores = Score.objects.filter(project=project)
        total = 0
        details = []
        for criterion in criteria:
            criterion_scores = scores.filter(criterion=criterion)
            if criterion_scores.exists():
                avg = sum(s.points for s in criterion_scores) / criterion_scores.count()
                weighted = avg * criterion.weight
                total += weighted
                details.append({'criterion': criterion, 'avg': round(avg, 2), 'weighted': round(weighted, 2)})
            else:
                details.append({'criterion': criterion, 'avg': 0, 'weighted': 0})
        rankings.append({
            'project': project,
            'total': round(total, 2),
            'details': details,
        })

    rankings.sort(key=lambda x: x['total'], reverse=True)

    return render(request, 'judging/results.html', {
        'hackathon': hackathon,
        'rankings': rankings,
        'criteria': criteria,
    })
