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

from qgis.PyQt.QtCore import QAbstractTableModel, QModelIndex, QVariant, Qt
from qgis.PyQt.QtGui import QBrush, QColor

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
    from .rat_utils import rat_log, RATField
    from .rat_classes import RATField
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME
    from rat_utils import rat_log, RATField
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

    def flags(self, index):

        if index.isValid():
            field_name = self.headers[index.column()]
            is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME

            flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
            # Cannot edit values
            if self.editable and (is_color or self.rat.fields[self.headers[index.column()]].usage not in (gdal.GFU_Min, gdal.GFU_Max, gdal.GFU_MinMax, gdal.GFU_PixelCount, gdal.GFU_MaxCount)):
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

            elif role == Qt.DisplayRole or role == Qt.EditRole:
                return self.rat.data[field_name][index.row()]

        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):

        if index.isValid() and role == Qt.EditRole:
            field_name = self.headers[index.column()]
            is_color = self.has_color and field_name == RAT_COLOR_HEADER_NAME
            if is_color and not isinstance(value, QColor):
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

    def headerData(self, section, orientation, role=Qt.DisplayRole):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.headers[section]
            except:
                pass

        return None

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
            self.insertColumn(index, self.index(0,0))
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


