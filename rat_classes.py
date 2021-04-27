# coding=utf-8
""""RAT data classes

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-27'
__copyright__ = 'Copyright 2021, ItOpen'

from osgeo import gdal

from qgis.PyQt.QtCore import QVariant, QCoreApplication
from qgis.core import (
    QgsFields,
    QgsField,
    QgsFeature,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
)

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME, RAT_UNIQUE_FIELDS
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME, RAT_UNIQUE_FIELDS


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

    @property
    def qgis_type(self):
        """Returns the QVariant type of the field

        :raises Exception: in case of unhandled type
        :return: QVariant type of the field
        :rtype: QVariant
        """

        if self.type == gdal.GFT_Integer:
            return QVariant.Int
        elif self.type == gdal.GFT_Real:
            return QVariant.Double
        elif self.type == gdal.GFT_String:
            return QVariant.String
        else:
            raise Exception('Unhandled RAT field type:  %s' % self.type)

    def __repr__(self):

        return f'RATField(name={self.name}, usage={self.usage}, type={self.type})'


class RAT:
    """Encapsulate RAT table data"""

    def __init__(self, data, is_sidecar, fields, path):
        """Create a RAT

        :param data: dictionary with RAT data
        :type data: dict
        :param is_sidecar: TRUE if is a .VAT.DBF sidecar RAT
        :type is_sidecar: bool
        :param fields: dictionary of RAT fields, name is the key
        :type fields: dict
        :param path: path to the RAT file (vat.dbf or aux.xml)
        :type fields: str
        """

        self.__data = data
        self.is_sidecar = is_sidecar
        self.fields = fields
        self.path = path

    @property
    def values(self) -> list:

        return list(self.__data.values())

    @property
    def keys(self) -> list:

        return list(self.__data.keys())

    @property
    def data(self) -> dict:

        return self.__data

    def isValid(self) -> bool:

        return len(self.keys) > 0

    @property
    def field_usages(self) -> set:
        """Returns all field usages in the rat

        :return: field usages
        :rtype: set
        """

        usages = set()
        for field in self.fields.values():
            usages.add(field.usage)

        return usages

    @property
    def has_color(self) -> bool:

        return RAT_COLOR_HEADER_NAME in self.keys

    def qgis_fields(self) -> QgsFields:

        fields = QgsFields()

        # collect fields
        for field in list(self.fields.values()):
            qgis_field = QgsField(field.name, field.qgis_type, comment='RAT usage: %s' % field.usage)
            fields.append(qgis_field)

        return fields

    def qgis_features(self) -> list:

        features = []
        fields = self.qgis_fields()
        for row_index in range(len(self.values[0])):
            feature = QgsFeature(fields)
            attributes = []
            for header in self.keys:
                attributes.append(self.data[header][row_index])
            feature.setAttributes(attributes)
            features.append(feature)

        return features

    def save_as_dbf(self, raster_source) -> bool:
        """Save/export a copy of the RAT to path"""

        # Add .VAT: .DBF is added by the exporter
        if not raster_source.upper().endswith('.VAT'):
            raster_source = raster_source + '.vat'

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'ESRI Shapefile'
        options.layerOptions = ['SHPT=NULL']

        writer = QgsVectorFileWriter.create(
            raster_source, self.qgis_fields(), QgsWkbTypes.Unknown, QgsCoordinateReferenceSystem(), QgsCoordinateTransformContext(), options)

        return writer.addFeatures(self.qgis_features())

    def save_as_xml(self, raster_source, band) -> bool:

        ds = gdal.OpenEx(raster_source)
        if ds:
            band = ds.GetRasterBand(band)
            if band:
                rat = gdal.RasterAttributeTable()
                for field in list(self.fields.values()):
                    rat.CreateColumn(field.name, field.type, field.usage)

                type_map = {gdal.GFT_Integer: 'Int',
                            gdal.GFT_Real: 'Double', gdal.GFT_String: 'String'}

                column_index = 0

                for field_name, values in self.data.items():
                    field = self.fields[field_name]
                    func = getattr(rat, 'SetValueAs%s' % type_map[field.type])

                    for row_index in range(len(values)):
                        func(row_index, column_index, values[row_index])

                    column_index += 1

                assert rat.GetColumnCount() == len(self.keys)
                assert rat.GetRowCount() == len(self.values[0])

                band.SetDefaultRAT(rat)

                return True

        return False

    def save(self, band) -> bool:
        """Saves the changes in the modified RAT"""

        raster_source = self.path[:-8]
        assert os.path.exists(raster_source)

        if self.is_sidecar:
            return self.save_as_dbf(raster_source)
        else:
            return self.save_as_xml(raster_source, band)

    def insert_column(self, index, field) -> (bool, str):
        """Inserts a field into the RAT a position index

        :param index: insertion point
        :type index: int
        :param field: RAT field to insert
        :type field: RATField
        :return:  (TRUE, None) on success, (FALSE, error_message) on failure
        :rtype: tuple
        """

        if index < 0 or index >= len(self.keys):
            return False, QCoreApplication.translate('RAT', 'Insertion point is out of range.')

        if field.name in self.fields.keys():
            return False, QCoreApplication.translate('RAT', 'Column %s already exists.' % field.name)

        if field.usage in RAT_UNIQUE_FIELDS and field.usage in self.field_usages:
            return False, QCoreApplication.translate('RAT', 'Column %s usage already exists and must be unique.' % field.name)

        if index < len(self.keys) - 1:
            next_key = self.keys[index]
            next_field = self.fields[next_key]
            if next_field.usage in (gdal.GFU_MinMax, gdal.GFU_PixelCount):
                return False, QCoreApplication.translate('RAT', 'Column %s cannot be inserted before a "Value" or "Count" column.' % field.name)

        # Validation ok: insert
        column_data = ['' if field.qgis_type ==
                       QVariant.String else 0] * len(self.values[0])
        self.data[field.name] = column_data

        # Fields: keep the ordering
        new_fields = {}
        i = 0
        field_index = index - 1 if self.has_color else index
        for field_name, field_data in self.fields.items():
            if field_index == i:
                new_fields[field.name] = field

            new_fields[field_name] = field_data
            i += 1

        self.fields = new_fields

        return True, None

    def remove_column(self, column_name) -> (bool, str):
        """Removes the column named column_name

        :param column_name: name of the column to remove
        :type column_name: str
        :return: (TRUE, None) on success, (FALSE, error_message) on failure
        :rtype: tuple
        """

        if column_name not in self.fields.keys() or column_name not in self.keys:
            return False, QCoreApplication.translate('RAT', 'Column %s does not exist.' % column_name)

        field_usage = self.fields[column_name].usage
        if field_usage in (gdal.GFU_MinMax, gdal.GFU_Min, gdal.GFU_Max, gdal.GFU_PixelCount):
            return False, QCoreApplication.translate('RAT', 'Removal of a "Value" or "Count" column is not allowed.')

        del(self.fields[column_name])
        del (self.data[column_name])

        return True, None
