import datetime
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
# from .modules.algorithm_parts.algorithm import algorithm
# from .modules.algorithm_parts.convert_datetime import convert_datetime
import datetime
from django.core.management import call_command


class AlgorithmTestCase(TestCase):

    def setUp(self):
        call_command('loaddata', 'test_data.json', verbosity=0)


    # def test_algorithm(self):
    #     expected_results = algorithm(
    #         'Gorzycka 110',
    #         'Centrum Przesiadkowe',
    #         datetime.date(2024, 6, 16),  # Correct usage of datetime.date
    #         datetime.time(12, 0)
    #     )
    #
    #     print(expected_results)
    #     assert(True)
