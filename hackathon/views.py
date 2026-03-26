from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Hackathon
from .forms import HackathonForm
from judging.models import Criterion, Vote
from django.contrib.auth.models import User
from django.db.models import Avg
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


# ============================================================
# PDF — Protokół wyników
# ============================================================

@admin_required
def pdf_results(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import io
    import os
    from django.conf import settings

    hackathon = Hackathon.current()
    criteria = list(Criterion.objects.filter(hackathon=hackathon).order_by('pk'))
    projects = Project.objects.filter(
        team__hackathon=hackathon, status='submitted'
    ).select_related('team')

    # Build rankings
    rankings = []
    for project in projects:
        total_weighted = 0
        details = []
        for c in criteria:
            avg = Vote.objects.filter(project=project, criterion=c).aggregate(a=Avg('score'))['a']
            avg = round(avg, 2) if avg else 0
            weighted = round(avg * c.weight, 2)
            total_weighted += weighted
            details.append({'name': c.name, 'avg': avg, 'weight': c.weight, 'weighted': weighted})
        jury_voted = Vote.objects.filter(project=project).values('jury_member').distinct().count()
        rankings.append({
            'project': project,
            'total': round(total_weighted, 2),
            'details': details,
            'votes_count': jury_voted,
        })
    rankings.sort(key=lambda x: x['total'], reverse=True)

    # Generate PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitlePL', parent=styles['Title'], fontSize=16, leading=20)
    normal = ParagraphStyle('NormalPL', parent=styles['Normal'], fontSize=9, leading=11)
    small = ParagraphStyle('SmallPL', parent=styles['Normal'], fontSize=8, leading=10)

    elements = []
    elements.append(Paragraph(f"Protokół wyników — {hackathon.name}", title_style))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        f"Data: {hackathon.date_start.strftime('%d.%m.%Y')} - {hackathon.date_end.strftime('%d.%m.%Y')}",
        normal
    ))
    elements.append(Spacer(1, 0.5 * cm))

    # Table header
    header = ['#', 'Projekt', 'Zespół']
    for c in criteria:
        header.append(f"{c.name}\n(x{c.weight})")
    header += ['Suma', 'Jurorzy']

    data = [header]
    for i, r in enumerate(rankings, 1):
        row = [str(i), r['project'].title, r['project'].team.name]
        for d in r['details']:
            row.append(f"{d['avg']}\n({d['weighted']})")
        row += [str(r['total']), str(r['votes_count'])]
        data.append(row)

    col_widths = [0.8 * cm, 4.5 * cm, 3.5 * cm]
    crit_w = max(1.8 * cm, (A4[0] - 3 * cm - 0.8 * cm - 4.5 * cm - 3.5 * cm - 1.5 * cm - 1.5 * cm) / max(len(criteria), 1))
    for _ in criteria:
        col_widths.append(crit_w)
    col_widths += [1.5 * cm, 1.5 * cm]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5a27')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f5f1')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Highlight top 3
    if len(rankings) >= 1:
        t.setStyle(TableStyle([('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fdf5e6'))]))
    if len(rankings) >= 2:
        t.setStyle(TableStyle([('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f3f3f0'))]))
    if len(rankings) >= 3:
        t.setStyle(TableStyle([('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#faf0e4'))]))

    elements.append(t)
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph("Podpisy komisji:", normal))
    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph("1. ______________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                               "2. ______________________________", normal))

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="protokol_wynikow_{hackathon.name}.pdf"'
    return response


# ============================================================
# PDF — Zestawienie zespołów
# ============================================================

@admin_required
def pdf_teams(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io

    hackathon = Hackathon.current()
    teams = Team.objects.filter(hackathon=hackathon).select_related('captain').order_by('name')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitlePL', parent=styles['Title'], fontSize=16, leading=20)
    normal = ParagraphStyle('NormalPL', parent=styles['Normal'], fontSize=9, leading=11)

    elements = []
    elements.append(Paragraph(f"Zestawienie zespołów — {hackathon.name}", title_style))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        f"Data: {hackathon.date_start.strftime('%d.%m.%Y')} - {hackathon.date_end.strftime('%d.%m.%Y')}"
        f" | Zespołów: {teams.count()}"
        f" | Max wielkość: {hackathon.max_team_size}",
        normal
    ))
    elements.append(Spacer(1, 0.5 * cm))

    data = [['#', 'Zespół', 'Kapitan', 'Członkowie', 'Projekt']]

    for i, team in enumerate(teams, 1):
        members_list = ', '.join(
            m.user.get_full_name() or m.user.username
            for m in team.members.all().select_related('user')
        )
        project_title = team.project.title if hasattr(team, 'project') else '—'
        captain_name = team.captain.get_full_name() or team.captain.username
        data.append([
            str(i),
            team.name,
            captain_name,
            members_list,
            project_title,
        ])

    col_widths = [0.8 * cm, 3.5 * cm, 3 * cm, 6 * cm, 4.5 * cm]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5a27')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f6f5f1')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(t)

    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="zestawienie_zespolow_{hackathon.name}.pdf"'
    return response
