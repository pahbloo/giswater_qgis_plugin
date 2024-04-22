from pathlib import Path

from qgis.PyQt.QtWidgets import QFileDialog

from ..dialog import GwAction
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
                # TODO Import the INP file
                pass
            else:
                tools_qgis.show_warning("The file selected is not an INP file")
