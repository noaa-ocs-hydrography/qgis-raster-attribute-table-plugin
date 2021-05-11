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
from qgis.PyQt.QtWidgets import QAction, QDialog, QMessageBox, QTableWidgetItem, QStyledItemDelegate, QColorDialog, QToolBar
from qgis.PyQt.QtTest import QAbstractItemModelTester
from qgis.core import Qgis, QgsApplication, QgsSettings

try:
    from ..rat_utils import get_rat, rat_classify, deduplicate_legend_entries, rat_column_info, rat_supported_column_info
    from ..rat_model import RATModel
    from ..rat_log import rat_log
    from ..rat_classes import RATField
    from ..rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA, RAT_COLOR_HEADER_NAME
except ValueError:
    from rat_utils import get_rat, rat_classify, deduplicate_legend_entries, rat_column_info, rat_supported_column_info
    from rat_log import rat_log
    from rat_model import RATModel
    from rat_classes import RATField
    from rat_constants import RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA, RAT_COLOR_HEADER_NAME

from .AddColumnDialog import AddColumnDialog
from .AddRowDialog import AddRowDialog


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


class ColorAlphaDelegate(ColorDelegate):

    def createEditor(self, parent, option, index):
        dialog = super().createEditor(parent, option, index)
        dialog.setOption(QColorDialog.ShowAlphaChannel)
        return dialog


class RasterAttributeTableDialog(QDialog):

    def __init__(self, raster_layer, iface=None):

        super().__init__(None, Qt.Dialog)
        # Set up the user interface from Designer.
        ui_path = os.path.join(os.path.dirname(
            __file__), 'Ui_RasterAttributeTableDialog.ui')
        uic.loadUi(ui_path, self)
        self.setWindowTitle(raster_layer.name() + ' — ' + self.windowTitle())

        self.raster_layer = raster_layer
        self.iface = iface
        self.editable = False
        self.is_dirty = False

        # Get band from renderer or data provider
        try:
            self.band = raster_layer.renderer().band()
            self.loadRat(self.band)
        except AttributeError:
            for band in range(1, raster_layer.dataProvider().bandCount() + 1):
                if self.loadRat(band):
                    self.band = band

        self.mRasterBand.setText(raster_layer.bandName(self.band))

        # Setup edit menu actions
        self.mActionToggleEditing = QAction(
            QgsApplication.getThemeIcon("/mActionEditTable.svg"), QCoreApplication.translate("RAT", "&Edit Attribute Table"))
        self.mActionToggleEditing.setCheckable(True)
        self.mActionNewColumn = QAction(
            QgsApplication.getThemeIcon("/mActionNewAttribute.svg"), QCoreApplication.translate("RAT", "New &Column"))
        self.mActionNewRow = QAction(
            QgsApplication.getThemeIcon("/mActionNewTableRow.svg"), QCoreApplication.translate("RAT", "New &Row"))
        self.mActionRemoveRow = QAction(
            QgsApplication.getThemeIcon("/mActionRemoveSelectedFeature.svg"), QCoreApplication.translate("RAT", "Remove Row"))
        self.mActionRemoveColumn = QAction(
            QgsApplication.getThemeIcon("/mActionDeleteAttribute.svg"), QCoreApplication.translate("RAT", "Remove Column"))
        self.mActionSaveChanges = QAction(
            QgsApplication.getThemeIcon("/mActionSaveAllEdits.svg"), QCoreApplication.translate("RAT", "&Save Changes"))

        self.mEditToolBar = QToolBar()
        self.mEditToolBar.addAction(self.mActionToggleEditing)
        self.mEditToolBar.addAction(self.mActionNewColumn)
        self.mEditToolBar.addAction(self.mActionNewRow)
        self.mEditToolBar.addAction(self.mActionRemoveColumn)
        self.mEditToolBar.addAction(self.mActionRemoveRow)
        self.mEditToolBar.addAction(self.mActionSaveChanges)
        self.layout().setMenuBar(self.mEditToolBar)

        self.setEditable(False)

        # Connections
        self.mClassifyButton.clicked.connect(self.classify)
        self.mButtonBox.accepted.connect(self.accept)
        self.mButtonBox.rejected.connect(self.reject)

        self.mActionToggleEditing.triggered.connect(self.setEditable)
        self.mActionSaveChanges.triggered.connect(self.saveChanges)
        self.mActionNewColumn.triggered.connect(self.addColumn)
        self.mActionRemoveColumn.triggered.connect(self.removeColumn)
        self.mActionNewRow.triggered.connect(self.addRow)
        self.mActionRemoveRow.triggered.connect(self.removeRow)

        try:
            self.restoreGeometry(QgsSettings().value(
                "RasterAttributeTable/geometry", None, QByteArray, QgsSettings.Plugins))
        except:
            pass

        self.updateButtons()

    def addRow(self):

        current_row = self.proxyModel.mapToSource(
            self.mRATView.selectionModel().currentIndex()).row()
        dlg = AddRowDialog(current_row)

        if dlg.exec_() == QDialog.Accepted:
            if not self.model.insert_row(current_row + (0 if dlg.mBefore.isChecked() else 1)):
                QMessageBox.warning(None,
                                    QCoreApplication.translate(
                                        'RAT', "Error Adding Row"),
                                    QCoreApplication.translate('RAT', "An error occourred while adding a new row to the RAT!"))

    def removeRow(self):

        if QMessageBox.question(None,
                                QCoreApplication.translate(
                                    'RAT', "Remove Row"),
                                QCoreApplication.translate('RAT', "Removing a row will remove the value from the RAT, do you want to continue?")) == QMessageBox.Yes:

            current_row = self.proxyModel.mapToSource(
                self.mRATView.selectionModel().currentIndex()).row()
            if not self.model.remove_row(current_row):
                QMessageBox.warning(None,
                                    QCoreApplication.translate(
                                        'RAT', "Error Removing Row"),
                                    QCoreApplication.translate('RAT', "An error occourred while removing a row from the RAT!"))

    def allowedAddedUsages(self) -> list:
        """Return the list of not-color usages that can be added

        :return: allowed usages that can be added
        :rtype: list
        """

        allowed_usages = []
        usages = self.model.rat.field_usages
        for usage, info in rat_supported_column_info().items():
            if not info['is_color'] and (not info['unique'] or usage not in usages):
                allowed_usages.append(usage)

        return allowed_usages

    def canAddAnyColumn(self) -> bool:
        """Check if any column can be added"""

        return not self.model.has_color or len(self.allowedAddedUsages()) > 0

    def addColumn(self):

        dlg = AddColumnDialog(self.model, self.iface)

        if self.model.has_color:
            dlg.mColumnType.hide()

        # List columns where insertion is allowed: skip value and count
        for field in self.model.rat.fields.values():
            if field.usage not in {gdal.GFU_MinMax, gdal.GFU_PixelCount}:
                dlg.mColumn.addItem(field.name)

        # List allowed usages
        allowed_usages = self.allowedAddedUsages()

        # Set insertion point
        col = self.proxyModel.mapToSource(
            self.mRATView.selectionModel().currentIndex()).column()
        header = self.model.headers[col]
        dlg.mColumn.setCurrentIndex(dlg.mColumn.findText(header))

        if not allowed_usages:
            if not self.model.has_color:
                dlg.mColor.setChecked(True)
                dlg.mStandardColumn.setEnabled(False)
            else:  # We cannot add any field, we should never get here!
                rat_log(
                    'Cannot add any column: this should have been checked before getting so far!', Qgis.Critical)

        else:
            usages_info = rat_column_info()
            for usage in allowed_usages:
                dlg.mUsage.addItem(usages_info[usage]['name'], usage)

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
                    # Try to update colors from current raster
                    self.model.rat.update_colors_from_raster(self.raster_layer)
                    self.is_dirty = True

            else:
                data_type = dlg.mDataType.currentData()
                usage = dlg.mUsage.currentData()
                name = dlg.mName.text()
                field = RATField(name, usage, data_type)
                result, error_message = self.model.insert_column(
                    insertion_point, field)
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
            usage = self.model.rat.fields[column_name].usage
            if self.columnIsColor(column_name) or usage in {gdal.GFU_Generic}:
                column_can_be_removed = True
            elif usage == gdal.GFU_Name:
                # Check if it's not the only one
                names_count = len(
                    [field for field in self.model.rat.fields.values() if field.usage == gdal.GFU_Name])
                if names_count > 1:
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
                                        QCoreApplication.translate('RAT', "<p>All color information (Red, Green, Blue and Alpha) will be removed from the RAT.</p><p>Do you want continue?</p>")) == QMessageBox.Yes:
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

        enable_editing_buttons = self.mRATView.selectionModel(
        ).currentIndex().isValid() and self.editable

        self.mActionNewColumn.setEnabled(
            enable_editing_buttons and self.canAddAnyColumn())
        self.mActionRemoveColumn.setEnabled(enable_editing_buttons)
        self.mActionNewRow.setEnabled(enable_editing_buttons)
        self.mActionRemoveRow.setEnabled(enable_editing_buttons)
        self.mActionSaveChanges.setEnabled(self.is_dirty)

    def setEditable(self, editable):

        if not editable and self.is_dirty:
            if QMessageBox.question(None,
                                    QCoreApplication.translate(
                                        'RAT', "Save RAT changes"),
                                    QCoreApplication.translate('RAT', "RAT has been modified, Do you want to save the changes?")) == QMessageBox.Yes:
                self.saveChanges()
            else:
                self.loadRat(self.band)

        self.editable = editable
        self.model.setEditable(editable)
        self.updateButtons()

    def saveChanges(self):
        """Store changes back into the RAT"""

        rat = self.model.rat
        if rat.save(self.band):
            self.is_dirty = False

    def accept(self):
        QgsSettings().setValue("RasterAttributeTable/geometry",
                               self.saveGeometry(), QgsSettings.Plugins)
        super().accept()

    def reject(self):

        if not self.is_dirty or QMessageBox.question(None,
                                                     QCoreApplication.translate(
                                                         'RAT', "Save RAT changes"),
                                                     QCoreApplication.translate('RAT', "<p>RAT has been modified, if you do not save the changes now or export the RAT they will be lost.</p><p>Exit without saving?<p>")) == QMessageBox.Yes:
            self.accept()

    def classify(self):
        """Create classification on the selected criteria"""

        if QMessageBox.question(None,
                                QCoreApplication.translate(
                                    'RAT', "Overwrite classification"),
                                QCoreApplication.translate('RAT', "The existing classification will be overwritten, do you want to continue?")) == QMessageBox.Yes:

            criteria = self.mClassifyComboBox.currentText()
            # TODO: ramp & feedback
            unique_class_row_indexes = rat_classify(
                self.raster_layer, self.band, self.rat, criteria)
            unique_class_row_indexes.insert(0, 0)
            if self.iface is not None:
                deduplicate_legend_entries(
                    self.iface, self.raster_layer, criteria, unique_class_row_indexes, expand=True)
            # Adopt the layer
            self.raster_layer.setCustomProperty(
                RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA, criteria)

    def updateClassify(self):

        current_index = self.mClassifyComboBox.currentIndex()
        self.mClassifyComboBox.clear()
        self.mClassifyComboBox.addItems([field.name for field in self.rat.fields.values(
        ) if field.usage in {gdal.GFU_Name, gdal.GFU_Generic}])

        if current_index > 0:
            self.mClassifyComboBox.setCurrentIndex(current_index)
        else:
            headers = self.rat.keys
            criteria = self.raster_layer.customProperty(
                RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA)
            if criteria in headers:
                self.mClassifyComboBox.setCurrentIndex(
                    self.mClassifyComboBox.findText(criteria))

    def dirty(self, *args):

        self.is_dirty = True
        rat_log('Model is dirty')
        self.updateButtons()

    def loadRat(self, band) -> bool:
        """Load RAT for raster band 1-based"""

        self.mClassifyComboBox.clear()

        self.rat = get_rat(self.raster_layer, band)

        if self.rat.keys:
            self.model = RATModel(self.rat)
            if os.environ.get('CI'):
                self.tester = QAbstractItemModelTester(self.model)
            self.model.dataChanged.connect(self.dirty)
            self.model.rowsInserted.connect(self.dirty)
            self.model.rowsRemoved.connect(self.dirty)
            self.model.columnsInserted.connect(self.dirty)
            self.model.columnsRemoved.connect(self.dirty)
            self.model.columnsInserted.connect(self.updateClassify)
            self.model.columnsRemoved.connect(self.updateClassify)
            self.proxyModel = QSortFilterProxyModel(self)
            self.proxyModel.setSourceModel(self.model)
            self.mRATView.setModel(self.proxyModel)
            self.mRATView.selectionModel().selectionChanged.connect(self.updateButtons)

            # Color picker
            if self.rat.has_color:
                if gdal.GFU_Alpha in self.rat.field_usages:
                    colorDelegate = ColorAlphaDelegate(self.mRATView)
                else:
                    colorDelegate = ColorDelegate(self.mRATView)
                self.mRATView.setItemDelegateForColumn(0, colorDelegate)

            self.updateClassify()
            self.mRATView.sortByColumn(self.model.headers.index(
                self.rat.value_columns[0]), Qt.AscendingOrder)
            return True
        else:
            rat_log(QCoreApplication.translate(
                'RAT', 'There is no Raster Attribute Table for the selected raster band %s.' % band), Qgis.Warning)
            return False
