from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr


class PromptLoader(BaseModel):
    prompt: str | None = None
    _path: Path = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        import inspect

        stack = inspect.stack()

        parent_path = Path(__file__).parent

        caller_frame = None
        for frame_info in stack:
            filename = frame_info.filename
            if Path(filename).is_relative_to(parent_path):
                continue
            if "pydantic" not in filename:
                caller_frame = frame_info
                break

        self._path = Path(caller_frame.filename).parent

        prompt_path = self._path / "PROMPT.txt"
        if prompt_path.exists():
            self.prompt = prompt_path.read_text()
