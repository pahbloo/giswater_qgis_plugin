"""
This file is part of Giswater 3
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import Qt

from ..maptool import GwMaptool
from ...utils import tools_gw
from ....libs import tools_qgis


class GwFlowTraceButton(GwMaptool):
    """ Button 56: Flow trace """

    def __init__(self, icon_path, action_name, text, toolbar, action_group):

        super().__init__(icon_path, action_name, text, toolbar, action_group)
        self.layers_added = []


    """ QgsMapTools inherited event functions """

    def canvasMoveEvent(self, event):

        # Hide marker and get coordinates
        self.vertex_marker.hide()
        event_point = self.snapper_manager.get_event_point(event)

        # Snapping
        result = self.snapper_manager.snap_to_current_layer(event_point)
        if result.isValid():
            self.snapper_manager.add_marker(result, self.vertex_marker)
            # Data for function
            self.snapped_feat = self.snapper_manager.get_snapped_feature(result)
        else:
            self.snapped_feat = None


    def canvasReleaseEvent(self, event):
        """ With left click the digitizing is finished """

        self._set_flow_trace(event)


    def activate(self):

        # set active and current layer
        self.layer_node = tools_qgis.get_layer_by_tablename("v_edit_node")
        self.iface.setActiveLayer(self.layer_node)
        self.current_layer = self.layer_node

        # Check action. It works if is selected from toolbar. Not working if is selected from menu or shortcut keys
        if hasattr(self.action, "setChecked"):
            self.action.setChecked(True)

        # Store user snapping configuration
        self.previous_snapping = self.snapper_manager.get_snapping_options()

        # Set snapping layers
        self.snapper_manager.set_snapping_layers()

        # Change cursor
        self.canvas.setCursor(self.cursor)

        # Show help message when action is activated
        if self.show_help:
            message = "Click on node to compute its upstream network"
            tools_qgis.show_info(message)

        # Control current layer (due to QGIS bug in snapping system)
        if self.canvas.currentLayer() is None:
            layer = tools_qgis.get_layer_by_tablename('v_edit_node')
            if layer:
                self.iface.setActiveLayer(layer)


    # region private functions

    def _set_flow_trace(self, event):

        if event.button() == Qt.LeftButton and self.current_layer:

            # Execute SQL function
            if self.snapped_feat is None:
                elem_id = 'null'
            else:
                elem_id = f"""{self.snapped_feat.attribute('node_id')}"""
            feature_id = f'"id":[{elem_id}]'
            point = tools_qgis.create_point(self.canvas, self.iface, event)
            scale_zoom = self.iface.mapCanvas().scale()
            extras = f' "coordinates":{{"xcoord":{point.x()},"ycoord":{point.y()}, "zoomRatio":{scale_zoom}}}'
            body = tools_gw.create_body(feature=feature_id, extras=extras)
            result = tools_gw.execute_procedure('gw_fct_graphanalytics_upstream', body)
            if not result or result['status'] == 'Failed':
                return

            # Refresh map canvas
            self.refresh_map_canvas()

            # Set action pan
            self.set_action_pan()

    # endregion
