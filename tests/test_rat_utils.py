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
from unittest import TestCase, main

from qgis.core import (
    QgsApplication,
    QgsRasterLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsPalettedRasterRenderer,
)
from rat_utils import get_rat, rat_classify
from rat_constants import RAT_COLOR_HEADER_NAME


class RatUtilsTest(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):

        pass

    def test_embedded_rat(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        self.assertTrue(raster_layer.isValid())

        rat = get_rat(raster_layer, 1)
        self.assertFalse(rat.is_sidecar)
        self.assertEqual(list(rat.keys), ['Value',
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
        self.assertEqual(rat.data['Value'][:10], [7, 15,
                                                  23, 24, 49, 54, 61, 63, 65, 79])
        rat = get_rat(raster_layer, 2)
        self.assertEqual(rat.data, {})

    def test_sidecar_rat(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        self.assertTrue(raster_layer.isValid())

        rat = get_rat(raster_layer, 1)
        self.assertTrue(rat.is_sidecar)
        self.assertEqual(rat.keys, [
            'VALUE',
            'COUNT',
            'EVT_NAME',
            'SYSTEMGROU',
            'SYSTMGRPNA',
            'SAF_SRM',
            'NVCSORDER',
            'NVCSCLASS',
            'NVCSSUBCLA',
            'SYSTMGRPPH',
            'R', 'G', 'B',
            'RED', 'GREEN', 'BLUE',
            RAT_COLOR_HEADER_NAME
        ]
        )
        self.assertEqual(rat.values[0][:10], [
                         11, 12, 13, 14, 16, 17, 21, 22, 23, 24])
        color = rat.data[RAT_COLOR_HEADER_NAME][0]
        self.assertEqual(color.red(), 0)
        self.assertEqual(color.green(), 0)
        self.assertEqual(color.blue(), 255)

        # Test RED, GREEN, BLUE
        rat = get_rat(raster_layer, 1, ('RED', 'GREEN', 'BLUE'))
        self.assertTrue(rat.is_sidecar)
        self.assertEqual(rat.keys, [
            'VALUE',
            'COUNT',
            'EVT_NAME',
            'SYSTEMGROU',
            'SYSTMGRPNA',
            'SAF_SRM',
            'NVCSORDER',
            'NVCSCLASS',
            'NVCSSUBCLA',
            'SYSTMGRPPH',
            'R', 'G', 'B',
            'RED', 'GREEN', 'BLUE',
            RAT_COLOR_HEADER_NAME
        ]
        )
        self.assertEqual(rat.values[0][:10], [
                         11, 12, 13, 14, 16, 17, 21, 22, 23, 24])
        color = rat.data[RAT_COLOR_HEADER_NAME][0]
        self.assertEqual(color.red(), 0)
        self.assertEqual(color.green(), 0)
        self.assertEqual(color.blue(), 255)

    def _test_classify(self, raster_layer, criteria):

        self.assertTrue(raster_layer.isValid())
        rat = get_rat(raster_layer, 1)
        unique_values_count = len(set(rat.data[criteria]))
        unique_row_indexes = rat_classify(raster_layer, 1, rat, criteria)
        self.assertEqual(len(unique_row_indexes), unique_values_count)

        renderer = raster_layer.renderer()
        classes = renderer.classes()

        colors = {}

        for idx in unique_row_indexes:
            klass = classes[idx - 1]
            colors[klass.label] = klass.color.name()

        for klass in classes:
            self.assertEqual(klass.color.name(), colors[klass.label])

    def test_embedded_classify_embedded(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        criteria = 'horizontal_uncert_fixed'
        self._test_classify(raster_layer, criteria)

    def test_sidecar_classify(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        criteria = 'SYSTMGRPPH'
        self._test_classify(raster_layer, criteria)


if __name__ == '__main__':
    main()
