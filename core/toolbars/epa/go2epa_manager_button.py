"""
This file is part of Giswater 3
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import json

from functools import partial

from qgis.PyQt.QtCore import Qt, QRegExp
from qgis.PyQt.QtWidgets import QAbstractItemView, QTableView
from qgis.PyQt.QtGui import QRegExpValidator, QStandardItemModel

from ..dialog import GwAction
from ...ui.ui_manager import GwEpaManagerUi
from ...utils import tools_gw
from ....libs import tools_qt, tools_db, tools_qgis, tools_os


class GwGo2EpaManagerButton(GwAction):
    """ Button 25: Go2epa maanger """

    def __init__(self, icon_path, action_name, text, toolbar, action_group):

        super().__init__(icon_path, action_name, text, toolbar, action_group)


    def clicked_event(self):

        self._manage_go2epa()


    # region private functions

    def _manage_go2epa(self):

        # Create the dialog
        self.dlg_manager = GwEpaManagerUi()
        tools_gw.load_settings(self.dlg_manager)

        # Manage widgets
        reg_exp = QRegExp("^[A-Za-z0-9_]{1,16}$")
        self.dlg_manager.txt_result_id.setValidator(QRegExpValidator(reg_exp))
        self.dlg_manager.txt_infolog.setReadOnly(True)
        self.dlg_manager.btn_set_corporate.setEnabled(False)
        if self.project_type != 'ws':
            self.dlg_manager.btn_set_corporate.setVisible(False)
            self.dlg_manager.btn_archive.setVisible(False)

        # Fill combo box and table view
        # self._fill_combo_result_id()
        self.dlg_manager.tbl_rpt_cat_result.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._fill_manager_table()
        model = self.dlg_manager.tbl_rpt_cat_result.model()
        model.itemChanged.connect(partial(self._update_data))
        model.flags = lambda index: self.flags(index, model)

        # Set signals
        self.dlg_manager.btn_archive.clicked.connect(partial(self._set_rpt_archived, self.dlg_manager.tbl_rpt_cat_result,
                                                              'result_id'))
        self.dlg_manager.btn_set_corporate.clicked.connect(partial(self._epa2data, self.dlg_manager.tbl_rpt_cat_result,
                                                              'result_id'))
        self.dlg_manager.btn_delete.clicked.connect(partial(self._multi_rows_delete, self.dlg_manager.tbl_rpt_cat_result,
                                                            'v_ui_rpt_cat_result', 'result_id'))
        selection_model = self.dlg_manager.tbl_rpt_cat_result.selectionModel()
        selection_model.selectionChanged.connect(partial(self._fill_txt_infolog))
        selection_model.selectionChanged.connect(partial(self._enable_btn_corporate))
        self.dlg_manager.tbl_rpt_cat_result.doubleClicked.connect(partial(self._set_result_id, self.dlg_manager, self.dlg_manager.tbl_rpt_cat_result))
        self.dlg_manager.btn_close.clicked.connect(partial(tools_gw.close_dialog, self.dlg_manager))
        self.dlg_manager.rejected.connect(partial(tools_gw.close_dialog, self.dlg_manager))
        self.dlg_manager.txt_result_id.textChanged.connect(partial(self._fill_manager_table))

        # Open form
        tools_gw.open_dialog(self.dlg_manager, dlg_name='go2epa_manager')


    def _fill_manager_table(self, filter_id=None):
        """ Fill dscenario manager table with data from v_edit_cat_dscenario """

        complet_list = self._get_list("v_ui_rpt_cat_result", filter_id)

        if complet_list is False:
            return False, False
        for field in complet_list['body']['data']['fields']:
            if field.get('hidden'): continue
            model = self.dlg_manager.tbl_rpt_cat_result.model()
            if model is None:
                model = QStandardItemModel()
                self.dlg_manager.tbl_rpt_cat_result.setModel(model)
            model.removeRows(0, model.rowCount())

            if field['value']:
                self.dlg_manager.tbl_rpt_cat_result = tools_gw.add_tableview_header(self.dlg_manager.tbl_rpt_cat_result, field)
                self.dlg_manager.tbl_rpt_cat_result = tools_gw.fill_tableview_rows(self.dlg_manager.tbl_rpt_cat_result, field)

        tools_gw.set_tablemodel_config(self.dlg_manager, self.dlg_manager.tbl_rpt_cat_result, 'v_ui_rpt_cat_result', isQStandardItemModel=True)
        tools_qt.set_tableview_config(self.dlg_manager.tbl_rpt_cat_result, edit_triggers=QTableView.DoubleClicked)

        return complet_list


    def _get_list(self, table_name='v_ui_rpt_cat_result', filter_id=None):
        """ Mount and execute the query for gw_fct_getlist """

        feature = f'"tableName":"{table_name}"'
        filter_fields = f'"limit": -1'
        if filter_id:
            filter_fields += f', "result_id": {{"filterSign":"ILIKE", "value":"{filter_id}"}}'
        body = tools_gw.create_body(feature=feature, filter_fields=filter_fields)
        json_result = tools_gw.execute_procedure('gw_fct_getlist', body)
        if json_result is None or json_result['status'] == 'Failed':
            return False
        complet_list = json_result
        if not complet_list:
            return False

        return complet_list


    def flags(self, index, model):

        # print(index.column())
        if index.column() != 1:
            flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            return flags

        return QStandardItemModel.flags(model, index)


    def _update_data(self, item):

        index = item.index()
        result_id = index.sibling(index.row(), 0).data()
        value = index.sibling(index.row(), index.column()).data()

        sql = f"UPDATE v_ui_rpt_cat_result SET expl_id = {value} WHERE result_id = '{result_id}';"
        result = tools_db.execute_sql(sql)
        if result:
            self._fill_manager_table(tools_qt.get_text(self.dlg_manager, 'txt_result_id'))


    def _fill_txt_infolog(self, selected):
        """
        Fill txt_infolog from epa_result_manager form with current data selected for columns:
            'export_options'
            'network_stats'
            'inp_options'
        """

        # Get id of selected row
        row = selected.indexes()
        if not row:
            tools_qt.set_widget_text(self.dlg_manager, 'txt_infolog', '')
            return

        msg = ""

        try:
            # Get column index for column export_options
            col_ind = tools_qt.get_col_index_by_col_name(self.dlg_manager.tbl_rpt_cat_result, 'export_options')
            export_options = json.loads(f'{row[col_ind].data()}')

            # Construct message with all data rows
            msg += f"<b>Export Options: </b> <br>"
            for text in export_options:
                msg += f"{text} : {export_options[text]} <br>"
        except Exception:
            pass

        try:
            # Get column index for column network_stats
            col_ind = tools_qt.get_col_index_by_col_name(self.dlg_manager.tbl_rpt_cat_result, 'network_stats')
            network_stats = json.loads(f'{row[col_ind].data()}')

            msg += f" <br> <b>Network Status: </b> <br>"
            for text in network_stats:
                msg += f"{text} : {network_stats[text]} <br>"
        except Exception:
            pass

        try:
            # Get column index for column inp_options
            col_ind = tools_qt.get_col_index_by_col_name(self.dlg_manager.tbl_rpt_cat_result, 'inp_options')
            inp_options = json.loads(f'{row[col_ind].data()}')

            msg += f" <br> <b>Inp Options: </b> <br>"
            for text in inp_options:
                msg += f"{text} : {inp_options[text]} <br>"
        except Exception:
            pass

        # Set message text into widget
        tools_qt.set_widget_text(self.dlg_manager, 'txt_infolog', msg)


    def _enable_btn_corporate(self, selected):
        valid = True
        selected_rows = self.dlg_manager.tbl_rpt_cat_result.selectionModel().selectedRows()
        for idx, index in enumerate(selected_rows):
            col_idx = tools_qt.get_col_index_by_col_name(self.dlg_manager.tbl_rpt_cat_result, 'rpt_stats')
            row = index.row()
            status = index.sibling(row, col_idx).data()
            if not status:
                valid = False

        if not selected_rows:
            valid = False
        self.dlg_manager.btn_set_corporate.setEnabled(valid)


    def _fill_combo_result_id(self):

        sql = "SELECT result_id FROM v_ui_rpt_cat_result ORDER BY result_id"
        rows = tools_db.get_rows(sql)
        tools_qt.fill_combo_values(self.dlg_manager.txt_result_id, rows, add_empty=True)


    def _filter_by_result_id(self):

        table = self.dlg_manager.tbl_rpt_cat_result
        widget_txt = self.dlg_manager.txt_result_id
        tablename = 'v_ui_rpt_cat_result'
        result_id = tools_qt.get_text(self.dlg_manager, widget_txt)
        if result_id != 'null':
            expr = f" result_id ILIKE '%{result_id}%'"
            # Refresh model with selected filter
            table.model().setFilter(expr)
            table.model().select()
        else:
            message = tools_qt.fill_table(table, tablename)
            if message:
                tools_qgis.show_warning(message)


    def _multi_rows_delete(self, widget, table_name, column_id):
        """ Delete selected elements of the table
        :param QTableView widget: origin
        :param table_name: table origin
        :param column_id: Refers to the id of the source table
        """

        # Get selected rows
        selected_list = widget.selectionModel().selectedRows()
        if len(selected_list) == 0:
            message = "Any record selected"
            tools_qgis.show_warning(message, dialog=self.dlg_manager)
            return

        inf_text = ""
        list_id = ""
        for i in range(0, len(selected_list)):
            row = selected_list[i].row()
            col = tools_qt.get_col_index_by_col_name(widget, str(column_id))
            id_ = widget.model().index(row, col).data()
            inf_text += f"{id_}, "
            list_id += f"'{id_}', "
        inf_text = inf_text[:-2]
        list_id = list_id[:-2]
        message = "Are you sure you want to delete these records?"
        title = "Delete records"
        answer = tools_qt.show_question(message, title, inf_text)
        if answer:
            sql = f"DELETE FROM {table_name}"
            sql += f" WHERE {column_id} IN ({list_id})"
            tools_db.execute_sql(sql)
            self._fill_manager_table(tools_qt.get_text(self.dlg_manager, 'txt_result_id'))


    def _set_rpt_archived(self, widget, column_id):
        """ Call gw_fct_set_rpt_archived with selected result_id
                :param QTableView widget: origin
                :param table_name: table origin
                :param column_id: Refers to the id of the source table
                """

        # Get selected rows
        selected_list = widget.selectionModel().selectedRows()
        if len(selected_list) == 0:
            message = "Any record selected"
            tools_qgis.show_warning(message, dialog=self.dlg_manager)
            return

        row = selected_list[0].row()
        col = tools_qt.get_col_index_by_col_name(widget, str(column_id))
        result_id = widget.model().index(row, col).data()

        # check corporate
        extras = f'"result_id":"{result_id}"'
        body = tools_gw.create_body(extras=extras)
        result = tools_gw.execute_procedure('gw_fct_set_rpt_archived', body)

        if not result or result.get('status') != 'Accepted':
            message = "gw_fct_set_rpt_archived execution failed. See logs for more details..."
            tools_qgis.show_warning(message, dialog=self.dlg_manager)
            return

        message = "Set rpt archived execution successful."
        tools_qgis.show_info(message, dialog=self.dlg_manager)
        # Refresh table
        self._fill_manager_table()


    def _epa2data(self, widget, column_id):
        """ Delete selected elements of the table
                :param QTableView widget: origin
                :param table_name: table origin
                :param column_id: Refers to the id of the source table
                """

        # Get selected rows
        selected_list = widget.selectionModel().selectedRows()
        if len(selected_list) == 0:
            message = "Any record selected"
            tools_qgis.show_warning(message, dialog=self.dlg_manager)
            return

        result_id = ""
        set_corporate = True
        for i in range(0, len(selected_list)):
            row = selected_list[i].row()
            col = tools_qt.get_col_index_by_col_name(widget, str(column_id))
            result_id = widget.model().index(row, col).data()
            col = tools_qt.get_col_index_by_col_name(widget, "iscorporate")
            set_corporate = widget.model().index(row, col).data()
        set_corporate = not tools_os.set_boolean(set_corporate, False)

        # check corporate
        extras = f'"resultId":"{result_id}", "action": "CHECK"'
        body = tools_gw.create_body(extras=extras)
        result = tools_gw.execute_procedure('gw_fct_epa2data', body)

        if not result or result.get('status') != 'Accepted':
            message = "Epa2data execution failed. See logs for more details..."
            tools_qgis.show_warning(message, dialog=self.dlg_manager)
            return

        current_sectors = result['body']['data']['info']['currentSectors']
        affected_results = result['body']['data']['info']['affectedResults']

        if current_sectors and current_sectors > 0:
            msg = (f"There are {current_sectors} sectors with affected results: {affected_results}. "
                   "Would you like to conitnue?")
        else:
            msg = ("You are going to make this result corporate. From now on the result values will appear on feature form. "
                   "Do you want to continue?")

        answer = tools_qt.show_question(msg)
        if not answer:
            return

        extras = f'"resultId":"{result_id}", "isCorporate": {str(set_corporate).lower()}'
        body = tools_gw.create_body(extras=extras)
        result = tools_gw.execute_procedure('gw_fct_epa2data', body)
        if not result or result.get('status') != 'Accepted':
            message = "Epa2data execution failed. See logs for more details..."
            tools_qgis.show_warning(message, dialog=self.dlg_manager)
            return
        message = "Epa2data execution successful."
        tools_qgis.show_info(message, dialog=self.dlg_manager)
        # Refresh table
        self._fill_manager_table()

    def _set_result_id(self, dialog, widget):
        selected_list = widget.selectionModel().selectedRows()
        if len(selected_list) == 0:
            message = "Any record selected"
            tools_qgis.show_warning(message, dialog=dialog)
            return

        row = selected_list[0].row()
        table_model = widget.model()
        result_id = table_model.data(table_model.index(row, 0))
        sql = f"DELETE FROM selector_rpt_main WHERE cur_user = current_user;" \
              f"INSERT INTO selector_rpt_main (result_id, cur_user) VALUES ('{result_id}', current_user);"
        tools_db.execute_sql(sql)
    # endregion
