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
import shutil
from osgeo import gdal
from unittest import TestCase, main, skipIf

from qgis.core import (
    QgsApplication,
    QgsRasterLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsPalettedRasterRenderer,
    QgsPresetSchemeColorRamp,
    QgsRandomColorRamp,
    QgsColorRampShader,
    QgsRasterShader,
    QgsRasterBandStats,
    QgsProject,
)

from qgis.PyQt.QtCore import QTemporaryDir
from qgis.PyQt.QtGui import QColor
from rat_utils import (
    get_rat,
    rat_classify,
    has_rat,
    can_create_rat,
    create_rat_from_raster,
    data_type_name,
)

from rat_constants import RAT_COLOR_HEADER_NAME


class RatUtilsTest(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):

        cls.qgs.exitQgis()

    def test_xml_rat(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        self.assertTrue(raster_layer.isValid())

        rat = get_rat(raster_layer, 1)
        self.assertEqual(rat.thematic_type, gdal.GRTT_THEMATIC)
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
        self.assertEqual(rat.thematic_type, gdal.GRTT_THEMATIC)
        self.assertIsNotNone(rat.path)
        self.assertIn('ExistingVegetationTypes_sample.img.vat.dbf', rat.path)
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
        self.assertEqual(rat.thematic_type, gdal.GRTT_THEMATIC)

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

    @skipIf(os.environ.get('CI', False), 'Fails on CI for unknown reason')
    def test_rat_save_dbf(self):

        tmp_dir = QTemporaryDir()
        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', 'ExistingVegetationTypes_sample.img'), tmp_dir.path())

        dest_raster_layer = QgsRasterLayer(os.path.join(tmp_dir.path(), 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        rat = get_rat(dest_raster_layer, 1)
        self.assertFalse(rat.isValid())

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')

        rat = get_rat(raster_layer, 1)
        self.assertTrue(rat.isValid())
        self.assertTrue(rat.save_as_dbf(os.path.join(tmp_dir.path(), 'ExistingVegetationTypes_sample.img')))

        dest_raster_layer = QgsRasterLayer(os.path.join(
            tmp_dir.path(), 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        rat_new = get_rat(dest_raster_layer, 1)
        self.assertTrue(rat_new.isValid())
        self.assertEqual(rat_new.data, rat.data)

    def test_rat_save_xml(self):

        tmp_dir = QTemporaryDir()
        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), tmp_dir.path())
        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.tiff.aux.xml'), tmp_dir.path())

        dest_raster_layer = QgsRasterLayer(os.path.join(
            tmp_dir.path(), 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        rat = get_rat(dest_raster_layer, 1)
        self.assertFalse(rat.isValid())

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')

        rat = get_rat(raster_layer, 1)
        self.assertTrue(rat.isValid())
        # Note: band 1
        self.assertTrue(rat.save_as_xml(os.path.join(
            tmp_dir.path(), 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 1))

        dest_raster_layer = QgsRasterLayer(os.path.join(
            tmp_dir.path(), 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        rat_new = get_rat(dest_raster_layer, 1)
        self.assertTrue(rat_new.isValid())
        self.assertEqual(rat_new.data, rat.data)

    def test_has_rat(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        self.assertTrue(has_rat(raster_layer))

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        self.assertTrue(has_rat(raster_layer))

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.tiff'), 'rat_test', 'gdal')
        self.assertFalse(has_rat(raster_layer))

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', '2x2_2_BANDS_INT16.tif'), 'rat_test', 'gdal')
        self.assertTrue(has_rat(raster_layer))


    def test_can_create_rat(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'NBS_US5PSMBE_20200923_0_generalized_p.tiff'), 'rat_test', 'gdal')
        self.assertFalse(can_create_rat(raster_layer))

        renderer = QgsPalettedRasterRenderer(raster_layer.dataProvider(), 1, [])
        raster_layer.setRenderer(renderer)
        self.assertTrue(can_create_rat(raster_layer))

    def test_rat_create(self):

        def _test(is_sidecar):

            QgsProject.instance().removeAllMapLayers()

            tmp_dir = QTemporaryDir()
            shutil.copy(os.path.join(os.path.dirname(
                __file__), 'data', 'raster-palette.tif'), tmp_dir.path())

            rat_path = os.path.join(
                tmp_dir.path(), 'raster-palette.tif' + ('.vat.dbf' if is_sidecar else '.aux.xml'))
            self.assertFalse(os.path.exists(rat_path))

            raster_layer = QgsRasterLayer(os.path.join(tmp_dir.path(), 'raster-palette.tif'), 'rat_test', 'gdal')
            QgsProject.instance().addMapLayer(raster_layer)

            self.assertTrue(raster_layer.isValid())
            self.assertFalse(can_create_rat(raster_layer))
            self.assertFalse(has_rat(raster_layer))

            band = 1

            # Set renderer
            ramp = QgsRandomColorRamp()
            renderer = QgsPalettedRasterRenderer(
                raster_layer.dataProvider(), 1, QgsPalettedRasterRenderer.classDataFromRaster(raster_layer.dataProvider(), band, ramp))
            raster_layer.setRenderer(renderer)
            self.assertTrue(can_create_rat(raster_layer))

            rat = create_rat_from_raster(raster_layer, is_sidecar, rat_path)
            self.assertTrue(rat.isValid())

            self.assertEqual(rat.data['Count'], [78, 176, 52])
            self.assertEqual(rat.data['Value'], [
                            2.257495271713565, 7.037407804695962, 270.4551067154352])
            self.assertEqual(rat.data['A'], [255, 255, 255])
            self.assertNotEqual(rat.data['R'], [0, 0, 0])

            self.assertTrue(rat.save(band))
            self.assertTrue(os.path.exists(rat_path))

            QgsProject.instance().removeMapLayers([raster_layer.id()])
            del (raster_layer)

            self.assertTrue(os.path.exists(rat_path))
            QgsApplication.processEvents()

            # Reload and check
            raster_layer = QgsRasterLayer(os.path.join(
                tmp_dir.path(), 'raster-palette.tif'), 'rat_test', 'gdal')
            self.assertTrue(raster_layer.isValid())
            self.assertFalse(can_create_rat(raster_layer))
            self.assertTrue(has_rat(raster_layer), rat_path)

            os.unlink(rat_path)

        _test(True)
        _test(False)

    def test_athematic_rat(self):
        """Test RAT from single band with range values"""

        tmp_dir = QTemporaryDir()

        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', '2x2_1_BAND_FLOAT.tif'), tmp_dir.path())

        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', '2x2_1_BAND_FLOAT.tif.aux.xml'), tmp_dir.path())

        raster_layer = QgsRasterLayer(os.path.join(
            tmp_dir.path(), '2x2_1_BAND_FLOAT.tif'), 'rat_test', 'gdal')

        band = 1

        rat = get_rat(raster_layer, band)
        self.assertTrue(rat.isValid())
        self.assertEqual(rat.thematic_type, gdal.GRTT_ATHEMATIC)
        self.assertEqual(rat.value_columns, ['Value Min', 'Value Max'])
        self.assertEqual(rat.field_usages, {
                         gdal.GFU_Generic, gdal.GFU_Name, gdal.GFU_Min, gdal.GFU_Max, gdal.GFU_Red, gdal.GFU_Green, gdal.GFU_Blue})
        self.assertEqual(rat.data[rat.value_columns[0]],
                         [-1e+25, 3000000000000.0, 1e+20])
        self.assertEqual(rat.data[rat.value_columns[1]], [
                         3000000000000.0, 1e+20, 5e+25])

        # Round trip tests
        unique_indexes = rat_classify(raster_layer, band, rat, 'Class', ramp=None)
        self.assertEqual(unique_indexes, [1, 2, 3])
        rat2 = create_rat_from_raster(raster_layer, True, os.path.join(
            tmp_dir.path(), '2x2_1_BAND_FLOAT.tif.vat.dbf'))
        self.assertTrue(rat2.isValid())
        # Generic (Class3) is gone
        self.assertEqual(rat2.field_usages, {
                         gdal.GFU_Name, gdal.GFU_Min, gdal.GFU_Max, gdal.GFU_Red, gdal.GFU_Green, gdal.GFU_Blue, gdal.GFU_Alpha})
        self.assertEqual(
            rat2.data['Value Min'], [-3.40282e+38, 3000000000000.0, 1e+20])
        self.assertEqual(
            rat2.data['Value Max'], [3000000000000.0, 1e+20, 5e+25])

        # Reclass on class 2
        unique_indexes = rat_classify(raster_layer, band, rat, 'Class2', ramp=None)
        self.assertEqual(unique_indexes, [1, 2])

        rat2 = create_rat_from_raster(raster_layer, True, os.path.join(
            tmp_dir.path(), '2x2_1_BAND_FLOAT.tif.vat.dbf'))
        self.assertTrue(rat2.isValid())
        # Generic (Class3) is gone
        self.assertEqual(rat2.field_usages, {
                         gdal.GFU_Name, gdal.GFU_Min, gdal.GFU_Max, gdal.GFU_Red, gdal.GFU_Green, gdal.GFU_Blue, gdal.GFU_Alpha})
        self.assertEqual(
            rat2.data['Value Min'], [-3.40282e+38, 3000000000000.0, 1e+20])
        self.assertEqual(
            rat2.data['Value Max'], [3000000000000.0, 1e+20, 5e+25])

    def test_classify_athematic(self):
        """Test issue with athematic RAT classification dedup"""

        tmp_dir = QTemporaryDir()
        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', 'band1_float32_noct_epsg4326.tif'), tmp_dir.path())
        shutil.copy(os.path.join(os.path.dirname(
            __file__), 'data', 'band1_float32_noct_epsg4326.tif.aux.xml'), tmp_dir.path())

        raster_layer = QgsRasterLayer(os.path.join(
            tmp_dir.path(), 'band1_float32_noct_epsg4326.tif'), 'rat_test', 'gdal')
        rat = get_rat(raster_layer, 1)
        self.assertTrue(rat.isValid())
        unique_indexes = rat_classify(raster_layer, 1, rat, 'class2')
        self.assertEqual(unique_indexes, [1, 2, 3])


    def test_data_type_name(self):

        self.assertEqual(data_type_name(gdal.GFT_Real), 'Floating point')
        self.assertEqual(data_type_name(gdal.GFT_Integer), 'Integer')
        self.assertEqual(data_type_name(gdal.GFT_String), 'String')
        self.assertEqual(data_type_name(-100), 'String')
        self.assertEqual(data_type_name(100), 'String')

if __name__ == '__main__':
    main()
