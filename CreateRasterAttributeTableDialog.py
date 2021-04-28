# coding=utf-8
""""Dialog to create a new RAT

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-28'
__copyright__ = 'Copyright 2021, ItOpen'


import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, QByteArray, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTableWidgetItem
from qgis.core import Qgis, QgsApplication, QgsSettings, QgsRasterLayer, QgsMapLayer

try:
    from .rat_utils import rat_log, create_rat_from_raster
    from .rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA
except ImportError:
    from rat_utils import rat_log, create_rat_from_raster
    from rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA


class CreateRasterAttributeTableDialog(QDialog):

    ratCreated = pyqtSignal(QgsMapLayer)

    def __init__(self, layer, iface=None):

        QDialog.__init__(self)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_CreateRasterAttributeTableDialog.ui')
        uic.loadUi(ui_path, self)

        self.layer = layer
        self.iface = iface

        try:
            self.restoreGeometry(QgsSettings().value(
                "CreateRasterAttributeTable/geometry", None, QByteArray, QgsSettings.Plugins))
        except:
            pass

    def accept(self):
        QgsSettings().setValue("CreateRasterAttributeTable/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)

        # Create the RAT
        is_sidecar = self.mDbfRadioButton.isChecked()
        rat_path = self.layer.publicSource() + ('.vat.dbf' if is_sidecar else '.aux.xml')
        rat = create_rat_from_raster(
            self.layer, is_sidecar, rat_path)
        if not rat.isValid():
            self.iface.messageBar().pushMessage(
                QCoreApplication.translate('RAT', "Error"),
                QCoreApplication.translate('RAT', "There was an error creating the RAT."), level=Qgis.Critical)
        else:
            if not rat.save(self.layer.renderer().band()):
                self.iface.messageBar().pushMessage(
                    QCoreApplication.translate('RAT', "Error"),
                    QCoreApplication.translate('RAT', "There was an error saving the RAT."), level=Qgis.Critical)
            else:
                rat_log("The Raster Attribute Table has been successfully saved to: %s" % rat_path)
                self.ratCreated.emit(self.layer)

        super().accept()

    def reject(self):
        QgsSettings().setValue("CreateRasterAttributeTable/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)
        super().reject()
