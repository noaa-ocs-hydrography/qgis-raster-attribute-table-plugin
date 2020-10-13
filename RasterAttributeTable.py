# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : RasterAttributeTable
Description          : RasterAttributeTable
Date                 : 12/Oct/2020
copyright            : (C) 2020 by ItOpen
email                : elpaso@itopen.it
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
from functools import partial

from osgeo import gdal
from qgis.core import QgsApplication, QgsMapLayer, QgsMapLayerType, QgsMessageLog, QgsProject
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

# Import the code for the dialog
from .RasterAttributeTableDialog import RasterAttributeTableDialog


class RasterAttributeTable(object):

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.action = QAction(
            QgsApplication.getThemeIcon("/mActionOpenTable.svg"), QCoreApplication.translate("RAT", "&Open Attribute Table"))
        self.action.triggered.connect(self.showAttributeTable)
        self.iface.addCustomActionForLayerType(self.action,
                                               None, QgsMapLayerType.RasterLayer, allLayers=False)

    def initGui(self):
        QgsProject.instance().layerWasAdded.connect(self.populateContextMenu)

    def log(self, message):
        QgsMessageLog.logMessage(message, "RAT")

    def unload(self):
        # Remove the plugin menu item and icon
        pass

    def populateContextMenu(self, layer):

        self.log("Layer added: %s" % layer.name())

        if layer and layer.type() == QgsMapLayerType.RasterLayer:
            ds = gdal.OpenEx(layer.source())
            if ds:
                for b in range(1, ds.RasterCount + 1):
                    band = ds.GetRasterBand(b)
                    rat = band.GetDefaultRAT()
                    if rat and rat.GetRowCount() > 0:
                        self.iface.addCustomActionForLayer(self.action, layer)
                        self.log("Custom Layer action added for: %s" %
                                 layer.name())
                        break
                del ds

    def showAttributeTable(self):

        # Get current raster
        layer = self.iface.activeLayer()

        self.log("Show attribute table for layer: %s" % layer.name())

        # Show the dialog
        self.dlg = RasterAttributeTableDialog(layer)
        self.dlg.show()


if __name__ == "__main__":
    pass
