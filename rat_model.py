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

from qgis.PyQt.QtCore import QAbstractTableModel, QModelIndex, Qt
from qgis.PyQt.QtGui import QBrush, QColor

try:
    from .rat_constants import RAT_COLOR_HEADER_NAME
except ImportError:
    from rat_constants import RAT_COLOR_HEADER_NAME


class RATModel(QAbstractTableModel):
    """RAT data model"""

    def __init__(self, rat, parent=None):
        super().__init__(parent)
        self.rat = rat
        self.row_count = len(self.rat.values[0])
        self.headers = self.rat.keys
        self.has_color = rat.has_color

        if self.has_color:
            self.headers = self.headers[:-1]
            self.headers.insert(0, RAT_COLOR_HEADER_NAME)

    def flags(self, index):

        if index.isValid():
            is_color = self.has_color and index.column() == 0
            # Cannot edit values
            if is_color or self.rat.fields[self.headers[index.column()]].usage != gdal.GFU_MinMax:
                return Qt.ItemIsEditable | Qt.ItemIsSelectable

        return Qt.ItemIsSelectable

    def data(self, index, role=Qt.DisplayRole):

        if index.isValid():

            field_name = self.headers[index.column()]
            is_color = self.has_color and index.column() == 0

            if role == Qt.ForegroundRole:
                return QColor(Qt.black)

            if role == Qt.BackgroundColorRole and self.has_color and field_name == RAT_COLOR_HEADER_NAME:
                return self.rat.data[RAT_COLOR_HEADER_NAME][index.row()]

            if not is_color:

                if role == Qt.TextAlignmentRole and self.rat.fields[field_name].type != gdal.GFT_String:
                    return Qt.AlignRight + Qt.AlignVCenter

                if role == Qt.DisplayRole:
                    return self.rat.data[field_name][index.row()]

        return None

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

    def setData(self, index, value, role=Qt.EditRole):

        return True

    def setHeaderData(self, index, value, role=Qt.EditRole):

        return True

    def insertRows(self, row, count, parent=QModelIndex()):

        return True

    def removeRows(self, row, count, parent=QModelIndex()):

        return True

    def insertColumns(self, column, count, parent=QModelIndex()):

        return True

    def removeColumns(self, column, count, parent=QModelIndex()):

        return True
