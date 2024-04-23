from pathlib import Path

from .task import GwTask


class GwInpReaderTask(GwTask):
    def __init__(self, description: str, filepath: Path) -> None:
        super().__init__(description)
        self.filepath = filepath


    def run(self) -> bool:
        super().run()
        print(f"Running GwInpReaderTask with {self.filepath}")
        return True