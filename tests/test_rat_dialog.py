# coding=utf-8
""""Tests for RAT dialog

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-20'
__copyright__ = 'Copyright 2021, ItOpen'


import os
from unittest import TestCase, main

from qgis.core import QgsApplication, QgsRasterLayer
from qgis.PyQt.QtCore import Qt
from RasterAttributeTableDialog import RasterAttributeTableDialog

from rat_constants import RAT_COLOR_HEADER_NAME

class RasterAttributeTableDialogTest(TestCase):

    @classmethod
    def setUpClass(cls):

        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()

    @classmethod
    def tearDownClass(cls):

        pass

    def test_dialog(self):

        raster_layer = QgsRasterLayer(os.path.join(os.path.dirname(
            __file__), 'data', 'ExistingVegetationTypes_sample.img'), 'rat_test', 'gdal')
        self.assertTrue(raster_layer.isValid())

        dialog = RasterAttributeTableDialog(raster_layer)
        model = dialog.mRATView.model()
        self.assertEqual(model.rowCount(model.index(0, 0)), 59)
        self.assertEqual(model.columnCount(model.index(0, 0)), 17)
        header_model = dialog.mRATView.horizontalHeader().model()
        self.assertEqual(header_model.headerData(
            0, Qt.Horizontal), RAT_COLOR_HEADER_NAME)
        model = dialog.mRATView.model()
        color = model.data(model.index(0, 0),
                           Qt.ItemDataRole.BackgroundColorRole)
        self.assertEqual(color.red(), 0)
        self.assertEqual(color.green(), 0)
        self.assertEqual(color.blue(), 255)
        self.assertEqual(header_model.headerData(
            0, Qt.Horizontal), RAT_COLOR_HEADER_NAME)
        self.assertEqual(header_model.headerData(1, Qt.Horizontal), 'VALUE')

        #dialog.exec_()


if __name__ == '__main__':
    main()
