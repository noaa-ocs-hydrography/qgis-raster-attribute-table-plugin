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
    QgsRasterBlockFeedback,
    QgsRandomColorRamp,
    QgsMessageLog,
    Qgis,
)


class RATField:

    def __init__(self, name, usage, data_type):
        self.name = name
        self.usage = usage
        self.data_type = data_type


class RAT:

    def __init__(self, values, is_sidecar, rat_fields):

        self.values = values
        self.is_sidecar = is_sidecar
        self.rat_fields = rat_fields


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
    rat_fields = {}

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
                rat_fields[column] = RATField(
                    column, rat.GetUsageOfCol(i), rat.GetTypeOfCol(i))

            for r in range(0, rat.GetRowCount()):
                for c in range(0, rat.GetColumnCount()):
                    column = headers[c]
                    if rat_fields[column].data_type == gdal.GFT_Integer:
                        values[headers[c]].append(rat.GetValueAsInt(r, c))
                    elif rat_fields[column].data_type == gdal.GFT_Real:
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
                            rat_fields[f.name()] = RATField(
                                f.name(), COLOR_ROLES[colors.index(f.name().upper())], gdal.GFT_Integer if f.type() in (QVariant.Int, QVariant.LongLong) else gdal.GFT_Real)
                        elif f.name().upper() == 'COUNT':
                            rat_fields[f.name()] = RATField(
                                f.name(), gdal.GFU_PixelCount, gdal.GFT_Integer)
                        elif f.name().upper() == 'VALUE':
                            rat_fields[f.name()] = RATField(
                                f.name(), gdal.GFU_MinMax, gdal.GFT_Integer if f.type() in (QVariant.Int, QVariant.LongLong) else gdal.GFT_Real)
                        else:
                            if f.type() in (QVariant.Int, QVariant.LongLong):
                                data_type = gdal.GFT_Integer
                            elif f.type() == QVariant.Double:
                                data_type = gdal.GFT_Real
                            else:
                                data_type = gdal.GFT_String

                            rat_fields[f.name()] = RATField(
                                f.name(), gdal.GFU_Generic, data_type)

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

        for name, f in rat_fields.items():
            if f.usage == gdal.GFU_Red:
                red = name
                is_integer = f.data_type == gdal.GFT_Integer
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
            headers.append('RAT Color')
            values['RAT Color'] = []
            for i in range(len(values[red])):
                func = 'fromRgb' if is_integer else 'fromRgbF'
                if alpha:
                    values['RAT Color'].append(getattr(QColor, func)(
                        values[red][i], values[green][i], values[blue][i], values[alpha][i]))
                else:
                    values['RAT Color'].append(getattr(QColor, func)(
                        values[red][i], values[green][i], values[blue][i]))

    return RAT(values, is_sidecar, rat_fields)


def rat_classify(raster_layer, band, rat, criteria, ramp=QgsRandomColorRamp(), feedback=QgsRasterBlockFeedback()):
    """Classify a raster

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
    :return: classes
    :rtype: list
    """

    classes = QgsPalettedRasterRenderer.classDataFromRaster(
        raster_layer.dataProvider(), band, ramp, feedback)
    has_color = 'RAT Color' in list(rat.values.keys())
    values = list(rat.values.values())[0 if not has_color else 1]
    labels = rat.values[criteria]

    label_colors = {}

    for klass in classes:
        index = values.index(klass.value)
        klass.label = str(labels[index])
        if has_color:
            if klass.label not in label_colors:
                label_colors[klass.label] = values['RAT Color'][index]
            klass.setColor(label_colors[klass.label])

    renderer = QgsPalettedRasterRenderer(
        raster_layer.dataProvider(), band, classes)
    raster_layer.setRenderer(renderer)
    return classes


def rat_log(message, level=Qgis.Info):

    QgsMessageLog.logMessage(message, "RAT", level)
