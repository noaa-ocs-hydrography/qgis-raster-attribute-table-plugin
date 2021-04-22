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
from qgis.PyQt.QtCore import QCoreApplication, QByteArray
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTableWidgetItem
from qgis.core import Qgis, QgsProject, QgsMapLayerLegendUtils, QgsSettings

try:
    from .rat_utils import get_rat, rat_classify, rat_log
    from .rat_model import RATModel
except ImportError:
    from rat_utils import get_rat, rat_classify, rat_log
    from rat_model import RATModel


class RasterAttributeTableDialog(QDialog):

    def __init__(self, layer, iface=None):
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_RasterAttributeTableDialog.ui')
        uic.loadUi(ui_path, self)

        self.layer = layer
        self.iface = iface

        self.mRasterBandsComboBox.addItems(
            [layer.bandName(bn) for bn in range(1, layer.bandCount() + 1)])
        self.mRasterBandsComboBox.currentIndexChanged.connect(
            self.load_rat)

        self.load_rat(0)

        self.mClassifyButton.clicked.connect(self.classify)

        self.mButtonBox.accepted.connect(self.accept)
        self.mButtonBox.rejected.connect(self.accept)

        try:
            self.restoreGeometry(QgsSettings().value(
                "RasterAttributeTable/geometry", None, QByteArray, QgsSettings.Plugins))
            rat_log('Dialog geometry restored')
        except:
            pass

    def accept(self):
        QgsSettings().setValue("RasterAttributeTable/geometry",
                             self.saveGeometry(), QgsSettings.Plugins)
        rat_log('Dialog geometry saved')
        super().accept()

    def classify(self):
        """Create a paletted/unique-value classification"""

        if QMessageBox.question(None, QCoreApplication.translate('RAT', "Overwrite classification"), QCoreApplication.translate('RAT', "The existing classification will be overwritten, do you want to continue?")) == QMessageBox.Yes:
            band = self.mRasterBandsComboBox.currentIndex() + 1
            criteria = self.mClassifyComboBox.currentText()
            rat = get_rat(self.layer, band)
            # TODO: ramp & feedback
            unique_class_row_indexes = rat_classify(
                self.layer, band, rat, criteria)
            unique_class_row_indexes.insert(0, 0)
            if self.iface is not None:
                model = self.iface.layerTreeView().layerTreeModel()
                root = QgsProject.instance().layerTreeRoot()
                node = root.findLayer(self.layer.id())
                QgsMapLayerLegendUtils.setLegendNodeOrder(
                    node, unique_class_row_indexes)
                QgsMapLayerLegendUtils.setLegendNodeUserLabel(node, 0, criteria)
                model.refreshLayerLegend(node)

    def load_rat(self, index):
        """Load RAT for raster band"""

        if type(index) != int:
            return

        self.mClassifyComboBox.clear()

        rat = get_rat(self.layer, index + 1)

        if rat.keys:
            self.model = RATModel(rat)
            self.mRATView.setModel(self.model)
            headers = rat.keys
            self.mClassifyComboBox.addItems(headers[2:])
        else:
            rat_log(QCoreApplication.translate(
                'RAT', 'There is no Raster Attribute Table for the selected raster.'), Qgis.Critical)
