from datetime import timedelta
from functools import partial
from pathlib import Path
from sip import isdeleted
from time import sleep, time

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QFileDialog, QLabel

from ..dialog import GwAction
from ...ui.ui_manager import GwInpParsingUi, GwInpConfigImportUi
from ...utils import tools_gw
from .... import global_vars
from ....libs import tools_qgis


class GwImportInp(GwAction):
    """Button 22: Import INP"""

    def __init__(self, icon_path, action_name, text, toolbar, action_group):
        super().__init__(icon_path, action_name, text, toolbar, action_group)
        self.project_type = global_vars.project_type

    def clicked_event(self):
        """Let the user select an INP file to import"""

        # Load a select file dialog for select a file with .inp extension
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select an INP file", "", "INP files (*.inp)"
        )
        if file_path:
            file_path = Path(file_path)

            # Check if the file extension is .inp
            if file_path.suffix == ".inp":
                self.parse_inp_file(file_path)
            else:
                tools_qgis.show_warning("The file selected is not an INP file")

    def parse_inp_file(self, file_path):
        """Parse INP file, showing a log to the user"""

        # Create and show parsing dialog
        self.dlg_inp_parsing = GwInpParsingUi()
        tools_gw.load_settings(self.dlg_inp_parsing)
        self.dlg_inp_parsing.rejected.connect(
            partial(tools_gw.save_settings, self.dlg_inp_parsing)
        )
        tools_gw.open_dialog(self.dlg_inp_parsing, dlg_name="project_check")

        # Create timer
        self.t0 = time()
        self.timer = QTimer()
        self.timer.timeout.connect(
            partial(self._calculate_elapsed_time, self.dlg_inp_parsing)
        )
        self.timer.start(1000)

    def _calculate_elapsed_time(self, dialog):
        tf = time()  # Final time
        td = tf - self.t0  # Delta time

        # TODO Remove this after really importing INP
        if td > 4:
            self.timer.stop()
            self.dlg_inp_parsing.close()
            self._open_config_import_dialog()
            return

        self._update_time_elapsed(f"Exec. time: {timedelta(seconds=round(td))}", dialog)

    def _open_config_import_dialog(self):
        self.dlg_config_import = GwInpConfigImportUi()
        tools_gw.load_settings(self.dlg_config_import)
        self.dlg_config_import.rejected.connect(
            partial(tools_gw.save_settings, self.dlg_config_import)
        )
        tools_gw.open_dialog(self.dlg_config_import, dlg_name="project_check")

    def _update_time_elapsed(self, text, dialog):
        if isdeleted(dialog):
            self.timer.stop()
            return

        lbl_time = dialog.findChild(QLabel, "lbl_time")
        lbl_time.setText(text)
