# coding=utf-8
""""RAT model

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-21'
__copyright__ = 'Copyright 2021, ItOpen'


import os
from osgeo import gdal

from qgis.PyQt.QtCore import QAbstractTableModel, QModelIndex, QVariant, Qt, QCoreApplication
from qgis.PyQt.QtGui import QBrush, QColor, QPixmap
from qgis.core import QgsApplication, Qgis

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
    from .rat_utils import data_type_name
    from .rat_log import rat_log
    from .rat_classes import RATField
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME
    from rat_log import rat_log
    from rat_utils import data_type_name
    from rat_classes import RATField


class RATModel(QAbstractTableModel):
    """RAT data model"""

    def __init__(self, rat, parent=None):
        """Creates a RAT model from a RAT

        :param rat: RAT data
        :type rat: RAT
        """

        self.rat = rat
        super().__init__(parent)
        self.editable = False

    @property
    def has_color(self):

        return self.rat.has_color

    @property
    def headers(self):

        headers = list(self.rat.fields.keys())
        if self.has_color:
            headers.insert(0, RAT_COLOR_HEADER_NAME)
        return headers

    def setEditable(self, editable):

        self.editable = editable

    def columnIsAnyRGBData(self, column) -> bool:
        """Returns TRUE if the field is any color data field, note that the "RAT Color"
        field is a virtual field and not a data field.

        :param column: column index
        :type column: int
        :return: TRUE if the field is any color data field
        :rtype: bool
        """

        field_name = self.headers[column]
        is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME

        if is_color:
            return False

        return self.rat.fields[field_name].is_color

    def columnIsEditable(self, column) -> bool:
        """Checks if a column is editable, color columns are not editable directly.

        :param column: [description]
        :type column: [type]
        :return: [description]
        :rtype: bool
        """

        field_name = self.headers[column]
        is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME

        if is_color:
            return True

        return not self.columnIsAnyRGBData(column)

    def flags(self, index):

        if index.isValid():
            flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
            if self.editable and self.columnIsEditable(index.column()):
                flags |= Qt.ItemIsEditable
            return flags

        return Qt.NoItemFlags

    def data(self, index, role=Qt.DisplayRole):

        if index.isValid():

            field_name = self.headers[index.column()]
            is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME

            if role == Qt.BackgroundColorRole and is_color:
                return self.rat.data[RAT_COLOR_HEADER_NAME][index.row()]

            elif not is_color and role == Qt.TextAlignmentRole and self.rat.fields[field_name].type != gdal.GFT_String:
                return Qt.AlignRight + Qt.AlignVCenter

            elif role == Qt.ToolTipRole and self.columnIsAnyRGBData(index.column()):
                return QCoreApplication.translate('RAT', 'This data is part of a color definition: click on "%s" column to edit.' % RAT_COLOR_HEADER_NAME)

            elif role == Qt.DisplayRole or role == Qt.EditRole:
                return self.rat.data[field_name][index.row()]

        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):

        if index.isValid() and role == Qt.EditRole:
            field_name = self.headers[index.column()]
            is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME
            if is_color:
                if not isinstance(value, QColor):
                    return False
                elif self.rat.set_color(index.row(), value):
                    for field in self.rat.fields.values():
                        if field.is_color:
                            color_column_index = self.index(
                                index.row(), self.headers.index(field.name), QModelIndex())
                            self.dataChanged.emit(
                                color_column_index, color_column_index)
                    return True
                else:
                    return False

            if self.rat.fields[field_name].type == gdal.GFT_Integer:
                try:
                    self.rat.data[field_name][index.row()] = int(value)
                except:
                    return False
            elif self.rat.fields[field_name].type == gdal.GFT_Real:
                try:
                    self.rat.data[field_name][index.row()] = float(value)
                except:
                    return False
            else:
                self.rat.data[field_name][index.row()] = str(value)

            self.dataChanged.emit(index, index)
            return True

        return False

    def getUsageDescription(self, usage) -> str:

        if usage == gdal.GFU_Generic:
            return QCoreApplication.translate('RAT', 'General purpose field.')
        elif usage == gdal.GFU_PixelCount:
            return QCoreApplication.translate('RAT', 'Histogram pixel count')
        elif usage == gdal.GFU_Name:
            return QCoreApplication.translate('RAT', 'Class name')
        elif usage == gdal.GFU_Min:
            return QCoreApplication.translate('RAT', 'Class range minimum')
        elif usage == gdal.GFU_Max:
            return QCoreApplication.translate('RAT', 'Class range maximum')
        elif usage == gdal.GFU_MinMax:
            return QCoreApplication.translate('RAT', 'Class value(min=max)')
        elif usage == gdal.GFU_Red:
            return QCoreApplication.translate('RAT', 'Red class color (0-255)')
        elif usage == gdal.GFU_Green:
            return QCoreApplication.translate('RAT', 'Green class color (0-255)')
        elif usage == gdal.GFU_Blue:
            return QCoreApplication.translate('RAT', 'Blue class color (0-255)')
        elif usage == gdal.GFU_Alpha:
            return QCoreApplication.translate('RAT', 'Alpha(0=transparent, 255=opaque)')
        elif usage == gdal.GFU_RedMin:
            return QCoreApplication.translate('RAT', 'Color Range Red Minimum')
        elif usage == gdal.GFU_GreenMin:
            return QCoreApplication.translate('RAT', 'Color Range Green Minimum')
        elif usage == gdal.GFU_BlueMin:
            return QCoreApplication.translate('RAT', 'Color Range Blue Minimum')
        elif usage == gdal.GFU_AlphaMin:
            return QCoreApplication.translate('RAT', 'Color Range Alpha Minimum')
        elif usage == gdal.GFU_RedMax:
            return QCoreApplication.translate('RAT', 'Color Range Red Maximum')
        elif usage == gdal.GFU_GreenMax:
            return QCoreApplication.translate('RAT', 'Color Range Green Maximum')
        elif usage == gdal.GFU_BlueMax:
            return QCoreApplication.translate('RAT', 'Color Range Blue Maximum')
        elif usage == gdal.GFU_AlphaMax:
            return QCoreApplication.translate('RAT', 'Color Range Alpha Maximum')
        elif usage == gdal.GFU_MaxCount:
            return QCoreApplication.translate('RAT', 'Maximum GFU value(equals to GFU_AlphaMax+1 currently)')
        else:
            return ''

    def getHeaderTooltip(self, section) -> str:

        field_name = self.headers[section]
        is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME

        if is_color:
            return QCoreApplication.translate('RAT', 'Virtual color field generated from the values in RGB(A) data columns')
        else:
            usage = self.rat.fields[field_name].usage
            description = self.getUsageDescription(usage)
            data_type = self.rat.fields[field_name].usage
            type_name = data_type_name(data_type)

            return QCoreApplication.translate('RAT', f"""
            <dl>
                <dt>Role</dt><dd>{description}</dd>
                <dt>Type</dt><dd>{type_name}</dd>
            </dl>
            """)

    def headerData(self, section, orientation, role=Qt.DisplayRole):

        if orientation == Qt.Horizontal:

            if role == Qt.DisplayRole:
                try:
                    return self.headers[section]
                except:
                    pass

            elif role == Qt.ToolTipRole:
                return self.getHeaderTooltip(section)

            elif role == Qt.DecorationRole:
                field_name = self.headers[section]
                is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME
                if is_color or self.columnIsAnyRGBData(section):
                    return QgsApplication.getThemeIcon('/paletted.svg')

        return super().headerData(section, orientation, role)

    def rowCount(self, index, parent=QModelIndex()):
        if index.isValid():
            return 0
        return len(self.rat.data[self.rat.value_column])

    def columnCount(self, index, parent=QModelIndex()):
        if index.isValid():
            return 0
        return len(self.headers)

    ###########################################################
    # Utilities to manipulate columns, not part of QT model API

    def insert_column(self, index, field) -> (bool, str):
        """Inserts a field into the RAT a position index

        :param index: insertion point
        :type index: int
        :param field: RAT field to insert
        :type field: RATField
        :return: (TRUE, None) on success, (FALSE, error_message) on failure
        :rtype: tuple
        """

        assert isinstance(field, RATField)
        rat_index = index - 1 if self.rat.has_color else index
        self.beginInsertColumns(QModelIndex(), index, index)
        result, error_message = self.rat.insert_column(rat_index, field)
        if result:
            self.insertColumn(index, QModelIndex())
        self.endInsertColumns()
        return result, error_message

    def remove_column(self, index) -> (bool, str):
        """Removes the column at index.

        :param index: column to remove (0-indexed)
        :type index: int
        :return: (TRUE, None) on success, (FALSE, error_message) on failure
        :rtype: tuple
        """

        column_name = self.headers[index]
        self.beginRemoveColumns(QModelIndex(), index, index)
        result, error_message = self.rat.remove_column(column_name)
        if result:
            self.removeColumn(index, QModelIndex())
        self.endRemoveColumns()
        return result, error_message

    def remove_color(self) -> bool:
        """Removes all color information

        :return: TRUE on success
        :rtype: bool
        """

        if not self.has_color:
            return False

        color_fields = [field.name for field in self.rat.fields.values() if field.is_color]
        assert len(color_fields) > 0

        # Remove actual color fields
        self.beginResetModel()
        result = self.rat.remove_color_fields()
        assert result
        self.endResetModel()
        return True

    def insert_color(self, column) -> bool:
        """Insert color columns (RGBA) at position column

        :param column: insertion point
        :type column: int
        :return: TRUE on success
        :rtype: bool
        """

        if self.has_color:
            return False

        self.beginResetModel()
        result, error_message = self.rat.insert_color_fields(column)
        if not result:
            rat_log('Error inserting color columns: %s' % error_message, Qgis.Warning)
        self.endResetModel()

        return result

    def insert_row(self, row) -> bool:
        """Insert a new row before position row 0-indexed

        :param row: insertion point 0-indexed
        :type row: int
        :return: TRUE on success
        :rtype: bool
        """

        assert row >= 0 and row <= self.rowCount(QModelIndex()), f'Out of range {row}'
        self.beginInsertRows(QModelIndex(), row, row)
        result, error_message = self.rat.insert_row(row)
        if not result:
            rat_log('Error inserting a new row: %s' % error_message, Qgis.Warning)
        self.endInsertRows()
        row_count = self.rowCount(QModelIndex())
        rat_log(f'Row {row} inserted successfully, row count is: {row_count}', Qgis.Info)
        return result

    def remove_row(self, row) -> bool:
        """Remove the row at position row 0-indexed

        :param row: removal point 0-indexed
        :type row: int
        :return: TRUE on success
        :rtype: bool
        """

        assert row >= 0 and row < self.rowCount(QModelIndex()), f'Out of range {row}'
        self.beginRemoveRows(QModelIndex(), row, row)
        result, error_message = self.rat.remove_row(row)
        if not result:
            rat_log('Error removing a row: %s' % error_message, Qgis.Warning)
        self.endRemoveRows()
        row_count = self.rowCount(QModelIndex())
        rat_log(f'Row {row} removed successfully, row count is: {row_count}', Qgis.Info)
        return result

