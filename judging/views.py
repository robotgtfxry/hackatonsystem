from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, FloatField, Avg
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import JuryAssignment, Score, Criterion, JuryMember, JurySession, Vote
from .forms import ScoreForm
from hackathon.models import Hackathon, HackathonStatus, PresentationSession
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


# ============================================================
# Jury Member Management (admin)
# ============================================================

def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            messages.error(request, 'Brak uprawnień administratora.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@admin_required
def jury_members_list(request):
    """Lista członków jury z tokenami QR."""
    members = JuryMember.objects.all().order_by('-created_at')
    # Kto ma sparowaną sesję
    paired_member_ids = set(
        JurySession.objects.filter(jury_member__isnull=False)
        .values_list('jury_member_id', flat=True)
    )
    return render(request, 'judging/jury_members_list.html', {
        'members': members,
        'paired_member_ids': paired_member_ids,
    })


@admin_required
def jury_members_add(request):
    """Dodaj wielu członków jury naraz."""
    if request.method == 'POST':
        entries = request.POST.get('entries', '').strip()
        count = 0
        for line in entries.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                name, email = parts[0], parts[1]
                if not JuryMember.objects.filter(email=email).exists():
                    JuryMember.objects.create(name=name, email=email)
                    count += 1
        messages.success(request, f'Dodano {count} członków jury.')
        return redirect('judging:jury_members_list')
    return render(request, 'judging/jury_members_add.html')


@admin_required
def jury_member_delete(request, pk):
    member = get_object_or_404(JuryMember, pk=pk)
    if request.method == 'POST':
        member.delete()
        messages.success(request, f'Usunięto: {member.name}')
    return redirect('judging:jury_members_list')


@admin_required
def jury_member_toggle(request, pk):
    member = get_object_or_404(JuryMember, pk=pk)
    member.is_active = not member.is_active
    member.save()
    return redirect('judging:jury_members_list')


# ============================================================
# QR — jeden link /judging/vote/ dla wszystkich jurorów
# ============================================================

def jury_vote_panel(request):
    """
    JEDEN link dla jury: /judging/vote/
    1. Juror otwiera stronę → dostaje JurySession z kodem QR na ekranie
    2. Admin skanuje ten QR → wybiera z listy jurorów → paruje sesję
    3. Juror automatycznie widzi panel głosowania (polling)
    """
    # Sprawdź czy ta przeglądarka ma już sparowaną sesję
    session_id = request.session.get('jury_session_id')
    jury_ses = None
    member = None

    if session_id:
        try:
            jury_ses = JurySession.objects.get(pk=session_id)
            member = jury_ses.jury_member
        except JurySession.DoesNotExist:
            del request.session['jury_session_id']

    # Brak sesji → utwórz nową i pokaż QR
    if not jury_ses:
        jury_ses = JurySession.objects.create()
        request.session['jury_session_id'] = jury_ses.pk

    # Sesja jest, ale admin jeszcze nie sparował z jurorem
    if not member:
        return render(request, 'judging/jury_vote_waiting.html', {
            'jury_session': jury_ses,
        })

    # Sparowane — sprawdź status hackatonu
    hs = HackathonStatus.load()
    if hs.status != 'jury_review' or not hs.active_hackathon:
        return render(request, 'judging/jury_vote_panel.html', {
            'waiting': True,
            'status': hs,
            'member': member,
        })

    hackathon = hs.active_hackathon
    try:
        pres_session = hackathon.presentation
        project = pres_session.current_project
    except PresentationSession.DoesNotExist:
        project = None

    existing_vote = None
    if project:
        existing_vote = Vote.objects.filter(jury_member=member, project=project).first()

    if request.method == 'POST' and project:
        score_val = request.POST.get('score')
        if score_val:
            try:
                score_int = int(score_val)
                if 1 <= score_int <= 10:
                    Vote.objects.update_or_create(
                        jury_member=member,
                        project=project,
                        defaults={'score': score_int},
                    )
                    messages.success(request, f'Ocena {score_int}/10 dla "{project.title}" zapisana!')
                    return redirect('judging:jury_vote_panel')
                else:
                    messages.error(request, 'Ocena musi być od 1 do 10.')
            except ValueError:
                messages.error(request, 'Nieprawidłowa ocena.')

    return render(request, 'judging/jury_vote_panel.html', {
        'waiting': False,
        'member': member,
        'project': project,
        'existing_vote': existing_vote,
        'hackathon': hackathon,
    })


def jury_check_session_api(request):
    """Polling — juror sprawdza czy admin sparował jego sesję + aktualny projekt."""
    session_id = request.session.get('jury_session_id')
    if not session_id:
        return JsonResponse({'paired': False})

    try:
        jury_ses = JurySession.objects.select_related('jury_member').get(pk=session_id)
    except JurySession.DoesNotExist:
        return JsonResponse({'paired': False})

    if not jury_ses.jury_member:
        return JsonResponse({'paired': False})

    member = jury_ses.jury_member
    hs = HackathonStatus.load()

    if hs.status != 'jury_review' or not hs.active_hackathon:
        return JsonResponse({'paired': True, 'member_name': member.name, 'project': None, 'status': hs.status})

    try:
        pres_session = hs.active_hackathon.presentation
        p = pres_session.current_project
        if p:
            voted = Vote.objects.filter(jury_member=member, project=p).exists()
            return JsonResponse({
                'paired': True,
                'member_name': member.name,
                'project': {'id': p.pk, 'title': p.title},
                'status': hs.status,
                'voted': voted,
            })
    except PresentationSession.DoesNotExist:
        pass

    return JsonResponse({'paired': True, 'member_name': member.name, 'project': None, 'status': hs.status})


# ============================================================
# Admin: Skaner QR — skanuje z ekranu jurora i paruje
# ============================================================

@admin_required
def jury_scanner(request):
    """Panel admina ze skanerem QR."""
    members = JuryMember.objects.filter(is_active=True).order_by('name')
    paired = JurySession.objects.filter(jury_member__isnull=False).select_related('jury_member').order_by('-created_at')[:20]
    return render(request, 'judging/jury_scanner.html', {
        'members': members,
        'paired_sessions': paired,
    })


@require_POST
def jury_pair_session(request):
    """
    Admin skanuje QR z ekranu jurora → dostaje kod sesji.
    Następnie wybiera jurora z listy → POST tutaj paruje sesję.
    """
    import json
    try:
        data = json.loads(request.body)
        session_code = data.get('session_code', '')
        member_id = data.get('member_id')
    except (json.JSONDecodeError, AttributeError):
        session_code = request.POST.get('session_code', '')
        member_id = request.POST.get('member_id')

    try:
        jury_ses = JurySession.objects.get(code=session_code)
    except (JurySession.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Nieprawidłowy kod sesji.'}, status=400)

    try:
        member = JuryMember.objects.get(pk=member_id, is_active=True)
    except (JuryMember.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Nieprawidłowy członek jury.'}, status=400)

    jury_ses.jury_member = member
    jury_ses.save()
    return JsonResponse({'success': True, 'name': member.name})


@admin_required
def jury_unpair_session(request, pk):
    """Admin odłącza jurora od sesji."""
    jury_ses = get_object_or_404(JurySession, pk=pk)
    jury_ses.jury_member = None
    jury_ses.save()
    messages.success(request, 'Sesja odłączona.')
    return redirect('judging:jury_scanner')


@admin_required
def jury_clear_sessions(request):
    """Admin czyści wszystkie sesje."""
    JurySession.objects.all().delete()
    messages.success(request, 'Wszystkie sesje wyczyszczone.')
    return redirect('judging:jury_scanner')


def jury_qr_display(request, qr_token):
    """Strona z kodem QR członka jury (do wydruku)."""
    member = get_object_or_404(JuryMember, qr_token=qr_token)
    return render(request, 'judging/jury_qr_display.html', {'member': member})


# ============================================================
# Admin: Presentation Mode
# ============================================================

@admin_required
def presentation_panel(request, hackathon_pk):
    """Panel prezentacji — admin kontroluje aktualny projekt."""
    hackathon = get_object_or_404(Hackathon, pk=hackathon_pk)
    projects = list(
        Project.objects.filter(team__hackathon=hackathon, status='submitted')
        .select_related('team')
        .order_by('pk')
    )

    session, created = PresentationSession.objects.get_or_create(
        hackathon=hackathon,
        defaults={
            'project_order': [p.pk for p in projects],
            'current_index': 0,
        }
    )

    if created or not session.project_order:
        session.project_order = [p.pk for p in projects]
        if projects:
            session.current_project = projects[0]
        session.save()

    # Statystyki głosów
    votes_summary = {}
    for p in projects:
        agg = Vote.objects.filter(project=p).aggregate(
            avg=Avg('score'), count=Sum('score', default=0)
        )
        votes_summary[p.pk] = {
            'avg': round(agg['avg'] or 0, 2),
            'votes_count': Vote.objects.filter(project=p).count(),
        }

    return render(request, 'judging/presentation_panel.html', {
        'hackathon': hackathon,
        'session': session,
        'projects': projects,
        'votes_summary': votes_summary,
    })


@admin_required
def presentation_next(request, hackathon_pk):
    """Przejdź do następnego projektu."""
    hackathon = get_object_or_404(Hackathon, pk=hackathon_pk)
    session = get_object_or_404(PresentationSession, hackathon=hackathon)

    if session.project_order:
        session.current_index = min(session.current_index + 1, len(session.project_order) - 1)
        project_id = session.project_order[session.current_index]
        session.current_project = Project.objects.filter(pk=project_id).first()
        session.save()

    return redirect('judging:presentation_panel', hackathon_pk=hackathon_pk)


@admin_required
def presentation_prev(request, hackathon_pk):
    """Wróć do poprzedniego projektu."""
    hackathon = get_object_or_404(Hackathon, pk=hackathon_pk)
    session = get_object_or_404(PresentationSession, hackathon=hackathon)

    if session.project_order:
        session.current_index = max(session.current_index - 1, 0)
        project_id = session.project_order[session.current_index]
        session.current_project = Project.objects.filter(pk=project_id).first()
        session.save()

    return redirect('judging:presentation_panel', hackathon_pk=hackathon_pk)


@admin_required
def presentation_set_project(request, hackathon_pk, project_pk):
    """Ustaw konkretny projekt jako aktualny."""
    hackathon = get_object_or_404(Hackathon, pk=hackathon_pk)
    session = get_object_or_404(PresentationSession, hackathon=hackathon)
    project = get_object_or_404(Project, pk=project_pk)

    session.current_project = project
    if project_pk in session.project_order:
        session.current_index = session.project_order.index(project_pk)
    session.save()

    return redirect('judging:presentation_panel', hackathon_pk=hackathon_pk)


# ============================================================
# Admin: Global Hackathon Status
# ============================================================

@admin_required
def hackathon_status_manage(request):
    """Zarządzanie globalnym statusem hackatonu."""
    hs = HackathonStatus.load()
    hackathons = Hackathon.objects.all()

    if request.method == 'POST':
        new_status = request.POST.get('status')
        hackathon_id = request.POST.get('active_hackathon')

        if new_status in dict(HackathonStatus.STATUS_CHOICES):
            hs.status = new_status
        if hackathon_id:
            hs.active_hackathon_id = int(hackathon_id)
        else:
            hs.active_hackathon = None
        hs.save()
        messages.success(request, f'Status zmieniony na: {hs.get_status_display()}')
        return redirect('judging:hackathon_status_manage')

    return render(request, 'judging/hackathon_status_manage.html', {
        'hs': hs,
        'hackathons': hackathons,
        'jury_count': JuryMember.objects.filter(is_active=True).count(),
        'session_count': JurySession.objects.filter(jury_member__isnull=False).count(),
    })


def hackathon_status_api(request):
    """Publiczny endpoint — aktualny status hackatonu."""
    hs = HackathonStatus.load()
    return JsonResponse({
        'status': hs.status,
        'status_display': hs.get_status_display(),
        'active_hackathon': hs.active_hackathon.name if hs.active_hackathon else None,
    })
