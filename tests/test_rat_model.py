# coding=utf-8
""""RAT model tests

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-27'
__copyright__ = 'Copyright 2021, ItOpen'


import os
from osgeo import gdal
import shutil
from unittest import TestCase, main
from qgis.PyQt.QtCore import QTemporaryDir, Qt, QModelIndex
from qgis.PyQt.QtTest import QAbstractItemModelTester
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsRasterLayer, QgsApplication
from rat_utils import get_rat
from rat_model import RATModel
from rat_classes import RATField
from rat_constants import RAT_COLOR_HEADER_NAME

class TestRATModel(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    def setUp(self):

        self.tmp_dir = QTemporaryDir()
        self.tmp_path = os.path.join(self.tmp_dir.path(), 'data')

        shutil.copytree(os.path.join(os.path.dirname(
            __file__), 'data'), self.tmp_path)

        self.raster_layer = QgsRasterLayer(os.path.join(
            self.tmp_path, 'NBS_US5PSMBE_20200923_0_generalized_p.source_information.tiff'), 'rat_test', 'gdal')
        self.assertTrue(self.raster_layer.isValid())

        self.raster_layer_color = QgsRasterLayer(os.path.join(
            self.tmp_path, 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        self.assertTrue(self.raster_layer_color.isValid())

    def test_insert_column(self):

        rat = get_rat(self.raster_layer, 1)
        self.assertTrue(rat.isValid())

        model = RATModel(rat)
        tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
        column_count = model.columnCount(QModelIndex())
        field = RATField('f1', gdal.GFU_Generic, gdal.GFT_String)
        self.assertTrue(model.insert_column(3, field)[0])
        self.assertEqual(model.columnCount(
            QModelIndex()), column_count + 1)
        self.assertEqual(model.headers.index('f1'), 3)

        # Error
        field = RATField('f1', gdal.GFU_Generic, gdal.GFT_String)
        self.assertFalse(model.insert_column(3, field)[0])
        self.assertEqual(model.columnCount(
            QModelIndex()), column_count + 1)

    def test_insert_column_color(self):

        rat = get_rat(self.raster_layer_color, 1)
        self.assertTrue(rat.isValid())

        model = RATModel(rat)
        tester = QAbstractItemModelTester(
            model, QAbstractItemModelTester.FailureReportingMode.Warning)
        column_count = model.columnCount(QModelIndex())
        field = RATField('f1', gdal.GFU_Generic, gdal.GFT_String)
        self.assertTrue(model.insert_column(3, field)[0])
        self.assertEqual(model.columnCount(
            QModelIndex()), column_count + 1)
        self.assertEqual(model.headers.index('f1'), 3)

        # Error
        field = RATField('f1', gdal.GFU_Generic, gdal.GFT_String)
        self.assertFalse(model.insert_column(3, field)[0])
        self.assertEqual(model.columnCount(
            QModelIndex()), column_count + 1)


    def test_remove_column(self):

        rat = get_rat(self.raster_layer, 1)
        self.assertTrue(rat.isValid())

        model = RATModel(rat)
        tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
        column_count = model.columnCount(QModelIndex())
        self.assertFalse(model.remove_column(0)[0])
        self.assertFalse(model.remove_column(1)[0])
        self.assertTrue(model.remove_column(2)[0])
        self.assertEqual(model.columnCount(
            QModelIndex()), column_count - 1)

    def test_edit_color(self):

        rat = get_rat(self.raster_layer_color, 1)
        model = RATModel(rat)
        tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)

        index = model.index(0, 0)
        value = QColor(Qt.magenta)
        model.setData(index, value)

        self.assertEqual(model.data(index, Qt.BackgroundColorRole), value)

    def test_remove_color(self):

        rat = get_rat(self.raster_layer_color, 1)
        model = RATModel(rat)
        tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)

        self.assertTrue({'R', 'G', 'B'}.issubset(rat.keys))
        self.assertTrue({'R', 'G', 'B'}.issubset(model.headers))
        self.assertTrue(model.has_color)
        column_count = model.columnCount(QModelIndex())
        self.assertEqual(column_count, 17)

        # Remove colors
        self.assertTrue(model.remove_color())
        self.assertEqual(model.columnCount(QModelIndex()), column_count - 4)

        self.assertFalse(rat.has_color)
        self.assertFalse(model.has_color)
        self.assertFalse({'R', 'G', 'B'}.issubset(rat.keys))
        self.assertFalse({'R', 'G', 'B'}.issubset(model.headers))

        # Add color back (with alpha)
        self.assertTrue(model.insert_color(2))
        self.assertEqual(model.columnCount(QModelIndex()), column_count + 1)
        self.assertTrue({'R', 'G', 'B'}.issubset(rat.keys))
        self.assertTrue({'R', 'G', 'B'}.issubset(model.headers))
        self.assertTrue(rat.has_color)
        self.assertTrue(model.has_color)
        self.assertTrue(RAT_COLOR_HEADER_NAME in rat.keys)

    def test_add_remove_row(self):

        def _test(raster_layer):

            rat = get_rat(self.raster_layer_color, 1)
            model = RATModel(rat)
            tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)

            row_count = model.rowCount(QModelIndex())
            value_index = 1 if model.has_color else 0
            value_0 = model.data(model.index(0, value_index, QModelIndex()))
            value_last = model.data(model.index(row_count - 1, value_index, QModelIndex()))

            # Insert first
            self.assertTrue(model.insert_row(0))
            self.assertEqual(model.rowCount(QModelIndex()), row_count + 1)
            self.assertNotEqual(model.data(model.index(0, value_index, QModelIndex())), value_0)
            self.assertEqual(model.data(model.index(0, value_index, QModelIndex())), 0)

            self.assertTrue(model.remove_row(0))
            self.assertEqual(model.rowCount(QModelIndex()), row_count)
            self.assertEqual(model.data(model.index(0, value_index, QModelIndex())), value_0)

            # Insert last
            self.assertTrue(model.insert_row(row_count))
            self.assertEqual(model.rowCount(QModelIndex()), row_count + 1)
            self.assertNotEqual(model.data(model.index(row_count, value_index, QModelIndex())), value_last)
            self.assertEqual(model.data(model.index(row_count, value_index, QModelIndex())), 0)
            self.assertEqual(model.data(model.index(row_count - 1, value_index, QModelIndex())), value_last)

            self.assertTrue(model.remove_row(row_count))
            self.assertEqual(model.rowCount(QModelIndex()), row_count)
            self.assertEqual(model.data(model.index(row_count - 1, value_index, QModelIndex())), value_last)

        _test(self.raster_layer)
        _test(self.raster_layer_color)

    def test_header_tooltip(self):

        rat = get_rat(self.raster_layer_color, 1)
        model = RATModel(rat)
        tooltip = model.getHeaderTooltip(1)
        self.assertIn('<dt>Role</dt><dd>Class value(min=max)</dd>', tooltip)
        self.assertIn('<dt>Type</dt><dd>Integer</dd>', tooltip)
        tooltip = model.getHeaderTooltip(2)
        self.assertIn('<dt>Role</dt><dd>Histogram pixel count</dd>', tooltip)
        self.assertIn('<dt>Type</dt><dd>Integer</dd>', tooltip)
        tooltip = model.getHeaderTooltip(3)
        self.assertIn('<dt>Role</dt><dd>General purpose field</dd>', tooltip)
        self.assertIn('<dt>Type</dt><dd>String</dd>', tooltip)


if __name__ == '__main__':
    main()
