"""Wypełnia bazę demo przykładowymi danymi. Uruchamiane przez: manage.py shell < seed.py"""
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from hackathon.models import Hackathon
from teams.models import Team, TeamMember
from projects.models import Project
from judging.models import Criterion, JuryMember, Vote

now = timezone.now()
admin = User.objects.create_superuser('admin', 'admin@hackathon.pl', 'Admin.Demo.2026',
                                      first_name='Administrator', last_name='Hackathonu')
admin.profile.role = 'admin'; admin.profile.save()

h = Hackathon.objects.create(
    name='Hackathon Szkolny 2026',
    description='24 godziny kodowania, pizza i dobre pomysły. Zbudujcie aplikację, która ułatwia życie w szkole lub mieście.',
    date_start=now - timedelta(hours=3), date_end=now + timedelta(hours=21),
    submit_deadline=now + timedelta(hours=20), status='active', max_team_size=4,
)
crit = [Criterion.objects.create(hackathon=h, name=n, max_points=10, weight=w, description=d) for n, w, d in [
    ('Innowacyjność', 1.0, 'Na ile pomysł jest nowy i odważny'),
    ('Wykonanie techniczne', 1.5, 'Jakość kodu i działanie aplikacji'),
    ('Prezentacja', 1.0, 'Jak zespół przedstawił projekt'),
]]
jury = [JuryMember.objects.create(name=n, email=e) for n, e in [
    ('Katarzyna Zielińska', 'k.zielinska@example.com'),
    ('Piotr Mazur', 'p.mazur@example.com'),
]]

demo = [
    ('Byte Brigade', ('Michał', 'Wiśniewski', 'michal'), [('Ola', 'Kamińska'), ('Kuba', 'Lewandowski')],
     ('EkoTrasa', 'Aplikacja planująca dojazd do szkoły z najmniejszym śladem węglowym.', 'Django, Leaflet, OpenStreetMap',
      'https://github.com/example/ekotrasa'), [8, 7, 9]),
    ('Kod Zero', ('Zuzanna', 'Dąbrowska', 'zuzanna'), [('Filip', 'Zając'), ('Maja', 'Szymańska'), ('Igor', 'Król')],
     ('SmartLibrary', 'Rezerwacja książek w szkolnej bibliotece z powiadomieniami o zwrocie.', 'React, FastAPI, PostgreSQL',
      'https://github.com/example/smartlibrary'), [7, 9, 8]),
]
for team_name, (fn, ln, un), members, (title, desc, tech, repo), scores in demo:
    u = User.objects.create_user(un, f'{un}@example.com', 'Haslo.Demo.2026', first_name=fn, last_name=ln)
    t = Team.create_with_captain(team_name, h, u)
    for mfn, mln in members:
        TeamMember.objects.create(team=t, first_name=mfn, last_name=mln, role='member')
    p = Project.objects.create(team=t, title=title, description=desc, technologies=tech, repo_url=repo, status='submitted')
    for j, delta in zip(jury, [0, -1]):
        for c, s in zip(crit, scores):
            Vote.objects.create(jury_member=j, project=p, criterion=c, score=max(1, s + delta))
print('seed OK')
