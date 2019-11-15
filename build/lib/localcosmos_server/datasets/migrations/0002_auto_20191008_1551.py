# Generated by Django 2.0.5 on 2019-10-08 15:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('datasets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('localcosmos_server', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetvalidationroutine',
            name='app',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='localcosmos_server.App'),
        ),
        migrations.AddField(
            model_name='datasetimages',
            name='dataset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datasets.Dataset'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, to_field='uuid'),
        ),
        migrations.AlterUniqueTogether(
            name='datasetvalidationroutine',
            unique_together={('app', 'validation_class')},
        ),
    ]