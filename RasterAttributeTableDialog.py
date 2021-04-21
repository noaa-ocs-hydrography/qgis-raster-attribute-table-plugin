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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QBrush
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTableWidgetItem

try:
    from .rat_utils import get_rat, rat_classify, rat_log
except ImportError:
    from rat_utils import get_rat, rat_classify, rat_log


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
            self.load_rat)

        self.load_rat(0)

        self.mClassifyButton.clicked.connect(self.classify)

        self.mButtonBox.accepted.connect(self.accept)
        self.mButtonBox.rejected.connect(self.accept)

    def classify(self):
        """Create a paletted/unique-value classification"""


        if QMessageBox.question(None, QCoreApplication.translate('RAT', "Overwrite classification"), QCoreApplication.translate('RAT', "The existing classification will be overwritten, do you want to continue?")) == QMessageBox.Yes:
            band = self.mRasterBandsComboBox.currentIndex() + 1
            column = self.mClassifyComboBox.currentText()
            rat = get_rat(self.layer, band)
            # TODO: ramp & feedback
            classes = rat_classify(self.layer, band, rat, column)
            rat_log('Classes: %s' % classes)

    def load_rat(self, index):
        """Load RAT for raster band"""

        if type(index) != int:
            return

        self.mRasterTableWidget.clear()
        self.mRasterTableWidget.setSortingEnabled(False)
        self.mClassifyComboBox.clear()

        rat = get_rat(self.layer, index + 1)
        rat_data = rat.values

        if rat_data:
            row_count = len(list(rat_data.values())[0])
            self.mRasterTableWidget.setRowCount(row_count)
            headers = list(rat_data.keys())
            has_color = 'RAT Color' in headers

            if has_color:
                headers = headers[:-1]
                headers.insert(0, 'RAT Color')

            self.mRasterTableWidget.setColumnCount(len(headers))
            self.mRasterTableWidget.setHorizontalHeaderLabels(headers)

            for r in range(row_count):
                c = 0
                for header in headers:
                    if header == 'RAT Color':
                        color = rat_data['RAT Color'][r]
                        widget = QTableWidgetItem(' ')
                        widget.setBackground(QBrush(color))
                        self.mRasterTableWidget.setItem(
                            r, c, widget)
                    else:
                        self.mRasterTableWidget.setItem(
                            r, c, QTableWidgetItem(str(rat_data[header][r])))
                    c += 1

            self.mRasterTableWidget.setSortingEnabled(True)
            self.mClassifyComboBox.addItems(headers[2:])
