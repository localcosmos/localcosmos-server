# Generated by Django 5.0.4 on 2024-06-10 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('localcosmos_server', '0003_alter_localcosmosuser_follows'),
    ]

    operations = [
        migrations.AddField(
            model_name='app',
            name='aab_url',
            field=models.URLField(null=True),
        ),
    ]
