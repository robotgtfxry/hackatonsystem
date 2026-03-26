from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Criterion, JuryMember, JurySession, Vote
from hackathon.models import Hackathon, PresentationSession
from projects.models import Project


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            messages.error(request, 'Brak uprawnień administratora.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ============================================================
# Jury Member Management (admin)
# ============================================================

@admin_required
def jury_members_list(request):
    hackathon = Hackathon.current()
    members = JuryMember.objects.all().order_by('-created_at')
    paired_member_ids = set(
        JurySession.objects.filter(jury_member__isnull=False)
        .values_list('jury_member_id', flat=True)
    )
    return render(request, 'judging/jury_members_list.html', {
        'hackathon': hackathon,
        'members': members,
        'paired_member_ids': paired_member_ids,
    })


@admin_required
def jury_members_add(request):
    hackathon = Hackathon.current()
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
        return redirect('jury:members')
    return render(request, 'judging/jury_members_add.html', {'hackathon': hackathon})


@admin_required
def jury_member_delete(request, pk):
    member = get_object_or_404(JuryMember, pk=pk)
    if request.method == 'POST':
        member.delete()
        messages.success(request, f'Usunięto: {member.name}')
    return redirect('jury:members')


def jury_qr_display(request, qr_token):
    member = get_object_or_404(JuryMember, qr_token=qr_token)
    hackathon = Hackathon.current()
    return render(request, 'judging/jury_qr_display.html', {
        'member': member,
        'hackathon': hackathon,
    })


# ============================================================
# Panel głosowania — /jury/vote/
# ============================================================

def jury_vote_panel(request):
    hackathon = Hackathon.current()

    session_key = 'jury_session'
    session_id = request.session.get(session_key)
    jury_ses = None
    member = None

    if session_id:
        try:
            jury_ses = JurySession.objects.get(pk=session_id)
            member = jury_ses.jury_member
        except JurySession.DoesNotExist:
            del request.session[session_key]

    if not jury_ses:
        jury_ses = JurySession.objects.create()
        request.session[session_key] = jury_ses.pk

    if not member:
        return render(request, 'judging/jury_vote_waiting.html', {
            'jury_session': jury_ses,
            'hackathon': hackathon,
        })

    if hackathon.status != 'judging':
        return render(request, 'judging/jury_vote_panel.html', {
            'waiting': True,
            'hackathon': hackathon,
            'member': member,
        })

    try:
        pres_session = hackathon.presentation
        project = pres_session.current_project
    except PresentationSession.DoesNotExist:
        project = None

    criteria = list(Criterion.objects.filter(hackathon=hackathon).order_by('pk'))
    existing_votes = {}
    if project and criteria:
        for v in Vote.objects.filter(jury_member=member, project=project, criterion__in=criteria):
            existing_votes[v.criterion_id] = v.score

    if request.method == 'POST' and project and criteria:
        all_valid = True
        scores_to_save = []
        for c in criteria:
            val = request.POST.get(f'score_{c.pk}')
            if val:
                try:
                    score_int = int(val)
                    if 1 <= score_int <= c.max_points:
                        scores_to_save.append((c, score_int))
                    else:
                        all_valid = False
                except ValueError:
                    all_valid = False
            else:
                all_valid = False

        if all_valid and scores_to_save:
            for c, score_int in scores_to_save:
                Vote.objects.update_or_create(
                    jury_member=member,
                    project=project,
                    criterion=c,
                    defaults={'score': score_int},
                )
            messages.success(request, f'Oceny dla "{project.title}" zapisane!')
            return redirect('jury:vote')
        else:
            messages.error(request, 'Wypełnij wszystkie kryteria.')

    return render(request, 'judging/jury_vote_panel.html', {
        'waiting': False,
        'hackathon': hackathon,
        'member': member,
        'project': project,
        'criteria': criteria,
        'existing_votes': existing_votes,
    })


def jury_check_session_api(request):
    hackathon = Hackathon.current()
    session_key = 'jury_session'
    session_id = request.session.get(session_key)
    if not session_id:
        return JsonResponse({'paired': False})

    try:
        jury_ses = JurySession.objects.select_related('jury_member').get(pk=session_id)
    except JurySession.DoesNotExist:
        return JsonResponse({'paired': False})

    if not jury_ses.jury_member:
        return JsonResponse({'paired': False})

    member = jury_ses.jury_member

    if hackathon.status != 'judging':
        return JsonResponse({'paired': True, 'member_name': member.name, 'project': None, 'status': hackathon.status})

    try:
        pres_session = hackathon.presentation
        p = pres_session.current_project
        if p:
            voted = Vote.objects.filter(jury_member=member, project=p).exists()
            return JsonResponse({
                'paired': True,
                'member_name': member.name,
                'project': {'id': p.pk, 'title': p.title},
                'status': hackathon.status,
                'voted': voted,
            })
    except PresentationSession.DoesNotExist:
        pass

    return JsonResponse({'paired': True, 'member_name': member.name, 'project': None, 'status': hackathon.status})


# ============================================================
# Skaner QR + parowanie (admin)
# ============================================================

@admin_required
def jury_scanner(request):
    hackathon = Hackathon.current()
    members = JuryMember.objects.filter(is_active=True).order_by('name')
    paired = JurySession.objects.filter(jury_member__isnull=False).select_related('jury_member').order_by('-created_at')[:20]
    return render(request, 'judging/jury_scanner.html', {
        'hackathon': hackathon,
        'members': members,
        'paired_sessions': paired,
    })


@require_POST
def jury_pair_session(request):
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
    jury_ses = get_object_or_404(JurySession, pk=pk)
    jury_ses.jury_member = None
    jury_ses.save()
    messages.success(request, 'Sesja odłączona.')
    return redirect('jury:scanner')


@admin_required
def jury_clear_sessions(request):
    JurySession.objects.all().delete()
    messages.success(request, 'Wszystkie sesje wyczyszczone.')
    return redirect('jury:scanner')


# ============================================================
# Prezentacja (admin)
# ============================================================

@admin_required
def presentation_panel(request):
    hackathon = Hackathon.current()
    projects = list(
        Project.objects.filter(team__hackathon=hackathon, status='submitted')
        .select_related('team').order_by('pk')
    )

    session, created = PresentationSession.objects.get_or_create(
        hackathon=hackathon,
        defaults={'project_order': [p.pk for p in projects], 'current_index': 0}
    )

    if created or not session.project_order:
        session.project_order = [p.pk for p in projects]
        if projects:
            session.current_project = projects[0]
        session.save()

    criteria = list(Criterion.objects.filter(hackathon=hackathon).order_by('pk'))

    votes_summary = {}
    for p in projects:
        criterion_stats = []
        total_weighted = 0
        total_weight = 0
        for c in criteria:
            avg = Vote.objects.filter(project=p, criterion=c).aggregate(a=Avg('score'))['a']
            avg = round(avg, 2) if avg else 0
            weighted = round(avg * c.weight, 2)
            total_weighted += weighted
            total_weight += c.weight
            criterion_stats.append({'criterion': c, 'avg': avg, 'weighted': weighted})

        jury_voted = Vote.objects.filter(project=p).values('jury_member').distinct().count()

        votes_summary[p.pk] = {
            'avg': round(total_weighted / total_weight, 2) if total_weight else 0,
            'total_weighted': round(total_weighted, 2),
            'votes_count': jury_voted,
            'criteria': criterion_stats,
        }

    return render(request, 'judging/presentation_panel.html', {
        'hackathon': hackathon,
        'session': session,
        'projects': projects,
        'criteria': criteria,
        'votes_summary': votes_summary,
    })


@admin_required
def presentation_next(request):
    hackathon = Hackathon.current()
    session = get_object_or_404(PresentationSession, hackathon=hackathon)
    if session.project_order:
        session.current_index = min(session.current_index + 1, len(session.project_order) - 1)
        session.current_project = Project.objects.filter(pk=session.project_order[session.current_index]).first()
        session.save()
    return redirect('jury:presentation')


@admin_required
def presentation_prev(request):
    hackathon = Hackathon.current()
    session = get_object_or_404(PresentationSession, hackathon=hackathon)
    if session.project_order:
        session.current_index = max(session.current_index - 1, 0)
        session.current_project = Project.objects.filter(pk=session.project_order[session.current_index]).first()
        session.save()
    return redirect('jury:presentation')


@admin_required
def presentation_set_project(request, project_pk):
    hackathon = Hackathon.current()
    session = get_object_or_404(PresentationSession, hackathon=hackathon)
    project = get_object_or_404(Project, pk=project_pk)
    session.current_project = project
    if project_pk in session.project_order:
        session.current_index = session.project_order.index(project_pk)
    session.save()
    return redirect('jury:presentation')


# ============================================================
# Status hackatonu (admin)
# ============================================================

@admin_required
def hackathon_status_manage(request):
    hackathon = Hackathon.current()

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Hackathon.STATUS_CHOICES):
            hackathon.status = new_status
            hackathon.save()
            messages.success(request, f'Status: {hackathon.get_status_display()}')
        return redirect('jury:status')

    return render(request, 'judging/hackathon_status_manage.html', {
        'hackathon': hackathon,
        'jury_count': JuryMember.objects.filter(is_active=True).count(),
        'session_count': JurySession.objects.filter(jury_member__isnull=False).count(),
        'criteria': Criterion.objects.filter(hackathon=hackathon).order_by('pk'),
    })


# ============================================================
# Wyniki (publiczne)
# ============================================================

def results(request):
    hackathon = Hackathon.current()
    criteria = list(Criterion.objects.filter(hackathon=hackathon).order_by('pk'))
    projects = Project.objects.filter(
        team__hackathon=hackathon, status='submitted'
    ).select_related('team')

    rankings = []
    for project in projects:
        total_weighted = 0
        details = []
        for c in criteria:
            avg = Vote.objects.filter(project=project, criterion=c).aggregate(a=Avg('score'))['a']
            avg = round(avg, 2) if avg else 0
            weighted = round(avg * c.weight, 2)
            total_weighted += weighted
            details.append({'criterion': c, 'avg': avg, 'weighted': weighted})

        jury_voted = Vote.objects.filter(project=project).values('jury_member').distinct().count()
        rankings.append({
            'project': project,
            'total': round(total_weighted, 2),
            'details': details,
            'votes_count': jury_voted,
        })

    rankings.sort(key=lambda x: x['total'], reverse=True)

    return render(request, 'judging/results.html', {
        'hackathon': hackathon,
        'rankings': rankings,
        'criteria': criteria,
    })
