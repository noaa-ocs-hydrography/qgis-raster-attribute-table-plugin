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
from qgis.core import (QgsApplication, QgsMapLayer, QgsMapLayerType,
                       QgsMessageLog, QgsProject, Qgis)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QPushButton

from .RasterAttributeTableDialog import RasterAttributeTableDialog
from .rat_utils import rat_log, has_rat
from .rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA


class RasterAttributeTable(object):

    def __init__(self, iface):

        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.action = QAction(
            QgsApplication.getThemeIcon("/mActionOpenTable.svg"), QCoreApplication.translate("RAT", "&Open Attribute Table"))
        rat_log("Init completed")

    def initGui(self):

        self.iface.addCustomActionForLayerType(self.action,
                                               None, QgsMapLayerType.RasterLayer, allLayers=False)

        QgsProject.instance().layerWasAdded.connect(self.connectRatActions)

        for layer in list(QgsProject.instance().mapLayers().values()):
            self.connectRatActions(layer)

        self.action.triggered.connect(self.showAttributeTable)
        rat_log("GUI loaded")

    def unload(self):

        self.iface.removeCustomActionForLayerType(self.action)
        rat_log("GUI unloaded")

    def connectRatActions(self, layer):

        if layer and layer.type() == QgsMapLayerType.RasterLayer:
            for band in range(1, layer.bandCount() + 1):
                values = has_rat(layer)
                if values:
                    self.iface.addCustomActionForLayer(self.action, layer)
                    # If layer was not adopted, notify the user the a RAT exists
                    if not layer.customProperty(RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA):

                        widget = self.iface.messageBar().createMessage(
                            QCoreApplication.translate("RAT", "RAT Available"),
                            QCoreApplication.translate("RAT", "Raster <b>%s</b> has an associated attribute table." % layer.name()))
                        button = QPushButton(widget)
                        button.setText("Open Raster Attribute Table")
                        button.pressed.connect(
                            partial(self.showAttributeTable, layer=layer))
                        widget.layout().addWidget(button)
                        self.iface.messageBar().pushWidget(widget, Qgis.Info)
                    rat_log("Custom Layer action added for: %s" %
                            layer.name())
                    break

    def showAttributeTable(self, checked=False, layer=None):

        if layer is None:
            layer = self.iface.activeLayer()
        self.dlg = RasterAttributeTableDialog(layer, self.iface)
        self.dlg.show()
