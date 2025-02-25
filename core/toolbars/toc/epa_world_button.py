"""
This file is part of Giswater 3
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QObject

from ..dialog import GwAction
from ...utils import tools_gw
from ....libs import tools_qgis, tools_db, tools_os, tools_qt
from .... import global_vars

layers_subsetstrings = {}
layers_stylesheets = {}


def _get_sectors():
    sectors = "NULL"

    # get selected selectors
    sql = f'SELECT sector_id FROM selector_sector WHERE cur_user = current_user'
    rows = tools_db.get_rows(sql)
    if rows:
        sectors = ", ".join(str(x[0]) for x in rows)

    return sectors


def _get_layers():
    arc_layers = [lyr for lyr in [tools_qgis.get_layer_by_tablename('v_edit_arc')] if lyr is not None]
    node_layers = [lyr for lyr in [tools_qgis.get_layer_by_tablename('v_edit_node')] if lyr is not None]
    connec_layers = [lyr for lyr in [tools_qgis.get_layer_by_tablename('v_edit_connec')] if lyr is not None]
    gully_layers = [lyr for lyr in [tools_qgis.get_layer_by_tablename('v_edit_gully')] if lyr is not None]
    link_layers = [lyr for lyr in [tools_qgis.get_layer_by_tablename('v_edit_link')] if lyr is not None]

    return arc_layers, node_layers, connec_layers, gully_layers, link_layers


def is_epa_world_active(default=False):
    return tools_os.set_boolean(tools_gw.get_config_parser("epa_world", "epa_world_active", 'user', 'session'), default)


def set_epa_world(_set_epa_world=None, selector_change=False, is_init=False):

    # Style
    epa_style = {"Arc": 201, "Connec": 202, "Link": 203, "Node": 204, "Gully": 205}

    # Get layers
    arc_layers, node_layers, connec_layers, gully_layers, link_layers = _get_layers()

    # Get set_epa_world from config
    if _set_epa_world is None:
        _set_epa_world = is_epa_world_active(False)
    # Deactivate EPA
    if not _set_epa_world:
        tools_gw.set_config_parser("epa_world", "epa_world_active", str(_set_epa_world), 'user', 'session')
        # Disable current filters and set previous layer filters
        for layer in arc_layers + node_layers + connec_layers + gully_layers + link_layers:
            if is_init:
                # Manage style & filter
                style_manager = layer.styleManager()
                if style_manager.currentStyle() == "GwEpaStyle":
                    layer.setSubsetString(None)
                    if not style_manager.setCurrentStyle("GwStyle"):
                        style_manager.setCurrentStyle(tools_qt.tr('default', context_name='QgsMapLayerStyleManager'))
            else:
                layer.setSubsetString(layers_subsetstrings.get(layer.name()))

                # Manage style
                style_manager = layer.styleManager()
                style_manager.setCurrentStyle(layers_stylesheets.get(layer.name()))

    # Activate EPA
    else:
        tools_gw.set_config_parser("epa_world", "epa_world_active", str(_set_epa_world), 'user', 'session')
        if not selector_change:
            # Get layers subsetStrings
            for layer in arc_layers + node_layers + connec_layers + gully_layers + link_layers:
                layers_subsetstrings[layer.name()] = layer.subsetString()

                # Manage style
                style_manager = layer.styleManager()
                layers_stylesheets[layer.name()] = style_manager.currentStyle()

                if style_manager.setCurrentStyle("GwEpaStyle"):
                    pass
                else:
                    style_id = epa_style.get(f"{layer.name()}", 204)
                    tools_gw.set_layer_style(style_id, layer, True)

        sectors = _get_sectors()
        # Get inp_options_networkmode
        inp_options_networkmode = tools_gw.get_config_value('inp_options_networkmode')
        try:
            inp_options_networkmode = int(inp_options_networkmode[0])
        except (ValueError, IndexError, TypeError):
            pass

        body = tools_gw.create_body()
        json_result = tools_gw.execute_procedure('gw_fct_getnodeborder', body)
        nodes = json_result.get('body', {}).get('data', {}).get('nodes', [])

        sql = f"is_operative = true AND epa_type != 'UNDEFINED' AND sector_id IN ({sectors})"

        # arc
        for layer in arc_layers:
            layer.setSubsetString(sql)

        # node
        for layer in node_layers:
            nodes_sql = sql
            if nodes:
                node_ids = "','".join(str(node) for node in nodes)
                nodes_sql += " OR node_id IN ('{}')".format(node_ids)
            layer.setSubsetString(nodes_sql)

        if global_vars.project_type == 'ws':
            # ws connec
            for layer in connec_layers:
                if inp_options_networkmode == 4:
                    layer.setSubsetString(sql)
                else:
                    layer.setSubsetString("FALSE")

            # ws link
            for layer in link_layers:
                if inp_options_networkmode == 4:
                    layer.setSubsetString(sql)
                else:
                    layer.setSubsetString("FALSE")

        elif global_vars.project_type == 'ud':
            # ud connec
            for layer in connec_layers:
                layer.setSubsetString("FALSE")

            # ud gully
            for layer in gully_layers:
                if inp_options_networkmode == 2:
                    layer.setSubsetString(sql)
                else:
                    layer.setSubsetString("FALSE")

            # ud link
            for layer in link_layers:
                if inp_options_networkmode == 2:
                    layer.setSubsetString(sql + ' AND feature_type = \'GULLY\'')
                else:
                    layer.setSubsetString("FALSE")

    return _set_epa_world


class GwEpaWorldButton(GwAction):
    """ Button 308: Switch EPA world """

    def __init__(self, icon_path, action_name, text, toolbar, action_group):

        super().__init__(icon_path, action_name, text, toolbar, action_group)
        self.action.setCheckable(True)
        tools_gw.set_config_parser("epa_world", "epa_world_active", 'false', 'user', 'session')

    def clicked_event(self):

        self._switch_epa_world()

    # region private functions

    def _switch_epa_world(self):

        # Check world type
        epa_world_active = is_epa_world_active()

        # Apply filters
        _set_epa_world = not epa_world_active

        set_epa_world(_set_epa_world)

        # Set action checked
        self._action_set_checked(_set_epa_world)

        # Show message
        if _set_epa_world:
            msg = "EPA point of view activated"
        else:
            msg = "EPA point of view deactivated"
        tools_qgis.show_info(msg)

    def _action_set_checked(self, checked):
        # Set checked
        self.action.setChecked(checked)

    # endregion
