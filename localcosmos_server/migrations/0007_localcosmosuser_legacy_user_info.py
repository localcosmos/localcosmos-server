from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('localcosmos_server', '0006_serverexternalmedia'),
    ]

    operations = [
        migrations.AddField(
            model_name='localcosmosuser',
            name='legacy_user_info',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
