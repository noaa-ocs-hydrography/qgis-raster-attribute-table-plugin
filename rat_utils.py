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
    QgsRasterShader,
    QgsColorRampShader,
)

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME


class RATField:

    def __init__(self, name, usage, type):
        self.name = name
        self.usage = usage
        self.type = type


class RAT:
    """Encapsulate RAT table data"""

    def __init__(self, data, is_sidecar, fields):

        self.__data = data
        self.is_sidecar = is_sidecar
        self.fields = fields

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

    return RAT(values, is_sidecar, fields)


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

    # Use paletted if there are only distinct classes
    if True or len(classes) == len(label_colors):
        rat_log('Using paletted renderer')
        renderer = QgsPalettedRasterRenderer(
            raster_layer.dataProvider(), band, classes)

    else:
        rat_log('Using singleband pseudocolor renderer')

        minValue = min(values)
        maxValue = max(values)

        shader = QgsRasterShader(minValue, maxValue)

        colorRampShaderFcn = QgsColorRampShader(
            minValue, maxValue, ramp)
        colorRampShaderFcn.setClip(True)

        items = []
        for klass in classes:
            items.append(QgsColorRampShader.ColorRampItem(
                klass.value, klass.color, klass.label))

        colorRampShaderFcn.setColorRampItemList(items)
        colorRampShaderFcn.setColorRampType(QgsColorRampShader.Exact)
        colorRampShaderFcn.setSourceColorRamp(
            colorRampShaderFcn.createColorRamp())
        colorRampShaderFcn.legendSettings().setUseContinuousLegend(False)
        shader.setRasterShaderFunction(colorRampShaderFcn)
        renderer = QgsSingleBandPseudoColorRenderer(
            raster_layer.dataProvider(), band, shader)

    raster_layer.setRenderer(renderer)
    raster_layer.triggerRepaint()

    return unique_indexes


def rat_log(message, level=Qgis.Info):

    QgsMessageLog.logMessage(message, "RAT", level)
