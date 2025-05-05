from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from localcosmos_server.tests.common import (test_settings, )

from localcosmos_server.taxonomy.TaxonManager import TaxonManager

from localcosmos_server.tests.mixins import (WithApp, WithUser, WithObservationForm, CommonSetUp,
                                             WithValidationRoutine)

from localcosmos_server.models import TaxonomicRestriction
from localcosmos_server.datasets.models import Dataset, DatasetValidationRoutine
from localcosmos_server.models import ServerImageStore

from localcosmos_server.taxonomy.lazy import LazyAppTaxon

ALL_TAXON_MODELS = [
    TaxonomicRestriction,
    Dataset,
    DatasetValidationRoutine,
    ServerImageStore,
]

class TestTaxonManager(WithValidationRoutine, WithObservationForm, CommonSetUp, WithApp, WithUser, TestCase):
    
    def setUp(self):
        super().setUp()
        
        picea_abies_kwargs = {
            "taxonNuid": "006002009001005007001",
            "nameUuid": "1541aa08-7c23-4de0-9898-80d87e9227b3",
            "taxonSource": "taxonomy.sources.col",
            "taxonLatname": "Picea abies",
            "taxonAuthor":"Linnaeus"
        }
        
        self.picea_abies = LazyAppTaxon(**picea_abies_kwargs)
        
        lacerta_agilis_kwargs = {
            'taxonSource': 'taxonomy.sources.col',
            'taxonNuid': '00100800c00301000m001',
            'taxonLatname': 'Lacerta agilis',
            'taxonAuthor': 'Linnaeus, 1758',
            'nameUuid': 'c36819f7-4b65-477b-8756-389289c531ec',
        }
        
        self.lacerta_agilis = LazyAppTaxon(**lacerta_agilis_kwargs)

    
    @test_settings
    def test_init(self):
        taxon_manager = TaxonManager(self.app)
        
        self.assertEqual(taxon_manager.app, self.app)
        self.assertIsInstance(taxon_manager, TaxonManager)
        
    @test_settings
    def test_get_taxon_models(self):
        taxon_manager = TaxonManager(self.app)
        
        taxon_models = taxon_manager.get_taxon_models()
        
        expected_models = set(ALL_TAXON_MODELS)
        self.assertEqual(set(taxon_models), expected_models)
    
    
    @test_settings
    def test_get_taxon_occurrences(self):
        taxon_manager = TaxonManager(self.app)
        
        # get the occurrences for the picea_abies taxon
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        self.assertEqual(occurrences, [])
        
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)
        
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        validation_routine.set_taxon(self.picea_abies)
        validation_routine.save()
        
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        expected_occurrences = [
            {
                'model': Dataset,
                'occurrences' : [dataset],
            },
            {
                'model' : DatasetValidationRoutine,
                'occurrences' : [validation_routine,],
            }
        ]
        occurrences[0]['occurrences'] = list(occurrences[0]['occurrences'])
        occurrences[1]['occurrences'] = list(occurrences[1]['occurrences'])
        self.assertEqual(occurrences, expected_occurrences)
    
    
    @test_settings
    def test_get_taxon_occurrences_from_taxonomic_restrictions(self):
        taxon_manager = TaxonManager(self.app)
        
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        restriction = TaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(validation_routine),
            object_id=validation_routine.pk,
        )
        restriction.set_taxon(self.picea_abies)
        restriction.save()
        
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        expected_occurrences = [
            {
                'model': TaxonomicRestriction,
                'occurrences' : [restriction,],
            }
        ]
        occurrences[0]['occurrences'] = list(occurrences[0]['occurrences'])
        
        self.assertEqual(occurrences, expected_occurrences)
    
    @test_settings
    def test_swap_taxon(self):
        
        # test unsupperted swap models
        
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)
        
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        validation_routine.set_taxon(self.picea_abies)
        validation_routine.save()
        
        taxon_manager = TaxonManager(self.app)
        
        taxon_manager.swap_taxon(self.picea_abies, self.lacerta_agilis)
        
        dataset.refresh_from_db()
        self.assertEqual(dataset.taxon, self.picea_abies)
        validation_routine.refresh_from_db()
        self.assertEqual(validation_routine.taxon, self.picea_abies)
        
    @test_settings
    def test_get_Dataset_occurrences_verbose(self):
        taxon_manager = TaxonManager(self.app)
        
        # create a dataset
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)
        
        taxon_manager = TaxonManager(self.app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        verbose_occurrences = taxon_manager._get_Dataset_occurrences_verbose(occurrences[0])
        
        verbose_occurrences[0]['occurrences'] = list(verbose_occurrences[0]['occurrences'])
        
        expected = [{
            'model': Dataset,
            'verbose_model_name': 'Dataset',
            'occurrences': [dataset],
            'verbose_occurrences': ['occurs in 1 datasets']
        }]
        
        self.assertEqual(verbose_occurrences, expected)
    
    
    @test_settings
    def test_get_DatasetValidationRoutine_occurrences_verbose(self):
        # create a validation routine
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        validation_routine.set_taxon(self.picea_abies)
        validation_routine.save()
        
        taxon_manager = TaxonManager(self.app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        verbose_occurrences = taxon_manager._get_DatasetValidationRoutine_occurrences_verbose(
            occurrences[0]
        )
        
        verbose_occurrences[0]['occurrences'] = list(verbose_occurrences[0]['occurrences'])
        
        expected = [{
            'model': DatasetValidationRoutine,
            'occurrences': [validation_routine],
            'verbose_model_name': 'Dataset Validation Routine',
            'verbose_occurrences': ['occurs in 1 validation routines']
        }]
        self.assertEqual(verbose_occurrences, expected)
    
    
    @test_settings
    def test_get_TaxonomicRestriction_occurrences_verbose(self):
        # create a validation routine
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        restriction = TaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(validation_routine),
            object_id=validation_routine.pk,
        )
        restriction.set_taxon(self.picea_abies)
        restriction.save()
        
        taxon_manager = TaxonManager(self.app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        verbose_occurrences = taxon_manager._get_TaxonomicRestriction_occurrences_verbose(
            occurrences[0]
        )
        
        verbose_occurrences[0]['occurrences'] = list(verbose_occurrences[0]['occurrences'])
        
        expected = [{
            'model': TaxonomicRestriction,
            'occurrences': [restriction],
            'verbose_model_name': 'Dataset Validation Routine',
            'verbose_occurrences': ['acts as a taxonomic restriction of Expert review']
        }]
        
        self.assertEqual(verbose_occurrences, expected)
        
        
    @test_settings
    def test_get_verbose_occurrences(self):
        
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)
        # create a validation routine
        self.create_validation_routine()
        
        validation_routine = DatasetValidationRoutine.objects.first()
        validation_routine.set_taxon(self.picea_abies)
        validation_routine.save()
        
        restriction = TaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(validation_routine),
            object_id=validation_routine.pk,
        )
        restriction.set_taxon(self.picea_abies)
        restriction.save()
        
        taxon_manager = TaxonManager(self.app)        
        verbose_occurrences = taxon_manager.get_verbose_occurrences(self.picea_abies)
        
        for occurrence in verbose_occurrences:
            occurrence['occurrences'] = list(occurrence['occurrences'])
        
        expected = [
            {
                'model': TaxonomicRestriction,
                'occurrences': [restriction,],
                'verbose_model_name': 'Dataset Validation Routine',
                'verbose_occurrences': ['acts as a taxonomic restriction of Expert review']
            },
            {
                'model': Dataset,
                'occurrences': [dataset],
                'verbose_model_name': 'Dataset',
                'verbose_occurrences': ['occurs in 1 datasets']
            },
            {
                'model': DatasetValidationRoutine,
                'occurrences': [validation_routine],
                'verbose_model_name': 'Dataset Validation Routine',
                'verbose_occurrences': ['occurs in 1 validation routines']
            }
        ]
        
        self.assertEqual(verbose_occurrences, expected)
        
    
    @test_settings
    def test_check_swappability(self):
        
        self.create_validation_routine()
        validation_routine = DatasetValidationRoutine.objects.first()
        validation_routine.set_taxon(self.picea_abies)
        validation_routine.save()
        
        taxon_manager = TaxonManager(self.app)
        
        restriction = TaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(validation_routine),
            object_id=validation_routine.pk,
        )
        restriction.set_taxon(self.picea_abies)
        restriction.save()
        
        is_swappable = taxon_manager.check_swappability([restriction], self.lacerta_agilis)
        self.assertTrue(is_swappable)
        
        restriction_2 = TaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(validation_routine),
            object_id=validation_routine.pk,
        )
        
        restriction_2.set_taxon(self.lacerta_agilis)
        restriction_2.save()
        
        is_swappable = taxon_manager.check_swappability([restriction], self.lacerta_agilis)
        self.assertFalse(is_swappable)