# coding=utf-8
""""RAT utils tests

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-19'
__copyright__ = 'Copyright 2021, ItOpen'

import os
from rat_utils import get_rat
from qgis.core import QgsApplication, QgsRasterLayer
from unittest import TestCase

class RatUtilsTest(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):

        cls.qgs.exitQgis()


    def test_embedded_rat(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(__file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        self.assertTrue(raster_layer.isValid())

        rat = get_rat(raster_layer, 1)
        self.assertEqual(list(rat.keys()), ['Value',
                                            'Count',
                                            'data_assessment',
                                            'feature_least_depth',
                                            'significant_features',
                                            'feature_size',
                                            'full_coverage',
                                            'bathy_coverage',
                                            'horizontal_uncert_fixed',
                                            'horizontal_uncert_var',
                                            'License_Name',
                                            'License_URL',
                                            'Source_Survey_ID',
                                            'Source_Institution',
                                            'survey_date_start',
                                            'survey_date_end'])
        self.assertEqual(rat['Value'][:10], ['7', '15', '23', '24', '49', '54', '61', '63', '65', '79'])
        rat = get_rat(raster_layer, 2)
        self.assertEqual(rat, {})



