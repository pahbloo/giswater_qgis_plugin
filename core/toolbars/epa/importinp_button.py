from ..dialog import GwAction
from .... import global_vars


class GwImportInp(GwAction):
    """Button 22: Import INP"""

    def __init__(self, icon_path, action_name, text, toolbar, action_group):
        super().__init__(icon_path, action_name, text, toolbar, action_group)
        self.project_type = global_vars.project_type
