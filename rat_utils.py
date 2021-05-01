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
from qgis.PyQt.QtCore import QFileInfo, QVariant, QCoreApplication
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsVectorLayer,
    QgsPalettedRasterRenderer,
    QgsRasterBlockFeedback,
    QgsRandomColorRamp,
    QgsMessageLog,
    Qgis,
    QgsProject,
    QgsMapLayerLegendUtils,
)

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
    from .rat_classes import RATField, RAT
    from .rat_log import rat_log
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME
    from rat_classes import RATField, RAT
    from rat_log import rat_log


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
            if rat is not None:
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
                            values[headers[c]].append(
                                rat.GetValueAsDouble(r, c))
                        else:
                            values[headers[c]].append(
                                rat.GetValueAsString(r, c))

            path = raster_layer.source() + '.aux.xml'

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


def rat_classify(raster_layer, band, rat, criteria, ramp=None, feedback=QgsRasterBlockFeedback()) -> list:
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
    # A valid RAT must have a value field
    value_column_name = [field.name for field in rat.fields.values(
    ) if field.usage == gdal.GFU_MinMax][0]
    values = rat.data[value_column_name]
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


def homogenize_colors(iface, raster_layer) -> bool:
    """Assign the color of the first class to all other
    classes having the same label.

    :param iface: QGIS interface
    :type iface: QgisInterface
    :param raster_layer: raster layer
    :type raster_layer: QgsRasterLayer
    :return: TRUE if the renderer has been reset
    :rtype: bool
    """

    assert iface is not None
    assert isinstance(raster_layer.renderer(), QgsPalettedRasterRenderer)

    if len(raster_layer.renderer().classes()) == 0:
        return

    unique_classes = {}
    require_changes = False
    classes = raster_layer.renderer().classes()
    for klass in classes:
        if klass.label not in unique_classes:
            unique_classes[klass.label] = klass.color
        else:
            klass.color = unique_classes[klass.label]
            require_changes = True

    if require_changes:
        renderer = QgsPalettedRasterRenderer(
            raster_layer.dataProvider(), raster_layer.renderer().band(), classes)
        raster_layer.setRenderer(renderer)
        raster_layer.triggerRepaint()

    return require_changes


def has_rat(raster_layer) -> bool:
    """Returns TRUE if the raster layer has a RAT table

    :param raster_layer: raster layer
    :type raster_layer: QgsRasterLayer
    :return: TRUE if the layer renderer has a RAT
    :rtype: bool
    """

    if not raster_layer.isValid():
        return False

    for band in range(1, raster_layer.bandCount() + 1):
        if get_rat(raster_layer, band).isValid():
            return True

    return False


def can_create_rat(raster_layer) -> bool:
    """Returns TRUE if a RAT can be created from the raster_layer

    :param raster_layer: raster layer
    :type raster_layer: QgsRasterLayer
    :return: TRUE if the layer renderer is compatible with a RAT
    :rtype: bool
    """

    # TODO: handle singleband pseudocolor
    return raster_layer.isValid() and isinstance(raster_layer.renderer(), (QgsPalettedRasterRenderer, ))


def create_rat_from_raster(raster_layer, is_sidecar, path, feedback=QgsRasterBlockFeedback()) -> RAT:
    """Creates a new RAT object from a raster layer, an invalid RAT is returned in case of errors.

    :param raster_layer: raster layer
    :type raster_layer: QgsRasterLayer
    :param is_sidecar: raster layer
    :type is_sidecar: bool
    :return: new RAT
    :rtype: RAT
    """

    if not can_create_rat(raster_layer):
        return RAT({}, {}, '')

    renderer = raster_layer.renderer()
    band = renderer.band()
    classes = renderer.classes()

    if len(classes) == 0:
        return RAT({}, {}, '')

    is_real = isinstance(classes[0].value, float)

    fields = {
        'Value': RATField('Value', gdal.GFU_MinMax, gdal.GFT_Real if is_real else gdal.GFT_Integer),
    }

    data = {
        RAT_COLOR_HEADER_NAME: [],
        'Value': []
    }

    histogram = raster_layer.dataProvider().histogram(band, feedback=feedback)
    histogram_values = []
    if histogram.valid:
        fields['Count'] = RATField(
            'Count', gdal.GFU_PixelCount, gdal.GFT_Integer)
        data['Count'] = []
        for val in histogram.histogramVector:
            if val != 0:
                histogram_values.append(val)

    fields['Class'] = RATField('Class', gdal.GFU_Name, gdal.GFT_String)
    data['Class'] = []

    fields['R'] = RATField('R', gdal.GFU_Red, gdal.GFT_Integer)
    fields['G'] = RATField('G', gdal.GFU_Green, gdal.GFT_Integer)
    fields['B'] = RATField('B', gdal.GFU_Blue, gdal.GFT_Integer)
    fields['A'] = RATField('A', gdal.GFU_Alpha, gdal.GFT_Integer)
    data['R'] = []
    data['G'] = []
    data['B'] = []
    data['A'] = []

    i = 0
    for klass in renderer.classes():
        data[RAT_COLOR_HEADER_NAME].append(klass.color)
        data['Value'].append(klass.value)
        data['Count'].append(histogram_values[i])
        data['Class'].append(klass.label)
        data['R'].append(klass.color.red())
        data['G'].append(klass.color.green())
        data['B'].append(klass.color.blue())
        data['A'].append(klass.color.alpha())
        i += 1

    return RAT(data, is_sidecar, fields, path)


def data_type_name(data_type) -> str:
    """Returns the translated name of a gdal.GFT_* data type

    :param data_type: gdal RAT data type
    :type data_type: gdal.GFT_*
    :return: the human readable name
    :rtype: str
    """

    if data_type == gdal.GFT_Integer:
        data_type_name = QCoreApplication.translate('RAT', 'Integer')
    elif data_type == gdal.GFT_Real:
        data_type_name = QCoreApplication.translate(
            'RAT', 'Floating point')
    else:
        data_type_name = QCoreApplication.translate('RAT', 'String')

    return data_type_name


def rat_column_info() -> dict:
    """Return information about all supported and unsupported raster column types"""

    return {
        gdal.GFU_Generic: {
            'name': QCoreApplication.translate('RAT', 'General purpose field.'),
            'unique': False,
            'required': False,
            'is_color': False,
            'data_types': [gdal.GFT_Integer, gdal.GFT_Real, gdal.GFT_String],
            'supported': True,
        },
        gdal.GFU_PixelCount: {
            'name': QCoreApplication.translate('RAT', 'Histogram pixel count'),
            'unique': True,
            'required': True,
            'is_color': False,
            'data_types': [gdal.GFT_Integer],
            'supported': True,
        },
        gdal.GFU_Name: {
            'name': QCoreApplication.translate('RAT', 'Class name'),
            'unique': False,
            'required': True,
            'is_color': False,
            'data_types': [gdal.GFT_String],
            'supported': True,
        },
        gdal.GFU_MinMax: {
            'name': QCoreApplication.translate('RAT', 'Class value(min=max)'),
            'unique': True,
            'required': False,
            'is_color': False,
            'data_types': [gdal.GFT_Integer, gdal.GFT_Real],
            'supported': True,
        },
        gdal.GFU_Red: {
            'name': QCoreApplication.translate('RAT', 'Red class color (0-255)'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': True,
        },
        gdal.GFU_Green: {
            'name': QCoreApplication.translate('RAT', 'Green class color (0-255)'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': True,
        },
        gdal.GFU_Blue: {
            'name': QCoreApplication.translate('RAT', 'Blue class color (0-255)'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': True,
        },
        gdal.GFU_Alpha: {
            'name': QCoreApplication.translate('RAT', 'Alpha(0=transparent, 255=opaque)'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': True,
        },

        # NOT YET SUPPORTED!!

        gdal.GFU_Min: {
            'name': QCoreApplication.translate('RAT', 'Class range minimum'),
            'unique': True,
            'required': False,
            'is_color': False,
            'data_types': [gdal.GFT_Integer, gdal.GFT_Real],
            'supported': False,
        },
        gdal.GFU_Max: {
            'name': QCoreApplication.translate('RAT', 'Class range maximum'),
            'unique': True,
            'required': False,
            'is_color': False,
            'data_types': [gdal.GFT_Integer, gdal.GFT_Real],
            'supported': False,
        },
        gdal.GFU_RedMin: {
            'name': QCoreApplication.translate('RAT', 'Color Range Red Minimum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_GreenMin: {
            'name': QCoreApplication.translate('RAT', 'Color Range Green Minimum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_BlueMin: {
            'name': QCoreApplication.translate('RAT', 'Color Range Blue Minimum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_AlphaMin: {
            'name': QCoreApplication.translate('RAT', 'Color Range Alpha Minimum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_RedMax: {
            'name': QCoreApplication.translate('RAT', 'Color Range Red Maximum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_GreenMax: {
            'name': QCoreApplication.translate('RAT', 'Color Range Green Maximum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_BlueMax: {
            'name': QCoreApplication.translate('RAT', 'Color Range Blue Maximum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_AlphaMax: {
            'name': QCoreApplication.translate('RAT', 'Color Range Alpha Maximum'),
            'unique': True,
            'required': False,
            'is_color': True,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
        gdal.GFU_MaxCount: {
            'name': QCoreApplication.translate('RAT', 'Maximum GFU value(equals to GFU_AlphaMax+1 currently)'),
            'unique': True,
            'required': False,
            'data_types': [gdal.GFT_Integer],
            'supported': False,
        },
    }


def rat_supported_column_info() -> dict:
    """Return information about supported raster column types"""

    return {usage: info for usage, info in rat_column_info().items() if info['supported']}
