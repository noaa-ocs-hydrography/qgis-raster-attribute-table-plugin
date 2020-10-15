# -*- coding: utf-8 -*-
"""
***************************************************************************
Name			 	 : RasterAttributeTable
Description          : RasterAttributeTable
Date                 : 12/Oct/2020
copyright            : (C) 2020 by ItOpen
email                : info@itopen.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


import os

from osgeo import gdal
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem


class RasterAttributeTableDialog(QDialog):
    def __init__(self, layer):
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_RasterAttributeTableDialog.ui')
        uic.loadUi(ui_path, self)

        self.layer = layer

        self.mRasterBandsComboBox.addItems(
            [layer.bandName(bn) for bn in range(1, layer.bandCount() + 1)])
        self.mRasterBandsComboBox.currentIndexChanged.connect(
            self.on_mRasterBandsComboBox_currentIndexChanged)

        self.mClassifyButton.clicked.connect(self.on_mClassifyButton_clicked)

        self.mButtonBox.accepted.connect(self.accept)
        self.mButtonBox.rejected.connect(self.accept)

    def on_mClassifyButton_clicked(self):
        """Classify"""

        # TODO
        pass

    def on_mRasterBandsComboBox_currentIndexChanged(self, index):
        """Load RAT for raster band"""

        if type(index) != int:
            return

        self.mRasterTableWidget.clear()
        self.mRasterTableWidget.setSortingEnabled(False)
        self.mClassifyComboBox.clear()

        ds = gdal.OpenEx(self.layer.source())
        if ds:
            band = ds.GetRasterBand(index + 1)
            if band:
                rat = band.GetDefaultRAT()
                self.mRasterTableWidget.setRowCount(rat.GetRowCount())
                self.mRasterTableWidget.setColumnCount(rat.GetColumnCount())
                # Header
                headers = []
                for i in range(0, rat.GetColumnCount()):
                    headers.append(rat.GetNameOfCol(i))

                self.mRasterTableWidget.setHorizontalHeaderLabels(headers)

                for r in range(0, rat.GetRowCount()):
                    for c in range(0, rat.GetColumnCount()):
                        self.mRasterTableWidget.setItem(
                            r, c, QTableWidgetItem(rat.GetValueAsString(r, c)))

                self.mRasterTableWidget.setSortingEnabled(True)
                self.mClassifyComboBox.addItems(headers[2:])
