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
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME


class RATModel(QAbstractTableModel):
    """RAT data model"""

    def __init__(self, rat, parent=None):
        """Creates a RAT model from a RAT

        :param rat: RAT data
        :type rat: RAT
        """

        super().__init__(parent)
        self.rat = rat
        self.row_count = len(self.rat.values[0])
        self.headers = self.rat.keys
        self.has_color = rat.has_color
        self.editable = False

        if self.has_color:
            self.headers = self.headers[:-1]
            self.headers.insert(0, RAT_COLOR_HEADER_NAME)

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

        return self.row_count

    def columnCount(self, index, parent=QModelIndex()):

        return len(self.headers)

    def insertRows(self, row, count, parent=QModelIndex()):

        return True

    def removeRows(self, row, count, parent=QModelIndex()):

        return True

    def insertColumns(self, column, count, parent=QModelIndex()):

        return True

    def removeColumns(self, column, count, parent=QModelIndex()):

        return True
