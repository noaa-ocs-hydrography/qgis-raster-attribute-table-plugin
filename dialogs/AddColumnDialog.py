# coding=utf-8
""""Dialog to add a new RAT column

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
from qgis.PyQt.QtCore import QCoreApplication, QByteArray, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QDialogButtonBox
from qgis.core import Qgis, QgsApplication, QgsSettings

try:
    from ..rat_utils import rat_log, data_type_name
except ValueError:
    from rat_utils import rat_log, data_type_name


class AddColumnDialog(QDialog):

    def __init__(self, model, iface=None):

        QDialog.__init__(self)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_AddColumnDialog.ui')
        uic.loadUi(ui_path, self)

        self.mError.setStyleSheet('* { color: red; }')

        try:
            self.restoreGeometry(QgsSettings().value(
                "AddColumn/geometry", None, QByteArray, QgsSettings.Plugins))
        except:
            pass

        self.mName.textChanged.connect(self.updateDialog)
        self.mStandardColumn.toggled.connect(self.updateDialog)

        self.mDataType.addItem(data_type_name(gdal.GFT_String), gdal.GFT_String)
        self.mDataType.addItem(data_type_name(gdal.GFT_Integer), gdal.GFT_Integer)
        self.mDataType.addItem(data_type_name(gdal.GFT_Real), gdal.GFT_Real)

        self.upper_headers = [h.upper() for h in model.headers]
        self.model = model
        self.updateDialog()

    def updateDialog(self):

        self.mDefinition.setEnabled(self.mStandardColumn.isChecked())
        is_valid = True
        self.mError.hide()
        if self.mStandardColumn:
            name = self.mName.text().strip().upper()
            if name == '' or name in self.upper_headers:
                self.mError.setText(QCoreApplication.translate('RAT', 'Name must be unique and it cannot be empty'))
                self.mError.show()
                is_valid = False

        self.mButtonBox.button(QDialogButtonBox.Ok).setEnabled(is_valid)

    def accept(self):
        QgsSettings().setValue("AddColumn/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)

        super().accept()

    def reject(self):
        QgsSettings().setValue("AddColumn/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)
        super().reject()
