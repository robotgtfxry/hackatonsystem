import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_names_from_users(apps, schema_editor):
    TeamMember = apps.get_model('teams', 'TeamMember')
    for m in TeamMember.objects.select_related('user'):
        if m.user_id:
            m.first_name = m.user.first_name or m.user.username
            m.last_name = m.user.last_name
            m.email = m.user.email
        # Konto zostaje tylko kapitanowi
        if m.role != 'captain':
            m.user = None
        m.save()


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0002_invitelink'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='teammember',
            name='first_name',
            field=models.CharField(default='', max_length=100, verbose_name='Imię'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='teammember',
            name='last_name',
            field=models.CharField(default='', max_length=100, verbose_name='Nazwisko'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='teammember',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Email'),
        ),
        migrations.AlterUniqueTogether(
            name='teammember',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='teammember',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='team_memberships', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterModelOptions(
            name='teammember',
            options={'ordering': ['role', 'joined_at']},
        ),
        migrations.RunPython(copy_names_from_users, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='InviteLink',
        ),
    ]
