from django.db import migrations

def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Buerger')
    Group.objects.get_or_create(name='Mitarbeiter')

class Migration(migrations.Migration):
    dependencies = [
        ('einwohnermeldeamt', '__first__'),  # <- anpassen (2. angepasst!
    ]

    operations = [
        migrations.RunPython(create_groups),
    ]