# Generated by Django 4.1.5 on 2023-02-10 14:50

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='platform',
            field=models.CharField(default='', editable=False, max_length=255),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='ObservationForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('version', models.IntegerField()),
                ('definition', models.JSONField()),
            ],
            options={
                'unique_together': {('uuid', 'version')},
            },
        ),
        migrations.CreateModel(
            name='MetaData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField()),
                ('observation_form', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='datasets.observationform')),
            ],
        ),
        migrations.AddField(
            model_name='dataset',
            name='meta_data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='datasets.metadata'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='observation_form',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.PROTECT, to='datasets.observationform'),
            preserve_default=False,
        ),
    ]