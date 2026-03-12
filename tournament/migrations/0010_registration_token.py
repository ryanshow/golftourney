import uuid

from django.db import migrations, models


def populate_tokens(apps, schema_editor):
    Registration = apps.get_model('tournament', 'Registration')
    for reg in Registration.objects.filter(token=None):
        reg.token = uuid.uuid4()
        reg.save(update_fields=['token'])


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0009_registration_logo_approved'),
    ]

    operations = [
        # Step 1: add nullable (no unique constraint yet) so existing rows don't collide
        migrations.AddField(
            model_name='registration',
            name='token',
            field=models.UUIDField(null=True, editable=False),
        ),
        # Step 2: fill in a unique UUID for every existing row
        migrations.RunPython(populate_tokens, migrations.RunPython.noop),
        # Step 3: make the field required and unique
        migrations.AlterField(
            model_name='registration',
            name='token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
