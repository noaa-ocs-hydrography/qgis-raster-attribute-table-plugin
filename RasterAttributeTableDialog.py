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

from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtWidgets import (
    QDialog,
    QTableWidgetItem,
    QMessageBox,
)

from .rat_classify import rat_classify
from .rat_utils import get_rat


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
        """Create a rule paletted unique-value classification"""

        if QMessageBox.Ok == QMessageBox.Question(None, QtCore.QCoreApplication.translate('RAT', "The existing classification will be overwritten, do you want to proceed?")):
            band = self.mRasterBandsComboBox.currentValue()
            column = self.mClassifyComboBox.currentValue()
            rat_classify(self.layer, band, column)

    def on_mRasterBandsComboBox_currentIndexChanged(self, index):
        """Load RAT for raster band"""

        if type(index) != int:
            return

        self.mRasterTableWidget.clear()
        self.mRasterTableWidget.setSortingEnabled(False)
        self.mClassifyComboBox.clear()

        rat = get_rat(self.layer, index + 1)

        if rat:
            row_count = len(list(rat.values())[0])
            self.mRasterTableWidget.setRowCount(row_count)
            headers = list(rat.keys())
            self.mRasterTableWidget.setColumnCount(len(headers))
            self.mRasterTableWidget.setHorizontalHeaderLabels(headers)

            for r in range(row_count):
                for c in range(len(headers)):
                    self.mRasterTableWidget.setItem(
                        r, c, QTableWidgetItem(rat[c][r]))

            self.mRasterTableWidget.setSortingEnabled(True)
            self.mClassifyComboBox.addItems(headers[2:])
