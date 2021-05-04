# coding=utf-8
""""RAT ManagedLayers Dialog

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-28'
__copyright__ = 'Copyright 2021, ItOpen'


import os
from osgeo import gdal

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, QByteArray
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QDialogButtonBox
from qgis.core import Qgis, QgsApplication, QgsSettings


class ManagedLayersDialog(QDialog):

    def __init__(self, current_row, iface=None):

        QDialog.__init__(self)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_ManagedLayersDialog.ui')
        uic.loadUi(ui_path, self)

        try:
            self.restoreGeometry(QgsSettings().value(
                "RATManagedLayers/geometry", None, QByteArray, QgsSettings.Plugins))
        except:
            pass

    def accept(self):
        QgsSettings().setValue("RATManagedLayers/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)

        super().accept()

    def reject(self):
        QgsSettings().setValue("RATManagedLayers/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)
        super().reject()
