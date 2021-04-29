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


from osgeo import gdal

from qgis.PyQt.QtCore import QAbstractTableModel, QModelIndex, QVariant, Qt, QCoreApplication
from qgis.PyQt.QtGui import QBrush, QColor

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
    from .rat_utils import rat_log, data_type_name
    from .rat_classes import RATField
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME
    from rat_utils import rat_log, data_type_name
    from rat_classes import RATField


class RATModel(QAbstractTableModel):
    """RAT data model"""

    def __init__(self, rat, parent=None):
        """Creates a RAT model from a RAT

        :param rat: RAT data
        :type rat: RAT
        """

        super().__init__(parent)
        self.rat = rat
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

        field_name = self.headers[column]
        is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME

        if is_color:
            return True

        usage = self.rat.fields[field_name].usage

        return not self.columnIsAnyRGBData(column) and usage not in (
            gdal.GFU_Min,
            gdal.GFU_Max,
            gdal.GFU_MinMax,
            gdal.GFU_PixelCount,
            gdal.GFU_MaxCount,
        )

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
                                index.row(), self.headers.index(field.name), self.index(0, 0))
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

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.headers[section]
            except:
                pass

        if role == Qt.ToolTipRole:
            return self.getHeaderTooltip(section)

        return super().headerData(section, orientation, role)

    def rowCount(self, index, parent=QModelIndex()):

        return len(self.rat.values[0])

    def columnCount(self, index, parent=QModelIndex()):

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
        self.beginInsertColumns(self.index(0, 0), index, 1)
        result, error_message = self.rat.insert_column(rat_index, field)
        if result:
            self.insertColumn(index, self.index(0, 0))
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
        self.beginRemoveColumns(self.index(0, 0), index, 1)
        result, error_message = self.rat.remove_column(column_name)
        if result:
            self.removeColumn(index, self.index(0, 0))
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

        # Remove virtual color field
        self.beginResetModel()
        result, error_message = self.rat.remove_column(RAT_COLOR_HEADER_NAME)
        assert result, error_message
        # Remove actual color fields
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
            rat_log('Error inserting color columns: %s' % error_message)
        self.endResetModel()

        return result




