from django.test import TestCase

from localcosmos_server.tests.mixins import (WithObservationForm, WithApp, WithUser)

from io import StringIO

from django.core.management import call_command

from localcosmos_server.datasets.models import ObservationForm, Dataset

from localcosmos_server.models import App

from localcosmos_server.management.commands.create_test_datasets import DATASET_COUNT

class TestCreateTestData(WithObservationForm, WithApp, WithUser, TestCase):

    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "create_test_datasets",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_command(self):

        of_qry = ObservationForm.objects.all()
        ds_qry = Dataset.objects.all()

        self.assertFalse(of_qry.exists())
        self.assertFalse(ds_qry.exists())

        out = self.call_command()

        self.assertTrue(of_qry.exists())
        self.assertTrue(ds_qry.exists())

        app_count = App.objects.all().count()
        of_count = of_qry.count()

        self.assertEqual(ds_qry.count(), app_count * of_count * DATASET_COUNT)

