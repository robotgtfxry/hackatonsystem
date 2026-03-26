from django.db import migrations, models
import django.db.models.deletion


def clear_votes(apps, schema_editor):
    Vote = apps.get_model('judging', 'Vote')
    Vote.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('judging', '0004_remove_jurymember_session_active_jurysession'),
    ]

    operations = [
        # Clear existing votes (no criterion assigned)
        migrations.RunPython(clear_votes, migrations.RunPython.noop),
        # Add criterion field
        migrations.AddField(
            model_name='vote',
            name='criterion',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='votes',
                to='judging.criterion',
            ),
            preserve_default=False,
        ),
        # Update unique_together
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together={('jury_member', 'project', 'criterion')},
        ),
    ]
