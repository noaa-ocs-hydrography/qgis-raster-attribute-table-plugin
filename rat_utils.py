# coding=utf-8
""""RAT Utilities

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-19'
__copyright__ = 'Copyright 2021, ItOpen'

import os
from osgeo import gdal
from qgis.PyQt.QtCore import QFileInfo, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsVectorLayer,
    QgsPalettedRasterRenderer,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterBlockFeedback,
    QgsRandomColorRamp,
    QgsMessageLog,
    Qgis,
    QgsProject,
    QgsMapLayerLegendUtils,
)

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME


class RATField:
    """RAT field"""

    def __init__(self, name, usage, type):
        """Create a RAT field

        :param name: name
        :type name: str
        :param usage: field usage type from gdal.GFU_*
        :type usage: enum GDALRATFieldUsage
        :param type: data type from gdal.GFT_* (Real, Int, String)
        :type type: enum GDALRATFieldType
        """
        self.name = name
        self.usage = usage
        self.type = type


class RAT:
    """Encapsulate RAT table data"""

    def __init__(self, data, is_sidecar, fields, path=None):
        """Create a RAT

        :param data: dictionary with RAT data
        :type data: dict
        :param is_sidecar: TRUE if is a sidecar RAT
        :type is_sidecar: bool
        :param fields: dictionary of RAT fields, name is the key
        :type fields: dict
        :param path: optional, path to the sidecar file
        :type fields: str
        """

        self.__data = data
        self.is_sidecar = is_sidecar
        self.fields = fields
        self.path = path

    @property
    def values(self):

        return list(self.__data.values())

    @property
    def keys(self):

        return list(self.__data.keys())

    @property
    def data(self):

        return self.__data

    @property
    def has_color(self):

        return RAT_COLOR_HEADER_NAME in self.keys


def get_rat(raster_layer, band, colors=('R', 'G', 'B', 'A')):
    """Extracts RAT from raster layer and given band

    :param raster_layer: the raster layer to classify
    :type raster_layer: QgsRasterLayer
    :param band: band number (1-based)
    :type band: int
    :param colors: name of the RGB(A) columns for sidecar DBF files, defaults to ('R', 'G', 'B', 'A')
    :type red_column_name: tuple, optional
    :return: RAT
    :rtype: RAT
    """

    headers = []
    values = {}
    fields = {}
    # For sidecar files
    path = None

    COLOR_ROLES = (gdal.GFU_Red, gdal.GFU_Green, gdal.GFU_Blue, gdal.GFU_Alpha)

    is_sidecar = False

    ds = gdal.OpenEx(raster_layer.source())
    if ds:
        band = ds.GetRasterBand(band)
        if band:
            rat = band.GetDefaultRAT()
            for i in range(0, rat.GetColumnCount()):
                column = rat.GetNameOfCol(i)
                headers.append(column)
                values[column] = []
                fields[column] = RATField(
                    column, rat.GetUsageOfCol(i), rat.GetTypeOfCol(i))

            for r in range(0, rat.GetRowCount()):
                for c in range(0, rat.GetColumnCount()):
                    column = headers[c]
                    if fields[column].type == gdal.GFT_Integer:
                        values[headers[c]].append(rat.GetValueAsInt(r, c))
                    elif fields[column].type == gdal.GFT_Real:
                        values[headers[c]].append(rat.GetValueAsDouble(r, c))
                    else:
                        values[headers[c]].append(rat.GetValueAsString(r, c))

    # Search for sidecar DBF files, `band` is ignored!
    if not values:

        info = QFileInfo(raster_layer.publicSource())
        directory = info.dir().path()
        basename = info.baseName()
        filename = info.fileName()
        candidates = (basename + '.dbf', basename + '.vat.dbf',
                      filename + '.dbf', filename + '.vat.dbf')

        for candidate in candidates:
            if os.path.exists(os.path.join(directory, candidate)):
                rat_layer = QgsVectorLayer(os.path.join(
                    directory, candidate), 'rat', 'ogr')
                if rat_layer.isValid():
                    path = os.path.join(directory, candidate)
                    for f in rat_layer.fields():
                        headers.append(f.name())
                        if f.name().upper() in colors:
                            fields[f.name()] = RATField(
                                f.name(), COLOR_ROLES[colors.index(f.name().upper())], gdal.GFT_Integer if f.type() in (QVariant.Int, QVariant.LongLong) else gdal.GFT_Real)
                        elif f.name().upper() == 'COUNT':
                            fields[f.name()] = RATField(
                                f.name(), gdal.GFU_PixelCount, gdal.GFT_Integer)
                        elif f.name().upper() == 'VALUE':
                            fields[f.name()] = RATField(
                                f.name(), gdal.GFU_MinMax, gdal.GFT_Integer if f.type() in (QVariant.Int, QVariant.LongLong) else gdal.GFT_Real)
                        else:
                            if f.type() in (QVariant.Int, QVariant.LongLong):
                                type = gdal.GFT_Integer
                            elif f.type() == QVariant.Double:
                                type = gdal.GFT_Real
                            else:
                                type = gdal.GFT_String

                            fields[f.name()] = RATField(
                                f.name(), gdal.GFU_Generic, type)

                    for header in headers:
                        values[header] = []
                    for f in rat_layer.getFeatures():
                        for header in headers:
                            values[header].append(f.attribute(header))
                    is_sidecar = True
                    break

    # Colors
    if headers:
        red = None
        green = None
        blue = None
        alpha = None
        is_integer = False

        for name, f in fields.items():
            if f.usage == gdal.GFU_Red:
                red = name
                is_integer = f.type == gdal.GFT_Integer
                continue
            if f.usage == gdal.GFU_Green:
                green = name
                continue
            if f.usage == gdal.GFU_Blue:
                blue = name
                continue
            if f.usage == gdal.GFU_Alpha:
                alpha = name
                continue

        if red and green and blue:
            headers.append(RAT_COLOR_HEADER_NAME)
            values[RAT_COLOR_HEADER_NAME] = []
            for i in range(len(values[red])):
                func = 'fromRgb' if is_integer else 'fromRgbF'
                if alpha:
                    values[RAT_COLOR_HEADER_NAME].append(getattr(QColor, func)(
                        values[red][i], values[green][i], values[blue][i], values[alpha][i]))
                else:
                    values[RAT_COLOR_HEADER_NAME].append(getattr(QColor, func)(
                        values[red][i], values[green][i], values[blue][i]))

    return RAT(values, is_sidecar, fields, path)


def rat_classify(raster_layer, band, rat, criteria, ramp=None, feedback=QgsRasterBlockFeedback()):
    """Classify a raster.

    Note: cannot use a custom shader function QgsColorRampShader subclass because it's lost in
          the clone stage of the renderer.

    :param raster_layer: the raster layer to classify
    :type raster_layer: QgsRasterLayer
    :param band: band number (1-based)
    :type band: int
    :param rat: the RAT data
    :type rat: dict
    :param criteria: key of the RAT to be used for labels
    :type criteria: str
    :param ramp: optional color ramp, defaults to QgsRandomColorRamp()
    :type ramp: QgsColorRamp, optional
    :param feedback: QGIS feedback object, defaults to QgsRasterBlockFeedback()
    :type feedback: QgsRasterBlockFeedback, optional
    :return: unique row indexes for legend items
    :rtype: list
    """
    if ramp is None:
        ramp = QgsRandomColorRamp()
    classes = QgsPalettedRasterRenderer.classDataFromRaster(
        raster_layer.dataProvider(), band, ramp, feedback)
    has_color = rat.has_color
    # Values is the first item
    # FIXME: use field role!
    values = rat.values[0]
    labels = rat.data[criteria]
    label_colors = {}
    is_integer = isinstance(values[0], int)
    unique_indexes = []

    row_index = 1
    for klass in classes:
        index = values.index(int(klass.value) if is_integer else klass.value)
        klass.label = str(labels[index])
        if klass.label not in label_colors:
            unique_indexes.append(row_index)
            if has_color:
                label_colors[klass.label] = rat.data[RAT_COLOR_HEADER_NAME][index]
            else:
                label_colors[klass.label] = klass.color
        klass.color = label_colors[klass.label]
        row_index += 1

    # Use paletted
    rat_log('Using paletted renderer')
    renderer = QgsPalettedRasterRenderer(
        raster_layer.dataProvider(), band, classes)

    raster_layer.setRenderer(renderer)
    raster_layer.triggerRepaint()

    return unique_indexes


def rat_log(message, level=Qgis.Info):

    QgsMessageLog.logMessage(message, "RAT", level)


def deduplicate_legend_entries(iface, layer, criteria, unique_class_row_indexes=None, expand=None):
    """Remove duplicate entries from layer legend.

    :param iface: QGIS interface
    :type iface: QgisInterface
    :param layer: raster layer
    :type layer: QgsRasterLayer
    :param criteria: classification criteria: label for the legend band
    :type criteria: str
    :param unique_class_row_indexes: list of 1-indexed unique entries, defaults to None
    :type unique_class_row_indexes: list, optional
    :param expand: whether to expand the legend, defaults to None
    :type expand: any, optional
    """

    assert iface is not None
    model = iface.layerTreeView().layerTreeModel()
    root = QgsProject.instance().layerTreeRoot()
    node = root.findLayer(layer.id())

    if unique_class_row_indexes is None:
        unique_class_row_indexes = [0]
        renderer = layer.renderer()
        unique_labels = []
        idx = 1
        for klass in renderer.classes():
            if klass.label not in unique_labels:
                unique_labels.append(klass.label)
                unique_class_row_indexes.append(idx)
            idx += 1

    QgsMapLayerLegendUtils.setLegendNodeOrder(
        node, unique_class_row_indexes)
    QgsMapLayerLegendUtils.setLegendNodeUserLabel(
        node, 0, criteria)
    model.refreshLayerLegend(node)
    if expand is not None:
        node.setExpanded(True)
