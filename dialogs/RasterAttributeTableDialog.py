# -*- coding: utf-8 -*-
"""
***************************************************************************
Name			 	 : RasterAttributeTable
Description          : RasterAttributeTable
Date                 : 12/Oct/2020
copyright            : (C) 2020 by ItOpen
email                : info@itopen.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""


import os
from osgeo import gdal

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QCoreApplication, QByteArray, QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QStyledItemDelegate, QColorDialog
from qgis.core import Qgis, QgsApplication, QgsSettings

try:
    from ..rat_utils import get_rat, rat_classify, rat_log, deduplicate_legend_entries
    from ..rat_model import RATModel
    from ..rat_classes import RATField
    from ..rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA, RAT_COLOR_HEADER_NAME
except ValueError:
    from rat_utils import get_rat, rat_classify, rat_log, deduplicate_legend_entries
    from rat_model import RATModel
    from rat_classes import RATField
    from rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA, RAT_COLOR_HEADER_NAME

from .AddColumnDialog import AddColumnDialog


class ColorDelegate(QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        dialog = QColorDialog(parent)
        return dialog

    def setEditorData(self, editor, index):
        color = index.data()
        editor.setCurrentColor(color)

    def setModelData(self, editor, model, index):
        color = editor.currentColor()
        model.setData(index, color)


class RasterAttributeTableDialog(QDialog):

    def __init__(self, layer, iface=None):

        QDialog.__init__(self)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_RasterAttributeTableDialog.ui')
        uic.loadUi(ui_path, self)

        self.layer = layer
        self.iface = iface
        self.editable = False
        self.is_dirty = False

        self.mRasterBandsComboBox.addItems(
            [layer.bandName(bn) for bn in range(1, layer.bandCount() + 1)])

        self.mToggleEditingToolButton.setIcon(
            QgsApplication.getThemeIcon("/mActionToggleEditing.svg"))
        self.mAddColumnToolButton.setIcon(
            QgsApplication.getThemeIcon("/mActionNewAttribute.svg"))
        self.mRemoveColumnToolButton.setIcon(
            QgsApplication.getThemeIcon("/mActionDeleteAttribute.svg"))
        self.mSaveChangesToolButton.setIcon(
            QgsApplication.getThemeIcon("/mActionSaveAllEdits.svg"))

        stylesheet = "QToolButton {padding: 1px;}"
        self.mToggleEditingToolButton.setStyleSheet(stylesheet)
        self.mAddColumnToolButton.setStyleSheet(
            stylesheet)
        self.mRemoveColumnToolButton.setStyleSheet(
            stylesheet)
        self.mSaveChangesToolButton.setStyleSheet(
            stylesheet)

        assert self.loadRat(0)

        self.setEditable(False)

        # Connections
        self.mClassifyButton.clicked.connect(self.classify)
        self.mRasterBandsComboBox.currentIndexChanged.connect(
            self.loadRat)
        self.mButtonBox.accepted.connect(self.accept)
        self.mButtonBox.rejected.connect(self.reject)

        self.mToggleEditingToolButton.toggled.connect(self.setEditable)
        self.mSaveChangesToolButton.clicked.connect(self.saveChanges)
        self.mAddColumnToolButton.clicked.connect(self.addColumn)
        self.mRemoveColumnToolButton.clicked.connect(self.removeColumn)

        try:
            self.restoreGeometry(QgsSettings().value(
                "RasterAttributeTable/geometry", None, QByteArray, QgsSettings.Plugins))
        except:
            pass

        self.updateButtons()

    def addColumn(self):

        dlg = AddColumnDialog(self.model, self.iface)

        if self.model.has_color:
            dlg.mColumnType.hide()

        # List columns where insertion is allowed: skip value and count
        for field in self.model.rat.fields.values():
            if field.usage not in {gdal.GFU_MinMax, gdal.GFU_PixelCount}:
                dlg.mColumn.addItem(field.name)

        if dlg.exec_() == QDialog.Accepted:
            position = dlg.mColumn.currentText()
            after = dlg.mAfter.isChecked()
            insertion_point = self.model.headers.index(
                position) + (1 if after else 0)

            if dlg.mColor.isChecked():
                if not self.model.insert_color(insertion_point):
                    QMessageBox.warning(None,
                                        QCoreApplication.translate(
                                            'RAT', "Error Adding Colors"),
                                        QCoreApplication.translate('RAT', "An error occourred while adding colors to the RAT!"))
                else:
                    self.is_dirty = True

            else:
                data_type = dlg.mType.currentData()
                name = dlg.mName.text()
                field = RATField(name, gdal.GFU_Generic, data_type)
                result, error_message = self.model.insert_column(insertion_point, field)
                if not result:
                    QMessageBox.warning(None,
                                        QCoreApplication.translate(
                                            'RAT', "Error Adding Column"),
                                        QCoreApplication.translate('RAT', "An error occourred while adding a column to the RAT: %s" % error_message))
                else:
                    self.is_dirty = True


    def columnIsColor(self, column_name) -> bool:

        return (column_name == RAT_COLOR_HEADER_NAME) or self.model.rat.fields[column_name].is_color

    def selectedColumnCanBeRemoved(self) -> bool:

        selected_column = self.mRATView.selectionModel().currentIndex().column()
        column_can_be_removed = False
        try:
            column_name = self.model.headers[selected_column]
            if self.columnIsColor(column_name) or self.model.rat.fields[column_name].usage in {gdal.GFU_Generic}:
                column_can_be_removed = True
        except Exception as ex:
            rat_log('Could not get selected column type: %s' % ex)

        return column_can_be_removed

    def removeColumn(self):

        if not self.selectedColumnCanBeRemoved():
            rat_log('Selected column cannot be removed!')
        else:
            selected_column = self.mRATView.selectionModel().currentIndex().column()
            column_name = self.model.headers[selected_column]

            # Handle color columns
            if self.columnIsColor(column_name):
                if QMessageBox.question(None,
                                        QCoreApplication.translate(
                                            'RAT', "Remove All Colors"),
                                        QCoreApplication.translate('RAT', "All color information (Red, Green, Blue and Alpha) will be removed from the RAT. Do you want continue?")) == QMessageBox.Yes:
                    # Remove all colors
                    if not self.model.remove_color():
                        QMessageBox.warning(None,
                                            QCoreApplication.translate(
                                                'RAT', "Error Removing Colors"),
                                            QCoreApplication.translate('RAT', "An error occourred while removing colors from the RAT!"))
                    else:
                        self.is_dirty = True

            # Normal columns
            elif QMessageBox.question(None,
                                      QCoreApplication.translate(
                                          'RAT', "Remove Column"),
                                      QCoreApplication.translate('RAT', "Column <b>%s</b> will be removed from the RAT. Do you want continue?" % column_name)) == QMessageBox.Yes:
                result, error_message = self.model.remove_column(
                    selected_column)
                if not result:
                    QMessageBox.warning(None,
                                        QCoreApplication.translate(
                                            'RAT', "Error Removing Column"),
                                        QCoreApplication.translate('RAT', "An error occourred while removing colum <b>%s</b> from the RAT: %s!" % (column_name, error_message)))
                else:
                    self.is_dirty = True

    def updateButtons(self):

        self.mAddColumnToolButton.setEnabled(self.editable)
        self.mRemoveColumnToolButton.setEnabled(
            self.editable and self.selectedColumnCanBeRemoved())
        self.mSaveChangesToolButton.setEnabled(self.is_dirty)

    def setEditable(self, editable):

        if not editable and self.is_dirty:
            if QMessageBox.question(None,
                                    QCoreApplication.translate(
                                        'RAT', "Save RAT changes"),
                                    QCoreApplication.translate('RAT', "RAT has been modified, Do you want to save the changes?")) == QMessageBox.Yes:
                self.saveChanges()
            else:
                self.loadRat(self.mRasterBandsComboBox.currentIndex())

        self.editable = editable
        self.model.setEditable(editable)
        self.updateButtons()

    def saveChanges(self):
        """Store changes back into the RAT"""

        rat = self.model.rat
        band = self.mRasterBandsComboBox.currentIndex() + 1
        rat.save(band)

    def accept(self):
        QgsSettings().setValue("RasterAttributeTable/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)
        super().accept()

    def reject(self):

        if not self.is_dirty or QMessageBox.question(None,
                                                     QCoreApplication.translate(
                                                         'RAT', "Save RAT changes"),
                                                     QCoreApplication.translate('RAT', "RAT has been modified, if you do not save the changes they will be lost. Do you really want to leave this dialog?")) == QMessageBox.Yes:
            self.accept()

    def classify(self):
        """Create a paletted/unique-value classification"""

        if QMessageBox.question(None,
                                QCoreApplication.translate(
                                    'RAT', "Overwrite classification"),
                                QCoreApplication.translate('RAT', "The existing classification will be overwritten, do you want to continue?")) == QMessageBox.Yes:
            band = self.mRasterBandsComboBox.currentIndex() + 1
            criteria = self.mClassifyComboBox.currentText()
            rat = get_rat(self.layer, band)
            # TODO: ramp & feedback
            unique_class_row_indexes = rat_classify(
                self.layer, band, rat, criteria)
            unique_class_row_indexes.insert(0, 0)
            if self.iface is not None:
                deduplicate_legend_entries(
                    self.iface, self.layer, criteria, unique_class_row_indexes, expand=True)
            # Adopt the layer
            self.layer.setCustomProperty(
                RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA, criteria)

    def dirty(self, *args):

        self.is_dirty = True
        self.mSaveChangesToolButton.setEnabled(self.is_dirty)

    def loadRat(self, band_0_based) -> bool:
        """Load RAT for raster band 0-based"""

        if type(band_0_based) != int:
            rat_log(QCoreApplication.translate(
                'RAT', 'Invalid band number for the selected raster.'), Qgis.Critical)
            return False

        self.mClassifyComboBox.clear()

        rat = get_rat(self.layer, band_0_based + 1)

        if rat.keys:
            self.model = RATModel(rat)
            self.model.dataChanged.connect(self.dirty)
            self.proxyModel = QSortFilterProxyModel(self)
            self.proxyModel.setSourceModel(self.model)
            self.mRATView.setModel(self.proxyModel)
            self.mRATView.selectionModel().selectionChanged.connect(self.updateButtons)
            if rat.has_color:
                colorDelegate = ColorDelegate(self.mRATView)
                self.mRATView.setItemDelegateForColumn(0, colorDelegate)
            headers = rat.keys
            self.mClassifyComboBox.addItems(headers[2:])
            criteria = self.layer.customProperty(
                RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA)
            if criteria in headers:
                self.mClassifyComboBox.setCurrentIndex(
                    self.mClassifyComboBox.findText(criteria))
            return True
        else:
            rat_log(QCoreApplication.translate(
                'RAT', 'There is no Raster Attribute Table for the selected raster.'), Qgis.Critical)
            return False
